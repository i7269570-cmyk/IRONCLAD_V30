from datetime import datetime

def get_current_mode():
    now = datetime.now()
    hhmmss = int(now.strftime("%H%M%S"))

    # 1. 장 종료 및 야간 (15:30:00 ~ 07:59:59)
    if hhmmss >= 153000 or hhmmss < 80000:
        return "CLOSED"
    
    # ⭐ 장 시작 전 데이터 수집 (08:00:00 ~ 08:59:59)
    if 80000 <= hhmmss < 90000:
        return "PRE_MARKET"

    # 2. 정상 운영 (09:00:00 ~ 14:49:59)
    if 90000 <= hhmmss < 145000:
        return "TRADE"

    # 3. 신규 진입 금지 (14:50:00 ~ 14:59:59)
    if 145000 <= hhmmss < 150000:
        return "NO_ENTRY"

    # 4. 강제 청산 (15:00:00 ~ 15:29:59)
    if 150000 <= hhmmss < 153000:
        return "FORCE_EXIT"

    return "CLOSED"