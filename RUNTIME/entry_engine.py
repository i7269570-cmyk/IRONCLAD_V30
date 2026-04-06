# ============================================================
# IRONCLAD_V31.22 - Strategic Entry Engine (Exception Propagation)
# ============================================================
import os
import yaml
import operator
from typing import List, Dict, Any
import pandas as pd
import logging

# [Standard] 로깅 인터페이스 설정
logger = logging.getLogger("IRONCLAD_RUNTIME.ENTRY_ENGINE")

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
        logger.error(f"STRATEGY_LOAD_FAILED: {rules_file} | {str(e)}")
    
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

# [4] 시그널 생성 엔진 (V31.22: Exception-Ready)
def generate_signals(
    data_bundle: Dict[str, Dict[str, Any]], 
    strat_path: str, 
    strategy_id: str, 
    state: Dict[str, Any], 
    system_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    [V31.22 시그널 생성 엔진]
    - 예외 발생 시 'continue' 대신 'raise'를 사용하여 상위 전파 (FAIL 해소)
    - 데이터 계약 및 SSOT 유지
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
            # 🔥 [V31.22 핵심 수정] 예외 흡수 제거
            # 결함(NaN 등) 발생 시 조용히 넘기지 않고 상위(run.py)로 즉시 전파
            logger.error(f"STRATEGY_INTEGRITY_FAIL: {symbol} | ID: {strategy_id} | Reason: {str(re)}")
            raise re

        if is_qualified:
            exec_price = current.get("price")
            if pd.isna(exec_price) or exec_price <= 0:
                logger.warning(f"EXECUTION_REJECTED: {symbol} | Invalid Price: {exec_price}")
                continue

            signals.append({
                "symbol": symbol,
                "side": "BUY",
                "price": float(exec_price),
                "asset_type": str(current["asset_type"]),
                "strategy_id": strategy_id, 
                "risk_per_trade": entry_cfg.get("risk_per_trade"),
                "stop_distance": entry_cfg.get("stop_distance")
            })
                
    return signals