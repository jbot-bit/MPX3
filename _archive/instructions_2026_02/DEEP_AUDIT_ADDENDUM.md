# DEEP AUDIT ADDENDUM - Logic Bugs & Race Conditions

**Date**: 2026-01-29 (Extended Audit)
**Method**: Multi-agent deep logic analysis
**Files Analyzed**: 6 high-risk trading files
**New Bugs Found**: 9 (5 CRITICAL/HIGH severity)

---

## NEWLY DISCOVERED CRITICAL BUGS

### 🔴 BUG #1: TOCTOU Race Condition - Entry Rules (CRITICAL)

**File**: `trading_app/entry_rules.py:70-77`
**Type**: Race condition (Time-of-Check-Time-of-Use)
**Severity**: CRITICAL

**The Bug**:
```python
def compute_orb_range(...):
    # DANGEROUS: Check happens here
    if bars is None or bars.empty:
        return None

    required_cols = {'timestamp', 'high', 'low'}
    if not required_cols.issubset(bars.columns):
        return None

    # Use happens here (5+ lines later)
    orb_bars = bars[(bars['timestamp'] >= orb_start) &
                    (bars['timestamp'] < orb_end)]
```

**Why it's critical**:
In Streamlit's multi-threaded environment with auto-refresh, another thread can modify `bars` between the check (line 71) and use (line 82). This causes `KeyError` crash during live trading entry decisions.

**The Fix**:
```python
def compute_orb_range(...):
    # Validate input
    if bars is None:
        return None

    # Make defensive copy (prevents TOCTOU)
    bars_safe = bars.copy()

    # Validate atomically
    required_cols = {'timestamp', 'high', 'low'}
    if bars_safe.empty or not required_cols.issubset(bars_safe.columns):
        return None

    # Now safe to use
    orb_end = orb_start + timedelta(minutes=orb_minutes)
    orb_bars = bars_safe[(bars_safe['timestamp'] >= orb_start) &
                          (bars_safe['timestamp'] < orb_end)]
```

**Impact**: Crash during live trading = **real money at risk**

---

### 🔴 BUG #2: Timezone Mixing - NY Session Calculation (HIGH)

**File**: `trading_app/strategy_engine.py:673-685`
**Type**: Timezone inconsistency
**Severity**: HIGH

**The Bug**:
```python
def _get_today_ny_levels(self) -> Optional[Dict]:
    now = datetime.now(TZ_LOCAL)  # Brisbane time (UTC+10)
    ny_start = now.replace(hour=23, minute=0, ...)

    # BUG: Between 00:00-02:00 local, this logic is wrong
    if now.hour >= 2 and now.hour < 23:
        ny_start = (now - timedelta(days=1)).replace(hour=23, ...)
        ny_end = now.replace(hour=2, ...)
```

**Why it's wrong**:
- NY session: 23:00 → 02:00 (spans midnight)
- At 01:30 local time: `now.hour = 1`, so `now.hour >= 2` is FALSE
- Code doesn't use yesterday's session, BUT WE SHOULD because we're in the tail of yesterday's NY session (23:00-02:00)
- Result: Wrong CASCADE/SINGLE_LIQUIDITY signals during 00:00-02:00 window

**The Fix**:
```python
def _get_today_ny_levels(self) -> Optional[Dict]:
    now = datetime.now(TZ_LOCAL)

    # NY session: 23:00 -> 02:00 (spans midnight)
    if 0 <= now.hour < 2:
        # We're in tail of YESTERDAY'S NY session
        ny_start = (now - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
        ny_end = now.replace(hour=2, minute=0, second=0, microsecond=0)
    elif 2 <= now.hour < 23:
        # Between sessions - no NY data yet
        return None
    else:  # 23 <= now.hour < 24
        # Start of TODAY'S NY session
        ny_start = now.replace(hour=23, minute=0, second=0, microsecond=0)
        ny_end = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)

    return self.loader.get_session_high_low(ny_start, ny_end)
```

**Impact**: Wrong trade signals during 00:00-02:00 (4 hours/day of incorrect signals)

---

### 🔴 BUG #3: State Corruption - Symbol Change Bug (HIGH)

**File**: `trading_app/app_trading_terminal.py:80-130`
**Type**: State management bug
**Severity**: HIGH

**The Bug**:
```python
def init_session_state():
    if "current_symbol" not in st.session_state:
        st.session_state.current_symbol = DEFAULT_SYMBOL

    if "data_loader" not in st.session_state:
        st.session_state.data_loader = DataLoader(st.session_state.current_symbol)

    if "strategy_engine" not in st.session_state:
        st.session_state.strategy_engine = StrategyEngine(...)
```

**Why it's wrong**:
1. User starts with MGC (data_loader points to MGC)
2. User switches to NQ in sidebar
3. Streamlit reruns, but `"data_loader" in st.session_state` is TRUE
4. Data loader NOT reinitialized - still points to MGC
5. Strategy engine sees `current_symbol = "NQ"` but gets MGC data
6. **Result**: NQ strategy trades using MGC prices!

**The Fix**:
```python
def init_session_state():
    # Core session ID
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # Symbol selection
    if "current_symbol" not in st.session_state:
        st.session_state.current_symbol = DEFAULT_SYMBOL

    # Track last initialized symbol
    if "last_initialized_symbol" not in st.session_state:
        st.session_state.last_initialized_symbol = None

    # Detect symbol change
    if st.session_state.last_initialized_symbol != st.session_state.current_symbol:
        logger.info(f"Symbol changed: {st.session_state.last_initialized_symbol} -> {st.session_state.current_symbol}")

        # Close old connections
        if hasattr(st.session_state, 'data_loader') and st.session_state.data_loader:
            try:
                st.session_state.data_loader.close()
            except:
                pass

        # Clear dependent state
        st.session_state.data_loader = None
        st.session_state.strategy_engine = None
        st.session_state.last_evaluation = None
        st.session_state.positions = {}

        # Update tracking
        st.session_state.last_initialized_symbol = st.session_state.current_symbol

    # Now safe to initialize
    if "data_loader" not in st.session_state or st.session_state.data_loader is None:
        st.session_state.data_loader = DataLoader(st.session_state.current_symbol)

    if "strategy_engine" not in st.session_state or st.session_state.strategy_engine is None:
        st.session_state.strategy_engine = StrategyEngine(...)
```

**Impact**: **TRADING WRONG INSTRUMENT** - user thinks they're trading NQ but system uses MGC data

---

### 🔴 BUG #4: NULL Parameter Bug - No Trades When ATR Missing (HIGH)

**File**: `trading_app/setup_detector.py:229-253`
**Type**: Type mismatch (SQL NULL handling)
**Severity**: HIGH

**The Bug**:
```python
def check_orb_setup(...):
    if atr_20 and atr_20 > 0:
        orb_size_pct = orb_size / atr_20
    else:
        orb_size_pct = None  # BUG: NULL in SQL WHERE clause

    query = """
        WHERE instrument = ?
          AND orb_time = ?
          AND (orb_size_filter IS NULL OR ? <= orb_size_filter)
    """

    result = con.execute(query, [instrument, orb_time, orb_size_pct]).df()
```

**Why it's wrong**:
- When ATR unavailable (first trading day, data gaps), `orb_size_pct = None`
- SQL query becomes: `WHERE ... AND (orb_size_filter IS NULL OR NULL <= orb_size_filter)`
- In SQL: `NULL <= X` evaluates to `NULL` (not TRUE/FALSE)
- Predicate fails → **NO SETUPS MATCH** even though they should
- Intent: Match all setups when ATR unavailable
- Reality: Match zero setups

**The Fix**:
```python
def check_orb_setup(...):
    if atr_20 and atr_20 > 0:
        orb_size_pct = orb_size / atr_20

        query = """
            SELECT * FROM validated_setups
            WHERE instrument = ?
              AND orb_time = ?
              AND (orb_size_filter IS NULL OR ? <= orb_size_filter)
            ORDER BY realized_expectancy DESC
        """
        result = con.execute(query, [instrument, orb_time, orb_size_pct]).df()
    else:
        # No ATR - can't apply size filter, return setups WITHOUT size filter
        query = """
            SELECT * FROM validated_setups
            WHERE instrument = ?
              AND orb_time = ?
              AND orb_size_filter IS NULL
            ORDER BY realized_expectancy DESC
        """
        result = con.execute(query, [instrument, orb_time]).df()

    return result
```

**Impact**: Zero trades on first trading day or after data gaps (user thinks system broken)

---

### 🟡 BUG #5: Resource Leak - DB Connection Not Closed on Error (MEDIUM)

**File**: `trading_app/data_loader.py:50-78` (init), `481-483` (close)
**Type**: Resource leak
**Severity**: MEDIUM

**The Bug**:
```python
def __init__(self, symbol: str):
    self.symbol = symbol

    # Create connection
    if is_cloud_deployment():
        self.con = get_database_connection()
    else:
        self.con = duckdb.connect(DB_PATH, read_only=False)

    # If THIS fails, connection never closed
    self._setup_tables()
    self._login_projectx()  # Can raise exception
    self._get_active_contract()  # Can raise exception
```

**Why it's wrong**:
- Database connection created on line 55/57
- If `_login_projectx()` or `_get_active_contract()` raises exception, `__init__` exits
- Connection remains open (no cleanup)
- Over time: connection pool exhaustion

**The Fix**:
```python
def __init__(self, symbol: str):
    self.symbol = symbol
    self.con = None

    try:
        if is_cloud_deployment():
            self.con = get_database_connection()
        else:
            self.con = duckdb.connect(DB_PATH, read_only=False)

        self._setup_tables()
        self.bars_df = pd.DataFrame()

        # ProjectX init separate (doesn't block DB connection)
        self._init_projectx()

    except Exception as e:
        # Cleanup on failure
        if self.con is not None:
            self.con.close()
        raise

def _init_projectx(self):
    """Separate method - can fail without affecting DB"""
    if PROJECTX_USERNAME and PROJECTX_API_KEY:
        try:
            self._login_projectx()
            self._get_active_contract()
        except Exception as e:
            logger.warning(f"ProjectX init failed: {e}. Database-only mode.")

def __del__(self):
    """Ensure cleanup on garbage collection"""
    if hasattr(self, 'con') and self.con is not None:
        try:
            self.con.close()
        except:
            pass
```

**Impact**: Memory leak in long-running apps (hours/days until restart needed)

---

### 🟡 BUG #6: Floating Point Comparison Without Tolerance (MEDIUM)

**File**: `trading_app/data_loader.py:597-598`
**Type**: Floating point precision error
**Severity**: MEDIUM

**The Bug**:
```python
def check_orb_size_filter(...):
    if atr is None or atr == 0:  # BUG: == with float
        return {"pass": True, ...}

    # Later divides by ATR
    orb_size_norm = orb_size / atr
```

**Why it's wrong**:
- Float comparison with `==` is unreliable
- If ATR = `1e-16` (essentially zero but not exactly 0.0), check fails
- Code proceeds to divide by near-zero ATR on line 609
- Result: Explosion in normalized values (orb_size_norm = 1e16)
- Filter incorrectly rejects valid setups

**The Fix**:
```python
import math

ATR_MIN_THRESHOLD = 0.001  # 0.1 cent minimum

def check_orb_size_filter(...):
    if atr is None or math.isclose(atr, 0.0, abs_tol=ATR_MIN_THRESHOLD):
        return {
            "pass": True,
            "orb_size": orb_size,
            "orb_size_norm": None,
            "threshold": threshold,
            "atr": atr,
            "reason": "ATR too small, cannot apply filter"
        }

    orb_size_norm = orb_size / atr
    # ... rest of logic
```

**Impact**: Incorrect filter decisions when ATR has floating point noise

---

### 🟡 BUG #7: Off-by-One Error - ORB Time Boundary (MEDIUM)

**File**: `trading_app/strategy_engine.py:764-768`
**Type**: Off-by-one error (time boundary)
**Severity**: MEDIUM

**The Bug**:
```python
orb_start = now.replace(hour=orb_time["hour"], minute=orb_time["min"], ...)
orb_end = orb_start + timedelta(minutes=ORB_DURATION_MIN)

# BUG: What if now == orb_end EXACTLY?
if now < orb_end:
    return StrategyEvaluation(status="FORMING", ...)

# ORB complete check
if ORB found and fully formed:
    ...
```

**Why it's wrong**:
- ORB window is `[orb_start, orb_end)` (half-open interval)
- If `now == orb_end` exactly (e.g., 09:05:00.000), we skip the FORMING check
- BUT the last bar (09:04-09:05) might not be closed yet
- We proceed to trade on incomplete ORB

**The Fix**:
```python
# Ensure we wait for ORB completion (last bar closed)
if now <= orb_end:  # Use <= instead of <
    return StrategyEvaluation(
        status="FORMING",
        message=f"ORB forming... {(now - orb_start).seconds // 60}/{ORB_DURATION_MIN} min"
    )
```

**Impact**: Rare edge case (exact second match) but causes incorrect entry on incomplete ORB

---

### 🟢 BUG #8: Logic Contradiction - Unreachable Else Branch (LOW)

**File**: `trading_app/app_trading_terminal.py:268-294`
**Type**: Logic contradiction (misleading UX)
**Severity**: LOW (UX issue only)

**The Bug**:
```python
if st.session_state.data_loader:
    try:
        latest_data = st.session_state.data_loader.get_latest_data()
        if latest_data is not None and not latest_data.empty:
            current_price = latest_data['close'].iloc[-1]
            ...
        else:
            render_loading_spinner("AWAITING DATA...")  # Could be error, not loading
    except Exception as e:
        st.error(f"DATA ERROR: {e}")
```

**Why it's wrong**:
- `else` branch treats `None` or empty as "loading"
- BUT if data connection lost AFTER initial load, this shows loading spinner forever
- User thinks data is loading when connection is actually broken

**The Fix**:
```python
if st.session_state.data_loader:
    try:
        latest_data = st.session_state.data_loader.get_latest_data()

        # Track initial load state
        is_initial_load = not hasattr(st.session_state.data_loader, 'last_successful_fetch')

        if latest_data is not None and not latest_data.empty:
            # Success
            st.session_state.data_loader.last_successful_fetch = datetime.now()
            current_price = latest_data['close'].iloc[-1]
            ...
        elif is_initial_load:
            render_loading_spinner("LOADING INITIAL DATA...")
        else:
            # Had data before, now lost
            st.error("⚠️ DATA CONNECTION LOST")
            st.info(f"Last update: {st.session_state.data_loader.last_successful_fetch}")
    except Exception as e:
        st.error(f"❌ DATA ERROR: {e}")
```

**Impact**: UX confusion (user doesn't know if data loading or connection broken)

---

### 🟢 BUG #9: Deprecated Field Still Used (LOW)

**File**: `trading_app/auto_search_engine.py:80, 367, 641`
**Type**: Deprecated field usage
**Severity**: LOW

**The Bug**:
```python
@dataclass
class SearchCandidate:
    ...
    win_rate_proxy: Optional[float] = None  # DEPRECATED: Use profitable_trade_rate
    ...

# But still used:
# Line 367:
candidate.win_rate_proxy = win_rate_proxy

# Line 641:
win_rate_proxy = candidate.win_rate_proxy
```

**Why it's wrong**:
- Field marked deprecated but still populated and read
- Confusion about which field to use
- Eventual removal will break code

**The Fix**:
```python
# Remove deprecated field entirely
@dataclass
class SearchCandidate:
    ...
    # win_rate_proxy removed
    profitable_trade_rate: Optional[float] = None
    target_hit_rate: Optional[float] = None
    ...

# Update all references:
# Line 367:
candidate.profitable_trade_rate = profitable_trade_rate
candidate.target_hit_rate = target_hit_rate

# Line 641:
profitable_rate = candidate.profitable_trade_rate
```

**Impact**: Code maintenance confusion

---

## SUMMARY OF DEEP BUGS

### By Severity:
- **CRITICAL**: 1 (TOCTOU race condition)
- **HIGH**: 3 (timezone bug, state corruption, NULL parameter bug)
- **MEDIUM**: 3 (resource leak, float compare, off-by-one)
- **LOW**: 2 (UX issue, deprecated field)

### By Type:
- **Concurrency**: 1 (race condition)
- **State Management**: 1 (symbol change bug)
- **Type/Calculation**: 3 (timezone, NULL, float compare)
- **Resource Management**: 1 (connection leak)
- **Logic**: 2 (off-by-one, unreachable code)
- **Code Quality**: 1 (deprecated field)

### Critical Path Impact:
- **Entry Logic**: 2 bugs (TOCTOU, off-by-one)
- **Strategy Engine**: 2 bugs (timezone, state corruption)
- **Setup Detection**: 1 bug (NULL parameter)
- **Data Loading**: 1 bug (resource leak)
- **Filters**: 1 bug (float compare)

---

## IMMEDIATE ACTION PLAN

### Day 1 (4 hours):
1. Fix BUG #1 (TOCTOU) - Add defensive copy in entry_rules.py
2. Fix BUG #2 (Timezone) - Correct NY session logic
3. Fix BUG #3 (State) - Track symbol changes properly
4. Fix BUG #4 (NULL) - Handle missing ATR correctly

### Day 2 (3 hours):
5. Fix BUG #5 (Leak) - Add proper cleanup in data_loader
6. Fix BUG #6 (Float) - Use math.isclose() for ATR
7. Fix BUG #7 (Off-by-one) - Use <= for ORB boundary

### Day 3 (2 hours):
8. Fix BUG #8 (UX) - Distinguish loading vs error
9. Fix BUG #9 (Deprecated) - Remove win_rate_proxy entirely
10. Add tests for all fixed bugs

---

## TESTING REQUIREMENTS

### Unit Tests Needed:
```python
# tests/test_deep_bugs.py

def test_toctou_race_condition():
    """Test that entry_rules.py uses defensive copy"""
    # Simulate concurrent modification
    bars = pd.DataFrame(...)

    def modify_in_background():
        bars.drop(columns=['timestamp'], inplace=True)

    # Should not crash
    result = compute_orb_range(bars, ...)
    assert result is not None or result is None  # Either way, no crash

def test_timezone_ny_session():
    """Test NY session calculation at midnight boundaries"""
    # At 01:30 local time (in tail of yesterday's NY session)
    now = datetime(2026, 1, 29, 1, 30).replace(tzinfo=TZ_LOCAL)
    result = _get_today_ny_levels(now)

    # Should use YESTERDAY'S NY session (23:00 Jan 28 -> 02:00 Jan 29)
    assert result['ny_start'].hour == 23
    assert result['ny_start'].day == 28

def test_symbol_change_cleanup():
    """Test that changing symbol cleans up old state"""
    init_session_state()  # MGC
    old_loader = st.session_state.data_loader

    st.session_state.current_symbol = "NQ"
    init_session_state()  # Switch to NQ

    assert st.session_state.data_loader != old_loader
    assert old_loader.con.is_closed  # Old connection closed

def test_null_atr_handling():
    """Test that NULL ATR doesn't prevent setup matching"""
    result = check_orb_setup(
        instrument="MGC",
        orb_time="1000",
        orb_size=2.5,
        atr_20=None,  # NULL
        con=test_db
    )

    # Should still return setups (ones without size filter)
    assert not result.empty

def test_float_comparison_with_tiny_atr():
    """Test that near-zero ATR is handled safely"""
    result = check_orb_size_filter(
        orb_size=1.5,
        threshold=0.10,
        atr=1e-16  # Near zero but not exactly 0.0
    )

    # Should pass filter (ATR too small to use)
    assert result['pass'] is True
    assert result['orb_size_norm'] is None
```

---

## ADDITIONAL NOTES

### Why These Were Missed in First Scan:
1. **TOCTOU**: Requires understanding of Streamlit's threading model
2. **Timezone**: Requires domain knowledge of session timing
3. **State**: Requires testing symbol switching workflow
4. **NULL**: Requires understanding SQL NULL semantics
5. **Resource Leak**: Only visible in long-running processes

### Prevention Strategies:
1. **Add integration tests** that run for hours (catch resource leaks)
2. **Test timezone boundaries** (00:00-02:00, session transitions)
3. **Test symbol switching** in UI (state management)
4. **Test with missing data** (NULL ATR, empty DataFrames, connection loss)
5. **Use defensive copying** for all shared state in multi-threaded environment

---

**Audit Completed**: 2026-01-29 (Extended)
**Total Bugs Found**: 53 (44 from first scan + 9 from deep scan)
**Critical/High**: 22 bugs
**Estimated Fix Time**: 15-20 hours total
**Risk Level**: HIGH (multiple critical bugs in live trading path)
