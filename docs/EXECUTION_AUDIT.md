# ORB EXECUTION LOGIC AUDIT

## Current State (strategies/execution_engine.py)

### 1. Signal Trigger Logic

**Lines 292-314:** Entry signal detection
```python
for i, (ts_local, high, low, close) in enumerate(bars):
    if close > orb_high:
        direction = "UP"
        consec += 1
    elif close < orb_low:
        direction = "DOWN"
        consec += 1

    if consec >= confirm_bars:
        entry_price = close  # ← SIGNAL TRIGGERS HERE
        entry_ts = ts_local
        break
```

**What triggers trade:**
- N consecutive 1-minute bar **closes** outside ORB range
- Default: 1 bar (confirm_bars=1)
- Signal fires at END of bar (when close is known)

**Issue:** Signal and fill are conflated - entry_price = close implies immediate fill at close

### 2. Fill Assumptions

**Line 311:** `entry_price = close`

**Current fill logic:**
- Assumes INSTANT fill at close price when signal fires
- No slippage or delay modeled
- Equivalent to: "market order filled at exact close price"

**Lines 338-343:** Optional entry buffer
```python
if buffer_ticks > 0:
    if direction == "UP":
        entry_price += buffer_price  # Worse fill
    else:
        entry_price -= buffer_price  # Worse fill
```

**Buffer behavior:**
- Simulates slippage by degrading entry price
- Applied AFTER signal, BEFORE stops/targets calculated
- Default: 0 ticks (no buffer)

**Problem:** Buffer is NOT actual slippage - it's a post-hoc adjustment that changes stop distance

### 3. Cost Application

**NO EXPLICIT COSTS IN EXECUTION ENGINE**

Costs are applied EXTERNALLY in TCA analysis:
- Commission: $1.00 per contract
- Slippage: $1.50 (1.5 ticks)
- Total: $2.50 per round-trip trade

**When applied:** Post-backtest in tca_professional.py
- Subtracts fixed cost_r from backtest E[R]
- Does NOT affect MAE/MFE calculations
- Does NOT affect trade entry/exit prices in backtest

**Problem:** Backtest assumes perfect fills, then applies costs afterward

### 4. SL/TP Resolution Logic

**Lines 387-436:** Outcome detection (unchanged)
```python
for _, high, low, close in bars[entry_idx + 1:]:
    if direction == "UP":
        hit_stop = low <= stop_price
        hit_target = high >= target_price

        # Conservative: if both hit same bar => LOSS
        if hit_stop and hit_target:
            outcome = "LOSS"
            break
```

**Logic:**
- Uses high/low from each bar (NOT close)
- Conservative same-bar resolution (both hit = LOSS)
- MAE/MFE tracked correctly from entry_price

**This part is CORRECT and should remain unchanged**

---

## Issues Identified

### Issue 1: Signal ≠ Fill Conflation

**Current:** `entry_price = close` mixes signal (bar closed outside) with fill (instant market order)

**Reality:**
- Close confirms signal
- Fill happens AFTER close (next tick, next bar, or never)
- Fill price depends on execution style (market vs limit)

### Issue 2: No Fill Conditions

**Current:** If signal fires, fill is guaranteed

**Reality:**
- Market orders: fill guaranteed, price = next available (slippage)
- Limit orders: fill only if price retraces to limit level
- Gap scenarios: limit orders never fill if price runs away

### Issue 3: Implicit Slippage Model

**Current:**
- Backtest assumes perfect fills (entry_price = close)
- TCA adds $1.50 slippage post-hoc

**Reality:**
- Market orders: immediate fill, guaranteed slippage
- Limit orders: delayed/no fill, zero slippage if filled

### Issue 4: Buffer Ticks are Not Slippage

**Current:** buffer_ticks degrades entry price and changes stop distance

**Reality:** True slippage:
- Degrades entry price (same)
- Does NOT change intended stop distance (stop should move with entry)
- Increases absolute risk in dollars

---

## Required Changes

### 1. Separate Signal from Fill

**Signal:** Bar close outside ORB (lines 292-314) → generates INTENT to trade
**Fill:** Separate function that determines IF/WHEN/WHAT_PRICE fill occurs

### 2. Introduce Execution Modes

**Mode A: MARKET_ON_CLOSE**
- Signal: N consecutive closes outside ORB
- Fill: Immediate at close price + slippage
- Fill guarantee: 100%
- Slippage: Yes (configurable, default 1.5 ticks)

**Mode B: LIMIT_AT_ORB**
- Signal: Price touches ORB boundary (NOT close-based)
- Fill: Instant at ORB edge (high or low)
- Fill guarantee: 100% if touched
- Slippage: No (limit order at exact level)

**Mode C: LIMIT_RETRACE**
- Signal: N consecutive closes outside ORB
- Fill: Only if price retraces back to ORB boundary after signal
- Fill guarantee: Conditional (no fill if price runs away)
- Slippage: No (limit fill at ORB edge)

### 3. Explicit Cost Tracking

**In TradeResult:**
- Add `slippage_ticks: float` (actual slippage incurred)
- Add `commission: float` (fixed cost)
- Add `total_cost_r: float` (slippage + commission in R)

**In execution logic:**
- Apply slippage at fill time (Mode A only)
- Track cost_r for each trade
- MAE/MFE computed from actual fill price (including slippage)

### 4. Fill Logic Requirements

**No fill if price never reaches fill level:**
- Mode B: If ORB never touched → NO TRADE
- Mode C: If signal fires but no retrace → NO TRADE

**Edge case: Both ORB boundaries touched same bar:**
- Rule: First boundary touched gets priority
- Check high vs low, compare to ORB high/low
- If indeterminate: skip trade (conservative)

---

## Implementation Plan

### Step 1: Add ExecutionMode enum
```python
class ExecutionMode(Enum):
    MARKET_ON_CLOSE = "market_on_close"
    LIMIT_AT_ORB = "limit_at_orb"
    LIMIT_RETRACE = "limit_retrace"
```

### Step 2: Refactor execute_orb() signature
```python
def execute_orb(
    ...,
    execution_mode: ExecutionMode = ExecutionMode.MARKET_ON_CLOSE,
    slippage_ticks: float = 1.5,  # only for MARKET_ON_CLOSE
    commission_per_contract: float = 1.0
) -> TradeResult:
```

### Step 3: Separate signal detection from fill logic
```python
# Detect signal (intent to trade)
signal = detect_orb_break_signal(bars, orb_high, orb_low, confirm_bars)

if signal is None:
    return NO_ENTRY

# Attempt fill based on execution mode
fill = attempt_fill(signal, bars, execution_mode, slippage_ticks)

if fill is None:
    return NO_FILL

# Resolve outcome (unchanged)
outcome = resolve_outcome(fill, bars, stop_price, target_price)
```

### Step 4: Implement fill functions

**market_on_close_fill():**
- Entry = signal close + slippage
- Guaranteed fill
- Slippage applied in direction of trade

**limit_at_orb_fill():**
- Entry = ORB boundary (exact)
- Check if boundary touched in data
- No fill if gap or no touch

**limit_retrace_fill():**
- Signal must fire first (close outside)
- Then check if price retraces to ORB edge
- Entry = ORB boundary if retrace occurs
- No fill if price runs away

### Step 5: Update TradeResult dataclass
```python
@dataclass
class TradeResult:
    ...existing fields...
    execution_mode: str
    slippage_ticks: float
    commission: float
    cost_r: float  # (slippage + commission) / risk
    fill_ts: Optional[str]  # when fill occurred (may differ from signal)
```

### Step 6: Add tests
- Test market mode always fills
- Test limit modes skip when no touch
- Test slippage only applied in market mode
- Test MAE/MFE computed from actual fill price
- Test edge case: both boundaries touched

---

## Expected Changes

### Trade Counts by Mode

**MARKET_ON_CLOSE:** Same as current (all signals fill)
**LIMIT_AT_ORB:** More trades (touches > breaks)
**LIMIT_RETRACE:** Fewer trades (only retraces fill)

### Expectancy by Mode

**MARKET_ON_CLOSE:** Lower (slippage cost)
**LIMIT_AT_ORB:** Higher (no slippage, better price)
**LIMIT_RETRACE:** Highest (cherry-picks only retraces, best price)

### Why Slippage Differs

**Market orders:** You pay to guarantee immediate fill
**Limit orders:** You trade speed for price - only fill if market comes to you

---

## Next Steps

1. Implement ExecutionMode enum and fill functions
2. Refactor execute_orb() to use new logic
3. Add tests to prove modes work correctly
4. Re-run backtests for all 3 modes
5. Compare trade counts and expectancy
6. Update TCA to remove double-counted slippage
