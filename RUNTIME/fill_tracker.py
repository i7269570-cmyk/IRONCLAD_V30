# ============================================================
# IRONCLAD_V31.18 - Fill Tracker (Strategy ID Continuity)
# ============================================================
import logging

# [Standard] Logging interface
logger = logging.getLogger("IRONCLAD_FILL_TRACKER")

def track_fills(order_results, state):
    """
    입력: order_results(list[dict]), state(dict)
    출력: list[dict] (정제된 체결 데이터 리스트)
    기능: 
    1. [V31.18] strategy_name을 폐기하고 strategy_id를 필수 계약 필드로 추가한다.
    2. state 직접 수정 금지 원칙 고수 (Reconciler 위임).
    3. 체결 실패(REJECTED/ERROR) 발생 시 데이터 오염 방지를 위해 즉시 RuntimeError 발생.
    """

    # [Standard] Input validation
    if not isinstance(order_results, list):
        raise RuntimeError("FILL_TRACKER_INPUT_INVALID") #

    if not isinstance(state, dict) or "positions" not in state:
        raise RuntimeError("STATE_POSITIONS_MISSING") #

    positions = state["positions"]
    fills = []

    # [V31.18 핵심 수정] strategy_id를 필수 필드로 지정 (데이터 사슬 보존)
    required_fields = [
        "status", "symbol", "side", "price", 
        "asset_type", "strategy_id", "volume"  # 🔥 [V31.18] ID 사슬의 핵심 연결 고리
    ]

    for o in order_results:
        if not isinstance(o, dict):
            raise RuntimeError("FILL_TRACKER_ITEM_INVALID") #

        # [Standard] Field presence validation (ID 누락 시 즉시 중단)
        for f in required_fields:
            if o.get(f) is None:
                # [V31.18] strategy_id가 없는 결과는 파이프라인 전체를 중단시킴
                raise RuntimeError(f"FILL_TRACKER_MISSING_FIELD: {f} for {o.get('symbol')}")

        status = o.get("status")
        symbol = o.get("symbol")

        # [Rule] Critical status handling
        if status in ["REJECTED", "ERROR"]:
            raise RuntimeError(f"ORDER_FAILED: {status} | {symbol}") #

        # [V31.18] FILLED 상태 데이터 정제 및 ID 전달
        if status == "FILLED":
            if symbol in positions:
                raise RuntimeError(f"FILL_DUPLICATE_POSITION: {symbol}") #

            # [핵심] Reconciler로 전달할 데이터 생성 (ID 포함)
            fills.append({
                "symbol": symbol,
                "side": o["side"],
                "price": o["price"],
                "asset_type": o["asset_type"],
                "strategy_id": o["strategy_id"], # 🔥 ID 사슬 유지 (Key 필드)
                "volume": o["volume"],
                "entry_price": o["price"],
                "hold_bars": 0
            })
        
        else:
            logger.warning(f"NON_FILLED_STATUS: {status} | {symbol}") #

    logger.info(f"FILL_TRACKER_SUCCESS: {len(fills)} signals tracked with ID continuity.") #

    return fills