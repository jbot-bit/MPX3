# ORB OPTIMIZATION FINDINGS - CANONICAL EXECUTION

## Summary

**Date**: 2026-01-25
**Status**: In progress - running canonical optimization on all 6 ORBs

## Critical Fix: Wrong Execution Logic

### The Problem

Initial optimization scripts used **WRONG** execution logic that didn't match the canonical system:

**WRONG logic (initial scripts):**
- Risk = entry - stop
- Target = entry +/- RR × risk
- Different results than validated_setups!

**CORRECT canonical logic (build_daily_features.py):**
- Risk = ORB EDGE - stop (NOT entry - stop)
- Target = ORB EDGE +/- RR × risk (NOT entry +/- RR × risk)
- For FULL mode: risk = ORB size (high - low)
- Entry price ONLY used for fill simulation

### Why This Matters

Example for UP break with ORB high=102, low=100, entry close=103:
- **Wrong**: risk = 103 - 100 = 3.0, target @ 127 (entry + 8×3)
- **Correct**: risk = 102 - 100 = 2.0, target @ 118 (ORB edge + 8×2)

Completely different targets and R-multiples!

## Critical Fixes Applied

1. ✅ **Database path**: Changed from `data/db/gold.db` to `gold.db` (canonical path)
2. ✅ **Table name**: Changed from `daily_features` (doesn't exist for MGC) to `daily_features` (canonical table)
3. ✅ **Risk calculation**: ORB EDGE to stop (not entry to stop)
4. ✅ **Target calculation**: From ORB EDGE (not entry)
5. ✅ **Stop fractions**: 1.00 = FULL (opposite edge), 0.50 = HALF (midpoint), 0.25 = QUARTER
6. ✅ **Timezone handling**: Using `zoneinfo.ZoneInfo` for proper timezone conversions
7. ✅ **Entry detection**: First CLOSE outside ORB (not touch)

## Preliminary Results (1000 ORB)

**Best setup (Stop=1.00, RR=8.0):**
- Trades: 526
- Win rate: 15.2% (need 11.1%)
- Avg R: -0.018 (nearly breakeven!)
- Total R: -9.4

**Patterns:**
- FULL stops (1.00) work better than tight stops (0.20)
  - Stop=0.20: -1.025 avg R
  - Stop=1.00: -0.018 avg R
- Higher RR works better than lower RR
  - RR=1.5: -0.653 avg R
  - RR=8.0: -0.400 avg R
- This makes sense: fixed $6 costs have less impact with larger risk (FULL stops)

## Running Tests

Currently testing all 6 ORBs (0900, 1000, 1100, 1800, 2300, 0030) with:
- Stop fractions: 0.20, 0.25, 0.33, 0.50, 0.75, 1.00
- RR values: 1.5, 2.0, 3.0, 4.0, 6.0, 8.0
- = 36 combinations per ORB × 6 ORBs = 216 tests

## Next Steps

1. ✅ **Broad search** (running now): Test all ORBs without filters
2. **Filter testing**: Apply session/ORB size/RSI filters to promising setups
3. **Update validated_setups**: Replace with profitable canonical setups
4. **Run test_app_sync.py**: Verify database/config synchronization

## Files Affected

### ✅ Corrected (canonical logic):
- `optimize_orb_canonical.py` - Correct implementation
- `summarize_all_orb_results.py` - Analysis script

### ❌ Wrong (archived):
- `optimize_single_orb.py` - Wrong risk calculation
- `comprehensive_stop_rr_optimization.py` - Wrong table name + logic
- `test_touch_vs_close_with_filters.py` - Wrong table name

### 📋 To Do:
- `test_filters_canonical.py` - Update to canonical logic
- Update validated_setups database
- Update trading_app/config.py
- Run test_app_sync.py

## Important Reminders

1. **Always match canonical logic**: build_daily_features.py is the source of truth
2. **Test synchronization**: Run `python test_app_sync.py` after ANY database/config changes
3. **Database path**: `gold.db` (root), NOT `data/db/gold.db`
4. **Table name**: `daily_features` (MGC FULL mode), NOT `daily_features`
5. **Filters required**: Most edges are unprofitable without filters (session type, ORB size, RSI)

## Architecture Notes

**Canonical execution model** (from build_daily_features.py):
```python
# ORB edge (anchor for ALL calculations)
orb_edge = orb_high if break_dir == 'UP' else orb_low

# Stop modes
if sl_mode == "full":
    stop = orb_low if break_dir == 'UP' else orb_high
else:  # half
    stop = orb_mid

# Risk from ORB EDGE
risk = abs(orb_edge - stop)

# Target from ORB EDGE
target = orb_edge + (rr * risk) if break_dir == 'UP' else orb_edge - (rr * risk)

# Entry price ONLY for fill simulation (not used in risk/target calc)
```

This ensures R-multiples are consistent across all RR values and represent true distance from ORB edge.
