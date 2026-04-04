import json
from datetime import datetime

STATE_PATH = "STATE/state.json"

def load_state():
    with open(STATE_PATH, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

def run_daily_setup(total_capital, stock_symbols, crypto_symbols):
    state = load_state()

    today = datetime.now().strftime("%Y-%m-%d")

    # 이미 오늘 세팅했으면 종료
    if state.get("date") == today:
        return

    # 자금 배분
    stock_alloc = total_capital * 0.45
    crypto_alloc = total_capital * 0.45

    # 상태 업데이트
    state["date"] = today
    state["capital"] = {
        "total": total_capital,
        "stock_alloc": stock_alloc,
        "crypto_alloc": crypto_alloc
    }

    state["symbols"] = {
        "stock": stock_symbols,
        "crypto": crypto_symbols
    }

    # 포지션/쿨다운 초기화
    state["positions"] = {}
    state["cooldown"] = {}

    save_state(state)