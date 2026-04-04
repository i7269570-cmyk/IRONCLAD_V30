import logging
from typing import List, Dict, Any

# =============================================================================
# IRONCLAD_V30.1_FINAL: ENTRY_ENGINE (Syntax Corrected)
# =============================================================================
logger = logging.getLogger("IRONCLAD_RUNTIME.ENTRY_ENGINE")

def generate_signals(candidates: List[Dict[str, Any]], strategy_path: str) -> List[Dict[str, Any]]:
    """후보 종목 리스트에서 진입 신호를 생성한다. (들여쓰기 오류 수정 완료)"""
    if not candidates:
        return []

    try:
        signals = []
        for asset in candidates:
            # 필수 데이터 포함 (pre_order_check 통과용)
            signals.append({
                "symbol": asset.get("symbol"),
                "side": "BUY",
                "price": asset.get("price"),
                "asset_type": asset.get("asset_type"),
                "entry_score": asset.get("selection_score", 0)
            })
        
        logger.info(f"ENTRY_ENGINE: Generated {len(signals)} signals.")
        return signals
        
    except Exception as e:
        raise RuntimeError(f"ENTRY_ENGINE_FAILURE: {str(e)}")