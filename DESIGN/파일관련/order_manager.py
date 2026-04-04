import logging
from typing import List, Dict, Any

# =============================================================================
# IRONCLAD_V30.1_FINAL: ORDER_MANAGER (Execution SSOT)
# FIX: FAIL-FAST (RAISE ON ERROR), INPUT TRUST PRINCIPLE, STATUS ENFORCEMENT
# =============================================================================

logger = logging.getLogger("IRONCLAD_RUNTIME.ORDER_MANAGER")

def execute_orders(final_signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    최종 검증된 신호를 거래소 API에 전송한다.
    
    [원칙]
    1. 입력 신뢰: pre_order_check를 통과한 데이터를 재추출/재검증하지 않고 그대로 사용한다.
    2. Fail-Fast: 주문 실패(Rejected)나 부분 실패(Partial Fail) 발생 시 예외를 raise하여 상위로 전파한다.
    """
    if not final_signals:
        logger.info("ORDER_MANAGER: No signals to execute.")
        return {"status": "success", "executed_count": 0, "results": []}

    execution_results = []
    success_count = 0
    total_count = len(final_signals)

    logger.info(f"ORDER_MANAGER: Executing {total_count} validated orders...")

    for signal in final_signals:
        try:
            # [입력 신뢰 원칙] signal 객체를 통째로 API 엔진에 전달 (재추출 금지)
            # 실제 구현 시: response = exchange_api.place_order(**signal)
            
            # 가상의 성공 응답 구조 (API 응답 기반)
            order_res = {
                **signal,  # 원본 데이터 유지
                "order_id": f"ORD-{signal['symbol']}-777",
                "status": "filled",
                "timestamp": "2026-03-23T16:05:20"
            }
            
            execution_results.append(order_res)
            success_count += 1
            logger.info(f"ORDER_SUCCESS: {signal['symbol']} | Side: {signal['side']}")

        except Exception as e:
            # 개별 주문 실패 시 즉시 상위로 예외 전파 (rejected 결과 흡수 방지)
            logger.critical(f"ORDER_CRITICAL_FAIL: {signal.get('symbol')} execution failed.")
            raise RuntimeError(f"API_EXECUTION_ERROR: {str(e)}") from e

    # [상태 판정 및 전파]
    if success_count < total_count:
        # 부분 실패 상황 (루프 내 raise가 없더라도 최종 정합성 확인)
        error_msg = f"PARTIAL_EXECUTION_FAILURE: {success_count}/{total_count} succeeded."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info(f"ORDER_MANAGER: All {success_count} orders filled successfully.")

    return {
        "status": "success",
        "executed_count": success_count,
        "results": execution_results
    }