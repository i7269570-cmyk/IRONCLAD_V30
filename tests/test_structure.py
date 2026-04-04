import os

ROOT = os.path.dirname(os.path.dirname(__file__))


def test_no_strategy_in_runtime():
    runtime_path = os.path.join(ROOT, "RUNTIME")

    banned = ["rsi <", "bb_", "ma20 <", "ma20 >"]

    EXCLUDE_FILES = [
        "indicator_calc.py",
        "entry_engine.py",
        "exit_engine.py"
    ]

    for root, _, files in os.walk(runtime_path):
        for file in files:
            if not file.endswith(".py") or file in EXCLUDE_FILES:
                continue

            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                content = f.read().lower()
                for b in banned:
                    assert b not in content, f"Strategy logic in {file}"


def test_state_file_exists():
    state_path = os.path.join(ROOT, "STATE", "state.json")
    assert os.path.exists(state_path), "state.json missing"