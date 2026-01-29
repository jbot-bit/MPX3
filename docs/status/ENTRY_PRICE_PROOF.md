# ENTRY PRICE PROOF (BLOCKER #2)
**Date:** 2026-01-28

---

## PART 1: SQL Query Includes OPEN Column ✅

**File:** `pipeline/build_daily_features.py` (line 113)

```python
SELECT ts_utc, open, high, low, close
FROM bars_1m
WHERE symbol = ?
  AND ts_utc >= ? AND ts_utc < ?
ORDER BY ts_utc
```

**PROOF:** ✅ The OPEN column IS fetched from bars_1m database.

---

## PART 2: Entry Price Calculation ⚠️ CRITICAL FINDING

**File:** `pipeline/build_daily_features.py` (lines 444-456)

```python
# Entry bar is the bar AFTER signal bar
entry_bar = bars[signal_bar_index + 1]
entry_ts, entry_bar_open, entry_bar_high, entry_bar_low, entry_bar_close = entry_bar

# Entry price = OPEN of entry bar (actual open from database)
# CRITICAL: Use WORST fill for conservative accounting
# UP break: Enter LONG at open, worst fill = HIGH (slippage works against you)
# DOWN break: Enter SHORT at open, worst fill = LOW (slippage works against you)
if break_dir == "UP":
    entry_price = float(entry_bar_high)  # Worst fill for long entry (conservative)
else:
    entry_price = float(entry_bar_low)  # Worst fill for short entry (conservative)
```

**CRITICAL FINDING:** ⚠️ The code does NOT use `entry_bar_open` for entry price!

**What happens:**
1. ✅ `entry_bar_open` IS unpacked from database (line 447)
2. ❌ `entry_bar_open` is NEVER used in calculation (lines 454-456)
3. ❌ Code uses `entry_bar_high` (UP) or `entry_bar_low` (DOWN) instead

---

## DECISION NEEDED: B-Entry Model Definition

**Your expectation (from blocker request):**
> "Show that B-entry uses next 1m OPEN (not high/low best-fill assumptions)"

**Current implementation:**
- Uses HIGH (UP) or LOW (DOWN) for "conservative worst-fill accounting"
- Comment says "Entry price = OPEN" but code uses HIGH/LOW
- This was marked as Bug #2 FIX in previous work

**Two interpretations:**

### Interpretation A: True B-Entry Model (Use OPEN)
```python
# Entry at NEXT 1m OPEN after signal close
entry_price = float(entry_bar_open)  # Actual fill at market open
```
**Pros:**
- Matches "B-entry" definition (entry at NEXT bar OPEN)
- More realistic (you enter at market open, not high/low)
- Simpler logic

**Cons:**
- Less conservative (assumes perfect fill at open)
- Doesn't account for slippage explicitly

### Interpretation B: Conservative Fill Assumption (Use HIGH/LOW)
```python
# Conservative worst-case fill
if break_dir == "UP":
    entry_price = float(entry_bar_high)  # Worst fill for long
else:
    entry_price = float(entry_bar_low)   # Worst fill for short
```
**Pros:**
- More conservative (pessimistic assumptions)
- Accounts for slippage implicitly

**Cons:**
- Not true "B-entry" (entry at HIGH/LOW, not OPEN)
- May understate edge (too pessimistic)

---

## RECOMMENDATION

**I believe you want Interpretation A (True B-Entry)**:
- Entry price = `entry_bar_open` (actual OPEN from database)
- Slippage should be handled separately in cost model (already has $4.00 slippage)
- B-entry means "entry at NEXT bar OPEN" not "entry at worst fill"

**If this is correct, the code needs ONE CHANGE:**

**File:** `pipeline/build_daily_features.py` (lines 449-456)

**CHANGE FROM:**
```python
# Entry price = OPEN of entry bar (actual open from database)
# CRITICAL: Use WORST fill for conservative accounting
if break_dir == "UP":
    entry_price = float(entry_bar_high)  # Worst fill for long entry (conservative)
else:
    entry_price = float(entry_bar_low)  # Worst fill for short entry (conservative)
```

**CHANGE TO:**
```python
# Entry price = OPEN of entry bar (B-entry model: enter at NEXT 1m OPEN)
# Slippage is handled separately in cost model ($4.00 per RT)
entry_price = float(entry_bar_open)
```

---

## BLOCKER #2 STATUS

**SQL Query:** ✅ OPEN column IS fetched (line 113)

**Entry Price Logic:** ❌ Code uses HIGH/LOW, NOT OPEN

**Action Required:**
1. Confirm interpretation: Should entry price = OPEN or HIGH/LOW?
2. If OPEN (recommended): Update lines 449-456 in build_daily_features.py
3. Re-populate tradeable metrics
4. Re-validate strategies

**Once confirmed, I can make the change and proceed with:**
- Backup DB
- Re-populate tradeable metrics
- Re-validate strategies
- Run test suite
