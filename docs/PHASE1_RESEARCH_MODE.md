# Phase 1: Research Mode - Edge Candidates Table

**Date**: 2026-01-19
**Status**: COMPLETE
**Goal**: Add database foundation for Research Mode (second lane for edge discovery)

---

## Overview

Phase 1 implements the database schema for storing research edge candidates. This is the foundation for Research Mode - a second lane that can discover and test new edges using ONLY our data, while keeping Trade Mode (AI Source Lock + validated_setups) locked and fail-closed.

**Key Principle**: Research Mode can explore and test, but can NEVER trade unless promoted through hard gates into `validated_setups`.

---

## What Was Implemented

### 1. Migration Script

**File**: `pipeline/migrate_add_edge_candidates.py`

**Features**:
- Creates `edge_candidates` table
- Idempotent (safe to re-run)
- Creates indexes on `status` and `instrument`
- Inserts example candidate for documentation
- Includes verification output

**Run**:
```bash
python pipeline/migrate_add_edge_candidates.py
```

**Output**:
```
============================================================
MIGRATION: Add edge_candidates Table (Phase 1)
============================================================
Database: C:\Users\sydne\OneDrive\myprojectx2\data\db\gold.db
Timestamp: 2026-01-19 19:58:08.916157

[OK] Connected to database
[OK] Created table: edge_candidates
[OK] Created index: idx_edge_candidates_status
[OK] Created index: idx_edge_candidates_instrument
[OK] Inserted example candidate (candidate_id=1)
[OK] Migration completed successfully
```

---

## Table Schema: `edge_candidates`

```sql
CREATE TABLE edge_candidates (
    -- Primary key
    candidate_id INTEGER PRIMARY KEY,

    -- Metadata
    created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    instrument VARCHAR NOT NULL,                    -- MGC, NQ, MPL, etc.
    name VARCHAR NOT NULL,                          -- Human-readable name
    hypothesis_text TEXT NOT NULL,                  -- Why this edge might work

    -- Specification (how the edge is defined)
    feature_spec_json JSON,                         -- Feature definitions, ORB params
    filter_spec_json JSON NOT NULL,                 -- Entry/stop/target rules

    -- Test window
    test_window_start DATE,                         -- Backtest start date
    test_window_end DATE,                           -- Backtest end date

    -- Performance metrics (computed by research runner)
    metrics_json JSON,                              -- Win rate, avg R, total R, n, etc.
    robustness_json JSON,                           -- Walk-forward, regime splits
    slippage_assumptions_json JSON,                 -- Slippage assumptions

    -- Status tracking
    status VARCHAR NOT NULL DEFAULT 'DRAFT',        -- DRAFT, TESTED, APPROVED, REJECTED
    notes TEXT,                                     -- Free-form notes

    -- Reproducibility (added 2026-01-19)
    code_version VARCHAR,                           -- Git commit hash or version tag
    data_version VARCHAR,                           -- Data snapshot identifier (e.g., "2026-01-19")
    test_config_json JSON,                          -- Full test configuration (seeds, params)

    -- Constraints
    CHECK (status IN ('DRAFT', 'TESTED', 'APPROVED', 'REJECTED'))
)
```

**Total Columns**: 17

**Indexes**:
- `idx_edge_candidates_status` on `status`
- `idx_edge_candidates_instrument` on `instrument`

---

## Column Details

### Metadata Columns

| Column | Type | Description |
|--------|------|-------------|
| `candidate_id` | INTEGER PK | Unique identifier |
| `created_at_utc` | TIMESTAMP | Creation timestamp (auto) |
| `instrument` | VARCHAR | Instrument (MGC, NQ, MPL) |
| `name` | VARCHAR | Human-readable name |
| `hypothesis_text` | TEXT | Why this edge might work |

### Specification Columns (JSON)

| Column | Type | Description |
|--------|------|-------------|
| `feature_spec_json` | JSON | Feature definitions, ORB params, indicators |
| `filter_spec_json` | JSON | Entry/stop/target rules, filters, thresholds |

**Example feature_spec_json**:
```json
{
  "orb_time": "1000",
  "orb_duration_minutes": 5,
  "sl_mode": "FULL",
  "atr_lookback": 14,
  "regime_features": ["asia_range", "london_sweep"]
}
```

**Example filter_spec_json**:
```json
{
  "orb_size_filter": 0.03,
  "min_asia_range": 5.0,
  "rr_target": 2.0,
  "entry_type": "breakout_close",
  "stop_type": "opposite_orb_edge"
}
```

### Test Window Columns

| Column | Type | Description |
|--------|------|-------------|
| `test_window_start` | DATE | Backtest start date |
| `test_window_end` | DATE | Backtest end date |

### Performance Columns (JSON)

| Column | Type | Description |
|--------|------|-------------|
| `metrics_json` | JSON | Win rate, avg R, total R, n, drawdown, MAE/MFE |
| `robustness_json` | JSON | Walk-forward results, regime split results |
| `slippage_assumptions_json` | JSON | Slippage/commission assumptions |

**Example metrics_json**:
```json
{
  "win_rate": 0.561,
  "avg_r": 0.403,
  "total_r": 104.78,
  "n_trades": 260,
  "max_drawdown_r": -15.3,
  "mae_avg": -0.25,
  "mfe_avg": 1.15
}
```

**Example robustness_json**:
```json
{
  "walk_forward_periods": 4,
  "walk_forward_avg_r": 0.385,
  "regime_split_results": {
    "high_vol": {"avg_r": 0.45, "n": 120},
    "low_vol": {"avg_r": 0.35, "n": 140}
  }
}
```

### Status Tracking

| Column | Type | Description |
|--------|------|-------------|
| `status` | VARCHAR | DRAFT, TESTED, APPROVED, REJECTED |
| `notes` | TEXT | Free-form notes, rejection reasons |

**Status Flow**:
1. **DRAFT** - Initial proposal, not yet tested
2. **TESTED** - Backtests run, metrics computed
3. **APPROVED** - Passed promotion gate, added to validated_setups
4. **REJECTED** - Failed promotion gate or manually rejected

### Reproducibility Fields (Added 2026-01-19)

| Column | Type | Description |
|--------|------|-------------|
| `code_version` | VARCHAR | Git commit hash or version tag when tested |
| `data_version` | VARCHAR | Data snapshot identifier (e.g., "2026-01-19") |
| `test_config_json` | JSON | Full test configuration |

**Purpose**: Ensure edge candidates can be reproduced exactly. Critical for scientific rigor and validating results.

**Example test_config_json**:
```json
{
  "random_seed": 42,
  "walk_forward_windows": 4,
  "train_pct": 0.7,
  "regime_detection": "volatility_quartiles",
  "slippage_ticks": 1,
  "commission_per_side": 0.62
}
```

**Migration**: Added via `migrate_add_reproducibility_fields.py` (safe ALTER TABLE)

---

## Verification

### Quick Verification

```bash
# Run migration
python pipeline/migrate_add_edge_candidates.py

# Verify table exists and has example row
python -c "import duckdb; \
           con = duckdb.connect('data/db/gold.db', read_only=True); \
           result = con.execute('SELECT candidate_id, instrument, name, status FROM edge_candidates').fetchall(); \
           print('Edge Candidates:', result); \
           con.close()"
```

**Expected Output**:
```
Edge Candidates: [(1, 'MGC', 'EXAMPLE: 1000 ORB Ultra-Tight Filter', 'DRAFT')]
```

### Query Examples

**List all candidates**:
```sql
SELECT candidate_id, instrument, name, status, created_at_utc
FROM edge_candidates
ORDER BY created_at_utc DESC;
```

**Filter by status**:
```sql
SELECT candidate_id, name, instrument
FROM edge_candidates
WHERE status = 'TESTED'
ORDER BY instrument;
```

**Get candidate with metrics**:
```sql
SELECT
    candidate_id,
    name,
    metrics_json,
    robustness_json
FROM edge_candidates
WHERE candidate_id = 1;
```

---

## Where the Table Lives

**Database Path**: `data/db/gold.db`
**Table Name**: `edge_candidates`

**Same database as**:
- `validated_setups` (Trade Mode - fail-closed)
- `bars_1m`, `bars_5m` (candle data)
- `daily_features` (ORB data)

---

## Migration Idempotency

The migration script is **idempotent** - safe to re-run multiple times:

```bash
# First run: creates table
python pipeline/migrate_add_edge_candidates.py
# Output: [OK] Created table: edge_candidates

# Second run: skips creation
python pipeline/migrate_add_edge_candidates.py
# Output: [WARN] Table 'edge_candidates' already exists. Skipping creation.
```

---

## Example Row

The migration inserts an example candidate for documentation:

```python
{
    "candidate_id": 1,
    "instrument": "MGC",
    "name": "EXAMPLE: 1000 ORB Ultra-Tight Filter",
    "hypothesis_text": "Hypothesis: 1000 ORB works better with tighter filter (<0.03×ATR) during high volatility regimes",
    "feature_spec_json": {
        "orb_time": "1000",
        "orb_duration_minutes": 5,
        "sl_mode": "FULL",
        "atr_lookback": 14,
        "regime_features": ["asia_range", "london_sweep"]
    },
    "filter_spec_json": {
        "orb_size_filter": 0.03,
        "min_asia_range": 5.0,
        "rr_target": 2.0,
        "entry_type": "breakout_close",
        "stop_type": "opposite_orb_edge"
    },
    "test_window_start": "2024-01-01",
    "test_window_end": "2025-12-31",
    "status": "DRAFT",
    "notes": "Example candidate for documentation. Metrics not yet computed.",
    "code_version": "v1.0.0-alpha",
    "data_version": "2026-01-19",
    "test_config_json": {
        "random_seed": 42,
        "walk_forward_windows": 4,
        "train_pct": 0.7,
        "regime_detection": "volatility_quartiles",
        "slippage_ticks": 1,
        "commission_per_side": 0.62
    }
}
```

---

## Next Steps (Phase 2+)

Phase 1 is **COMPLETE**. Next phases:

- **Phase 2**: Research Runner (backtest script, metrics computation)
- **Phase 3**: Promotion Gate (hard rules to move to validated_setups)
- **Phase 4**: Research AI (LLM-assisted edge discovery)
- **Phase 5**: Tests (verify separation between Trade/Research modes)

---

## Critical Guarantees

✅ **Trade Mode UNCHANGED**: AI Source Lock (validated_setups) remains fail-closed
✅ **Research Mode ISOLATED**: edge_candidates table is separate
✅ **No Auto-Trading**: Research candidates CANNOT be traded until promoted
✅ **Data-Only**: Research Mode will use ONLY our database (same as Trade Mode)
✅ **Hard Gate**: Promotion to validated_setups requires passing objective thresholds

---

## Files Created

1. `pipeline/migrate_add_edge_candidates.py` - Initial table creation (270 lines)
2. `pipeline/migrate_add_reproducibility_fields.py` - Add reproducibility fields (220 lines)
3. `PHASE1_RESEARCH_MODE.md` - This documentation

---

## Verification Commands

```bash
# 1. Check table exists
python -c "import duckdb; con = duckdb.connect('data/db/gold.db'); \
           tables = con.execute('SHOW TABLES').fetchall(); \
           print('edge_candidates' in [t[0] for t in tables]); \
           con.close()"
# Expected: True

# 2. Count candidates
python -c "import duckdb; con = duckdb.connect('data/db/gold.db'); \
           count = con.execute('SELECT COUNT(*) FROM edge_candidates').fetchone()[0]; \
           print(f'Total candidates: {count}'); \
           con.close()"
# Expected: Total candidates: 1

# 3. View schema
python -c "import duckdb; con = duckdb.connect('data/db/gold.db'); \
           schema = con.execute('DESCRIBE edge_candidates').fetchall(); \
           [print(f'{s[0]:30s} {s[1]:20s}') for s in schema]; \
           con.close()"
# Expected: 17 columns listed

# 4. Verify reproducibility fields
python -c "import duckdb; con = duckdb.connect('data/db/gold.db'); \
           result = con.execute('SELECT code_version, data_version FROM edge_candidates WHERE candidate_id=1').fetchone(); \
           print(f'code_version: {result[0]}, data_version: {result[1]}'); \
           con.close()"
# Expected: code_version: v1.0.0-alpha, data_version: 2026-01-19
```

---

**PHASE 1 STATUS: COMPLETE ✅**

**Includes reproducibility fields (code_version, data_version, test_config_json) added 2026-01-19**

**Ready for Phase 2 when you say "next".**
