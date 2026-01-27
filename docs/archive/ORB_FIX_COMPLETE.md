# ORB Temporal Logic Fix - COMPLETE

## Date: 2026-01-19

## Problem Statement

The chart analyzer had a critical bug where ORB states could revert once broken:

**Before Fix:**
- Chart at 09:10: 0900 ORB shows "BROKEN_UP" (price at 2655)
- Chart at 10:10: 0900 ORB shows "INSIDE" (price retraced to 2645)
- **BUG**: ORB state changed from BROKEN to INSIDE

This violated trading logic because:
1. **ORBs cannot "un-break"** - Once an ORB breaks, the trade signal is triggered
2. **Recommendations changed retroactively** - Same ORB gave different signals at different times
3. **No temporal consistency** - Past decisions could be invalidated by future price action

## Root Cause

`csv_chart_analyzer.py` line 140-151:

```python
# OLD BROKEN CODE
latest_price = df['close'].iloc[-1]

if latest_price > orb_high:
    position = "ABOVE"
elif latest_price < orb_low:
    position = "BELOW"
else:
    position = "INSIDE"
```

**Issue**: Used LATEST price to determine ORB state, causing state to flip as price moved.

## Solution Implemented

### 1. Explicit State Model

Added 5 ORB states with one-way transitions:

```
PENDING → FORMING → ACTIVE → BROKEN_UP → LOCKED
                           → BROKEN_DOWN → LOCKED

NEVER: BROKEN_UP → ACTIVE (cannot revert!)
```

**States:**
- `PENDING`: ORB time not reached yet (e.g., 1800 ORB at 10:00)
- `FORMING`: Inside 5-minute ORB window (e.g., 09:00-09:05)
- `ACTIVE`: ORB formed, waiting for breakout
- `BROKEN_UP`: First close above ORB (LOCKED forever)
- `BROKEN_DOWN`: First close below ORB (LOCKED forever)

### 2. Lock-on-Break Logic

```python
# NEW CORRECT CODE
# Find FIRST close outside ORB after window closed
for idx, row in bars_after_orb.iterrows():
    close = row['close']

    if close > orb_high:
        state = "BROKEN_UP"
        break_time = row['time']
        break_price = close
        break  # LOCK STATE - stop searching
```

**Key Change**: Find FIRST break, then LOCK state permanently.

### 3. Separate Display from Decision

```python
# Current price position (for display only)
current_price = df['close'].iloc[-1]
if current_price > orb_high:
    current_position = "ABOVE"
elif current_price < orb_low:
    current_position = "BELOW"
else:
    current_position = "INSIDE"

# ORB state (for trading decisions) - IMMUTABLE once broken
if state in ["BROKEN_UP", "BROKEN_DOWN"]:
    result["locked"] = True  # Cannot change
    result["current_price_position"] = current_position  # Can change (display only)
```

### 4. Time-Gated Evaluation

```python
# Don't show future ORBs as active
if latest_time < orb_start_utc:
    return {"state": "PENDING", "note": "ORB window not reached yet"}

# Don't evaluate ORB while it's forming
if orb_start_utc <= latest_time < orb_end_utc:
    return {"state": "FORMING", "note": "ORB forming now"}
```

### 5. Validation

Added `_validate_orb_states()` to catch illegal transitions:

```python
# Rule: BROKEN states must be locked
if state in ["BROKEN_UP", "BROKEN_DOWN"] and not locked:
    raise ValueError(f"{orb_name}: BROKEN state must have locked=True")

# Rule: LOCKED states cannot revert
if locked and state not in ["BROKEN_UP", "BROKEN_DOWN"]:
    raise ValueError(f"{orb_name}: LOCKED state cannot change")
```

### 6. Updated Scoring

```python
# Prioritize broken ORBs (active trades)
if orb_state in ["BROKEN_UP", "BROKEN_DOWN"]:
    score += 30  # HIGHEST priority
    if orb_data.get("locked"):
        score += 10  # Immutable state = high confidence

# Lower score for active ORBs (waiting for break)
elif orb_state == "ACTIVE":
    score += 15

# Skip pending/forming ORBs
elif orb_state in ["PENDING", "FORMING"]:
    score += 5  # Low priority
```

### 7. Enhanced UI Display

Mobile UI now shows:
- **PENDING**: Future ORBs (grayed out, upcoming)
- **FORMING**: ORBs forming now (orange, animated)
- **ACTIVE**: ORBs ready for breakout (blue, waiting)
- **BROKEN**: ORBs with confirmed signal (green/red, locked icon)

```
0900 ORB 🔒
Range: $2640.00 - $2650.00 (10.00 pts)
LONG BROKEN at 09:06 @ $2650.50
🔒 LOCKED (immutable)
```

## Test Results

Created `test_orb_temporal_consistency.py` - ALL TESTS PASS:

```
TEST 1: Chart at 09:10 (break just occurred)
0900 ORB State: BROKEN_UP ✅
0900 ORB Locked: True ✅

TEST 2: Chart at 10:10 (price retraced inside ORB)
0900 ORB State: BROKEN_UP ✅ (STILL BROKEN!)
0900 ORB Locked: True ✅
Current Price Position: INSIDE ✅ (display only)

TEST 3: Chart at 11:10 (price still inside ORB)
0900 ORB State: BROKEN_UP ✅ (IMMUTABLE!)
0900 ORB Locked: True ✅

TEST 4: Validation
All states passed validation ✅
```

**CRITICAL PROOF**: ORB state remained BROKEN_UP even though current price moved back inside the ORB range.

## Files Changed

### Core Logic
1. **`trading_app/csv_chart_analyzer.py`**
   - Replaced `_detect_orbs()` with stateful logic (lines 114-259)
   - Added `_validate_orb_states()` (lines 261-298)
   - Updated `_score_setup_csv()` for state-based scoring (lines 507-557)
   - Updated `_generate_reasoning_csv()` for state display (lines 575-633)

### UI
2. **`trading_app/mobile_ui.py`**
   - Updated ORB display section (lines 1570-1670)
   - Shows PENDING, FORMING, ACTIVE, BROKEN states
   - Displays lock icon for immutable states
   - Shows break time and price for broken ORBs

### Testing
3. **`test_orb_temporal_consistency.py`** (NEW)
   - Proves temporal consistency across 09:10 → 10:10 → 11:10
   - Tests state immutability
   - Validates one-way transitions

## Benefits

### Before Fix (BROKEN):
- ❌ ORB states flip as price moves
- ❌ Recommendations change retroactively
- ❌ Cannot trust historical signals
- ❌ Impossible to backtest correctly
- ❌ Would cause real money losses

### After Fix (CORRECT):
- ✅ ORB states lock once broken (immutable)
- ✅ Recommendations stay consistent over time
- ✅ Historical signals are reliable
- ✅ Proper backtesting possible
- ✅ Matches real trading constraints

## Example

**Scenario**: 0900 ORB breaks up at 09:06, then price retraces at 10:00.

### Before Fix (BROKEN):
```
09:10 Chart: "0900 ORB BROKEN_UP → Trade LONG"
10:10 Chart: "0900 ORB INSIDE → Wait for breakout"  ❌ WRONG!
```

### After Fix (CORRECT):
```
09:10 Chart: "0900 ORB BROKEN_UP at 09:06 → Trade LONG 🔒"
10:10 Chart: "0900 ORB BROKEN_UP at 09:06 → Trade LONG 🔒"
11:10 Chart: "0900 ORB BROKEN_UP at 09:06 → Trade LONG 🔒"
```

Current price position updates (for display), but ORB state stays LOCKED.

## Technical Details

### State Tracking

Each ORB result now contains:

```python
{
    "state": "BROKEN_UP",           # Immutable once broken
    "locked": True,                 # Cannot change
    "break_time": datetime(...),     # When it broke
    "break_price": 2650.50,         # Price at break
    "high": 2650.0,                 # ORB levels
    "low": 2640.0,
    "current_price_position": "INSIDE"  # For display only (can change)
}
```

### Temporal Logic Rules

1. **One-way transitions**: States can only move forward (PENDING → FORMING → ACTIVE → BROKEN → LOCKED)
2. **Lock-on-break**: First close outside ORB locks the state forever
3. **Time-gating**: Future ORBs show as PENDING until their window arrives
4. **Separation of concerns**: ORB state (decision) vs current price position (display)

## Verification

Run the test:

```bash
python test_orb_temporal_consistency.py
```

Expected output: ALL TESTS PASSED!

## Impact

This fix is **CRITICAL** for:
- **Live trading**: Prevents missed trades or wrong signals
- **Backtesting**: Ensures historical accuracy
- **Strategy validation**: ORB state matches actual trading behavior
- **User trust**: Recommendations don't change retroactively

**Without this fix, the system was unusable for live trading.**

## Status

✅ **COMPLETE** - All tests pass, ready for deployment.

---

**Fixed by**: Claude Sonnet 4.5
**Date**: 2026-01-19
**Test Status**: ✅ ALL TESTS PASS
