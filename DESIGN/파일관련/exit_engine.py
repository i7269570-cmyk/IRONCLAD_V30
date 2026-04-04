import os
import yaml
import logging
from typing import List, Dict, Any

logger = logging.getLogger("IRONCLAD_RUNTIME.EXIT_ENGINE")

def process_exits(mode: str, current_state: Dict[str, Any], strategy_path: str) -> Dict[str, Any]:
    """
    보유 포지션을 전수 검사하여 청산 신호를 생성한다.
    [FIX] 감사 추적을 위해 asset_type 및 reason 필드를 강제 포함한다.
    """
    positions = current_state.get("positions", [])
    exit_signals = []
    
    if not positions:
        return {"exit_signals": []}

    try:
        rules_path = os.path.join(strategy_path, "exit_rules.yaml")
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
            tp_limit = rules["take_profit"] # [RISK 해결] 기본값 없음
            sl_limit = rules["stop_loss"]
    except Exception as e:
        raise RuntimeError(f"EXIT_CONFIG_FATAL: {str(e)}")

    for pos in positions:
        # 수익률 계산
        entry_price = pos["price"]
        current_price = pos.get("current_price", entry_price)
        pnl_rate = (current_price - entry_price) / entry_price if entry_price > 0 else 0

        should_exit = False
        reason = ""

        if mode == "FORCE_EXIT":
            should_exit, reason = True, "FORCE_EXIT_TIME_REACHED"
        elif pnl_rate >= tp_limit:
            should_exit, reason = True, f"TAKE_PROFIT_TRIGGERED({pnl_rate:.2%})"
        elif pnl_rate <= sl_limit:
            should_exit, reason = True, f"STOP_LOSS_TRIGGERED({pnl_rate:.2%})"

        if should_exit:
            # [FIX] 컨텍스트 유지: 원본 포지션의 모든 정보와 청산 사유 병합
            exit_signals.append({
                **pos, 
                "side": "SELL",
                "reason": reason,
                "asset_type": pos.get("asset_type") # [RISK 해결] 자산군 정보 유지
            })
            logger.info(f"EXIT_SIGNAL: {pos['symbol']} | Reason: {reason}")

    return {"exit_signals": exit_signals}