# ============================================================
# IRONCLAD_V31.14 - Pre-Order Integrity (Clean Role Separation)
# ============================================================
import logging

# [Standard] Logging interface
logger = logging.getLogger("IRONCLAD_RUNTIME.PRE_ORDER_CHECK")

def validate_before_order(signals, mode, positions, system_config):
    """
    입력: signals(list[dict]), mode(str), positions(dict), system_config(dict)
    출력: list[dict]
    기능: 
    1. risk_gate와 중복되는 리스크/한도 로직(max_positions 등)을 완전히 제거한다.
    2. 주문 실행 직전의 필수 필드 무결성 및 중복 주문 여부만 검증한다.
    """

    # [Rule] NO_ENTRY mode: Immediate return of empty list
    if mode == "NO_ENTRY":
        return []

    # [Standard] Input structure validation (RuntimeError on structural failure)
    if not isinstance(signals, list):
        raise RuntimeError(f"INPUT_STRUCTURE_ERROR: signals must be list, got {type(signals)}")

    # [Standard] Required field verification for execution contract
    required_fields = [
        "symbol", "side", "price", "asset_type", 
        "strategy_name", "risk_per_trade", "stop_distance", "volume"
    ]

    for sig in signals:
        if not isinstance(sig, dict):
            raise RuntimeError("SIGNAL_STRUCTURE_ERROR: signal item must be dict")
        for f in required_fields:
            if sig.get(f) is None:
                raise RuntimeError(f"REQUIRED_FIELD_MISSING: {f}")

    # [V31.14] Role Separation: Logic for max_positions/exposure removed (Handled by risk_gate)
    validated = []
    
    for sig in signals:
        symbol = sig["symbol"]

        # [Rule] Integrity Check: Duplicate position verification
        # Prevents redundant orders for assets already in the portfolio
        if symbol in positions:
            logger.warning(f"SKIP_DUPLICATE_POSITION: {symbol}")
            continue

        # [Final State] Pass only signals that meet pure execution integrity
        validated.append(sig)

    return validated