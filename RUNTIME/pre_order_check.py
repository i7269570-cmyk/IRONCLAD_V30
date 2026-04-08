# ============================================================
# IRONCLAD_V31.23 - Pre-Order Integrity Gate (Exception Ready)
# ============================================================

def validate_before_order(sig: dict, market_data: dict, constraints: dict, state: dict):
    """
    [V31.23] 실행 가능성 최종 검증 게이트
    - 논리적 거부 시: False 반환 (정상 흐름)
    - 시스템 결함 시: Exception 발생 (SAFE_HALT 트리거)
    """

    try:
        price = sig["price"]
        symbol = sig["symbol"]

        # 1. 필수 필드 검증 (데이터 계약 확인)
        required = ["price", "symbol", "side"]
        for r in required:
            if r not in sig:
                # 필드 누락은 시스템 결함으로 간주하여 에러 발생 가능성 존재 (하단 except에서 포착)
                raise KeyError(f"MISSING_REQUIRED_FIELD: {r}")

        # 2. 거래대금 체크 (유동성 검증)
        if market_data["value"] < constraints["liquidity"]["min_value"]:
            return False

        # 3. 거래량 비율 (이상 거래 감지)
        if market_data.get("volume_ratio", 0) < constraints["liquidity"]["min_volume_ratio"]:
            return False

        # 4. 스프레드 (시장가 진입 리스크)
        bid = market_data["bid"]
        ask = market_data["ask"]
        spread_pct = (ask - bid) / price

        if spread_pct > constraints["spread"]["max_spread_pct"]:
            return False

        # 5. 슬리피지 예상 (체결가 보호)
        expected_slippage = abs(ask - price) / price
        if expected_slippage > constraints["slippage"]["max_slippage_pct"]:
            return False

        # 6. 중복 포지션 금지 (동일 심볼 제한)
        if constraints["safety"]["forbid_duplicate_position"]:
            if symbol in state["positions"]:
                return False

        # 7. 동일 자산군 금지 (상관관계 리스크 관리)
        if constraints["safety"]["forbid_same_asset_group"]:
            asset_group = sig.get("asset_group")
            for pos in state["positions"].values():
                if pos.get("asset_group") == asset_group:
                    return False

        return True

    except Exception as e:
        # 🔴 [V31.23 핵심] 예외를 절대 삼키지 않고 상위(run.py)로 전파
        # 이로 인해 데이터 결함 발생 시 즉시 SAFE_HALT가 작동함
        raise RuntimeError(f"PRE_ORDER_CHECK_CRITICAL_FAIL: {str(e)}")