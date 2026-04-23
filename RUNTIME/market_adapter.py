# ============================================================
# IRONCLAD_V31.37 - Market Data Adapter
# ============================================================
# SSOT 계약:
#   data_bundle[symbol] = {
#       "asset_type":  str,   ← 최상위 (regime/entry 접근 편의)
#       "asset_group": str,   ← 최상위 (regime/entry 접근 편의)
#       "current":     dict,  # price, value, asset_type, asset_group 포함
#       "history":     DataFrame  # 지표 포함 전체 df
#   }
# ============================================================
from typing import Dict, Any


def build_market_data_map(raw_data_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    data_loader 출력에 asset_type/group 을 최상위로 추가하여 반환.
    구조 변환 최소화 — current/history 원본 유지.
    """
    result = {}

    for symbol, v in raw_data_bundle.items():
        current = v.get("current")
        history = v.get("history")

        if history is None or history.empty:
            raise RuntimeError(f"EMPTY_HISTORY: {symbol}")

        if not current:
            raise RuntimeError(f"MISSING_CURRENT: {symbol}")

        asset_type  = current.get("asset_type")
        asset_group = current.get("asset_group")

        if not asset_type or not asset_group:
            raise RuntimeError(f"METADATA_MISSING: {symbol}")

        result[symbol] = {
            "asset_type":  asset_type,   # 최상위 노출 (regime/entry 직접 접근)
            "asset_group": asset_group,  # 최상위 노출
            "current":     current,      # 원본 유지
            "history":     history,      # 원본 유지
        }

    return result
