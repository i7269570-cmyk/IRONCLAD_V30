# ============================================================
# IRONCLAD_V31.22 - Strategic Exit Engine (Data Integrity Patch)
# ============================================================
import os
import yaml
import operator
from typing import List, Dict, Any
import pandas as pd
import logging

# [Standard] 로깅 인터페이스 설정
logger = logging.getLogger("IRONCLAD_RUNTIME.EXIT_ENGINE")

# [SSOT] 지원 연산자 매핑
OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq
}

def load_strategy_exit_rules(strat_path: str) -> Dict[str, Any]:
    """절대 경로 기반 해당 전략의 exit_rules.yaml 로드"""
    if not os.path.isdir(strat_path):
        return {}

    rules_file = os.path.join(strat_path, "exit_rules.yaml")
    
    if os.path.exists(rules_file):
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                rules_data = yaml.safe_load(f)
                if rules_data and "exit" in rules_data:
                    return rules_data["exit"]
        except Exception as e:
            logger.error(f"EXIT_CONFIG_LOAD_FAILED: {rules_file} -> {e}")
    return {}

def evaluate_exit_condition(history: pd.DataFrame, last_row: pd.Series, condition: Dict[str, Any]) -> bool:
    """YAML 정의 기반 청산 조건 해석기 (원칙 1, 2, 6, 9 준수)"""
    field = condition.get("field")
    op_str = condition.get("op")

    if field not in history.columns:
        raise RuntimeError(f"INVALID_EXIT_FIELD: {field} not in history")
    if op_str not in OPERATORS:
        raise RuntimeError(f"UNSUPPORTED_EXIT_OPERATOR: {op_str}")

    # [V31.22 핵심 수정] 데이터 무결성 검사 (NaN 및 None 차단)
    left = last_row[field]

    # 원칙 9: 결함 은폐 금지. 판단 데이터가 유효하지 않으면 즉시 중단
    if pd.isna(left):
        raise RuntimeError(f"EXIT_DATA_INVALID: field '{field}' is NaN or None")

    op_func = OPERATORS[op_str]

    if "ref" in condition:
        ref_field = condition["ref"]
        if ref_field not in history.columns:
            raise RuntimeError(f"INVALID_EXIT_REF_FIELD: {ref_field}")
        
        right = last_row[ref_field]
        
        # 참조 데이터(ref) 무결성 검사
        if pd.isna(right):
            raise RuntimeError(f"EXIT_REF_DATA_INVALID: ref field '{ref_field}' is NaN")
            
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
    [V31.22 청산 엔진]
    - 'strategy_id' 필터링을 통해 타 전략 포지션 간섭 방지
    - 예외 발생 시 상위 전파를 통한 SAFE_HALT 유도
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
        
        # [핵심 필터링] 자기 전략 ID가 부여된 포지션만 처리 (Cross-Exit 방지)
        if pos_info.get("strategy_id") != current_strategy_id:
            continue

        current_volume = pos_info.get("volume", 0)
        if current_volume <= 0:
            continue
        
        current = bundle["current"]
        history = bundle["history"]
        
        if history.empty:
            continue
            
        last_row = history.iloc[-1]

        # ------------------------------------------------------------
        # YAML 조건 해석 루프 (예외 전파 허용)
        # ------------------------------------------------------------
        is_exit_qualified = False
        conditions = rules.get("conditions", [])
        
        try:
            for cond in conditions:
                if evaluate_exit_condition(history, last_row, cond):
                    is_exit_qualified = True
                    break
        except RuntimeError as re:
            # 원칙 9: 청산 판단 중 데이터 오류 발생 시 조용히 넘기지 않고 즉시 보고
            logger.error(f"EXIT_INTEGRITY_FAIL: {symbol} | ID: {current_strategy_id} | {str(re)}")
            raise re
        
        if is_exit_qualified:
            exec_price = current.get("price")
            if pd.isna(exec_price) or exec_price <= 0:
                logger.warning(f"EXIT_EXECUTION_REJECTED: {symbol} | Invalid Price: {exec_price}")
                continue

            exit_signals.append({
                "symbol": symbol,
                "action": "SELL",
                "side": "SELL",
                "price": float(exec_price),
                "asset_type": str(current.get("asset_type", "UNKNOWN")),
                "strategy_id": current_strategy_id,
                "volume": current_volume
            })

    return exit_signals