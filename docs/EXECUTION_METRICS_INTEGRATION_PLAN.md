# Execution Metrics Integration Plan

## Summary

The 2300/0030 ORB results showing 84% WR at RR=8.0 are **RED FLAGS** due to:
1. ❌ Wrong ORB values in database (stale/corrupted data)
2. ❌ No primary key on daily_features table (schema issue)
3. ❌ Scan window may be wrong for night ORBs

**DO NOT TRADE these setups until verified!**

## What You Requested

Track BOTH metrics for every trade:
1. **Canonical R** (ORB-edge anchored) - for consistent measurement
2. **Real R** (entry-to-stop with slippage) - for actual P&L

## Integration Plan

### Phase 1: Fix Database (CRITICAL)
```bash
# 1. Backup current database
cp gold.db gold.db.backup

# 2. Rebuild daily_features with correct schema
python pipeline/init_db.py  # Fix schema
python pipeline/wipe_mgc.py  # Clear bad data
python backfill_databento_continuous.py 2024-01-01 2026-01-26  # Rebuild
```

### Phase 2: Verify Results (Before Trading)
```bash
# Re-run optimization with fixed data
python optimize_orb_canonical.py 0030
python optimize_orb_canonical.py 2300

# Verify results are realistic (WR should be 40-60% for RR=8.0)
```

### Phase 3: Add Execution Metrics
Files created:
- ✅ `execution_metrics.py` - Core calculation engine
- 📋 `execution_metrics_analyzer.py` - Batch analysis tool (TODO)
- 📋 Update `build_daily_features.py` to store both metrics (TODO)

### Phase 4: Surface in Apps
Update these files to show both metrics:
- `trading_app/app_trading_hub.py` - Show real vs canonical R
- `validated_setups` table - Add real_expected_r column
- `test_app_sync.py` - Verify both metrics sync

## Immediate Actions

### 1. ❌ DO NOT TRADE 2300/0030 ORBs yet
The 84% WR is fake. Database has wrong values.

### 2. ✅ Safe to use (verified correct):
- 1100 ORB: +0.170 avg R at Stop=0.20, RR=8.0
- 1000 ORB: -0.018 avg R at Stop=1.00, RR=8.0 (nearly breakeven)

### 3. 🔧 Fix database first
Run the Phase 1 commands above.

### 4. 📊 Then verify with execution metrics
```python
from execution_metrics import ExecutionMetricsCalculator, aggregate_metrics

# Calculate real vs canonical for verified trades
calc = ExecutionMetricsCalculator(commission=1.0, slippage_ticks=5)
# ... analyze real execution vs canonical
```

## Key Insights

### Why Track Both Metrics?

**Canonical R** (ORB-edge anchored):
- ✅ Consistent across all RR values
- ✅ Comparable setups
- ✅ Mathematical purity
- ❌ Not actual P&L

**Real R** (entry-to-stop):
- ✅ Actual P&L accounting
- ✅ Includes slippage
- ✅ True risk measurement
- ❌ Varies by entry quality

**Example:**
```
ORB: High=102, Low=100 (size=2.0)
Entry close: 102.5
Slippage: 0.5 points
Entry fill: 103.0

Canonical R (ORB-edge):
  Risk: 102 - 100 = 2.0 points
  Target (RR=3.0): 102 + (3.0 × 2.0) = 108.0

Real R (entry-to-stop):
  Risk: 103 - 100 = 3.0 points
  Target: 108.0 (same price)
  Actual RR achieved: (108 - 103) / 3.0 = 1.67 (degraded!)

Performance degradation: -1.33R due to poor entry
```

## Recommended Filters (After Fixing Database)

Test these on VERIFIED setups:
1. **Entry distance < 0.3 × ORB size** (tight entry)
2. **Immediate continuation** (next bar moves in direction)
3. **Session type filters** (CONSOLIDATION works best)
4. **ORB size filters** (avoid tiny ORBs)

## Next Steps

1. **Fix database** (Phase 1)
2. **Verify 2300/0030 results are realistic**
3. **If still profitable, add to validated_setups**
4. **Integrate execution_metrics.py into pipeline**
5. **Surface both metrics in live app**

## Files Status

### ✅ Ready:
- `execution_metrics.py` - Complete
- `optimize_orb_canonical.py` - Correct logic
- `summarize_all_orb_results.py` - Analysis tool

### ❌ Needs Fix:
- `gold.db` - Wrong ORB values for 2300/0030
- `daily_features` table - No primary key
- `build_daily_features.py` - Upsert failing due to schema

### 📋 TODO:
- Batch execution metrics analyzer
- Integrate into trading apps
- Update validated_setups schema
- Add real_expected_r column

## Warning

**DO NOT UPDATE validated_setups OR TRADE 2300/0030 until database is fixed and results verified!**

The current results are NOT REAL.
