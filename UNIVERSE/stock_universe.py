import pandas as pd
import yfinance as yf
import os

# 저장 위치
SAVE_PATH = os.path.join(os.path.dirname(__file__), "../data/target_100.csv")


def generate_stock_universe():

    universe_list = [
        "005930.KS", "000660.KS", "035420.KS",
        "AAPL", "MSFT", "NVDA", "TSLA"
    ]

    data = yf.download(
        tickers=universe_list,
        period="5d",
        interval="1d",
        group_by="ticker"
    )

    rows = []

    for ticker in universe_list:
        try:
            df = data[ticker].dropna()

            if len(df) < 2:
                continue

            close = df['Close'].iloc[-1]
            volume = df['Volume'].iloc[-1]
            prev_volume = df['Volume'].iloc[-2]

            turnover = close * volume
            volume_change = (volume - prev_volume) / prev_volume
            ret = (close - df['Close'].iloc[-2]) / df['Close'].iloc[-2]

            rows.append({
                "symbol": ticker,
                "turnover": turnover,
                "volume_change": volume_change,
                "return": ret,
                "asset_type": "STOCK"
            })

        except:
            continue

    result = pd.DataFrame(rows)

    result = result.sort_values(
        by=["turnover", "volume_change", "return"],
        ascending=False
    ).head(100)

    result.to_csv(SAVE_PATH, index=False)

    print("STOCK UNIVERSE GENERATED:", len(result))


if __name__ == "__main__":
    generate_stock_universe()