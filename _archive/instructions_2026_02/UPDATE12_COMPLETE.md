# UPDATE12 - CRITICAL BUGS FIXED

**Date**: 2026-01-29
**Status**: ✅ BUGS FIXED, DATA REBUILDING

---

## Summary

Fixed 3 critical bugs in Quick Search that caused incorrect/contradictory data:
1. Scoring engine used wrong column names
2. One metric always returned None
3. **Pipeline data corruption: WIN trades with RR = 0.0**

All bugs traced to root cause and fixed. Data rebuild in progress.

---

## Bug 1: Quick Search Used Wrong Column Names

### Issue:
Engine looked for `orb_1000_tradeable_realized_rr_2_0` (with RR suffix).
**Column doesn't exist.** Actual column is `orb_1000_tradeable_realized_rr`.

### Fix:
Updated `auto_search_engine.py` to use correct column names.

**Commit**: `88732ca`

---

## Bug 2: One Metric Always None

### Issue:
Scoring had two paths:
- **Primary path**: Returns `profitable_trade_rate`, sets `target_hit_rate = None`
- **Fallback path**: Returns `target_hit_rate`, sets `profitable_trade_rate = None`

Result: One metric always missing (shown as 0.0% in UI).

### Fix:
Single unified query computes **both metrics** from same dataset.

**Commit**: `88732ca`

---

## Bug 3: WIN with RR <= 0 (CRITICAL DATA CORRUPTION)

### The Smoking Gun:
```
Query: SELECT COUNT(*) FROM daily_features
       WHERE outcome = 'WIN' AND realized_rr <= 0

Result: 26 trades
```

**This is IMPOSSIBLE.** If a trade wins, RR must be > 0.

### Root Cause:

**Pipeline logic error in `build_daily_features.py`:**

1. **Outcome logic** (lines 634-667):
   - Checks if price hit target
   - **Ignores costs!**
   - Marks as "WIN"

2. **RR calculation** (`cost_model.py` lines 267-268):
   ```python
   if realized_reward_dollars <= 0:
       realized_rr = 0.0  # Costs exceeded profit!
   ```

3. **Result**: WIN + 0.0R (contradiction)

### How It Happened:

```
Example trade:
- ORB size: 0.8 points
- Target (RR=1.0): 0.8 points = $8.00 profit
- Friction: $8.40 (commission $2.40 + spread $2.00 + slippage $4.00)
- Realized reward: $8.00 - $8.40 = -$0.40 (NEGATIVE!)
- cost_model returns: realized_rr = 0.0
- Price hit target → outcome = "WIN"
- Database stores: WIN with 0.0R ← IMPOSSIBLE!
```

### The Fix:

**Lines 669-677 in `build_daily_features.py`:**

```python
# STEP 8: Calculate final realized_rr based on outcome
# CRITICAL FIX: If costs exceed profit, downgrade WIN to LOSS
if outcome == "WIN":
    if realized_rr_win is not None and realized_rr_win <= 0:
        # Price hit target but costs ate all profit → not a real win
        outcome = "LOSS"  # Downgrade to LOSS
        final_realized_rr = realized_rr_win  # Keep actual RR (0.0 or negative)
    else:
        final_realized_rr = realized_rr_win
elif outcome == "LOSS":
    final_realized_rr = -1.0
else:  # OPEN
    final_realized_rr = None
```

**Logic**: If costs exceed profit, it's not a real win. Downgrade to LOSS.

### Verification (Jan 2024 Sample):

```
BEFORE FIX:
- 5 trades with WIN + RR <= 0 (contradiction)
- Profit Rate: 47.1%
- Target Hit: 52.0%
- Logical error: Profit% < Target Hit% (impossible)

AFTER FIX:
- 0 contradictions
- WIN trades: 4 trades, avg RR = +0.217R
- LOSS trades: 18 trades, avg RR = -0.722R
- Profit Rate >= Target Hit Rate (logically consistent)
```

**Commit**: `98736ef`

---

## Impact on Quick Search

### Before Fixes:
- Looked for non-existent columns → always failed to fallback
- Used baseline RR=1.0 data for all RR targets → wrong
- One metric always None → shown as 0.0%
- Data had 26 corrupted trades → unreliable

### After Fixes:
- Uses correct column names
- Computes both metrics properly
- Estimates Expected R for different RR targets
- Data will be clean after rebuild

---

## Data Rebuild Status

**Command**: `python pipeline/build_daily_features.py 2024-01-01 2026-01-31`

**Progress**: Running in background (task ID: bff2c37)

**ETA**: ~10-15 minutes for 757 days

**Verification**: Jan 2024 already rebuilt and verified clean.

---

## Files Modified

### Engine:
- `trading_app/auto_search_engine.py`
  - Fixed column names (removed non-existent RR suffix)
  - Unified query for both metrics
  - Added RR estimation for non-1.0 targets

### Pipeline:
- `pipeline/build_daily_features.py`
  - Added cost-aware outcome logic
  - Downgrades WIN → LOSS if costs exceed profit
  - Eliminates logical contradictions

### Commits:
```
98736ef - Fix critical bug: WIN with RR <= 0 (costs exceeded profit)
88732ca - Fix Quick Search scoring: use correct columns, compute both metrics
f70f4b4 - Strip back to basic UI - remove all fancy styling
```

---

## Testing Checklist

### ✅ Verified:
- [x] Column names correct (checked with PRAGMA table_info)
- [x] Both metrics computed (no more None values)
- [x] Jan 2024 data clean (0 contradictions)
- [x] Feb 2024 still has bugs (not rebuilt yet)
- [x] WIN trades now have RR > 0 only
- [x] Profit Rate >= Target Hit Rate (logical)

### ⏳ Pending:
- [ ] Full data rebuild completes
- [ ] Re-run Quick Search on clean data
- [ ] Verify results make sense
- [ ] No more 0.0% values in UI

---

## Next Steps

1. **Wait for rebuild** to complete (~10-15 min)
2. **Launch Quick Search**: `streamlit run trading_app/app_canonical.py`
3. **Run search** with ORB times: 1000, 1100
4. **Verify results**:
   - No 0.0% values
   - Profit Rate >= Target Hit Rate
   - Expected R changes with different RR targets
   - All metrics populated

---

## Lessons Learned

### Honesty Over Accuracy:
1. **Don't trust the UI** - data corruption was in the pipeline
2. **Check logical consistency** - Profit% < Target Hit% revealed the bug
3. **Trace to root cause** - UI was fine, pipeline was broken
4. **Verify assumptions** - Column names weren't what we thought

### Key Principle:
**If outcome = WIN, then RR must be > 0.**
Any violation of this is a bug, not a data quirk.

---

**Status**: ✅ FIXED - Waiting for data rebuild to complete

**Launch when ready**: `streamlit run trading_app/app_canonical.py`
