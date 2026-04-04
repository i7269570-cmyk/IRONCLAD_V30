import yaml
import sys
import logging

logger = logging.getLogger("IRONCLAD_RUNTIME.EXCEPTION_HANDLER")


def cancel_all_orders(paths: dict):
    """
    [SAFE_HALT] 모든 미체결 주문 취소 수행 위치.
    실제 API 호출 없이 구조적 위치만 확보한다.
    """
    try:
        # 주문 취소 로직 실행 위치 (Placeholder)
        logger.info("SAFE_HALT: Initiating Cancel-All Orders...")
    except Exception:
        # 취소 실패 시에도 SAFE_HALT 프로세스는 계속 진행되어야 함
        pass


def handle_critical_error(error_context: str, paths: dict):
    """
    치명적 예외 발생 시 모든 주문을 취소하고 recovery_policy를 확인한 뒤
    안전하게 종료(SAFE_HALT)한다.
    """
    logger.critical(f"SAFE_HALT_TRIGGERED: {error_context}")

    # [수정] 종료 전 최우선적으로 모든 주문 취소 시도
    cancel_all_orders(paths)

    try:
        if not isinstance(paths, dict):
            raise ValueError("INVALID_PATHS")

        policy_path = paths.get("RECOVERY_POLICY")
        if not policy_path:
            raise KeyError("RECOVERY_POLICY")

        with open(policy_path, "r", encoding="utf-8") as f:
            policy_data = yaml.safe_load(f)

        if not isinstance(policy_data, dict):
            raise ValueError("EMPTY_POLICY_FILE")

        # recovery_policy.yaml 최종 구조와 일치
        policy = policy_data.get("RECOVERY_POLICY", {})
        if not isinstance(policy, dict):
            raise ValueError("INVALID_POLICY_SECTION")

        # [수정] recovery_policy 강제 및 비정상 정책 차단 검증
        allow_recovery = policy.get("allow_recovery")
        restart_required = policy.get("restart_required")

        # 정책 위반 및 부적절한 설정 강제 차단 (RuntimeError 발생)
        if allow_recovery is True:
            raise RuntimeError("RECOVERY_POLICY_VIOLATION")

        if restart_required is not True:
            raise RuntimeError("RECOVERY_POLICY_INVALID")

        # 정책 값이 정상일 경우 (False/True) 안전하게 종료
        if allow_recovery is False and restart_required is True:
            logger.info("POLICY_ENFORCED: Auto-recovery disabled. Process terminated.")
            sys.exit(1)

        # 그 외 모든 정책 상황에서도 안전하게 프로세스 종료
        logger.info("POLICY_ENFORCED: Process terminated.")
        sys.exit(1)

    except Exception as e:
        # RuntimeError 포함 모든 예외 발생 시 최종 중단
        logger.error(f"HANDLER_FATAL: Recovery policy unreachable or malformed. {str(e)}")
        sys.exit(1)