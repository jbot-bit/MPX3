# Reproducibility Fields Added to edge_candidates

**Date**: 2026-01-19
**Status**: COMPLETE
**Migration**: `pipeline/migrate_add_reproducibility_fields.py`

---

## Summary

Added three reproducibility fields to the `edge_candidates` table to ensure all research edge candidates can be reproduced exactly. This is critical for scientific rigor and validating backtesting results.

---

## Fields Added

### 1. `code_version` (VARCHAR)
- Git commit hash or version tag
- Identifies the exact codebase version used for testing
- Example: `"v1.0.0-alpha"`, `"abc123def"`, `"2026-01-19-research"`

### 2. `data_version` (VARCHAR)
- Data snapshot identifier
- Identifies which version of the data was used
- Example: `"2026-01-19"`, `"snapshot-20260119"`, `"backfill-v2"`

### 3. `test_config_json` (JSON)
- Full test configuration
- All parameters needed to reproduce the backtest
- Includes: random seeds, walk-forward windows, slippage, commission, etc.

**Example**:
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

---

## Migration Details

### Migration Script

**File**: `pipeline/migrate_add_reproducibility_fields.py` (220 lines)

**Features**:
- ✅ Safe ALTER TABLE ADD COLUMN (non-destructive)
- ✅ Idempotent (safe to re-run)
- ✅ Checks if columns exist before adding
- ✅ Updates example candidate with sensible defaults
- ✅ Includes verification output

**Run**:
```bash
python pipeline/migrate_add_reproducibility_fields.py
```

---

## Migration Output

```
============================================================
MIGRATION: Add Reproducibility Fields
============================================================
Database: C:\Users\sydne\OneDrive\myprojectx2\data\db\gold.db

[OK] Connected to database
[OK] Added column: code_version
[OK] Added column: data_version
[OK] Added column: test_config_json
[OK] Updated example candidate with reproducibility fields
[OK] Migration completed successfully

Total columns: 17 (expected: 17)

Reproducibility fields:
  [OK] code_version
  [OK] data_version
  [OK] test_config_json
```

---

## Verification

### Check columns exist:
```bash
python -c "import duckdb; \
           con = duckdb.connect('data/db/gold.db'); \
           schema = con.execute('DESCRIBE edge_candidates').fetchall(); \
           print('Total columns:', len(schema)); \
           con.close()"
```
**Expected**: `Total columns: 17`

### Check example candidate:
```bash
python -c "import duckdb; \
           con = duckdb.connect('data/db/gold.db'); \
           result = con.execute('SELECT code_version, data_version FROM edge_candidates WHERE candidate_id=1').fetchone(); \
           print(f'code_version: {result[0]}, data_version: {result[1]}'); \
           con.close()"
```
**Expected**: `code_version: v1.0.0-alpha, data_version: 2026-01-19`

### View test_config_json:
```bash
python -c "import duckdb; import json; \
           con = duckdb.connect('data/db/gold.db'); \
           result = con.execute('SELECT test_config_json FROM edge_candidates WHERE candidate_id=1').fetchone(); \
           print(json.dumps(json.loads(result[0]), indent=2)); \
           con.close()"
```
**Expected**: Full JSON config with random_seed, walk_forward_windows, etc.

---

## Idempotency Test

Running migration again:
```
[SKIP] Column 'code_version' already exists
[SKIP] Column 'data_version' already exists
[SKIP] Column 'test_config_json' already exists
[OK] No changes needed - all fields already exist
```

✅ Safe to re-run multiple times

---

## Updated Schema

```sql
CREATE TABLE edge_candidates (
    -- Primary key
    candidate_id INTEGER PRIMARY KEY,

    -- Metadata
    created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    instrument VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    hypothesis_text TEXT NOT NULL,

    -- Specification (JSON columns)
    feature_spec_json JSON,
    filter_spec_json JSON NOT NULL,

    -- Test window
    test_window_start DATE,
    test_window_end DATE,

    -- Performance (JSON columns)
    metrics_json JSON,
    robustness_json JSON,
    slippage_assumptions_json JSON,

    -- Status tracking
    status VARCHAR NOT NULL DEFAULT 'DRAFT',
    notes TEXT,

    -- Reproducibility (added 2026-01-19)
    code_version VARCHAR,
    data_version VARCHAR,
    test_config_json JSON
)
```

**Total Columns**: 17 (was 14, added 3)

---

## Why This Matters

### Before Reproducibility Fields:
- ❌ No way to reproduce backtest results exactly
- ❌ Unknown which data version was used
- ❌ Unknown which code version was used
- ❌ Parameters might be lost or misremembered
- ❌ Cannot verify results independently

### After Reproducibility Fields:
- ✅ Complete record of test environment
- ✅ Exact data version tracked
- ✅ Exact code version tracked
- ✅ All parameters stored in JSON
- ✅ Results can be verified/reproduced
- ✅ Scientific rigor maintained

---

## Usage Example

When creating a new edge candidate in Phase 2:

```python
import subprocess
import json
from datetime import datetime

# Get current git commit
code_version = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()[:7]

# Set data version (snapshot date)
data_version = datetime.now().strftime('%Y-%m-%d')

# Create test config
test_config = {
    "random_seed": 42,
    "walk_forward_windows": 4,
    "train_pct": 0.7,
    "regime_detection": "volatility_quartiles",
    "slippage_ticks": 1,
    "commission_per_side": 0.62
}

# Insert candidate with reproducibility fields
con.execute("""
    INSERT INTO edge_candidates (
        instrument, name, hypothesis_text,
        filter_spec_json, code_version, data_version, test_config_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
""", [
    'MGC',
    'New Edge Candidate',
    'Hypothesis...',
    json.dumps(filter_spec),
    code_version,
    data_version,
    json.dumps(test_config)
])
```

---

## Files Modified/Created

1. **Created**: `pipeline/migrate_add_reproducibility_fields.py`
   - Safe ALTER TABLE migration
   - 220 lines
   - Idempotent

2. **Updated**: `PHASE1_RESEARCH_MODE.md`
   - Added reproducibility fields documentation
   - Updated schema diagram
   - Updated example row
   - Updated verification commands
   - Updated column count (14 → 17)

3. **Created**: `REPRODUCIBILITY_FIELDS_ADDED.md` (this file)
   - Complete documentation of enhancement
   - Usage examples
   - Verification commands

---

## Database Location

**Path**: `data/db/gold.db`
**Table**: `edge_candidates`
**Total Columns**: 17

---

## Next Steps

These fields will be populated automatically by the Research Runner (Phase 2) when running backtests on edge candidates.

**Phase 2 Integration**:
- Research Runner will auto-populate `code_version` from git
- Research Runner will auto-populate `data_version` from data timestamp
- Research Runner will save complete `test_config_json` before each test

---

## Status: COMPLETE ✅

Reproducibility fields successfully added to edge_candidates table.

**Phase 1 remains COMPLETE** - no Phase 2 work started.

**Ready for Phase 2 when requested.**
