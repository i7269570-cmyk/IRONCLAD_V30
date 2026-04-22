# ============================================================
# IRONCLAD_V31.24 - Fill Tracker (Asset Group Integrity)
# ============================================================
import logging

logger = logging.getLogger("IRONCLAD_FILL_TRACKER")

def track_fills(order_results, state):
    """
    입력: order_results(list[dict]), state(dict)
    출력: list[dict]

    규칙:
    - FILLED만 처리
    - REJECTED / ERROR → 즉시 중단 (SAFE_HALT)
    - asset_group 필드 필수 포함
    - state 직접 수정 금지 (reconciler 위임)
    """

    if not isinstance(order_results, list):
        raise RuntimeError("FILL_TRACKER_INPUT_INVALID")

    if not isinstance(state, dict) or "positions" not in state:
        raise RuntimeError("STATE_POSITIONS_MISSING")

    positions = state["positions"]
    fills = []

    required_fields = [
        "status", "symbol", "side", "price",
        "asset_type", "asset_group", "strategy_id", "volume"
    ]

    for o in order_results:
        if not isinstance(o, dict):
            raise RuntimeError("ORDER_ITEM_INVALID")

        for f in required_fields:
            if f not in o or o[f] is None:
                raise RuntimeError(f"FILL_TRACKER_MISSING_FIELD: {f} | {o.get('symbol', 'UNKNOWN')}")

        status = o["status"]
        symbol = o["symbol"]

        if status in ["REJECTED", "ERROR"]:
            raise RuntimeError(f"ORDER_FAILED: {status} | {symbol}")

        if status == "FILLED":
            if symbol in positions:
                raise RuntimeError(f"FILL_DUPLICATE_POSITION: {symbol}")

            fills.append({
                "symbol": symbol,
                "side": o["side"],
                "price": o["price"],
                "asset_type": o["asset_type"],
                "asset_group": o["asset_group"],
                "strategy_id": o["strategy_id"],
                "volume": o["volume"],
                "entry_price": o["price"],
                "hold_bars": 0
            })
        else:
            logger.warning(f"IGNORED_STATUS: {status} | {symbol}")

    return fills
