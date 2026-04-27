"""
IRONCLAD - Backtest Engine
수집된 1분봉 데이터로 전략 조건식 검증

사용법:
    python BACKTEST/backtest_engine.py --asset CRYPTO
    python BACKTEST/backtest_engine.py --asset STOCK
    python BACKTEST/backtest_engine.py --asset CRYPTO --symbol KRW-AAVE --resample 5

결과: BACKTEST/RESULTS/backtest_history.csv (누적 저장)
로그: BACKTEST/LOGS/{timestamp}.log
"""

import os
import sys
import argparse
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from RUNTIME.indicator_calc import calculate_indicators

RESULTS_DIR = os.path.join(PROJECT_ROOT, "BACKTEST", "RESULTS")
LOG_DIR     = os.path.join(PROJECT_ROOT, "BACKTEST", "LOGS")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

HISTORY_PATH = os.path.join(RESULTS_DIR, "backtest_history.csv")

FEE = {
    "STOCK":  0.0003,
    "CRYPTO": 0.001,
}


# =========================
# 로그 설정
# =========================
def setup_logger() -> logging.Logger:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path  = os.path.join(LOG_DIR, f"{timestamp}.log")

    logger = logging.getLogger("BACKTEST")
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    return logger


logger = setup_logger()


# =========================
# 종목별 즉시 저장
# =========================
def save_incrementally(df_result: pd.DataFrame, asset: str, resample_min: int):
    """
    결과를 backtest_history.csv 에 누적 저장
    중간에 꺼져도 데이터 보존
    """
    if df_result.empty:
        return

    df_result["asset"]       = asset
    df_result["resample_min"] = resample_min
    df_result["saved_at"]    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = not os.path.exists(HISTORY_PATH)
    df_result.to_csv(
        HISTORY_PATH, mode="a",
        header=header, index=False,
        encoding="utf-8-sig"
    )


# =========================
# 데이터 로드
# =========================
def load_data(asset: str, symbol: str) -> pd.DataFrame:
    if asset == "CRYPTO":
        fname    = symbol.replace("-", "_") + ".csv"
        filepath = os.path.join(PROJECT_ROOT, "BACKTEST", "crypto", fname)
    else:
        fname    = symbol + ".csv"
        filepath = os.path.join(PROJECT_ROOT, "BACKTEST", "data", "stock", fname)

    if not os.path.exists(filepath):
        raise RuntimeError(f"파일 없음: {filepath}")

    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


# =========================
# 리샘플링
# =========================
def resample_ohlcv(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if minutes <= 1:
        return df

    df = df.set_index("datetime")
    resampled = df.resample(f"{minutes}min").agg({
        "open":   "first",
        "high":   "max",
        "low":    "min",
        "close":  "last",
        "volume": "sum",
    }).dropna()

    resampled = resampled[resampled["volume"] > 0]
    resampled = resampled.reset_index()
    return resampled


# =========================
# 백테스트 단일 실행
# =========================
def run_backtest(
    df: pd.DataFrame,
    symbol: str,
    asset: str,
    take_profit:      float,
    stop_loss:        float,
    max_hold_bars:    int,
    min_profit:       float,
    volume_ratio_min: float,
    rsi_max:          float,
) -> dict:

    fee = FEE.get(asset, 0.001)

    try:
        df = calculate_indicators(df.copy())
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    trades   = []
    position = None

    for i in range(200, len(df)):
        row = df.iloc[i]

        if position is None:
            try:
                prev_row = df.iloc[i-1]
                cond1 = float(row["close"])        > float(prev_row["highest_20"])  # 이전 20봉 신고가 돌파
                cond2 = float(row["volume_ratio"]) >= volume_ratio_min
                cond3 = float(row["ma5"])          > float(row["ma20"])
                cond4 = float(row["rsi"])          < rsi_max
            except Exception:
                continue

            if cond1 and cond2 and cond3 and cond4:
                position = {
                    "entry_price": float(row["close"]),
                    "entry_idx":   i,
                    "entry_time":  row["datetime"],
                }

        else:
            current_price = float(row["close"])
            entry_price   = position["entry_price"]
            hold_bars     = i - position["entry_idx"]
            pnl_pct       = (current_price - entry_price) / entry_price

            exit_reason = None
            if pnl_pct >= take_profit:
                exit_reason = "TP"
            elif pnl_pct <= -stop_loss:
                exit_reason = "SL"
            elif hold_bars > max_hold_bars and pnl_pct < min_profit:
                exit_reason = "HOLD"

            if exit_reason:
                net_pnl = pnl_pct - fee
                trades.append({
                    "symbol":      symbol,
                    "entry_time":  position["entry_time"],
                    "exit_time":   row["datetime"],
                    "entry_price": entry_price,
                    "exit_price":  current_price,
                    "hold_bars":   hold_bars,
                    "pnl_pct":     pnl_pct,
                    "net_pnl":     net_pnl,
                    "exit_reason": exit_reason,
                })
                position = None

    if not trades:
        return {
            "symbol": symbol, "take_profit": take_profit,
            "stop_loss": stop_loss, "max_hold_bars": max_hold_bars,
            "volume_ratio": volume_ratio_min, "rsi_max": rsi_max,
            "total_trades": 0, "win_rate": 0, "total_return": 0,
            "mdd": 0, "pf": 0, "avg_hold_bars": 0,
        }

    df_trades    = pd.DataFrame(trades)
    total_trades = len(df_trades)
    wins         = df_trades[df_trades["net_pnl"] > 0]
    losses       = df_trades[df_trades["net_pnl"] <= 0]
    win_rate     = len(wins) / total_trades * 100
    total_return = df_trades["net_pnl"].sum() * 100

    cumulative  = (1 + df_trades["net_pnl"]).cumprod()
    rolling_max = cumulative.cummax()
    drawdown    = (cumulative - rolling_max) / rolling_max
    mdd         = drawdown.min() * 100

    gross_profit = wins["net_pnl"].sum()
    gross_loss   = abs(losses["net_pnl"].sum())
    pf           = gross_profit / gross_loss if gross_loss > 0 else 999.0
    avg_hold     = df_trades["hold_bars"].mean()

    return {
        "symbol":        symbol,
        "take_profit":   take_profit,
        "stop_loss":     stop_loss,
        "max_hold_bars": max_hold_bars,
        "volume_ratio":  volume_ratio_min,
        "rsi_max":       rsi_max,
        "total_trades":  total_trades,
        "win_rate":      round(win_rate, 1),
        "total_return":  round(total_return, 2),
        "mdd":           round(mdd, 2),
        "pf":            round(pf, 3),
        "avg_hold_bars": round(avg_hold, 1),
    }


# =========================
# 파라미터 그리드 서치
# =========================
def grid_search(asset: str, symbol: str, resample_min: int) -> pd.DataFrame:
    logger.info(f"[{symbol}] 백테스트 시작")

    try:
        df = load_data(asset, symbol)
    except RuntimeError as e:
        logger.warning(f"[{symbol}] {e}")
        return pd.DataFrame()

    if len(df) < 50000:
        logger.warning(f"[{symbol}] 데이터 부족 ({len(df)}봉) → 건너뜀")
        return pd.DataFrame()

    if resample_min > 1:
        df = resample_ohlcv(df, resample_min)
        logger.info(f"[{symbol}] 데이터: {len(df)}봉 ({resample_min}분봉)")
    else:
        logger.info(f"[{symbol}] 데이터: {len(df)}봉 (1분봉)")

    param_grid = {
        "take_profit":   [0.005, 0.01, 0.015, 0.02, 0.03],
        "stop_loss":     [0.003, 0.005, 0.008, 0.01],
        "max_hold_bars": [10, 20, 30, 50],
        "volume_ratio":  [1.2, 1.5, 2.0],
        "rsi_max":       [65, 70],
    }

    results = []
    count   = 0

    for tp in param_grid["take_profit"]:
        for sl in param_grid["stop_loss"]:
            # 손익비 필터: take_profit >= stop_loss 조합만 테스트
            if tp < sl:
                continue
            for mhb in param_grid["max_hold_bars"]:
                for vr in param_grid["volume_ratio"]:
                    for rsi in param_grid["rsi_max"]:
                        result = run_backtest(
                            df.copy(), symbol, asset,
                            take_profit=tp, stop_loss=sl,
                            max_hold_bars=mhb, min_profit=0.002,
                            volume_ratio_min=vr, rsi_max=rsi,
                        )
                        results.append(result)
                        count += 1

    logger.info(f"[{symbol}] 완료: {count}개 조합 테스트")

    if not results:
        return pd.DataFrame()

    df_results = pd.DataFrame(results)
    df_results = df_results[df_results["total_trades"] > 0]
    df_results = df_results.sort_values("pf", ascending=False)

    # 즉시 저장
    save_incrementally(df_results, asset, resample_min)
    logger.info(f"[{symbol}] 저장 완료 → {HISTORY_PATH}")

    return df_results


# =========================
# 실행
# =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset",    default="CRYPTO", choices=["STOCK", "CRYPTO"])
    parser.add_argument("--symbol",   default="",       help="특정 종목만 (미입력시 전체)")
    parser.add_argument("--resample", default=5, type=int, help="리샘플링 분 단위 (기본값: 5)")
    args = parser.parse_args()

    asset        = args.asset.upper()
    resample_min = args.resample

    if args.symbol:
        symbols = [args.symbol]
    else:
        if asset == "CRYPTO":
            data_dir = os.path.join(PROJECT_ROOT, "BACKTEST", "crypto")
            symbols  = [
                f.stem.replace("_", "-", 1)
                for f in Path(data_dir).glob("*.csv")
            ]
        else:
            data_dir = os.path.join(PROJECT_ROOT, "BACKTEST", "data", "stock")
            symbols  = [f.stem for f in Path(data_dir).glob("*.csv")]

    logger.info(f"백테스트 시작: {asset} / {len(symbols)}개 종목 / {resample_min}분봉")
    logger.info(f"결과 저장: {HISTORY_PATH}")

    all_results = []

    for symbol in symbols:
        df_result = grid_search(asset, symbol, resample_min)
        if not df_result.empty:
            all_results.append(df_result)
            logger.info(f"\n[{symbol}] 상위 3개:")
            logger.info(df_result.head(3).to_string(index=False))

    if all_results:
        final = pd.concat(all_results, ignore_index=True)
        final = final.sort_values("pf", ascending=False)

        logger.info(f"\n{'='*60}")
        logger.info(f"전체 상위 10개 조합:")
        logger.info(final.head(10).to_string(index=False))
    else:
        logger.info("결과 없음")
