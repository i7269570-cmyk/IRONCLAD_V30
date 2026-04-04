from datetime import datetime

def get_current_mode():
     """
     감사 기준 4단계 시간 구조를 정밀하게 준수한다.
     [FIX] 14:50:00 정각 누락 리스크 해결 (밀착 경계 적용)
     """
     now = datetime.now()
     hhmmss = int(now.strftime("%H%M%S"))

     # 1. 장 종료 및 야간 (15:30:00 ~ 08:59:59)
     if hhmmss >= 153000 or hhmmss < 90000:
         return "CLOSED"
     
     # 2. 강제 청산 (15:00:00 ~ 15:29:59)
     if 150000 <= hhmmss < 153000:
         return "FORCE_EXIT"

     # 3. 신규 진입 금지 (14:50:00 ~ 14:59:59)
     if 145000 <= hhmmss < 150000:
         return "NO_ENTRY"

     # 4. 정상 운영 (09:00:00 ~ 14:49:59)
     # [FIX] 하한 90000 포함, 상한 145000 미만으로 NO_ENTRY와 공백 없이 연결
     if 90000 <= hhmmss < 145000:
         return "TRADE"

     return "CLOSED"