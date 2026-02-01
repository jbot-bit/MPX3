# UPDATE13 COMPLETE (update13.txt)

**Date**: 2026-01-29
**Status**: ✅ PHASES 0-3 COMPLETE, ⏳ PHASE 4 PENDING

---

## SUMMARY

Implemented update13.txt requirements to fix Quick/Auto Search:
1. ✅ Use correct tradeable_* columns
2. ✅ Remove misleading "RR=1.0" labels
3. ✅ Add Truth Panel for transparency
4. ✅ Add Sanity Checks expander

---

## CRITICAL FINDING: tradeable vs non-tradeable

**HUGE PERFORMANCE DIFFERENCE**:

```
NON-TRADEABLE (limit order at ORB edge):
  Win Rate: 60.0%
  Expected R: +0.200R ✅ Profitable

TRADEABLE (wait for 1st close outside):
  Win Rate: 47.0%
  Expected R: -0.247R ❌ LOSING!

Difference: 0.447R per trade!
```

**Why tradeable performs worse**:
- Worse entry price (farther from ORB edge)
- Same stop (opposite ORB edge)
- Result: Worse entry + same risk = worse R-multiple

**Implication**: Entry method selection is CRITICAL. Waiting for confirmation costs 0.447R per trade.

---

## PHASE 0: FINDINGS (✅ COMPLETE)

### Column Structure:
```
daily_features has TWO sets of columns per ORB:
1. Non-tradeable (limit order):
   - orb_{time}_outcome
   - orb_{time}_r_multiple

2. Tradeable (1st close outside):
   - orb_{time}_tradeable_outcome    ← NOW USING
   - orb_{time}_tradeable_realized_rr ← NOW USING
```

### RR Dimension:
- **daily_features**: NO RR dimension (single model per ORB)
- **validated_setups**: YES RR dimension (multiple RR per ORB)

**Conclusion**: Quick Search must operate in "Proxy Mode" (no RR-specific data).

---

## PHASE 1: CORE LOGIC FIXES (✅ COMPLETE)

### Fix 1: Use Correct Columns

**File**: `trading_app/auto_search_engine.py`

**Lines 358-360**:
```python
# BEFORE (WRONG):
realized_rr_col = f"orb_{orb_time}_r_multiple"
outcome_col = f"orb_{orb_time}_outcome"

# AFTER (CORRECT):
realized_rr_col = f"orb_{orb_time}_tradeable_realized_rr"
outcome_col = f"orb_{orb_time}_tradeable_outcome"
```

**Impact**: Now uses correct entry method (1st close outside ORB).

### Fix 2: Update Labels

**File**: `trading_app/app_canonical.py`

**Lines 1094-1097**:
```python
# BEFORE (MISLEADING):
rr_targets = [1.0]
st.text("RR Target: 1.0 (baseline data only)")

# AFTER (HONEST):
rr_targets = [None]  # NULL = proxy mode
st.info("📊 **Stored Model Proxy** (from daily_features tradeable columns)")
st.caption("⚠️ These metrics use a single stored model per ORB time. Entry: 1st close outside ORB. For RR-specific results, use validated_setups.")
```

### Fix 3: Handle None RR Target

**File**: `trading_app/auto_search_engine.py`

**Lines 314-317**:
```python
# BEFORE:
if rr_target != 1.0:
    logger.warning(f"Skipping RR={rr_target}...")
    continue

# AFTER:
if rr_target is not None and rr_target != 1.0:
    logger.warning(f"Skipping RR={rr_target} (proxy mode only)")
    continue
```

---

## PHASE 2: TRUTH PANEL (✅ COMPLETE)

### Expander 1: "What exactly is being measured?"

**File**: `trading_app/app_canonical.py` (lines 1252-1274)

Shows:
- Data source: `daily_features` table
- Entry rule: 1st close outside ORB (NOT limit order)
- Stop loss: Opposite edge of ORB
- Columns used: `tradeable_outcome`, `tradeable_realized_rr`
- Metric definitions:
  - **Target Hit Rate**: % outcome == 'WIN'
  - **Profitable Rate**: % realized_rr > 0
  - **Expected R**: mean(realized_rr)

**Purpose**: User knows EXACTLY what's being measured (no assumptions).

### Expander 2: "Sanity Checks"

**File**: `trading_app/app_canonical.py` (lines 1276-1330)

Shows:
- **Counts**: n_total, n_win, n_profit, n_loss
- **Invariant Checks** with ✅/❌ indicators:
  1. WIN count <= Profitable count (should be true)
  2. No WIN with RR <= 0 (should be 0 violations)
  3. Expected R matches mean(realized_rr) (within 0.001)

**Purpose**: Self-auditing. UI validates its own data logic.

### Sample Output:

```
Counts for 1000 ORB:
- Total Trades: 530
- WIN outcomes: 249 (47.0%)
- Profitable (RR > 0): 249 (47.0%)
- Losses (RR < 0): 281 (53.0%)

Invariant Checks:
✅ WIN count <= Profitable count (249 <= 249)
✅ No WIN with RR <= 0 (found 0 violations)
✅ Expected R matches mean(realized_rr) (-0.247 ≈ -0.247)
```

---

## PHASE 3: DATA MODEL (✅ NO CHANGES NEEDED)

Existing tables are sufficient:
- `search_runs` (metadata)
- `search_candidates` (results)
- `search_memory` (deduplication)

Fields already exist:
- `target_hit_rate` ✅
- `profitable_trade_rate` ✅
- `score_proxy` (used for expected_r) ✅
- `rr_target` (NULL for proxy mode) ✅

**No migration required.**

---

## PHASE 4: VERIFICATION (⏳ NEXT STEP)

**TODO**: Create `scripts/check/check_quick_search.py`

Requirements:
- Runtime: <10 seconds
- Test column usage (verify tradeable_* columns used)
- Test metric definitions (verify formulas)
- Test sanity invariants (verify checks pass)
- Print PASS/FAIL with reasons

**Command to run** (after creating script):
```bash
python scripts/check/check_quick_search.py
```

---

## FILES MODIFIED

### Engine:
- `trading_app/auto_search_engine.py`
  - Lines 358-360: Use tradeable_* columns
  - Lines 314-317: Handle None rr_target
  - Lines 382-384: Update comments

### UI:
- `trading_app/app_canonical.py`
  - Lines 1094-1097: Fix labels (Proxy mode)
  - Lines 1252-1330: Add Truth Panel (2 expanders)

### Documentation:
- `UPDATE13_PLAN.md` (created)
- `UPDATE13_FINAL.md` (this file)

---

## VERIFICATION COMMANDS

### 1. Test tradeable columns:
```bash
python scratchpad/test_tradeable_columns.py
```

Expected output:
```
TRADEABLE (1st close outside):
  Sample: 530 | Profit: 47.0% | Target Hit: 47.0% | ExpR: -0.247R
```

### 2. Launch app:
```bash
streamlit run trading_app/app_canonical.py
```

### 3. Run Quick Search:
- Navigate to "Quick Search" tab
- Select ORB times: 1000
- Click "Run Search"
- Verify results show:
  - Info box: "Stored Model Proxy"
  - Expander: "What exactly is being measured?"
  - Expander: "Sanity Checks" with ✅ indicators

---

## NON-NEGOTIABLES COMPLIANCE

✅ **Discovery is deterministic** - No LLM usage
✅ **Canonical table: daily_features** - Used tradeable columns
✅ **"WIN" = hit target** - Verified via outcome column
✅ **No false "RR=1.0" labels** - Changed to "Proxy Mode"
✅ **Manual confirm** - Not changed (still manual)
✅ **No Streamlit freeze** - No long-running operations added
✅ **Max runtime 300s** - Not changed

---

## KEY LESSONS

### 1. Entry Method Matters (0.447R difference!)
- Limit order at edge: +0.200R
- Wait for 1st close outside: -0.247R
- **Takeaway**: Confirmation costs money

### 2. Column Names Matter
- daily_features has TWO column sets (tradeable vs non-tradeable)
- Using wrong columns = analyzing wrong strategy
- **Takeaway**: Always verify columns in PHASE 0

### 3. Labels Matter
- "RR=1.0" implies RR-specific data (misleading)
- "Proxy Mode" is honest about limitations
- **Takeaway**: Transparency builds trust

### 4. Self-Auditing Works
- Sanity Checks expander catches data bugs
- UI validates its own logic
- **Takeaway**: Build verification into the product

---

## NEXT STEPS

### Immediate (User Testing):
1. Launch app: `streamlit run trading_app/app_canonical.py`
2. Test Quick Search with 1000 ORB
3. Verify Truth Panel expanders work
4. Confirm metrics match expectations

### Medium Priority:
1. Create verification script (`scripts/check/check_quick_search.py`)
2. Test with other ORB times (0900, 1100, 1800)
3. Document tradeable vs non-tradeable differences

### Future Enhancements:
1. Add toggle to switch between tradeable/non-tradeable columns
2. Show both entry methods side-by-side for comparison
3. Add filters (ORB size, session travel, day-of-week)
4. Consider RR-specific backtest integration (if needed)

---

## TECHNICAL DEBT

### High Priority:
- **Schema documentation**: Document all daily_features columns (tradeable vs non-tradeable)
- **Verification script**: Automate Phase 4 checks

### Medium Priority:
- **Entry method comparison**: Add UI to compare limit order vs 1st close
- **Performance metrics**: Track query speeds
- **Error handling**: Better error messages for missing columns

### Low Priority:
- **Multi-RR support**: If needed, integrate with execution_engine
- **Filter combinations**: Add ORB size + travel filters
- **Export results**: CSV download for candidates

---

## COMMITS

**0f24bf9** - UPDATE13 (update13.txt): Fix Quick Search columns + add Truth Panel
- Use tradeable_* columns (correct entry method)
- Fix UI labels (no more "RR=1.0")
- Add Truth Panel (transparency + sanity checks)
- FINDING: tradeable shows -0.247R (vs +0.200R non-tradeable)

---

**Status**: ✅ PHASES 0-3 COMPLETE

**Next**: Create verification script (PHASE 4)

**Ready to test**: `streamlit run trading_app/app_canonical.py`
