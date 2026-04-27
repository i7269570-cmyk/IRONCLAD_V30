"""
IRONCLAD - Crypto Backtest Data Collector
업비트 1분봉 과거 데이터 수집 (인증 불필요)
저장 위치: BACKTEST/data/crypto/{symbol}.csv

사용법:
    python BACKTEST/crypto_collector.py

수집 기간: 2년치 1분봉
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "BACKTEST", "data", "crypto")
os.makedirs(OUTPUT_DIR, exist_ok=True)

UPBIT_URL = "https://api.upbit.com/v1/candles/minutes/1"


# =========================
# 단일 요청
# =========================
def _fetch_once(market: str, to: str = "") -> list:
    """
    market: KRW-BTC 형식
    to    : 마지막 캔들 시각 (ISO8601, 미입력시 현재)
    반환  : 최대 200봉 리스트
    """
    params = {"market": market, "count": 200}
    if to:
        params["to"] = to

    res = requests.get(UPBIT_URL, params=params, timeout=10)

    if res.status_code == 429:
        print(f"  ⚠️ Rate limit → 5초 대기")
        time.sleep(5)
        return _fetch_once(market, to)

    if res.status_code != 200:
        raise RuntimeError(f"API_FAILED: {market} -> {res.status_code}")

    return res.json()


# =========================
# 종목 1개 수집
# =========================
def fetch_minutes(market: str, years: int = 2) -> pd.DataFrame:
    now      = datetime.now(timezone.utc)
    sdate    = now - timedelta(days=365 * years + 5)
    all_rows = []
    to       = ""

    print(f"  [{market}] 수집 시작 ({sdate.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')})")

    page = 0
    while True:
        page += 1
        try:
            rows = _fetch_once(market, to)
        except RuntimeError as e:
            print(f"  ⚠️ [{market}] 페이지{page} 실패: {e}")
            break

        if not rows:
            break

        all_rows.extend(rows)

        # 마지막 봉 시각 확인
        last_time_str = rows[-1].get("candle_date_time_utc", "")
        if not last_time_str:
            break

        last_time = datetime.fromisoformat(last_time_str).replace(tzinfo=timezone.utc)

        if page % 50 == 0:
            print(f"  [{market}] 페이지{page}: 누적 {len(all_rows)}봉 | {last_time.strftime('%Y-%m-%d %H:%M')}")

        # 수집 시작일 이전이면 종료
        if last_time <= sdate:
            break

        # 다음 요청용 to 설정
        to = rows[-1].get("candle_date_time_utc", "")

        time.sleep(0.12)   # 업비트 rate limit 대응

    if not all_rows:
        print(f"  ⚠️ [{market}] 데이터 없음")
        return pd.DataFrame()

    # DataFrame 변환
    df = pd.DataFrame(all_rows)
    df = df.rename(columns={
        "candle_date_time_kst": "datetime",
        "opening_price":        "open",
        "high_price":           "high",
        "low_price":            "low",
        "trade_price":          "close",
        "candle_acc_trade_volume": "volume",
    })

    required = ["datetime", "open", "high", "low", "close", "volume"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        print(f"  ⚠️ [{market}] 필드 누락: {missing}")
        return pd.DataFrame()

    df = df[required].copy()
    df["open"]   = pd.to_numeric(df["open"],   errors="coerce")
    df["high"]   = pd.to_numeric(df["high"],   errors="coerce")
    df["low"]    = pd.to_numeric(df["low"],    errors="coerce")
    df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    df = df.dropna()
    df = df[df["volume"] > 0]

    # 시작일 필터
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df[df["datetime"] >= pd.Timestamp(sdate).tz_localize(None)]

    # 시간 오름차순 정렬
    df = df.sort_values("datetime").reset_index(drop=True)

    return df


# =========================
# 전체 종목 수집
# =========================
def collect_all(symbols: list, years: int = 2):
    total   = len(symbols)
    success = 0
    failed  = []

    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{total}] {symbol} 수집 중...")

        # 이미 수집된 파일 건너뜀
        out_path = os.path.join(OUTPUT_DIR, f"{symbol.replace('-', '_')}.csv")
        if os.path.exists(out_path):
            print(f"  ✅ [{symbol}] 이미 존재 → 건너뜀")
            success += 1
            continue

        try:
            df = fetch_minutes(symbol, years)

            if df.empty:
                failed.append(symbol)
                continue

            df.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"  ✅ [{symbol}] {len(df)}봉 저장 → {out_path}")
            success += 1

        except Exception as e:
            print(f"  ❌ [{symbol}] 실패: {e}")
            failed.append(symbol)

        time.sleep(1.0)

    print(f"\n{'='*50}")
    print(f"완료: {success}/{total}개 성공")
    if failed:
        print(f"실패: {failed}")
    print(f"저장 위치: {OUTPUT_DIR}")


# =========================
# 실행
# =========================
if __name__ == "__main__":
    # universe 에서 코인 종목 읽기
    universe_path = os.path.join(PROJECT_ROOT, "UNIVERSE", "coin_universe.json")
    if not os.path.exists(universe_path):
        print(f"❌ universe 파일 없음: {universe_path}")
        sys.exit(1)

    with open(universe_path, "r", encoding="utf-8") as f:
        symbols = json.load(f).get("symbols", [])

    if not symbols:
        print("❌ universe 종목 없음")
        sys.exit(1)

    print(f"수집 대상: {len(symbols)}개 종목 / {2}년치 1분봉")
    print(f"예상 시간: 약 {len(symbols) * 18 // 60}시간 (종목당 약 18분)")
    print(f"중단 후 재시작해도 수집된 파일은 건너뜁니다.")
    print()

    collect_all(symbols, years=2)
