import logging

# [수정 1] 로깅 인터페이스 정의
logger = logging.getLogger("IRONCLAD_RUNTIME.ORDER_MANAGER")

def execute_orders(signals):
    """
    입력: list[dict] (검증된 신호 리스트)
    출력: dict {"results": list[dict]} (체결 결과 데이터)
    기능: 신호를 수신하여 주문을 실행하고 계약된 구조의 체결 결과를 반환한다.
    """
    
    # =========================
    # 🔵 [수정 2] 입력 계약 재검증 (입력 단계 차단기)
    # =========================
    if not isinstance(signals, list):
        raise RuntimeError("ORDER_MANAGER_INPUT_TYPE_ERROR: signals must be list")

    required_fields = [
        "symbol",
        "side",
        "price",
        "asset_type",
        "strategy_name",
        "risk_per_trade",
        "stop_distance",
        "volume"
    ]

    for sig in signals:
        # [수정 3] 신호 타입 검증 및 무음 처리(continue) 제거
        if not isinstance(sig, dict):
            raise RuntimeError("ORDER_MANAGER_INVALID_SIGNAL")
            
        for f in required_fields:
            if sig.get(f) is None:
                raise RuntimeError(f"ORDER_MANAGER_MISSING_FIELD: {f}")

    # =========================
    # 🔵 주문 실행 및 결과 생성
    # =========================
    results = []

    for sig in signals:
        try:
            # 실제 주문 API 호출 위치 (본 코드에서는 계약된 결과 변환 로직만 수행)
            logger.info(f"ORDER_EXECUTING: {sig['symbol']} | {sig['side']} | Vol: {sig['volume']}")

            # [수정 4] execution_results 구조 보강 (전략 및 수량 정보 포함)
            execution_item = {
                "status": "FILLED",
                "symbol": sig["symbol"],
                "side": sig["side"],
                "price": sig["price"],
                "asset_type": sig["asset_type"],
                "strategy_name": sig["strategy_name"],
                "volume": sig["volume"]
            }
            results.append(execution_item)

        except Exception as e:
            # 주문 실행 중 예외 발생 시 무음 처리 없이 즉시 중단
            raise RuntimeError(f"ORDER_EXECUTION_FAILED: {sig['symbol']} - {str(e)}")

    # =========================
    # 🔵 [수정 1, 5] 출력 계약 준수 및 타입 보장
    # =========================
    if not isinstance(results, list):
        raise RuntimeError("ORDER_MANAGER_RESULTS_INVALID")

    # 반드시 dict 구조로 반환하여 후속 모듈(fill_tracker 등)과의 계약 준수
    return {
        "results": results
    }