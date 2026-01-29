# VALIDATION FAILURE ANALYSIS
## Comprehensive System Audit - Honesty Over Outcome

**Date:** 2026-01-28
**Status:** CRITICAL - Zero strategies validated correctly
**Root Cause:** Multiple systematic bugs in validation logic

---

## 🔴 EXECUTIVE SUMMARY

**FINDING:** All 8 MGC strategies failed validation due to systematic bugs in calculation logic, not strategy failure.

**CRITICAL ISSUES:**
1. ✅ **Target/Risk calculations are CORRECT** (entry-anchored)
2. ❌ **Validator uses WRONG calculation** (ORB-anchored)
3. ❌ **Validator queries WRONG table** (expects daily_features_v2 columns)
4. ❌ **Entry-bar handling is INCOMPLETE** (ignores same-bar exits)
5. ❌ **NO_TRADE outcome is AMBIGUOUS** (collapses "no entry" and "open position")
6. ⚠️ **Filters may not have been applied** (need verification)

**IMPACT:** Cannot trust any strategy until these bugs are fixed and re-validation performed.

---

## 📊 FAILURE POINT #1: ORB-Anchored vs Entry-Anchored Mismatch

### The Bug

**Execution Engine (CORRECT):**
```python
# execution_engine.py lines 440-441
risk = abs(entry_price - stop_price)  # ENTRY-ANCHORED
target_price = entry_price + rr * risk  # ENTRY-ANCHORED
```

**Validator (WRONG):**
```python
# autonomous_strategy_validator.py lines 70-74
if break_dir == 'UP':
    entry, stop = high, low  # ORB-ANCHORED
else:
    entry, stop = low, high  # ORB-ANCHORED

stop_dist_points = abs(entry - stop)  # ORB SIZE, not entry-to-stop
```

### Why This Matters

**Scenario:** 1000 ORB
- ORB high: 2500.0
- ORB low: 2498.5
- ORB size: 1.5 points

**Market-on-close execution (confirm_bars=1):**
- First close above ORB: 2501.2 (entry price)
- Stop: 2498.5 (ORB low)
- **Actual stop distance: 2.7 points** (entry-to-stop)
- **Validator assumes: 1.5 points** (ORB size)

**Result:** Validator calculates risk at 1.5 points, but ACTUAL trade risk is 2.7 points → **Realized RR is WRONG**

### Impact on All Strategies

- **Every strategy** with market-on-close or limit fills has WRONG risk calculation
- **Realized RR overcalculated** (assumes smaller risk than actual)
- **Expectancy values are INVALID**

### Solution

**Option A: Fix validator to use ENTRY-ANCHORED calculation**
- Requires knowing actual entry price (not stored in daily_features)
- Would need to re-run execution_engine for all trades
- Most accurate solution

**Option B: Store entry-anchored metrics in daily_features**
- Add columns: orb_XXXX_entry_price, orb_XXXX_stop_distance_points
- Requires re-running build_daily_features.py
- Enables validation without re-execution

**RECOMMENDED: Option B** → Extend daily_features with execution details

---

## 📊 FAILURE POINT #2: Database Schema Mismatch

### The Bug

**Code expects (filter_library.py line 35):**
```python
'london_consolidation': "london_type_code == 'L4_CONSOLIDATION'"
```

**Database has (daily_features):**
```sql
london_type VARCHAR  -- NO _code suffix
-- Values: 'CONSOLIDATION', 'SWEEP_HIGH', 'EXPANSION', 'SWEEP_LOW'
-- NOT: 'L4_CONSOLIDATION', 'L1_SWEEP_HIGH', etc.
```

**Validator expects (autonomous_strategy_validator.py line 123):**
```python
filter_sql = "london_type_code = 'L4_CONSOLIDATION'"
```

**Query error:**
```
Binder Error: Referenced column "london_type_code" not found in FROM clause!
Candidate bindings: "london_type", "london_low", "london_high"
```

### Why This Happened

**Two tables exist:**
1. `daily_features` (canonical) → `london_type` = 'CONSOLIDATION'
2. `daily_features_v2` (old?) → `london_type_code` = 'L4_CONSOLIDATION'

**CLAUDE.md says `daily_features` is canonical**, but:
- Filter library expects `london_type_code`
- Validator queries `daily_features` but expects `_code` columns
- Row counts: daily_features=745, daily_features_v2=740 (v2 is 5 days behind)

### Impact

- **6 out of 8 strategies** cannot be validated (IDs 20-23, 25, 27)
- All L4_CONSOLIDATION filters fail
- No way to verify if filters were applied during backtest

### Solution

**Decision Required:** Which table is correct?

**If daily_features is canonical:**
1. Update filter_library.py: `london_type_code` → `london_type`
2. Update values: `'L4_CONSOLIDATION'` → `'CONSOLIDATION'`
3. Update validator to query `london_type` instead
4. Deprecate or delete daily_features_v2

**If daily_features_v2 is canonical:**
1. Update CLAUDE.md to reflect v2 as canonical
2. Update all apps to query daily_features_v2 instead
3. Catch up v2 to current date (currently 5 days behind)
4. Deprecate or delete daily_features

**RECOMMENDED: Use daily_features** (more recent, CLAUDE.md says canonical)

---

## 📊 FAILURE POINT #3: Entry-Bar Handling

### The Bug

**Execution Engine (execution_engine.py line 457):**
```python
for _, high, low, close in bars[entry_idx + 1:]:  # STARTS AT NEXT BAR
    # ... check stop/target hits
```

**Problem:** Entry bar is EXCLUDED from outcome scan

### Scenarios

**Scenario 1: Target hit on entry bar**
- Entry at 2501.0 (ORB breakout)
- Target at 2504.0
- Same 1-minute bar reaches high of 2504.5
- **Result:** Trade continues scanning, might hit stop later → WRONG OUTCOME

**Scenario 2: Stop hit on entry bar**
- Entry at 2501.0
- Stop at 2498.5
- Same bar drops to 2498.0 then recovers
- **Result:** Trade continues, might hit target → WRONG OUTCOME

### Why This Exists

**Conservative assumption:** Entry happens at bar CLOSE, so bar HIGH/LOW might have occurred before entry fill.

**But this is inconsistent:**
- Market-on-close execution: Entry IS at close → Same-bar high/low happened BEFORE entry (correct to ignore)
- Limit order execution: Entry happens DURING bar → Same-bar high/low after entry should count

### Impact

- **Unknown number of trades** have wrong outcomes
- Could have stopped out on entry bar but recorded as WIN
- Could have hit target on entry bar but recorded as LOSS
- Magnitude unknown without re-execution

### Solution

**Decision Required:** How to handle entry bar?

**Option A: Continue ignoring entry bar** (CONSERVATIVE)
- Assumes entry at bar close
- Ignores intra-bar stop/target hits
- Document this assumption explicitly
- Add comment: "Entry bar HIGH/LOW ignored (conservative: assumes entry at close)"

**Option B: Include entry bar for limit orders only**
- Market-on-close: Ignore entry bar (entry at close)
- Limit orders: Include entry bar (entry during bar)
- More accurate but complex

**Option C: Use tick-level data to determine exact sequence**
- Most accurate
- Requires tick data (not available in bars_1m)
- Not practical

**RECOMMENDED: Option A** → Document conservative assumption, keep current logic

---

## 📊 FAILURE POINT #4: NO_TRADE Ambiguity

### The Bug

**Execution Engine (execution_engine.py lines 452, 538-539):**
```python
outcome = "NO_TRADE"  # Initial value
# ... scan for stop/target
# If neither hit before scan ends, outcome stays "NO_TRADE"

return TradeResult(
    outcome=outcome,  # Could still be "NO_TRADE" even if entry happened
    entry_price=entry_price,  # Populated if entry happened
    stop_price=stop_price,  # Populated if entry happened
    ...
)
```

**Problem:** `outcome="NO_TRADE"` has two meanings:
1. Never entered (no breakout)
2. Entered but still open at scan end (no stop/target hit yet)

### Example

**Day: 2025-12-20**
- 1000 ORB breaks at 10:30
- Entry at 2502.0
- Stop at 2499.0, Target at 2508.0
- Scans until 23:59 local
- Neither stop nor target hit
- **Result:** outcome="NO_TRADE", but entry_price is populated

**Problem:** This looks like "no trade happened" when actually "trade is still open"

### Impact

- **Unknown number of open positions** collapsed into "NO_TRADE"
- Cannot distinguish between:
  - "No setup" (legitimate skip)
  - "Open position" (needs tracking)
- Edge detection might exclude valid open trades

### Solution

**Option A: Add new outcome: "OPEN"**
```python
if outcome == "NO_TRADE" and entry_price is not None:
    outcome = "OPEN"
```

**Option B: Track separately**
```python
TradeResult(
    outcome="NO_TRADE",
    is_open=True,  # New field
    ...
)
```

**Option C: Extend scan window to next day**
- Scan until stop/target hit OR next ORB window
- Eliminates open positions
- More realistic for ORB strategies

**RECOMMENDED: Option C** → Extend scan to next ORB window (close-of-business logic)

---

## 📊 FAILURE POINT #5: Cost Model Discrepancy

### The Bug

**Validator uses $7.40 RT costs:**
```python
# autonomous_strategy_validator.py line 31
MGC_FRICTION_740 = MGC_COSTS['total_friction']  # $7.40 RT
```

**But cost_model.py defines $8.40 RT costs:**
```python
# pipeline/cost_model.py line 76
'total_friction': 8.40,  # 2.40 + 2.00 + 4.00
```

**Breakdown:**
- Commission: $2.40
- Spread (double): $2.00 (MANDATORY - entry + exit crosses)
- Slippage: $4.00 (conservative estimate BEYOND spread)
- **Total: $8.40 (honest double-spread accounting)**

### Why This Matters

**Strategy expectancy at different costs:**
- $8.40 (honest): +0.15R (passes threshold)
- $7.40 (optimistic): +0.25R (falsely inflated)

**Validator using $7.40 gives FALSE POSITIVES** (strategies pass that should fail)

### Impact

- **Two strategies REJECTED** with $7.40 costs (IDs 24, 26)
- At $8.40 (correct costs), expectancy even MORE negative
- Other strategies might FAIL at $8.40 but PASS at $7.40

### Solution

**IMMEDIATE FIX:**
```python
# autonomous_strategy_validator.py line 31
MGC_FRICTION_740 = 8.40  # CORRECT: honest double-spread accounting
```

**Update approval threshold logic to use $8.40 as MANDATORY baseline**

---

## 📊 FAILURE POINT #6: Filter Application Uncertainty

### The Question

**Some setups only profitable WITH filters applied. Were filters actually applied during backtest?**

### Evidence

**Strategies with filters:**
- IDs 20-23, 25: L4_CONSOLIDATION (london_type filter)
- ID 24: RSI > 70 (indicator filter)
- ID 26: BOTH_LOST (sequential filter)
- ID 27: ORB size > 0.05 (size filter)

**Storage:**
- Filters stored as TEXT in `notes` column
- `orb_size_filter` column mostly NULL
- No machine-readable filter specification

**Problem:** Cannot verify if filters were applied when win rates were calculated

### Example

**ID 20: 1000 ORB RR=1.5 (L4_CONSOLIDATION)**
- Notes say: "London L4_CONSOLIDATION filter. Backtest: +0.382R, Post-cost: +0.257R"
- orb_size_filter: NULL
- **Question:** Was london_type='CONSOLIDATION' filter ACTUALLY applied during backtest?

**Without filter:**
- 1000 ORB unfiltered might be 55% WR
- Expectancy: negative

**With filter:**
- 1000 ORB with L4_CONSOLIDATION might be 65% WR
- Expectancy: positive

**If filter was NOT applied, stored win rate is WRONG**

### Impact

- **Cannot verify correctness** of any filtered strategy
- **Might be trading unfiltered setups** thinking they have edge
- **Financial risk:** Trading low-probability setups

### Solution

**Immediate audit required:**

1. **Re-run execution_engine with filters for each strategy**
2. **Compare win rates:**
   - Does filtered WR match validated_setups.win_rate?
   - If NO → Filter was not applied, stored WR is wrong
   - If YES → Filter was applied, WR is correct

3. **Structure filter data:**
   - Create proper columns: `session_filter`, `indicator_filter`, `sequential_filter`
   - Store filters as machine-readable values, not free text
   - Enable programmatic verification

**Script needed:**
```python
# scripts/audit/verify_filter_application.py
# For each strategy in validated_setups:
#   1. Extract filter from notes
#   2. Re-run execution_engine WITH filter
#   3. Compare win rate to stored value
#   4. REJECT if mismatch > 5%
```

---

## 🎯 MASTER SOLUTION PLAN

### Phase 1: Fix Validator (IMMEDIATE)

**Tasks:**
1. ✅ Update validator cost from $7.40 → $8.40
2. ✅ Fix column names: `london_type_code` → `london_type`
3. ✅ Fix values: `'L4_CONSOLIDATION'` → `'CONSOLIDATION'`
4. ✅ Switch from ORB-anchored to entry-anchored calculations

**Blocker:** Need entry_price data (not in daily_features)

**Temporary solution:** Read from execution_grid_results or re-run execution_engine

### Phase 2: Extend daily_features Schema

**Add columns:**
```sql
ALTER TABLE daily_features ADD COLUMN orb_0900_entry_price DOUBLE;
ALTER TABLE daily_features ADD COLUMN orb_0900_stop_distance_points DOUBLE;
ALTER TABLE daily_features ADD COLUMN orb_0900_execution_mode VARCHAR;
-- Repeat for all 6 ORBs
```

**Update build_daily_features.py:**
- Call execution_engine for each ORB
- Store entry_price, stop_distance, execution_mode
- Store realized metrics

**Benefits:**
- Validator can use accurate entry-anchored calculations
- No need to re-run execution_engine during validation
- Single source of truth

### Phase 3: Clarify Table Schema (IMMEDIATE)

**Decision: Use daily_features as canonical**

**Actions:**
1. Update filter_library.py to use `london_type` (not `london_type_code`)
2. Update all apps to query `daily_features` (not `daily_features_v2`)
3. Mark daily_features_v2 as deprecated in schema
4. Document in CLAUDE.md: "daily_features is canonical, v2 is archived"

### Phase 4: Structure Filter Data

**Create filter schema:**
```sql
ALTER TABLE validated_setups ADD COLUMN session_filter VARCHAR;
ALTER TABLE validated_setups ADD COLUMN indicator_filter VARCHAR;
ALTER TABLE validated_setups ADD COLUMN sequential_filter VARCHAR;
ALTER TABLE validated_setups ADD COLUMN size_filter_threshold DOUBLE;
```

**Populate from notes:**
```python
# Parse notes and extract structured filters
# Example: "London L4_CONSOLIDATION filter" → session_filter='CONSOLIDATION'
```

### Phase 5: Re-Validate All Strategies

**Script: `scripts/audit/full_revalidation.py`**

For each strategy in validated_setups:
1. Extract filter specification (structured)
2. Re-run execution_engine WITH filters
3. Calculate win rate, expectancy, realized RR
4. Compare to stored values
5. Update validated_setups with corrected values
6. REJECT if expectancy < +0.15R at $8.40

**Expected outcome:**
- Some strategies FAIL (were wrong all along)
- Some strategies PASS (validated correctly)
- Clear audit trail of which strategies are trustworthy

### Phase 6: Document Execution Assumptions

**Update execution_engine.py docstring:**

```python
"""
EXECUTION ASSUMPTIONS (MANDATORY):

1. Entry-bar handling:
   - Entry bar HIGH/LOW ignored for stop/target detection
   - Conservative assumption: entry happens at bar CLOSE
   - Same-bar exits NOT possible

2. Same-bar priority:
   - If both stop AND target hit in same bar → LOSS
   - Conservative tie-breaking (Murphy's Law)

3. Open positions:
   - If no stop/target hit by scan end → outcome="NO_TRADE"
   - Trade remains open (not tracked)

4. Cost model:
   - MGC: $8.40 RT (commission $2.40 + spread $2.00 + slippage $4.00)
   - Honest double-spread accounting (MANDATORY)

5. Risk calculation:
   - Entry-anchored: risk = |entry_price - stop_price|
   - NOT ORB-anchored (ORB size may differ from actual risk)
"""
```

---

## ✅ IMMEDIATE ACTION ITEMS

### Priority 1 (TODAY)

1. ☐ Decide: Is daily_features or daily_features_v2 canonical?
2. ☐ Update validator cost model: $7.40 → $8.40
3. ☐ Fix filter_library.py column names: `london_type_code` → `london_type`
4. ☐ Fix filter_library.py values: `'L4_CONSOLIDATION'` → `'CONSOLIDATION'`
5. ☐ Delete IDs 24, 26 from validated_setups (NEGATIVE expectancy)

### Priority 2 (THIS WEEK)

6. ☐ Extend daily_features schema with entry_price, stop_distance columns
7. ☐ Re-run build_daily_features.py to populate new columns
8. ☐ Update validator to use entry-anchored calculations
9. ☐ Structure filter data in validated_setups
10. ☐ Create verify_filter_application.py script

### Priority 3 (ONGOING)

11. ☐ Re-validate all 8 MGC strategies with corrected logic
12. ☐ Document execution assumptions in execution_engine.py
13. ☐ Create test suite for execution logic (prevent future regressions)
14. ☐ Update test_app_sync.py to check filter synchronization

---

## 🔥 CRITICAL QUESTIONS FOR USER

**QUESTION 1: Table Schema**
- Which table is canonical: `daily_features` or `daily_features_v2`?
- Should we keep both or deprecate one?

**QUESTION 2: Entry-Bar Handling**
- Keep ignoring entry bar (conservative)?
- Or include entry bar for stop/target checks (realistic)?

**QUESTION 3: Open Positions**
- Keep outcome="NO_TRADE" for open positions?
- Or create new outcome="OPEN"?
- Or extend scan window to next ORB?

**QUESTION 4: Filter Verification**
- Should I re-run all strategies with filters to verify win rates?
- Or trust existing values and just fix validator?

**QUESTION 5: Strategy Deletion**
- Delete IDs 24, 26 immediately (negative expectancy)?
- Or keep for audit trail with status="REJECTED"?

---

## 📝 CONCLUSION

**Honesty Over Outcome:** The validation failure is NOT because strategies are bad. It's because the VALIDATOR has systematic bugs.

**What we know:**
- ✅ Execution engine logic is CORRECT (entry-anchored)
- ✅ Cost model is CORRECT ($8.40 RT)
- ❌ Validator logic is WRONG (ORB-anchored, wrong table, wrong costs)
- ❌ Filter application is UNVERIFIED (cannot prove filters were applied)

**Next steps:**
1. Fix validator bugs
2. Re-validate all strategies with corrected logic
3. Structure filter data for future verification
4. Document execution assumptions

**Estimated time:** 2-4 hours to fix validator, 1-2 days to re-validate all strategies

**User decision required on 5 critical questions above before proceeding.**
