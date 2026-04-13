# ============================================================
# IRONCLAD_V31.35 - Central Indicator Calculator (Final)
# ============================================================
import pandas as pd
import numpy as np

def calculate_indicators(df):
    """
    [V31.35 수정]
    1. volume_ratio 초기 NaN 취약점 보정 (.fillna(1.0))
    2. true_range 재사용을 통한 연산 최적화 (ATR/ADX/Turtle)
    3. 터틀 전략 필수 지표 3종 추가 (highest_high_20, lowest_low_10, atr_20)
    4. 데이터 계약 및 무결성 검증 강화
    """
    
    # [V31.0] 필수 컬럼 검증
    required_columns = [
        "datetime", "open", "high", "low", "close", "volume", "asset_type"
    ]

    for col in required_columns:
        if col not in df.columns:
            raise RuntimeError(f"DATA_CONTRACT_VIOLATION: missing {col}")

    try:
        # [규격] 동일 객체 유지
        df['value'] = df['close'] * df['volume']

        # =========================
        # 1. 이동평균선
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
        # 4. Volume Indicators (Stabilized)
        # =========================
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        # [V31.35] 초기 NaN 구간을 1.0(중립 비율)로 보정하여 연산 안정성 확보
        df['volume_ratio'] = (df['volume'] / df['volume_ma']).fillna(1.0)

        # =========================
        # 5. ATR 및 ADX (Optimized)
        # =========================
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        
        # true_range를 변수로 추출하여 하단 지표에서 재사용
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        df['atr_percent'] = (df['atr'] / df['close']) * 100

        # ADX 계산
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
        # 기존 전략 지표
        df["highest_20"] = df["high"].rolling(window=20).max()
        df["lowest_10"] = df["low"].rolling(window=10).min()
        df["disparity_20"] = (df["close"] / df["ma20"]) * 100
        df['disparity_abs'] = (df['close'] - df['ma20']).abs() / df['ma20']

        # [TURTLE INDICATORS START]
        # 최적화된 true_range 재사용
        df["highest_high_20"] = df["high"].rolling(window=20).max()
        df["lowest_low_10"] = df["low"].rolling(window=10).min()
        df["atr_20"] = true_range.rolling(window=20).mean()
        # [TURTLE INDICATORS END]

        # [무결성] 필수 필드 전수 조사
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