import pandas as pd
import yaml
import os
import json
from ls_adapter import LSAdapter

def load_market_data(asset_types, strategy_path, access_token):
    # 🎯 핵심: 실행 파일 위치(RUNTIME/) 기준으로 프로젝트 루트를 정확히 포착
    # /프로젝트/RUNTIME/data_loader.py -> 상위로 두 번 이동하면 /프로젝트/ 루트 도달
    PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    adapter = LSAdapter(access_token)
    
    rules_path = os.path.join(strategy_path, "data_rules.yaml")
    
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            data_rules = yaml.safe_load(f)
            
        window_size = data_rules.get("window_size")
        universe_paths = data_rules.get("universe_paths")

        if window_size is None:
            raise RuntimeError("MISSING_WINDOW_SIZE")

    except Exception as e:
        raise RuntimeError(f"CONFIG_LOAD_FAILED: {str(e)}")

    data_bundle = {}

    for asset_type in asset_types:
        suffix = universe_paths.get(asset_type.lower())
        if not suffix:
            continue
            
        # 🎯 핵심: 명시적으로 계산된 PROJECT_ROOT를 사용하여 읽기 경로 생성
        universe_file = os.path.join(PROJECT_ROOT, suffix)

        if not os.path.exists(universe_file):
            # 파일이 없으면 빈 번들을 반환하여 시스템 중단 방지
            continue

        with open(universe_file, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)
            
        symbols = universe_data if isinstance(universe_data, list) else universe_data.get("symbols", [])

        for symbol in symbols:
            raw_data = adapter.fetch_ohlcv(symbol, window_size)
            if raw_data is None or len(raw_data) == 0:
                continue 

            current = raw_data[-1]
            data_bundle[symbol] = {
                
                "current": {
                    "price": current["close"],          # ✔ 수정
                    "volume": current["volume"],
                    "high": current["high"], 
                    "low": current["low"],
                    "asset_type": "STOCK",              # ✔ 추가
                    "asset_group": "KOSPI_KOSDAQ"       # ✔ 추가
                },
                "history": raw_data
            }

    return data_bundle