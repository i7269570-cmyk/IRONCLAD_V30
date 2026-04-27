import os
import pandas as pd

STOCK_ROOT = r"C:\Users\PC\OneDrive\바탕 화면\주식 테이터\stock"
OUTPUT_PATH = r"C:\Users\PC\OneDrive\바탕 화면\원본 주식데이터\TRINITY_RESEARCH\주식 테이터\data\merged.csv"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

dfs = []
files = sorted([f for f in os.listdir(STOCK_ROOT) if f.endswith("_1m.csv")])

for fname in files:
    symbol = fname.replace("_1m.csv", "")
    path = os.path.join(STOCK_ROOT, fname)
    try:
        df = pd.read_csv(path)
        df.columns = [c.lower() for c in df.columns]

        # volume 컬럼 정규화
        if "jdiff_vol" in df.columns:
            df = df.rename(columns={"jdiff_vol": "volume"})

        # symbol 컬럼 추가
        df["symbol"] = symbol

        dfs.append(df)
        print(f"✅ {symbol}: {len(df)}행")
    except Exception as e:
        print(f"❌ {symbol}: {e}")

merged = pd.concat(dfs, ignore_index=True)
merged.to_csv(OUTPUT_PATH, index=False)
print(f"\n완료: {OUTPUT_PATH}")
print(f"전체: {len(merged)}행 / {merged['symbol'].nunique()}종목")


