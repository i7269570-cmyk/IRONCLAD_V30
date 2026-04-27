# ============================================================
# IRONCLAD_BACKTEST - Runner
# ============================================================
import os
import sys
import yaml
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "RUNTIME"))

from backtest_engine import run_backtest
from performance_tracker import calculate_performance, save_results

PROCESSED_DATA_ROOT = r"C:\Users\PC\OneDrive\바탕 화면\원본 주식데이터\TRINITY_RESEARCH\주식 테이터\processed"
STRATEGY_SPEC_PATH = os.path.join(BASE_DIR, "STRATEGY", "STOCK", "strategy_spec.yaml")
RESULTS_PATH = os.path.join(BASE_DIR, "BACKTEST", "RESULTS")
INITIAL_CAPITAL = 10_000_000


def load_processed_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df.columns = [c.lower() for c in df.columns]

    required = ["open", "high", "low", "close", "volume"]
    for col in required:
        if col not in df.columns:
            raise RuntimeError(f"COLUMN_MISSING: {col}")

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)

    df = df[df["volume"] > 0].reset_index(drop=True)
    return df


if __name__ == "__main__":
    print("=" * 50)
    print("IRONCLAD BACKTEST 시작")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    with open(STRATEGY_SPEC_PATH, "r", encoding="utf-8") as f:
        strategy_spec = yaml.safe_load(f)

    print(f"익절: {strategy_spec['exit']['take_profit']*100}% / "
          f"손절: {strategy_spec['exit']['stop_loss']*100}% / "
          f"최대보유: {strategy_spec['exit'].get('max_hold_bars', 5)}봉")
    print()

    csv_files = sorted([f for f in os.listdir(PROCESSED_DATA_ROOT) if f.endswith(".csv")])
    print(f"종목 수: {len(csv_files)}개")
    print()

    results = []
    for i, fname in enumerate(csv_files, 1):
        symbol = fname.replace(".csv", "")
        filepath = os.path.join(PROCESSED_DATA_ROOT, fname)
        try:
            df = load_processed_data(filepath)
            result = run_backtest(symbol, df, strategy_spec, INITIAL_CAPITAL, window=20)
            results.append(result)
            print(f"[{i:02d}/{len(csv_files)}] {symbol} | "
                  f"거래:{result['total_trades']}회 | "
                  f"수익:{result['total_return_pct']:+.2f}%")
        except Exception as e:
            print(f"[{i:02d}/{len(csv_files)}] {symbol} | 오류: {e}")
            continue

    print()
    print("=" * 50)
    performance = calculate_performance(results)
    save_results(performance, results, RESULTS_PATH)
    print("=" * 50)
    print(f"완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
