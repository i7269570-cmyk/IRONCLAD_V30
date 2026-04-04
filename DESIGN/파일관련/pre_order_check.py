import logging
from typing import List, Dict, Any

# =============================================================================
# IRONCLAD_V30.1_FINAL: PRE_ORDER_CHECK (Dual Guarding)
# =============================================================================
logger = logging.getLogger("IRONCLAD_RUNTIME.PRE_ORDER_CHECK")

def validate_before_order(
    signals: List[Dict[str, Any]],
    mode: str,
    current_positions: List[Dict[str, Any]],
    system_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """주문 직전 최종 게이트키퍼: 2차 중복 검사 및 독립적 모드 차단 수행"""
    
    # [1] 독립적 운영 모드 검증 (상위 분기 우회 대비)
    if mode != "TRADE":
        logger.warning(f"PRE_ORDER: Blocked. Independent mode check failed (Current: {mode})")
        return []

    if not signals:
        return []

    # [2] 현재 보유 심볼 리스트 추출 (2차 검사용)
    current_symbols = {pos.get("symbol") for pos in current_positions}
    
    passed_signals = []
    for signal in signals:
        symbol = signal.get("symbol")
        price = signal.get("price")
        volume = signal.get("volume")

        # [3] 2차 Symbol 중복 검증 (RISK 해결)
        if symbol in current_symbols:
            logger.warning(f"PRE_ORDER: {symbol} blocked by 2nd duplicate check.")
            continue

        # [4] 물리적 데이터 유효성 검사 (Price/Volume)
        if price and volume and price > 0 and volume > 0:
            passed_signals.append(signal)
            # 루프 내 중복 진입 방지 위해 추가
            current_symbols.add(symbol)
        else:
            logger.error(f"PRE_ORDER: Invalid data integrity for {symbol}")

    logger.info(f"PRE_ORDER: {len(passed_signals)}/{len(signals)} passed final gate.")
    return passed_signals