# AUDIT SYSTEM - Quick Start Guide

**Created:** 2026-01-17
**Purpose:** Complete validation of trading system integrity
**Based on:** STEPONE through STEPTHREE documentation + STEPHARNESS

---

## 🚀 Quick Start (3 Ways to Run)

### Option 1: Double-Click Batch File (Easiest)
```
Double-click: RUN_AUDIT.bat
```
Runs complete audit suite and shows results in console.

### Option 2: Command Line (Full Control)
```bash
# Run everything
python audit_master.py

# Run specific step
python audit_master.py --step 1
python audit_master.py --step 2

# Quick audit (critical tests only)
python audit_master.py --quick
```

### Option 3: Quick Audit Batch
```
Double-click: RUN_AUDIT_QUICK.bat
```
Runs only critical tests (faster, for weekly checks).

---

## 📋 What Gets Tested

### STEP 1: Data Integrity (Foundation)
**Purpose:** Prove database matches reality

Tests:
- ✅ Session boundaries exact (Asia/London/NY)
- ✅ ORB windows exactly 5 minutes
- ✅ No missing 1-minute bars
- ✅ No duplicate timestamps
- ✅ ORB construction (high/low from first 5 mins)
- ✅ ATR validity (no zeros, reasonable range)
- ✅ Zero-lookahead guardrails

**Critical:** If Step 1 fails, STOP. Fix data before proceeding.

### STEP 2: Feature Verification
**Purpose:** Every calculated feature must be correct

Tests:
- ✅ Deterministic rebuild (same inputs → same outputs)
- ✅ ORB size = high - low (exact match)
- ✅ Session range = high - low (exact match)
- ✅ Feature distributions (no constant/clipped features)
- ✅ Leakage detection (correlation scan)

**Critical:** Features must be time-safe and mathematically correct.

### STEP 3: Strategy Validation (Future)
**Purpose:** Prove strategy is robust

Tests:
- ⏳ Strategy manifest lock
- ⏳ Backtest determinism
- ⏳ Walk-forward testing
- ⏳ Attack testing (see below)

*Note: Step 3 requires strategy implementation integration*

---

## 🎯 Attack Testing Framework (STEPHARNESS)

The attack harness simulates adversarial conditions to prove strategies are robust.

### Implemented Attacks

| Attack | Purpose | Pass Criteria |
|--------|---------|---------------|
| **Slippage Shock** | +1, +3, +5 tick slippage | Edge stays > 0R |
| **Stop-First Bias** | Ambiguous candles resolved pessimistically | Expectancy decreases but stays positive |
| **Latency Injection** | +1, +2 candle delay | Edge survives +1 candle |
| **Trade Skipping** | 10%, 20%, 30% trades skipped | Equity curve shape intact |
| **Spread Widening** | 15% fills rejected | No loss explosion |
| **Missing Bars** | 5% data loss | Skip trade safely |

### How to Use Attack Harness

```python
from audits.attack_harness import run_all_attacks, AttackResult

# Your backtest function (takes data, returns trades DataFrame)
def my_backtest_fn(data):
    # ... your backtest logic
    return trades_df  # Must have: r_multiple, outcome columns

# Run attacks
baseline = AttackResult(name="Baseline", avg_r=0.48, winrate=58.0, trades=240)
attack_results = run_all_attacks(my_backtest_fn, clean_data, baseline)

# View results
print(attack_results)
```

### Stop Conditions (HARD FAIL)
❌ **DO NOT DEPLOY** if any attack:
- Flips expectancy negative
- Explodes loss per trade (< -2.0R)
- Shows 80%+ degradation (optimistic fill dependency)

---

## 📊 Reading Results

### Console Output
```
========================================
MASTER AUDIT SUMMARY
========================================

✅ Step 1: Data Integrity
   Passed: 7/7 (100.0%)

✅ Step 2: Feature Verification
   Passed: 12/13 (92.3%)

OVERALL: 19/20 tests passed (95.0%)

✅ VERDICT: SYSTEM READY FOR DEPLOYMENT
========================================
```

### Report Files (audit_reports/)
- **master_audit_report.json** - Complete audit results
- **audit_summary.csv** - Quick summary spreadsheet
- **step1_data_integrity_report.json** - Detailed Step 1 results
- **step2_feature_verification_report.json** - Detailed Step 2 results

---

## ⚠️ What to Do If Tests Fail

### Data Integrity Failures (Step 1)
**Impact:** CRITICAL - Everything downstream is invalid

**Actions:**
1. Check `audit_reports/step1_data_integrity_report.json` for details
2. Identify which test failed
3. Common issues:
   - **Missing bars:** Re-run backfill for affected dates
   - **Duplicate timestamps:** Check data import logic
   - **ATR zeros:** Re-run `build_daily_features_v2.py`
4. Fix issue
5. Re-run: `python audit_master.py --step 1`
6. Verify 100% pass rate before proceeding

### Feature Verification Failures (Step 2)
**Impact:** HIGH - Calculated features may be wrong

**Actions:**
1. Check `audit_reports/step2_feature_verification_report.json`
2. Identify which feature failed
3. Common issues:
   - **ORB size mismatch:** Re-run `build_daily_features_v2.py`
   - **Non-deterministic rebuild:** Check for random seeds, timestamp dependencies
   - **High null percentage:** Check feature calculation logic
4. Fix issue
5. Re-run: `python audit_master.py --step 2`
6. Verify 100% pass rate

### Attack Test Failures (Step 3.4)
**Impact:** CRITICAL - Strategy not deployable

**Actions:**
1. Review attack matrix results
2. If any attack causes negative expectancy:
   - **DO NOT DEPLOY**
   - Strategy relies on optimistic fills
   - Re-design with more conservative assumptions
3. If edge degrades but stays positive:
   - Acceptable (realistic markets)
   - Adjust position sizing for extra margin

---

## 🔄 When to Run Audits

### Before Live Trading (MANDATORY)
```bash
python audit_master.py
```
- Must achieve 100% pass rate on Step 1 and Step 2
- Review all warnings
- Confirm attack matrix results acceptable

### After Data Updates
```bash
python audit_master.py --step 1 --step 2
```
- Run after backfilling new data
- Run after re-building features

### After Strategy Changes
```bash
python audit_master.py --step 3
```
- Run after modifying strategy logic
- Run after changing filters or RR values

### Weekly Validation
```bash
python audit_master.py --quick
```
- Quick health check
- Catches data drift early

---

## 📁 File Structure

```
myprojectx/
├── audit_master.py                    # Main runner ⭐
├── RUN_AUDIT.bat                      # Windows quick start ⭐
├── RUN_AUDIT_QUICK.bat                # Quick audit
├── AUDIT_README.md                    # This file
├── MASTER_AUDIT_PLAN.md               # Complete documentation
├── audits/
│   ├── __init__.py
│   ├── attack_harness.py             # Attack framework
│   ├── step1_data_integrity.py       # Step 1 tests
│   └── step2_feature_verification.py # Step 2 tests
├── audit_reports/                     # Generated reports
│   ├── master_audit_report.json
│   ├── audit_summary.csv
│   ├── step1_data_integrity_report.json
│   └── step2_feature_verification_report.json
└── gold.db                            # Your database
```

---

## 🛠️ Troubleshooting

### "Database not found: gold.db"
**Solution:** Run from project directory where gold.db is located
```bash
cd C:\Users\sydne\OneDrive\myprojectx
python audit_master.py
```

### "ModuleNotFoundError: No module named 'duckdb'"
**Solution:** Install required packages
```bash
pip install duckdb pandas numpy
```

### "Permission denied" on Windows
**Solution:** Right-click batch file → "Run as administrator"

### Tests taking too long
**Solution:** Use quick mode
```bash
python audit_master.py --quick
```

---

## 📚 Additional Documentation

- **MASTER_AUDIT_PLAN.md** - Complete audit specification
- **STEPONE.txt** - Data integrity test details
- **STEPTWO.txt** - Feature verification test details
- **STEPTHREE.txt** - Strategy validation test details
- **STEPHARNESS.txt** - Attack testing framework

---

## ✅ Success Criteria

**Ready for deployment when:**
- ✅ Step 1: 100% pass rate (no data integrity issues)
- ✅ Step 2: ≥95% pass rate (minor warnings acceptable)
- ✅ Step 3: All attacks pass (edge stays positive)
- ✅ No critical failures
- ✅ All warnings reviewed and understood

---

## 🚨 Critical Rules

1. **Data First:** If Step 1 fails, STOP. Fix data before proceeding.
2. **No Shortcuts:** Do not skip tests to save time.
3. **Time-Safety:** Zero-lookahead must be enforced at code level.
4. **Attack Matrix:** If any attack flips expectancy, DO NOT DEPLOY.
5. **Weekly Re-audit:** Run `--quick` audit every week.

---

**Status:** Framework complete, ready for execution
**Last Updated:** 2026-01-17
**Contact:** Review results in audit_reports/ folder
