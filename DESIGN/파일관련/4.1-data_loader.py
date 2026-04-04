# ============================================================
# IRONCLAD_V31.11 - Structural Data Loader (Selector Field Patch)
# ============================================================
import pandas as pd
import yaml
import os
import json

def load_market_data(asset_types, strategy_path):
    """
    [V31.11 수정]
    1. current(snapshot) 내 selector 필수 필드(change_rate, value) 강제 포함
    2. 계산 로직: history 기반 산출 (0 대체 또는 자동 보정 금지)
    3. 안전성: change_rate 계산을 위한 최소 데이터(2개 행) 검증 강화
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
        # [규격] asset_type 검증 유지
        if asset_type not in ["STOCK", "CRYPTO"]:
            raise RuntimeError(f"INVALID_ASSET_TYPE: {asset_type}")

        universe_filename = f"{asset_type.lower()}_universe.json"
        universe_path = os.path.join(BASE_DIR, "UNIVERSE", universe_filename)
        
        if not os.path.exists(universe_path):
            continue 

        try:
            with open(universe_path, 'r', encoding='utf-8') as f:
                symbols = json.load(f) 
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"UNIVERSE_FILE_CORRUPTED: {universe_path} -> {str(e)}")

        for symbol in symbols:
            # exchange_fetch_logic_placeholder (데이터 수집부 호출 결과가 df라고 가정)
            # [규격] 필수 컬럼 구성: datetime, open, high, low, close, volume
            # ohlcv = fetch_ohlcv(symbol)
            df = pd.DataFrame([], columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])

            # [V31.11] 안전성 검증: change_rate 계산을 위해 최소 2개 이상의 행 필요
            if len(df) < 2 or len(df) < window_size:
                raise RuntimeError(f"INSUFFICIENT_HISTORY: {symbol} (Required at least 2 for change_rate)")

            # [규격] history 데이터 구성
            df['asset_type'] = asset_type

            # [V31.11] Selector 필수 필드 계산 (history 기준)
            last = df.iloc[-1]
            prev = df.iloc[-2]

            # 1. change_rate 계산: ((종가 - 전일종가) / 전일종가) * 100
            change_rate = ((last["close"] - prev["close"]) / prev["close"]) * 100

            # 2. value(거래대금) 계산: 종가 * 거래량
            value = last["close"] * last["volume"]

            # [V31.11] current 스냅샷 구조 수정 (완전성 보장)
            current_snapshot = {
                "symbol": symbol,
                "asset_type": asset_type,
                "price": last["close"],
                "datetime": last["datetime"],
                "change_rate": change_rate,
                "value": value
            }

            # [V31.11] 최종 반환 구조 할당
            data_bundle[symbol] = {
                "current": current_snapshot,
                "history": df
            }

    if not data_bundle:
        raise RuntimeError(f"EMPTY_DATA_BUNDLE: {os.path.join(BASE_DIR, 'UNIVERSE')}")

    return data_bundle