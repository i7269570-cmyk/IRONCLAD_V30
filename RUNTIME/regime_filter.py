# RUNTIME/regime_filter.py
import logging
import operator
from typing import List, Dict, Any

logger = logging.getLogger("IRONCLAD_RUNTIME.REGIME_FILTER")

OPERATORS = {
    "<": operator.lt, "<=": operator.le, ">": operator.gt,
    ">=": operator.ge, "==": operator.eq
}

def evaluate_market_regime(market_data: List[Dict[str, Any]], strategy_spec: Dict[str, Any]) -> str:
    if not market_data:
        logger.warning("REGIME_FILTER: NO_MARKET_DATA -> NO_TRADE")
        return "NO_TRADE"

    try:
        regime_cfg = strategy_spec.get("regime")
        if not regime_cfg:
            logger.info("REGIME_FILTER: regime 섹션 없음 -> TREND PASS_THROUGH")
            return "TREND"

        g_filter = regime_cfg.get("global_filter")
        if g_filter:
            metric = g_filter["metric"]
            threshold = g_filter["threshold"]
            pass_count = 0
            for d in market_data:
                if metric not in d:
                    raise RuntimeError(f"GLOBAL_FILTER_FIELD_MISSING: {metric}")
                if d[metric] >= threshold:
                    pass_count += 1
            if pass_count < (len(market_data) / 2):
                logger.info(f"REGIME: BLOCKED (Global Majority Fail: {pass_count}/{len(market_data)})")
                return "NO_TRADE"

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


def apply_market_direction_filter(base_regime: str, data_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    STOCK: ma20 <= ma60 (RANGE) 일 때만 진입 허용
    CRYPTO: index 종목 없음 → base_regime 그대로 통과
    검증 결과: RANGE PF 2.814 / TREND PF 0.7
    """
    index_symbol = "069500"

    if index_symbol not in data_bundle:
        # CRYPTO → base_regime 그대로 통과
        if base_regime in ("TREND", "RANGE"):
            return {"final_regime": base_regime}
        return {"final_regime": "NO_TRADE"}

    index_data = data_bundle[index_symbol]

    ma20 = index_data.get("ma20")
    ma60 = index_data.get("ma60")
    close = index_data.get("close")

    if ma20 is None or close is None:
        raise RuntimeError(
            f"REGIME_FILTER_ERROR: index({index_symbol}) ma20 또는 close 누락"
        )

    # ma60 없으면 ma200 으로 대체
    if ma60 is None:
        ma60 = index_data.get("ma200")

    if ma60 is None:
        raise RuntimeError(
            f"REGIME_FILTER_ERROR: index({index_symbol}) ma60/ma200 누락"
        )

    # RANGE 구간 판단: ma20 <= ma60
    is_range = ma20 <= ma60

    if not is_range:
        logger.info(f"REGIME_FILTER: TREND 구간 감지 (ma20={ma20:.0f} > ma60={ma60:.0f}) -> NO_TRADE")
        return {"final_regime": "NO_TRADE"}

    if base_regime in ("TREND", "RANGE"):
        return {"final_regime": base_regime}

    return {"final_regime": "NO_TRADE"}
