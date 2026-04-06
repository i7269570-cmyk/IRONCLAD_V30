# ============================================================
# IRONCLAD_V31.19 - Strategic Entry Engine (Direct ID-Binding)
# ============================================================
import os
import yaml
import operator
import traceback
from typing import List, Dict, Any
import pandas as pd

# [1] 지원 연산자 정의 (원칙 1 준수)
OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq
}

# [2] 전략별 진입 규칙 로드 (원칙 6, 10 준수)
def load_strategy_entry_rules(strat_path: str) -> Dict[str, Any]:
    rules_file = os.path.join(strat_path, "entry_rules.yaml")
    if not os.path.exists(rules_file):
        return {}

    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            rules_data = yaml.safe_load(f)
            if rules_data and "entry" in rules_data:
                return rules_data["entry"]
    except Exception as e:
        print(f"[ERROR] Strategy Load Failed: {rules_file} | {str(e)}")
    
    return {}

# [3] YAML 조건 해석기 (원칙 1, 2, 9 준수)
def evaluate_condition(last_row: pd.Series, condition: Dict[str, Any]) -> bool:
    field = condition.get("field")
    op_str = condition.get("op")
    
    if field not in last_row:
        raise RuntimeError(f"FIELD_NOT_FOUND: {field}")
    if op_str not in OPERATORS:
        raise RuntimeError(f"INVALID_OPERATOR: {op_str}")

    left_val = last_row[field]
    
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
        raise RuntimeError(f"INCOMPLETE_CONDITION_SPEC: {field} requires 'value' or 'ref'")

    return op_func(left_val, right_val)

# [4] 시그널 생성 엔진 (V31.19: Direct ID Injection)
def generate_signals(
    data_bundle: Dict[str, Dict[str, Any]], 
    strat_path: str, 
    strategy_id: str, # 🔥 [V31.19] 진짜 ID를 직접 수신
    state: Dict[str, Any], 
    system_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    [V31.19 시그널 생성 엔진]
    - 'strategy_id'를 인자로 받아 생성 시점부터 바인딩 (PENDING 제거)
    - 데이터 계약 및 판단/실행 분리 유지
    """
    signals = []
    
    entry_cfg = load_strategy_entry_rules(strat_path)
    if not entry_cfg:
        return []

    conditions = entry_cfg.get("conditions", [])

    for symbol, bundle in data_bundle.items():
        current = bundle["current"]
        history = bundle["history"]

        if history.empty:
            continue
            
        if "asset_type" not in current:
             raise RuntimeError(f"DATA_CONTRACT_VIOLATION: current asset_type missing for {symbol}")

        last_row = history.iloc[-1]
        is_qualified = True

        try:
            for cond in conditions:
                if not evaluate_condition(last_row, cond):
                    is_qualified = False
                    break
        
        except RuntimeError as re:
            print(f"[INTEGRITY_SIGNAL_REJECTED] {symbol} | Path: {strat_path} | Reason: {str(re)}")
            is_qualified = False
            continue 

        if is_qualified:
            exec_price = current.get("price")
            if pd.isna(exec_price) or exec_price <= 0:
                print(f"[EXECUTION_REJECTED] {symbol} | Invalid Price: {exec_price}")
                continue

            # 🔥 [V31.19] 'PENDING'을 제거하고 인자로 받은 진짜 strategy_id 사용
            signals.append({
                "symbol": symbol,
                "side": "BUY",
                "price": float(exec_price),
                "asset_type": str(current["asset_type"]),
                "strategy_id": strategy_id, # SSOT(Single Source of Truth) 강화
                "risk_per_trade": entry_cfg.get("risk_per_trade"),
                "stop_distance": entry_cfg.get("stop_distance")
            })
                
    return signals