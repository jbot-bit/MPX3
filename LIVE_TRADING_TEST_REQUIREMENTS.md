# LIVE TRADING TEST REQUIREMENTS - MPX3

**Status**: MANDATORY
**Enforcement**: All pull requests for live trading code
**Effective Date**: 2026-01-29

---

## STANDING RULE: BOUNDARY + STATE TEST SUITE

**Any code that runs in LIVE mode must pass a "boundary + state" test suite.**

This rule is **NON-NEGOTIABLE** and applies to:
- Entry/exit logic
- Position sizing calculations
- Risk management code
- Data validation
- State management
- API integrations
- Database queries
- Price/P&L calculations

---

## WHAT IS A BOUNDARY + STATE TEST?

### Boundary Tests
Tests that verify code handles edge cases and extreme inputs correctly:
- Empty data (DataFrames with 0 rows)
- Single data point (minimal valid input)
- Null/None values
- Missing columns
- Out-of-range values (negative prices, zero ATR, etc.)
- Exact boundaries (e.g., exactly at ORB end time)
- Floating point precision issues

### State Tests
Tests that verify code maintains consistency across state transitions:
- Symbol changes (MGC → NQ → MGC)
- Connection loss and reconnection
- Partial data availability
- Concurrent modifications (race conditions)
- Session state corruption
- Stale cache issues
- Resource cleanup on errors

---

## TEST REQUIREMENTS BY CODE TYPE

### 1. Entry/Exit Logic
**File Pattern**: `*entry_rules.py`, `*execution_*.py`, `*strategy_*.py`

#### Boundary Tests Required:
- [ ] Empty bars DataFrame
- [ ] Single bar DataFrame
- [ ] Bars missing required columns
- [ ] ORB with 0 size
- [ ] Exact time boundary (now == orb_end)
- [ ] Timestamps out of order

#### State Tests Required:
- [ ] Concurrent DataFrame modification (TOCTOU)
- [ ] Multiple calls with same input (idempotent)
- [ ] State cleanup on error

**Example Test**:
```python
def test_entry_rules_empty_bars():
    """Test that entry rules handle empty bars without crashing"""
    bars = pd.DataFrame()  # Empty
    result = compute_1st_close_outside(
        bars=bars,
        orb_high=2700,
        orb_low=2690,
        orb_start=datetime(2026, 1, 29, 9, 0),
        orb_end=datetime(2026, 1, 29, 9, 5),
        direction='LONG'
    )
    assert result is None  # Should return None, not crash

def test_entry_rules_toctou_race():
    """Test that concurrent modification doesn't crash"""
    bars = get_test_bars()

    def modify_bars():
        time.sleep(0.01)
        bars.drop(columns=['timestamp'], inplace=True)

    thread = threading.Thread(target=modify_bars)
    thread.start()

    # Should not crash (uses defensive copy)
    result = compute_orb_range(bars, ...)
    thread.join()

    # Either returns valid result or None
    assert result is None or isinstance(result, dict)
```

---

### 2. Position Sizing & Risk Management
**File Pattern**: `*risk_*.py`, `*position_*.py`, `*sizing_*.py`

#### Boundary Tests Required:
- [ ] Zero account size
- [ ] Negative risk per trade
- [ ] Risk > 100% of account
- [ ] Zero ATR (stop distance calculation)
- [ ] Price exactly at stop level
- [ ] Max position size exceeded

#### State Tests Required:
- [ ] Multiple positions on same instrument
- [ ] Position modification during calculation
- [ ] Account size change mid-calculation

**Example Test**:
```python
def test_position_sizing_zero_atr():
    """Test position sizing with zero ATR (can't calculate stop)"""
    result = calculate_position_size(
        account_size=10000,
        risk_per_trade=1.0,  # 1%
        entry_price=2700,
        stop_price=2690,
        atr=0.0  # Zero ATR - edge case
    )
    assert result is None or result['shares'] == 0

def test_position_sizing_negative_risk():
    """Test that negative risk is rejected"""
    with pytest.raises(ValueError):
        calculate_position_size(
            account_size=10000,
            risk_per_trade=-5.0,  # Negative!
            entry_price=2700,
            stop_price=2690,
            atr=2.5
        )
```

---

### 3. Data Validation & Loading
**File Pattern**: `*data_loader.py`, `*validator.py`, `*bars_*.py`

#### Boundary Tests Required:
- [ ] Empty DataFrame from API
- [ ] Missing columns in response
- [ ] Null values in critical fields
- [ ] Duplicate timestamps
- [ ] Gaps in time series
- [ ] Data from wrong symbol

#### State Tests Required:
- [ ] Connection loss during fetch
- [ ] Symbol change during load
- [ ] Partial response handling
- [ ] Resource cleanup on error

**Example Test**:
```python
def test_data_loader_empty_response():
    """Test data loader handles empty API response"""
    loader = DataLoader("MGC")

    # Mock API returning empty data
    with patch.object(loader, '_fetch_from_projectx', return_value=pd.DataFrame()):
        result = loader.fetch_latest_bars(lookback_minutes=60)

    # Should return empty with correct columns, not crash
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert result.empty

def test_data_loader_symbol_change():
    """Test that symbol change cleans up old state"""
    loader = DataLoader("MGC")
    old_symbol = loader.symbol

    # Change symbol
    loader.symbol = "NQ"
    loader.fetch_latest_bars()

    # Verify uses new symbol
    assert loader.active_contract_symbol != old_symbol
```

---

### 4. Price/P&L Calculations
**File Pattern**: `*pnl_*.py`, `*calculator.py`, `*execution_*.py`

#### Boundary Tests Required:
- [ ] Zero realized_rr
- [ ] Negative P&L calculation
- [ ] Entry price == current price (no movement)
- [ ] Floating point precision (0.1 + 0.2 != 0.3)
- [ ] Very large P&L (overflow check)
- [ ] Stop hit exactly at entry

#### State Tests Required:
- [ ] P&L recalculation after price update
- [ ] Multiple position updates in sequence
- [ ] Unrealized → Realized transition

**Example Test**:
```python
def test_pnl_calculation_zero_movement():
    """Test P&L when price hasn't moved"""
    pnl = calculate_pnl(
        entry_price=2700.0,
        current_price=2700.0,  # No movement
        position_size=1,
        direction='LONG'
    )
    assert math.isclose(pnl, 0.0, abs_tol=0.01)

def test_pnl_floating_point_precision():
    """Test that floating point errors don't cause wrong P&L"""
    # Known floating point issue: 0.1 + 0.2 != 0.3
    pnl = calculate_pnl(
        entry_price=2700.1,
        current_price=2700.3,
        position_size=1,
        direction='LONG'
    )
    expected = 0.2 * 10  # $2.00 profit
    assert math.isclose(pnl, expected, abs_tol=0.01)
```

---

### 5. State Management (Streamlit Apps)
**File Pattern**: `*app_*.py`, `*terminal*.py`, `*ui*.py`

#### Boundary Tests Required:
- [ ] Session state not initialized
- [ ] Missing required keys
- [ ] Invalid data types in state
- [ ] State corruption after error

#### State Tests Required:
- [ ] Symbol change cleanup
- [ ] Multiple tab switches
- [ ] Browser refresh
- [ ] Concurrent user sessions
- [ ] State rollback on error

**Example Test**:
```python
def test_session_state_symbol_change():
    """Test that symbol change cleans up dependent state"""
    # Initialize with MGC
    st.session_state.current_symbol = "MGC"
    init_session_state()

    old_loader = st.session_state.data_loader
    assert old_loader.symbol == "MGC"

    # Change to NQ
    st.session_state.current_symbol = "NQ"
    init_session_state()

    # Verify cleanup
    assert st.session_state.data_loader != old_loader
    assert st.session_state.data_loader.symbol == "NQ"
    assert st.session_state.strategy_engine is None  # Cleared

def test_session_state_missing_key():
    """Test that missing keys don't crash app"""
    # Clear a required key
    if "data_loader" in st.session_state:
        del st.session_state.data_loader

    # Should reinitialize, not crash
    init_session_state()
    assert "data_loader" in st.session_state
```

---

## TEST SUITE STRUCTURE

### Directory Layout
```
tests/
├── boundary/
│   ├── test_entry_rules_boundary.py
│   ├── test_data_loader_boundary.py
│   ├── test_position_sizing_boundary.py
│   └── test_pnl_calculation_boundary.py
├── state/
│   ├── test_symbol_change_state.py
│   ├── test_connection_loss_state.py
│   ├── test_concurrent_access_state.py
│   └── test_cleanup_state.py
└── live_trading_suite.py  # Combined runner
```

### Running the Test Suite
```bash
# Run all boundary + state tests
python -m pytest tests/boundary/ tests/state/ -v

# Run specific test category
python -m pytest tests/boundary/ -v  # Boundary only
python -m pytest tests/state/ -v    # State only

# Run live trading suite (combines both)
python tests/live_trading_suite.py

# Run with coverage
python -m pytest tests/boundary/ tests/state/ --cov=trading_app --cov-report=html
```

---

## ENFORCEMENT

### Pull Request Checklist
Before merging code that touches live trading:

- [ ] Boundary tests added for all edge cases
- [ ] State tests added for all state transitions
- [ ] All tests pass locally
- [ ] Coverage > 80% for modified code
- [ ] Manual testing completed in staging
- [ ] Code review includes test review

### Automated Checks
```yaml
# .github/workflows/live-trading-tests.yml
name: Live Trading Tests

on: [pull_request]

jobs:
  boundary-state-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run boundary tests
        run: pytest tests/boundary/ -v
      - name: Run state tests
        run: pytest tests/state/ -v
      - name: Check coverage
        run: pytest tests/boundary/ tests/state/ --cov=trading_app --cov-fail-under=80
```

---

## EXAMPLES OF VIOLATIONS

### ❌ BAD: No boundary tests
```python
def calculate_position_size(account_size, risk_pct, stop_distance):
    # No validation!
    shares = (account_size * risk_pct) / stop_distance
    return shares
# PROBLEM: Crashes if stop_distance = 0, no test for it
```

### ✅ GOOD: Boundary tests included
```python
def calculate_position_size(account_size, risk_pct, stop_distance):
    # Validate boundaries
    if stop_distance <= 0:
        raise ValueError("stop_distance must be positive")
    if risk_pct <= 0 or risk_pct > 100:
        raise ValueError("risk_pct must be 0-100")

    shares = (account_size * risk_pct / 100) / stop_distance
    return shares

# Test included:
def test_position_sizing_zero_stop():
    with pytest.raises(ValueError, match="stop_distance must be positive"):
        calculate_position_size(10000, 1.0, 0.0)
```

---

### ❌ BAD: No state tests
```python
def init_session_state():
    if "data_loader" not in st.session_state:
        st.session_state.data_loader = DataLoader(st.session_state.current_symbol)
# PROBLEM: If symbol changes, data_loader not reinitialized, no test for it
```

### ✅ GOOD: State tests included
```python
def init_session_state():
    # Track symbol changes
    if "last_symbol" not in st.session_state:
        st.session_state.last_symbol = None

    if st.session_state.last_symbol != st.session_state.current_symbol:
        # Clean up old state
        if st.session_state.data_loader:
            st.session_state.data_loader.close()
        st.session_state.data_loader = None
        st.session_state.last_symbol = st.session_state.current_symbol

    if "data_loader" not in st.session_state or st.session_state.data_loader is None:
        st.session_state.data_loader = DataLoader(st.session_state.current_symbol)

# Test included:
def test_symbol_change_cleanup():
    st.session_state.current_symbol = "MGC"
    init_session_state()
    old_loader = st.session_state.data_loader

    st.session_state.current_symbol = "NQ"
    init_session_state()

    assert st.session_state.data_loader != old_loader  # New loader created
```

---

## RATIONALE

### Why This Rule Exists:
1. **Ghost Audit Found 53 Bugs** - 40% were boundary/state issues
2. **Production Safety** - Live trading requires zero tolerance for crashes
3. **Real Money Risk** - Bugs cause financial losses
4. **Prevent Regressions** - Tests catch bugs before deployment

### What This Rule Prevents:
- Empty DataFrame crashes (17 instances found)
- TOCTOU race conditions (1 instance found)
- State corruption on symbol change (1 instance found)
- NULL parameter bugs (1 instance found)
- Float comparison errors (1 instance found)
- Resource leaks (1 instance found)

### Cost of Non-Compliance:
- Production crashes during live trading
- Wrong trades executed (wrong instrument, wrong size)
- Financial losses
- System downtime
- User trust erosion

---

## EXEMPTIONS

### When This Rule Does NOT Apply:
- Research/analysis code (not in trading path)
- One-off scripts in `scripts/` directory
- Visualization/UI code that doesn't affect trades
- Historical backtesting (non-live)

### Partial Exemption (Relaxed Requirements):
- Internal admin tools (fewer boundary tests acceptable)
- Staging-only features (can defer tests until production-ready)

---

## IMPLEMENTATION CHECKLIST

### For Existing Code:
- [ ] Audit all live trading code paths
- [ ] Write boundary tests for identified edge cases
- [ ] Write state tests for identified state transitions
- [ ] Achieve 80%+ test coverage
- [ ] Document test rationale in docstrings

### For New Code:
- [ ] Write tests BEFORE implementation (TDD)
- [ ] Include boundary tests in initial PR
- [ ] Include state tests in initial PR
- [ ] Run test suite before requesting review
- [ ] Add tests to CI/CD pipeline

---

## MAINTENANCE

### Quarterly Review:
- Review test coverage metrics
- Identify gaps in boundary/state testing
- Update test suite based on production incidents
- Add new test categories as system evolves

### Post-Incident Protocol:
After any production bug:
1. Write test that would have caught the bug
2. Add to test suite
3. Run full suite to verify fix
4. Update this document if new test category needed

---

## RESOURCES

### Test Templates:
- `tests/templates/boundary_test_template.py`
- `tests/templates/state_test_template.py`

### Documentation:
- `GHOST_AUDIT_COMPLETE.md` - Original bug findings
- `DEEP_AUDIT_ADDENDUM.md` - Logic bugs found
- `TOP_4_BUGS_FIXED.md` - Example fixes

### Tools:
- pytest (test runner)
- pytest-cov (coverage)
- hypothesis (property-based testing for boundaries)
- pytest-timeout (prevent infinite loops)

---

## APPROVAL

This rule is approved and mandatory for all MPX3 live trading code.

**Effective**: 2026-01-29
**Enforced By**: Code review + CI/CD pipeline
**Exception Authority**: Project owner only
**Review Cadence**: Quarterly

---

**Summary**: Any code that runs in LIVE mode must pass boundary + state tests. No exceptions. Tests must cover empty data, null values, edge cases, race conditions, symbol changes, and state cleanup. 80%+ coverage required.
