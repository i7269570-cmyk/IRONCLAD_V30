# GC Scan Report

- Time: 2026-04-05T01:36:08.556878

## LOCKED/GUARDS/preflight_gate.py
- FORBID_PATTERN: 'print('
- FORBID_PATTERN: 'temp'

## MAINTENANCE/gc_rules.yaml
- FORBID_PATTERN: 'print('
- FORBID_PATTERN: 'TODO'
- FORBID_PATTERN: 'FIXME'
- FORBID_PATTERN: 'PENDING'
- FORBID_PATTERN: 'temp'
- FORBID_PATTERN: 'debug'
- FORBID_PATTERN: 'hardcoded'

## MAINTENANCE/gc_scan.py
- FORBID_PATTERN: 'print('

## RUNTIME/collector_100.py
- FORBID_PATTERN: 'temp'

## RUNTIME/entry_engine.py
- FORBID_PATTERN: 'print('
- FORBID_PATTERN: 'PENDING'

## RUNTIME/exit_engine.py
- FORBID_PATTERN: 'print('

## RUNTIME/indicator_calc.py
- RUNTIME_STRATEGY_RISK: 'bb_'

## RUNTIME/ledger_writer.py
- FORBID_PATTERN: 'temp'

## RUNTIME/run.py
- FORBID_PATTERN: 'PENDING'

## RUNTIME/state_manager.py
- FORBID_PATTERN: 'temp'

## UNIVERSE/auto_run.py
- FORBID_PATTERN: 'print('

## UNIVERSE/build_universe.py
- FORBID_PATTERN: 'print('

## UNIVERSE/crypto_universe.py
- FORBID_PATTERN: 'print('

## UNIVERSE/stock_universe.py
- FORBID_PATTERN: 'print('
