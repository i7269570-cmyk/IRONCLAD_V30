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
        price = sig["price"]
        symbol = sig["symbol"]

        # 1. Required Field Validation
        required = ["price", "symbol", "side"]
        for r in required:
            if r not in sig:
                raise KeyError(f"MISSING_REQUIRED_FIELD_IN_SIG: {r}")

        # 2. Minimum Value Check (Liquidity)
        if market_data["value"] < constraints["liquidity"]["min_value"]:
            return False

        # 3. Volume Ratio Check (Anomaly Detection)
        if "volume_ratio" not in market_data:
            raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'volume_ratio' missing in market_data.")
            
        if market_data["volume_ratio"] < constraints["liquidity"]["min_volume_ratio"]:
            return False

        # 4. Price Deviation Check (Spread Replacement)
        # [V31.25 Update] Removed bid/ask reference -> use market_data["price"]
        if "price" not in market_data:
            raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'price' missing in market_data.")

        m_price = market_data["price"]
        price_diff_pct = abs(m_price - price) / price

        if price_diff_pct > constraints["spread"]["max_spread_pct"]:
            return False

        # 5. Slippage Protection
        # Refers to order_max_slippage_pct in execution_constraints.yaml
        if price_diff_pct > constraints["slippage"]["order_max_slippage_pct"]:
            return False

        # 6. Duplicate Position Check
        if constraints["safety"]["forbid_duplicate_position"]:
            if symbol in state["positions"]:
                return False

        # 7. Same Asset Group Check (Correlation Risk)
        if constraints["safety"]["forbid_same_asset_group"]:
            if "asset_group" not in sig:
                raise RuntimeError("PRE_ORDER_CHECK_FAULT: 'asset_group' missing in sig.")
            
            asset_group = sig["asset_group"]
            for pos in state["positions"].values():
                if "asset_group" not in pos:
                    raise RuntimeError(f"PRE_ORDER_CHECK_FAULT: 'asset_group' missing in state position.")
                
                if pos["asset_group"] == asset_group:
                    return False

        return True

    except Exception as e:
        # All exceptions propagate to run.py to trigger SAFE_HALT
        if isinstance(e, (RuntimeError, KeyError)):
            raise e
        raise RuntimeError(f"PRE_ORDER_CHECK_CRITICAL_FAIL: {str(e)}")