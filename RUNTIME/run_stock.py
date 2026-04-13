import os
import json
import yaml
import time
from run import run_pipeline
from status_logger import status_normal, status_warning, status_error

if __name__ == "__main__":
    paths = {}
    no_trade_count = 0
    status_normal("IRONCLAD STOCK ENGINE 시작")

    try:
        strategy_path = "STRATEGY/STOCK"
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

        while True:
            # [수정 1] 중복 출력 제거
            result = run_pipeline(["STOCK"], paths, strategy_path, state_path, evidence_path, state, system_config)

            if result == "NO_TRADE":
                no_trade_count += 1
            else:
                no_trade_count = 0

            # [수정 2] 알림 최적화
            if no_trade_count == 3:
                status_warning(f"STOCK: NO_TRADE 3회 연속 발생 (관찰 필요)")

            time.sleep(1)

    except Exception as e:
        status_error(f"STOCK 치명적 오류: {str(e)}")
        from exception_handler import handle_critical_error
        handle_critical_error(str(e), paths)