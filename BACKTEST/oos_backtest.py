import sys
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from strategy import MeanReversion_Disparity

data_path = r"C:\Users\PC\OneDrive\바탕 화면\원본 주식데이터\TRINITY_RESEARCH\주식 테이터\data\merged.csv"
df = pd.read_csv(data_path)
df.columns = [c.lower() for c in df.columns]

print("📊 지표 생성 중...")
df['ma20'] = df.groupby('symbol')['close'].transform(lambda x: x.rolling(20).mean())
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

# 기간 분리
IS_END = 20251130
df_is = df[df['date'] <= IS_END]
df_oos = df[df['date'] > IS_END]

print(f"학습(IS): {df_is['date'].min()} ~ {df_is['date'].max()} | {df_is['date'].nunique()}일")
print(f"검증(OOS): {df_oos['date'].min()} ~ {df_oos['date'].max()} | {df_oos['date'].nunique()}일")
print()

def run_backtest(data):
    results = []
    for sym in data["symbol"].unique():
        sub = data[data["symbol"] == sym].copy().reset_index(drop=True)
        if len(sub) < 50: continue
        strategy = MeanReversion_Disparity()
        position = None
        for i in range(20, len(sub)):
            row = sub.iloc[i]
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
    pf = round(r[r > 0].sum() / loss_sum, 3) if loss_sum != 0 else "Inf"
    print(f"{name}: 거래:{len(r)} | 승률:{round((r>0).mean()*100,1)}% | PF:{pf} | 평균:{round(r.mean()*100,4)}%")

r_is = run_backtest(df_is)
r_oos = run_backtest(df_oos)

print("=" * 50)
print("[Disparity 전략 OOS 검증]")
print_result("학습(IS) ", r_is)
print_result("검증(OOS)", r_oos)
print("=" * 50)

if len(r_oos) > 0:
    pf_is = r_is[r_is > 0].sum() / abs(r_is[r_is < 0].sum()) if len(r_is[r_is < 0]) > 0 else 0
    pf_oos = r_oos[r_oos > 0].sum() / abs(r_oos[r_oos < 0].sum()) if len(r_oos[r_oos < 0]) > 0 else 0
    degradation = (pf_is - pf_oos) / pf_is * 100 if pf_is > 0 else 0
    print(f"PF 저하율: {degradation:.1f}%")
    if pf_oos >= 1.2 and degradation < 40:
        print("✅ 통과: 강건한 전략")
    else:
        print("❌ 주의: 과적합 가능성")
