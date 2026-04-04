# ============================================================
# IRONCLAD_V31.18 - Multi-Strategy & YAML Logic Integrated
# ============================================================
import sys
import os
import json
import yaml
from typing import Dict, Any, List

# [1] 경로 설정 및 프리플라이트 가드 실행
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)

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
from exception_handler import handle_critical_error
from strategy_loader import load_active_strategies

def run_pipeline(paths: dict, strategy_path: str, state_path: str, evidence_path: str, state: Dict[str, Any], system_config: Dict[str, Any]):
    """
    [V31.18 Pipeline Specification]
    1. Multi-Strategy: 모든 전략의 Entry/Exit 조건을 개별 루프에서 해석
    2. Data Integrity: 필수 필드 누락 시 즉시 중단 (Fail-Fast)
    3. strategy_id SSOT: 포지션 식별 및 청산 로직의 표준 키로 사용
    """
    try:
        # 1. scheduler: 운영 모드 확인
        mode = get_current_mode()
        if mode == "CLOSED":
            save_state(state, state_path)
            return state

        # 2. data_loader & 3. indicator_calc
        asset_types = ["STOCK", "CRYPTO"]
        data_bundle = load_market_data(asset_types, strategy_path)
        
        for symbol in data_bundle:
            data_bundle[symbol]["history"] = calculate_indicators(data_bundle[symbol]["history"])

        # 4. Field Integrity Validation
        selector_input = []
        for symbol, bundle in data_bundle.items():
            current = bundle["current"]
            required_fields = ["price", "asset_type", "change_rate", "value"]
            for field in required_fields:
                if field not in current or current[field] is None:
                    raise RuntimeError(f"MISSING_FIELD: {field} for {symbol}")

            selector_input.append({
                "symbol": symbol, "price": current["price"],
                "asset_type": current["asset_type"], "change_rate": current["change_rate"],
                "value": current["value"]
            })

        # 활성 전략 목록 로드
        spec_path = os.path.join(ROOT, "STRATEGY", "strategy_spec.yaml")
        active_strategies = load_active_strategies(spec_path)

        fill_results = []
        exit_results = {}

        # ------------------------------------------------------------
        # 5~9. ENTRY PIPELINE (멀티 전략 루프)
        # ------------------------------------------------------------
        if mode == "TRADE":
            selected = select_candidates(selector_input, strategy_path)
            regime_ok = evaluate_market_regime(selector_input, strategy_path)
            
            if regime_ok:
                selected_symbols = [item["symbol"] for item in selected if "symbol" in item]
                filtered_bundle = {s: data_bundle[s] for s in selected_symbols if s in data_bundle}
                
                entry_signals = []
                for strat in active_strategies:
                    signals = generate_signals(filtered_bundle, strat["path"], state, system_config)
                    for sig in signals:
                        sig["strategy_id"] = strat["id"]
                    entry_signals.extend(signals)

                candidate_signals = []
                for sig in entry_signals:
                    risk_res = validate_risk_and_size(sig, state, system_config)
                    if risk_res.get("allowed"):
                        sig["volume"] = risk_res["size"]
                        candidate_signals.append(sig)

                if candidate_signals:
                    approved_signals = validate_before_order(candidate_signals, mode, state["positions"], system_config)
                    if approved_signals:
                        order_results = execute_orders(approved_signals)
                        fill_results = track_fills(order_results.get("results", []), state)

        # ------------------------------------------------------------
        # 10. EXIT PIPELINE (전략별 ID 필터링 적용)
        # ------------------------------------------------------------
        if mode in ["TRADE", "NO_ENTRY", "FORCE_EXIT"]:
            exit_list = []
            for strat in active_strategies:
                # [Fix] 각 전략은 본인의 ID에 해당하는 포지션만 청산
                exits = process_exits(data_bundle, state, strat["path"], strat["id"])
                exit_list.extend(exits)
            
            for item in exit_list:
                symbol = item["symbol"]
                if symbol not in exit_results:
                    exit_results[symbol] = item

        # ------------------------------------------------------------
        # 11~13. FINALIZATION
        # ------------------------------------------------------------
        if fill_results or exit_results:
            record_to_ledger({"fills": fill_results, "exits": exit_results}, evidence_path)
            state = reconcile_positions(state, {"entries": fill_results, "exits": exit_results}, state_path)

        save_state(state, state_path)
        return state

    except Exception as e:
        # [Critical] handle_critical_error가 paths["RECOVERY_POLICY"]를 참조함
        handle_critical_error(str(e), paths)
        raise

# ============================================================
# EXECUTION LAYER (Main Entry Point)
# ============================================================
if __name__ == "__main__":
    print("🔥 RUN PIPELINE START")

    # [Standard] 기본 경로 설정 - RECOVERY_POLICY 추가 완료
    paths = {
        "STRATEGY": os.path.join(ROOT, "STRATEGY"),
        "STATE": os.path.join(ROOT, "STATE", "state.json"),
        "EVIDENCE": os.path.join(ROOT, "EVIDENCE"),
        "RECOVERY_POLICY": os.path.join(ROOT, "LOCKED", "recovery_policy.yaml") # 🔥 추가
    }

    # state 로드
    with open(paths["STATE"], "r", encoding="utf-8") as f:
        state = json.load(f)

    # system_config 로드
    with open(os.path.join(ROOT, "LOCKED", "system_config.yaml"), "r", encoding="utf-8") as f:
        system_config = yaml.safe_load(f)

    # 실행
    run_pipeline(
        paths=paths,
        strategy_path=paths["STRATEGY"],
        state_path=paths["STATE"],
        evidence_path=paths["EVIDENCE"],
        state=state,
        system_config=system_config
    )