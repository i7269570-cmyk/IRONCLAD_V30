import os
import pandas as pd
import logging
import tempfile

logger = logging.getLogger("IRONCLAD_V30.COLLECTOR")

def refresh_target_300(collected_data: list):
    """
    Universe 100 생성:
    - 거래대금 상위 150
    - 상승 종목 필터 (등락률 > 0)
    - 최종 100개
    """

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_path = os.path.normpath(
            os.path.join(base_dir, "..", "data", "target_100.csv")
        )
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        df = pd.DataFrame(collected_data)

        required_cols = ['종목명', '현재가', '거래대금', '등락률']
        df = df[required_cols]

        # ⭐ 컬럼 완전 통일 (감사 FAIL 해결)
        df.rename(columns={
            '종목명': 'symbol',
            '현재가': 'price',
            '거래대금': 'value',
            '등락률': 'change_rate'
        }, inplace=True)

        # 핵심 로직
        df = df.sort_values(by='value', ascending=False).head(150)
        df = df[df['change_rate'] > 0]
        df = df.head(100)

        # atomic write
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(target_path), text=True)

        try:
            with os.fdopen(fd, 'w', encoding='utf-8-sig', newline='') as f:
                df.to_csv(f, index=False)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, target_path)
            logger.info(f"COLLECTOR_SUCCESS: {len(df)} assets saved.")

        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    except Exception as e:
        logger.error(f"COLLECTOR_CRITICAL_FAILURE: {e}")
        raise RuntimeError(e)