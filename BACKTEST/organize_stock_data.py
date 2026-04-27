"""
주식 1분봉 데이터 정리 스크립트
- 원본: BACKTEST/stock/1분봉-stock/{종목코드}_1m.csv
- 대상: BACKTEST/data/stock/{종목코드}.csv
- 컬럼: date+time → datetime, jdiff_vol → volume 으로 정규화
"""

import os
import sys
import shutil
import pandas as pd
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SRC_DIR = os.path.join(PROJECT_ROOT, "BACKTEST", "stock", "1분봉-stock")
DST_DIR = os.path.join(PROJECT_ROOT, "BACKTEST", "data", "stock")
os.makedirs(DST_DIR, exist_ok=True)


def normalize(src_path: str, dst_path: str) -> int:
    """
    컬럼 정규화:
    date + time → datetime
    jdiff_vol   → volume
    필요 컬럼만 추출: datetime, open, high, low, close, volume
    """
    df = pd.read_csv(src_path, encoding="utf-8-sig")

    # date + time 합쳐서 datetime 생성
    if "date" in df.columns and "time" in df.columns:
        df["datetime"] = pd.to_datetime(
            df["date"].astype(str) + " " + df["time"].astype(str).str.zfill(6),
            format="%Y%m%d %H%M%S",
            errors="coerce"
        )
    elif "date" in df.columns:
        df["datetime"] = pd.to_datetime(df["date"].astype(str), errors="coerce")
    else:
        raise RuntimeError(f"date 컬럼 없음: {src_path}")

    # jdiff_vol → volume
    if "jdiff_vol" in df.columns:
        df["volume"] = df["jdiff_vol"]
    elif "volume" not in df.columns:
        raise RuntimeError(f"volume 컬럼 없음: {src_path}")

    # 필요 컬럼만
    required = ["datetime", "open", "high", "low", "close", "volume"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"필드 누락: {missing}")

    df = df[required].copy()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()
    df = df[df["volume"] > 0]
    df = df.sort_values("datetime").reset_index(drop=True)

    df.to_csv(dst_path, index=False, encoding="utf-8-sig")
    return len(df)


if __name__ == "__main__":
    files   = list(Path(SRC_DIR).glob("*_1m.csv"))
    total   = len(files)
    success = 0
    failed  = []

    print(f"정리 대상: {total}개 파일")
    print(f"원본: {SRC_DIR}")
    print(f"대상: {DST_DIR}")
    print()

    for f in sorted(files):
        symbol   = f.stem.replace("_1m", "")
        dst_path = os.path.join(DST_DIR, f"{symbol}.csv")

        # 이미 정리된 파일 건너뜀
        if os.path.exists(dst_path):
            print(f"  ✅ [{symbol}] 이미 존재 → 건너뜀")
            success += 1
            continue

        try:
            rows = normalize(str(f), dst_path)
            print(f"  ✅ [{symbol}] {rows}봉 저장")
            success += 1
        except Exception as e:
            print(f"  ❌ [{symbol}] 실패: {e}")
            failed.append(symbol)

    print(f"\n{'='*50}")
    print(f"완료: {success}/{total}개 성공")
    if failed:
        print(f"실패: {failed}")
    print(f"저장 위치: {DST_DIR}")