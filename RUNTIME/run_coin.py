import os
import json
import yaml
import time
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from RUNTIME.run import run_pipeline
from color_log import log_info, log_warn, log_error

if __name__ == "__main__":
    paths = {}
    no_trade_count = 0
    cycle = 0

    log_info("IRONCLAD COIN ENGINE 시작")

    try:
        strategy_path = "STRATEGY"
        state_path = "STATE/state_coin.json"
        evidence_path = "EVIDENCE/COIN"
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

        access_token = system_config.get("access_token", "NONE")

        while True:
            cycle += 1

            result = run_pipeline(
                ["CRYPTO"],
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
                print(f"\r[COIN] 대기중... 사이클#{cycle}", end="", flush=True)
            else:
                no_trade_count = 0
                log_info(f"[COIN] 사이클#{cycle} 완료: {result}")

            if no_trade_count == 3:
                log_warn("COIN: NO_TRADE 3회 연속 발생")
                no_trade_count = 0

            time.sleep(1)

    except Exception as e:
        log_error(f"치명적 오류 발생: {str(e)}")
