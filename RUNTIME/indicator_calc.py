# ============================================================
# IRONCLAD_V31.37 - Zero-Distortion Indicator Engine (Final)
# ============================================================
import pandas as pd
import numpy as np

def calculate_indicators(df):
    # [1] 기초 데이터 및 계약 검증 (SSOT)
    if df is None or df.empty:
        raise RuntimeError("INVALID_DATA: EMPTY")
    
    required_columns = ["open", "high", "low", "close", "volume", "asset_type"]
    for col in required_columns:
        if col not in df.columns:
            raise RuntimeError(f"DATA_CONTRACT_VIOLATION: missing {col}")

    # 마지막 행 유효성 검사 (0값 및 결측치 차단)
    if df["close"].iloc[-1] == 0 or df["volume"].iloc[-1] == 0:
        raise RuntimeError("INVALID_DATA: ZERO_VALUE_DETECTED")

    try:
        # [2] 공통 지표 계산 (무결성 중심)
        df['value'] = df['close'] * df['volume']

        # 1. 이동평균선
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        df['ma200'] = df['close'].rolling(window=200).mean()
        
        # 2. RSI (14) - 1e-9 제거 (분모 0일 때 NaN 발생 유도)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0.0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
        # 왜곡 방지: loss가 0이면 rsi는 NaN이 되며, 이는 안전하게 걸러짐
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. Bollinger Bands
        std20 = df['close'].rolling(window=20).std()
        df['bb_middle'] = df['ma20']
        df['bb_upper'] = df['bb_middle'] + (std20 * 2)
        df['bb_lower'] = df['bb_middle'] - (std20 * 2)

        # 4. Volume Indicators - fillna 제거 (데이터 없으면 진행 불가)
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # 5. ATR 및 변동성 지표
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        df['atr_percent'] = (df['atr'] / df['close']) * 100

        # 6. 전략 특화 지표 (Turtle & Disparity)
        df["highest_20"] = df["high"].rolling(window=20).max()
        df["lowest_10"] = df["low"].rolling(window=10).min()
        df["disparity_20"] = (df["close"] / df['ma20']) * 100
        df['disparity_abs'] = (df['close'] - df['ma20']).abs() / df['ma20']
        df["atr_20"] = true_range.rolling(window=20).mean()

        # [3] 자산별 특수 보정 (물리적 임계치 적용)
        asset_type = df["asset_type"].iloc[-1]

        if asset_type == "CRYPTO":
            # 코인: 변동성 가중치 보정
            df['atr_percent'] *= 1.2
            
        elif asset_type == "STOCK":
            # 주식: 이상 거래량 수치 왜곡 방지 (Clip)
            df['volume_ratio'] = df['volume_ratio'].clip(0, 5)

        # [4] 최종 무결성 검증 (필수 지표 생성 및 NaN 체크)
        required_final = [
            "ma20", "atr_percent", "volume_ratio", "disparity_20", 
            "highest_20", "lowest_10", "rsi"
        ]
        
        # 마지막 행에 NaN이 하나라도 있으면 즉시 중단 (왜곡된 매매 방지)
        latest_data = df.iloc[-1]
        for col in required_final:
            if col not in latest_data or pd.isna(latest_data[col]):
                raise RuntimeError(f"INTEGRITY_CHECK_FAILED: {col} is NaN or Missing")

        return df

    except Exception as e:
        raise RuntimeError(f"INDICATOR_ENGINE_HALT: {str(e)}")