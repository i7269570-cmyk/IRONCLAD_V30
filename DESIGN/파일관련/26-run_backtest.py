import pandas as pd

data_path = r"C:\Users\PC\OneDrive\바탕 화면\IRONCLAD_V27_CORE\TRINITY_RESEARCH\data\merged.csv"

df = pd.read_csv(data_path)

df.columns = [c.lower() for c in df.columns]

close_col = None
for c in df.columns:
    if "close" in c or "종가" in c:
        close_col = c
        break

if close_col is None:
    print("❌ close 컬럼 없음")
    exit()

df["close"] = pd.to_numeric(df[close_col], errors="coerce")
df = df.dropna(subset=["close"])

if "symbol" not in df.columns:
    print("❌ symbol 없음")
    exit()

all_returns = []

for sym in df["symbol"].unique():
    sub = df[df["symbol"] == sym].copy()

    if len(sub) < 50:
        continue

    sub["ret"] = sub["close"].pct_change()

    for i in range(5, len(sub) - 1):

        r = sub.iloc[i]["ret"]
        prev = sub.iloc[i - 1]["ret"]
        next_close = sub.iloc[i + 1]["close"]
        cur_close = sub.iloc[i]["close"]

        if (
            r < -0.02 and
            prev < 0 and
            next_close > cur_close
        ):
            entry = sub.iloc[i + 1]["close"]  
            exit = sub.iloc[i + 2]["close"]   

            if entry > 0:
                all_returns.append((exit - entry) / entry)

if len(all_returns) == 0:
    print("❌ 거래 없음")
else:
    r = pd.Series(all_returns)

    print("\n===== RESULT =====")
    print("거래수:", len(r))
    print("승률:", round((r > 0).mean(), 3))
    print("PF:", round(r[r > 0].sum() / abs(r[r < 0].sum()), 3))
    print("평균:", round(r.mean(), 6))
    print("MDD:", round((r.cumsum().cummax() - r.cumsum()).max(), 4))