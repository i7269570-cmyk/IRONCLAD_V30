# ============================================================
# IRONCLAD_V31.19 - Atomic Cumulative Ledger (Final)
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
    입력: data(dict {"fills": list, "exits": dict}), evidence_path(str)
    기능: 
    1. 기존 ledger 파일을 읽어 메모리에 로드한다. (기존 데이터 유지)
    2. 신규 체결/청산 데이터를 규정된 필드에 맞춰 가공한다. (필드 명시)
    3. 기존 데이터와 신규 데이터를 병합하여 임시 파일에 기록 후 원자적으로 교체한다. (Atomic Cumulative Write)
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

    # [V31.19] 1. Load Existing Records (Persistence)
    if os.path.exists(final_path):
        try:
            with open(final_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_records.append(json.loads(line))
        except Exception as e:
            raise RuntimeError(f"LEDGER_READ_FAILURE: {str(e)}")

    # [V31.19] 2. Generate New Records (Field Explicit)
    new_records = []
    timestamp = datetime.now().isoformat()

    # Process FILL Data
    for fill in fills:
        if not isinstance(fill, dict):
            raise RuntimeError("LEDGER_FILL_ITEM_INVALID")
        
        # Strict Field Verification
        for key in ["symbol", "side", "price", "asset_type", "strategy_name", "volume"]:
            if key not in fill or fill[key] is None:
                raise RuntimeError(f"MISSING_FIELD_IN_FILL: {key}")
        
        new_records.append({
            "timestamp": timestamp,
            "type": "FILL",
            "symbol": fill["symbol"],
            "side": fill["side"],
            "price": fill["price"],
            "asset_type": fill["asset_type"],
            "strategy_name": fill["strategy_name"],
            "volume": fill["volume"]
        })

    # Process EXIT Data
    for symbol, exit_info in exits.items():
        if not isinstance(exit_info, dict):
            raise RuntimeError(f"LEDGER_EXIT_ITEM_INVALID: {symbol}")

        # Strict Field Verification
        for key in ["action", "side", "price", "asset_type", "strategy_name", "volume"]:
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
            "strategy_name": exit_info["strategy_name"],
            "volume": exit_info["volume"]
        })

    # [V31.19] 3. Merge Records
    all_records.extend(new_records)

    # [V31.19] 4. Atomic Write Execution
    temp_path = f"{final_path}.tmp"

    try:
        # Write merged records to temporary file
        with open(temp_path, "w", encoding="utf-8") as f:
            for record in all_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
            # Ensure physical disk sync
            f.flush()
            os.fsync(f.fileno())

        # Atomic replacement: No open(..., "a") used.
        os.replace(temp_path, final_path)
        
        logger.info(f"LEDGER_WRITER_SUCCESS: Cumulative atomic write complete. Total: {len(all_records)}")

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if isinstance(e, RuntimeError):
            raise e
        raise RuntimeError(f"LEDGER_WRITE_FAILURE: {str(e)}")