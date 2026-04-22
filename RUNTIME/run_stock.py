import os
from dotenv import load_dotenv
from color_log import log_info, log_warn, log_error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import sys
sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

import json
import yaml
import time
import requests

from run import run_pipeline
from ls_adapter import LSAdapter

if __name__ == "__main__":
    paths = {}
    no_trade_count = 0
    cycle = 0

    log_info("IRONCLAD STOCK ENGINE 시작")

    try:
        strategy_path = "STRATEGY"
        state_path = "STATE/state_stock.json"
        evidence_path = "EVIDENCE/STOCK"
        os.makedirs(evidence_path, exist_ok=True)

        paths = {
            "STRATEGY": strategy_path,
            "STATE": state_path,
            "EVIDENCE": evidence_path,
            "RECOVERY_POLICY": "LOCKED/recovery_policy.yaml"
        }

        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        with open("LOCKED/system_config.yaml", "r", encoding="utf-8") as f:
            system_config = yaml.safe_load(f)

        app_key = os.getenv("LS_APP_KEY")
        app_secret = os.getenv("LS_APP_SECRET")

        if not app_key or not app_secret:
            raise RuntimeError("API_KEY_MISSING")

        url = "https://openapi.ls-sec.co.kr:8080/oauth2/token"
        headers = {"content-type": "application/x-www-form-urlencoded"}

        body = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "appsecretkey": app_secret,
            "scope": "oob"
        }

        res = requests.post(url, data=body, headers=headers)

        if res.status_code != 200:
            raise RuntimeError(f"TOKEN_REQUEST_FAILED: {res.text}")

        access_token = res.json().get("access_token")

        if not access_token:
            raise RuntimeError("ACCESS_TOKEN_GENERATION_FAILED")

        if "asset_type" not in state:
            state["asset_type"] = "STOCK"

        # 실행 루프
        while True:
            cycle += 1

            if "symbols" in state and "stock" in state["symbols"]:
                state["asset_type"] = "STOCK"

            result = run_pipeline(
                ["STOCK"],
                paths,
                strategy_path,
                state_path,
                evidence_path,
                state,
                system_config,
                access_token
            )

            if result == "NO_TRADE":
                no_trade_count += 1
                print(f"\r[STOCK] 대기중... 사이클#{cycle}", end="", flush=True)
            else:
                no_trade_count = 0
                log_info(f"[STOCK] 사이클#{cycle} 완료: {result}")

            if no_trade_count == 3:
                log_warn("STOCK: NO_TRADE 3회 연속 발생")
                no_trade_count = 0

            time.sleep(1)

    except Exception as e:
        log_error(f"STOCK 치명적 오류: {str(e)}")
