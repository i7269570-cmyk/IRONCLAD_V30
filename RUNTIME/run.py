# ============================================================
# IRONCLAD_V31.19 - Final Integrated Orchestrator (Patched)
# ============================================================
import sys
import os
import json
import yaml
from typing import Dict, Any, List
from datetime import datetime

# [1] 경로 설정 및 프리플라이트 가드 실행
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from LOCKED.GUARDS.preflight_gate import run_preflight
run_preflight()

# [2] Module Imports
from scheduler import get_current_mode
from data_loader import load_market_data
from indicator_calc import calculate_indicators
from selector import select_candidates
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

        # 3. 활성 전략 목록 로드 (ROOT -> BASE_DIR 수정)
        spec_path = os.path.join(BASE_DIR, "STRATEGY", "strategy_spec.yaml")
        
        with open(spec_path, "r", encoding="utf-8") as f:
            active_strategies = yaml.safe_load(f).get("strategies", [])

        fill_results = []
        exit_results = {}

        # ------------------------------------------------------------
        # 4. ENTRY PIPELINE (멀티 전략 루프)
        # ------------------------------------------------------------
        if mode == "TRADE":
            regime_ok = evaluate_market_regime(data_bundle, strategy_path)
            
            if regime_ok:
                entry_signals = []
                for strat in active_strategies:
                    # [V31.19] 경로 생성 로직 수정 (straROOT -> BASE_DIR)
                    abs_strat_path = os.path.join(BASE_DIR, strat["path"])
                    
                    signals = generate_signals(
                        data_bundle, 
                        abs_strat_path, 
                        strat["id"], 
                        state, 
                        system_config
                    )
                    
                    for sig in signals:
                        sig["approved"] = False
                    
                    entry_signals.extend(signals)

                candidate_signals = []
                for sig in entry_signals:
                    risk_res = validate_risk_and_size(sig, state, system_config)
                    if risk_res.get("allowed"):
                        sig["volume"] = risk_res["size"]
                        candidate_signals.append(sig)

                if candidate_signals:
                    validated = validate_before_order(candidate_signals, mode, state["positions"], system_config)
                    
                    for sig in validated:
                        sig["approved"] = True 
                    
                    if validated:
                        order_results = execute_orders(validated)
                        fill_results = track_fills(order_results.get("results", []), state)

        # ------------------------------------------------------------
        # 5. EXIT PIPELINE (전략별 독립 청산)
        # ------------------------------------------------------------
        if mode in ["TRADE", "NO_ENTRY", "FORCE_EXIT"]:
            exit_list = []
            for strat in active_strategies:
                # ROOT -> BASE_DIR 수정
                abs_strat_path = os.path.join(BASE_DIR, strat["path"])
                exits = process_exits(data_bundle, state, abs_strat_path, strat["id"])
                exit_list.extend(exits)
            
            for item in exit_list:
                exit_results[item["symbol"]] = item

        # ------------------------------------------------------------
        # 6. FINALIZATION (포지션 정산 및 저장)
        # ------------------------------------------------------------
        if fill_results or exit_results:
            record_to_ledger({"fills": fill_results, "exits": exit_results}, evidence_path)
            state = reconcile_positions(state, {"entries": fill_results, "exits": exit_results}, state_path)

        save_state(state, state_path)
        return state

    except Exception as e:
        from exception_handler import handle_critical_error
        handle_critical_error(str(e), paths)

# ============================================================
# EXECUTION LAYER
# ============================================================
if __name__ == "__main__":
    # 전역 범위 내 모든 ROOT를 BASE_DIR로 교체 완료
    paths = {
        "STRATEGY": os.path.join(BASE_DIR, "STRATEGY"),
        "STATE": os.path.join(BASE_DIR, "STATE", "state.json"),
        "EVIDENCE": os.path.join(BASE_DIR, "EVIDENCE"),
        "RECOVERY_POLICY": os.path.join(BASE_DIR, "LOCKED", "recovery_policy.yaml")
    }

    # 초기 상태 및 시스템 설정 로드
    with open(paths["STATE"], "r", encoding="utf-8") as f:
        current_state = json.load(f)

    with open(os.path.join(BASE_DIR, "LOCKED", "system_config.yaml"), "r", encoding="utf-8") as f:
        sys_config = yaml.safe_load(f)

    # 파이프라인 가동
    run_pipeline(paths, paths["STRATEGY"], paths["STATE"], paths["EVIDENCE"], current_state, sys_config)