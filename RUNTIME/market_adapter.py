# ============================================================
# IRONCLAD_V31.38 - Market Data Adapter
# ============================================================
# SSOT 계약:
#   data_bundle[symbol] = {
#       "asset_type":  str,        ← 최상위
#       "asset_group": str,        ← 최상위
#       "current":     dict,       # price, value, asset_type, asset_group 포함
#       "history":     DataFrame,  # 지표 포함 전체 df (보존용)
#       "snapshot":    Series,     # history.iloc[-1] (계산용)
#   }
# ============================================================
from typing import Dict, Any


def build_market_data_map(raw_data_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    data_loader 출력에 최상위 키 + snapshot 추가.
    current / history 원본 유지.
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
            "asset_type":  asset_type,          # 최상위 (regime/entry 직접 접근)
            "asset_group": asset_group,         # 최상위
            "current":     current,             # 원본 유지
            "history":     history,             # 보존용 원본 DataFrame
            "snapshot":    history.iloc[-1],    # 계산용 최신 Series
        }

    return result
