# ============================================================
# IRONCLAD_V31.23 - Ledger Writer (Strategy ID Integrity)
# ============================================================
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("IRONCLAD_RUNTIME.LEDGER_WRITER")

def record_to_ledger(data: Dict[str, Any], evidence_path: str):
    """
    목표: 진입/청산 기록 시 strategy_id 보존 및 누락 방지
    """
    # 1. 입력 구조 및 타입 검증
    if not isinstance(data, dict):
        raise RuntimeError("LEDGER_INPUT_INVALID")

    fills = data.get("fills", [])
    exits = data.get("exits", {})

    final_path = os.path.join(evidence_path, "trade_ledger.jsonl")
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

    # 3. 신규 기록 생성 (strategy_id 보존 집중)
    new_records = []
    timestamp = datetime.now().isoformat()

    # [FILL 데이터 처리] - 진입 시 strategy_id 필수 검증
    for fill in fills:
        # 🔴 [V31.23 핵심] strategy_id 포함 필수 필드 존재 여부 엄격 검사
        # 하드코딩이나 빈 문자열 삽입 없이, 입력된 sig/fill의 값을 그대로 보존
        required_keys = ["symbol", "side", "price", "asset_type", "strategy_id", "volume"]
        for key in required_keys:
            if key not in fill or fill[key] is None:
                # 원칙: 억지 생성 금지. 누락 시 즉시 에러 발생시켜 상위에서 처리 유도
                raise RuntimeError(f"MISSING_FIELD_IN_FILL: {key}")
        
        new_records.append({
            "timestamp": timestamp,
            "type": "FILL",
            "symbol": fill["symbol"],
            "side": fill["side"],
            "price": fill["price"],
            "asset_type": fill["asset_type"],
            "strategy_id": fill["strategy_id"], # 주입된 ID 보존
            "volume": fill["volume"]
        })

    # [EXIT 데이터 처리] - 청산 시 strategy_id 필수 검증
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
            "strategy_id": exit_info["strategy_id"], # 주입된 ID 보존
            "volume": exit_info["volume"]
        })

    # 4. Atomic Write 실행 (원자적 교체 방식 유지)
    all_records.extend(new_records)
    temp_path = f"{final_path}.tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            for record in all_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, final_path)
        logger.info(f"LEDGER_WRITER_SUCCESS: Records preserved. Count: {len(all_records)}")

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise RuntimeError(f"LEDGER_WRITE_FAILURE: {str(e)}")