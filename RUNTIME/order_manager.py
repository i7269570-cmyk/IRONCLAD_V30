# ============================================================
# IRONCLAD_V31.18 - Order Manager (Strategy ID Integrity)
# ============================================================
import logging

# [Standard] 로깅 인터페이스 정의
logger = logging.getLogger("IRONCLAD_RUNTIME.ORDER_MANAGER")

def execute_orders(signals):
    """
    입력: list[dict] (검증된 신호 리스트)
    출력: dict {"results": list[dict]} (체결 결과 데이터)
    기능: 
    1. [V31.18] strategy_name을 폐기하고 strategy_id를 필수 계약 필드로 추가한다.
    2. 신호를 수신하여 주문을 실행하고 계약된 구조의 체결 결과를 반환한다.
    """
    
    # =========================
    # 🔵 [Standard] 입력 계약 재검증
    # =========================
    if not isinstance(signals, list):
        raise RuntimeError("ORDER_MANAGER_INPUT_TYPE_ERROR: signals must be list")

    # [V31.18 핵심 수정] strategy_id를 필수 필드로 지정
    required_fields = [
        "symbol",
        "side",
        "price",
        "asset_type",
        "strategy_id",   # 🔥 strategy_name -> strategy_id 변경
        "risk_per_trade",
        "stop_distance",
        "volume"
    ]

    for sig in signals:
        if not isinstance(sig, dict):
            raise RuntimeError("ORDER_MANAGER_INVALID_SIGNAL")
            
        for f in required_fields:
            if sig.get(f) is None:
                # 필드 누락 시 데이터 오염 방지를 위해 즉시 중단 (Fail-Fast)
                raise RuntimeError(f"ORDER_MANAGER_MISSING_FIELD: {f} for {sig.get('symbol')}")

    # =========================
    # 🔵 주문 실행 및 결과 생성
    # =========================
    results = []

    for sig in signals:
        try:
            # 실제 주문 API 호출 위치 (ID 사슬 유지 확인)
            logger.info(f"ORDER_EXECUTING: {sig['symbol']} | ID: {sig['strategy_id']} | Vol: {sig['volume']}")

            # [V31.18] execution_results 구조 보강 (strategy_id 포함)
            execution_item = {
                "status": "FILLED",
                "symbol": sig["symbol"],
                "side": sig["side"],
                "price": sig["price"],
                "asset_type": sig["asset_type"],
                "strategy_id": sig["strategy_id"], # 🔥 ID 사슬 유지
                "volume": sig["volume"]
            }
            results.append(execution_item)

        except Exception as e:
            # 주문 실행 중 예외 발생 시 무음 처리 없이 즉시 중단
            raise RuntimeError(f"ORDER_EXECUTION_FAILED: {sig['symbol']} - {str(e)}")

    # =========================
    # 🔵 [Standard] 출력 계약 준수
    # =========================
    if not isinstance(results, list):
        raise RuntimeError("ORDER_MANAGER_RESULTS_INVALID")

    # 반드시 dict 구조로 반환하여 후속 모듈(fill_tracker 등)과의 계약 준수
    return {
        "results": results
    }