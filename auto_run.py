import os
import sys
from datetime import datetime

# [1] 경로 설정: 실행 파일 위치와 상관없이 프로젝트 루트를 SSOT로 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

def daily_ready():
    """
    아침 장 시작 전 '딱 한 번' 실행
    순서: 후보 수집(50개) -> 정예 선정(3개) -> 매매 가동
    """
    print(f"\n🚀 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] IRONCLAD 단타 가동")
    print("="*55)

    try:
        # 1️⃣ Step: 후보군 생성 (전체 시장 -> 300억 이상 50개)
        # build_universe.py는 .env를 읽어 후보를 UNIVERSE 폴더에 저장함
        print("1. [UNIVERSE] 후보 종목 50개 수집 중...")
        os.system(f"python {os.path.join(PROJECT_ROOT, 'UNIVERSE', 'build_universe.py')}")

        # 2️⃣ Step: 정예 선정 (50개 분석 -> 3개 선정 및 STATE 갱신)
        # selector_runner.py는 선정 결과를 STATE/state_stock.json 등에 직접 주입함
        print("\n2. [SELECTOR] 정예 종목 선정 및 STATE 갱신 중...")
        os.system(f"python {os.path.join(PROJECT_ROOT, 'RUNTIME', 'selector_runner.py')}")

        # 3️⃣ Step: 실제 매매 엔진 가동 (사용자 선택에 따라 주식/코인 실행)
        # 단타를 위해 선정된 종목만 집중 감시하며 전략에 맞으면 즉시 매수
        print("\n3. [EXECUTION] 매매 엔진 가동 (Monitoring Start)")
        
        # 주식 단타 실행 시
        os.system(f"python {os.path.join(PROJECT_ROOT, 'RUNTIME', 'run_stock.py')}")
        
        # 코인 단타도 동시에 실행할 경우 아래 주석 해제
        # os.system(f"python {os.path.join(PROJECT_ROOT, 'RUNTIME', 'run_coin.py')}")

    except Exception as e:
        print(f"❌ CRITICAL ERROR during auto_run: {e}")

if __name__ == "__main__":
    # 아침에 이 파일을 실행하면 오늘 매매 준비가 끝납니다.
    daily_ready()