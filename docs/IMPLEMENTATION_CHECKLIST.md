# Implementation Checklist - ORB Optimization Project

## Status: Audit Complete, Ready to Execute

All assumptions locked. Execute tasks in dependency order.

---

## ☑️ Phase 1: Fix Database (CRITICAL - Task #1)

### Prerequisites
- [ ] Read AUDIT_LOCKED_ASSUMPTIONS.md completely
- [ ] Understand all 4 batches of locked assumptions
- [ ] Backup current database

### Execution
```bash
# 1. Backup
cd /c/Users/sydne/OneDrive/Desktop/MPX2_fresh
cp gold.db gold.db.backup_2026-01-25

# 2. Fix schema
python pipeline/init_db.py

# 3. Rebuild (takes ~30-60 minutes)
python backfill_databento_continuous.py 2024-01-01 2026-01-26
```

### Verification
```bash
# Verify 0030 ORB values
python -c "
import duckdb
conn = duckdb.connect('gold.db')
row = conn.execute('''
    SELECT orb_0030_high, orb_0030_low
    FROM daily_features
    WHERE instrument='MGC' AND date_local='2026-01-09'
''').fetchone()
print(f'Expected: high=4504.2, low=4491.6')
print(f'Got: high={row[0]}, low={row[1]}')
assert abs(row[0] - 4504.2) < 1.0, 'FAIL: ORB high mismatch'
assert abs(row[1] - 4491.6) < 1.0, 'FAIL: ORB low mismatch'
print('✅ PASS')
"

# Verify primary key
python -c "
import duckdb
conn = duckdb.connect('gold.db')
schema = conn.execute('PRAGMA table_info(daily_features)').fetchdf()
pk_cols = schema[schema['pk'] > 0]
assert len(pk_cols) > 0, 'FAIL: No primary key'
print('Primary key columns:', list(pk_cols['name']))
print('✅ PASS')
"
```

### Acceptance
- [ ] ✅ Primary key exists on (date_local, instrument)
- [ ] ✅ 0030 ORB values match actual bars
- [ ] ✅ build_daily_features.py can upsert without errors

---

## ☑️ Phase 2: Re-run Optimizations (Task #2)

### Prerequisites
- [ ] ✅ Phase 1 complete and verified
- [ ] Updated optimize_orb_canonical.py with $3 costs
- [ ] Verified LOCKED ASSUMPTIONS are embedded in code

### Execution
```bash
# Run all 6 ORBs (takes ~15-20 minutes)
for orb in 0900 1000 1100 1800 2300 0030; do
    echo "Running $orb ORB..."
    python optimize_orb_canonical.py $orb > results_${orb}_verified.txt 2>&1
done

# Summarize
python summarize_all_orb_results.py > summary_verified.txt
cat summary_verified.txt
```

### Verification Protocol (4 steps)
```bash
# For each ORB, run verification
python verify_optimization_results.py 1100 optimization_results_1100_canonical.json
python verify_optimization_results.py 1000 optimization_results_1000_canonical.json
# ... etc for all 6 ORBs
```

### Red Flag Checks
- [ ] ❌ No WR > 70% for RR > 4.0
- [ ] ❌ No avg R > RR/2
- [ ] ❌ All WR within realistic ranges:
  - RR=1.5: 50-65%
  - RR=3.0: 30-45%
  - RR=6.0: 15-25%
  - RR=8.0: 10-15%

### Acceptance
- [ ] ✅ All verifications pass (4 steps × 6 ORBs = 24 checks)
- [ ] ✅ NO_OUTCOME rate < 30% for all ORBs
- [ ] ✅ Results match daily_features for RR=1.0 FULL

---

## ☑️ Phase 3: Integrate Execution Metrics (Task #3)

### Prerequisites
- [ ] ✅ Phase 2 complete and verified
- [ ] execution_metrics.py has locked assumptions embedded

### Changes to build_daily_features.py
```python
# Add imports
from execution_metrics import ExecutionMetricsCalculator

# In build_features():
calc = ExecutionMetricsCalculator(commission=1.5, slippage_ticks=5.0)

# For each ORB, calculate both metrics
for orb_time in ['0900', '1000', '1100', '1800', '2300', '0030']:
    # ... existing ORB calculation ...

    # Add execution metrics
    metrics = calc.calculate_trade_metrics(
        orb_high=orb_data['high'],
        orb_low=orb_data['low'],
        entry_close=entry_close,
        break_dir=orb_data['break_dir'],
        bars_1m=bars_after_orb,
        rr=1.0,  # Database uses RR=1.0
        stop_mode='full'
    )

    # Store both canonical and real metrics
```

### Schema Updates
```sql
-- Add to daily_features table
ALTER TABLE daily_features ADD COLUMN orb_0900_real_risk DOUBLE;
ALTER TABLE daily_features ADD COLUMN orb_0900_real_r_multiple DOUBLE;
ALTER TABLE daily_features ADD COLUMN orb_0900_slippage_cost_r DOUBLE;
ALTER TABLE daily_features ADD COLUMN orb_0900_entry_distance DOUBLE;
-- Repeat for all 6 ORBs
```

### Acceptance
- [ ] ✅ daily_features has both canonical and real columns
- [ ] ✅ Real R within 0.10R of canonical for good setups
- [ ] ✅ Apps show both metrics side-by-side
- [ ] ✅ test_app_sync.py passes

---

## ☑️ Phase 4: Test Filters (Task #4)

### Prerequisites
- [ ] ✅ Phase 2, 3 complete
- [ ] Identified setups passing ALL 4 acceptance criteria

### Candidate Setups
Based on Phase 2 results, test filters on setups with:
1. Avg R > 0.05 (near-profitable, might improve with filters)
2. Win rate within realistic range
3. Sample size > 100 trades

### Execution
```bash
# Example for 1100 ORB
python test_filters_canonical.py 1100 0.20 4.0
python test_filters_canonical.py 1100 0.33 6.0

# Test all promising setups
```

### Filters to Test
- [ ] Session type (CONSOLIDATION, SWEEP_HIGH, SWEEP_LOW)
- [ ] ORB size (>1.5 ATR, <0.8 ATR)
- [ ] RSI (>70, <30)
- [ ] Entry quality (<0.3 × ORB size from edge)
- [ ] Combinations

### Acceptance
- [ ] ✅ Found ≥1 filtered setup with avg R > 0.20
- [ ] ✅ Filtered WR still realistic
- [ ] ✅ Sample size ≥30 trades after filtering
- [ ] ✅ Verified with execution_metrics.py

---

## ☑️ Phase 5: Update validated_setups (Task #5)

### Prerequisites
- [ ] ✅ All phases 1-4 complete
- [ ] Have ≥1 setup passing ALL 4 acceptance criteria:
  1. Avg R > 0.15 after costs
  2. Win rate within realistic range
  3. Sample size > 100 trades
  4. Real R within 0.10R of canonical

### Before Making Changes
```bash
# Backup
cp gold.db gold.db.pre_update
```

### Update Database
```sql
-- Example: Add profitable 1100 ORB setup
INSERT INTO validated_setups (
    instrument, orb_time, rr, sl_mode,
    orb_size_filter, session_filter,
    win_rate, expected_r, sample_size
) VALUES (
    'MGC', '1100', 4.0, '0.20',
    NULL, 'CONSOLIDATION',
    45.2, 0.25, 120
);
```

### Update config.py
```python
# trading_app/config.py
MGC_ORB_SIZE_FILTERS = {
    '0900': None,
    '1000': None,
    '1100': None,  # Update if filtered
    '1800': None,
    '2300': None,
    '0030': None,
}
```

### CRITICAL: Run Sync Test
```bash
python test_app_sync.py
```

**DO NOT PROCEED if this test fails!**

### Acceptance
- [ ] ✅ test_app_sync.py passes ALL tests
- [ ] ✅ config.py matches validated_setups exactly
- [ ] ✅ trading_app/app_trading_hub.py works
- [ ] ✅ unified_trading_app.py works
- [ ] ✅ All apps show both canonical and real R

---

## ✅ Final Checklist

Before trading ANY setup:

- [ ] ✅ Database rebuilt and verified
- [ ] ✅ All optimization results verified (4-step protocol)
- [ ] ✅ Execution metrics integrated
- [ ] ✅ Filters tested and profitable found
- [ ] ✅ validated_setups updated
- [ ] ✅ test_app_sync.py passes
- [ ] ✅ All apps work correctly
- [ ] ✅ Both canonical and real R shown in apps

---

## 🚨 Red Flags - STOP if ANY of these occur

1. ❌ Win rate >70% for RR>4.0
2. ❌ ORB values don't match bars_1m
3. ❌ NO_OUTCOME rate >30%
4. ❌ Results change drastically with small parameter tweaks
5. ❌ test_app_sync.py fails
6. ❌ Real R degradation >0.20R from canonical

---

## 📁 Key Files Reference

### Documentation
- `AUDIT_LOCKED_ASSUMPTIONS.md` - Source of truth for all assumptions
- `AUDIT_COMPLETE_SUMMARY.md` - Audit results and next steps
- `IMPLEMENTATION_CHECKLIST.md` - This file

### Code (with embedded assumptions)
- `optimize_orb_canonical.py` - Optimization engine
- `execution_metrics.py` - Dual risk tracking
- `verify_optimization_results.py` - 4-step verification
- `build_daily_features.py` - Feature pipeline

### Verification
- `test_app_sync.py` - Database/config sync test
- `verify_optimization_results.py` - Results verification

---

## 📞 Support

If you encounter issues:
1. Check AUDIT_LOCKED_ASSUMPTIONS.md for definitions
2. Run verify_optimization_results.py to diagnose
3. Review red flags checklist
4. DO NOT trade until all phases pass

---

**Current Status**: Phase 1 pending (database rebuild required)

**Next Action**: Execute Phase 1 checklist above
