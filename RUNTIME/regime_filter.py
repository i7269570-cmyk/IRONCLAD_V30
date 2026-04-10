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

def evaluate_market_regime(market_data: List[Dict[str, Any]], strategy_spec: Dict[str, Any]) -> Dict[str, str]:
    """
    기능: 
    1. global_filter(과반수 검증)를 통해 시장 진입 가능 여부를 1차 판단한다.
    2. 통과 시 evaluation_order에 따라 상세 Regime(TREND/RANGE)을 판정한다.
    """
    if not market_data:
        logger.warning("REGIME_FILTER: NO_MARKET_DATA -> FALLBACK TO NO_TRADE")
        return {"regime": "NO_TRADE"}

    try:
        regime_cfg = strategy_spec["regime"]
        
        # [STEP 1] Global Filter (Majority Evaluation) - regime_rules 통합 로직
        g_filter = regime_cfg.get("global_filter")
        if g_filter:
            metric = g_filter["metric"]
            threshold = g_filter["threshold"]
            
            # [수정] 기본값(-999) 자동 삽입 제거 및 명시적 필드 검증 (SAFE_HALT)
            pass_count = 0
            for d in market_data:
                if metric not in d:
                    raise RuntimeError(f"GLOBAL_FILTER_FIELD_MISSING: {metric}")
                
                value = d[metric]
                if value >= threshold:
                    pass_count += 1
            
            # 과반수 미달 시 진입 차단 (Blocker)
            if pass_count < (len(market_data) / 2):
                logger.info(f"REGIME: BLOCKED (Global Majority Fail: {pass_count}/{len(market_data)})")
                return {"regime": "NO_TRADE"}

        # [STEP 2] 상세 Regime 판정 (Dynamic Parser)
        latest_data = market_data[-1]
        eval_order = regime_cfg["evaluation_order"]

        for state in eval_order:
            # NO_TRADE는 fallback 처리
            if state == "NO_TRADE":
                logger.info("REGIME: NO_TRADE (FALLBACK)")
                return {"regime": "NO_TRADE"}

            state_conditions = regime_cfg["conditions"].get(state, {}).get("all", [])
            
            # 모든 조건을 만족하면 해당 상태 반환
            if _evaluate_condition_set(latest_data, state_conditions):
                logger.info(f"REGIME: {state}")
                return {"regime": state}

        return {"regime": "NO_TRADE"}

    except Exception as e:
        logger.error(f"REGIME_FILTER_CRITICAL_FAILURE: {str(e)}")
        raise RuntimeError(f"REGIME_SSOT_INTEGRITY_FAIL: {str(e)}")

def _evaluate_condition_set(data: Dict[str, Any], conditions: List[Dict[str, Any]]) -> bool:
    """조건 리스트(all)를 순회하며 전체 일치 여부를 판별한다."""
    if not conditions:
        return False

    for cond in conditions:
        if not _parse_and_compare(data, cond):
            return False
    return True

def _parse_and_compare(data: Dict[str, Any], cond: Dict[str, Any]) -> bool:
    """단일 YAML 조건 필드를 파싱하고 연산을 수행한다. (SAFE_HALT 유지)"""
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
            
            # multiplier 필수 (자동 보정 금지/하드코딩 제거)
            if "multiplier" not in cond:
                 raise RuntimeError(f"MULTIPLIER_REQUIRED_FOR_REF: {field}")
            
            right_val = data[ref_field] * float(cond["multiplier"])
        else:
            raise RuntimeError(f"YAML_STRUCTURE_ERROR: Missing 'value' or 'ref' in {field}")

        return op_func(left_val, right_val)

    except KeyError as e:
        raise RuntimeError(f"YAML_KEY_ERROR: {str(e)} in condition {cond}")