# ============================================================
# IRONCLAD_V31.22 - Exception Handler (Final Policy Enforcer)
# ============================================================
import yaml
import sys
import logging

# [Standard] 로깅 인터페이스 설정
logger = logging.getLogger("IRONCLAD_RUNTIME.EXCEPTION_HANDLER")

def cancel_all_orders(paths: dict):
    """
    [SAFE_HALT] 종료 전 모든 미체결 주문 취소 시도
    """
    try:
        logger.info("SAFE_HALT: Initiating Cancel-All Orders...")
        # 실제 취소 로직은 order_manager 또는 관련 모듈 연동 필요
    except Exception:
        pass

def handle_critical_error(error_context: str, paths: dict):
    """
    치명적 예외 발생 시 호출:
    1. 모든 주문 취소
    2. 복구 정책(RECOVERY_POLICY) 검증
    3. 정책 위반 확인 시 즉시 종료 (SAFE_HALT)
    """
    logger.critical(f"SAFE_HALT_TRIGGERED: {error_context}")
    
    # 종료 전 최우선 주문 취소
    cancel_all_orders(paths)

    try:
        if not isinstance(paths, dict):
            raise ValueError("INVALID_PATHS_STRUCTURE")

        policy_path = paths.get("RECOVERY_POLICY")
        if not policy_path:
            raise KeyError("RECOVERY_POLICY_PATH_MISSING")

        with open(policy_path, "r", encoding="utf-8") as f:
            policy_data = yaml.safe_load(f)

        # [V31.22] 중첩 구조 명시적 추출 (SSOT 준수)
        policy = policy_data.get("RECOVERY_POLICY", {})
        state_protection = policy.get("state_protection", {})
        failure_policy = policy.get("failure_policy", {})

        # YAML 계층 구조에 따른 필드 매핑
        allow_recovery = state_protection.get("allow_auto_recovery")
        restart_required = failure_policy.get("allow_restart")

        # [Strict Guard] 정책(False/False) 위반 및 유효성 검증
        # 원칙: 시스템에 의한 자동 복구 및 자동 재시작은 절대 금지됨
        if allow_recovery is not False or restart_required is not False:
            raise RuntimeError("RECOVERY_POLICY_VIOLATION: Policy must be strictly FALSE")

        logger.info("POLICY_ENFORCED: Auto-recovery blocked. Safe Halt executed.")
        sys.exit(1)

    except Exception as e:
        # 정책 파일을 읽지 못하거나 구조가 틀린 경우에도 안전을 위해 강제 종료
        logger.error(f"HANDLER_FATAL: Policy unreachable or malformed. {str(e)}")
        sys.exit(1)