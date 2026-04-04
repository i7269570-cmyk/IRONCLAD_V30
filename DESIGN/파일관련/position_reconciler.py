import logging
from datetime import datetime
from typing import Dict, Any
from state_manager import save_state

logger = logging.getLogger("IRONCLAD_RUNTIME.RECONCILER")

def reconcile_positions(current_state: Dict[str, Any], exit_results: Dict[str, Any], state_path: str) -> Dict[str, Any]:
    """
    [FIX] 시그니처 일치: (current_state, exit_results, state_path) 3인자 구성
    [FIX] SSOT 준수: 내부 경로 추론 제거, 주입된 state_path 사용
    """
    updated_positions = current_state.get("positions", []).copy()
    exit_signals = exit_results.get("exit_signals", [])
    exited_symbols = {s["symbol"] for s in exit_signals}
    
    # 1. 청산 반영
    final_positions = [p for p in updated_positions if p["symbol"] not in exited_symbols]
    
    # 2. 내부 상태 갱신
    current_state["positions"] = final_positions
    current_state["last_reconciled"] = datetime.now().isoformat()
    
    # 3. 주입된 SSOT 경로에 저장
    try:
        save_state(current_state, state_path)
        logger.info(f"RECONCILER: State saved to {state_path}")
    except Exception as e:
        raise RuntimeError(f"RECONCILER_SAVE_FAILURE: {str(e)}")

    return current_state