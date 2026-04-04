# ============================================================
# IRONCLAD_V31.18 - Strategic Exit Engine (Strict ID Filtering)
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
    """전략 경로의 exit_rules.yaml 로드"""
    if not os.path.exists(strategy_path):
        return {}

    rules_file = os.path.join(strategy_path, "exit_rules.yaml")
    if os.path.exists(rules_file):
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                rules_data = yaml.safe_load(f)
                if rules_data and "exit" in rules_data:
                    return rules_data["exit"]
        except Exception as e:
            print(f"[ERROR] Failed to load {rules_file}: {e}")
    return {}

def evaluate_exit_condition(history: pd.DataFrame, last_row: pd.Series, condition: Dict[str, Any]) -> bool:
    """YAML 정의 기반 청산 조건 해석기"""
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
    strat_path: str,
    current_strategy_id: str  # 🔥 [추가] 현재 엔진이 처리 중인 전략 ID
) -> List[Dict[str, Any]]:
    """
    [V31.18 청산 엔진]
    핵심: 포지션의 strategy_id와 현재 엔진의 strategy_id가 일치할 때만 청산 판단.
    """
    exit_signals = []
    rules = load_strategy_exit_rules(strat_path)
    if not rules:
        return []
    
    current_positions = state.get("positions", {})
    if not current_positions:
        return []

    for symbol, bundle in data_bundle.items():
        if symbol not in current_positions:
            continue

        pos_info = current_positions[symbol]
        
        # 🔥 [핵심 필터링] 자기 전략 포지션이 아니면 스킵 (크로스 청산 방지)
        pos_strategy_id = pos_info.get("strategy_id")
        if pos_strategy_id != current_strategy_id:
            continue

        # [데이터 계약 검증]
        if "volume" not in pos_info:
            raise RuntimeError(f"POSITION_VOLUME_MISSING: {symbol}")
        
        current_volume = pos_info["volume"]
        current = bundle["current"]
        history = bundle["history"]
        last_row = history.iloc[-1]

        # 조건 해석
        is_exit_qualified = False
        for cond in rules.get("conditions", []):
            if evaluate_exit_condition(history, last_row, cond):
                is_exit_qualified = True
                break
        
        if is_exit_qualified:
            exit_signals.append({
                "symbol": symbol,
                "action": "SELL",
                "side": "SELL",
                "price": float(current["price"]),
                "asset_type": current["asset_type"],
                "strategy_id": current_strategy_id,
                "volume": current_volume
            })

    return exit_signals