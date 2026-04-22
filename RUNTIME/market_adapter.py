# ============================================================
# IRONCLAD_V31.35 - Unified Market Data Adapter (Full Contract Sync)
# ============================================================
from typing import Dict, Any
import pandas as pd

def build_market_data_map(data_bundle: Dict[str, Any]) -> Dict[str, Any]:
    result = {}

    for symbol, v in data_bundle.items():
        current = v.get("current")
        history = v.get("history")

        if history is None or history.empty:
            raise RuntimeError(f"EMPTY_HISTORY: {symbol}")

        asset_type = current.get("asset_type")
        asset_group = current.get("asset_group")

        if not asset_type or not asset_group:
            raise RuntimeError(f"METADATA_MISSING: {symbol} (asset_type/group)")

        last_row = history.iloc[-1]

        required_indicators = [
            "close", "ma20", "ma50", "ma60", "ma200",
            "atr_percent", "disparity_abs",
            "highest_20", "lowest_10", "disparity_20", "volume_ratio"
        ]
        for field in required_indicators:
            if field not in last_row:
                print(f"⚠️ SKIP: {symbol} missing {field}")
                continue

        result[symbol] = {
            "asset_type": asset_type,
            "asset_group": asset_group,

            # Regime Filter
            "close": last_row["close"],
            "ma20": last_row["ma20"],
            "ma50": last_row["ma50"],
            "ma60": last_row["ma60"],
            "ma200": last_row["ma200"],
            "atr_percent": last_row["atr_percent"],
            "disparity_abs": last_row["disparity_abs"],

            # Entry/Exit
            "highest_20": last_row["highest_20"],
            "lowest_10": last_row["lowest_10"],
            "disparity_20": last_row["disparity_20"],
            "low": last_row["low"],

            # Execution
            "value": current["value"],
            "volume_ratio": last_row["volume_ratio"],

            # 원본 보존
            "_history_row": last_row
        }

    return result
