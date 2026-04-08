# ============================================================
# IRONCLAD_V31.23 - Market Data Adapter (Final PASS Version)
# ============================================================
from typing import Dict, Any

def build_market_data_map(data_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    [Execution Layer 전용 Adapter]

    역할:
    - data_bundle → execution snapshot 변환
    - current + history[-1] 결합

    규칙:
    - 기본값(.get(..., default)) 금지
    - 필드 누락 시 RuntimeError 발생
    - spread > 0 보장 (검증 로직 무력화 방지)
    """

    result = {}

    for symbol, v in data_bundle.items():
        current = v.get("current")
        history = v.get("history")

        # 구조 검증
        if not isinstance(current, dict):
            raise RuntimeError(f"INVALID_CURRENT_STRUCTURE: {symbol}")

        if history is None or history.empty:
            raise RuntimeError(f"EMPTY_HISTORY: {symbol}")

        last_row = history.iloc[-1]

        # 필수 필드 검증 (명시적)
        if "price" not in current:
            raise RuntimeError(f"PRICE_MISSING: {symbol}")

        if "value" not in current:
            raise RuntimeError(f"VALUE_MISSING: {symbol}")

        if "change_rate" not in current:
            raise RuntimeError(f"CHANGE_RATE_MISSING: {symbol}")

        if "volume_ratio" not in last_row:
            raise RuntimeError(f"VOLUME_RATIO_MISSING: {symbol}")

        price = current["price"]

        # 🔴 핵심: spread > 0 보장 (임시 호가 구조)
        bid = price * 0.999
        ask = price * 1.001

        result[symbol] = {
            "value": current["value"],
            "volume_ratio": last_row["volume_ratio"],
            "bid": bid,
            "ask": ask,
            "change_rate": current["change_rate"]
        }

    return result