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

# Regime 분류: ma20 > ma60 이면 TREND, 아니면 RANGE
df['regime'] = np.where(df['ma20'] > df['ma60'], 'TREND', 'RANGE')

def run_backtest_with_regime(data):
    results = []
    for sym in data["symbol"].unique():
        sub = data[data["symbol"] == sym].copy().reset_index(drop=True)
        if len(sub) < 60: continue
        strategy = MeanReversion_Disparity()
        position = None
        for i in range(60, len(sub)):
            row = sub.iloc[i]
            if position is None:
                if strategy.on_bar(row, position) == "BUY":
                    position = {
                        "entry_price": row["close"],
                        "hold_bars": 0,
                        "regime": row["regime"]
                    }
            else:
                if strategy.on_position(row, position) == "EXIT":
                    pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
                    results.append({
                        "pnl": pnl,
                        "regime": position["regime"],
                        "date": row["date"]
                    })
                    position = None
    return pd.DataFrame(results)

print("백테스트 실행 중...")
result_df = run_backtest_with_regime(df)

if len(result_df) == 0:
    print("거래 없음")
else:
    print(f"\n전체 거래: {len(result_df)}건")
    print("=" * 50)

    for regime in ["TREND", "RANGE"]:
        r = result_df[result_df["regime"] == regime]["pnl"]
        if len(r) == 0:
            print(f"{regime}: 거래 없음")
            continue
        loss_sum = abs(r[r < 0].sum())
        pf = round(r[r > 0].sum() / loss_sum, 3) if loss_sum > 0 else "Inf"
        print(f"{regime}: 거래:{len(r)} | 승률:{round((r>0).mean()*100,1)}% | PF:{pf} | 평균:{round(r.mean()*100,4)}%")

    print("=" * 50)
    print("\n월별 성과:")
    result_df["month"] = result_df["date"].astype(str).str[:6]
    monthly = result_df.groupby("month")["pnl"].agg(
        거래수="count",
        승률=lambda x: round((x > 0).mean() * 100, 1),
        평균수익=lambda x: round(x.mean() * 100, 3)
    )
    print(monthly.to_string())
