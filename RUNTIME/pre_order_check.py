# ============================================================
# IRONCLAD_V31.24 - Pre-Order Integrity Gate (Strict Contract)
# ============================================================

def validate_before_order(sig: dict, market_data: dict, constraints: dict, state: dict):
    """
    [V31.24] 실행 가능성 최종 검증 게이트
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
                raise KeyError(f"MISSING_REQUIRED_FIELD_IN_SIG: {r}")

        # 2. 거래대금 체크 (유동성 검증)
        if market_data["value"] < constraints["liquidity"]["min_value"]:
            return False

        # 3. 거래량 비율 (이상 거래 감지)
        # 🔴 [V31.24 수정] .get 및 기본값 제거 -> 명시적 검증
        if "volume_ratio" not in market_data:
            raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'volume_ratio' missing in market_data.")
            
        if market_data["volume_ratio"] < constraints["liquidity"]["min_volume_ratio"]:
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
            # 🔴 [V31.24 수정] sig.get("asset_group") 제거 -> 직접 참조
            if "asset_group" not in sig:
                raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'asset_group' missing in sig.")
            
            asset_group = sig["asset_group"]
            for pos in state["positions"].values():
                # 포지션 데이터 내 asset_group 존재 여부도 엄격히 확인
                if "asset_group" not in pos:
                    raise RuntimeError(f"PRE_ORDER_CHECK_FAULT: 'asset_group' missing in state position.")
                
                if pos["asset_group"] == asset_group:
                    return False

        return True

    except Exception as e:
        # 모든 예외는 상위(run.py)로 전파되어 SAFE_HALT 트리거
        if isinstance(e, (RuntimeError, KeyError)):
            raise e
        raise RuntimeError(f"PRE_ORDER_CHECK_CRITICAL_FAIL: {str(e)}")