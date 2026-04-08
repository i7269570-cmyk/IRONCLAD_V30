# ============================================================
# IRONCLAD_V31.18 - Fill Tracker (PRODUCTION READY)
# ============================================================
import logging

logger = logging.getLogger("IRONCLAD_FILL_TRACKER")


def track_fills(order_results, state):
    """
    입력: order_results(list[dict]), state(dict)
    출력: list[dict]

    규칙:
    - FILLED만 처리 (실전 기준)
    - REJECTED / ERROR → 즉시 중단
    - 나머지 상태 → 무시 (로그만)
    - state 직접 수정 금지 (reconciler 위임)
    """

    # ---------- Input Validation ----------
    if not isinstance(order_results, list):
        raise RuntimeError("FILL_TRACKER_INPUT_INVALID")

    if not isinstance(state, dict) or "positions" not in state:
        raise RuntimeError("STATE_POSITIONS_MISSING")

    positions = state["positions"]
    fills = []

    required_fields = [
        "status", "symbol", "side", "price",
        "asset_type", "strategy_id", "volume"
    ]

    # ---------- Process ----------
    for o in order_results:
        if not isinstance(o, dict):
            raise RuntimeError("FILL_TRACKER_ITEM_INVALID")

        # 필수 필드 검증
        for f in required_fields:
            if o.get(f) is None:
                raise RuntimeError(
                    f"FILL_TRACKER_MISSING_FIELD: {f} | {o.get('symbol')}"
                )

        status = o["status"]
        symbol = o["symbol"]

        # ---------- Critical Fail ----------
        if status in ["REJECTED", "ERROR"]:
            raise RuntimeError(f"ORDER_FAILED: {status} | {symbol}")

        # ---------- Only FILLED ----------
        if status == "FILLED":

            # 중복 포지션 방지
            if symbol in positions:
                raise RuntimeError(f"FILL_DUPLICATE_POSITION: {symbol}")

            fills.append({
                "symbol": symbol,
                "side": o["side"],
                "price": o["price"],
                "asset_type": o["asset_type"],
                "strategy_id": o["strategy_id"],
                "volume": o["volume"],
                "entry_price": o["price"],
                "hold_bars": 0
            })

        # ---------- Ignore Others ----------
        else:
            logger.warning(f"IGNORED_STATUS: {status} | {symbol}")

    logger.info(
        f"FILL_TRACKER_SUCCESS: {len(fills)} fills (FILLED only)."
    )

    return fills