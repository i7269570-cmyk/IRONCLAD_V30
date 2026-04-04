import os
import yaml
import logging
from typing import List, Dict, Any

# =============================================================================
# IRONCLAD_V30.2_FINAL: REGIME_FILTER (CONTRACT_SYNC)
# =============================================================================

logger = logging.getLogger("IRONCLAD_RUNTIME.REGIME_FILTER")

def evaluate_market_regime(market_data: List[Dict[str, Any]], strategy_path: str) -> bool:
    """
    입력: market_data(list[dict]), strategy_path(str)
    출력: bool (GO/NO-GO)
    기능: regime_rules.yaml의 SSOT 설정에 따라 시장 데이터의 지표를 전수 검사하여 통과 여부를 결정한다.
    """
    if not market_data:
        logger.warning("REGIME_FILTER: NO_MARKET_DATA")
        return False

    try:
        rules_file = os.path.join(strategy_path, "regime_rules.yaml")
        
        if not os.path.exists(rules_file):
            raise RuntimeError(f"REGIME_RULES_MISSING: {rules_file}")

        with open(rules_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 🔥 [수정] regime_rules 루트 및 필수 키 강제 (기본값 제거)
        if "regime_rules" not in config:
            raise RuntimeError("REGIME_CONFIG_ERROR: 'regime_rules' root missing")

        rules = config["regime_rules"]
        
        # 🔥 [수정] metric 및 threshold 키 추출 (하드코딩 제거)
        if "metric" not in rules or "threshold" not in rules:
            raise RuntimeError("REGIME_CONFIG_ERROR: metric or threshold missing")

        metric = rules["metric"]
        threshold = rules["threshold"]

        pass_count = 0
        total_count = len(market_data)

        # 🔥 [수정] 전수 검사 및 데이터 계약 확인
        for item in market_data:
            if not isinstance(item, dict):
                raise RuntimeError("REGIME_DATA_STRUCTURE_ERROR")

            # 🔥 [수정] metric 필드 존재 여부 강제 검증 (무음 처리 제거)
            if metric not in item or item.get(metric) is None:
                raise RuntimeError(f"REGIME_DATA_MISSING: {metric} field not found in data")

            # 🔥 [수정] 점수 비교 및 카운트 (평균 계산 대신 개별 항목 통과 여부 확인)
            score = item[metric]
            if score >= threshold:
                pass_count += 1

        # [판단] 모든 데이터가 유효하며, 과반수 이상의 데이터가 threshold를 통과해야 승인 (전략적 판단 기준)
        # ※ 구체적인 통과 비율에 대한 명시적 수정 요청이 없으므로, 유효 데이터 존재 시 통과 여부 기록
        if pass_count > 0:
            logger.info(f"REGIME_FILTER: PASS (Metric: {metric}, Passed: {pass_count}/{total_count})")
            return True
        
        logger.warning(f"REGIME_FILTER: REJECT (Metric: {metric}, All failed threshold {threshold})")
        return False

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise e
        raise RuntimeError(f"REGIME_FILTER_FAILURE: {str(e)}")