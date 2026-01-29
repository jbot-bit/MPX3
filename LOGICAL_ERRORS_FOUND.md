# Logical Errors Found - 2026-01-29

**Review Status:** COMPLETE
**Severity:** 1 MEDIUM issue found

---

## Summary

After systematically reviewing the recent code changes (update4.txt, update5.txt, update6.txt, experimental scanner fixes, and Unicode fixes), I found **ONE logical error** in the Auto Search scoring logic.

**Runtime Status:** ✅ App starts without errors, no crashes

---

## Issue #1: Scoring Discrepancy in Auto Search Engine

**File:** `trading_app/auto_search_engine.py`
**Lines:** 359 vs 388
**Severity:** MEDIUM
**Status:** PRESENT IN PRODUCTION CODE

### Problem

The Auto Search engine uses **two different methods** to compute "win_rate", which are NOT equivalent:

#### Method 1: Line 359 (Primary scoring path)
```python
AVG(CASE WHEN {realized_rr_col} > 0 THEN 1.0 ELSE 0.0 END) as win_rate
```
- Computes: Proportion of trades where `realized_rr > 0`
- This is actually "positive expectancy rate" or "profitable trade rate"
- **Includes partial profits:** A trade with realized_rr = 0.1 counts as a "win"
- **Does NOT require hitting profit target**

#### Method 2: Line 388 (Fallback scoring path)
```python
AVG(CASE WHEN {outcome_col} = 'WIN' THEN 1.0 ELSE 0.0 END) as win_rate
```
- Computes: Proportion of trades where `outcome = 'WIN'`
- This is true "win rate" (hit profit target)
- **Requires hitting profit target**
- Matches how validated_setups defines "win"

### Impact

1. **Inconsistent Results:**
   - Same ORB time + RR can show different "win rates" depending on which method is used
   - Method 1 will ALWAYS show higher "win rate" than Method 2
   - Users cannot compare candidates from different scoring paths

2. **Misleading Expectations:**
   - A candidate with 60% "win rate" (Method 1) might only have 45% true win rate (Method 2)
   - User promotes candidate expecting 60% WR, gets 45% in live trading
   - Expectancy is still correct (expected_r), but perception is wrong

3. **Terminology Confusion:**
   - Column is named "win_rate" but actually measures "positive expectancy rate" in Method 1
   - Creates confusion when reading search_candidates table

### Example Scenario

**ORB 0900 RR=1.5 trades:**
- 30 trades hit profit target (WIN)
- 10 trades closed positive but didn't hit target (realized_rr = 0.3)
- 10 trades lost (LOSS)

**Method 1 (realized_rr > 0):**
- Win rate = (30 + 10) / 50 = **80%**
- Misleading: suggests 80% hit profit target

**Method 2 (outcome = 'WIN'):**
- Win rate = 30 / 50 = **60%**
- Accurate: 60% hit profit target

**Both have same expected_r**, but user perception differs significantly.

### Recommendations

**Option A: Rename Method 1 metric (RECOMMENDED)**
```python
# Line 359 - rename the metric
return {
    'sample_size': result[0],
    'profitable_trade_rate': result[1],  # NOT win_rate
    'expected_r': result[2],
    'score_proxy': result[2]
}
```

**Option B: Use Method 2 for all scoring**
- Remove Method 1 entirely
- Always use outcome-based win rate
- Consistent with validated_setups

**Option C: Document the difference**
- Add comments explaining Method 1 vs Method 2
- Store both metrics with clear names
- Let user choose which to use

### Why This Matters

This affects **Auto Search candidate evaluation**:
- Users see candidates with "win_rate" and expect it to match validated_setups
- validated_setups uses outcome-based win rate (Method 2)
- Auto Search uses realized_rr-based rate (Method 1)
- **Mismatch causes false expectations**

### Fix Priority

**MEDIUM (not blocking, but should be fixed soon)**

**Reasoning:**
- Does NOT cause crashes or data corruption
- Does NOT affect expectancy calculations (expected_r is still correct)
- DOES cause user confusion and false expectations
- DOES make candidates incomparable
- Should fix before users rely on Auto Search heavily

---

## Issue #2: None Found

After reviewing:
- ✅ Validation queue integration - field mapping correct
- ✅ Experimental scanner validation - logic sound
- ✅ Session schema migration - parsing correct
- ✅ Error handling - appropriate everywhere
- ✅ Database operations - no SQL injection risks
- ✅ Unicode handling - fixed correctly
- ✅ Timeout enforcement - working as designed

No other logical errors found.

---

## Additional Observations (Not Errors)

### 1. Hard-coded Defaults in Validation Queue
**File:** `trading_app/app_canonical.py` (line 1218)
```python
direction='BOTH', sl_mode='FULL'
```
- Auto Search candidates default to BOTH/FULL
- Might want to make configurable in future
- **NOT AN ERROR** - sensible defaults

### 2. Queue Cleanup Not Automated
**File:** `validation_queue` table
- Items marked 'IN_PROGRESS' stay in queue forever
- No automatic cleanup of old items
- Could grow large over time
- **NOT AN ERROR** - intentional for audit trail

### 3. Auto Search Timeout is Hard-coded
**File:** `trading_app/auto_search_engine.py` (line 140)
```python
self.max_seconds = max_seconds  # Default 300 in UI
```
- User can adjust in UI, but 300 seconds hard-coded as default
- Might want to make configurable in settings
- **NOT AN ERROR** - reasonable default

---

## Testing Performed

1. ✅ App startup - no crashes
2. ✅ Module imports - all successful
3. ✅ app_errors.txt - clean (no runtime errors)
4. ✅ Code review - systematic review of 1,750+ lines
5. ✅ Database schema - correct field mappings
6. ✅ Validation logic - mathematically correct
7. ✅ Error handling - appropriate try/except blocks

---

## Recommendation

**Immediate Action:**
- Fix Issue #1 (scoring discrepancy) using Option A or B
- Add unit test to verify win_rate consistency
- Document the fix in UPDATE5_COMPLETE.md

**Optional Improvements:**
- Make validation queue cleanup configurable
- Make Auto Search defaults configurable
- Add win_rate comparison test to check scripts

---

## Honesty Assessment

**I found 1 logical error after thorough review.**

**What I checked:**
- All new code from update4.txt (~300 lines)
- All new code from update5.txt (~1,150 lines)
- All new code from update6.txt (~110 lines)
- Experimental scanner fixes (~150 lines)
- Unicode fixes (~20 lines)
- **Total reviewed:** ~1,750 lines of new/modified code

**What I did NOT check:**
- Legacy code (pre-session)
- Backfill scripts (unchanged)
- Edge registry logic (unchanged)
- Strategy validation (unchanged in this session)

**Confidence Level:** HIGH

The scoring discrepancy is a real issue that will cause user confusion. Everything else is logically sound based on my review.

---

**Next Steps:**
1. Decide on fix approach (A, B, or C)
2. Implement fix
3. Add test to verify consistency
4. Update documentation
