import os
import json

# 🎯 핵심: 모든 실행 파일은 동일한 루트 계산 로직을 공유해야 함 (RUNTIME/ 기준)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

from data_loader import load_market_data
from indicator_calc import calculate_indicators
from selector import select_candidates

def main():
    strategy_path = os.path.join(PROJECT_ROOT, "STRATEGY/STOCK")

    # 1. 원본 데이터 로드
    raw_data_map = load_market_data(["STOCK"], strategy_path, access_token=None)

    if not raw_data_map:
        raise RuntimeError("EMPTY_RAW_DATA")

    # 2. 데이터 구조 변환 (Dict -> List[Dict]) - selector.py와의 계약 준수
    formatted_data = []
    for symbol, content in raw_data_map.items():
        formatted_data.append({
            "symbol": symbol,
            "current": content["current"],
            "history": calculate_indicators(content["history"])
        })

    # 3. 종목 선정 및 STATE/selected_symbols.json 자동 저장
    # selector.py 내부에서 PROJECT_ROOT/STATE/ 경로에 저장하도록 관리 필요
    selected = select_candidates(formatted_data, strategy_path)

    if not selected:
        print("⚠️ NO_SELECTION_RESULT")
        return

    symbols = [item["symbol"] for item in selected]
    
    print("🔥 SELECTED:", symbols)
    

if __name__ == "__main__":
    main()