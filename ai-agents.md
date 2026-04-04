# IRONCLAD SYSTEM CONSTITUTION

## 1. SSOT (Single Source of Truth)

- system_config.yaml is the ONLY source for:
  - safety limits
  - global constraints
  - risk caps

- NO other file is allowed to define:
  - position size
  - risk limits
  - exposure limits

- If violated → SAFE_HALT

---

## 2. STRATEGY ISOLATION

- All strategy logic MUST exist ONLY in:
  /STRATEGY/

Includes:
- entry rules
- exit rules
- selector rules
- parameters

RUNTIME must NOT contain:
- indicators
- thresholds
- conditions

If detected → SAFE_HALT

---

## 3. NO HARDCODING

- No numeric values allowed in RUNTIME
- No default values allowed
- No fallback logic allowed

All values must come from:
- strategy files
- system_config.yaml

Violation → SAFE_HALT

---

## 4. PIPELINE RULE

Execution must follow:

S0 → S1 → S2 → ... → S11

- No step skipping
- No backward flow
- No conditional branching outside defined structure

Violation → SAFE_HALT

---

## 5. STATE MANAGEMENT

- state.json is mandatory
- State must be:
  - loaded at start
  - saved ONCE at end of run.py

- Atomic write required:
  temp → fsync → replace

- No module is allowed to mutate state arbitrarily

Violation → SAFE_HALT

---

## 6. ORDER EXECUTION CONTROL

- Orders MUST pass through:
  risk_gate → order_manager

- Direct order execution is strictly forbidden

- Required conditions:
  - risk_passed == True
  - position limits satisfied
  - asset duplication check passed

Violation → BLOCK ORDER

---

## 7. POSITION RULES

- Max positions defined by system_config.yaml
- No duplicate asset exposure
- No same asset group duplication

Violation → TRADE_ALLOWED_FALSE

---

## 8. FAILURE POLICY

- Structural violation → SAFE_HALT
- Strategy condition not met → TRADE_ALLOWED_FALSE
- Data missing → SAFE_HALT
- Config mismatch → SAFE_HALT

---

## 9. FILE ACCESS CONTROL

- LOCKED/ → read-only
- STRATEGY/ → strategy logic only
- RUNTIME/ → execution only (no logic)
- STATE/ → state only
- EVIDENCE/ → logs only

Unauthorized write → SAFE_HALT

---

## 10. DEVELOPMENT PRINCIPLE

- DO NOT fix errors with prompts
- FIX the system so error cannot occur again

System > Prompt

---

## FINAL RULE

This system must run for 10+ years without manual intervention.

Stability > Performance
Structure > Strategy
Safety > Profit