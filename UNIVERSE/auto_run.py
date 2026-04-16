import schedule
import time
import os

from build_universe import build_universe


def run_all():
    print("===== DAILY START =====")

    # 1. Universe 생성
    build_universe()

    # 2. RUNTIME 실행
    os.system("python RUNTIME/run.py")

    print("===== DAILY END =====")


# 08:00 실행
schedule.every().day.at("08:00").do(run_all)

print("SCHEDULER STARTED...")

while True:
    schedule.run_pending()
    time.sleep(30)