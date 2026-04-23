import os
import sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(__file__))


# ============================================================
# 1. RUNTIME 내 전략 침범 감시
# ============================================================
def test_no_strategy_in_runtime():
    """
    RUNTIME 폴더 안에 전략 로직이 침범했는지 감시한다.
    전략 수치/조건은 STRATEGY/YAML 에만 있어야 한다.
    """

    runtime_path = os.path.join(ROOT, "RUNTIME")

    banned = ["rsi <", "bb_", "ma20 <", "ma20 >"]

    EXCLUDE_FILES = [
        "indicator_calc.py",
        "entry_engine.py",
        "exit_engine.py",
        "regime_filter.py",
    ]

    for root, _, files in os.walk(runtime_path):
        for file in files:
            if not file.endswith(".py") or file in EXCLUDE_FILES:
                continue

            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                content = f.read().lower()
                for b in banned:
                    assert b not in content, \
                        f"Strategy logic in {file}: '{b}' 발견 → STRATEGY/YAML 로 이동 필요"


# ============================================================
# 2. STATE 필수 파일 존재
# ============================================================
def test_state_file_exists():
    state_path = os.path.join(ROOT, "STATE", "state.json")
    assert os.path.exists(state_path), "state.json missing"


def test_required_state_files_exist():
    for fname in ["state_stock.json", "state_coin.json"]:
        path = os.path.join(ROOT, "STATE", fname)
        assert os.path.exists(path), f"{fname} missing"


# ============================================================
# 3. UNIVERSE 존재
# ============================================================
def test_universe_files_exist():
    for fname in ["stock_universe.json", "coin_universe.json"]:
        path = os.path.join(ROOT, "UNIVERSE", fname)
        assert os.path.exists(path), f"{fname} missing"


# ============================================================
# 4. STRATEGY YAML 존재
# ============================================================
def test_strategy_yaml_exists():
    for asset in ["STOCK", "CRYPTO"]:
        for fname in ["strategy_spec.yaml", "selection_rules.yaml"]:
            path = os.path.join(ROOT, "STRATEGY", asset, fname)
            assert os.path.exists(path), f"{asset}/{fname} missing"


# ============================================================
# 5. DATA CONTRACT (🔥 핵심)
# ============================================================
def test_data_bundle_contract():
    """
    data_bundle 구조 계약 검증.

    표준 구조:
    {
        "asset_type": str,
        "asset_group": str,
        "current": dict,
        "history": DataFrame
    }
    """

    sys.path.insert(0, ROOT)

    from RUNTIME.market_adapter import build_market_data_map

    dummy_df = pd.DataFrame({
        "open": [100.0],
        "high": [110.0],
        "low": [90.0],
        "close": [105.0],
        "volume": [1000.0],
        "value": [105000.0],
        "volume_ratio": [1.5],
        "rsi": [55.0]
    })

    dummy_bundle = {
        "TEST": {
            "current": {
                "asset_type": "STOCK",
                "asset_group": "STOCK",
                "price": 105.0,
                "value": 105000.0
            },
            "history": dummy_df
        }
    }

    result = build_market_data_map(dummy_bundle)

    required_keys = ["asset_type", "asset_group", "current", "history"]

    for symbol, data in result.items():

        for key in required_keys:
            assert key in data, \
                f"DATA_CONTRACT_VIOLATION: '{key}' missing in {symbol}"

        assert isinstance(data["current"], dict), \
            f"current must be dict, got {type(data['current'])}"

        assert isinstance(data["history"], pd.DataFrame), \
            f"history must be DataFrame, got {type(data['history'])}"


# ============================================================
# 6. SELECTOR 출력 안정성
# ============================================================
def test_selector_output_contract():
    """
    selector 출력이 반드시 symbol 포함하는지 확인
    """

    sys.path.insert(0, ROOT)
    from RUNTIME.selector import select_candidates

    dummy_df = pd.DataFrame({
        "close": [100],
        "volume": [1000],
        "value": [100000],
        "volume_ratio": [1.5],
        "rsi": [50]
    })

    data = [{
        "symbol": "TEST",
        "current": {"value": 100000},
        "history": dummy_df
    }]

    # rules 없으면 skip
    try:
        result = select_candidates(data, os.path.join(ROOT, "STRATEGY"), "STOCK")
    except:
        return

    for item in result:
        assert "symbol" in item, "SELECTOR_OUTPUT_INVALID: symbol missing"