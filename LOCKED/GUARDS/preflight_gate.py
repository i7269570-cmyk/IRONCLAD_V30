# ============================================================
# IRONCLAD_V31.44 - Preflight Gate (Split-State & Regex Fix)
# ============================================================
import os
import sys
import re
import yaml
import logging

logger = logging.getLogger("IRONCLAD_RUNTIME.PREFLIGHT")

ENGINE_FILES = [
    "indicator_calc.py",
    "entry_engine.py",
    "exit_engine.py",
    "data_loader.py",
    "position_reconciler.py",
    "run_stock.py",
    "run_coin.py",
    "exception_handler.py"
]

def fail(msg):
    print(f"[PREFLIGHT_FAIL] {msg}")
    sys.exit(1)

def check_no_direct_strategy_logic(base_dir):
    runtime_path = os.path.join(base_dir, "RUNTIME")
    if not os.path.exists(runtime_path): return

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

def check_state_protection(base_dir):
    runtime_path = os.path.join(base_dir, "RUNTIME")
    if not os.path.exists(runtime_path): return

    for root, _, files in os.walk(runtime_path):
        for file in files:
            if file in ENGINE_FILES or not file.endswith(".py"):
                continue

            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if re.search(r'open\(.*state(_\w+)?\.json.*\s*,\s*[\'"](w|a|r\+)', content):
                    fail(f"Direct state modification attempt in {file}. Use position_reconciler.")
            except Exception:
                continue

def run_preflight():
    try:
        current_file = os.path.abspath(__file__)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

        check_list = [
            os.path.join(base_dir, "STRATEGY"),
            os.path.join(base_dir, "STATE", "state_stock.json"),
            os.path.join(base_dir, "STATE", "state_coin.json"),
            os.path.join(base_dir, "LOCKED", "system_config.yaml"),
            os.path.join(base_dir, "LOCKED", "recovery_policy.yaml")
        ]

        for p in check_list:
            if not os.path.exists(p):
                fail(f"Missing essential path: {p}")

        check_no_direct_strategy_logic(base_dir)
        check_state_protection(base_dir)

    except Exception as e:
        print(f"PREFLIGHT_CRITICAL_ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_preflight()
