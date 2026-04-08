import os
import yaml
import pandas as pd

def filter_by_strategy(market_data: list, strategy_path: str):

    spec_file = os.path.join(strategy_path, "strategy_spec.yaml")
    with open(spec_file, 'r', encoding='utf-8') as f:
        spec = yaml.safe_load(f)

    strategies = spec.get("strategies", [])

    enabled_strategies = [
        s["name"] for s in strategies if s.get("enabled", False)
    ]

    if not enabled_strategies:
        raise ValueError("NO_ENABLED_STRATEGY")

    # 현재 구조에서는 단일 전략만 사용
    selected_strategy = enabled_strategies[0]

    df = pd.DataFrame(market_data)

    # 기본 필터 (필요 최소만 유지)
    candidates = df.nlargest(50, 'value')

    return candidates.to_dict('records')
    
    
    
    raise RuntimeError("TEST FAIL")