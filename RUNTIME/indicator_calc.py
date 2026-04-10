# ============================================================
# IRONCLAD_V31.34 - Central Indicator Calculator (Final)
# ============================================================
import pandas as pd
import numpy as np

def calculate_indicators(df):
    """
    [V31.34 수정]
    1. 필수 컬럼 검증 완전성 확보 (7대 필수 컬럼 전수 조사)
    2. 데이터 계약(Data Contract) 위반 시 즉시 HALT
    3. market_adapter 요구 지표 전수 생성 (ma, atr, disparity, adx 등)
    4. TURTLE 및 DISPARITY 전략 필수 지표 강제 계산 (highest_20, lowest_10, disparity_20)
    """
    
    # [V31.0] 필수 컬럼 검증
    required_columns = [
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "asset_type"
    ]

    for col in required_columns:
        if col not in df.columns:
            raise RuntimeError(f"DATA_CONTRACT_VIOLATION: missing {col}")

    try:
        # [규격] 동일 객체 유지
        df['value'] = df['close'] * df['volume']

        # =========================
        # 1. 이동평균선 (Regime 판정용 포함)
        # =========================
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        df['ma200'] = df['close'].rolling(window=200).mean()
        
        # =========================
        # 2. RSI (14)
        # =========================
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0.0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # =========================
        # 3. Bollinger Bands
        # =========================
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (std20 * 2)
        df['bb_lower'] = df['bb_middle'] - (std20 * 2)

        # =========================
        # 4. Volume Indicators
        # =========================
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # =========================
        # 5. ATR 및 ADX (Standard Calculation)
        # =========================
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        df['atr_percent'] = (df['atr'] / df['close']) * 100

        # ADX 계산 (high/low/close 기반 표준 방식)
        up_move = df['high'] - df['high'].shift()
        down_move = df['low'].shift() - df['low']
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        tr14 = true_range.rolling(window=14).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=14).mean() / tr14)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=14).mean() / tr14)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=14).mean()

        # ============================================================
        # 6. 전략 필수 지표 및 무결성 검증
        # ============================================================
        # TURTLE 진입/청산 지표
        df["highest_20"] = df["high"].rolling(window=20).max()
        df["lowest_10"] = df["low"].rolling(window=10).min()
        
        # DISPARITY 진입 지표
        df["disparity_20"] = (df["close"] / df["ma20"]) * 100
        
        # Regime 판정용 지표 (disparity_abs)
        df['disparity_abs'] = (df['close'] - df['ma20']).abs() / df['ma20']

        # [무결성] market_adapter 및 전략 필수 필드 전수 조사
        required = [
            "ma20", "ma50", "ma200", "atr_percent", "disparity_abs", 
            "highest_20", "lowest_10", "adx", "disparity_20"
        ]
        for col in required:
            if col not in df.columns:
                raise RuntimeError(f"INDICATOR_GENERATION_FAILED: missing {col}")

        return df

    except Exception as e:
        raise RuntimeError(f"INDICATOR_CALC_CRITICAL_FAILURE: {str(e)}")