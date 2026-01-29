# VALIDATED_TRADES IMPLEMENTATION - COMPLETE ✅
**Date:** 2026-01-28

---

## EXECUTIVE SUMMARY

**Status:** ✅ **IMPLEMENTATION COMPLETE - ALL 7 STEPS DONE**

**Architecture:** STRUCTURAL vs TRADEABLE split fully operational

**Result:** 0/8 strategies APPROVED (all negative expectancy)

---

## COMPLETED STEPS

### ✅ Step 1: Create validated_trades schema

**File:** `pipeline/schema_validated_trades.sql`

**Schema:**
```sql
CREATE TABLE validated_trades (
    date_local DATE NOT NULL,
    setup_id INTEGER NOT NULL,
    instrument VARCHAR NOT NULL,
    orb_time VARCHAR NOT NULL,
    entry_price DOUBLE,
    stop_price DOUBLE,
    target_price DOUBLE,
    exit_price DOUBLE,
    risk_points DOUBLE,
    target_points DOUBLE,
    risk_dollars DOUBLE,
    outcome VARCHAR,
    realized_rr DOUBLE,
    mae DOUBLE,
    mfe DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date_local, setup_id),
    FOREIGN KEY (setup_id) REFERENCES validated_setups(id) ON DELETE RESTRICT
);
```

**Indexes Created:**
- `idx_validated_trades_setup` (setup_id, date_local)
- `idx_validated_trades_date` (date_local)
- `idx_validated_trades_instrument` (instrument)
- `idx_validated_trades_orb` (orb_time)
- `idx_validated_trades_outcome` (outcome)

**Status:** ✅ Table created, 17 columns, 5 indexes

---

### ✅ Step 2: Update populate script for validated_trades

**File:** `pipeline/populate_validated_trades.py`

**Key Changes:**
1. Writes to validated_trades (not daily_features)
2. Loads ALL strategies from validated_setups (not just first per ORB)
3. One row per (date_local, setup_id)
4. Uses RR from validated_setups per strategy
5. B-entry model: Entry = NEXT 1m OPEN after signal close

**Status:** ✅ Script created, tested, working

---

### ✅ Step 3: Remove ORB-level RR collapsing logic

**Old Code (BROKEN):**
```python
# Store first occurrence for each ORB time (lowest RR if multiple)
if orb_time not in config:
    config[orb_time] = {'rr': s['rr'], 'sl_mode': s['sl_mode'], 'filter': s['filter']}
```

**New Code (FIXED):**
```python
# Process EACH strategy separately (no collapsing)
for strategy in strategies:
    setup_id = strategy['id']
    orb_time = strategy['orb_time']
    rr = strategy['rr']  # Use strategy-specific RR

    result = calculate_tradeable_for_strategy(...)
```

**Status:** ✅ Each strategy gets its own data

---

### ✅ Step 4: Update validator to read validated_trades

**File:** `scripts/audit/autonomous_strategy_validator_v2.py`

**Key Changes:**
1. Queries validated_trades by setup_id (not daily_features)
2. Uses shared loader from load_validated_setups.py
3. RR comes from validated_setups via FK
4. Target/Risk ratio verification per strategy

**Status:** ✅ Validator working, validates all 8 strategies independently

---

### ✅ Step 5: Re-populate all dates

**Command:**
```bash
python pipeline/populate_validated_trades.py
```

**Results:**
- 745 dates processed
- 4,208 total rows inserted (8 strategies × ~526 days)
- ~30-40 seconds runtime

**Distribution:**
```
Setup ID   ORB    RR     Trades   Wins   Losses   Open
25         0900   1.5    526      193    318      14
20         1000   1.5    526      221    302      3
27         1000   1.5    526      221    302      3
21         1000   2.0    526      183    338      5
22         1000   2.5    526      149    366      11
23         1000   3.0    526      137    376      13
26         1100   1.5    526      201    308      17
24         1800   1.5    525      212    303      10
```

**Status:** ✅ All strategies populated

---

### ✅ Step 6: Re-run validator for IDs 20-27

**Command:**
```bash
python scripts/audit/autonomous_strategy_validator_v2.py
```

**Results:**
- 8/8 strategies validated
- 0/8 APPROVED (all fail +0.15R threshold)
- Sample sizes: 509-523 trades (all sufficient)

**Expectancy Results:**
| Setup ID | ORB  | RR  | Expectancy | Status   |
|----------|------|-----|------------|----------|
| 20       | 1000 | 1.5 | -0.239R    | REJECTED |
| 21       | 1000 | 2.0 | -0.236R    | REJECTED |
| 22       | 1000 | 2.5 | -0.264R    | REJECTED |
| 23       | 1000 | 3.0 | -0.224R    | REJECTED |
| 24       | 1800 | 1.5 | -0.219R    | REJECTED |
| 25       | 0900 | 1.5 | -0.341R    | REJECTED |
| 26       | 1100 | 1.5 | -0.212R    | REJECTED |
| 27       | 1000 | 1.5 | -0.239R    | REJECTED |

**Status:** ✅ All strategies validated, all negative expectancy

---

### ✅ Step 7: Generate RR comparison table

**File:** `RR_COMPARISON_TABLE.md`

**Key Findings:**
1. **B-entry model now uses OPEN:** ✅ Verified in 10 sample trades
2. **Per-strategy results available:** ✅ RR=1.5/2.0/2.5/3.0 all independent
3. **Target/Risk ratios correct:** ✅ All match configured RR values
4. **All strategies negative:** ⚠️ Range -0.341R to -0.212R

**1000 ORB RR Comparison:**
- RR=1.5: -0.239R (42.3% win rate)
- RR=2.0: -0.236R (35.1% win rate)
- RR=2.5: -0.264R (28.9% win rate)
- RR=3.0: -0.224R (26.7% win rate)

**Status:** ✅ Comparison table complete

---

## SANITY CHECK ANSWERS ✅

### "Why does it keep acting like 1R?"

**FIXED:** RR is now strategy-specific (not collapsed to 1.0 default)

**Proof:**
```sql
SELECT setup_id, orb_time, AVG(target_points / risk_points) as avg_rr
FROM validated_trades
WHERE outcome != 'NO_TRADE' AND risk_points > 0
GROUP BY setup_id, orb_time;
```

**Results:**
- Setup 20 (RR=1.5): avg_rr = 1.50 ✓
- Setup 21 (RR=2.0): avg_rr = 2.00 ✓
- Setup 22 (RR=2.5): avg_rr = 2.50 ✓
- Setup 23 (RR=3.0): avg_rr = 3.00 ✓

---

### "Why do higher RR strats vanish?"

**FIXED:** validated_trades stores ALL strategies separately

**Proof:**
```sql
SELECT orb_time, COUNT(DISTINCT setup_id) as strategy_count
FROM validated_trades
GROUP BY orb_time;
```

**Results:**
- 0900 ORB: 1 strategy (ID 25, RR=1.5)
- 1000 ORB: 4 strategies (IDs 20/21/22/23, RR=1.5/2.0/2.5/3.0)
- 1100 ORB: 1 strategy (ID 26, RR=1.5)
- 1800 ORB: 1 strategy (ID 24, RR=1.5)

**Before:** Only RR=1.5 was stored (first occurrence)
**After:** All RR values stored independently

---

### "Why do results feel wrong vs live trading?"

**FIXED:** B-entry model now uses actual OPEN price (not HIGH/LOW worst-case)

**Before:**
```python
if break_dir == "UP":
    entry_price = float(entry_bar_high)  # Pessimistic
else:
    entry_price = float(entry_bar_low)   # Pessimistic
```

**After:**
```python
# B-ENTRY: Entry at NEXT 1m OPEN after signal close
entry_price = float(entry_bar_open)
```

**Impact:** More realistic fills, matches live trading execution

---

### "Why does fixing one thing break another?"

**ROOT CAUSE:** RR was ORB-specific (not strategy-specific)

**Solution:** validated_trades architecture separates strategies

**Benefits:**
1. Change one strategy RR → only re-populate that strategy
2. Add new RR value → no schema changes
3. Compare multiple RR values → side-by-side in one query
4. No more "first occurrence" collapsing logic

---

## FILES CREATED/MODIFIED

### Created Files ✅
1. `pipeline/schema_validated_trades.sql` - Table schema
2. `pipeline/populate_validated_trades.py` - Population script
3. `scripts/audit/autonomous_strategy_validator_v2.py` - Updated validator
4. `RR_COMPARISON_TABLE.md` - Analysis and findings
5. `verify_validated_trades.py` - Verification script
6. `VALIDATED_TRADES_COMPLETE.md` - This file

### Modified Files ✅
1. `pipeline/build_daily_features.py` - B-entry uses OPEN (line 449-451)
2. `pipeline/load_validated_setups.py` - Already existed (shared loader)

### Backup Files ✅
1. `data/db/gold_backup_20260128.db` - Pre-change backup (716MB)

---

## DATABASE STATE

**Table:** validated_trades

**Rows:** 4,208 (8 strategies × 526 days average)

**Size:** ~2-3 MB (minimal overhead)

**Indexes:** 5 indexes for query performance

**Integrity:**
- All setup_id values exist in validated_setups ✓
- All date_local values exist in daily_features ✓
- All target/risk ratios match configured RR ✓
- All outcomes are valid (WIN/LOSS/OPEN/NO_TRADE) ✓

---

## BLOCKER STATUS

### ✅ BLOCKER #1: COMPLETE - Shared Loader Function

**Status:** RESOLVED

**Evidence:**
- `pipeline/load_validated_setups.py` exists
- `pipeline/populate_validated_trades.py` imports it
- `scripts/audit/autonomous_strategy_validator_v2.py` imports it
- No duplicated queries
- CHECK.TXT Req #6 satisfied

---

### ✅ BLOCKER #2: COMPLETE - Entry Price Truth

**Status:** RESOLVED

**Evidence:**
1. **SQL includes OPEN:** ✓ Line 113 in build_daily_features.py
   ```python
   SELECT ts_utc, open, high, low, close FROM bars_1m
   ```

2. **B-entry uses OPEN:** ✓ Lines 449-451 in build_daily_features.py
   ```python
   entry_price = float(entry_bar_open)
   ```

3. **Verification:** ✓ 10 sample trades show OPEN price used
   ```
   2024-01-02: Entry $2073.60 (OPEN from database)
   ```

---

## VALIDATION RESULTS

**Summary:** 0/8 strategies APPROVED

**Why?** All strategies have negative expectancy (-0.341R to -0.212R)

**This is NOT a bug.** The system is working correctly and honestly reporting:
- ORB breakouts on MGC (with current parameters) are NOT profitable
- Cost model ($8.40 RT) may be too aggressive
- B-entry model may degrade edge vs immediate entry
- OR: These specific ORB times/modes simply don't have edge

---

## NEXT STEPS (RECOMMENDED)

### Option A: Test Lower Costs

Edit `pipeline/cost_model.py`:
```python
'total_friction': 4.00  # Down from 8.40 (optimistic scenario)
```

Re-run:
```bash
python pipeline/populate_validated_trades.py
python scripts/audit/autonomous_strategy_validator_v2.py
```

**Expected:** Some strategies may pass +0.15R threshold

---

### Option B: Test Signal-Bar Entry

Change from B-entry (NEXT OPEN) to signal-bar CLOSE:
- Entry = signal bar CLOSE (immediate)
- More aggressive, less waiting time

---

### Option C: Add Filters

Test strategies with additional filters:
- Session type (CONSOLIDATION only)
- Pre-ORB travel (> 2.0 points)
- Sequential patterns (0900 LOSS → 1000 entry)

---

### Option D: Accept Reality

**Conclusion:** ORB breakouts may not be profitable on MGC with these parameters.

**Evidence:**
- Large sample sizes (509-523 trades)
- All 8 strategies negative
- Reasonable cost model
- Correct implementation

**Recommendation:** Either find filters that work OR try different approach entirely.

---

## HONESTY OVER OUTCOME ✅

**What We Built:**
1. ✅ validated_trades table (per-strategy results)
2. ✅ B-entry model (uses OPEN price)
3. ✅ Shared loader function (no code duplication)
4. ✅ Per-strategy validation (RR=1.5/2.0/2.5/3.0)
5. ✅ Complete audit trail (4,208 trades)

**What We Discovered:**
1. ⚠️ All MGC strategies are NEGATIVE expectancy
2. ⚠️ Higher RR does NOT help (still negative)
3. ⚠️ Current approach needs major overhaul OR different parameters

**System is CORRECT. The strategies are UNPROFITABLE.**

**DO NOT TRADE LIVE until expectancy is positive.**

---

## FINAL CHECKLIST ✅

- [x] Create validated_trades table
- [x] Update populate script for validated_trades
- [x] Remove ORB-level RR collapsing logic
- [x] Update validator to read validated_trades
- [x] Re-populate all dates (4,208 rows)
- [x] Re-run validator for IDs 20-27
- [x] Generate RR comparison table
- [x] Verify entry price uses OPEN
- [x] Verify target/risk ratios correct
- [x] Backup database before changes
- [x] Document all findings

**ALL STEPS COMPLETE. SYSTEM READY.**
