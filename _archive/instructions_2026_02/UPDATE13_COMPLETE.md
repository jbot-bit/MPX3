# UPDATE13 - QUICK SEARCH LOGIC FIXED

**Date**: 2026-01-29
**Status**: ✅ ENGINE FIXED, DATA REBUILDING

---

## Summary

Fixed CRITICAL logic error in Quick Search: RR > 1.0 projections used RR=1.0 hit rates (mathematically incorrect).

**User feedback**: "LOGIC DOESNT ADD UP FOR THOSE FIGURES"

**Root cause**: Database only has RR=1.0 baseline data, but engine projected RR=2.5 and RR=3.0 results using same 47% hit rate.

**Honest fix**: Restrict Quick Search to RR=1.0 only (no projections).

---

## The Logic Error

### What Quick Search Was Showing:

```
1000 ORB:
  RR=1.0: +0.235R | N: 530 | Profit: 47% | Target: 47%
  RR=2.5: +0.644R | N: 530 | Profit: 47% | Target: 47%  ← WRONG!
  RR=3.0: +0.879R | N: 530 | Profit: 47% | Target: 47%  ← WRONG!
```

### The Math Looked Right:

```
ExpR = 0.47 × 2.5 + 0.53 × (-1.0) = 0.645R  ✓
```

### But The Assumption Was WRONG:

**Assumed**: 47% hit rate at RR=2.5 (target 2.5x farther)
**Reality**: Hit rate DECREASES as target moves farther

**Analogy**: Saying "I hit 50% of 10-foot shots, so I'll hit 50% of 30-foot shots too"

---

## The Real Problem: No Multi-RR Data

### Database Check:

```sql
PRAGMA table_info(daily_features);

-- Columns found:
orb_1000_r_multiple    ← Realized RR (baseline RR=1.0 only)
orb_1000_outcome       ← WIN/LOSS/OPEN

-- Columns NOT found:
orb_1000_tradeable_realized_rr_2_0  ← Does not exist!
orb_1000_tradeable_realized_rr_2_5  ← Does not exist!
orb_1000_tradeable_realized_rr_3_0  ← Does not exist!
```

**Database only contains RR=1.0 baseline data.**

Projecting higher RR targets using same hit rate = UNRELIABLE.

---

## Additional Bug Found: Wrong Column Names (AGAIN!)

### Engine Was Querying:

```python
# Lines 359-360 (auto_search_engine.py)
realized_rr_col = f"orb_{orb_time}_tradeable_realized_rr"  ← WRONG!
outcome_col = f"orb_{orb_time}_tradeable_outcome"          ← WRONG!
```

### These Columns DON'T EXIST!

```sql
SELECT COUNT(*) FROM daily_features WHERE orb_1000_tradeable_outcome = 'WIN';
-- ERROR: Referenced column "orb_1000_tradeable_outcome" not found
```

### Correct Column Names:

```python
realized_rr_col = f"orb_{orb_time}_r_multiple"  ← CORRECT
outcome_col = f"orb_{orb_time}_outcome"         ← CORRECT
```

**This means Quick Search NEVER WORKED! It's been querying non-existent columns.**

---

## The Fix

### 1. Restrict to RR=1.0 Only

**File**: `trading_app/auto_search_engine.py`

**Lines 311-327** (Candidate generation):
```python
for orb_time in settings.orb_times:
    for rr_target in settings.rr_targets:
        # HONESTY FIX: Skip RR != 1.0 (no actual data, projections unreliable)
        if rr_target != 1.0:
            logger.warning(f"Skipping RR={rr_target} for {orb_time} (only RR=1.0 baseline data available)")
            continue

        combinations.append({
            'instrument': settings.instrument,
            'setup_family': settings.setup_family,
            'orb_time': orb_time,
            'rr_target': rr_target,
            'filters': {}
        })
```

**Lines 371-382** (Scoring logic):
```python
sample_size = result[0]
profitable_trade_rate = result[1]
target_hit_rate = result[2]
avg_realized_rr = result[3]

# Only RR=1.0 supported (baseline data only)
# Use actual average realized RR (no projections)
expected_r = avg_realized_rr

return {
    'sample_size': sample_size,
    'profitable_trade_rate': profitable_trade_rate,
    'target_hit_rate': target_hit_rate,
    'expected_r': expected_r,
    'score_proxy': expected_r
}
```

Removed flawed projection logic entirely.

### 2. Fixed Column Names

**Lines 357-372**:
```python
# FIXED: Use correct column names (no 'tradeable' prefix)
realized_rr_col = f"orb_{orb_time}_r_multiple"
outcome_col = f"orb_{orb_time}_outcome"

query = f"""
    SELECT
        COUNT(*) as sample_size,
        AVG(CASE WHEN {realized_rr_col} > 0 THEN 1.0 ELSE 0.0 END) as profitable_trade_rate,
        AVG(CASE WHEN {outcome_col} = 'WIN' THEN 1.0 ELSE 0.0 END) as target_hit_rate,
        AVG({realized_rr_col}) as avg_realized_rr
    FROM daily_features
    WHERE instrument = ?
      AND {realized_rr_col} IS NOT NULL
      AND {outcome_col} IS NOT NULL
"""
```

### 3. Updated UI

**File**: `trading_app/app_canonical.py`

**Lines 1094-1096** (Removed all RR checkboxes):
```python
# RR Targets (fixed to 1.0 - only baseline data available)
rr_targets = [1.0]
st.text("RR Target: 1.0 (baseline data only)")
```

Simplified from 24 lines to 3 lines. No more misleading multi-RR options.

---

## Why This Is Critical

### Honesty Over Accuracy

**CLAUDE.md principle**: "honesty over accuracy"

**Wrong approach**: Show fancy projections that look good but are mathematically unsound
**Right approach**: Only show real data, restrict to what we actually have

### Lessons From Update12

Update12 taught us:
- Trust logical consistency (Profit% < Target Hit% revealed bug)
- Trace to root cause (don't trust assumptions)
- Check column names (don't assume they exist)

**Same lesson applies here**: If hit rates look the same at all RR targets, that's a red flag.

### Real Trading Impact

If a trader used Quick Search projections:
- Sees "RR=3.0 expected +0.879R" (47% win rate)
- Takes trade expecting 47% success at 3R target
- Reality: Hit rate at 3R is maybe 25-30% (much lower!)
- Result: LOSSES

**Projections mislead. Real data protects.**

---

## Data Verification (Pending Rebuild)

### Expected Results After Rebuild:

```
1000 ORB RR=1.0:
  Sample Size: ~530 trades
  Profit Rate: 47% (% with RR > 0)
  Target Hit: 47% (% outcome = WIN)
  Expected R: ~+0.24R

Logical check: Profit Rate >= Target Hit Rate ✓
WIN with RR <= 0: 0 trades ✓
```

### Rebuild Status:

**Command**: `python pipeline/build_daily_features.py 2024-01-01 2026-01-31`

**Progress**: Running in background (task ID: bf06147)

**ETA**: ~10-15 minutes for 757 days

---

## Files Modified

### Engine:
- `trading_app/auto_search_engine.py`
  - Lines 311-327: Skip RR != 1.0 at candidate generation
  - Lines 357-372: Fixed column names (removed 'tradeable' prefix)
  - Lines 371-382: Removed projection logic, use actual avg_realized_rr

### UI:
- `trading_app/app_canonical.py`
  - Lines 1094-1096: Hardcoded to RR=1.0, removed checkboxes

---

## Testing Checklist

### ✅ Fixed:
- [x] Column names corrected (orb_{time}_r_multiple, orb_{time}_outcome)
- [x] RR projection logic removed
- [x] UI simplified to RR=1.0 only
- [x] Candidate generation skips RR != 1.0

### ⏳ Pending:
- [ ] Data rebuild completes
- [ ] Test Quick Search with real data
- [ ] Verify results match database query
- [ ] Confirm no projections shown

---

## Next Steps

1. **Wait for rebuild** to complete (~10-15 min)
2. **Test Quick Search**:
   ```bash
   streamlit run trading_app/app_canonical.py
   ```
3. **Run search** with ORB times: 0900, 1000, 1100
4. **Verify results**:
   - Only RR=1.0 shown
   - No projections
   - Metrics match database
   - Profit Rate >= Target Hit Rate

---

## Why RR=1.0 Only?

### Option 1: Restrict to RR=1.0 (CHOSEN)
✅ Honest (only show real data)
✅ Simple (no complex logic)
✅ Safe (no misleading projections)
❌ Limited (can't search higher RR)

### Option 2: Add Disclaimer
❌ Users ignore disclaimers
❌ Still shows wrong numbers
❌ Looks authoritative (comes from "AI search")

### Option 3: Fix Pipeline
✅ Correct (compute actual multi-RR data)
❌ Time-consuming (significant rework)
❌ Slow (must run execution_engine for each RR)
❌ Storage (152 × 5 RR targets = 760 columns!)

**Decision**: Start with Option 1 (honest), upgrade to Option 3 if needed.

---

## Relationship to Update12

### Update12 Fixed:
1. Wrong column names (query looked for RR suffix that doesn't exist)
2. One metric always None (dual-path logic)
3. WIN with RR <= 0 (pipeline didn't account for costs)

### Update13 Fixed:
1. Wrong column names AGAIN (still had 'tradeable' prefix!)
2. RR projection logic (used RR=1.0 hit rates for all RR targets)
3. UI complexity (removed misleading multi-RR checkboxes)

**Pattern**: Column name assumptions keep breaking. Need better schema documentation.

---

**Status**: ✅ FIXED - Waiting for data rebuild to complete

**Launch when ready**: `streamlit run trading_app/app_canonical.py`

---

## Technical Debt

### Future Improvements:

1. **Schema Documentation**
   - Document all daily_features columns with types and descriptions
   - Prevent future column name assumptions

2. **Multi-RR Support** (if needed)
   - Option A: Run execution_engine.py for each RR target during feature build
   - Option B: Store only RR=1.0, compute higher RR on-demand (slower but accurate)
   - Option C: Compute approximate RR scaling (hit_rate_rr2 ≈ hit_rate_rr1 × 0.8)

3. **Quick Search Filters**
   - Add ORB size filters
   - Add session travel filters
   - Add day-of-week filters
   - Currently: baseline only (no filters)

---

**Commits**:
- TBD (after testing with rebuilt data)
