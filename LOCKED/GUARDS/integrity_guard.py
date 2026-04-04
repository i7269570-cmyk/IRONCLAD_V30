import os
import hashlib
from typing import Dict, Set

class IntegrityGuard:
    def __init__(self, locked_path: str):
        self.locked_path = locked_path
        # baseline: 초기화 시점의 파일 목록과 해시값을 SSOT로 저장
        self.baseline_snapshot: Dict[str, str] = self._scan_locked_dir()

    def _calc_hash(self, path: str) -> str:
        """파일의 SHA-256 해시를 계산한다."""
        sha = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    sha.update(chunk)
            return sha.hexdigest()
        except FileNotFoundError:
            return "MISSING"

    def _scan_locked_dir(self) -> Dict[str, str]:
        """LOCKED 하위 파일을 스캔하여 해시 맵을 생성한다 (GUARDS 제외)."""
        snapshot = {}
        for root, dirs, files in os.walk(self.locked_path):
            # 🔥 수정: GUARDS 디렉토리 스캔 제외 및 자기 참조 방지
            if "GUARDS" in dirs:
                dirs.remove("GUARDS")
            
            for f in files:
                # integrity_guard.py 자신은 감시 대상에서 제외
                if f == "integrity_guard.py":
                    continue
                    
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, self.locked_path)
                snapshot[rel_path] = self._calc_hash(full_path)
        return snapshot

    def check(self) -> bool:
        """
        변조(변경, 삭제, 추가) 감지 시 INTEGRITY_FAIL raise.
        """
        current_snapshot = self._scan_locked_dir()

        # 1. 파일 삭제 및 내용 변경 검증
        for rel_path, baseline_hash in self.baseline_snapshot.items():
            if rel_path not in current_snapshot:
                raise RuntimeError(f"INTEGRITY_FAIL: File deleted - {rel_path}")
            
            if current_snapshot[rel_path] != baseline_hash:
                raise RuntimeError(f"INTEGRITY_FAIL: Content modified - {rel_path}")

        # 2. 파일 추가 검증
        for rel_path in current_snapshot:
            if rel_path not in self.baseline_snapshot:
                raise RuntimeError(f"INTEGRITY_FAIL: Unauthorized file added - {rel_path}")

        return True