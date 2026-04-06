# RUNTIME/audit_job.py

from state_manager import load_state
from exchange_adapter import get_positions


def compare_state_vs_exchange(state, exchange_positions):
    if "positions" not in state:
        raise RuntimeError("SAFE_HALT: state missing 'positions'")

    state_positions = state["positions"]

    if not isinstance(state_positions, dict):
        raise RuntimeError("SAFE_HALT: state['positions'] must be dict")

    mismatches = []

    for symbol, pos in state_positions.items():
        if not isinstance(pos, dict):
            raise RuntimeError(f"SAFE_HALT: invalid position structure -> {symbol}")

        if "qty" not in pos:
            raise RuntimeError(f"SAFE_HALT: missing qty in state position -> {symbol}")

        state_qty = pos["qty"]

        if symbol not in exchange_positions:
            ex_qty = 0
        else:
            ex_qty = exchange_positions[symbol]

        if abs(state_qty - ex_qty) > 1e-6:
            mismatches.append({
                "symbol": symbol,
                "state_qty": state_qty,
                "exchange_qty": ex_qty
            })

    return mismatches


def run_audit():
    print("=== AUDIT START ===")

    state = load_state()
    exchange_positions = get_positions()

    mismatches = compare_state_vs_exchange(state, exchange_positions)

    if mismatches:
        print("❌ MISMATCH DETECTED")
        for item in mismatches:
            print(item)
        raise RuntimeError("SAFE_HALT: INTEGRITY VIOLATION")

    print("✅ AUDIT PASS")


if __name__ == "__main__":
    run_audit()