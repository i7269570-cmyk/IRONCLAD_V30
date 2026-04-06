# ============================================================
# IRONCLAD_V31.22 - Preflight Gate (Integrated & Unified)
# ============================================================
import os
import sys
import re
import yaml
import logging

# [Standard] 로깅 인터페이스 설정
logger = logging.getLogger("IRONCLAD_RUNTIME.PREFLIGHT")

# [원칙 8] 모듈 역할 분리에 따른 검사 예외 대상
ENGINE_FILES = [
    "indicator_calc.py",
    "entry_engine.py",
    "exit_engine.py",
    "data_loader.py",
    "position_reconciler.py"
]

def fail(msg):
    """실패 시 자동 보정 없이 즉시 중단 (원칙 9 준수)"""
    print(f"[PREFLIGHT_FAIL] {msg}")
    sys.exit(1)

# 1️⃣ 하드코딩 방지: 직접 전략 로직 검사
def check_no_direct_strategy_logic(base_dir):
    runtime_path = os.path.join(base_dir, "RUNTIME")
    if not os.path.exists(runtime_path):
        return

    banned_patterns = [
        r"rsi\s*[<>]=?\s*\d+",
        r"close\s*[<>]=?\s*\d+",
        r"ma\d+\b\s*[<>]=?\s*",
        r"profit\s*[<>]=?\s*0\.\d+"
    ]

    for root, _, files in os.walk(runtime_path):
        for file in files:
            if not file.endswith(".py") or file in ENGINE_FILES:
                continue

            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for pattern in banned_patterns:
                    if re.search(pattern, content):
                        fail(f"Direct strategy logic detected in {file}. Use YAML rules.")
            except Exception:
                continue

# 2️⃣ 상태 관리자 보호 (원칙 4)
def check_state_protection(base_dir):
    runtime_path = os.path.join(base_dir, "RUNTIME")
    if not os.path.exists(runtime_path):
        return

    for root, _, files in os.walk(runtime_path):
        for file in files:
            if file == "position_reconciler.py" or not file.endswith(".py"):
                continue
            
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                if re.search(r'open\(.*state\.json.*\s*,\s*[\'"](w|a|r\+)', f.read()):
                    fail(f"Direct state modification attempt in {file}. Use position_reconciler.")

# 🔥 [V31.22] 무인자 호출 시그니처 고정 및 통합 실행
def run_preflight():
    """
    [Standard] 인자 없이 호출되는 단일 기동 가드.
    경로 검증 및 시스템 구조 무결성을 확인한다.
    """
    print("🚀 STARTING PREFLIGHT GATE (V31.22)...")
    
    try:
        # [V31.22] BASE_DIR 추적 (파일 위치 기준 3단계 상위: LOCKED/GUARDS/preflight.py)
        current_file = os.path.abspath(__file__)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        # 1. 필수 경로 및 파일 존재 검증
        check_list = [
            os.path.join(base_dir, "STRATEGY"),
            os.path.join(base_dir, "STATE", "state.json"),
            os.path.join(base_dir, "LOCKED", "system_config.yaml"),
            os.path.join(base_dir, "LOCKED", "recovery_policy.yaml")
        ]

        for p in check_list:
            if not os.path.exists(p):
                fail(f"Missing essential path: {p}")

        # 2. 기존 정밀 검사 로직 수행
        check_no_direct_strategy_logic(base_dir) # 원칙 6: 하드코딩 검사
        check_state_protection(base_dir)         # 원칙 4: 상태 보호 검사
        
        print("✅ PREFLIGHT PASS: SYSTEM STRUCTURE VERIFIED")
                
    except Exception as e:
        print(f"PREFLIGHT_CRITICAL_ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_preflight()