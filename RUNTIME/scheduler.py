# ============================================================
# IRONCLAD_V4.11 - Operational Scheduler (Strict 4-Day Policy)
# ============================================================
from datetime import datetime

def get_current_mode():
    """
    [4.11 운영 정책]
    1. 요일 제한: 월, 화, 수, 목 (0, 1, 2, 3)만 실행 / 금, 토, 일 종료
    2. 시간 제한: 주식 시장 시간 기준 (09:00 ~ 15:20)
    3. 대상: 주식 및 코인 공통 적용
    """
    now = datetime.now()
    
    # [1] 요일 판별 (월:0, 화:1, 수:2, 목:3, 금:4, 토:5, 일:6)
    weekday = now.weekday()
    if weekday >= 4:  # 금, 토, 일 전면 폐쇄
        return "CLOSED"

    # [2] 시간 판별 (HHMMSS 정수 변환 - 문자열 비교 금지 원칙)
    hhmmss = int(now.strftime("%H%M%S"))

    # 00:00:00 ~ 08:59:59: 장 시작 전
    if hhmmss < 90000:
        return "CLOSED"

    # 09:00:00 ~ 14:49:59: 정상 거래 (TRADE)
    if 90000 <= hhmmss < 145000:
        return "TRADE"

    # 14:50:00 ~ 14:59:59: 신규 진입 금지 (NO_ENTRY)
    if 145000 <= hhmmss < 150000:
        return "NO_ENTRY"

    # 15:00:00 ~ 15:19:59: 강제 청산 (FORCE_EXIT)
    # [V4.11 수정] 15:20:00 정각 CLOSED 전환에 따른 범위 주석 정정
    if 150000 <= hhmmss < 152000:
        return "FORCE_EXIT"

    # 15:20:00 ~ 23:59:59: 장 종료 (CLOSED)
    if hhmmss >= 152000:
        return "CLOSED"

    return "CLOSED"