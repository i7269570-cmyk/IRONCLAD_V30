import logging
from typing import List, Dict, Any

logger = logging.getLogger("IRONCLAD_RUNTIME.FILL_TRACKER")

def track_fills(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """[FIX] 데이터 결함 시 무시하지 않고 예외를 발생시켜 incident 전파 보장"""
    processed_fills = []

    for order in orders:
        status = order.get("status", "FAILED").upper()
        
        if status in ["FILLED", "PARTIAL"]:
            price = order.get("executed_price")
            volume = order.get("executed_volume")
            
            # [FIX] continue 제거 -> 예외 발생으로 상위 에러 핸들러 호출 유도
            if price is None or volume is None or price <= 0 or volume <= 0:
                error_msg = f"FILL_TRACKER_CRITICAL: Malformed data for {order.get('symbol')}"
                logger.critical(error_msg)
                raise RuntimeError(error_msg)

            processed_fills.append({
                "symbol": order.get("symbol"),
                "status": status,
                "filled_price": price,
                "filled_size": volume,
                "side": order.get("side")
            })
    return processed_fills