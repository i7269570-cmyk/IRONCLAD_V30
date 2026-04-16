# ============================================================
# IRONCLAD_V4.11 - Operational Scheduler (Strict 4-Day Policy)
# ============================================================
from datetime import datetime, timezone, timedelta

def get_current_mode():
    """
    [4.11 Operational Policy]
    1. Day Limit: Mon, Tue, Wed, Thu (0, 1, 2, 3) / Closed Fri, Sat, Sun
    2. Time Limit: Market Hours (09:00 ~ 15:20 KST)
    3. Target: Common application for Stocks and Crypto
    """
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    
    # [1] Day of week check (Mon:0, Tue:1, Wed:2, Thu:3, Fri:4, Sat:5, Sun:6)
    weekday = now.weekday()
    if weekday >= 4:  # Full closure on Fri, Sat, Sun
        return "CLOSED"

    # [2] Time check (HHMMSS integer conversion - No string comparison)
    hhmmss = int(now.strftime("%H%M%S"))

    # 00:00:00 ~ 08:59:59: Before Market Open
    if hhmmss < 90000:
        return "CLOSED"

    # 09:00:00 ~ 14:49:59: Normal Trading (TRADE)
    if 90000 <= hhmmss < 145000:
        return "TRADE"

    # 14:50:00 ~ 15:04:59: Entry Restricted (NO_ENTRY)
    if 145000 <= hhmmss < 150500:
        return "NO_ENTRY"

    # 15:05:00 ~ 15:20:00: Forced Exit (FORCE_EXIT)
    if 150500 <= hhmmss <= 152000:
        return "FORCE_EXIT"

    # 15:20:01 ~ 23:59:59: After Market Close
    if hhmmss > 152000:
        return "CLOSED"

    return "CLOSED"