# ============================================================
# IRONCLAD_V31.20 - Atomic Cumulative Ledger (Fixed Contract)
# ============================================================
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# [Standard] Logging interface
logger = logging.getLogger("IRONCLAD_RUNTIME.LEDGER_WRITER")

def record_to_ledger(data: Dict[str, Any], evidence_path: str):
    """
    기능: strategy_name -> strategy_id 데이터 계약 수정 및 원자적 기록
    """
    
    # [Standard] Input structure and type validation
    if not isinstance(data, dict):
        raise RuntimeError("LEDGER_INPUT_INVALID")

    if "fills" not in data or "exits" not in data:
        raise RuntimeError("LEDGER_KEYS_MISSING")

    fills = data["fills"]
    exits = data["exits"]

    if not isinstance(fills, list):
        raise RuntimeError("LEDGER_FILLS_INVALID")

    if not isinstance(exits, dict):
        raise RuntimeError("LEDGER_EXITS_INVALID: exits must be dict")

    final_path = os.path.join(evidence_path, "trade_ledger.jsonl")
    all_records = []

    # [V31.20] 1. Load Existing Records
    if os.path.exists(final_path):
        try:
            with open(final_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_records.append(json.loads(line))
        except Exception as e:
            raise RuntimeError(f"LEDGER_READ_FAILURE: {str(e)}")

    # [V31.20] 2. Generate New Records (Field Correction: strategy_id)
    new_records = []
    timestamp = datetime.now().isoformat()

    # Process FILL Data
    for fill in fills:
        if not isinstance(fill, dict):
            raise RuntimeError("LEDGER_FILL_ITEM_INVALID")
        
        # [Strict] strategy_id 필드 준수
        for key in ["symbol", "side", "price", "asset_type", "strategy_id", "volume"]:
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

    # Process EXIT Data
    for symbol, exit_info in exits.items():
        if not isinstance(exit_info, dict):
            raise RuntimeError(f"LEDGER_EXIT_ITEM_INVALID: {symbol}")

        # [Strict] strategy_id 필드 준수
        for key in ["action", "side", "price", "asset_type", "strategy_id", "volume"]:
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

    # [V31.20] 3. Atomic Write Execution
    all_records.extend(new_records)
    temp_path = f"{final_path}.tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            for record in all_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, final_path)
        logger.info(f"LEDGER_WRITER_SUCCESS: Atomic write complete. strategy_id applied. Count: {len(all_records)}")

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise RuntimeError(f"LEDGER_WRITE_FAILURE: {str(e)}")