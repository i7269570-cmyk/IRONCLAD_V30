import sys
import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from strategy import MeanReversion_Disparity

data_path = r"C:\Users\PC\OneDrive\바탕 화면\원본 주식데이터\TRINITY_RESEARCH\주식 테이터\data\merged.csv"
df = pd.read_csv(data_path)
df.columns = [c.lower() for c in df.columns]

print("📊 지표 생성 중...")
df['ma20'] = df.groupby('symbol')['close'].transform(lambda x: x.rolling(20).mean())
df['ma60'] = df.groupby('symbol')['close'].transform(lambda x: x.rolling(60).mean())
df['std20'] = df.groupby('symbol')['close'].transform(lambda x: x.rolling(20).std())
df['bb_lower'] = df['ma20'] - (2 * df['std20'])
df['bb_middle'] = df['ma20']
df['volume_ma'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(20).mean())
df['volume_ratio'] = df['volume'] / df['volume_ma']

delta = df.groupby('symbol')['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.groupby(df['symbol']).transform(lambda x: x.rolling(14).mean())
avg_loss = loss.groupby(df['symbol']).transform(lambda x: x.rolling(14).mean())
df['rsi'] = 100 - (100 / (1 + (avg_gain / avg_loss)))
df = df.dropna()

# Regime 필터 적용
df['regime'] = np.where(df['ma20'] > df['ma60'], 'TREND', 'RANGE')

IS_END = 20251130

def run_backtest(data, regime_filter=None):
    results = []
    for sym in data["symbol"].unique():
        sub = data[data["symbol"] == sym].copy().reset_index(drop=True)
        if len(sub) < 60: continue
        strategy = MeanReversion_Disparity()
        position = None
        for i in range(60, len(sub)):
            row = sub.iloc[i]

            # Regime 필터 적용
            if regime_filter and row["regime"] != regime_filter:
                continue

            if position is None:
                if strategy.on_bar(row, position) == "BUY":
                    position = {"entry_price": row["close"], "hold_bars": 0}
            else:
                if strategy.on_position(row, position) == "EXIT":
                    pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
                    results.append(pnl)
                    position = None
    return pd.Series(results)

def print_result(name, r):
    if len(r) == 0:
        print(f"{name}: ❌ 거래 없음"); return
    loss_sum = abs(r[r < 0].sum())
    pf = round(r[r > 0].sum() / loss_sum, 3) if loss_sum > 0 else "Inf"
    print(f"{name}: 거래:{len(r)} | 승률:{round((r>0).mean()*100,1)}% | PF:{pf} | 평균:{round(r.mean()*100,4)}%")

df_is = df[df['date'] <= IS_END]
df_oos = df[df['date'] > IS_END]

print("\n[필터 없음]")
print_result("IS ", run_backtest(df_is))
print_result("OOS", run_backtest(df_oos))

print("\n[RANGE 구간만 진입]")
print_result("IS ", run_backtest(df_is, "RANGE"))
print_result("OOS", run_backtest(df_oos, "RANGE"))
