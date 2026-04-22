import os
import json
import requests
import re
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "UNIVERSE")

# =========================
# 1. 주식 수집
# =========================
def build_stock_universe():
    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://finance.naver.com/sise/sise_quant.naver"
    res = requests.get(url, headers=headers)

    code_pattern = re.compile(r"/item/main\.naver\?code=(\d+)")
    matches = code_pattern.findall(res.text)

    symbols = []
    seen = set()

    for code in matches:
        if code not in seen:
            symbols.append(code)
            seen.add(code)
        if len(symbols) >= 50:
            break

    if "069500" not in symbols:
        symbols.insert(0, "069500")

    return symbols[:50]

# =========================
# 2. 코인 수집
# =========================
def build_coin_universe():
    url = "https://api.upbit.com/v1/market/all"
    res = requests.get(url)
    data = res.json()

    symbols = [item["market"] for item in data if item["market"].startswith("KRW-")]

    return symbols[:50]

# =========================
# 3. 안전 저장 (atomic write)
# =========================
def atomic_write(file_path, data):
    tmp_path = file_path + ".tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_path, file_path)  # 원자 교체

# =========================
# 4. 실행
# =========================
if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 주식
    stock_list = build_stock_universe()
    stock_path = os.path.join(OUTPUT_DIR, "stock_universe.json")

    atomic_write(stock_path, {
        "symbols": stock_list,
        "updated_at": str(datetime.now())
    })

    print(f"🔥 STOCK SUCCESS: {len(stock_list)} symbols extracted.")

    # 코인
    coin_list = build_coin_universe()
    coin_path = os.path.join(OUTPUT_DIR, "coin_universe.json")

    atomic_write(coin_path, {
        "symbols": coin_list,
        "updated_at": str(datetime.now())
    })

    print(f"🔥 COIN SUCCESS: {len(coin_list)} symbols extracted.")