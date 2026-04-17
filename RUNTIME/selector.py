import os
import yaml
import json
import logging
from typing import List, Dict, Any

# [1] BASE_DIR: 절대경로 기준점 (상태 관리용)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger = logging.getLogger("IRONCLAD_RUNTIME.SELECTOR")

def select_candidates(data: List[Dict[str, Any]], strategy_path: str) -> List[Dict[str, Any]]:
    if not data:
        return []

    try:
        # [1] 규칙 로드 (YAML 계약 복구: selector_rules 제거)
        rules_file = os.path.join(strategy_path, "selection_rules.yaml")
        if not os.path.exists(rules_file):
            raise RuntimeError(f"SELECTOR_RULES_MISSING: {rules_file}")

        with open(rules_file, 'r', encoding='utf-8') as f:
            # 🎯 수정: YAML 구조와 직접 일치 (KeyError 방지)
            rules = yaml.safe_load(f)

        # [2] 시장 통계 (데이터 무결성 검사)
        valid_data = [d for d in data if "history" in d and len(d["history"]) > 0]
        if not valid_data:
            return []

        # [3] Market Check
        m_check = rules["market_check"]
        if m_check.get("enabled", False):
            # 필요한 경우 시장 진단 로직 수행
            pass

        # [4] 1차 필터링 (Liquidity & Volatility)
        # 🎯 SSOT 준수: .get() 대신 직접 참조로 데이터 누락 시 에러 발생 유도
        f_cfg = rules["filter"]
        liq_sorted = sorted(valid_data, key=lambda x: x["current"]["value"], reverse=True)
        liq_candidates = liq_sorted[:f_cfg["liquidity"]["top_n"]]
        
        vol_sorted = sorted(liq_candidates, key=lambda x: x["history"][-1].get("atr_percent", 0), reverse=True)
        intermediate = vol_sorted[:f_cfg["volatility"]["top_n"]]

        # [5] 랭킹 및 가중치 점수 계산
        rank_weights = {item["field"]: item["weight"] for item in rules["ranking"]}
        
        def calculate_score(x: Dict[str, Any]) -> float:
            score = 0.0
            last_row = x["history"][-1]
            curr_info = x["current"]
            for field, weight in rank_weights.items():
                # 필드 존재 강제 확인 (SSOT 위반 방지)
                val = last_row.get(field) if field in last_row else curr_info[field]
                score += float(val) * weight
            return score

        # [6] 최종 선발 및 자산별 분리 저장
        final_sorted = sorted(intermediate, key=calculate_score, reverse=True)
        final_top_k = rules["selection"]["final_top_k"]
        final_selection = final_sorted[:final_top_k]

        _save_selected_symbols(final_selection)
        return final_selection

    except Exception as e:
        logger.error(f"SELECTOR_HALT: {str(e)}")
        raise RuntimeError(f"SAFE_HALT_TRIGGERED: {str(e)}")

def _save_selected_symbols(final_selection: List[Dict[str, Any]]):
    symbols = [item["symbol"] for item in final_selection]
    state_dir = os.path.join(BASE_DIR, "STATE")
    os.makedirs(state_dir, exist_ok=True)

    # 자산 타입 자동 판별 (주식: . 포함 / 코인: 미포함)
    stock_symbols = [s for s in symbols if "." in s]
    coin_symbols = [s for s in symbols if "." not in s]

    # 자산별 JSON 물리적 분리 저장
    if stock_symbols:
        with open(os.path.join(state_dir, "selected_symbols_stock.json"), "w", encoding="utf-8") as f:
            json.dump(stock_symbols, f, indent=2, ensure_ascii=False)

    if coin_symbols:
        with open(os.path.join(state_dir, "selected_symbols_coin.json"), "w", encoding="utf-8") as f:
            json.dump(coin_symbols, f, indent=2, ensure_ascii=False)

    # 통합본 (기존 시스템 호환용)
    with open(os.path.join(state_dir, "selected_symbols.json"), "w", encoding="utf-8") as f:
        json.dump(symbols, f, indent=2, ensure_ascii=False)