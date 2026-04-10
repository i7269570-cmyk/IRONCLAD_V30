# ============================================================
# IRONCLAD_V31.33 - Structural Data Loader (List[str] Schema)
# ============================================================
import pandas as pd
import yaml
import os
import json
import numpy as np

def _assign_asset_group(symbol: str, asset_type: str) -> str:
    """
    [V31.33] 심볼 및 타입 기반 자산 그룹 명시적 분류 함수
    - 자동 기본값 삽입 금지: 정의되지 않은 조건 시 RuntimeError 발생
    """
    if asset_type == "CRYPTO":
        return "COIN_MAIN"
    elif asset_type == "STOCK":
        # 한국 주식 시장 코드 체계 기반 명시적 분류
        if len(symbol) == 6 and symbol.isdigit():
            return "KOSPI_KOSDAQ"
        else:
            raise RuntimeError(f"INVALID_STOCK_SYMBOL_FORMAT: {symbol}")
    else:
        raise RuntimeError(f"UNKNOWN_ASSET_TYPE_FOR_GROUPING: {asset_type}")

def load_market_data(asset_types, strategy_path):
    """
    [V31.33 STRICT MODE]
    1. universe_data (List[str]) 기반 심볼 추출
    2. 빈 DataFrame 생성 및 더미 로직 완전 제거 (Data Integrity)
    3. 실제 데이터 로드 실패 시 즉시 RuntimeError (SAFE_HALT)
    4. current_snapshot 필수 계약 필드 전수 포함
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
                universe_data = json.load(f)
            if not isinstance(universe_data, list):
                raise RuntimeError(f"INVALID_UNIVERSE_FORMAT: Expected List[str] in {universe_filename}")
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"UNIVERSE_FILE_CORRUPTED: {universe_path} -> {str(e)}")

        for item in universe_data:
            symbol = str(item)
            asset_group = _assign_asset_group(symbol, asset_type)

            # [Integrity] 실제 데이터 로드 시도 (Placeholder 생성 금지)
            # 로컬 경로 예시: DATA/{asset_type}/{symbol}.csv
            data_path = os.path.join(BASE_DIR, "DATA", asset_type, f"{symbol}.csv")
            
            if not os.path.exists(data_path):
                raise RuntimeError(f"DATA_SOURCE_MISSING: {symbol} at {data_path}")

            try:
                # 데이터 로드 시도
                df = pd.read_csv(data_path)
            except Exception as e:
                raise RuntimeError(f"DATA_LOAD_CRITICAL_FAILURE: {symbol} -> {str(e)}")

            # [Strict] 데이터 무결성 검증 (빈 파일 또는 결손 데이터 차단)
            if df is None or df.empty:
                raise RuntimeError(f"DATA_SOURCE_EMPTY: {symbol}")

            # window_size 검증 (미달 시 즉시 중단)
            if len(df) < window_size:
                raise RuntimeError(f"INSUFFICIENT_HISTORY: {symbol} (Len: {len(df)} < Req: {window_size})")

            df["asset_type"] = asset_type
            df["asset_group"] = asset_group

            # ============================================================
            # [V31.33] Selector 필드 및 Snapshot 구성 (계약 준수)
            # ============================================================
            last = df.iloc[-1]
            prev = df.iloc[-2]

            change_rate = ((last["close"] - prev["close"]) / prev["close"]) * 100
            value = float(last["close"] * last["volume"])

            # [V31.33] market_adapter 및 selector를 위한 최정예 계약 구조
            current_snapshot = {
                "symbol": symbol,
                "asset_type": asset_type,
                "asset_group": asset_group,
                "price": float(last["close"]),
                "datetime": last["datetime"],
                "change_rate": float(change_rate),
                "value": value
            }

            # 최종 반환 구조 할당 (계약 일치)
            data_bundle[symbol] = {
                "symbol": symbol,
                "current": current_snapshot,
                "history": df
            }

    # 전체 후보군 중 하나라도 로드되지 않으면 파이프라인 중단
    if not data_bundle:
        raise RuntimeError(f"EMPTY_DATA_BUNDLE: Critical failure in data acquisition")

    return data_bundle