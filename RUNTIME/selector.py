# ============================================================
# IRONCLAD_V31.24 - Selector Integrity (Zero-Tolerance Top_K)
# ============================================================
import os
import yaml
import json
import logging
from typing import List, Dict, Any

# [Standard] Logging interface
logger = logging.getLogger("IRONCLAD_RUNTIME.SELECTOR")

def save_selected_symbols(final_selection: List[Dict[str, Any]]):
    """
    [V31.24 추가] 선택된 심볼을 콘솔에 출력하고 파일로 저장
    """
    try:
        symbols = [item["symbol"] for item in final_selection]

        print("\n[SELECTED SYMBOLS]")
        for s in symbols:
            print(f"- {s}")

        # STATE 디렉토리 보장
        os.makedirs("STATE", exist_ok=True)

        # 원자적 기록 (JSON)
        with open("STATE/selected_symbols.json", "w", encoding="utf-8") as f:
            json.dump(symbols, f, indent=2, ensure_ascii=False)
            
        logger.info(f"SELECTOR_SYMBOLS_SAVED: {len(symbols)} items")

    except Exception as e:
        # 결함 은폐 금지 원칙 준수
        raise RuntimeError(f"SELECTOR_SAVE_FAILED: {str(e)}")

def select_candidates(data: List[Dict[str, Any]], strategy_path: str) -> List[Dict[str, Any]]:
    """
    입력: data(list[dict]), strategy_path(str)
    출력: list[dict]
    기능: 
    1. top_k 설정 내 'stock', 'crypto' 필드 누락 시 즉시 RuntimeError를 발생시킨다.
    2. get(..., 0)과 같은 자동 보정(Default Value) 로직을 전면 폐기한다.
    """

    if not data:
        return []

    try:
        rules_file = os.path.join(strategy_path, "selection_rules.yaml")

        if not os.path.exists(rules_file):
            raise RuntimeError(f"SELECTOR_RULES_MISSING: {rules_file}")

        with open(rules_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if "selector_rules" not in config:
            raise RuntimeError("SELECTOR_CONFIG_ERROR: 'selector_rules' root missing")

        rules = config["selector_rules"]
        
        # [Standard] Section Presence Validation
        required_sections = ["universe", "ranking", "top_k", "weights"]
        for section in required_sections:
            if section not in rules:
                raise RuntimeError(f"SELECTOR_CONFIG_ERROR: '{section}' section missing")

        u_cfg = rules["universe"]
        ranking_cfg = rules["ranking"]
        topk_cfg = rules["top_k"]
        weights_cfg = rules["weights"]

        # [Standard] Weights Validation (No Default)
        if "change_rate" not in weights_cfg or "value" not in weights_cfg:
            raise RuntimeError("SELECTOR_CONFIG_ERROR: weights must include 'change_rate' and 'value'")

        # 1. Universe Scoring (Strict Validation)
        top_n = u_cfg["top_n"]

        def calculate_score(x: Dict[str, Any]) -> float:
            if "change_rate" not in x:
                raise RuntimeError(f"MISSING_FIELD: change_rate {x.get('symbol', 'UNKNOWN')}")
            if "value" not in x:
                raise RuntimeError(f"MISSING_FIELD: value {x.get('symbol', 'UNKNOWN')}")
            
            return (
                x["change_rate"] * weights_cfg["change_rate"] + 
                x["value"] * weights_cfg["value"]
            )

        universe_sorted = sorted(data, key=calculate_score, reverse=True)
        intermediate_candidates = universe_sorted[:top_n]

        # 2. Ranking (Strict Field Validation)
        final_sorted = intermediate_candidates
        for rank_rule in reversed(ranking_cfg):
            field = rank_rule["field"]
            order = rank_rule["order"]
            is_reverse = True if order == "desc" else False
            
            for item in final_sorted:
                if field not in item:
                    raise RuntimeError(f"SELECTOR_FIELD_MISSING: {field}")

            final_sorted = sorted(final_sorted, key=lambda x: x[field], reverse=is_reverse)

        # --------------------------------------------------------
        # [V31.24] Top_K Validation (No Default / No get)
        # --------------------------------------------------------
        # 🔥 필드 누락 시 즉시 RuntimeError (get 제거됨)
        if "stock" not in topk_cfg:
            raise RuntimeError("MISSING_TOPK_CONFIG: stock")

        if "crypto" not in topk_cfg:
            raise RuntimeError("MISSING_TOPK_CONFIG: crypto")

        stock_limit = topk_cfg["stock"]
        crypto_limit = topk_cfg["crypto"]

        final_candidates = []
        stock_count = 0
        crypto_count = 0

        for item in final_sorted:
            a_type = item.get("asset_type")
            if a_type == "STOCK":
                if stock_count < stock_limit:
                    final_candidates.append(item)
                    stock_count += 1
            elif a_type == "CRYPTO":
                if crypto_count < crypto_limit:
                    final_candidates.append(item)
                    crypto_count += 1
            else:
                raise RuntimeError(f"SELECTOR_UNKNOWN_ASSET_TYPE: {a_type}")

        # 🔴 [V31.24 추가] 선택 결과 저장 및 출력 호출
        save_selected_symbols(final_candidates)

        logger.info(f"SELECTOR_SUCCESS: Stock({stock_count}), Crypto({crypto_count})")
        return final_candidates

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise e
        raise RuntimeError(f"SELECTOR_FAILURE: {str(e)}")