 IRONCLAD_V30.1_FINAL용 run.py를 새로 설계하라.

중요:
- 기존 V27 코드를 복사하거나 재사용하지 말고, 구조만 참고해서 V30에 맞게 새로 작성한다.
- 목표는 “주식 + 코인 통합 실행 엔진”이다.
- 단일 진입점 run.py 하나만 존재해야 한다.
- 전략 연구/백테스트 로직은 넣지 않는다.
- 실행 로직만 만든다.

[참고 의도]
- V27의 RUNTIME/run.py는 검증/통제/SAFE_HALT 중심 구조였다.
- V27의 STOCK/run.py는 단순한 전략 실행 흐름 예시였다.
- 이번 V30은 두 장점을 합쳐서:
  1) 실행 전 검증과 예외 차단은 강하게 유지
  2) 실행 흐름은 단순하고 실전형으로 만든다

[최종 폴더 기준]
IRONCLAD_V30.1_FINAL/
├─ LOCKED/
│  ├─ system_config.yaml
│  ├─ schema.json
│  ├─ recovery_policy.yaml
│  └─ GUARDS/
│     ├─ preflight_gate.py
│     └─ integrity_guard.py
├─ STRATEGY/
│  ├─ strategy_spec.yaml
│  ├─ selector_rules.yaml
│  ├─ entry_rules.yaml
│  └─ exit_rules.yaml
├─ RUNTIME/
│  ├─ run.py
│  ├─ scheduler.py
│  ├─ data_loader.py
│  ├─ selector.py
│  ├─ regime_filter.py
│  ├─ entry_engine.py
│  ├─ risk_gate.py
│  ├─ pre_order_check.py
│  ├─ order_manager.py
│  ├─ fill_tracker.py
│  ├─ position_reconciler.py
│  ├─ state_manager.py
│  ├─ ledger_writer.py
│  ├─ exit_engine.py
│  └─ exception_handler.py
├─ STATE/
│  ├─ state.json
│  └─ runtime_status.json
└─ EVIDENCE/
   ├─ ledger/
   └─ incident/

[run.py가 반드시 해야 할 일]
1. 유일 진입점이어야 한다.
2. LOCKED/GUARDS의 preflight_gate.py를 먼저 호출한다.
3. scheduler.py로 현재 모드를 판정한다.
4. 모드가 CLOSED면 아무 주문도 하지 않고 종료한다.
5. data_loader.py를 통해 주식/코인 데이터를 각각 로드한다.
6. 전 종목 스캔 금지, Top-N(30~50개)만 다룬다.
7. selector.py로 각 자산군 후보를 압축한다.
8. regime_filter.py로 시장 상태를 판정한다.
9. entry_engine.py로 진입 조건을 평가한다.
10. risk_gate.py에서 다음을 수행한다:
   - 최대 2포지션 제한
   - 동일 자산군 중복 금지
   - 총 노출 한도 확인
   - position sizing 계산
11. pre_order_check.py로 주문 직전 최종 검증을 한다.
12. order_manager.py에서 자산별 API로 주문을 보낸다.
   - STOCK은 증권사 API
   - CRYPTO는 거래소 API
13. fill_tracker.py로 체결 상태를 반영한다.
14. state_manager.py는 atomic write로 상태를 저장한다.
15. ledger_writer.py로 append-only 로그를 남긴다.
16. exit_engine.py로 청산을 수행한다.
17. position_reconciler.py로 실제 계좌 상태와 내부 상태를 맞춘다.
18. 예외 발생 시 exception_handler.py를 호출한다.
19. 예외 흐름은 반드시:
   Cancel-All → incident 기록 → SAFE_HALT
20. 기본값 자동 생성 금지, 필수 키 누락 시 즉시 중단한다.

[시간 구조]
- 09:00~14:50 → TRADE
- 14:50~15:00 → NO_ENTRY
- 15:00~15:30 → FORCE_EXIT
- 15:30 이후 → CLOSED

주의:
- 15:30에 청산하는 구조가 아니다.
- 15:00부터 강제 청산 시작해서 15:30 전에 포지션 0이어야 한다.

[자산 구조]
- 주식 + 코인 둘 다 같은 run.py에서 처리한다.
- 하지만 포지션은 최대 2개다.
- 허용 예: 주식 1 + 코인 1
- 금지 예: 주식 2, 코인 2
- 동일 자산군 중복 금지

[구현 원칙]
- 함수는 단일 책임
- 하드코딩 금지
- 전략 조건은 STRATEGY 폴더에서만 읽는다
- 안전 상한선은 LOCKED에서만 읽는다
- state.json 직접 덮어쓰기 금지
- 반드시 atomic write 사용
- 로그 남기기
- 타입 힌트 사용
- 예외 처리 포함

[출력 요구]
- run.py 전체 코드만 출력
- 설명문 최소화
- 바로 파일로 저장 가능한 형태로 작성