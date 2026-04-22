import time
import pandas as pd
import yaml
import os
import json
import sys
import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from RUNTIME.ls_adapter import LSAdapter

def load_market_data(asset_types, strategy_path, access_token):
    rules_path = os.path.join(strategy_path, "data_rules.yaml")
    with open(rules_path, "r", encoding="utf-8") as f:
        data_rules = yaml.safe_load(f)
    window_size = data_rules.get("window_size", 20)

    data_bundle = {}

    for asset_type in asset_types:

        # 1. 주식 데이터 처리
        if asset_type.upper() == "STOCK":
            adapter = LSAdapter(access_token)
            selected_path = os.path.join(PROJECT_ROOT, "STATE", "selected_symbols_STOCK.json")

            symbols = []
            if os.path.exists(selected_path):
                with open(selected_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    symbols = data.get("symbols", [])

            if not symbols:
                universe_path = os.path.join(PROJECT_ROOT, "UNIVERSE", "stock_universe.json")
                with open(universe_path, "r", encoding="utf-8") as f:
                    symbols = json.load(f).get("symbols", [])

            for symbol in symbols:
                time.sleep(0.6)
                try:
                    raw_data = adapter.fetch_ohlcv(symbol, window_size)

                    if not raw_data:
                        continue

                    if isinstance(raw_data, dict):
                        if "rsp_cd" in raw_data or "rsp_msg" in raw_data:
                            print(f"⚠️ SKIP: {symbol} load fail -> STOCK_STRUCTURE_ERROR: {symbol} -> {raw_data}")
                            continue
                        continue

                    df = pd.DataFrame(raw_data)
                    df = df.rename(columns={
                        "opnprc": "open", "hgprc": "high", "lwprc": "low",
                        "clsprc": "close", "jvol": "volume", "vol": "volume"
                    })

                    if "open" not in df.columns and "close" in df.columns:
                        df["open"] = df["close"]

                    required_cols = ["open", "high", "low", "close", "volume"]
                    if not all(col in df.columns for col in required_cols):
                        continue

                    df = df[df["volume"] > 0]
                    if df.empty:
                        continue

                    current = df.iloc[-1]
                    current_dict = current.to_dict()
                    current_dict.update({
                        "asset_type": "STOCK",
                        "asset_group": "STOCK",
                        "price": float(current["close"]),
                        "value": float(current["close"]) * float(current["volume"])
                    })

                    data_bundle[symbol] = {
                        "current": current_dict,
                        "history": df
                    }
                except Exception as e:
                    print(f"⚠️ SKIP: {symbol} load fail -> {e}")
                    continue

        # 2. 코인 데이터 처리
        elif asset_type.upper() == "CRYPTO":
            selected_path = os.path.join(PROJECT_ROOT, "STATE", "selected_symbols_CRYPTO.json")

            symbols = []
            if os.path.exists(selected_path):
                with open(selected_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    symbols = data.get("symbols", [])

            if not symbols:
                universe_path = os.path.join(PROJECT_ROOT, "UNIVERSE", "coin_universe.json")
                with open(universe_path, "r", encoding="utf-8") as f:
                    symbols = json.load(f).get("symbols", [])

            for symbol in symbols:
                time.sleep(0.2)
                url = f"https://api.upbit.com/v1/candles/minutes/1?market={symbol}&count={window_size}"
                res = requests.get(url)
                if res.status_code != 200:
                    continue
                raw_data = res.json()
                if not raw_data:
                    continue

                df = pd.DataFrame(raw_data)
                df = df.rename(columns={
                    "opening_price": "open", "high_price": "high", "low_price": "low",
                    "trade_price": "close", "candle_acc_trade_volume": "volume"
                })
                df = df.sort_values(by="candle_date_time_utc")

                current = df.iloc[-1]
                current_dict = current.to_dict()
                current_dict.update({
                    "asset_type": "CRYPTO",
                    "asset_group": "CRYPTO",
                    "price": float(current["close"]),
                    "value": float(current["close"]) * float(current["volume"])
                })

                data_bundle[symbol] = {"current": current_dict, "history": df}

    return data_bundle
