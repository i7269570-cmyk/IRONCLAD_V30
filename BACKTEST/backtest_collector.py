"""
IRONCLAD - Backtest Data Collector
LS증권 t8410 (gubun=2, 일봉) 연속조회로 종목별 5년치 일봉 수집
저장 위치: BACKTEST/data/{symbol}.csv

사용법:
    python BACKTEST/backtest_collector.py

필요 환경변수 (.env):
    LS_APP_KEY
    LS_APP_SECRET
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "BACKTEST", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL   = "https://openapi.ls-sec.co.kr:8080"
CHART_PATH = "stock/chart"


# =========================
# 토큰 발급
# =========================
def get_access_token(app_key: str, app_secret: str) -> str:
    url     = f"{BASE_URL}/oauth2/token"
    headers = {"content-type": "application/x-www-form-urlencoded"}
    body    = {
        "grant_type":   "client_credentials",
        "appkey":       app_key,
        "appsecretkey": app_secret,
        "scope":        "oob"
    }
    res = requests.post(url, data=body, headers=headers)
    if res.status_code != 200:
        raise RuntimeError(f"TOKEN_FAILED: {res.text}")
    token = res.json().get("access_token")
    if not token:
        raise RuntimeError("TOKEN_EMPTY")
    return token


# =========================
# t8410 일봉 단일 요청
# =========================
def _fetch_t8410_once(token: str, symbol: str, edate: str, cts_date: str = "") -> dict:
    """
    t8410 일봉 조회 (gubun=2)
    edate   : 조회 종료일 (YYYYMMDD)
    cts_date: 연속조회 키 (첫 조회시 공백)
    반환: {"rows": [...], "cts_date": str, "has_next": bool}
    """
    headers = {
        "content-type":  "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd":         "t8410",
        "tr_cont":       "Y" if cts_date else "N",
        "tr_cont_key":   cts_date
    }

    body = {
        "t8410InBlock": {
            "shcode":   symbol,
            "gubun":    "2",      # 2 = 일봉
            "qrycnt":   500,      # 1회 최대 500봉
            "sdate":    "",
            "edate":    edate,
            "cts_date": cts_date,
            "comp_yn":  "N"
        }
    }

    time.sleep(0.5)

    res = requests.post(
        f"{BASE_URL}/{CHART_PATH}",
        headers=headers,
        json=body,
        timeout=10
    )

    if res.status_code != 200:
        raise RuntimeError(f"API_FAILED: {symbol} -> {res.status_code} {res.text}")

    data = res.json()

    rsp_cd = data.get("rsp_cd", "")
    if rsp_cd not in ("", "00000"):
        raise RuntimeError(f"API_ERROR: {symbol} -> {data.get('rsp_msg', rsp_cd)}")

    rows = data.get("t8410OutBlock1", [])

    # 연속조회 키
    next_cts = ""
    out_block = data.get("t8410OutBlock", {})
    if isinstance(out_block, dict):
        next_cts = str(out_block.get("cts_date", "")).strip()

    has_next = bool(next_cts) and next_cts != "00000000" and len(rows) >= 500

    return {"rows": rows, "cts_date": next_cts, "has_next": has_next}


# =========================
# 종목 1개 5년치 수집
# =========================
def fetch_daily_ohlcv(token: str, symbol: str, years: int = 5) -> pd.DataFrame:
    edate    = datetime.now().strftime("%Y%m%d")
    sdate    = (datetime.now() - timedelta(days=365 * years + 30)).strftime("%Y%m%d")
    cts_date = ""
    all_rows = []

    print(f"  [{symbol}] 수집 시작 ({sdate} ~ {edate})")

    for page in range(1, 20):
        try:
            result = _fetch_t8410_once(token, symbol, edate, cts_date)
        except RuntimeError as e:
            print(f"  ⚠️ [{symbol}] 페이지{page} 실패: {e}")
            break

        rows = result["rows"]
        if not rows:
            break

        all_rows.extend(rows)
        print(f"  [{symbol}] 페이지{page}: {len(rows)}봉 (누적: {len(all_rows)}봉)")

        # 시작일 이전 데이터면 종료
        last_date = str(rows[-1].get("date", ""))
        if last_date and last_date <= sdate:
            break

        if not result["has_next"]:
            break

        cts_date = result["cts_date"]

    if not all_rows:
        print(f"  ⚠️ [{symbol}] 데이터 없음")
        return pd.DataFrame()

    # DataFrame 변환
    df = pd.DataFrame(all_rows)

    rename_map = {
        "date":      "date",
        "open":      "open",
        "high":      "high",
        "low":       "low",
        "close":     "close",
        "jdiff_vol": "volume",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    required = ["date", "open", "high", "low", "close", "volume"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        print(f"  ⚠️ [{symbol}] 필드 누락: {missing}")
        return pd.DataFrame()

    df = df[required].copy()
    df["date"]   = df["date"].astype(str)
    df["open"]   = pd.to_numeric(df["open"],   errors="coerce")
    df["high"]   = pd.to_numeric(df["high"],   errors="coerce")
    df["low"]    = pd.to_numeric(df["low"],    errors="coerce")
    df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    df = df.dropna()
    df = df[df["volume"] > 0]
    df = df[df["date"] >= sdate]
    df = df.sort_values("date").reset_index(drop=True)

    return df


# =========================
# 전체 종목 수집
# =========================
def collect_all(token: str, symbols: list, years: int = 5):
    total   = len(symbols)
    success = 0
    failed  = []

    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{total}] {symbol} 수집 중...")

        try:
            df = fetch_daily_ohlcv(token, symbol, years)

            if df.empty:
                failed.append(symbol)
                continue

            out_path = os.path.join(OUTPUT_DIR, f"{symbol}.csv")
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
    app_key    = os.getenv("LS_APP_KEY")
    app_secret = os.getenv("LS_APP_SECRET")

    if not app_key or not app_secret:
        print("❌ .env 파일에 LS_APP_KEY / LS_APP_SECRET 설정 필요")
        sys.exit(1)

    print("토큰 발급 중...")
    token = get_access_token(app_key, app_secret)
    print("✅ 토큰 발급 완료")

    # universe 에서 종목 읽기
    universe_path = os.path.join(PROJECT_ROOT, "UNIVERSE", "stock_universe.json")
    if not os.path.exists(universe_path):
        print(f"❌ universe 파일 없음: {universe_path}")
        sys.exit(1)

    with open(universe_path, "r", encoding="utf-8") as f:
        symbols = json.load(f).get("symbols", [])

    if not symbols:
        print("❌ universe 종목 없음")
        sys.exit(1)

    print(f"수집 대상: {len(symbols)}개 종목 / {5}년치 일봉")
    collect_all(token, symbols, years=5)
