# ============================================================
# IRONCLAD_V31.22 - Final Integrated Orchestrator (Patched)
# ============================================================
import sys
import os
import json
import yaml
from typing import Dict, Any, List

# [1] 경로 설정 및 프리플라이트 가드 실행
# 구조: PROJECT_ROOT/RUNTIME/run.py 기준 상위 1단계가 PROJECT_ROOT
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# [V31.22] 시그니처가 통일된 무인자(No-arg) 프리플라이트 가드 호출
from LOCKED.GUARDS.preflight_gate import run_preflight
run_preflight()

# [2] Module Imports
from scheduler import get_current_mode
from data_loader import load_market_data
from indicator_calc import calculate_indicators
from regime_filter import evaluate_market_regime
from entry_engine import generate_signals
from risk_gate import validate_risk_and_size
from pre_order_check import validate_before_order
from order_manager import execute_orders
from fill_tracker import track_fills
from ledger_writer import record_to_ledger
from exit_engine import process_exits
from position_reconciler import reconcile_positions
from state_manager import save_state

def run_pipeline(paths: dict, strategy_path: str, state_path: str, evidence_path: str, state: Dict[str, Any], system_config: Dict[str, Any]):
    try:
        # 1. 운영 모드 확인
        mode = get_current_mode()
        if mode == "CLOSED":
            save_state(state, state_path)
            return state

        # 2. 데이터 로드 및 지표 계산
        asset_types = ["STOCK", "CRYPTO"]
        data_bundle = load_market_data(asset_types, strategy_path)
        for symbol in data_bundle:
            data_bundle[symbol]["history"] = calculate_indicators(data_bundle[symbol]["history"])

        # 3. [Strict Guard] 활성 전략 로드 및 검증 (원칙 9 준수)
        spec_path = os.path.join(BASE_DIR, "STRATEGY", "strategy_spec.yaml")
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)
            active_strategies = spec.get("active_strategies")
        
        if not active_strategies: 
            raise RuntimeError("NO_ACTIVE_STRATEGIES_DEFINED")

        fill_results, exit_results = [], {}

        # ------------------------------------------------------------
        # 4. ENTRY PIPELINE (시장 판단 -> 전략 루프 -> 리스크 검증 -> 실행)
        # ------------------------------------------------------------
        if mode == "TRADE":
            # [Contract Fix] regime_filter용 스냅샷 리스트 생성 (Dict 리스트)
            market_data = []
            for v in data_bundle.values():
                current = v.get("current")
                if not isinstance(current, dict):
                    raise RuntimeError("REGIME_DATA_STRUCTURE_ERROR")
                market_data.append(current)

            # 판단(Regime) 단계: 스냅샷 데이터 사용
            if evaluate_market_regime(market_data, strategy_path):
                entry_signals = []
                for strat in active_strategies:
                    # 실행(Entry) 단계: 시계열 포함 data_bundle 사용
                    signals = generate_signals(
                        data_bundle, 
                        os.path.join(BASE_DIR, strat["path"]), 
                        strat["id"], 
                        state, 
                        system_config
                    )
                    entry_signals.extend(signals)

                candidate_signals = []
                for sig in entry_signals:
                    risk_res = validate_risk_and_size(sig, state, system_config)
                    if risk_res.get("allowed"):
                        sig.update({"volume": risk_res["size"], "approved": True})
                        candidate_signals.append(sig)

                if candidate_signals:
                    validated = validate_before_order(candidate_signals, mode, state["positions"], system_config)
                    if validated:
                        order_results = execute_orders(validated)
                        fill_results = track_fills(order_results.get("results", []), state)

        # ------------------------------------------------------------
        # 5. EXIT PIPELINE (청산 로직 실행)
        # ------------------------------------------------------------
        if mode in ["TRADE", "NO_ENTRY", "FORCE_EXIT"]:
            exit_list = []
            for strat in active_strategies:
                exits = process_exits(data_bundle, state, os.path.join(BASE_DIR, strat["path"]), strat["id"])
                exit_list.extend(exits)
            for item in exit_list: 
                exit_results[item["symbol"]] = item

        # ------------------------------------------------------------
        # 6. FINALIZATION (원자적 원장 기록 및 상태 갱신)
        # ------------------------------------------------------------
        if fill_results or exit_results:
            record_to_ledger({"fills": fill_results, "exits": exit_results}, evidence_path)
            state = reconcile_positions(state, {"entries": fill_results, "exits": exit_results}, state_path)

        save_state(state, state_path)
        return state

    except Exception as e:
        # [V31.22] 예외 발생 시 전파된 에러를 핸들러로 전달 (SAFE_HALT 실행)
        from exception_handler import handle_critical_error
        handle_critical_error(str(e), paths)

if __name__ == "__main__":
    # [V31.22 수정] 하위 모듈이 필요로 하는 모든 필수 경로 보강
    paths = {
        "STRATEGY": os.path.join(BASE_DIR, "STRATEGY"),
        "STATE": os.path.join(BASE_DIR, "STATE", "state.json"),
        "EVIDENCE": os.path.join(BASE_DIR, "EVIDENCE"),
        "RECOVERY_POLICY": os.path.join(BASE_DIR, "LOCKED", "recovery_policy.yaml"),
        "LOCKED": os.path.join(BASE_DIR, "LOCKED") # 핸들러 정책 파싱용 필수 경로
    }

    # 초기 상태 로드 및 설정 로드
    if not os.path.exists(paths["STATE"]):
        print(f"CRITICAL: State file not found at {paths['STATE']}")
        sys.exit(1)

    with open(paths["STATE"], "r", encoding="utf-8") as f:
        current_state = json.load(f)

    config_path = os.path.join(BASE_DIR, "LOCKED", "system_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        sys_config = yaml.safe_load(f)

    # 파이프라인 가동
    run_pipeline(paths, paths["STRATEGY"], paths["STATE"], paths["EVIDENCE"], current_state, sys_config)