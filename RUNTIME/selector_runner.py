import os
import json
import pandas as pd
import requests
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

from data_loader import load_market_data
from indicator_calc import calculate_indicators
from selector import select_candidates

def main():
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    
    # 1. 토큰 발급
    app_key = os.getenv("LS_APP_KEY")
    app_secret = os.getenv("LS_APP_SECRET")
    url = "https://openapi.ls-sec.co.kr:8080/oauth2/token"
    res = requests.post(url, data={
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecretkey": app_secret,
        "scope": "oob"
    }, headers={"content-type": "application/x-www-form-urlencoded"})
    
    access_token = res.json().get("access_token")

    asset_configs = {
        "STOCK": os.path.join(PROJECT_ROOT, "STRATEGY/STOCK"),
        "CRYPTO": os.path.join(PROJECT_ROOT, "STRATEGY/COIN") 
    }

    formatted_data = []

    for asset_type, strategy_path in asset_configs.items():
        if not os.path.exists(os.path.join(strategy_path, "data_rules.yaml")):
            print(f"⚠️ SKIP: No configuration found for {asset_type}")
            continue

        # [1단계 확인] 데이터 로더가 유니버스에서 종목을 몇 개나 긁어왔는지 확인
        raw_data_map = load_market_data([asset_type], strategy_path, access_token)
        print(f"🔥 RAW_DATA_MAP SIZE ({asset_type}):", len(raw_data_map))

        for symbol, content in raw_data_map.items():
            # [2단계 확인] 각 종목별로 히스토리 데이터가 실제로 존재하는지 확인
            print(f"🔥 SYMBOL: {symbol} | HISTORY LEN: {len(content['history'])}")
            
            df = pd.DataFrame(content["history"])
            
            if "jvol" in df.columns:
                df["volume"] = df["jvol"]
            elif "vol" in df.columns and "volume" not in df.columns:
                df["volume"] = df["vol"]
            
            try:
                processed_history = calculate_indicators(df)
                formatted_data.append({
                    "symbol": symbol,
                    "current": content["current"],
                    "history": processed_history,
                    "strategy_path": strategy_path 
                })
            except Exception as e:
                # [3단계 확인] 지표 계산 로직에서 무결성 위반 등으로 탈락하는지 확인
                print(f"❌ INDICATOR FAIL: {symbol} -> {e}")
                continue

    if not formatted_data:
        print("⚠️ ABORT: NO_VALID_DATA")
        return

    # 종목 선정 (자산별 독립 처리)
    selected = []
    for asset_type, strategy_path in asset_configs.items():
        asset_data = [d for d in formatted_data if d["current"]["asset_type"] == asset_type]
        if not asset_data:
            continue
        selected += select_candidates(asset_data, strategy_path)

    for item in selected:
        print(f"✅ SELECTED: {item['symbol']} ({item['current']['asset_type']})")

    # ============================================================
    # 🔥 STATE 자동 갱신 (핵심 연결) - 요청하신 로직 그대로 적용
    # ============================================================
    state_paths = {
        "STOCK": os.path.join(PROJECT_ROOT, "STATE/state_stock.json"),
        "CRYPTO": os.path.join(PROJECT_ROOT, "STATE/state_coin.json")
    }

    for asset_type in asset_configs.keys():
        current_symbols = [
            item["symbol"]
            for item in selected
            if item["current"]["asset_type"] == asset_type
        ]

        state_path = state_paths.get(asset_type)
        # 파일이 없으면 생성하거나 건너뛰도록 보호
        if not state_path or not os.path.exists(state_path):
            print(f"⚠️ STATE FILE NOT FOUND: {state_path}")
            continue

        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        # 핵심: symbols 필드 덮어쓰기 (자산 타입별 분기)
        if asset_type == "STOCK":
            # state.json 구조에 따라 symbols 내부에 저장
            if "symbols" not in state: state["symbols"] = {}
            state["symbols"]["stock"] = current_symbols
            
        elif asset_type == "CRYPTO":
            if "symbols" not in state: state["symbols"] = {}
            state["symbols"]["crypto"] = current_symbols

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        print(f"🔥 STATE UPDATED ({asset_type}): {current_symbols}")

if __name__ == "__main__":
    main()