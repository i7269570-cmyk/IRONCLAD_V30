import sys
import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

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

df['regime'] = np.where(df['ma20'] > df['ma60'], 'TREND', 'RANGE')

IS_END = 20251130

def run_backtest(data, use_regime=False, rsi_threshold=None):
    results = []
    for sym in data["symbol"].unique():
        sub = data[data["symbol"] == sym].copy().reset_index(drop=True)
        if len(sub) < 60: continue
        position = None
        for i in range(60, len(sub)):
            row = sub.iloc[i]

            if position is None:
                # Regime 필터
                if use_regime and row["regime"] == "TREND":
                    continue

                # 기본 Disparity 조건
                try:
                    c1 = row['close'] < row['ma20'] * 0.96
                    c2 = row['close'] > row['ma20'] * 0.90
                    c3 = row['volume_ratio'] >= 1.2
                    c4 = row['close'] > row['low'] * 1.005
                    c5 = True if rsi_threshold is None else row['rsi'] < rsi_threshold
                    if c1 and c2 and c3 and c4 and c5:
                        position = {"entry_price": row["close"], "hold_bars": 0}
                except:
                    continue
            else:
                try:
                    pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
                    hold = position["hold_bars"]
                    if row['close'] >= row['ma20'] or pnl >= 0.015 or pnl <= -0.010 or hold >= 5:
                        results.append(pnl)
                        position = None
                    else:
                        position["hold_bars"] = hold + 1
                except:
                    continue
    return pd.Series(results)

def print_result(name, r):
    if len(r) == 0:
        print(f"  {name}: ❌ 거래 없음"); return
    loss_sum = abs(r[r < 0].sum())
    pf = round(r[r > 0].sum() / loss_sum, 3) if loss_sum > 0 else "Inf"
    print(f"  {name}: 거래:{len(r)} | 승률:{round((r>0).mean()*100,1)}% | PF:{pf} | 평균:{round(r.mean()*100,4)}%")

df_is = df[df['date'] <= IS_END]
df_oos = df[df['date'] > IS_END]

configs = [
    ("RANGE + RSI<40", True, 40),
    ("RANGE + RSI<35", True, 35),
    ("RANGE + RSI<45", True, 45),
    ("RANGE만",        True, None),
]

print()
for name, regime, rsi in configs:
    print(f"[{name}]")
    print_result("IS ", run_backtest(df_is, regime, rsi))
    print_result("OOS", run_backtest(df_oos, regime, rsi))
    print()
