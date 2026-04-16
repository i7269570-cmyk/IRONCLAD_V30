import os
import json
import yaml
import time
from RUNTIME.run import run_pipeline
from .status_logger import status_normal, status_warning, status_error

# [1] 전역 변수 추가 (체결 추적용)
last_order_symbol = None

if __name__ == "__main__":
    paths = {}
    no_trade_count = 0
    status_normal("IRONCLAD COIN ENGINE 시작")

    try:
        strategy_path = "STRATEGY/COIN"
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

        while True:
            # [2] 체결 이상 감지 (루프 시작 시 직전 주문 검증)
            if last_order_symbol:
                if last_order_symbol not in state.get("positions", {}):
                    status_error(f"FILL_FAIL_DETECTED: {last_order_symbol}")

            # [수정 1] 불필요한 중복 print 제거 및 파이프라인 실행
            result = run_pipeline(["CRYPTO"], paths, strategy_path, state_path, evidence_path, state, system_config)

            if result == "NO_TRADE":
                no_trade_count += 1
            else:
                no_trade_count = 0

            # [3] 성공 결과 처리 및 마지막 주문 심볼 갱신
            if result == "SUCCESS":
                if state.get("positions"):
                    last_order_symbol = list(state["positions"].keys())[0]

            # [수정 2] '==' 연산자로 로그 폭발 방지 (딱 3회차에 1번만 경고)
            if no_trade_count == 3:
                status_warning(f"COIN: NO_TRADE 3회 연속 발생 (관찰 필요)")

            time.sleep(1)

    except Exception as e:
        status_error(f"COIN 치명적 오류: {str(e)}")
        from exception_handler import handle_critical_error
        handle_critical_error(str(e), paths)