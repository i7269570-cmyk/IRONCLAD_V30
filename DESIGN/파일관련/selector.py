import os
import yaml
import logging
from typing import List, Dict, Any

logger = logging.getLogger("IRONCLAD_RUNTIME.SELECTOR")

def select_candidates(data: List[Dict[str, Any]], strategy_path: str) -> List[Dict[str, Any]]:

    if not data:
        return []

    try:
        rules_file = os.path.join(strategy_path, "selection_rules.yaml")

        with open(rules_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        weights = config['weights']
        top_k = config.get("top_k", 50)

        scored_list = []

        for item in data:
            val_score = item['value'] * weights['value']
            chg_score = item['change_rate'] * weights['change_rate']

            scored_item = dict(item)
            scored_item['selection_score'] = val_score + chg_score
            scored_list.append(scored_item)

        sorted_list = sorted(
            scored_list,
            key=lambda x: x['selection_score'],
            reverse=True
        )

        final_candidates = sorted_list[:top_k]

        logger.info(f"SELECTOR: Final selection complete ({len(final_candidates)} assets).")

        return final_candidates

    except Exception as e:
        raise RuntimeError(f"SELECTOR_FAILURE: {str(e)}")