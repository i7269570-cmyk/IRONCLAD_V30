# ============================================================
# IRONCLAD_V31.24 - Unified Position Reconciler (Asset Group Sync)
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
    1. trade_results 내의 'entries'(List)와 'exits'(Dict)를 처리하여 state 동기화.
    2. [V31.24] 포지션 생성 시 'asset_group' 필드를 필수 저장하여 계약 일치 보장.
    3. 모든 상태 변경은 이 함수를 통해서만 수행되는 단일 경로 원칙 고수.
    """

    # [검증] 필수 데이터 구조 검증
    if not isinstance(trade_results, dict):
        raise RuntimeError("RECONCILER_INPUT_INVALID")
    
    if "entries" not in trade_results:
        raise RuntimeError("MISSING_ENTRIES")
        
    if "exits" not in trade_results:
        raise RuntimeError("MISSING_EXITS")

    # [검증] 포지션 데이터 참조 및 타입 검증
    # 🔴 [V31.24 수정] .get 제거 및 직접 인덱싱을 통한 엄격 검증
    if "positions" not in current_state:
        raise RuntimeError("RECONCILER_STATE_CORRUPTION: 'positions' key missing in state.")
        
    positions = current_state["positions"]
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

        # 🔴 [V31.24 핵심] asset_group 필드 존재 여부 엄격 검증 (No Default)
        if "asset_group" not in fill or fill["asset_group"] is None:
            raise RuntimeError(f"RECONCILER_ENTRY_FIELD_MISSING: asset_group for {symbol}")

        # [V31.24] 포지션 생성 및 asset_group 각인
        positions[symbol] = {
            "symbol": symbol,
            "side": fill["side"],
            "price": fill["price"],
            "asset_type": fill["asset_type"],
            "asset_group": fill["asset_group"],   # 🔥 변경: 계약 일치를 위한 필드 추가
            "strategy_id": fill["strategy_id"],
            "volume": fill["volume"],
            "entry_price": fill["price"],
            "hold_bars": 0
        }
        logger.info(f"RECONCILER_ENTRY_ADDED: {symbol} (Group: {fill['asset_group']})")

    # --------------------------------------------------------
    # [2] Exit (exit_results) 처리
    # --------------------------------------------------------
    exit_results = trade_results["exits"]
    
    # 필수 필드 정의 (strategy_id 포함 필수 체크)
    exit_required_fields = ["action", "side", "price", "asset_type", "strategy_id", "volume"]

    for symbol, exit_info in exit_results.items():
        if not isinstance(exit_info, dict):
            raise RuntimeError(f"RECONCILER_EXIT_ITEM_INVALID: {symbol}")

        # 필드 유효성 검증 (.get 기본값 금지)
        for f in exit_required_fields:
            if f not in exit_info or exit_info[f] is None:
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

    return current_state