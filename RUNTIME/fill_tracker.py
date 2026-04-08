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
    - FILLED만 처리 (실전 기준)
    - REJECTED / ERROR → 즉시 중단 (SAFE_HALT)
    - asset_group 필드 필수 포함 (No Default)
    - state 직접 수정 금지 (reconciler 위임)
    """

    # ---------- Input Validation ----------
    if not isinstance(order_results, list):
        raise RuntimeError("FILL_TRACKER_INPUT_INVALID")

    if not isinstance(state, dict) or "positions" not in state:
        raise RuntimeError("STATE_POSITIONS_MISSING")

    positions = state["positions"]
    fills = []

    # 🔴 [V31.24 수정] 필수 필드 목록에 asset_group 추가
    required_fields = [
        "status", "symbol", "side", "price",
        "asset_type", "asset_group", "strategy_id", "volume"
    ]

    # ---------- Process ----------
    for o in order_results:
        if not isinstance(o, dict):
            raise RuntimeError("FILL_TRACKER_ITEM_INVALID")

        # 필수 필드 검증 (.get 기본값 금지)
        for f in required_fields:
            # 🔴 [V31.24 수정] .get(f) is None 체크를 통해 키 누락 시 즉시 예외 발생
            if f not in o or o[f] is None:
                raise RuntimeError(
                    f"FILL_TRACKER_MISSING_FIELD: {f} | {o.get('symbol', 'UNKNOWN')}"
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

            # 🔴 [V31.24 수정] 반환 fill 객체에 asset_group 포함
            fills.append({
                "symbol": symbol,
                "side": o["side"],
                "price": o["price"],
                "asset_type": o["asset_type"],
                "asset_group": o["asset_group"], # 계약 일치를 위한 필드 추가
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