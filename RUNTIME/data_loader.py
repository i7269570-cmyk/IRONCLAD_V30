# ============================================================
# IRONCLAD_V31.11 - Structural Data Loader (STRICT)
# ============================================================
import pandas as pd
import yaml
import os
import json
import numpy as np

def load_market_data(asset_types, strategy_path):
    """
    [V31.11 STRICT MODE]
    1. 지표 계산 로직 제거 (indicator_calc 이동)
    2. NaN 제거 금지 (history 원본 유지)
    3. asset_type 필드 강제 포함
    4. window_size 외 하드코딩 검증 삭제
    5. 에러 메시지 내 symbol 포함 (디버깅 강화)
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    rules_path = os.path.join(strategy_path, "data_rules.yaml")
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            data_rules = yaml.safe_load(f)
        window_size = data_rules.get("window_size")
        if window_size is None:
            raise RuntimeError(f"MISSING_WINDOW_SIZE: {rules_path}")
    except (FileNotFoundError, yaml.YAMLError) as e:
        raise RuntimeError(f"CONFIG_LOAD_FAILED: {str(e)}")

    data_bundle = {}

    for asset_type in asset_types:
        if asset_type not in ["STOCK", "CRYPTO"]:
            raise RuntimeError(f"INVALID_ASSET_TYPE: {asset_type}")

        universe_filename = f"{asset_type.lower()}_universe.json"
        universe_path = os.path.join(BASE_DIR, "UNIVERSE", universe_filename)
        
        if not os.path.exists(universe_path):
            raise RuntimeError(f"UNIVERSE_FILE_MISSING: {universe_path}")

        try:
            with open(universe_path, 'r', encoding='utf-8') as f:
                symbols = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"UNIVERSE_FILE_CORRUPTED: {universe_path} -> {str(e)}")

        for symbol in symbols:
            # [규격] 데이터 수집 (외부 fetch 로직 결과물 가정)
            # 필수 컬럼: datetime, open, high, low, close, volume
            df = pd.DataFrame([], columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])

            # [V31.11] 하드코딩 제거 및 window_size 검증 (추적 가능하도록 symbol 추가)
            if len(df) < window_size:
                raise RuntimeError(f"INSUFFICIENT_HISTORY: {symbol}")

            # [V31.11] asset_type 명시적 추가
            df["asset_type"] = asset_type

            # ============================================================
            # [V31.11] Selector 필드 계산 및 Snapshot 구성
            # ============================================================
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # change_rate: ((현재종가 - 이전종가) / 이전종가) * 100
            change_rate = ((last["close"] - prev["close"]) / prev["close"]) * 100
            # value: 종가 * 거래량
            value = last["close"] * last["volume"]

            current_snapshot = {
                "symbol": symbol,
                "asset_type": asset_type,
                "price": last["close"],
                "datetime": last["datetime"],
                "change_rate": change_rate,
                "value": value
            }

            # 최종 반환 구조 할당 (NaN 유지)
            data_bundle[symbol] = {
                "current": current_snapshot,
                "history": df
            }

    if not data_bundle:
        raise RuntimeError(f"EMPTY_DATA_BUNDLE: {os.path.join(BASE_DIR, 'UNIVERSE')}")

    return data_bundle