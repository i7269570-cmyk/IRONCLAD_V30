# ============================================================
# IRONCLAD_V31.4 - Risk Gate (Total Exposure Enforcement)
# ============================================================

def validate_risk_and_size(signal, state, system_config):
    """
    입력: signal(dict), state(dict), system_config(dict)
    출력: dict {allowed: bool, size: float}
    기능: 신규 포지션의 노출액을 포함한 총 노출(Total Exposure)이 한도를 초과하는지 검증한다.
    """

    # =========================
    # 🔵 1. 입력 방어 및 기본 검증
    # =========================
    if not isinstance(signal, dict) or not isinstance(state, dict) or not isinstance(system_config, dict):
        return {"allowed": False, "size": 0}

    symbol = signal.get("symbol")
    price = signal.get("price")
    asset_type = signal.get("asset_type")

    if not symbol or price is None or not asset_type:
        return {"allowed": False, "size": 0}

    # =========================
    # 🔵 2. system_config SSOT 검증 (기본값 제거)
    # =========================
    if "risk_limits" not in system_config:
        raise RuntimeError("SCHEMA_VIOLATION: 'risk_limits' section missing")

    risk_limits = system_config["risk_limits"]
    required_keys = [
        "max_positions",
        "max_per_asset",
        "max_total_exposure_pct",
        "max_daily_loss_pct",
    ]

    for key in required_keys:
        if key not in risk_limits or risk_limits[key] is None:
            raise RuntimeError(f"SSOT_MISSING_{key.upper()}")

    max_total_exposure_pct = risk_limits["max_total_exposure_pct"]
    max_daily_loss_pct = risk_limits["max_daily_loss_pct"]

    # =========================
    # 🔵 3. 자본 및 상태 데이터 확보
    # =========================
    if "capital" not in state or "positions" not in state or "daily_pnl" not in state:
        raise RuntimeError("RISK_GATE_STATE_INCOMPLETE")

    total_capital = state["capital"].get("total", 0)
    if total_capital <= 0:
        raise RuntimeError("RISK_GATE_INVALID_CAPITAL")

    # 일일 손실 제한 검증 (HALT 트리거)
    if state["daily_pnl"] <= -(total_capital * max_daily_loss_pct):
        raise RuntimeError("RISK_GATE_DAILY_LOSS_LIMIT")

    # =========================
    # 🔵 4. 기초 리스크 한도 검증 (수량/자산군)
    # =========================
    if len(state["positions"]) >= risk_limits["max_positions"]:
        return {"allowed": False, "size": 0}

    same_asset_count = sum(
        1 for pos in state["positions"].values() 
        if isinstance(pos, dict) and pos.get("asset_type") == asset_type
    )
    if same_asset_count >= risk_limits["max_per_asset"]:
        return {"allowed": False, "size": 0}

    # =========================
    # 🔵 5. 전략 기반 포지션 사이징 (Size 계산)
    # =========================
    risk_per_trade = signal.get("risk_per_trade")
    stop_distance = signal.get("stop_distance")

    if not risk_per_trade or not stop_distance or risk_per_trade <= 0 or stop_distance <= 0:
        return {"allowed": False, "size": 0}

    # 사이징 계산
    size = (total_capital * risk_per_trade) / stop_distance
    if size <= 0:
        return {"allowed": False, "size": 0}

    # =========================
    # 🔵 6. [V31.4] 총 노출 한도 검증 (신규 진입 포함)
    # =========================
    # [계약 1] 현재 노출 계산 (state["positions"] 내 volume 및 price 기반)
    current_exposure = 0
    for pos in state["positions"].values():
        if "price" not in pos or "volume" not in pos:
             raise RuntimeError(f"POSITION_DATA_INCOMPLETE: {pos.get('symbol')}")
        current_exposure += pos["price"] * pos["volume"]

    # [계약 2] 신규 포지션 노출 계산
    new_exposure = price * size

    # [계약 3] 총 노출 및 한도 계산
    total_exposure = current_exposure + new_exposure
    max_exposure_allowed = max_total_exposure_pct * total_capital

    # [계약 4] 한도 초과 시 진입 거부 (자동 보정 금지)
    if total_exposure > max_exposure_allowed:
        return {"allowed": False, "size": 0}

    # =========================
    # 🔵 7. 최종 승인
    # =========================
    return {
        "allowed": True,
        "size": size
    }