# ============================================================
# IRONCLAD_V31.21 - Exception Handler (Nested Patch)
# ============================================================
import yaml
import sys
import logging

logger = logging.getLogger("IRONCLAD_RUNTIME.EXCEPTION_HANDLER")

def handle_critical_error(error_context: str, paths: dict):
    logger.critical(f"SAFE_HALT_TRIGGERED: {error_context}")
    
    try:
        policy_path = paths.get("RECOVERY_POLICY")
        with open(policy_path, "r", encoding="utf-8") as f:
            policy_data = yaml.safe_load(f)

        # 중첩 구조 명시적 추출 (SSOT 준수)
        policy = policy_data.get("RECOVERY_POLICY", {})
        state_protection = policy.get("state_protection", {})
        failure_policy = policy.get("failure_policy", {})

        allow_recovery = state_protection.get("allow_auto_recovery")
        restart_required = failure_policy.get("allow_restart")

        if allow_recovery is not False or restart_required is not True:
            raise RuntimeError("RECOVERY_POLICY_VIOLATION")

        logger.info("POLICY_ENFORCED: Auto-recovery blocked. Process terminated.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"HANDLER_FATAL: Policy mapping failure. {str(e)}")
        sys.exit(1)