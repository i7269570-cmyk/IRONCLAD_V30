# ============================================================
# IRONCLAD_V31.35 - Unified Market Data Adapter (Full Contract Sync)
# ============================================================
from typing import Dict, Any
import pandas as pd

def build_market_data_map(data_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    역할: data_bundle -> regime_filter, entry_engine, exit_engine 통합 스냅샷 변환
    규칙: 
    1. asset_type/group 포함 필수
    2. 전략(TURTLE/DISPARITY) 및 청산에 필요한 모든 ref 필드 최상위 노출
    3. 데이터 누락 시 자동 보정 없이 즉시 RuntimeError (SAFE_HALT)
    """
    result = {}

    for symbol, v in data_bundle.items():
        current = v.get("current")
        history = v.get("history")

        # 1. 구조 및 메타데이터 검증
        if history is None or history.empty:
            raise RuntimeError(f"EMPTY_HISTORY: {symbol}")
            
        asset_type = current.get("asset_type")
        asset_group = current.get("asset_group")
        
        if not asset_type or not asset_group:
            raise RuntimeError(f"METADATA_MISSING: {symbol} (asset_type/group)")

        # 최신 지표 데이터 추출
        last_row = history.iloc[-1]

        # 2. 필수 지표 및 전략 필드 검증 (계약 전수 조사)
        required_indicators = [
            "close", "ma20", "ma50", "ma200", 
            "adx", "atr_percent", "disparity_abs",
            "highest_20", "lowest_10", "disparity_20", "volume_ratio"
        ]
        for field in required_indicators:
            if field not in last_row:
                # 하드코딩된 기본값 삽입 금지, 즉시 SAFE_HALT 유도
                raise RuntimeError(f"INDICATOR_MISSING_IN_ADAPTER: {symbol} -> {field}")

        # 3. 최종 통합 Snapshot 생성 (Regime + Entry + Exit + Metadata)
        result[symbol] = {
            # Metadata (Entry Engine 및 Risk Gate 필수)
            "asset_type": asset_type,
            "asset_group": asset_group,
            
            # Regime Filter 요구 지표
            "close": last_row["close"],
            "ma20": last_row["ma20"],
            "ma50": last_row["ma50"],
            "ma200": last_row["ma200"],
            "adx": last_row["adx"],
            "atr_percent": last_row["atr_percent"],
            "disparity_abs": last_row["disparity_abs"],
            
            # 전략(Entry/Exit) 요구 핵심 필드 (🔥 V31.35 추가)
            "highest_20": last_row["highest_20"],
            "lowest_10": last_row["lowest_10"],
            "disparity_20": last_row["disparity_20"],
            
            # Execution Layer 요구 데이터
            "value": current["value"],
            "volume_ratio": last_row["volume_ratio"],
            "change_rate": current["change_rate"],
            
            # 내부 참조용 원본 데이터 보존
            "_history_row": last_row 
        }

    return result