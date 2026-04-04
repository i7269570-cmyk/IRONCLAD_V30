# ============================================================
# IRONCLAD_V31 - Central Indicator Calculator (V31.0 Schema)
# ============================================================
import pandas as pd
import numpy as np

def calculate_indicators(df):
    """
    [V31.0 수정]
    1. 필수 컬럼 검증 완전성 확보 (7대 필수 컬럼 전수 조사)
    2. 데이터 계약(Data Contract) 위반 시 즉시 HALT
    3. 지표 계산 로직 및 객체 동일성 유지
    """
    
    # [V31.0] 필수 컬럼 검증 (RISK -> PASS)
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

    # [규격] DataFrame 복사 금지 및 동일 객체에 컬럼 추가
    df['value'] = df['close'] * df['volume']

    # 1. 이동평균선 (MA)
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    
    # 2. RSI (14 기준)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 3. 볼린저 밴드 (20 기준, std=2)
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    std20 = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (std20 * 2)
    df['bb_lower'] = df['bb_middle'] - (std20 * 2)
    
    # [규격] 초기 구간 NaN 유지 및 동일 DataFrame 객체 반환
    return df