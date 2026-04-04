# ============================================================
# IRONCLAD_V31.18 - Strategic Entry Engine (ID-Chain Integrity)
# ============================================================
import os
import yaml
import operator
import traceback
from typing import List, Dict, Any
import pandas as pd

# [1] OPERATORS 정의
OPERATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq
}

# [2] load_strategy_entry_rules (단일 경로 해석 방식으로 변경)
def load_strategy_entry_rules(strat_path: str) -> Dict[str, Any]:
    """
    run.py의 루프에서 전달받은 특정 전략 폴더의 entry_rules.yaml만 로드함.
    전략 폴더 전체를 스캔하던 이전 방식을 폐기하여 격리성 강화.
    """
    rules_file = os.path.join(strat_path, "entry_rules.yaml")
    if not os.path.exists(rules_file):
        return {}

    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            rules_data = yaml.safe_load(f)
            if rules_data and "entry" in rules_data:
                return rules_data["entry"]
    except Exception as e:
        print(f"[ERROR] Strategy Load Failed: {rules_file} | {str(e)}")
    
    return {}

# [3] evaluate_condition (NaN 및 유효성 검증 유지)
def evaluate_condition(last_row: pd.Series, condition: Dict[str, Any]) -> bool:
    field = condition.get("field")
    op_str = condition.get("op")
    
    if field not in last_row:
        raise RuntimeError(f"FIELD_NOT_FOUND: {field}")
    if op_str not in OPERATORS:
        raise RuntimeError(f"INVALID_OPERATOR: {op_str}")

    left_val = last_row[field]
    
    # NaN 탐지: 무음 통과 방지
    if pd.isna(left_val):
        raise RuntimeError(f"NAN_VALUE_DETECTED: field '{field}'")

    op_func = OPERATORS[op_str]

    if "value" in condition:
        right_val = float(condition["value"])
    elif "ref" in condition:
        ref_field = condition["ref"]
        if ref_field not in last_row:
            raise RuntimeError(f"REF_FIELD_NOT_FOUND: {ref_field}")
        
        multiplier = float(condition.get("multiplier", 1.0))
        right_val = last_row[ref_field]
        
        if pd.isna(right_val):
            raise RuntimeError(f"NAN_REF_VALUE_DETECTED: field '{ref_field}'")
            
        right_val *= multiplier
    else:
        raise RuntimeError(f"INCOMPLETE_CONDITION_SPEC: {field}")

    return op_func(left_val, right_val)

# [4] generate_signals (V31.18: strategy_id 사슬 보존)
def generate_signals(
    data_bundle: Dict[str, Dict[str, Any]], 
    strat_path: str, 
    state: Dict[str, Any], 
    system_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    [V31.18 시그널 생성 엔진]
    - 'strategy_name' 필드를 삭제하고 'strategy_id'를 최우선으로 사용.
    - 외부에서 주입된 strat_path의 규칙만 해석하여 상위 루프와 동기화.
    """
    signals = []
    # run.py 루프에서 전달된 특정 전략의 규칙 로드
    entry_cfg = load_strategy_entry_rules(strat_path)
    if not entry_cfg:
        return []

    conditions = entry_cfg.get("conditions", [])

    for symbol, bundle in data_bundle.items():
        current = bundle["current"]
        history = bundle["history"]

        if history.empty:
            continue
            
        # 데이터 계약 검증
        if "asset_type" not in history.columns:
            raise RuntimeError(f"DATA_CONTRACT_VIOLATION: asset_type missing for {symbol}")

        last_row = history.iloc[-1]
        is_qualified = True

        try:
            for cond in conditions:
                if not evaluate_condition(last_row, cond):
                    is_qualified = False
                    break
        
        except RuntimeError as re:
            print(f"[INTEGRITY_SIGNAL_REJECTED] {symbol} | Path: {strat_path} | Reason: {str(re)}")
            is_qualified = False
            continue 

        except Exception:
            print(f"[UNEXPECTED_ENGINE_ERROR] {symbol} | Path: {strat_path}")
            print(traceback.format_exc()) 
            is_qualified = False
            continue
        
        if is_qualified:
            # Snapshot 유효성 검사 (실행 가격 보호)
            if pd.isna(current.get("price")):
                print(f"[EXECUTION_REJECTED] {symbol} | Price is NaN")
                continue

            # [V31.18] 시그널 생성 (strategy_id는 run.py 루프에서 부여됨)
            signals.append({
                "symbol": symbol,
                "side": "BUY",
                "price": float(current["price"]),
                "asset_type": str(current["asset_type"]),
                # strategy_id 필드는 run.py의 루프에서 strat["id"]로 덮어씌워짐
                "strategy_id": "PENDING", 
                "risk_per_trade": entry_cfg.get("risk_per_trade"),
                "stop_distance": entry_cfg.get("stop_distance")
            })
                
    return signals