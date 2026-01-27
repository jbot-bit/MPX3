# Execution Engine Refactoring Plan

## Objective
Refactor execution_engine.py to support 3 execution modes while preserving all existing logic.

## Approach: Minimal Invasive Change

Instead of rewriting the entire function, I'll:
1. Add execution_mode parameter to simulate_orb_trade()
2. Replace lines 285-343 (entry logic) with calls to execution_modes functions
3. Keep everything else identical

## Changes Required

### File: strategies/execution_engine.py

**ADD at top:**
```python
from strategies.execution_modes import (
    ExecutionMode,
    attempt_market_on_close_fill,
    attempt_limit_at_orb_fill,
    attempt_limit_retrace_fill
)
```

**MODIFY function signature (line 122):**
```python
def simulate_orb_trade(
    con: duckdb.DuckDBPyConnection,
    date_local: date,
    orb: str,
    mode: str = "1m",
    confirm_bars: int = 1,
    rr: float = 1.0,
    sl_mode: str = "full",
    buffer_ticks: float = 0,  # DEPRECATED in LIMIT modes
    entry_delay_bars: int = 0,
    max_stop_ticks: float = 999999,
    asia_tp_cap_ticks: float = 999999,
    apply_size_filter: bool = False,
    size_filter_threshold: float = None,
    execution_mode: ExecutionMode = ExecutionMode.MARKET_ON_CLOSE,  # NEW
    slippage_ticks: float = 1.5,  # NEW (only for MARKET mode)
    commission_per_contract: float = 1.0,  # NEW
) -> TradeResult:
```

**REPLACE lines 285-343 (entry logic) with:**
```python
# Attempt fill based on execution mode
if execution_mode == ExecutionMode.MARKET_ON_CLOSE:
    fill = attempt_market_on_close_fill(
        bars=bars,
        orb_high=orb_high,
        orb_low=orb_low,
        confirm_bars=confirm_bars,
        slippage_ticks=slippage_ticks,
        tick_size=TICK_SIZE
    )
elif execution_mode == ExecutionMode.LIMIT_AT_ORB:
    fill = attempt_limit_at_orb_fill(
        bars=bars,
        orb_high=orb_high,
        orb_low=orb_low,
        tick_size=TICK_SIZE
    )
elif execution_mode == ExecutionMode.LIMIT_RETRACE:
    fill = attempt_limit_retrace_fill(
        bars=bars,
        orb_high=orb_high,
        orb_low=orb_low,
        confirm_bars=confirm_bars,
        tick_size=TICK_SIZE
    )
else:
    raise ValueError(f"Invalid execution_mode: {execution_mode}")

if not fill.filled:
    return TradeResult(
        outcome='SKIPPED_NO_ENTRY',
        direction=fill.direction,
        entry_ts=None,
        entry_price=None,
        stop_price=None,
        target_price=None,
        stop_ticks=None,
        r_multiple=0.0,
        entry_delay_bars=0,
        mae_r=None,
        mfe_r=None,
        execution_mode=execution_mode.value,
        execution_params=execution_params,
        slippage_ticks=0.0,
        commission=0.0,
        cost_r=0.0,
        fill_ts=None
    )

# Fill successful - extract values
entry_price = fill.fill_price
entry_ts = fill.fill_ts
entry_idx = fill.fill_idx
direction = fill.direction

# VALIDATE: For LIMIT modes, entry should be at ORB edge
if execution_mode in (ExecutionMode.LIMIT_AT_ORB, ExecutionMode.LIMIT_RETRACE):
    if direction == "UP":
        assert abs(entry_price - orb_high) < 0.001, f"LIMIT fill should be at ORB high: {entry_price} != {orb_high}"
    else:
        assert abs(entry_price - orb_low) < 0.001, f"LIMIT fill should be at ORB low: {entry_price} != {orb_low}"

# Apply entry buffer ONLY for MARKET mode (for backwards compatibility)
# NOTE: This is DEPRECATED - use slippage_ticks instead
if execution_mode == ExecutionMode.MARKET_ON_CLOSE and buffer_ticks > 0:
    buffer_price = buffer_ticks * TICK_SIZE
    if direction == "UP":
        entry_price += buffer_price
    else:
        entry_price -= buffer_price
```

**UPDATE TradeResult dataclass (line 69):**
```python
@dataclass
class TradeResult:
    """Result from simulating a single ORB trade"""
    outcome: str
    direction: Optional[str]
    entry_ts: Optional[str]
    entry_price: Optional[float]
    stop_price: Optional[float]
    target_price: Optional[float]
    stop_ticks: Optional[float]
    r_multiple: float
    entry_delay_bars: int
    mae_r: Optional[float]
    mfe_r: Optional[float]
    execution_mode: str
    execution_params: dict
    slippage_ticks: float  # NEW: Actual slippage incurred
    commission: float  # NEW: Commission per contract
    cost_r: float  # NEW: Total cost in R (slippage + commission)
    fill_ts: Optional[str]  # NEW: When fill occurred (may differ from signal)
```

**UPDATE all TradeResult returns to include new fields:**
```python
# Example for SKIPPED_NO_ENTRY:
return TradeResult(
    ...existing fields...
    slippage_ticks=0.0,
    commission=0.0,
    cost_r=0.0,
    fill_ts=None
)
```

**COMPUTE cost_r at end (after stop_ticks calculated):**
```python
# After line 355 (stop_ticks = ...)
# Compute total cost in R
cost_in_dollars = (fill.slippage_ticks * TICK_SIZE * 10.0) + commission_per_contract
risk_in_dollars = stop_ticks * TICK_SIZE * 10.0
cost_r = cost_in_dollars / risk_in_dollars if risk_in_dollars > 0 else 0.0
```

**UPDATE final TradeResult return (after outcome resolution):**
```python
return TradeResult(
    outcome=outcome,
    direction=direction,
    entry_ts=str(entry_ts) if entry_ts else None,
    entry_price=entry_price,
    stop_price=stop_price,
    target_price=target_price,
    stop_ticks=stop_ticks,
    r_multiple=r_mult,
    entry_delay_bars=entry_delay_bars_val,
    mae_r=mae_r,
    mfe_r=mfe_r,
    execution_mode=execution_mode.value,  # String representation
    execution_params=execution_params,
    slippage_ticks=fill.slippage_ticks,
    commission=commission_per_contract,
    cost_r=cost_r,
    fill_ts=fill.fill_ts
)
```

## Testing Strategy

### 1. Backwards Compatibility Test
```python
# Current behavior (MARKET_ON_CLOSE with slippage=0) should match old behavior
old_result = simulate_orb_trade(..., buffer_ticks=0)
new_result = simulate_orb_trade(..., execution_mode=ExecutionMode.MARKET_ON_CLOSE, slippage_ticks=0)

assert old_result.entry_price == new_result.entry_price
assert old_result.outcome == new_result.outcome
```

### 2. Mode Comparison Test
```python
# Test all 3 modes on same day
market_result = simulate_orb_trade(..., execution_mode=ExecutionMode.MARKET_ON_CLOSE)
limit_orb_result = simulate_orb_trade(..., execution_mode=ExecutionMode.LIMIT_AT_ORB)
limit_retrace_result = simulate_orb_trade(..., execution_mode=ExecutionMode.LIMIT_RETRACE)

# LIMIT_AT_ORB should have entry at ORB edge
if limit_orb_result.outcome != 'SKIPPED_NO_ENTRY':
    if limit_orb_result.direction == "UP":
        assert limit_orb_result.entry_price == orb_high
    else:
        assert limit_orb_result.entry_price == orb_low

# MARKET should have slippage
if market_result.outcome != 'SKIPPED_NO_ENTRY':
    assert market_result.slippage_ticks > 0
    assert market_result.cost_r > 0

# LIMIT modes should have no slippage
if limit_orb_result.outcome != 'SKIPPED_NO_ENTRY':
    assert limit_orb_result.slippage_ticks == 0
```

### 3. Trade Count Test
```python
# Run all 3 modes across 100 days
market_trades = [simulate_orb_trade(..., execution_mode=ExecutionMode.MARKET_ON_CLOSE) for day in days]
limit_orb_trades = [simulate_orb_trade(..., execution_mode=ExecutionMode.LIMIT_AT_ORB) for day in days]
limit_retrace_trades = [simulate_orb_trade(..., execution_mode=ExecutionMode.LIMIT_RETRACE) for day in days]

market_count = sum(1 for t in market_trades if t.outcome in ('WIN', 'LOSS'))
limit_orb_count = sum(1 for t in limit_orb_trades if t.outcome in ('WIN', 'LOSS'))
limit_retrace_count = sum(1 for t in limit_retrace_trades if t.outcome in ('WIN', 'LOSS'))

# Expected: LIMIT_AT_ORB >= MARKET >= LIMIT_RETRACE
assert limit_orb_count >= market_count
assert market_count >= limit_retrace_count

print(f"MARKET: {market_count} trades")
print(f"LIMIT_AT_ORB: {limit_orb_count} trades (+{limit_orb_count - market_count})")
print(f"LIMIT_RETRACE: {limit_retrace_count} trades ({limit_retrace_count - market_count})")
```

## Rollout Plan

1. Create refactored execution_engine.py with new execution_mode parameter
2. Run test suite to verify MARKET_ON_CLOSE matches old behavior
3. Run comparison test across 100 days for all 3 modes
4. Submit for code review via code-review-pipeline skill (CRITICAL trading logic)
5. After review approval: Update all backtest scripts to use new engine
6. Re-run TCA analysis with LIMIT_AT_ORB mode to see improved expectancy
7. Update validated_setups with LIMIT mode results

## Expected Results

### Trade Counts (1000 ORB, 100 days):
- MARKET_ON_CLOSE: ~70 trades (current baseline)
- LIMIT_AT_ORB: ~75-80 trades (more fills from touches)
- LIMIT_RETRACE: ~40-50 trades (only retraces)

### Expectancy (1000 ORB RR=1.5 with L4_CONSOLIDATION filter):
- MARKET_ON_CLOSE: +0.257R (current TCA validated)
- LIMIT_AT_ORB: +0.407R (+0.15R from no slippage)
- LIMIT_RETRACE: +0.50R+ (cherry-picks best setups)

### Cost Comparison (0.3pt half-stop):
- MARKET: 0.833R (83% of risk) - UNVIABLE
- LIMIT: 0.333R (33% of risk) - VIABLE

## Risk Mitigation

1. Keep old function available as simulate_orb_trade_legacy() for comparison
2. Add extensive logging to fill functions (why fills succeeded/failed)
3. Test on historical data before live deployment
4. Start with paper trading LIMIT modes before real money
5. Monitor fill rates in live trading vs backtest (slippage model validation)
