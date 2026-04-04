import os
import sys
import logging
import yaml
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("IRONCLAD_RUNTIME")

def setup_guard_path(root_path):
    guard_path = os.path.join(root_path, "LOCKED", "GUARDS")
    if guard_path not in sys.path:
        sys.path.append(guard_path)

class IroncladEngine:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.root_path = os.path.dirname(self.base_path)

        self.paths = {
            "LOCKED": os.path.join(self.root_path, "LOCKED"),
            "STRATEGY": os.path.join(self.root_path, "STRATEGY"),
            "STATE": os.path.join(self.root_path, "STATE"),
            "EVIDENCE": os.path.join(self.root_path, "EVIDENCE"),
            "SYSTEM_CONFIG": os.path.join(self.root_path, "LOCKED", "system_config.yaml"),
            "RECOVERY_POLICY": os.path.join(self.root_path, "LOCKED", "recovery_policy.yaml")
        }

        self.system_config = self._load_config()
        setup_guard_path(self.root_path)
        self.current_state = {}

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.paths["SYSTEM_CONFIG"], 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if not config:
                    raise ValueError("EMPTY_CONFIG")
                return config
        except Exception as e:
            raise RuntimeError(f"CONFIG_LOAD_FATAL: {str(e)}")

    def run(self):
        from exception_handler import handle_critical_error
        from preflight_gate import run_preflight_checks
        from state_manager import load_state, save_state
        from scheduler import get_current_mode
        from data_loader import load_market_data
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
        from integrity_guard import IntegrityGuard

        state_file_path = os.path.join(self.paths["STATE"], "state.json")

        evidence_root = os.path.join(self.paths["EVIDENCE"], "incident")
        os.makedirs(evidence_root, exist_ok=True)

        try:
            # PHASE 1
            run_preflight_checks(self.paths)
            self.guard = IntegrityGuard(self.paths["LOCKED"])
            self.guard.check()

            self.current_state = load_state(state_file_path)

            # PHASE 2
            mode = get_current_mode()
            if mode == "CLOSED":
                logger.info("SYSTEM_HALT: Market is closed.")
                return

            # PHASE 3 (Loader → Selector → Entry)
            market_data = load_market_data(["STOCK", "CRYPTO"], self.paths["STRATEGY"])
            candidates = select_candidates(market_data, self.paths["STRATEGY"])

            self.guard.check()

            if evaluate_market_regime(candidates, self.paths["STRATEGY"]):

                if mode == "TRADE":
                    raw_signals = generate_signals(candidates, self.paths["STRATEGY"])

                    approved_signals = []
                    for sig in raw_signals:
                        res = validate_risk_and_size(sig, self.current_state, self.system_config)

                        if res.get("allowed"):
                            sig.update({
                                "volume": res.get("size"),
                                "risk_reason": res.get("reason")
                            })
                            approved_signals.append(sig)

                    final_signals = validate_before_order(
                        approved_signals,
                        mode,
                        self.current_state.get("positions", []),
                        self.system_config
                    )

                    if final_signals:
                        self.guard.check()
                        execution_results = execute_orders(final_signals)

                        # PHASE 4 (Fill → Ledger → State)
                        fills = track_fills(execution_results)

                        if not isinstance(fills, list):
                            raise TypeError("FILL_TRACKER_OUTPUT_INVALID")

                        # ⭐ 순서 고정 (감사 핵심)
                        record_to_ledger(fills, evidence_root)
                        save_state(self.current_state, state_file_path)

            # PHASE 5 (Exit → Reconcile → State)
            exit_results = process_exits(mode, self.current_state, self.paths["STRATEGY"])

            self.current_state = reconcile_positions(
                current_state=self.current_state,
                exit_results=exit_results,
                state_path=state_file_path
            )

            save_state(self.current_state, state_file_path)

            self.guard.check()

            logger.info(
                f"CYCLE_COMPLETE: Mode={mode} | Active Positions: {len(self.current_state.get('positions', []))}"
            )

        except Exception as e:
            logger.error(f"RUNTIME_EXCEPTION: {str(e)}")
            handle_critical_error(str(e), self.paths)


if __name__ == "__main__":
    engine = IroncladEngine()
    engine.run()