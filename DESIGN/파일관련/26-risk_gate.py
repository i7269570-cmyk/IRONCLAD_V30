import logging
from typing import Dict, Any

logger = logging.getLogger("IRONCLAD_RUNTIME.RISK_GATE")

def validate_risk_and_size(asset_info: Dict[str, Any], current_state: Dict[str, Any], system_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    [FIX] system_config의 max_daily_loss_pct를 참조하여 일일 누적 손실을 차단한다.
    """
    try:
        limits = system_config["risk_limits"]
        
        # 1. 일일 누적 손실 검증 (RISK 해결)
        # state_manager 또는 reconciler에 의해 업데이트된 당일 수익률 참조
        today_pnl = current_state.get("today_pnl_pct", 0.0)
        daily_loss_limit = limits["max_daily_loss_pct"]
        
        if today_pnl <= -(daily_loss_limit):
            logger.critical(f"RISK_GATE: Daily loss limit ({daily_loss_limit}) reached. Blocking all entries.")
            return {"allowed": False, "reason": "DAILY_LOSS_LIMIT_EXCEEDED"}

        # 2. 포지션 수 및 비중 제한 검증
        max_pos = limits["max_positions"]
        current_positions = current_state.get("positions", [])
        
        if len(current_positions) >= max_pos:
            return {"allowed": False, "reason": "MAX_POSITIONS_EXCEEDED"}

        return {
            "allowed": True, 
            "size": limits["max_position_pct"], 
            "reason": "PASS_SAFETY_LIMITS"
        }
    except KeyError as e:
        raise RuntimeError(f"RISK_GATE_CRITICAL: Missing config key {str(e)}")