import requests
import pandas as pd
import time

class UpbitAdapter:
    """
    [IRONCLAD_V31] 업비트 전용 데이터 어댑터
    Single Source of Truth: Upbit KRW Market
    """
    def __init__(self):
        self.base_url = "https://api.upbit.com/v1"

    def fetch_ohlcv(self, symbol, window_size=200):
        """
        업비트 분봉(1분봉) 데이터를 가져와 공통 규격으로 반환
        """
        # 심볼 정규화 (예: BTC -> KRW-BTC)
        if not symbol.startswith("KRW-"):
            market = f"KRW-{symbol}"
        else:
            market = symbol

        url = f"{self.base_url}/candles/minutes/1"
        params = {
            "market": market,
            "count": window_size
        }

        try:
            res = requests.get(url, params=params, timeout=5)
            if res.status_code != 200:
                return None
            
            data = res.json()
            
            # 업비트 데이터를 엔진 공통 규격으로 매핑
            processed = []
            for d in reversed(data): # 과거 -> 현재 순서로 정렬
                processed.append({
                    "open": d["opening_price"],
                    "high": d["high_price"],
                    "low": d["low_price"],
                    "close": d["trade_price"],
                    "volume": d["candle_acc_trade_volume"],
                    "jvol": d["candle_acc_trade_volume"], # 필드 호환성 유지
                    "timestamp": d["candle_date_time_kst"],
                     "asset_type": "CRYPTO" 
                })
            return processed
            
        except Exception as e:
            print(f"⚠️ UPBIT_ADAPTER_ERROR [{symbol}]: {e}")
            return None