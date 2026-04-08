# ============================================================
# IRONCLAD_V31.23 - Audit Job (Strict Path Signature)
# ============================================================
import os
from state_manager import load_state
from exchange_adapter import get_positions

def compare_state_vs_exchange(state, exchange_positions):
    """상태 파일과 거래소 간 포지션 수량 검증"""
    # 🔴 [V31.23] state_manager에서 보정을 제거했으므로, 여기서 명시적 검증 수행
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

        # 거래소 데이터와 비교
        ex_qty = exchange_positions.get(symbol, 0)

        if abs(state_qty - ex_qty) > 1e-6:
            mismatches.append({
                "symbol": symbol,
                "state_qty": state_qty,
                "exchange_qty": ex_qty
            })

    return mismatches

def run_audit(paths: dict):
    """
    정기 무결성 검사 실행
    - load_state 호출 시 반드시 경로 전달 (규칙 준수)
    """
    print("=== AUDIT START ===")

    # 🔴 [V31.23 핵심] 시그니처 불일치 해결: paths["STATE"] 전달
    # 파일 부재 시 state_manager 내부에서 RuntimeError(SAFE_HALT) 발생
    state = load_state(paths["STATE"])
    exchange_positions = get_positions()

    mismatches = compare_state_vs_exchange(state, exchange_positions)

    if mismatches:
        print("❌ MISMATCH DETECTED")
        for item in mismatches:
            print(item)
        # 데이터 불일치 시 즉시 SAFE_HALT 트리거
        raise RuntimeError("SAFE_HALT: INTEGRITY VIOLATION")

    print("✅ AUDIT PASS")

if __name__ == "__main__":
    # 실행 시 필요한 경로 구조 정의 (run.py와 동일 계층)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = {
        "STATE": os.path.join(BASE_DIR, "STATE", "state.json")
    }
    
    run_audit(paths)