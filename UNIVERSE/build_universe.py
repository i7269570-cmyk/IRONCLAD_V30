import os
import json
import pandas as pd
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# ============================================================
# IRONCLAD_V31.52 - Universe Builder (OHLCV-Based Stock Scoring)
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "UNIVERSE")
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class LSClient:
    """LS증권 공통 클라이언트 (인증 전담)"""
    def __init__(self):
        self.app_key = os.getenv("LS_APP_KEY")
        self.app_secret = os.getenv("LS_APP_SECRET")
        self.base_url = "https://openapi.ls-sec.co.kr:8080"
        self.access_token = self._get_token()

    def _get_token(self):
        url = f"{self.base_url}/oauth2/token"
        params = {"grant_type": "client_credentials", "appkey": self.app_key, "appsecretkey": self.app_secret, "scope": "oob"}
        res = requests.post(url, headers={"content-type": "application/x-www-form-urlencoded"}, data=params)
        return res.json().get("access_token")

class LSStockUniverse:
    """[보안] 전일 OHLCV 기반 거래대금 산출 클래스"""
    def __init__(self, access_token):
        self.base_url = "https://openapi.ls-sec.co.kr:8080"
        self.token = access_token

    def get_all_symbols(self):
        """전체 종목 리스트 수집 (t8436)"""
        url = f"{self.base_url}/stock/master"
        headers = {"authorization": f"Bearer {self.token}", "tr_cd": "t8436"}
        res = requests.post(url, headers=headers, json={})
        data = res.json()
        return [item["shcode"] for item in data.get("t8436OutBlock", [])]

    def fetch_ohlcv(self, symbol):
        """전일 일봉 데이터 수집 및 거래대금 계산 (t8410)"""
        url = f"{self.base_url}/stock/chart"
        headers = {"authorization": f"Bearer {self.token}", "tr_cd": "t8410"}
        body = {"t8410InBlock": {"shcode": symbol, "gubun": "2", "qrycnt": "2"}} # 일봉 2개
        
        try:
            res = requests.post(url, headers=headers, json=body)
            out = res.json().get("t8411OutBlock", res.json().get("t8410OutBlock", [])) # TR 호환성 대응
            if len(out) < 2: return None
            
            prev = out[1] # 전일 데이터 (인덱스 주의: LS API 특성에 따라 조정 가능)
            close = float(prev["close"])
            volume = float(prev["volume"])
            return close * volume # 거래대금 산출
        except:
            return None

def build_stock_universe(access_token):
    client = LSStockUniverse(access_token)
    print("🚀 [STOCK] 전체 종목 수집 및 전일 수급 분석 중...")
    symbols = client.get_all_symbols()
    results = []

    for i, sym in enumerate(symbols):
        try:
            val = client.fetch_ohlcv(sym)
            if val is not None:
                results.append({"symbol": sym, "value": val})
        except: continue
        
        time.sleep(0.05) # API 속도 최적화 (0.2s -> 0.05s 단축 시도)
        if i % 100 == 0:
            print(f"진행: {i}/{len(symbols)} (수급 분석 중)")

    df = pd.DataFrame(results)
    if df.empty: return []
    
    # 🎯 100억 이상 상위 50개 필터링
    return df[df["value"] >= 10000000000].sort_values(by="value", ascending=False).head(50)["symbol"].tolist()

def build_universe():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    # 1. STOCK (OHLCV 전수조사 기반)
    try:
        auth = LSClient()
        stock_list = build_stock_universe(auth.access_token)
        with open(os.path.join(OUTPUT_DIR, "stock_universe.json"), "w", encoding="utf-8") as f:
            json.dump({"symbols": stock_list, "updated_at": str(datetime.now())}, f, indent=4, ensure_ascii=False)
        print(f"✅ STOCK UNIVERSE 완료: {len(stock_list)} 종목 선정 (300억↑)")
    except Exception as e: print(f"❌ STOCK_BUILD_FAIL: {e}")

    # 2. CRYPTO (Upbit KRW 기준)
    try:
        res = requests.get("https://api.upbit.com/v1/market/all")
        krw_markets = [d["market"] for d in res.json() if d["market"].startswith("KRW-")]
        t_res = requests.get(f"https://api.upbit.com/v1/ticker?markets={','.join(krw_markets)}")
        tickers = t_res.json()
        crypto_list = [t['market'] for t in sorted(tickers, key=lambda x: x['acc_trade_price_24h'], reverse=True)[:50]]
        with open(os.path.join(OUTPUT_DIR, "crypto_universe.json"), "w", encoding="utf-8") as f:
            json.dump({"symbols": crypto_list, "updated_at": str(datetime.now())}, f, indent=4)
        print(f"✅ CRYPTO UNIVERSE 완료: {len(crypto_list)} 종목 선정 (Upbit KRW)")
    except Exception as e: print(f"❌ CRYPTO_BUILD_FAIL: {e}")

if __name__ == "__main__":
    build_universe()