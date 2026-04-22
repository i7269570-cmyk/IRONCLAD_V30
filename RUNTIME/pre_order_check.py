# ============================================================
# IRONCLAD_V31.25 - Pre-Order Integrity Gate (Strict Contract)
# ============================================================

def validate_before_order(sig: dict, market_data: dict, constraints: dict, state: dict):
    """
    [V31.25] Final Execution Validation Gate
    - Logic Rejection: Returns False
    - System Fault: Raises Exception (Triggers SAFE_HALT)
    """

    try:
        # Validate constraints schema
        if "safety" not in constraints:
            raise RuntimeError("CONSTRAINTS_SCHEMA_VIOLATION: safety missing")

        if "forbid_same_asset_group" not in constraints["safety"]:
            raise RuntimeError("CONSTRAINTS_SCHEMA_VIOLATION: forbid_same_asset_group missing")

        # Validate state schema
        if "positions" not in state:
            raise RuntimeError("STATE_SCHEMA_VIOLATION: positions missing")

        required_fields = ["symbol", "price", "side"]
        for field in required_fields:
            if field not in sig:
                raise RuntimeError(f"REQUIRED_FIELD_MISSING: {field}")

        price = sig["price"]
        symbol = sig["symbol"]

        # 2. Minimum Value Check (Liquidity)
        if "min_daily_volume_value" not in constraints["liquidity"]:
            raise RuntimeError("CONSTRAINTS_SCHEMA_VIOLATION: min_daily_volume_value missing")

        if market_data["value"] < constraints["liquidity"]["min_daily_volume_value"]:
            return False

        # 3. Volume Ratio Check (Anomaly Detection)
        if "volume_ratio" not in market_data:
            raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'volume_ratio' missing in market_data.")

        if market_data["volume_ratio"] < constraints["liquidity"]["min_volume_ratio"]:
            return False

        # 4. Price Deviation Check (close 기준)
        if "close" not in market_data:
            raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'close' missing in market_data.")

        m_price = market_data["close"]
        price_diff_pct = abs(m_price - price) / price

        if price_diff_pct > constraints["spread"]["max_spread_pct"]:
            return False

        # 5. Slippage Protection
        if price_diff_pct > constraints["slippage"]["order_max_slippage_pct"]:
            return False

        # 6. Anti-Duplicate Order
        if symbol in state["positions"]:
            return False

        if state.get("pending_orders", {}).get(symbol):
            raise RuntimeError(f"PENDING_ORDER_EXISTS: {symbol}")

        # 7. Same Asset Group Check
        if constraints["safety"]["forbid_same_asset_group"]:
            if "asset_group" not in sig:
                raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'asset_group' missing in sig.")

            asset_group = sig["asset_group"]
            for pos in state["positions"].values():
                if "asset_group" not in pos:
                    raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'asset_group' missing in state position.")

                if pos["asset_group"] == asset_group:
                    return False

        return True

    except Exception as e:
        if isinstance(e, (RuntimeError, KeyError)):
            raise e
        raise RuntimeError(f"PRE_ORDER_CHECK_CRITICAL_FAIL: {str(e)}")
