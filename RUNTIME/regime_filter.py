# RUNTIME/regime_filter.py
import logging
import operator
from typing import List, Dict, Any

# =============================================================================
# IRONCLAD_V30.7_FINAL: REGIME_FILTER (DYNAMIC PARSER + GLOBAL FILTER)
# =============================================================================

logger = logging.getLogger("IRONCLAD_RUNTIME.REGIME_FILTER")

# 연산자 매핑 (SSOT)
OPERATORS = {
    "<": operator.lt, "<=": operator.le, ">": operator.gt,
    ">=": operator.ge, "==": operator.eq
}

def evaluate_market_regime(market_data: List[Dict[str, Any]], strategy_spec: Dict[str, Any]) -> str:
    """
    기능: 
    1. global_filter(과반수 검증)를 통해 시장 진입 가능 여부를 1차 판단한다.
    2. 통과 시 evaluation_order에 따라 상세 Regime(TREND/RANGE)을 판정한다.
    반환: Regime 명칭 (문자열만 반환)
    """
    if not market_data:
        logger.warning("REGIME_FILTER: NO_MARKET_DATA -> FALLBACK TO NO_TRADE")
        return "NO_TRADE"

    try:
        regime_cfg = strategy_spec["regime"]
        
        # [STEP 1] Global Filter (Majority Evaluation)
        g_filter = regime_cfg.get("global_filter")
        if g_filter:
            metric = g_filter["metric"]
            threshold = g_filter["threshold"]
            
            pass_count = 0
            for d in market_data:
                if metric not in d:
                    raise RuntimeError(f"GLOBAL_FILTER_FIELD_MISSING: {metric}")
                
                value = d[metric]
                if value >= threshold:
                    pass_count += 1
            
            if pass_count < (len(market_data) / 2):
                logger.info(f"REGIME: BLOCKED (Global Majority Fail: {pass_count}/{len(market_data)})")
                return "NO_TRADE"

        # [STEP 2] 상세 Regime 판정
        latest_data = market_data[-1]
        eval_order = regime_cfg["evaluation_order"]

        for state in eval_order:
            if state == "NO_TRADE":
                logger.info("REGIME: NO_TRADE (FALLBACK)")
                return "NO_TRADE"

            state_conditions = regime_cfg["conditions"].get(state, {}).get("all", [])
            
            if _evaluate_condition_set(latest_data, state_conditions):
                logger.info(f"REGIME: {state}")
                return state

        return "NO_TRADE"

    except Exception as e:
        logger.error(f"REGIME_FILTER_CRITICAL_FAILURE: {str(e)}")
        raise RuntimeError(f"REGIME_SSOT_INTEGRITY_FAIL: {str(e)}")

def _evaluate_condition_set(data: Dict[str, Any], conditions: List[Dict[str, Any]]) -> bool:
    if not conditions:
        return False

    for cond in conditions:
        if not _parse_and_compare(data, cond):
            return False
    return True

def _parse_and_compare(data: Dict[str, Any], cond: Dict[str, Any]) -> bool:
    try:
        field = cond["field"]
        op_str = cond["op"]
        
        if field not in data:
            raise RuntimeError(f"DATA_FIELD_MISSING: {field}")
        
        left_val = data[field]
        if left_val is None:
            return False

        if op_str not in OPERATORS:
            raise RuntimeError(f"INVALID_YAML_OPERATOR: {op_str}")
        op_func = OPERATORS[op_str]

        if "value" in cond:
            right_val = float(cond["value"])
        elif "ref" in cond:
            ref_field = cond["ref"]
            if ref_field not in data:
                raise RuntimeError(f"REF_FIELD_MISSING: {ref_field}")
            
            if "multiplier" not in cond:
                 raise RuntimeError(f"MULTIPLIER_REQUIRED_FOR_REF: {field}")
            
            right_val = data[ref_field] * float(cond["multiplier"])
        else:
            raise RuntimeError(f"YAML_STRUCTURE_ERROR: Missing 'value' or 'ref' in {field}")

        return op_func(left_val, right_val)

    except KeyError as e:
        raise RuntimeError(f"YAML_KEY_ERROR: {str(e)} in condition {cond}")