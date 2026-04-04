import os
import json
from typing import Dict


def save_state(state: Dict, path: str) -> None:
    """
    atomic write 방식으로 상태 저장
    temp → write → flush → fsync → replace
    """
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