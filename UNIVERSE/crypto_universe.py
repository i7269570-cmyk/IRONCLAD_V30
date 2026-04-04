import ccxt
import pandas as pd
import os

SAVE_PATH = os.path.join(os.path.dirname(__file__), "../data/target_100.csv")


def generate_crypto_universe():

    exchange = ccxt.binance()

    markets = exchange.load_markets()

    symbols = [s for s in markets if "/USDT" in s]

    rows = []

    for symbol in symbols[:200]:  # 너무 많으니 제한
        try:
            ticker = exchange.fetch_ticker(symbol)

            turnover = ticker['quoteVolume']
            volatility = (ticker['high'] - ticker['low']) / ticker['low']
            volume = ticker['baseVolume']

            rows.append({
                "symbol": symbol,
                "turnover": turnover,
                "volatility": volatility,
                "volume": volume,
                "asset_type": "CRYPTO"
            })

        except:
            continue

    df = pd.DataFrame(rows)

    df = df.sort_values(
        by=["turnover", "volatility", "volume"],
        ascending=False
    ).head(100)

    df.to_csv(SAVE_PATH, index=False)

    print("CRYPTO UNIVERSE GENERATED:", len(df))


if __name__ == "__main__":
    generate_crypto_universe()