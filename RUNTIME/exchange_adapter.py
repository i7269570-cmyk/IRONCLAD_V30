# RUNTIME/exchange_adapter.py

import os
from dotenv import load_dotenv

load_dotenv()


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise RuntimeError(f"SAFE_HALT: Missing ENV -> {key}")
    return value


def get_positions():
    positions = {}

    positions.update(get_ls_positions())
    positions.update(get_upbit_positions())

    return positions


# ==============================
# LS증권
# ==============================

def get_ls_positions():
    _require_env("LS_APP_KEY")
    _require_env("LS_APP_SECRET")

    return {}


# ==============================
# Upbit
# ==============================

import requests
import jwt
import uuid


def get_upbit_positions():
    access_key = _require_env("UPBIT_ACCESS_KEY")
    secret_key = _require_env("UPBIT_SECRET_KEY")

    url = _require_env("UPBIT_API_URL")  # ✅ 하드코딩 제거

    payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4())
    }

    jwt_token = jwt.encode(payload, secret_key)

    headers = {
        "Authorization": f"Bearer {jwt_token}"
    }

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        raise RuntimeError("SAFE_HALT: Upbit API error")

    data = res.json()

    result = {}

    for item in data:
        currency = item["currency"]
        balance = float(item["balance"])

        if balance > 0:
            result[currency] = balance

    return result