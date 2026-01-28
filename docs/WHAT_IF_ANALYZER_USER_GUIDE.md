# What-If Analyzer V1 - User Guide

**Version:** 1.0
**Status:** Production Ready
**Date:** 2026-01-28

---

## Overview

The What-If Analyzer is a deterministic system for testing conditional filter rules against historical trade data. It answers the question:

> "What if I only traded when condition X was true?"

**Key Features:**
- **Deterministic**: Same inputs always produce identical outputs
- **Reproducible**: All analyses can be reloaded and re-evaluated with exact results
- **Integrated**: Snapshots promote directly to validation candidates
- **Live-Ready**: Validated conditions enforce as real-time trading gates

---

## Quick Start

### 1. Run What-If Analysis

```python
from analysis.what_if_engine import WhatIfEngine
import duckdb

conn = duckdb.connect('data/db/gold.db')
engine = WhatIfEngine(conn)

# Analyze setup with conditions
result = engine.analyze_conditions(
    instrument='MGC',
    orb_time='1000',
    direction='BOTH',
    rr=2.0,
    sl_mode='FULL',
    conditions={
        'orb_size_min': 0.5,  # ORB >= 0.5 ATR
        'asia_travel_max': 2.5  # Asia travel < 2.5 ATR
    },
    date_start='2024-01-01',
    date_end='2025-12-31'
)

# Check results
print(f"Baseline: {result['baseline'].expected_r:.3f}R")
print(f"Conditional: {result['conditional'].expected_r:.3f}R")
print(f"Improvement: {result['delta']['expected_r']:+.3f}R")
```

### 2. Save Snapshot (If Improved)

```python
from analysis.what_if_snapshots import SnapshotManager

manager = SnapshotManager(conn)

if result['delta']['expected_r'] >= 0.05:  # Meaningful improvement
    snapshot_id = manager.save_snapshot(
        result=result,
        notes="ORB size filter improves expectancy",
        created_by="analyst@example.com"
    )
    print(f"Saved: {snapshot_id}")
```

### 3. Promote to Validation

```python
edge_id = manager.promote_snapshot_to_candidate(
    snapshot_id=snapshot_id,
    trigger_definition="ORB breakout with size filter",
    notes="Promoted for T6/T7 validation"
)

print(f"Candidate created: {edge_id}")
# Now run validation pipeline on this candidate
```

### 4. Live Gate Enforcement

Once validated and promoted, conditions automatically enforce in live trading:

```python
from trading_app.live_scanner import LiveScanner

scanner = LiveScanner(conn)
active_setups = scanner.scan_current_market('MGC')

for setup in active_setups:
    print(f"{setup['edge_id']}: {setup['status']}")
    print(f"  Reason: {setup['reason']}")
    # Status: ACTIVE | WAITING | INVALID
    # INVALID = condition gate blocked trade
```

---

## Workflow

### Full Lifecycle

```
Discovery → Condition Testing → Snapshot → Promotion → Validation → Production
```

1. **Discovery**: Edge discovery finds profitable pattern
2. **Condition Testing**: What-If Analyzer tests filter rules
3. **Snapshot**: Results saved with full reproducibility
4. **Promotion**: Snapshot becomes validation candidate
5. **Validation**: T6/T7 validation confirms edge quality
6. **Production**: Live scanner enforces conditions pre-trade

### Decision Flow

```
What-If Analysis Result
    |
    ├─ Delta ExpR >= +0.10R → SAVE SNAPSHOT → Promote immediately
    ├─ Delta ExpR >= +0.05R → SAVE SNAPSHOT → Review before promoting
    ├─ Delta ExpR >= +0.01R → NOTE RESULT → Consider with other conditions
    └─ Delta ExpR < +0.01R  → DISCARD → No meaningful improvement
```

---

## V1 Condition Types

### 1. ORB Size Threshold (Normalized by ATR)

**Logic:** `orb_size / atr_20 >= min_threshold`

**Example:**
```python
conditions = {
    'orb_size_min': 0.5,  # ORB must be >= 0.5 ATR
    'orb_size_max': 2.0   # ORB must be <= 2.0 ATR
}
```

**Use Case:** Filter out tiny ranges (traps) or abnormally large ranges (news events)

### 2. Pre-Session Travel Filter (Normalized by ATR)

**Logic:** `pre_orb_travel / atr_20 < max_threshold`

**Example:**
```python
conditions = {
    'asia_travel_max': 2.5,       # Asia travel < 2.5 ATR
    'pre_orb_travel_max': 1.0     # Pre-ORB travel < 1.0 ATR
}
```

**Use Case:** Avoid trading after big overnight/morning moves

### 3. Session Type Filter

**Logic:** `asia_type IN ['QUIET', 'CHOPPY', 'TRENDING']`

**Example:**
```python
conditions = {
    'asia_types': ['QUIET'],          # Only QUIET Asia
    'london_types': ['QUIET', 'CHOPPY']  # QUIET or CHOPPY London
}
```

**Use Case:** Trade only after specific session characteristics

### 4. Range Percentile Filter

**Logic:** `percentile_rank(orb_size, recent_20_days) < threshold`

**Example:**
```python
conditions = {
    'orb_size_percentile_min': 25.0,  # Bottom 25% of recent ranges
    'orb_size_percentile_max': 75.0,  # Top 75% of recent ranges
    'percentile_window_days': 20      # Rolling 20-day window
}
```

**Use Case:** Trade only unusually small/large ORBs relative to recent history

---

## Reproducibility Guarantees

### Deterministic Query Engine

The What-If Engine uses **deterministic caching** with MD5 hash keys:

```
cache_key = MD5(
    instrument + orb_time + direction +
    rr + sl_mode + condition_hash +
    date_start + date_end +
    engine_version
)
```

**Guarantee:** If cache key matches, results are IDENTICAL (down to 0.000000000R precision)

### Snapshot Persistence

All 52 columns stored:
- Setup parameters (instrument, ORB time, direction, RR, SL mode)
- Baseline metrics (12 fields: sample size, win rate, ExpR, stress tests, etc.)
- Conditional metrics (12 fields: same as baseline)
- Non-matched metrics (3 fields: excluded trades)
- Delta metrics (8 fields: improvements)
- Metadata (cache key, conditions, timestamps, version)

**Guarantee:** Load snapshot → Re-evaluate → EXACT match (verified by test suite)

### Version Control

- **Engine version**: `v1` (stamped on all snapshots)
- **Data version**: `date_local` range stored (for schema migrations)
- **Condition schema**: JSON with explicit `None` values (no ambiguity)

**Guarantee:** Old snapshots remain evaluable even after schema changes

---

## UI Integration

### RESEARCH Tab (app_canonical.py)

**Location:** Lines 540-780 in `trading_app/app_canonical.py`

**Features:**
- Setup selector (instrument, ORB, direction, RR, SL mode)
- Condition filter inputs (4 types: ORB size, travel, session, percentile)
- "Run What-If Analysis" button
- Results display (baseline vs conditional with delta highlighting)
- "Save Snapshot" button (only if meaningful improvement)
- Recent snapshots list with "Promote" buttons

**Color Coding:**
- Green text: Improvements (positive delta)
- Red text: Degradations (negative delta)
- Matrix green (#00FF00): Significant improvements (>= +0.10R)

---

## Data Requirements

### Required Tables

1. **daily_features_v2** (or current canonical features table)
   - Columns: `date_local`, `instrument`, `orb_<time>_*`, `atr_20`, `asia_travel`, `pre_orb_travel`
   - Must have completed ORB data with outcomes

2. **what_if_snapshots** (created automatically)
   - Schema: `docs/what_if_snapshots_schema.sql`
   - 52 columns for full reproducibility

3. **edge_registry** (existing table)
   - Used for promoted candidates
   - Status: NEVER_TESTED → T6_PASSED → VALIDATED → PROMOTED

### Data Quality

- **Minimum sample size**: 30 trades recommended
- **Date range**: Must cover full market cycles (avoid single-regime data)
- **Missing data**: ORBs with NULL outcomes are filtered out automatically

---

## Best Practices

### When to Use What-If Analyzer

**Good Use Cases:**
- Testing size filters on discovered edges
- Testing pre-session travel filters
- Testing session type filters
- Combining multiple conditions to refine edges
- Exploring why an edge works (or fails)

**Poor Use Cases:**
- Curve-fitting to noise (use T6/T7 validation to catch this)
- Over-optimization (too many conditions = overfitting)
- Testing conditions with < 30 trades (insufficient sample)

### Workflow Best Practices

1. **Start Simple**: Test one condition at a time
2. **Require Meaningful Improvement**: >= +0.05R minimum delta
3. **Validate Stress Tests**: Conditional must pass +25% AND +50% cost stress
4. **Document Assumptions**: Write clear notes explaining WHY condition should work
5. **Promote Conservatively**: Not every +0.05R improvement needs promotion

### Avoiding Overfitting

**Red Flags:**
- Conditional sample size < 20 trades
- Non-matched trades have BETTER metrics than conditional (you filtered out winners!)
- Stress tests fail (edge too brittle)
- Multiple conditions with tiny individual improvements (likely noise)

**Green Flags:**
- Conditional sample size >= 30 trades
- Delta >= +0.10R (substantial improvement)
- Stress tests pass both +25% AND +50%
- Single condition with clear economic reasoning

---

## API Reference

### WhatIfEngine

**Constructor:**
```python
engine = WhatIfEngine(db_connection: duckdb.DuckDBPyConnection)
```

**Methods:**

```python
analyze_conditions(
    instrument: str,
    orb_time: str,
    direction: str,  # 'UP', 'DOWN', 'BOTH'
    rr: float,
    sl_mode: str,  # 'FULL', 'HALF'
    conditions: Optional[Dict] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]
```

**Returns:**
```python
{
    'baseline': MetricsResult,      # All trades
    'conditional': MetricsResult,   # Condition-matched only
    'non_matched': MetricsResult,   # Condition-excluded
    'delta': {                       # Conditional - Baseline
        'sample_size': int,
        'win_rate_pct': float,
        'expected_r': float,
        ...
    },
    'condition_set': ConditionSet,
    'cache_key': str
}
```

### SnapshotManager

**Constructor:**
```python
manager = SnapshotManager(db_connection: duckdb.DuckDBPyConnection)
```

**Methods:**

```python
save_snapshot(
    result: Dict,
    notes: Optional[str] = None,
    created_by: Optional[str] = None
) -> str  # Returns snapshot_id
```

```python
load_snapshot(snapshot_id: str) -> Dict
```

```python
re_evaluate_snapshot(snapshot_id: str, engine: WhatIfEngine) -> Dict
```

```python
promote_snapshot_to_candidate(
    snapshot_id: str,
    trigger_definition: str,
    notes: Optional[str] = None
) -> str  # Returns edge_id
```

```python
list_snapshots(
    limit: int = 20,
    instrument: Optional[str] = None,
    orb_time: Optional[str] = None,
    promoted_only: bool = False
) -> List[Dict]
```

### LiveScanner

**Constructor:**
```python
scanner = LiveScanner(db_connection: duckdb.DuckDBPyConnection)
```

**Methods:**

```python
scan_current_market(instrument: str = 'MGC') -> List[Dict]
```

Returns list of dicts with:
- `edge_id`: The edge ID
- `status`: 'ACTIVE' | 'WAITING' | 'INVALID'
- `reason`: Why it's active/waiting/invalid
- `orb_size_norm`: Current normalized ORB size
- `passes_filter`: Boolean (includes promoted conditions)

---

## Testing

### End-to-End Tests

Run comprehensive test suite:

```bash
python tests/test_what_if_end_to_end.py
```

**Tests:**
1. Deterministic Evaluation (same inputs = same outputs)
2. Snapshot Roundtrip (save → load → re-eval = exact match)
3. Snapshot Promotion (creates edge in registry)
4. Live Gate Enforcement (conditions block trades)
5. Full Lifecycle (discovery → snapshot → promotion → live gate)

**Expected Output:**
```
Total: 5/5 tests passed
*** ALL TESTS PASSED!
```

---

## Troubleshooting

### Issue: "No trades match conditions"

**Cause:** Conditions too restrictive (filtered out all trades)

**Fix:** Relax conditions or check data availability

### Issue: "Non-deterministic results"

**Cause:** Database changed between runs OR cache disabled

**Fix:** Run with `use_cache=False` to force fresh calculation OR verify database unchanged

### Issue: "Snapshot re-evaluation mismatch"

**Cause:** Database schema changed OR execution engine updated

**Fix:** Check `engine_version` and `data_version` in snapshot metadata

### Issue: "Promoted conditions not enforcing"

**Cause:** LiveScanner not loading conditions from snapshot

**Fix:** Verify `promoted_to_candidate=TRUE` in snapshot AND `candidate_edge_id` linked correctly

---

## Future Enhancements (V2+)

**Planned Features:**
- Multi-condition combinator (AND/OR logic)
- Time-of-day filters (trade only after 10:00 AM)
- Correlation filters (trade only when MPL/MGC aligned)
- Regime filters (volatility, trend strength)
- Machine learning condition discovery
- Backtesting with walk-forward analysis

**Not Planned for V1:**
- Pre-ORB travel percentile (requires percentile calculation at analysis time)
- Intraday momentum filters (requires bar-level data in analysis)
- Multi-instrument conditions (requires cross-table joins)

---

## References

- **What-If Engine Source**: `analysis/what_if_engine.py`
- **Snapshot Manager Source**: `analysis/what_if_snapshots.py`
- **Live Scanner Source**: `trading_app/live_scanner.py`
- **Schema Definition**: `docs/what_if_snapshots_schema.sql`
- **V1 Conditions Spec**: `docs/what_if_analyzer_v1_conditions.md`
- **Progress Report**: `docs/WHAT_IF_ANALYZER_PROGRESS.md`
- **Test Suite**: `tests/test_what_if_end_to_end.py`

---

**Questions?** See `docs/WHAT_IF_ANALYZER_PROGRESS.md` for architecture details and completion status.
