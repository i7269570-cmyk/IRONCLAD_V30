# ============================================================
# IRONCLAD_V31.3 - Strategic Exit Engine (Position Contract Sync)
# ============================================================
import os
import yaml
import operator
from typing import List, Dict, Any
import pandas as pd

# [SSOT] 지원 연산자 매핑
OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq
}

def load_strategy_exit_rules(strategy_path: str) -> Dict[str, Any]:
    """모든 전략 폴더에서 exit_rules.yaml을 수집하여 반환함"""
    all_rules = {}
    if not os.path.exists(strategy_path):
        raise RuntimeError(f"STRATEGY_ROOT_MISSING: {strategy_path}")

    for folder in os.listdir(strategy_path):
        folder_path = os.path.join(strategy_path, folder)
        if not os.path.isdir(folder_path):
            continue
        
        rules_file = os.path.join(folder_path, "exit_rules.yaml")
        if os.path.exists(rules_file):
            try:
                with open(rules_file, "r", encoding="utf-8") as f:
                    rules_data = yaml.safe_load(f)
                    if rules_data and "exit" in rules_data:
                        all_rules[folder] = rules_data["exit"]
            except Exception as e:
                print(f"[ERROR] Failed to load {rules_file}: {e}")
    
    return all_rules

def evaluate_exit_condition(history: pd.DataFrame, last_row: pd.Series, condition: Dict[str, Any]) -> bool:
    """YAML 정의 기반 청산 조건 해석기 (판단 전용: history 기반)"""
    field = condition.get("field")
    op_str = condition.get("op")

    if field not in history.columns:
        raise RuntimeError(f"INVALID_EXIT_FIELD: {field}")
    if op_str not in OPERATORS:
        raise RuntimeError(f"UNSUPPORTED_EXIT_OPERATOR: {op_str}")

    left = last_row[field]
    op_func = OPERATORS[op_str]

    if "ref" in condition:
        ref_field = condition["ref"]
        right = last_row[ref_field]
        if "multiplier" in condition:
            right = right * float(condition["multiplier"])
    else:
        right = float(condition["value"])

    return op_func(left, right)

def process_exits(
    data_bundle: Dict[str, Dict[str, Any]], 
    state: Dict[str, Any],
    strategy_path: str
) -> List[Dict[str, Any]]:
    """
    [V31.3 청산 엔진]
    목표: state/position 계약 필드 일치 (volume SSOT)
    1. volume: pos_info["volume"] 필드 사용 (quantity 폐기)
    2. 검증: "volume" 필드 누락 시 POSITION_VOLUME_MISSING 발생
    """
    exit_signals = []
    strategy_rules = load_strategy_exit_rules(strategy_path)
    
    current_positions = state.get("positions", {})
    if not current_positions:
        return []

    for symbol, bundle in data_bundle.items():
        if symbol not in current_positions:
            continue

        pos_info = current_positions[symbol]
        
        # [수정] position 계약 필드 검증 및 추출 (quantity -> volume)
        if "volume" not in pos_info:
            raise RuntimeError(f"POSITION_VOLUME_MISSING: {symbol}")
        
        current_volume = pos_info["volume"]
        
        current = bundle["current"]
        history = bundle["history"]
        last_row = history.iloc[-1]
        
        strategy_name = pos_info.get("strategy_name")
        rules = strategy_rules.get(strategy_name)
        if not rules: 
            continue

        is_exit_qualified = False
        for cond in rules.get("conditions", []):
            if evaluate_exit_condition(history, last_row, cond):
                is_exit_qualified = True
                break
        
        if is_exit_qualified:
            # [규격] reconciler required_fields 충족
            exit_signals.append({
                "symbol": symbol,
                "action": "SELL",
                "side": "SELL",
                "price": float(current["price"]),
                "asset_type": current["asset_type"],
                "strategy_name": strategy_name,
                "volume": current_volume
            })

    return exit_signals