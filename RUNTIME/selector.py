# ============================================================
# IRONCLAD_V31.34 - Data Integrity & Strict-Contract Selector
# ============================================================
import os
import yaml
import json
import logging
from typing import List, Dict, Any

# [1] BASE_DIR 정의: 상대경로 의존성 제거를 위한 절대경로 기준점 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("IRONCLAD_RUNTIME.SELECTOR")

def select_candidates(data: List[Dict[str, Any]], strategy_path: str) -> List[Dict[str, Any]]:
    """
    기능: 
    1. 데이터 구조 {symbol, current, history}를 유지하며 필터링 및 랭킹 수행.
    2. list 구조의 history 데이터를 기반으로 시장 진단 및 필터링 수행.
    """
    if not data:
        return []

    try:
        # [1] 규칙 로드 (SSOT 준수)
        rules_file = os.path.join(strategy_path, "selection_rules.yaml")
        if not os.path.exists(rules_file):
            raise RuntimeError(f"SELECTOR_RULES_MISSING: {rules_file}")

        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)["selector_rules"]

        # [2] 시장 통계 필드 계산 (history: list 구조에 맞춤)
        # 수정: .empty 대신 len() 사용 (list 구조 대응)
        valid_data = [d for d in data if "history" in d and len(d["history"]) > 0]
        if not valid_data:
            raise RuntimeError("SELECTOR_STAT_ERROR: No history data available for statistics")

        above_ma20_count = 0
        for d in valid_data:
            # 수정: list의 마지막 요소[-1] 접근 (DataFrame iloc 대체)
            last_row = d["history"][-1]
            # ma20 필드가 없을 경우를 대비한 안전장치 (버그 방지)
            if "ma20" in last_row and last_row["close"] > last_row["ma20"]:
                above_ma20_count += 1
        
        ma20_ratio = above_ma20_count / len(valid_data)
        logger.info(f"MARKET_STAT: close_above_ma20_ratio = {ma20_ratio:.2f}")

        # [3] Market Check (진입 차단 로직)
        m_check = rules["market_check"]
        if m_check["enabled"]:
            m_cond = m_check["condition"]
            if ma20_ratio < m_cond["value"]:
                logger.info(f"SELECTOR: BLOCKED (Market integrity fail: {ma20_ratio:.2f} < {m_cond['value']})")
                return [] 

        # [4] 1차 필터링 (Liquidity & Volatility)
        f_cfg = rules["filter"]
        
        # 유동성 필터 (current 딕셔너리 접근)
        liq_sorted = sorted(valid_data, key=lambda x: x["current"]["value"], reverse=True)
        liq_candidates = liq_sorted[:f_cfg["liquidity"]["top_n"]]
        
        # 변동성 필터 (history list의 마지막 요소 접근)
        vol_sorted = sorted(liq_candidates, key=lambda x: x["history"][-1].get("atr_percent", 0), reverse=True)
        intermediate = vol_sorted[:f_cfg["volatility"]["top_n"]]

        # [5] 랭킹 및 가중치 점수 계산
        rank_weights = {item["field"]: item["weight"] for item in rules["ranking"]}
        
        def calculate_score(x: Dict[str, Any]) -> float:
            score = 0.0
            last_row = x["history"][-1] # list의 마지막 요소
            curr_info = x["current"]
            
            for field, weight in rank_weights.items():
                if field in last_row:
                    val = last_row[field]
                elif field in curr_info:
                    val = curr_info[field]
                else:
                    raise RuntimeError(f"SELECTOR_FIELD_MISSING: {field} for {x['symbol']}")
                score += float(val) * weight
            return score

        # [6] 최종 선발 및 반환
        final_sorted = sorted(intermediate, key=calculate_score, reverse=True)
        final_top_k = rules["selection"]["final_top_k"]
        final_selection = final_sorted[:final_top_k]

        _save_selected_symbols(final_selection)
        logger.info(f"SELECTOR_SUCCESS: Selected {len(final_selection)} symbols")
        
        return final_selection

    except Exception as e:
        logger.error(f"SELECTOR_CRITICAL_FAILURE: {str(e)}")
        raise RuntimeError(f"SELECTOR_HALT: {str(e)}")

def _save_selected_symbols(final_selection: List[Dict[str, Any]]):
    symbols = [item["symbol"] for item in final_selection]
    state_dir = os.path.join(BASE_DIR, "STATE")
    os.makedirs(state_dir, exist_ok=True)
    file_path = os.path.join(state_dir, "selected_symbols.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(symbols, f, indent=2, ensure_ascii=False)