# ============================================================
# IRONCLAD_V4.11 - Operational Scheduler (Strict 4-Day Policy)
# ============================================================
from datetime import datetime, timezone, timedelta

def get_current_mode(asset_type: str = "STOCK") -> str:
    """
    STOCK: 월~목, 09:00~15:20 KST
    CRYPTO: 24/7 항상 TRADE
    """
    if asset_type.upper() == "CRYPTO":
        return "TRADE"

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)

    # [1] Day of week check (Mon:0 ~ Thu:3 / Fri:4 ~ Sun:6)
    weekday = now.weekday()
    if weekday >= 4:
        return "CLOSED"

    # [2] Time check
    hhmmss = int(now.strftime("%H%M%S"))

    if hhmmss < 90000:
        return "CLOSED"

    if 90000 <= hhmmss < 145000:
        return "TRADE"

    if 145000 <= hhmmss < 150500:
        return "NO_ENTRY"

    if 150500 <= hhmmss <= 152000:
        return "FORCE_EXIT"

    if hhmmss > 152000:
        return "CLOSED"

    return "CLOSED"
