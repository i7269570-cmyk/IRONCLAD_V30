import os
import re
import yaml # 반드시 설치되어 있어야 함 (pip install pyyaml)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# [원칙 8] 모듈 역할 분리에 따른 검사 예외 대상
ENGINE_FILES = [
    "indicator_calc.py",
    "entry_engine.py",
    "exit_engine.py",
    "data_loader.py",
    "position_reconciler.py"
]

def fail(msg):
    raise RuntimeError(f"[SAFE_HALT] {msg}")

# 1️⃣ 직접 전략 로직 검사 (하드코딩 방지)
def check_runtime_no_direct_strategy_logic():
    runtime_path = os.path.join(ROOT, "RUNTIME")
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
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().lower()

            for pattern in banned_patterns:
                if re.search(pattern, content):
                    fail(f"Direct strategy logic detected in {file}. Use YAML rules instead.")

# 2️⃣ 상태 관리자 보호 (원칙 4)
def check_state_manager_protection():
    runtime_path = os.path.join(ROOT, "RUNTIME")
    for root, _, files in os.walk(runtime_path):
        for file in files:
            if file == "position_reconciler.py" or not file.endswith(".py"):
                continue
            
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if re.search(r'open\(.*state\.json.*\s*,\s*[\'"](w|a|r\+)', content):
                    fail(f"Direct state modification attempt in {file}. Use position_reconciler.")

# 3️⃣ [수정] 시스템 구성 기본 검증 (존재 및 딕셔너리 여부만)
def check_system_config():
    # 경로: LOCKED/system_config.yaml
    config_path = os.path.join(ROOT, "LOCKED", "system_config.yaml")

    if not os.path.exists(config_path):
        fail("system_config.yaml is missing in LOCKED folder.")

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
        except Exception as e:
            fail(f"YAML Parse Error in system_config: {e}")

    # [원칙 적용] 키 이름을 강제하지 않고, '데이터가 유효한 딕셔너리인가'만 확인
    if not isinstance(config, dict):
        fail("system_config.yaml must be a valid dictionary structure.")

    if not config: # 빈 파일 방지
        fail("system_config.yaml is empty. Configuration required.")

# 4️⃣ 전략 폴더 존재 여부 확인
def check_strategy_exists():
    strategy_path = os.path.join(ROOT, "STRATEGY")
    if not os.path.exists(strategy_path) or not os.listdir(strategy_path):
        fail("No strategy files found in STRATEGY folder.")

# 🔥 실행 파이프라인
def run_preflight():
    print("🚀 STARTING PREFLIGHT GATE (Flexible Mode)...")
    
    check_runtime_no_direct_strategy_logic() # 하드코딩 검사
    check_state_manager_protection()        # 상태 보호 검사
    check_system_config()                   # [수정] 유연한 설정 검사
    check_strategy_exists()                 # 전략 존재 확인
    
    print("✅ PREFLIGHT PASS: SYSTEM STRUCTURE VERIFIED")

if __name__ == "__main__":
    run_preflight()