# CRITICAL BUGS FLAGGED - MUST FIX BEFORE PRODUCTION
**Date:** 2026-01-28
**Status:** 🚨 **7 CRITICAL BUGS FOUND**

---

## EXECUTIVE SUMMARY

Parallel agent validation (3 agents) discovered **7 critical bugs** in the dual-track implementation:
- **4 CRITICAL** (financial loss risk)
- **2 MEDIUM** (logic errors)
- **1 LOW** (edge case)

**Most serious:** ALL validation results are INVALID because populate script uses RR=1.0 instead of strategy's configured RR.

---

## BUG #1: RR MISMATCH ❌ CRITICAL
**Priority:** **HIGHEST - ALL VALIDATION RESULTS INVALID**

**Problem:** `populate_tradeable_metrics.py` hardcodes `RR_DEFAULT = 1.0`, ignoring strategy's configured RR from validated_setups.

**Evidence:**
| Strategy ID | Configured RR | Populate Uses | Result |
|-------------|---------------|---------------|--------|
| 20 | 1.5 | **1.0 (WRONG)** | +0.149R (INVALID) |
| 21 | 2.0 | **1.0 (WRONG)** | +0.149R (INVALID) |
| 22 | 2.5 | **1.0 (WRONG)** | +0.149R (INVALID) |
| 23 | 3.0 | **1.0 (WRONG)** | +0.149R (INVALID) |

**Proof:** IDs 20-23 show IDENTICAL expectancy (+0.149R) despite having DIFFERENT configured RR.

**bugs.txt HARDPRESS NOT implemented:**
- ❌ Single source of truth for RR (should read from validated_setups)
- ❌ Fail-closed logic (defaults to 1.0 instead of aborting)
- ❌ `--rr-scan` CLI flag for explicit scanning
- ❌ Regression test to catch RR=1.0 default

**Files affected:**
- `pipeline/populate_tradeable_metrics.py` line 29 (RR_DEFAULT = 1.0)
- `pipeline/populate_tradeable_metrics.py` line 297 (no rr parameter passed)

**Impact:**
- **0/8 strategies rejected** - but with WRONG RR
- Need to re-populate with correct RR per strategy
- Need to re-validate after re-population

**Fix required:**
1. Create `get_strategy_config()` function to query validated_setups
2. Remove RR_DEFAULT constant
3. Pass strategy's RR to calculate_tradeable_for_orb()
4. Add fail-closed logic if RR is None/0
5. Print "RR EVIDENCE TABLE" before aborting
6. Create regression test

---

## BUG #2: ENTRY PRICE LOGIC (BACKWARDS) ❌ CRITICAL
**Priority:** HIGH - Financial bias in backtests

**Problem:** Entry price uses BEST fill instead of WORST fill (conservative).

**File:** `pipeline/build_daily_features.py` lines 449-455
**Also in:** `pipeline/populate_tradeable_metrics.py` lines 141-144

**Current code:**
```python
if break_dir == "UP":
    entry_price = float(entry_bar_low)  # Conservative: assume open = low (worst fill)
else:
    entry_price = float(entry_bar_high)  # Conservative: assume open = high (worst fill)
```

**Problem:**
- **UP break (buying):** LOW is the BEST fill (cheapest), not worst
- **DOWN break (selling):** HIGH is the BEST fill (most profitable), not worst
- Comment claims "conservative" but logic is OPTIMISTIC

**Correct logic (if truly conservative):**
```python
if break_dir == "UP":
    entry_price = float(entry_bar_high)  # Worst fill for long (most expensive)
else:
    entry_price = float(entry_bar_low)  # Worst fill for short (least favorable)
```

**Impact:**
- **Optimistic bias** in backtest results (better fills than realistic)
- Risk points calculated will be **smaller** than they should be
- Realized RR will be **inflated**
- Strategies may appear profitable in backtest but fail in live trading

**Fix required:**
1. Reverse the logic (HIGH for UP, LOW for DOWN)
2. OR change comment to clarify this is "optimistic" fill
3. OR explain if there's a valid reason for current logic

---

## BUG #3: MISSING OPEN COLUMN ❌ CRITICAL
**Priority:** HIGH - Wrong entry price for ALL trades

**Problem:** Code assumes OPEN = LOW (UP) or HIGH (DOWN), but this is FALSE for 1-minute bars.

**File:** `pipeline/build_daily_features.py` line 116
**Also in:** `pipeline/populate_tradeable_metrics.py` lines 36-52

**Current query:**
```python
SELECT ts_utc, high, low, close
```

**Missing:** `open` column

**Code assumption:**
```python
# Entry price = OPEN of entry bar
# In 1m OHLCV data, open is the low for UP breaks, high for DOWN breaks (first print)
```

**Why this is wrong:**

In a 1-minute bar:
- **OPEN** = first trade price
- **HIGH** = highest price during the minute
- **LOW** = lowest price during the minute
- **CLOSE** = last trade price

**Example:** Bar opens at 2545.0, spikes to 2546.0 (high), drops to 2544.0 (low), closes at 2545.5.
→ Open (2545.0) is **NEITHER** high nor low.

**Impact:**
- **Entry price is WRONG** for most trades
- Risk calculations are inaccurate
- Realized RR is incorrect
- Backtest results are unreliable

**Fix required:**
1. Fetch OPEN from bars_1m table: `SELECT ts_utc, open, high, low, close`
2. Use actual OPEN price for entry: `entry_price = float(entry_bar_open)`
3. Remove incorrect assumptions

---

## BUG #4: MISSING SCHEMA COLUMNS ❌ CRITICAL
**Priority:** MEDIUM - Code may crash on fresh init

**Problem:** Schema definition (`init_schema_v2()`) does NOT include 48 tradeable columns.

**File:** `pipeline/build_daily_features.py` lines 971-1076

**Missing columns:**
- `orb_0900_tradeable_entry_price` (x6 ORBs)
- `orb_0900_tradeable_stop_price` (x6 ORBs)
- `orb_0900_tradeable_risk_points` (x6 ORBs)
- `orb_0900_tradeable_target_price` (x6 ORBs)
- `orb_0900_tradeable_outcome` (x6 ORBs)
- `orb_0900_tradeable_realized_rr` (x6 ORBs)
- `orb_0900_tradeable_realized_risk_dollars` (x6 ORBs)
- `orb_0900_tradeable_realized_reward_dollars` (x6 ORBs)
- Total: **48 columns**

**Impact:**
- INSERT statement (lines 730-792) will FAIL if schema is created fresh
- Database will reject the insert
- Script will crash on first run
- Currently works because migration added columns separately

**Fix required:**
1. Add all 48 tradeable columns to `init_schema_v2()` method
2. Ensure schema is up-to-date before any inserts
3. Consider removing `init_schema_v2()` and using migrations only

---

## BUG #5: INCONSISTENT OPEN OUTCOME HANDLING ⚠️ MEDIUM
**Priority:** MEDIUM - Confusing output

**Problem:** Validator excludes OPEN outcomes from calculations but includes them in trade counts.

**File:** `scripts/audit/autonomous_strategy_validator.py` lines 74-75, 256-263

**Code:**
```python
# Skip NO_TRADE, OPEN, or NULL outcomes
if outcome in ['NO_TRADE', 'OPEN'] or realized_rr is None:
    continue

# But count them in total
open_count = sum(1 for t in trades if t[1] == 'OPEN')
```

**Confusing output:**
```
Total trades: 55
  WIN: 40
  LOSS: 10
  OPEN (NO_TRADE): 5 (excluded from expectancy)
Resolved trades: 50
```

**Problem:** Output suggests OPEN = NO_TRADE, but they're different outcomes.

**Impact:**
- Misleading output (users may think sample size is larger than it is)
- Sample size validation correctly uses `resolved_count` (OK)
- Confusing distinction between OPEN and NO_TRADE

**Fix required:**
1. Either fetch ONLY WIN/LOSS trades from database (exclude OPEN in SQL)
2. OR clarify output to distinguish OPEN (signal generated) from NO_TRADE (no signal)

---

## BUG #6: ZERO RISK EDGE CASE ⚠️ MEDIUM
**Priority:** MEDIUM - Rare but wrong classification

**Problem:** When `risk_points <= 0`, function returns "OPEN" instead of "NO_TRADE".

**File:** `pipeline/build_daily_features.py` lines 466-477
**Also in:** `pipeline/populate_tradeable_metrics.py` line 161

**Code:**
```python
if risk_points <= 0:
    # Should never happen, but guard against it
    return {
        "outcome": "OPEN",  # <-- BUG: Should be NO_TRADE
        ...
    }
```

**Problem:**
- **OPEN** means "signal generated, entry occurred, but no exit yet"
- **NO_TRADE** means "setup conditions failed, no valid trade possible"
- When `risk_points <= 0`, stop equals entry (invalid setup) = **NO_TRADE**

**Impact:**
- Edge case (should "never happen" per comment)
- If it happens: OPEN outcomes excluded from expectancy (correct) but counted in totals (misleading)

**Fix required:**
1. Change `"outcome": "OPEN"` to `"outcome": "NO_TRADE"`

---

## BUG #7: ENTRY BAR SKIP IN OUTCOME LOOP ℹ️ LOW
**Priority:** LOW - May be intentional conservative design

**Problem:** Outcome loop starts at bar N+2 (skips entry bar N+1).

**File:** `pipeline/build_daily_features.py` line 505
**Also in:** `pipeline/populate_tradeable_metrics.py` line 192

**Code:**
```python
# STEP 7: Check outcome using bars AFTER entry bar (conservative same-bar resolution)
for ts_utc, h, l, c in bars[signal_bar_index + 2:]:  # Start checking AFTER entry bar
```

**Question:** Is this intentional?

If entry happens at OPEN of bar N+1, then:
- **Conservative:** Check from N+2 (exit cannot happen in entry bar) ✅
- **Realistic:** Check from N+1 (exit could happen later in entry bar if TP/SL hit)

**Impact:**
- Slightly optimistic (gives entry bar a "free pass")
- For fast-moving markets, may miss exits in entry bar

**Fix required:**
1. Clarify in comments whether this is intentional conservative logic
2. OR adjust to start checking from N+1 if realistic

---

## TICK/POINT CALCULATIONS ✅ VERIFIED CORRECT

**User question:** "you know that i trade micros right, ticks - is that all calculcated properly"

**Answer:** YES, calculations are CORRECT for MGC (Micro Gold).

**MGC Specifications:**
- Tick size: $0.10 (10 cents)
- Tick value: $1.00 per tick
- **1 point = 10 ticks = $1.00 price movement**

**Verification (3 sample trades checked):**
```
Entry: $4488.20
Stop: $4493.70
Distance: $5.50 = 55 ticks = 5.5 points
Tick value: 55 ticks × $1.00 = $55.00
+ Friction: $8.40
= Total Risk: $63.40 ✅ MATCHES DATABASE (100%)
```

**All tick/point calculations verified:** 100% match between manual calculation and database values.

---

## SUMMARY TABLE

| Bug # | Severity | File | Issue | Impact |
|-------|----------|------|-------|--------|
| **1** | CRITICAL | populate_tradeable_metrics.py | RR=1.0 hardcoded (wrong) | **ALL validation results INVALID** |
| **2** | CRITICAL | build_daily_features.py | Wrong entry price (best vs worst) | Optimistic backtest bias |
| **3** | CRITICAL | build_daily_features.py | OPEN column not fetched | Wrong entry price for all trades |
| **4** | CRITICAL | build_daily_features.py | Missing 48 schema columns | Code may crash on fresh init |
| **5** | MEDIUM | autonomous_strategy_validator.py | OPEN outcome confusion | Misleading output |
| **6** | MEDIUM | build_daily_features.py | Zero risk returns OPEN (not NO_TRADE) | Wrong classification (rare) |
| **7** | LOW | build_daily_features.py | Entry bar skip in outcome loop | Slightly optimistic (may be intentional) |

**Total:** 7 bugs (4 CRITICAL, 2 MEDIUM, 1 LOW)

---

## NEXT ACTIONS (PRIORITY ORDER)

### 🚨 IMMEDIATE (CRITICAL - DO FIRST)

1. **Fix Bug #1 (RR mismatch)** - HIGHEST PRIORITY
   - Implement bugs.txt HARDPRESS requirements
   - Create `get_strategy_config()` function
   - Remove RR_DEFAULT = 1.0
   - Add fail-closed logic
   - Re-populate with correct RR per strategy
   - Re-validate all strategies

2. **Fix Bug #3 (missing OPEN column)**
   - Fetch OPEN from bars_1m
   - Use actual OPEN price for entry
   - Test on sample dates

3. **Fix Bug #2 (entry price logic)**
   - Reverse logic or clarify intent
   - Test impact on risk calculations

### ⚠️ HIGH PRIORITY

4. **Fix Bug #4 (missing schema columns)**
   - Add 48 tradeable columns to schema
   - OR remove init_schema_v2() (use migrations only)

### 📋 MEDIUM PRIORITY

5. **Fix Bug #5 (OPEN outcome confusion)**
   - Clarify output or exclude OPEN from query

6. **Fix Bug #6 (zero risk edge case)**
   - Change outcome to NO_TRADE

### ℹ️ LOW PRIORITY

7. **Review Bug #7 (entry bar skip)**
   - Clarify if intentional or needs fixing

---

## VALIDATION STATUS

**Current state:** Implementation 60% complete
- ✅ Dual-track architecture: COMPLETE
- ✅ Schema migration: COMPLETE (48 columns added)
- ✅ Data population: COMPLETE (745 dates)
- ✅ Tick/point calculations: CORRECT
- ❌ RR source of truth: NOT IMPLEMENTED
- ❌ Validation results: **INVALID** (wrong RR used)

**After fixes:**
- Re-populate tradeable metrics with correct RR
- Re-validate all 8 strategies
- Check if any pass +0.15R with correct RR
- Update DUAL_TRACK_RECONCILIATION_REPORT.md

---

## AGENT OUTPUTS

**3 agents ran in parallel:**
1. **bugs.txt verification agent:** Found RR mismatch (Bug #1)
2. **Data integrity agent:** Verified tick/point calculations ✅
3. **Code review agent:** Found 6 additional bugs (#2-7)

**All outputs saved for reference:**
- Agent 1 ID: a30817c
- Agent 2 ID: af7ffa1
- Agent 3 ID: ac1a5ef

---

**HONESTY OVER OUTCOME.**

The system correctly exposed these issues through:
- Identical expectancy for different RR configurations (Bug #1 proof)
- Agent-based comprehensive validation
- Parallel analysis revealing architectural flaws

**DO NOT DEPLOY TO PRODUCTION** until Bug #1 (RR mismatch) is fixed and re-validation is complete.
