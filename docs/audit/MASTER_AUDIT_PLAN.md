# MASTER AUDIT PLAN - Trading System Validation Framework

**Created:** 2026-01-17
**Purpose:** Comprehensive validation of data integrity, feature correctness, and strategy robustness
**Run Mode:** Local execution with gold.db

---

## Overview

This audit framework validates your trading system across 7 critical dimensions:

1. **Raw Data Integrity** (Step 1)
2. **Gap & Transition Behavior** (Step 1.5)
3. **Feature Verification** (Step 2)
4. **Time-Safety Assertions** (Step 2.4)
5. **Strategy Validation** (Step 3)
6. **Adversarial Testing** (Step 3.4)
7. **Attack Harness** (Core Framework)

**Key Principle:** If data is wrong, everything downstream is invalid.

---

## Execution Structure

### Quick Start
```bash
# Run complete audit suite
python audit_master.py

# Run specific step
python audit_master.py --step 1
python audit_master.py --step 2
python audit_master.py --step 3

# Run with detailed output
python audit_master.py --verbose

# Export results
python audit_master.py --export results.csv
```

### Audit Stages

```
STAGE 1: DATA FOUNDATION
├── Step 1:   Raw data & chart integrity
├── Step 1.5: Gap & transition behavior
└── Output:   Data quality report

STAGE 2: FEATURE LAYER
├── Step 2:   Feature verification
├── Step 2.4: Time-safety assertions
└── Output:   Feature validation report

STAGE 3: STRATEGY LAYER
├── Step 3:   Strategy correctness
├── Step 3.4: Attack testing
└── Output:   Strategy robustness report

FINAL OUTPUT: Master audit report + pass/fail verdict
```

---

## Step 1: Raw Data & Chart Integrity

**Purpose:** Prove database matches reality

### Tests Implemented

#### 1.1 Time & Session Integrity
- ✅ UTC → UTC+10 conversion
- ✅ Session boundaries exact (no bleed)
- ✅ Asia: 09:00–17:00
- ✅ London: 18:00–23:00
- ✅ NY: 23:00–02:00
- ✅ ORB windows exact (5-minute blocks)

**SQL Check:**
```sql
SELECT COUNT(*) AS bad_rows
FROM bars_1m
WHERE (local_time < '09:00' OR local_time > '02:00')
  AND session IS NOT NULL;
```
**Pass:** `bad_rows = 0`

#### 1.2 Candle Completeness
- ✅ No missing 1-minute bars during trading hours
- ✅ No duplicate timestamps
- ✅ 1m → 5m aggregation consistency

#### 1.3 Chart Parity Test
- ✅ DB high/low matches TradingView ±1 tick
- ✅ No systematic offset
- ✅ 10 random date samples

#### 1.4 ORB Construction
- ✅ ORB high = max(high) of first 5 mins
- ✅ ORB low = min(low) of first 5 mins

#### 1.5 ATR Integrity
- ✅ ATR computed from historical bars only
- ✅ No forward candles
- ✅ No zero ATR values

#### 1.6 Zero-Lookahead Guardrails
- ✅ ORB data available after ORB close
- ✅ ATR available before ORB
- ✅ Session labels used only after session end

**Output:** `step1_data_integrity_report.json`

---

## Step 1.5: Gap & Transition Behavior

**Purpose:** Explicit modeling of dead time and session gaps

### New Time Buckets
- PRE_ASIA: 07:00–09:00
- ASIA→LONDON TRANSITION: 17:00–18:00
- LONDON→NY TRANSITION: 22:00–23:00
- NY→ASIA GAP: 02:00–07:00

### Tests Implemented

#### Gap Metrics
- ✅ Asia gap = 09:00 open − last NY close
- ✅ Transition range (17:00–18:00)
- ✅ Range / ATR normalization

#### Hypotheses to Test
1. **H1:** Pre-London compression → London expansion
2. **H2:** Pre-Asia gap predicts Asia ORB direction
3. **H3:** Last candle → first candle discontinuity

**Output:** `step1a_gaps_transitions_report.json`

---

## Step 2: Feature & Derived Metric Verification

**Purpose:** Every calculated feature must be provably correct

### Tests Implemented

#### 2.1 Feature Contract Lock
- ✅ Canonical feature spec (source, formula, availability)
- ✅ Feature availability matrix (which ORBs can use which features)

#### 2.2 Deterministic Rebuild Test (CRITICAL)
```python
# Rebuild daily_features_v2 twice
hash_run_1 = hash(daily_features_v2_run1)
hash_run_2 = hash(daily_features_v2_run2)
assert hash_run_1 == hash_run_2
```
**Pass:** Identical hashes

#### 2.3 Single-Feature Truth Tests
For EACH feature:
```sql
SELECT date, asia_gap,
       asia_open - prior_ny_close AS recomputed
FROM daily_features_v2
WHERE ABS(asia_gap - recomputed) > 0.1;
```
**Pass:** Zero rows

#### 2.4 Time-Safety Assertions
```python
assert feature_time <= orb_open_time
```
**Fail:** Raise exception, not warning

#### 2.5 Feature Distribution Sanity
- ✅ Min/max/mean/std checks
- ✅ % zeros / nulls
- ✅ Flag constant or clipped features

#### 2.6 Feature Correlation Scan
- ✅ Correlation to outcomes only (not to other features)
- ✅ Detect inverted signs
- ✅ Detect leakage (|corr| > 0.3 suspicious)

**Output:** `step2_feature_verification_report.json`

---

## Step 2.4: Time-Safety Assertions (Hard-Fail)

**Purpose:** Enforce time-safety at code level, not just documentation

### Implemented Safeguards

#### Feature Availability Map
```python
FEATURE_AVAILABLE_AT = {
    "pre_asia_range": time(9, 0),
    "asia_gap": time(9, 0),
    "transition_1700_1800_range": time(18, 0),
    "atr_20": time(0, 0),
    "orb_0900_size": time(9, 5),
    # ... etc
}
```

#### Assertion Function
```python
def assert_window_ends_before(feature_name: str, window_end: pd.Timestamp):
    """Hard-fail if feature uses candles after availability."""
    declared = FEATURE_AVAILABLE_AT[feature_name]
    if window_end > declared_ts:
        raise AssertionError(f"[LOOKAHEAD] {feature_name}")
```

#### Strategy Usage Control
```python
STRATEGY_CAN_USE = {
    "0900": {"pre_asia_range", "asia_gap", "atr_20", "orb_0900_size"},
    "1800": {"atr_20", "transition_1700_1800_range", "orb_1800_size"},
    # ...
}
```

**Output:** `step2a_time_assertions_report.json`

---

## Step 3: Strategy Validation

**Purpose:** Prove strategy is mechanically correct and deterministic

### Tests Implemented

#### 3.1 Strategy Definition Lock
- ✅ Strategy manifest (JSON hash)
- ✅ Same manifest → identical results
- ✅ Any code change = new hash

#### 3.2 Backtest Engine Correctness
- ✅ Entry determinism (same candles → same entry)
- ✅ Three execution modes:
  - **Ideal:** Close price
  - **Realistic:** Close ± 1-2 ticks
  - **Hostile:** Worst-case fill, stop-first bias

#### 3.3 Walk-Forward & Regime Safety
- ✅ Rolling walk-forward (90 train / 30 test)
- ✅ Time-shuffle test (should degrade toward zero)
- ✅ Feature drop test (small degradation = robust)

**Output:** `step3_strategy_validation_report.json`

---

## Step 3.4: Adversarial / Attack Testing

**Purpose:** Break it on purpose. If it survives, it's real.

### Attack Matrix

| Attack | Severity | Pass Criteria |
|--------|----------|---------------|
| **Slippage Shock** | +1, +3, +5 ticks | Edge > 0R in Normal, bounded in Extreme |
| **Spread Widening** | 15% rejection | Trade count drops, no loss explosion |
| **Stop-First Bias** | Ambiguous candles | Expectancy decreases but stays positive |
| **Latency Injection** | +1, +2 candles | Edge survives +1 candle |
| **Missing Bars** | 5% data loss | Skip trade safely, no silent invalid ORBs |
| **Trade Skipping** | 10%, 20%, 30% | Equity curve shape intact |
| **Capital Limits** | Max 2 concurrent, -3R daily | Drawdown capped, no martingale |

### Attack Harness (from STEPHARNESS.txt)
```python
@dataclass
class AttackResult:
    name: str
    avg_r: float
    winrate: float
    trades: int

def run_attack(name, backtest_fn, mutate_fn, data, **kwargs):
    attacked_data = mutate_fn(data.copy(), **kwargs)
    trades = backtest_fn(attacked_data)
    return AttackResult(...)
```

### Stop Conditions (HARD FAIL)
- ❌ Flips expectancy negative
- ❌ Explodes loss per trade
- ❌ Depends on optimistic fills
- **→ Strategy is NOT deployable**

**Output:** `step3a_attack_test_results.json`

---

## Expected Final Output

### Console Output
```
========================================
MASTER AUDIT REPORT
========================================
Database: gold.db
Date Range: 2020-12-20 to 2026-01-10
Total Days: 740

STAGE 1: DATA FOUNDATION ✅
  Step 1:   Data Integrity     [PASS] 100% (12/12 tests)
  Step 1.5: Gaps & Transitions [PASS] 100% (6/6 tests)

STAGE 2: FEATURE LAYER ✅
  Step 2:   Feature Verification [PASS] 95% (19/20 tests)
  Step 2.4: Time Assertions      [PASS] 100% (8/8 tests)

STAGE 3: STRATEGY LAYER ✅
  Step 3:   Strategy Validation [PASS] 100% (10/10 tests)
  Step 3.4: Attack Testing      [PASS] 85% (11/13 attacks survived)

========================================
VERDICT: SYSTEM READY FOR DEPLOYMENT ✅
========================================

Warnings:
  - Step 2: asia_gap feature has 2% nulls (acceptable)
  - Attack: Spread widening at 25% causes borderline performance

Critical Failures: 0
Warnings: 2
Passed: 68/71 tests (96%)

Reports Generated:
  - master_audit_report.json
  - master_audit_report.html
  - attack_matrix.csv
```

---

## File Structure

```
myprojectx/
├── audit_master.py                    # Main runner
├── audits/
│   ├── __init__.py
│   ├── step1_data_integrity.py       # Step 1 tests
│   ├── step1a_gaps_transitions.py    # Step 1.5 tests
│   ├── step2_feature_verification.py # Step 2 tests
│   ├── step2a_time_assertions.py     # Step 2.4 tests
│   ├── step3_strategy_validation.py  # Step 3 tests
│   ├── step3a_attack_tests.py        # Step 3.4 attacks
│   └── attack_harness.py             # Attack framework
├── audit_reports/                     # Generated reports
│   ├── master_audit_report.json
│   ├── master_audit_report.html
│   └── attack_matrix.csv
└── MASTER_AUDIT_PLAN.md              # This file
```

---

## Usage Examples

### Run Full Audit
```bash
python audit_master.py
```

### Run Data Foundation Only
```bash
python audit_master.py --stage 1
```

### Run Attack Tests Only
```bash
python audit_master.py --step 3.4
```

### Export Results
```bash
python audit_master.py --export audit_reports/results.csv
```

### Continuous Validation (Weekly)
```bash
python audit_master.py --quick  # Fast subset of critical tests
```

---

## Integration with Existing System

### Before Live Trading
1. ✅ Run full audit suite
2. ✅ Verify 100% pass rate on critical tests
3. ✅ Review attack matrix results
4. ✅ Confirm time-safety assertions enabled

### After Data Updates
```bash
python audit_master.py --step 1 --step 2
```

### After Strategy Changes
```bash
python audit_master.py --step 3
```

### Weekly Validation
```bash
python audit_master.py --quick --email results@yourdomain.com
```

---

## Next Steps

1. **Run Initial Audit:** `python audit_master.py`
2. **Review Reports:** Check `audit_reports/master_audit_report.html`
3. **Fix Failures:** Address any critical failures
4. **Re-run:** Verify fixes with `python audit_master.py`
5. **Go Live:** System validated and ready

---

## Critical Rules

1. **Data First:** If Step 1 fails, STOP. Fix data before proceeding.
2. **Time-Safety:** Step 2.4 assertions must be enforced in ALL code.
3. **Attack Matrix:** If any attack causes negative expectancy, strategy is NOT deployable.
4. **Determinism:** Same inputs MUST produce identical outputs.
5. **Weekly Re-audit:** Run audit suite every week to catch data drift.

---

**Status:** Framework complete, ready for execution
**Last Updated:** 2026-01-17
