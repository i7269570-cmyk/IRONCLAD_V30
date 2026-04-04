import yaml

def load_active_strategies(spec_path: str):
    with open(spec_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    strategies = data.get("active_strategies", [])

    if not strategies:
        raise RuntimeError("NO_ACTIVE_STRATEGIES_DEFINED")

    for s in strategies:
        if "id" not in s or "path" not in s:
            raise RuntimeError("INVALID_STRATEGY_SPEC_FORMAT")

    return strategies