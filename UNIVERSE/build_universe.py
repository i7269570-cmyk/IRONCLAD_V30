import os
import yaml
import json
import logging
import pandas as pd
import ccxt
import requests
from datetime import datetime

# ============================================================
# IRONCLAD_V28.1 - Universe Builder (Standard Mapping Fixed)
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "UNIVERSE")
STRATEGY_DIR = os.path.join(PROJECT_ROOT, "STRATEGY")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "LOCKED", "system_config.yaml")

class LSClient:
    """LS증권 OpenAPI 기반 종목 데이터 수집 클라이언트"""
    def __init__(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        self.app_key = config["ls_api"]["app_key"]
        self.app_secret = config["ls_api"]["app_secret"]
        self.base_url = "https://openapi.ls-sec.co.kr:8080"
        self.access_token = self._get_token()

    def _get_token(self):
        url = f"{self.base_url}/oauth2/token"
        headers = {"content-type": "application/x-www-form-urlencoded"}
        params = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "scope": "oob"
        }
        res = requests.post(url, headers=headers, data=params)
        if res.status_code == 200:
            return res.json()["access_token"]
        raise RuntimeError(f"LS_API_AUTH_FAILED: {res.text}")

    def get_stock_list(self):
        """KOSPI(0) + KOSDAQ(1) 전종목 리스트 수집 (t8436)"""
        url = f"{self.base_url}/stock/etc" 
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "tr_cd": "t8436",
            "tr_cont": "N"
        }
        
        all_stocks = []
        for gubun in ["0", "1"]: 
            body = {"t8436InBlock": {"gubun": gubun}}
            res = requests.post(url, headers=headers, json=body)
            if res.status_code == 200:
                # t8436 응답: shcode(단축코드), hname(종목명), expcode(표준코드) 등
                all_stocks.extend(res.json()["t8436OutBlock"])
        return all_stocks

    def get_market_data(self, stocks):
        """LS API 실제 필드 매핑 (amt: 거래대금)"""
        processed_data = []
        # 실제 환경에서는 t1102(주식현재가호가) 또는 t8407(주식멀티조회) 활용
        # 본 코드에서는 LS API 필드 명세에 따라 'amt'(백만단위)를 'value'로 매핑
        for s in stocks:
            try:
                # 'amt'는 LS증권 API에서 주로 사용하는 거래대금 필드명 (백만원 단위)
                raw_value = float(s.get("amt", s.get("value", 0))) 
                processed_data.append({
                    "symbol": s["shcode"],
                    "name": s["hname"],
                    "price": float(s.get("price", 0)),
                    "value": raw_value * 1000000, # 원 단위 변환
                    "change_rate": float(s.get("diff", 0)) # 등락률
                })
            except:
                continue
        return processed_data

def get_stock_candidates():
    client = LSClient()
    raw_list = client.get_stock_list()
    if not raw_list:
        raise RuntimeError("LS_API_RETURNED_EMPTY_LIST")
    return client.get_market_data(raw_list)

def filter_universe(asset_type: str, candidates: list) -> list:
    df = pd.DataFrame(candidates)
    if df.empty:
        return []

    # [수정 1] SSOT 준수: system_config에서 직접 min_value 참조
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        system_config = yaml.safe_load(f)
    
    # execution_constraints -> liquidity -> min_value (300억)
    try:
        min_value = system_config["execution_constraints"]["liquidity"]["min_value"]
    except KeyError:
        min_value = 30000000000 # 최후의 방어선

    # 1. 거래대금 필터링
    df = df[df['value'] >= min_value]
    if df.empty:
        return []

    # [수정 2] Universe Limit 고정 (50개)
    # selector_rules의 top_n과 혼동 방지를 위해 하드코딩 또는 명시적 상수 사용
    limit = 50 

    # 2. 거래대금 상위 정렬 및 추출
    df = df.sort_values(by="value", ascending=False)
    universe = df['symbol'].head(limit).tolist()
    
    # [수정 3] 예외 처리 강화
    if asset_type == "STOCK" and len(universe) < 50:
        logging.warning(f"STOCK_UNIVERSE_INCOMPLETE: {len(universe)} symbols found.")
        # 50개 미만 시 에러를 던져 파이프라인 중단 (요구사항 준수)
        raise RuntimeError(f"SAFE_HALT: Universe count {len(universe)} is under 50.")
        
    return universe

def build_universe():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 1. STOCK
    try:
        stock_candidates = get_stock_candidates()
        stock_universe = filter_universe("STOCK", stock_candidates)
        
        output = {
            "symbols": stock_universe, 
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "LS_OPEN_API"
        }
        with open(os.path.join(OUTPUT_DIR, "stock_universe.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4)
        print(f"✅ STOCK UNIVERSE: {len(stock_universe)} symbols (Min Value: 300억)")
    except Exception as e:
        raise RuntimeError(f"STOCK_BUILD_CRITICAL: {str(e)}")

    # 2. CRYPTO (기존 로직 유지)
    try:
        exchange = ccxt.binance()
        ticker_data = exchange.fetch_tickers()
        crypto_candidates = []
        for symbol, ticker in ticker_data.items():
            if symbol.endswith('/USDT'):
                crypto_candidates.append({
                    'symbol': symbol,
                    'value': ticker.get('quoteVolume', 0),
                    'change_rate': ticker.get('percentage', 0)
                })
        crypto_universe = filter_universe("CRYPTO", crypto_candidates)
        
        with open(os.path.join(OUTPUT_DIR, "crypto_universe.json"), "w", encoding="utf-8") as f:
            json.dump({"symbols": crypto_universe, "updated_at": str(datetime.now())}, f, indent=4)
        print(f"✅ CRYPTO UNIVERSE: {len(crypto_universe)} symbols")
    except Exception as e:
        print(f"❌ CRYPTO_BUILD_FAILED: {e}")

if __name__ == "__main__":
    build_universe()