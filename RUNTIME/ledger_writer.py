# ============================================================
# IRONCLAD_V4.10 - Isolated Ledger Writer (Strict Path)
# ============================================================
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("IRONCLAD_RUNTIME.LEDGER_WRITER")

def record_to_ledger(data: Dict[str, Any], evidence_path: str):
    """
    [V4.10] 자산군별(STOCK/COIN) 경로 완전 격리 기록
    - 주입받은 evidence_path를 SSOT로 사용하여 기록 위치 결정
    """
    # 1. 입력 구조 및 타입 검증
    if not isinstance(data, dict):
        raise RuntimeError("LEDGER_INPUT_INVALID")

    # 🔴 [V4.10 수정] .get() 제거 및 명시적 키 검사 (No-Default 원칙)
    if "fills" not in data or "exits" not in data:
        raise RuntimeError("LEDGER_INPUT_SCHEMA_ERROR: 'fills' or 'exits' missing")

    fills = data["fills"]
    exits = data["exits"]

    # 🔴 [V4.10 핵심] 주입된 경로를 절대 신뢰 (분리 실행의 핵심)
    # evidence_path는 run_stock.py 혹은 run_coin.py에서 결정되어 넘어옴
    final_path = os.path.join(evidence_path, "trade_ledger.jsonl")
    
    # 해당 경로 폴더가 없으면 생성 (STOCK/COIN 폴더 격리 보장)
    os.makedirs(evidence_path, exist_ok=True)

    all_records = []

    # 2. 기존 기록 로드 (Atomic Read)
    if os.path.exists(final_path):
        try:
            with open(final_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_records.append(json.loads(line))
        except Exception as e:
            raise RuntimeError(f"LEDGER_READ_FAILURE: {str(e)}")

    # 3. 신규 기록 생성 (기존 검증 로직 유지)
    new_records = []
    timestamp = datetime.now().isoformat()

    # [FILL 데이터 처리]
    for fill in fills:
        required_keys = ["symbol", "side", "price", "asset_type", "strategy_id", "volume"]
        for key in required_keys:
            if key not in fill or fill[key] is None:
                raise RuntimeError(f"MISSING_FIELD_IN_FILL: {key}")
        
        new_records.append({
            "timestamp": timestamp,
            "type": "FILL",
            "symbol": fill["symbol"],
            "side": fill["side"],
            "price": fill["price"],
            "asset_type": fill["asset_type"],
            "strategy_id": fill["strategy_id"],
            "volume": fill["volume"]
        })

    # [EXIT 데이터 처리]
    for symbol, exit_info in exits.items():
        required_keys = ["action", "side", "price", "asset_type", "strategy_id", "volume"]
        for key in required_keys:
            if key not in exit_info or exit_info[key] is None:
                raise RuntimeError(f"MISSING_FIELD_IN_EXIT: {key} for {symbol}")
        
        new_records.append({
            "timestamp": timestamp,
            "type": "EXIT",
            "symbol": symbol,
            "action": exit_info["action"],
            "side": exit_info["side"],
            "price": exit_info["price"],
            "asset_type": exit_info["asset_type"],
            "strategy_id": exit_info["strategy_id"],
            "volume": exit_info["volume"]
        })

    # 4. Atomic Write 실행 (원자적 교체 유지)
    all_records.extend(new_records)
    temp_path = f"{final_path}.tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            for record in all_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, final_path)
        logger.info(f"LEDGER_WRITER_SUCCESS: {evidence_path} preserved.")

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise RuntimeError(f"LEDGER_WRITE_FAILURE: {str(e)}")