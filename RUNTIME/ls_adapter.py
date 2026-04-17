import requests
import time
from datetime import datetime

class LSAdapter:
    def __init__(self, access_token):
        self.access_token = access_token
        self.stock_url = "https://openapi.ls-sec.co.kr:8080/stock/chart"

    def fetch_ohlcv(self, symbol, window_size):
        # 🔥 코인 분기
        if not symbol.isdigit():
            return self._fetch_crypto(symbol, window_size)

        # 🔥 주식 분기
        return self._fetch_stock(symbol, window_size)

    # -----------------------------
    # 📈 주식 데이터
    # -----------------------------
    def _fetch_stock(self, symbol, window_size):
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "tr_cd": "t8410",
            "tr_cont": "N"
        }

        body = {
            "t8410InBlock": {
                "shcode": symbol,
                "gubun": "2",
                "qrycnt": window_size + 60,  # 🔥 여유 확보
                "sdate": "",
                "edate": datetime.now().strftime("%Y%m%d"),
                "comp_yn": "N"
            }
        }

        time.sleep(0.3)

        res = requests.post(self.stock_url, headers=headers, json=body)

        if res.status_code != 200:
            raise RuntimeError(f"STOCK_API_FAILED: {symbol} -> {res.text}")

        data = res.json()

        if "t8410OutBlock1" not in data:
            raise RuntimeError(f"STOCK_STRUCTURE_ERROR: {symbol} -> {data}")

        return [
            {
                "close": float(d["close"]),
                "volume": float(d.get("jdiff_vol", 0)),
                "high": float(d["high"]),
                "low": float(d["low"])
            }
            for d in data["t8410OutBlock1"]
        ]

    # -----------------------------
    # 🪙 코인 데이터 (Upbit)
    # -----------------------------
    def _fetch_crypto(self, symbol, window_size):
        url = "https://api.upbit.com/v1/candles/minutes/1"

        params = {
            "market": f"KRW-{symbol}",
            "count": window_size + 60
        }

        time.sleep(0.1)

        res = requests.get(url, params=params)

        if res.status_code != 200:
            raise RuntimeError(f"CRYPTO_API_FAILED: {symbol}")

        data = res.json()

        return [
            {
                "close": d["trade_price"],
                "volume": d["candle_acc_trade_volume"],
                "high": d["high_price"],
                "low": d["low_price"]
            }
            for d in data
        ]