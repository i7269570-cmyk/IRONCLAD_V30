# ============================================================
# IRONCLAD_V31.20 - Final Integrated Orchestrator (Patched)
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

        # 3. [수정] 활성 전략 목록 로드 및 가드 강화
        spec_path = os.path.join(BASE_DIR, "STRATEGY", "strategy_spec.yaml")
        
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)
            active_strategies = spec.get("active_strategies")
            
        # 가드: active_strategies 키 사용 및 빈 리스트 시 즉시 중단 (원칙 9 준수)
        if not active_strategies:
            raise RuntimeError("NO_ACTIVE_STRATEGIES_DEFINED")

        fill_results = []
        exit_results = {}

        # ------------------------------------------------------------
        # 4. ENTRY PIPELINE (멀티 전략 루프)
        # ------------------------------------------------------------
        if mode == "TRADE":
            # [수정] regime_filter 데이터 계약 준수 (Dict -> List[Dict] 변환)
            history_list = [v["history"] for v in data_bundle.values()]
            regime_ok = evaluate_market_regime(history_list, strategy_path)
            
            if regime_ok:
                entry_signals = []
                for strat in active_strategies:
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

if __name__ == "__main__":
    paths = {
        "STRATEGY": os.path.join(BASE_DIR, "STRATEGY"),
        "STATE": os.path.join(BASE_DIR, "STATE", "state.json"),
        "EVIDENCE": os.path.join(BASE_DIR, "EVIDENCE"),
        "RECOVERY_POLICY": os.path.join(BASE_DIR, "LOCKED", "recovery_policy.yaml")
    }

    with open(paths["STATE"], "r", encoding="utf-8") as f:
        current_state = json.load(f)

    with open(os.path.join(BASE_DIR, "LOCKED", "system_config.yaml"), "r", encoding="utf-8") as f:
        sys_config = yaml.safe_load(f)

    run_pipeline(paths, paths["STRATEGY"], paths["STATE"], paths["EVIDENCE"], current_state, sys_config)