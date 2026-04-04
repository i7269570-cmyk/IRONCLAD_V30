# ============================================================
# IRONCLAD_V31.15 - Fill Tracker (State Mutation Removal)
# ============================================================
import logging

# [Standard] Logging interface
logger = logging.getLogger("IRONCLAD_FILL_TRACKER")

def track_fills(order_results, state):
    """
    입력: order_results(list[dict]), state(dict)
    출력: list[dict] (정제된 체결 데이터 리스트)
    기능: 
    1. state["positions"] 직접 수정 로직을 전면 제거한다. (Reconciler 위임)
    2. 체결 상태(FILLED) 데이터를 정제하여 Reconciler가 처리 가능한 형식으로 반환한다.
    3. REJECTED / ERROR 상태 발생 시 즉시 RuntimeError를 발생시킨다.
    """

    # [Standard] Input validation
    if not isinstance(order_results, list):
        raise RuntimeError("FILL_TRACKER_INPUT_INVALID")

    if not isinstance(state, dict) or "positions" not in state:
        raise RuntimeError("STATE_POSITIONS_MISSING")

    # [V31.15] state["positions"] is for reference only; direct modification is prohibited.
    positions = state["positions"]
    fills = []

    # [Standard] Required field definition for data contract
    required_fields = [
        "status", "symbol", "side", "price", 
        "asset_type", "strategy_name", "volume"
    ]

    for o in order_results:
        # [Standard] Item type validation
        if not isinstance(o, dict):
            raise RuntimeError("FILL_TRACKER_ITEM_INVALID")

        # [Standard] Field presence validation
        for f in required_fields:
            if o.get(f) is None:
                raise RuntimeError(f"FILL_TRACKER_MISSING_FIELD: {f}")

        status = o.get("status")
        symbol = o.get("symbol")

        # [Rule] Critical status handling: Immediate Halt on failure
        if status in ["REJECTED", "ERROR"]:
            raise RuntimeError(f"ORDER_FAILED: {status} | {symbol}")

        # [V31.15] Data refinement for FILLED status
        if status == "FILLED":
            # [Rule] Integrity Check: Signal duplicate position to prevent data corruption
            if symbol in positions:
                raise RuntimeError(f"FILL_DUPLICATE_POSITION: {symbol}")

            # [V31.15] Generate finalized fill data without updating state.
            # This list will be passed to position_reconciler later.
            fills.append({
                "symbol": symbol,
                "side": o["side"],
                "price": o["price"],
                "asset_type": o["asset_type"],
                "strategy_name": o["strategy_name"],
                "volume": o["volume"],
                "entry_price": o["price"], # Initial entry price equals fill price
                "hold_bars": 0             # Reset hold counter for new position
            })
        
        else:
            logger.warning(f"NON_FILLED_STATUS: {status} | {symbol}")

    logger.info(f"FILL_TRACKER_SUCCESS: {len(fills)} signals generated.")

    # [Final State] Pure list of fill results returned for Reconciler.
    return fills