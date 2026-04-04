# ============================================================
# IRONCLAD_V31.18 - Unified Position Reconciler (Strategy ID Sync)
# ============================================================
import logging
from datetime import datetime
from typing import Dict, Any, List

# [Standard] Logging interface
logger = logging.getLogger("IRONCLAD_RUNTIME.RECONCILER")

def reconcile_positions(current_state: Dict[str, Any], trade_results: Dict[str, Any], state_path: str) -> Dict[str, Any]:
    """
    입력: current_state(dict), trade_results(dict), state_path(str)
    출력: updated_state(dict)
    기능: 
    1. trade_results 내의 'entries'(List)와 'exits'(Dict)를 모두 처리하여 state를 동기화한다.
    2. [V31.18] strategy_name을 폐기하고 strategy_id를 포지션의 핵심 식별자로 사용한다.
    3. 모든 상태 변경(Mutation)은 이 함수를 통해서만 수행되는 단일 경로 원칙을 고수한다.
    """

    # [검증] 필수 데이터 구조 검증
    if not isinstance(trade_results, dict):
        raise RuntimeError("RECONCILER_INPUT_INVALID")
    
    if "entries" not in trade_results:
        raise RuntimeError("MISSING_ENTRIES")
        
    if "exits" not in trade_results:
        raise RuntimeError("MISSING_EXITS")

    # [검증] 포지션 데이터 참조 및 타입 검증
    positions = current_state.get("positions")
    if not isinstance(positions, dict):
        raise RuntimeError("RECONCILER_STATE_CORRUPTION: positions must be a dict")

    # --------------------------------------------------------
    # [1] Entry (fill_results) 처리
    # --------------------------------------------------------
    for fill in trade_results["entries"]:
        if not isinstance(fill, dict):
            raise RuntimeError("RECONCILER_ENTRY_ITEM_INVALID")

        symbol = fill["symbol"]

        # 중복 진입 방지 (데이터 무결성 보호)
        if symbol in positions:
            raise RuntimeError(f"DUPLICATE_ENTRY: {symbol}")

        # [V31.18 핵심 수정] strategy_id 바인딩 및 포지션 생성
        # 🔥 이 시점부터 strategy_id가 state에 각인됨
        positions[symbol] = {
            "symbol": symbol,
            "side": fill["side"],
            "price": fill["price"],
            "asset_type": fill["asset_type"],
            "strategy_id": fill["strategy_id"],   # 🔥 변경: name -> id
            "volume": fill["volume"],
            "entry_price": fill["price"],
            "hold_bars": 0
        }
        logger.info(f"RECONCILER_ENTRY_ADDED: {symbol} (Strategy: {fill['strategy_id']})")

    # --------------------------------------------------------
    # [2] Exit (exit_results) 처리
    # --------------------------------------------------------
    exit_results = trade_results["exits"]
    
    # [V31.18 핵심 수정] 필수 필드 정의 (strategy_id 포함 필수 체크)
    exit_required_fields = ["action", "side", "price", "asset_type", "strategy_id", "volume"]

    for symbol, exit_info in exit_results.items():
        if not isinstance(exit_info, dict):
            raise RuntimeError(f"RECONCILER_EXIT_ITEM_INVALID: {symbol}")

        # 필드 유효성 검증 (ID 누락 시 즉시 차단)
        for f in exit_required_fields:
            if exit_info.get(f) is None:
                raise RuntimeError(f"RECONCILER_EXIT_FIELD_MISSING: {f} for {symbol}")

        # 포지션 존재 여부 검증
        if symbol not in positions:
            raise RuntimeError(f"RECONCILER_POSITION_NOT_FOUND: {symbol}")

        # 최종 제거 (포지션 소멸)
        del positions[symbol]
        logger.info(f"RECONCILER_EXIT_REMOVED: {symbol} (Reason: Strategy Signal)")

    # [업데이트] 내부 상태 데이터 갱신 및 타임스탬프 기록
    current_state["positions"] = positions
    current_state["last_reconciled"] = datetime.now().isoformat()

    # 단일 저장 원칙 준수 (업데이트된 객체만 반환)
    return current_state