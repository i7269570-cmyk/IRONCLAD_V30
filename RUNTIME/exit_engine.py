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

def load_strategy_exit_rules(strat_path: str) -> Dict[str, Any]:
    """
    [V31.18] 절대 경로를 기반으로 해당 전략의 exit_rules.yaml 로드
    strat_path: run.py에서 보정된 절대 경로 (예: /root/STRATEGY/stock_A)
    """
    # 원칙 10: 디렉토리 여부 확인
    if not os.path.isdir(strat_path):
        return {}

    rules_file = os.path.join(strat_path, "exit_rules.yaml")
    
    if os.path.exists(rules_file):
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                rules_data = yaml.safe_load(f)
                # 원칙 1: exit 섹션 필수 존재 확인
                if rules_data and "exit" in rules_data:
                    return rules_data["exit"]
        except Exception as e:
            # 원칙 9: 설정 오류 시 무음 실패 방지 (Logging)
            print(f"[ERROR] EXIT_CONFIG_LOAD_FAILED: {rules_file} -> {e}")
    return {}

def evaluate_exit_condition(history: pd.DataFrame, last_row: pd.Series, condition: Dict[str, Any]) -> bool:
    """YAML 정의 기반 청산 조건 해석기 (원칙 1, 2, 6 준수)"""
    field = condition.get("field")
    op_str = condition.get("op")

    # 원칙 9: 필드 및 연산자 누락 시 즉시 중단
    if field not in history.columns:
        raise RuntimeError(f"INVALID_EXIT_FIELD: {field} not in history")
    if op_str not in OPERATORS:
        raise RuntimeError(f"UNSUPPORTED_EXIT_OPERATOR: {op_str}")

    left = last_row[field]
    op_func = OPERATORS[op_str]

    # 원칙 1: ref(참조필드) 또는 value(상수) 처리
    if "ref" in condition:
        ref_field = condition["ref"]
        if ref_field not in history.columns:
            raise RuntimeError(f"INVALID_EXIT_REF_FIELD: {ref_field}")
        
        right = last_row[ref_field]
        if "multiplier" in condition:
            right = right * float(condition["multiplier"])
    else:
        if "value" not in condition:
            raise RuntimeError(f"MISSING_EXIT_VALUE: Condition for {field} needs ref or value")
        right = float(condition["value"])

    return op_func(left, right)

def process_exits(
    data_bundle: Dict[str, Dict[str, Any]], 
    state: Dict[str, Any],
    strat_path: str,
    current_strategy_id: str
) -> List[Dict[str, Any]]:
    """
    [V31.18 청산 엔진]
    핵심: 포지션의 strategy_id와 현재 엔진의 strategy_id가 일치할 때만 청산 판단.
    """
    exit_signals = []
    
    # run.py로부터 받은 절대 경로를 통해 규칙 로드
    rules = load_strategy_exit_rules(strat_path)
    if not rules:
        return []
    
    current_positions = state.get("positions", {})
    if not current_positions:
        return []

    for symbol, bundle in data_bundle.items():
        # 해당 심볼의 포지션이 없으면 스킵
        if symbol not in current_positions:
            continue

        pos_info = current_positions[symbol]
        
        # 🔥 [핵심 필터링] 원칙: 자기 전략 ID가 부여된 포지션만 건드린다 (Cross-Exit 방지)
        pos_strategy_id = pos_info.get("strategy_id")
        if pos_strategy_id != current_strategy_id:
            continue

        # [데이터 계약 검증] (원칙 9)
        if "volume" not in pos_info or pos_info["volume"] <= 0:
            # 포지션 데이터 무결성 오류 처리
            continue
        
        current_volume = pos_info["volume"]
        current = bundle["current"]
        history = bundle["history"]
        
        if history.empty:
            continue
            
        last_row = history.iloc[-1]

        # ------------------------------------------------------------
        # YAML 조건 해석 루프
        # ------------------------------------------------------------
        is_exit_qualified = False
        conditions = rules.get("conditions", [])
        
        # conditions가 리스트인 경우, 하나라도 만족하면 청산 (OR logic)
        for cond in conditions:
            if evaluate_exit_condition(history, last_row, cond):
                is_exit_qualified = True
                break
        
        if is_exit_qualified:
            exit_signals.append({
                "symbol": symbol,
                "action": "SELL",
                "side": "SELL",
                "price": float(current["price"]),
                "asset_type": current.get("asset_type", "UNKNOWN"),
                "strategy_id": current_strategy_id, # SSOT 유지
                "volume": current_volume
            })

    return exit_signals