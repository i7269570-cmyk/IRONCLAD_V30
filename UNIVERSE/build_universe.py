# ============================================================
# IRONCLAD_V31.22 - Zero-Tolerance Universe Builder (No-Drop)
# ============================================================
import os
import yaml
import json
import pandas as pd
import yfinance as yf
import ccxt
from typing import List, Dict, Any

# [SSOT] 경로 정의
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(BASE_DIR, "STRATEGY", "selection_rules.yaml")
STOCK_SOURCE_PATH = os.path.join(BASE_DIR, "UNIVERSE", "stock_candidates.csv")
STOCK_OUT = os.path.join(BASE_DIR, "UNIVERSE", "stock_universe.json")
CRYPTO_OUT = os.path.join(BASE_DIR, "UNIVERSE", "crypto_universe.json")

def load_selection_rules() -> Dict[str, Any]:
    """[SSOT] selection_rules.yaml 로드"""
    if not os.path.exists(RULES_PATH):
        raise RuntimeError(f"CONFIG_MISSING: {RULES_PATH}")
    
    with open(RULES_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config["selector_rules"]

def load_stock_universe_source() -> List[str]:
    """
    [V31.22 수정] dropna 제거 및 데이터 계약 강제
    누락 데이터 발견 시 무음 제거 대신 즉시 RuntimeError 발생
    """
    if not os.path.exists(STOCK_SOURCE_PATH):
        raise RuntimeError(f"STOCK_SOURCE_MISSING: {STOCK_SOURCE_PATH}")
    
    df = pd.read_csv(STOCK_SOURCE_PATH)
    
    if "symbol" not in df.columns:
        raise RuntimeError("INVALID_SOURCE_FORMAT: 'symbol' column missing")
    
    # 🔥 [수정] dropna() 제거 -> 결측치 존재 시 즉시 실패 처리
    if df["symbol"].isnull().any():
        raise RuntimeError("UNIVERSE_SOURCE_INVALID: missing symbol detected in source file")
    
    symbols = df["symbol"].unique().tolist()
    
    if not symbols:
        raise RuntimeError("STOCK_SOURCE_EMPTY")
    return symbols

def fetch_and_validate_series(symbol: str, asset_type: str, window_size: int) -> Dict[str, Any]:
    """
    [규격] 시계열 데이터 검증 및 지표 산출
    모든 실패 상황에서 RuntimeError 발생 (자동 보정 금지)
    """
    try:
        if asset_type == "STOCK":
            # [규격] 최소 window_size 이상 데이터 확보 강제
            df = yf.download(symbol, period="1mo", interval="1d", progress=False, auto_adjust=True)
            
            # 🔥 [수정] dropna() 제거 -> 데이터 결손 시 자동 제거 대신 예외 발생 유도
            if df.isnull().values.any():
                raise ValueError(f"DATA_CORRUPTION_DETECTED: {symbol} contains NaN values")
        else:
            exchange = ccxt.binance()
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=window_size + 5)
            df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
            
            if df.isnull().values.any():
                raise ValueError(f"DATA_CORRUPTION_DETECTED: {symbol} contains NaN values")

        if len(df) < window_size:
            raise ValueError(f"INSUFFICIENT_DATA: {symbol} (Len: {len(df)})")

        last = df.iloc[-1]
        prev = df.iloc[-2]

        return {
            "symbol": symbol,
            "price": float(last['close']),
            "value": float(last['close'] * last['volume']),
            "change_rate": float(((last['close'] - prev['close']) / prev['close']) * 100.0)
        }

    except Exception as e:
        raise RuntimeError(f"UNIVERSE_BUILD_ERROR: {symbol} {str(e)}")

def build_universe():
    """
    [V31.22] 100% 무결성 보장 유니버스 빌더
    """
    rules = load_selection_rules()
    u_cfg = rules["universe"]
    weights = rules["weights"]
    top_k = rules["top_k"]

    exchange = ccxt.binance()
    markets = exchange.load_markets()
    crypto_candidates = [s for s in markets if "/USDT" in s]
    stock_candidates = load_stock_universe_source()

    def process_group(candidates: List[str], asset_type: str, limit: int) -> List[str]:
        results = []
        for symbol in candidates:
            data = fetch_and_validate_series(symbol, asset_type, window_size=20)
            results.append(data)

        df = pd.DataFrame(results)
        
        # [규격] 0 대체 없이 가중치 기반 스코어링
        df['score'] = (df['change_rate'] * weights['change_rate'] + 
                       df['value'] * weights['value'])
        
        df = df.sort_values(by='score', ascending=False).head(u_cfg['top_n'])
        return df['symbol'].head(limit).tolist()

    # 하나라도 실패 시 전체 중단
    stock_list = process_group(stock_candidates, "STOCK", top_k["stock"])
    crypto_list = process_group(crypto_candidates, "CRYPTO", top_k["crypto"])

    # [규격] 최종 List[str] JSON 저장
    with open(STOCK_OUT, "w", encoding="utf-8") as f:
        json.dump(stock_list, f, indent=4)
    
    with open(CRYPTO_OUT, "w", encoding="utf-8") as f:
        json.dump(crypto_list, f, indent=4)

    print(f"UNIVERSE_BUILD_SUCCESS: STOCK({len(stock_list)}), CRYPTO({len(crypto_list)})")

if __name__ == "__main__":
    build_universe()