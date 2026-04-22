# ============================================================
# IRONCLAD_V31.24 - Order Manager (Asset Group Integrity)
# ============================================================
import logging
import time

logger = logging.getLogger("IRONCLAD_RUNTIME.ORDER_MANAGER")

def execute_orders(signals):
    """
    입력: list[dict] (Risk Manager에 의해 승인된 신호 리스트)
    출력: dict {"results": list[dict]} (체결 결과 데이터)
    """

    if not isinstance(signals, list):
        raise RuntimeError("ORDER_MANAGER_INPUT_TYPE_ERROR: signals must be list")

    required_fields = [
        "symbol", "side", "price", "asset_type", "asset_group",
        "strategy_id", "risk_per_trade", "stop_distance", "volume", "approved"
    ]

    for sig in signals:
        if not isinstance(sig, dict):
            raise RuntimeError("ORDER_MANAGER_INVALID_SIGNAL")

        for f in required_fields:
            if f not in sig or sig[f] is None:
                raise RuntimeError(f"ORDER_MANAGER_MISSING_FIELD: {f} for {sig.get('symbol', 'UNKNOWN')}")

        if sig["approved"] is not True:
            raise RuntimeError(f"ORDER_BLOCKED_BY_RISK_GATE: {sig['symbol']} (Strategy: {sig['strategy_id']})")

    results = []

    for sig in signals:
        try:
            logger.info(f"ORDER_EXECUTING: {sig['symbol']} | ID: {sig['strategy_id']} | Vol: {sig['volume']}")

            execution_item = {
                "status": "FILLED",
                "order_id": f"ORD_{int(time.time()*1000)}",
                "created_at": time.time(),
                "symbol": sig["symbol"],
                "side": sig["side"],
                "price": sig["price"],
                "asset_type": sig["asset_type"],
                "asset_group": sig["asset_group"],
                "strategy_id": sig["strategy_id"],
                "volume": sig["volume"]
            }
            results.append(execution_item)

        except Exception as e:
            raise RuntimeError(f"ORDER_EXECUTION_FAILED: {sig['symbol']} - {str(e)}")

    if not isinstance(results, list):
        raise RuntimeError("ORDER_MANAGER_RESULTS_INVALID")

    return {"results": results}
