# ============================================================
# IRONCLAD_V31.37 - Zero-Distortion Indicator Engine (Final)
# ============================================================
import pandas as pd
import numpy as np

def calculate_indicators(df):
    # [1] 기초 데이터 및 계약 검증 (SSOT)
    if df is None or df.empty:
        raise RuntimeError("INVALID_DATA: EMPTY")

    required_columns = ["open", "high", "low", "close", "volume"]
    for col in required_columns:
        if col not in df.columns:
            raise RuntimeError(f"DATA_CONTRACT_VIOLATION: missing {col}")

    if df["close"].iloc[-1] == 0 or df["volume"].iloc[-1] == 0:
        raise RuntimeError("INVALID_DATA: ZERO_VALUE_DETECTED")

    try:
        # [2] 공통 지표 계산
        df['value'] = df['close'] * df['volume']

        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        df['ma200'] = df['close'].rolling(window=200).mean()

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0.0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        std20 = df['close'].rolling(window=20).std()
        df['bb_middle'] = df['ma20']
        df['bb_upper'] = df['bb_middle'] + (std20 * 2)
        df['bb_lower'] = df['bb_middle'] - (std20 * 2)

        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        df['atr_percent'] = (df['atr'] / df['close']) * 100

        df["volatility"] = df["atr_percent"]
        df["trend_score"] = np.where(df["ma5"] > df["ma20"], 1.0, -1.0)

        df["highest_20"] = df["high"].rolling(window=20).max()
        df["lowest_10"] = df["low"].rolling(window=10).min()
        df["disparity_20"] = (df["close"] / df['ma20']) * 100
        df['disparity_abs'] = (df['close'] - df['ma20']).abs() / df['ma20']
        df["atr_20"] = true_range.rolling(window=20).mean()

        # [3] 최종 무결성 검증
        required_final = [
            "ma20", "ma60", "atr_percent", "volume_ratio", "disparity_20",
            "highest_20", "lowest_10", "rsi", "volatility", "trend_score"
        ]

        df = df.dropna(subset=["rsi"])
        latest_data = df.iloc[-1]
        for col in required_final:
            if col not in latest_data or pd.isna(latest_data[col]):
                raise RuntimeError(f"INTEGRITY_CHECK_FAILED: {col} is NaN or Missing")

        return df

    except Exception as e:
        raise RuntimeError(f"INDICATOR_ENGINE_HALT: {str(e)}")
