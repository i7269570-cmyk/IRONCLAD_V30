# ============================================================
# IRONCLAD_V31.24 - Order Manager (Asset Group Integrity)
# ============================================================
import logging

# [Standard] 로깅 인터페이스 정의
logger = logging.getLogger("IRONCLAD_RUNTIME.ORDER_MANAGER")

def execute_orders(signals):
    """
    입력: list[dict] (Risk Manager에 의해 승인된 신호 리스트)
    출력: dict {"results": list[dict]} (체결 결과 데이터)
    기능: 
    1. [V31.24] 'asset_group' 필드 검증 및 전파 (Downstream 계약 준수)
    2. [V31.24] 주문 상태 'FILLED' 반환 (즉시 체결 계약 준수)
    3. strategy_id 무결성 유지 (ID 사슬 보존)
    """
    
    # =========================
    # 🔵 [Standard] 입력 계약 재검증
    # =========================
    if not isinstance(signals, list):
        raise RuntimeError("ORDER_MANAGER_INPUT_TYPE_ERROR: signals must be list")

    # [V31.24] 필수 필드 정의 (asset_group 추가)
    required_fields = [
        "symbol",
        "side",
        "price",
        "asset_type",
        "asset_group", 
        "strategy_id",
        "risk_per_trade",
        "stop_distance",
        "volume",
        "approved"
    ]

    # =========================
    # 🔵 Risk-Gate 및 무결성 전수 검사
    # =========================
    for sig in signals:
        if not isinstance(sig, dict):
            raise RuntimeError("ORDER_MANAGER_INVALID_SIGNAL")
            
        # 1. 필드 누락 검사 (Strict Mode: .get 기본값 금지)
        for f in required_fields:
            if f not in sig or sig[f] is None:
                raise RuntimeError(f"ORDER_MANAGER_MISSING_FIELD: {f} for {sig.get('symbol', 'UNKNOWN')}")

        # 2. Risk-Gate 차단 확인
        if sig["approved"] is not True:
            raise RuntimeError(f"ORDER_BLOCKED_BY_RISK_GATE: {sig['symbol']} (Strategy: {sig['strategy_id']})")

    # =========================
    # 🔵 주문 실행 및 결과 생성
    # =========================
    results = []

    for sig in signals:
        try:
            logger.info(f"ORDER_EXECUTING: {sig['symbol']} | ID: {sig['strategy_id']} | Vol: {sig['volume']}")

            # [V31.24] execution_results 구조 준수 (status를 FILLED로 수정)
            execution_item = {
                "status": "FILLED", # 🔴 [V31.24 수정] PENDING에서 FILLED로 변경하여 체결 추적 보장
                "symbol": sig["symbol"],
                "side": sig["side"],
                "price": sig["price"],
                "asset_type": sig["asset_type"],
                "asset_group": sig["asset_group"], 
                "strategy_id": sig["strategy_id"], 
                "volume": sig["volume"]
            }
            results.append(execution_item)

        except Exception as e:
            # 주문 실행 중 예외 발생 시 시스템 정지 (SAFE_HALT)
            raise RuntimeError(f"ORDER_EXECUTION_FAILED: {sig['symbol']} - {str(e)}")

    # =========================
    # 🔵 [Standard] 출력 계약 준수
    # =========================
    if not isinstance(results, list):
        raise RuntimeError("ORDER_MANAGER_RESULTS_INVALID")

    return {
        "results": results
    }