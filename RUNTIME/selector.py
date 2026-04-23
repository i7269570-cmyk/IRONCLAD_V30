import os
import yaml
import logging
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = logging.getLogger("IRONCLAD_RUNTIME.SELECTOR")

def select_candidates(data: List[Dict[str, Any]], strategy_path: str, asset_type: str) -> List[Dict[str, Any]]:
    if not data:
        return []

    try:
        rules_file = os.path.join(strategy_path, asset_type, "selection_rules.yaml")

        if not os.path.exists(rules_file):
            raise RuntimeError(f"SELECTOR_RULES_MISSING: {rules_file}")

        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)

        # history 있는 항목만 처리
        valid_data = [d for d in data if "history" in d and len(d["history"]) > 0]

        if not valid_data:
            return []

        # [1차 필터링 (Liquidity)]
        f_cfg = rules["filter"]
        liq_sorted = sorted(valid_data, key=lambda x: x["current"]["value"], reverse=True)
        liq_candidates = liq_sorted[:f_cfg["liquidity"]["top_n"]]

        # [랭킹 및 가중치]
        rank_weights = {item["field"]: item["weight"] for item in rules["ranking"]}

        def calculate_score(x: Dict[str, Any]) -> float:
            score = 0.0
            last_row = x["history"].iloc[-1]
            curr_info = x["current"]
            for field, weight in rank_weights.items():
                if field in last_row:
                    val = last_row[field]
                elif field in curr_info:
                    val = curr_info[field]
                else:
                    raise RuntimeError(f"SELECTOR_FIELD_MISSING: {field}")
                score += float(val) * weight
            return score

        final_sorted = sorted(liq_candidates, key=calculate_score, reverse=True)
        final_top_k = rules["selection"]["final_top_k"]
        final_selection = final_sorted[:final_top_k]

        return final_selection

    except Exception as e:
        logger.error(f"SELECTOR_HALT: {str(e)}")
        raise RuntimeError(f"SAFE_HALT_TRIGGERED: {str(e)}")
