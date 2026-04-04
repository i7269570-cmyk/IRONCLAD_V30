# ============================================================
# IRONCLAD_V31 - Strategic Entry Engine (V31.18 Full Visibility)
# ============================================================
import os
import yaml
import operator
import traceback
from typing import List, Dict, Any
import pandas as pd

# [2-1] OPERATORS 정의
OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq
}

# [2-2] load_strategy_entry_rules
def load_strategy_entry_rules(strategy_path: str) -> Dict[str, Any]:
    all_rules = {}
    if not os.path.exists(strategy_path):
        raise RuntimeError(f"STRATEGY_ROOT_MISSING: {strategy_path}")

    for folder in os.listdir(strategy_path):
        folder_path = os.path.join(strategy_path, folder)
        if not os.path.isdir(folder_path):
            continue
        
        rules_file = os.path.join(folder_path, "entry_rules.yaml")
        if os.path.exists(rules_file):
            try:
                with open(rules_file, "r", encoding="utf-8") as f:
                    rules_data = yaml.safe_load(f)
                    if rules_data and "entry" in rules_data:
                        all_rules[folder] = rules_data["entry"]
            except Exception as e:
                print(f"[ERROR] Strategy Load Failed: {rules_file} | {str(e)}")
    
    return all_rules

# [2-3] evaluate_condition (NaN 및 유효성 검증 강화)
def evaluate_condition(last_row: pd.Series, condition: Dict[str, Any]) -> bool:
    field = condition.get("field")
    op_str = condition.get("op")
    
    if field not in last_row:
        raise RuntimeError(f"FIELD_NOT_FOUND: {field}")
    if op_str not in OPERATORS:
        raise RuntimeError(f"INVALID_OPERATOR: {op_str}")

    left_val = last_row[field]
    
    # [CRITICAL] NaN 탐지: 무음 통과 방지
    if pd.isna(left_val):
        raise RuntimeError(f"NAN_VALUE_DETECTED: field '{field}'")

    op_func = OPERATORS[op_str]

    if "value" in condition:
        right_val = float(condition["value"])
    elif "ref" in condition:
        ref_field = condition["ref"]
        if ref_field not in last_row:
            raise RuntimeError(f"REF_FIELD_NOT_FOUND: {ref_field}")
        
        multiplier = float(condition.get("multiplier", 1.0))
        right_val = last_row[ref_field]
        
        if pd.isna(right_val):
            raise RuntimeError(f"NAN_REF_VALUE_DETECTED: field '{ref_field}'")
            
        right_val *= multiplier
    else:
        raise RuntimeError(f"INCOMPLETE_CONDITION_SPEC: {field}")

    return op_func(left_val, right_val)

# [2-4] generate_signals (V31.18: No-Silent-Failure Structure)
def generate_signals(
    data_bundle: Dict[str, Dict[str, Any]], 
    strategy_path: str, 
    state: Dict[str, Any], 
    system_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    [V31.18 시그널 생성 엔진]
    - 모든 예외(RuntimeError, Exception)에 대해 명시적 로깅 강제.
    - 예외 발생 시 is_qualified는 False가 되나, 원인은 반드시 표준 출력에 기록됨.
    """
    signals = []
    strategy_rules = load_strategy_entry_rules(strategy_path)
    if not strategy_rules:
        return []

    for symbol, bundle in data_bundle.items():
        current = bundle["current"]
        history = bundle["history"]

        if history.empty:
            continue
            
        if "asset_type" not in history.columns:
            raise RuntimeError(f"DATA_CONTRACT_VIOLATION: asset_type column missing for {symbol}")

        last_row = history.iloc[-1]

        for strategy_name, entry_cfg in strategy_rules.items():
            conditions = entry_cfg.get("conditions", [])
            if not conditions:
                continue

            is_qualified = True
            try:
                for cond in conditions:
                    if not evaluate_condition(last_row, cond):
                        is_qualified = False
                        break
            
            # 1. 의도된 데이터 무결성 예외 (NaN 등)
            except RuntimeError as re:
                print(f"[INTEGRITY_SIGNAL_REJECTED] {symbol} | {strategy_name} | Reason: {str(re)}")
                is_qualified = False
                continue 

            # 2. 예기치 못한 일반 예외 (타입 에러, 인덱스 에러 등)
            except Exception as e:
                # [V31.18 핵심] 예외를 무음 흡수하지 않고 트레이스백을 출력하여 개발자에게 경고
                print(f"[UNEXPECTED_ENGINE_ERROR] {symbol} | {strategy_name}")
                print(traceback.format_exc()) 
                is_qualified = False
                continue
            
            if is_qualified:
                # 시그널 생성 직전 최종 실행 값(Snapshot) 유효성 검사
                if pd.isna(current.get("price")):
                    print(f"[EXECUTION_REJECTED] {symbol} | Price is NaN")
                    continue

                signals.append({
                    "symbol": symbol,
                    "side": "BUY",
                    "price": float(current["price"]),
                    "asset_type": str(current["asset_type"]),
                    "strategy_name": strategy_name,
                    "risk_per_trade": entry_cfg.get("risk_per_trade"),
                    "stop_distance": entry_cfg.get("stop_distance")
                })
                # 1자산 1신호 원칙 준수
                break
                x = 999
    return signals