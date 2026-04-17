import time
import pandas as pd
import yaml
import os
import json
import sys

sys.path.append(os.path.dirname(__file__))

# ============================================================
# IRONCLAD_V31.47 - Data Loader (Adapter Branching Applied)
# ============================================================

def load_market_data(asset_types, strategy_path, access_token):
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    rules_path = os.path.join(strategy_path, "data_rules.yaml")
    
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            data_rules = yaml.safe_load(f)
            
        window_size = data_rules.get("window_size") # [보안] MISSING_WINDOW_SIZE 해결책
        universe_paths = data_rules.get("universe_paths")

        if window_size is None:
            raise RuntimeError("MISSING_WINDOW_SIZE")

    except Exception as e:
        raise RuntimeError(f"CONFIG_LOAD_FAILED: {str(e)}")

    data_bundle = {}

    # 🎯 [보안점 해결] 자산별 루프 진입
    for asset_type in asset_types:
        current_asset_type = asset_type.upper()
        
        # 🔥 [사용자 제안 로직 적용] 어댑터 물리적 분리
        if current_asset_type == "STOCK":
            from ls_adapter import LSAdapter
            adapter = LSAdapter(access_token)
        elif current_asset_type == "CRYPTO":
            try:
                from upbit_adapter import UpbitAdapter
                adapter = UpbitAdapter()
            except ImportError:
                print("⚠️ [SKIP] UpbitAdapter.py 누락으로 코인 수집 건너뜀")
                continue
        else:
            continue

        suffix = universe_paths.get(asset_type.lower())
        if not suffix: continue
            
        universe_full_path = os.path.join(PROJECT_ROOT, suffix)
        
        try:
            with open(universe_full_path, "r", encoding="utf-8") as f:
                univ_data = json.load(f)
                symbols = univ_data.get("symbols", [])
        except Exception: continue

        for symbol in symbols:
            # API 레이트 리밋 보호 (0.6초 대기)
            time.sleep(0.6)
            
            # 🎯 해당 자산 전용 어댑터로 OHLCV 데이터 호출
            raw_data = adapter.fetch_ohlcv(symbol, window_size)
            
            if not raw_data: continue

            # 유효 데이터 필터링 (거래량 > 0)
            valid_rows = [row for row in raw_data if int(row.get("jvol") or row.get("volume") or 0) > 0]
            if not valid_rows: continue

            current = valid_rows[-1]
            data_bundle[symbol] = {
                "current": {
                    "price": current["close"],
                    "volume": current.get("volume") or current.get("jvol"),
                    "high": current["high"],
                    "low": current["low"],
                    "open": current["open"]
                },
                "history": pd.DataFrame(valid_rows),
                "asset_type": current_asset_type
            }

    return data_bundle