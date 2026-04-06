# ============================================================
# IRONCLAD_V31.19 - Order Manager (Risk-Gate Interlock)
# ============================================================
import logging

# [Standard] 로깅 인터페이스 정의
logger = logging.getLogger("IRONCLAD_RUNTIME.ORDER_MANAGER")

def execute_orders(signals):
    """
    입력: list[dict] (Risk Manager에 의해 승인된 신호 리스트)
    출력: dict {"results": list[dict]} (체결 결과 데이터)
    기능: 
    1. [V31.19] 'approved' 필드 검증 (Risk-Gate 필수 통과 확인)
    2. [V31.18] strategy_id 무결성 유지 (ID 사슬 보존)
    3. 실전 주문 실행 전 최종 Fail-Fast 가드 가동
    """
    
    # =========================
    # 🔵 [Standard] 입력 계약 재검증
    # =========================
    if not isinstance(signals, list):
        raise RuntimeError("ORDER_MANAGER_INPUT_TYPE_ERROR: signals must be list")

    # 필수 필드 정의 (strategy_id 포함)
    required_fields = [
        "symbol",
        "side",
        "price",
        "asset_type",
        "strategy_id",
        "risk_per_trade",
        "stop_distance",
        "volume",
        "approved"  # 🔥 V31.19 추가: 리스크 승인 여부
    ]

    # =========================
    # 🔵 Risk-Gate 및 무결성 전수 검사
    # =========================
    for sig in signals:
        if not isinstance(sig, dict):
            raise RuntimeError("ORDER_MANAGER_INVALID_SIGNAL")
            
        # 1. 필드 누락 검사
        for f in required_fields:
            if sig.get(f) is None:
                raise RuntimeError(f"ORDER_MANAGER_MISSING_FIELD: {f} for {sig.get('symbol')}")

        # 2. 🔥 [V31.19 핵심] Risk-Gate 차단 확인
        # Risk Manager를 거치지 않았거나, False인 경우 즉시 중단
        if sig.get("approved") is not True:
            raise RuntimeError(f"ORDER_BLOCKED_BY_RISK_GATE: {sig.get('symbol')} (Strategy: {sig.get('strategy_id')})")

    # =========================
    # 🔵 주문 실행 및 결과 생성
    # =========================
    results = []

    for sig in signals:
        try:
            # ID 사슬 유지 및 로깅
            logger.info(f"ORDER_EXECUTING: {sig['symbol']} | ID: {sig['strategy_id']} | Vol: {sig['volume']}")

            # [V31.18] execution_results 구조 준수
            execution_item = {
                "status": "FILLED",
                "symbol": sig["symbol"],
                "side": sig["side"],
                "price": sig["price"],
                "asset_type": sig["asset_type"],
                "strategy_id": sig["strategy_id"], 
                "volume": sig["volume"]
            }
            results.append(execution_item)

        except Exception as e:
            # 주문 실행 중 예외 발생 시 시스템 정지 (데이터 오염 방지)
            raise RuntimeError(f"ORDER_EXECUTION_FAILED: {sig['symbol']} - {str(e)}")

    # =========================
    # 🔵 [Standard] 출력 계약 준수
    # =========================
    if not isinstance(results, list):
        raise RuntimeError("ORDER_MANAGER_RESULTS_INVALID")

    return {
        "results": results
    }