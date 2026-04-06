import os
import json
from typing import Dict


def save_state(state: Dict, path: str) -> None:
    """
    atomic write 방식으로 상태 저장
    저장 직전 compact_context를 호출하여 허용된 필드만 필터링 (데이터 계약 준수)
    """
    # 1. 시계열 + 스냅샷 분리: 저장 직전 필터링 수행
    state = compact_context(state)
    
    temp_path = f"{path}.tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, path)

    except Exception as e:
        # ❗ 절대 종료하지 않는다 → 예외만 던진다
        raise RuntimeError(f"State write failed: {str(e)}")


def load_state(path: str) -> Dict:
    """
    상태 파일 로드
    파일 없으면 예외 발생 (조용한 실패 금지)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"State file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        raise RuntimeError(f"State load failed: {str(e)}")


def compact_context(state: dict) -> dict:
    """
    시스템 핵심 스냅샷 필드만 유지.
    지정된 key 외의 런타임 데이터(indicator, temp data 등)는 영구 저장소에서 제외함.
    """
    keys_to_keep = {
        "capital",
        "positions",
        "symbols",
        "date",
        "cooldown",
        "last_reconciled",
        "daily_pnl"
    }

    # 필드 누락 시 자동 보정 금지 원칙 준수 (존재하는 값만 필터링)
    return {k: state[k] for k in state if k in keys_to_keep}