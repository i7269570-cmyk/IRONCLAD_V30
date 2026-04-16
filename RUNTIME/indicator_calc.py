# ============================================================
# IRONCLAD_V31.35 - Central Indicator Calculator (Final)
# ============================================================
import pandas as pd
import numpy as np

def calculate_indicators(df):
    if df is None or df.empty:
        raise RuntimeError("INVALID_DATA: EMPTY")
    if df["close"].iloc[-1] == 0:
        raise RuntimeError("INVALID_DATA: CLOSE_ZERO")
    if df["volume"].iloc[-1] == 0:
        raise RuntimeError("INVALID_DATA: VOLUME_ZERO")
    
    # [V31.35 수정] 실전 가동성을 위해 마지막 행의 유효성만 검증 (Rolling 초기 NaN 허용)
    if df.iloc[-1].isnull().any():
        raise RuntimeError(f"INVALID_DATA: LATEST_ROW_HAS_NAN -> {df.iloc[-1].to_dict()}")

    required_columns = [
        "datetime", "open", "high", "low", "close", "volume", "asset_type"
    ]
    for col in required_columns:
        if col not in df.columns:
            raise RuntimeError(f"DATA_CONTRACT_VIOLATION: missing {col}")

    try:
        df['value'] = df['close'] * df['volume']

        # 1. 이동평균선
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        df['ma200'] = df['close'].rolling(window=200).mean()
        
        # 2. RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0.0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (std20 * 2)
        df['bb_lower'] = df['bb_middle'] - (std20 * 2)

        # 4. Volume Indicators
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = (df['volume'] / df['volume_ma']).fillna(1.0)

        # 5. ATR 및 ADX (true_range 최적화)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        df['atr'] = true_range.rolling(window=14).mean()
        df['atr_percent'] = (df['atr'] / df['close']) * 100

        # ADX
        up_move = df['high'] - df['high'].shift()
        down_move = df['low'].shift() - df['low']
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        tr14 = true_range.rolling(window=14).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=14).mean() / tr14)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=14).mean() / tr14)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=14).mean()

        # 6. 전략 필수 지표 (Turtle 및 기초 지표)
        df["highest_20"] = df["high"].rolling(window=20).max()
        df["lowest_10"] = df["low"].rolling(window=10).min()
        df["disparity_20"] = (df["close"] / df["ma20"]) * 100
        df['disparity_abs'] = (df['close'] - df['ma20']).abs() / df['ma20']

        # [TURTLE SPECIFIC]
        df["highest_high_20"] = df["highest_20"]
        df["lowest_low_10"] = df["lowest_10"]
        df["atr_20"] = true_range.rolling(window=20).mean()

        required = [
            "ma20", "ma50", "ma200", "atr_percent", "disparity_abs", 
            "highest_20", "lowest_10", "adx", "disparity_20",
            "highest_high_20", "lowest_low_10", "atr_20", "volume_ratio"
        ]
        for col in required:
            if col not in df.columns:
                raise RuntimeError(f"INDICATOR_GENERATION_FAILED: missing {col}")

        return df

    except Exception as e:
        raise RuntimeError(f"INDICATOR_CALC_CRITICAL_FAILURE: {str(e)}")