# UPDATE14 IMPLEMENTATION PLAN

**Date**: 2026-01-29
**Goal**: Create unified "Execution Spec" architecture for all calculations
**Status**: ⏳ PLANNING

---

## OVERVIEW

**Problem**: Multiple calculation paths use different assumptions:
- `daily_features` has TWO column sets (tradeable vs non-tradeable)
- Entry rules are implicit (limit order vs 1st close vs 5m close)
- No single source of truth for "how was this computed?"
- Can't reproduce results without guessing parameters

**Solution**: Single "Execution Spec" object consumed by ALL paths.

---

## STEP 1: Execution Spec Object

### Design:

```python
@dataclass
class ExecutionSpec:
    """Single source of truth for how trades are computed"""

    # Data inputs
    bar_tf: Literal["1m", "5m"]  # Base timeframe
    data_source: str = "bars_1m"  # Table name

    # ORB definition
    orb_minutes: int = 5  # ORB duration (5, 15, etc.)
    orb_time: str  # "0900", "1000", etc.

    # Entry rule
    entry_rule: Literal["limit_at_orb", "1st_close_outside", "2nd_close_outside", "5m_close_outside"]
    confirm_tf: Literal["1m", "5m"]  # For "5m close outside"

    # Risk/Reward
    rr_target: float  # 1.0, 1.5, 2.0, etc.
    sl_mode: Literal["orb_opposite", "atr", "fixed"]

    # Costs
    cost_model: str = "mgc_tradovate"  # References cost_model.py

    # Time
    session_tz: str = "Australia/Brisbane"

    def __post_init__(self):
        """Validate spec on creation"""
        # Validate entry_rule + confirm_tf compatibility
        if self.entry_rule == "5m_close_outside" and self.confirm_tf != "5m":
            raise ValueError("5m_close_outside requires confirm_tf=5m")

        # Validate orb_time format
        if not re.match(r'^\d{4}$', self.orb_time):
            raise ValueError(f"orb_time must be 4 digits, got: {self.orb_time}")

    def to_dict(self) -> dict:
        """Serialize for storage"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ExecutionSpec':
        """Deserialize from storage"""
        return cls(**data)

    def spec_hash(self) -> str:
        """Unique identifier for this spec"""
        import hashlib
        spec_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(spec_str.encode()).hexdigest()[:12]
```

### Storage Decision:

**Option A**: Store in DB (execution_specs table)
- ✅ Reproducible (can reconstruct exact run)
- ✅ Searchable (find all runs with spec X)
- ❌ Schema complexity (new table + migrations)

**Option B**: Store in code only (config.py constants)
- ✅ Simple (no DB changes)
- ✅ Version controlled (git history)
- ❌ Not reproducible (can't reconstruct old runs)

**DECISION**: Start with Option B (code only), migrate to Option A if needed.

**Location**: Create `trading_app/execution_spec.py`

---

## STEP 2: Required Inputs Contract

### Design:

```python
@dataclass
class ExecutionContract:
    """Defines requirements and invariants for an execution spec"""

    required_columns: List[str]  # DB columns needed
    required_tables: List[str]  # Tables needed
    required_spec_fields: List[str]  # Spec fields that must be set
    allowed_combinations: Dict[str, List[Any]]  # Valid values per field
    invariants: List[Callable[[ExecutionSpec, pd.DataFrame], bool]]  # Must be true

    def validate(self, spec: ExecutionSpec, data: pd.DataFrame) -> ContractResult:
        """Check if spec + data satisfy contract"""
        errors = []
        warnings = []

        # Check required fields
        for field in self.required_spec_fields:
            if not hasattr(spec, field) or getattr(spec, field) is None:
                errors.append(f"Missing required field: {field}")

        # Check allowed combinations
        for field, allowed_values in self.allowed_combinations.items():
            value = getattr(spec, field)
            if value not in allowed_values:
                errors.append(f"{field}={value} not in allowed: {allowed_values}")

        # Check columns exist
        for col in self.required_columns:
            if col not in data.columns:
                errors.append(f"Missing required column: {col}")

        # Check invariants
        for invariant_func in self.invariants:
            try:
                if not invariant_func(spec, data):
                    warnings.append(f"Invariant failed: {invariant_func.__name__}")
            except Exception as e:
                errors.append(f"Invariant error: {invariant_func.__name__}: {e}")

        return ContractResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

@dataclass
class ContractResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
```

### Example Contract (5m_close_outside):

```python
def contract_5m_close_outside() -> ExecutionContract:
    """Contract for 5m close outside entry rule"""

    def check_orb_window_complete(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """ORB window has exactly orb_minutes bars"""
        orb_bars = data[data['is_orb_window']]
        expected = spec.orb_minutes
        return len(orb_bars) == expected

    def check_entry_after_orb(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """Entry timestamp > ORB end timestamp"""
        entry_ts = data['entry_timestamp'].iloc[0]
        orb_end = data['orb_end_timestamp'].iloc[0]
        return entry_ts > orb_end

    def check_no_lookahead(spec: ExecutionSpec, data: pd.DataFrame) -> bool:
        """Entry uses only bars after confirmation close"""
        entry_ts = data['entry_timestamp'].iloc[0]
        confirm_ts = data['confirm_timestamp'].iloc[0]
        return entry_ts >= confirm_ts

    return ExecutionContract(
        required_columns=['timestamp', 'open', 'high', 'low', 'close'],
        required_tables=['bars_1m'],
        required_spec_fields=['orb_time', 'orb_minutes', 'confirm_tf', 'rr_target'],
        allowed_combinations={
            'confirm_tf': ['5m'],
            'entry_rule': ['5m_close_outside']
        },
        invariants=[
            check_orb_window_complete,
            check_entry_after_orb,
            check_no_lookahead
        ]
    )
```

### Fail Mode Decision:

**Option A**: Hard fail (stop run, force fix)
- ✅ Safe (no bad data)
- ❌ Annoying (blocks exploration)

**Option B**: Soft fail (warn + skip variant)
- ✅ Flexible (auto-skip invalid)
- ❌ Silent failures (may miss issues)

**DECISION**: Hybrid approach:
- **Errors** (missing data, incompatible config) → Hard fail
- **Warnings** (invariant violations, suspicious values) → Soft fail + log

**Location**: Add to `trading_app/execution_spec.py`

---

## STEP 3: Define "5m close outside" Unambiguously

### Current Ambiguity:

- Is ORB built from 5m bars or aggregated 1m bars?
- Is confirmation based on 5m close or 1m closes?
- What happens if 5m bars don't align with ORB window?

### Definition (MUST PICK ONE):

**Option A**: Native 5m bars only
- ORB: First 5 minutes = 1 bar from bars_5m
- Confirmation: Full 5m bar closes outside ORB
- Entry: Next bar after confirmation close

**Option B**: Aggregate 1m → 5m
- ORB: Aggregate 5x 1m bars (09:00-09:04)
- Confirmation: Aggregate 5x 1m bars closes outside ORB
- Entry: Next 1m bar after 5m confirmation close

**Option C**: Hybrid (5m confirmation, 1m entry)
- ORB: From 1m bars (09:00:00-09:04:59)
- Confirmation: Aggregate to 5m, check if close outside
- Entry: Next 1m bar after 5m boundary

**DECISION**: Option C (hybrid)
- Most flexible (works with bars_1m only)
- Best granularity (1m entry after 5m confirmation)
- Matches current `tradeable_*` columns behavior

### Implementation:

```python
def compute_5m_close_outside(
    spec: ExecutionSpec,
    data: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute 5m close outside entry with hybrid approach.

    ORB: Built from 1m bars in ORB window
    Confirmation: Aggregate 1m → 5m, check close outside ORB
    Entry: First 1m bar after 5m confirmation close

    Args:
        spec: ExecutionSpec with entry_rule='5m_close_outside'
        data: bars_1m with timestamp, open, high, low, close

    Returns:
        DataFrame with entry_timestamp, entry_price, direction
    """
    # Step 1: Build ORB from 1m bars
    orb_start = parse_orb_time(spec.orb_time, spec.session_tz)
    orb_end = orb_start + timedelta(minutes=spec.orb_minutes)

    orb_bars = data[(data['timestamp'] >= orb_start) & (data['timestamp'] < orb_end)]
    orb_high = orb_bars['high'].max()
    orb_low = orb_bars['low'].min()

    # Step 2: Aggregate post-ORB bars to 5m
    post_orb = data[data['timestamp'] >= orb_end]
    post_orb_5m = aggregate_1m_to_5m(post_orb, align='floor')

    # Step 3: Find first 5m close outside ORB
    for idx, bar_5m in post_orb_5m.iterrows():
        if bar_5m['close'] > orb_high:
            # Long confirmation
            confirm_ts = bar_5m['timestamp_end']
            direction = 'LONG'
            break
        elif bar_5m['close'] < orb_low:
            # Short confirmation
            confirm_ts = bar_5m['timestamp_end']
            direction = 'SHORT'
            break
    else:
        # No confirmation
        return None

    # Step 4: Entry = first 1m bar after confirmation
    entry_bars = data[data['timestamp'] >= confirm_ts]
    if len(entry_bars) == 0:
        return None

    entry_bar = entry_bars.iloc[0]
    entry_timestamp = entry_bar['timestamp']
    entry_price = entry_bar['open']  # Enter at open of next bar

    return {
        'entry_timestamp': entry_timestamp,
        'entry_price': entry_price,
        'direction': direction,
        'orb_high': orb_high,
        'orb_low': orb_low,
        'confirm_timestamp': confirm_ts
    }
```

**Location**: Create `trading_app/entry_rules.py`

### Decision on ORB timeframe:

**Question**: Do you want 5m ORB + 5m confirmation, or 1m ORB + 5m confirmation?

**ANSWER (from current code)**: 1m ORB + 5m confirmation (hybrid)
- ORB always 1m granularity (09:00:00-09:04:59)
- Confirmation can be any timeframe (1m or 5m)
- Most flexible, matches current implementation

---

## STEP 4: Self-Defining Panel in UI

### Design:

Add expander after Quick Search results:

```python
with st.expander("⚙️ Execution Spec Used"):
    st.markdown(f"""
**Spec ID**: `{spec.spec_hash()}`

**Data Inputs**:
- Bar timeframe: {spec.bar_tf}
- Data source: {spec.data_source}

**ORB Definition**:
- ORB time: {spec.orb_time}
- ORB duration: {spec.orb_minutes} minutes
- Window: {orb_start_ts} to {orb_end_ts}

**Entry Rule**: {spec.entry_rule}
- Confirmation timeframe: {spec.confirm_tf}
- Entry timestamp: {entry_ts}

**Risk/Reward**:
- RR target: {spec.rr_target}
- SL mode: {spec.sl_mode}

**Costs**: {spec.cost_model} (${friction:.2f} RT)

**Contract Status**:
{contract_status_display}
    """)
```

### Contract Status Display:

```python
def display_contract_status(result: ContractResult):
    """Show contract validation results"""

    if result.valid and len(result.warnings) == 0:
        st.success("✅ All requirements met")
    elif result.valid and len(result.warnings) > 0:
        st.warning(f"⚠️ {len(result.warnings)} warnings")
        for warning in result.warnings:
            st.caption(f"  - {warning}")
    else:
        st.error(f"❌ {len(result.errors)} conflicts (run blocked)")
        for error in result.errors:
            st.caption(f"  - {error}")
```

### Auto-Skip Decision:

**Option A**: Auto-skip invalid variants
- Continue running, log skipped
- ✅ User-friendly (doesn't break flow)
- ❌ May hide configuration errors

**Option B**: Block run, force fix
- Stop immediately on error
- ✅ Forces correct configuration
- ❌ Annoying during exploration

**DECISION**: Hybrid:
- **Critical errors** (missing data, incompatible config) → Block
- **Minor warnings** (invariant violations) → Auto-skip + log

**Location**: Add to `trading_app/app_canonical.py` Quick Search section

---

## STEP 5: Golden Tests + Invariants

### Test Suite Structure:

```
tests/
  test_execution_spec.py     # Spec creation, validation, serialization
  test_entry_rules.py         # Entry rule logic (limit, 1st close, 5m close)
  test_contracts.py           # Contract validation
  test_golden_cases.py        # Known days, exact values
  test_invariants.py          # Universal truth checks
```

### Golden Case Example:

```python
def test_1000_orb_2024_01_15():
    """Golden case: 2024-01-15, 1000 ORB, known outcome"""

    spec = ExecutionSpec(
        bar_tf="1m",
        orb_time="1000",
        orb_minutes=5,
        entry_rule="1st_close_outside",
        confirm_tf="1m",
        rr_target=1.0,
        sl_mode="orb_opposite",
        cost_model="mgc_tradovate"
    )

    # Load data for this day
    data = load_bars_1m("2024-01-15")

    # Compute entry
    result = compute_entry(spec, data)

    # Assert exact values (from manual verification)
    assert result['orb_high'] == 2034.5
    assert result['orb_low'] == 2032.1
    assert result['entry_timestamp'] == pd.Timestamp("2024-01-15 10:06:00", tz="Australia/Brisbane")
    assert result['entry_price'] == 2034.6
    assert result['direction'] == 'LONG'
```

### Invariant Tests:

```python
def test_no_lookahead(spec, data):
    """Entry never uses bars from the future"""
    result = compute_entry(spec, data)

    # Entry bar must be after confirmation
    assert result['entry_timestamp'] >= result['confirm_timestamp']

    # Entry bar must be after ORB end
    assert result['entry_timestamp'] >= result['orb_end_timestamp']

def test_orb_window_complete(spec, data):
    """ORB window has exact number of expected bars"""
    orb_bars = get_orb_bars(spec, data)
    expected_bars = spec.orb_minutes  # For 1m bars
    assert len(orb_bars) == expected_bars

def test_structural_before_tradeable(spec, data):
    """Structural entry (limit) <= tradeable entry (1st close) for longs"""
    spec_limit = spec.copy()
    spec_limit.entry_rule = "limit_at_orb"
    result_limit = compute_entry(spec_limit, data)

    spec_tradeable = spec.copy()
    spec_tradeable.entry_rule = "1st_close_outside"
    result_tradeable = compute_entry(spec_tradeable, data)

    if result_limit['direction'] == 'LONG' and result_tradeable['direction'] == 'LONG':
        # Limit entry should be at or before 1st close entry
        assert result_limit['entry_timestamp'] <= result_tradeable['entry_timestamp']
```

### CI Decision:

**Option A**: pytest + GitHub Actions CI
- ✅ Industry standard
- ✅ Auto-run on commit
- ❌ Setup complexity

**Option B**: scripts/check/ style
- ✅ Simple (just Python files)
- ✅ Run manually
- ❌ No auto-enforcement

**DECISION**: Start with Option B (scripts/check/), migrate to Option A later.

**Location**: Create `scripts/check/check_execution_spec.py`

---

## IMPLEMENTATION SEQUENCE

### Phase 1: Core Infrastructure (60 min)
1. Create `trading_app/execution_spec.py` (ExecutionSpec class)
2. Create `trading_app/execution_contract.py` (ExecutionContract class)
3. Create `trading_app/entry_rules.py` (entry rule implementations)
4. Unit tests: `scripts/check/check_execution_spec.py`

### Phase 2: Integration with Quick Search (45 min)
5. Update `auto_search_engine.py` to use ExecutionSpec
6. Add "Execution Spec Used" expander to UI
7. Display contract status in results

### Phase 3: Golden Tests (30 min)
8. Create golden test cases (3-5 known days)
9. Add invariant checks
10. Document in UPDATE14_COMPLETE.md

---

## OPEN QUESTIONS (NEED ANSWERS)

### Q1: Store specs in DB or code?
**DECISION**: Code only (for now)

### Q2: Hard fail or soft fail on contract violations?
**DECISION**: Hybrid (errors block, warnings skip)

### Q3: 5m ORB + 5m confirmation, or 1m ORB + 5m confirmation?
**DECISION**: 1m ORB + 5m confirmation (hybrid)

### Q4: Auto-skip invalid variants or block run?
**DECISION**: Hybrid (critical errors block, warnings skip)

### Q5: pytest CI or scripts/check/?
**DECISION**: scripts/check/ (for now)

---

## FILES TO CREATE

1. `trading_app/execution_spec.py` (ExecutionSpec dataclass)
2. `trading_app/execution_contract.py` (ExecutionContract, validation)
3. `trading_app/entry_rules.py` (compute_entry functions)
4. `scripts/check/check_execution_spec.py` (test suite)
5. `UPDATE14_COMPLETE.md` (documentation)

## FILES TO MODIFY

1. `trading_app/auto_search_engine.py` (integrate ExecutionSpec)
2. `trading_app/app_canonical.py` (add Execution Spec expander)

---

**Next**: Start Phase 1 (create core infrastructure)
