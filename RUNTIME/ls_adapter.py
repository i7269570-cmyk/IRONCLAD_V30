import requests
import time
from datetime import datetime

class LSAdapter:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://openapi.ls-sec.co.kr:8080/stock/chart"

    def fetch_ohlcv(self, symbol, window_size):
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "tr_cd": "t8410", "tr_cont": "N"
        }
        body = {
            "t8410InBlock": {
                "shcode": symbol, "gubun": "2",
                "qrycnt": window_size, "sdate": "", 
                "edate": datetime.now().strftime("%Y%m%d"),
                "comp_yn": "N"
            }
        }
        
        time.sleep(0.3)
        res = requests.post(self.base_url, headers=headers, json=body)
        
        if res.status_code != 200:
            raise RuntimeError(f"API_CALL_FAILED: {symbol} -> {res.text}")
            
        response_json = res.json()
        if "t8410OutBlock1" not in response_json:
            raise RuntimeError(f"API_RESPONSE_STRUCTURE_ERROR: {symbol} -> {response_json}")
            
        return response_json["t8410OutBlock1"]