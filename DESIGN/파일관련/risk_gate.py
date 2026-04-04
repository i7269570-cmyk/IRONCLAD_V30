def validate_risk_and_size(signal, state, system_config):
    try:
        total_capital = state.get("capital", {}).get("total", 0)

        if total_capital <= 0:
            return {"allowed": False, "reason": "NO_CAPITAL"}

        asset_type = signal.get("asset_type")
        entry_price = signal.get("price")

        if not entry_price or entry_price <= 0:
            return {"allowed": False, "reason": "INVALID_PRICE"}

        # =========================
        # 1. 포지션 제한
        # =========================
        positions = list(state.get("positions", {}).values())  # ✅ 수정된 부분

        if len(positions) >= 2:
            return {"allowed": False, "reason": "MAX_POSITIONS"}

        for p in positions:
            if p.get("asset_type") == asset_type:
                return {"allowed": False, "reason": "SAME_ASSET_BLOCK"}

        # =========================
        # 2. 자금 버킷
        # =========================
        if asset_type == "STOCK":
            bucket_cap = state.get("capital", {}).get("stock_alloc", 0)
        else:
            bucket_cap = state.get("capital", {}).get("crypto_alloc", 0)

        if bucket_cap <= 0:
            return {"allowed": False, "reason": "NO_BUCKET"}

        # =========================
        # 3. 리스크 계산
        # =========================
        risk_amount = total_capital * 0.005

        # ⚠️ ATR 연결 전 임시 (추후 교체)
        atr_stop = entry_price * 0.01

        if atr_stop <= 0:
            return {"allowed": False, "reason": "INVALID_STOP"}

        qty = risk_amount / atr_stop
        position_value = qty * entry_price

        # =========================
        # 4. 버킷 제한
        # =========================
        if position_value > bucket_cap:
            qty = bucket_cap / entry_price

        # =========================
        # 5. 최소 수량
        # =========================
        lot_size = 1
        qty = (qty // lot_size) * lot_size

        if qty <= 0:
            return {"allowed": False, "reason": "QTY_ZERO"}

        # =========================
        # 6. 통과
        # =========================
        return {
            "allowed": True,
            "size": qty,
            "reason": "OK"
        }

    except Exception as e:
        return {"allowed": False, "reason": f"ERROR: {str(e)}"}