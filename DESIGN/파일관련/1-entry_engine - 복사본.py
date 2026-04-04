def process_exits(mode, state, strategy_path):

    if not isinstance(state, dict):
        return {}

    positions = state.get("positions", {})
    if not isinstance(positions, dict):
        return {}

    exit_results = {}

    for symbol, pos in positions.items():

        if not isinstance(pos, dict):
            continue

        asset = pos.get("asset_type", "STOCK")

        # 전략 선택
        if asset == "STOCK":
            strategy_folder = "stock_A"
        else:
            strategy_folder = "crypto_A"

        import os, yaml
        path = os.path.join(strategy_path, strategy_folder, "exit_rules.yaml")

        try:
            with open(path, "r") as f:
                rules = yaml.safe_load(f)
        except:
            continue

        exit_rule = rules.get("exit", {})

        tp = exit_rule.get("take_profit")
        sl = exit_rule.get("stop_loss")
        max_hold = exit_rule.get("max_hold")

        entry_price = pos.get("entry_price")
        current_price = pos.get("price")

        if not entry_price or not current_price:
            continue

        pnl = (current_price - entry_price) / entry_price
        hold = pos.get("hold_bars", 0)

        if tp and pnl >= tp:
            exit_results[symbol] = "EXIT"
            continue

        if sl and pnl <= -sl:
            exit_results[symbol] = "EXIT"
            continue

        if max_hold and hold >= max_hold:
            exit_results[symbol] = "EXIT"
            continue

        pos["hold_bars"] = hold + 1

    return exit_results