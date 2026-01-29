# Dual-Track Implementation Test Suite

**Purpose:** Comprehensive test suite for validating dual-track edge pipeline implementation (structural vs tradeable metrics).

**Created:** 2026-01-28

---

## Test Files

### 1. `test_rr_sync.py` - RR Synchronization Tests
**What it tests:**
- RR values are read from `validated_setups` table (NOT hardcoded)
- Each ORB time has correct RR from database
- Fail-closed logic: aborts if RR is None/0/missing
- RR propagation from database to calculations

**Why it matters:**
- Prevents hardcoded RR values (Bug #1)
- Ensures RR comes from validated_setups (single source of truth)
- Catches mismatches between database and code

**Run:**
```bash
python tests/test_rr_sync.py                    # Standalone (no pytest needed)
pytest tests/test_rr_sync.py -v                # With pytest
```

### 2. `test_entry_price.py` - Entry Price Calculation Tests
**What it tests:**
- Entry uses NEXT 1m bar OPEN (not signal CLOSE) - B-entry model
- Entry slippage calculations (entry - ORB edge)
- Entry-anchored risk calculations (not ORB-anchored)
- Entry occurs AFTER ORB completion

**Why it matters:**
- Validates B-entry model (realistic entry prices)
- Ensures entry slippage is properly accounted for
- Catches A-entry model bugs (using CLOSE instead of OPEN)

**Run:**
```bash
pytest tests/test_entry_price.py -v
```

### 3. `test_tradeable_calculations.py` - Tradeable Calculations Tests
**What it tests:**
- Risk = abs(entry - stop) NOT ORB size
- Target = entry +/- RR * risk
- Realized RR formulas from cost_model.py
- Stop placement (full vs half mode)

**Why it matters:**
- Validates entry-anchored calculations (not ORB-anchored)
- Ensures RR is applied correctly to actual risk
- Verifies CANONICAL formulas (CANONICAL_LOGIC.txt)

**Run:**
```bash
pytest tests/test_tradeable_calculations.py -v
```

### 4. `test_cost_model_integration.py` - Cost Model Integration Tests
**What it tests:**
- MGC total friction = $8.40 (commission $2.40 + spread_double $2.00 + slippage $4.00)
- Costs INCREASE risk (added to stop)
- Costs REDUCE reward (subtracted from target)
- Realized RR < theoretical RR (due to costs)

**Why it matters:**
- Validates honest double-spread accounting
- Ensures costs are embedded correctly (not optional)
- Catches cost model calculation errors

**Run:**
```bash
pytest tests/test_cost_model_integration.py -v
```

### 5. `test_outcome_classification.py` - Outcome Classification Tests
**What it tests:**
- Valid outcome values: WIN, LOSS, OPEN, NO_TRADE
- WIN means target hit, LOSS means stop hit
- OPEN means position still active (neither target nor stop hit)
- NO_TRADE means no entry occurred
- Same-bar TP+SL hit = LOSS (conservative logic)

**Why it matters:**
- Validates outcome determination logic
- Ensures conservative same-bar handling
- Catches outcome classification bugs

**Run:**
```bash
pytest tests/test_outcome_classification.py -v
```

---

## Running All Tests

### Option 1: Run All Tests with pytest
```bash
cd tests
pytest -v
```

### Option 2: Run Specific Test File
```bash
pytest tests/test_rr_sync.py -v
pytest tests/test_entry_price.py -v
pytest tests/test_tradeable_calculations.py -v
pytest tests/test_cost_model_integration.py -v
pytest tests/test_outcome_classification.py -v
```

### Option 3: Run by Marker (if markers added)
```bash
pytest -m rr_sync -v                # RR sync tests only
pytest -m entry_price -v            # Entry price tests only
pytest -m cost_model -v             # Cost model tests only
```

### Option 4: Run with Coverage (if pytest-cov installed)
```bash
pytest --cov=pipeline --cov=strategies --cov-report=term-missing
```

---

## Test Output Examples

### Successful Test Run
```
tests/test_rr_sync.py::TestRRSync::test_validated_setups_has_rr_column PASSED
tests/test_rr_sync.py::TestRRSync::test_all_mgc_strategies_have_valid_rr PASSED
tests/test_entry_price.py::TestEntryPrice::test_tradeable_entry_price_column_exists PASSED
tests/test_entry_price.py::TestEntryPrice::test_entry_price_differs_from_orb_edge PASSED
...
========================== 45 passed in 12.34s ==========================
```

### Failed Test (Example)
```
FAILED tests/test_rr_sync.py::TestRRSync::test_all_mgc_strategies_have_valid_rr
AssertionError: Strategy 20 (ORB 1000) has invalid RR=None
```

---

## Prerequisites

### Install pytest (if not already installed)
```bash
pip install pytest
```

### Database Requirements
- `data/db/gold.db` must exist with:
  - `validated_setups` table (with MGC strategies)
  - `daily_features` table (with tradeable columns)
  - Tradeable columns must be populated (run `pipeline/populate_tradeable_metrics.py` first)

### Before Running Tests
1. Ensure dual-track migration is complete:
   ```bash
   python pipeline/migrations/001_add_dual_track_columns.sql
   ```

2. Populate tradeable metrics:
   ```bash
   python pipeline/populate_tradeable_metrics.py
   ```

3. Verify database synchronization:
   ```bash
   python test_app_sync.py
   ```

---

## Test Philosophy

### 1. Test Real Data (Not Mocks)
- All tests use actual `data/db/gold.db` database
- Tests validate against real MGC data
- No mocked database connections

### 2. Positive and Negative Cases
- Each test includes both:
  - Positive: Verify correct behavior
  - Negative: Verify error handling

### 3. Clear Assertion Messages
- Every assertion has descriptive message
- Failures show exactly what went wrong
- Includes date_local for data debugging

### 4. Independent Tests
- Each test can run standalone
- No dependencies between test files
- Tests clean up after themselves

### 5. Regression Prevention
- Tests prevent known bugs from returning
- Covers critical calculation paths
- Validates CANONICAL formulas

---

## Common Issues

### Issue: pytest not found
**Solution:** Install pytest
```bash
pip install pytest
```

### Issue: Database not found
**Solution:** Check database path in test files (should be `data/db/gold.db`)

### Issue: No tradeable data found (tests skipped)
**Solution:** Run populate_tradeable_metrics.py first
```bash
python pipeline/populate_tradeable_metrics.py
```

### Issue: Tests fail with assertion errors
**Solution:** This indicates a real bug! Investigate the failure:
1. Read the assertion message carefully
2. Check the date_local where failure occurred
3. Query database manually to verify expected behavior
4. Fix the code (not the test)

---

## Adding New Tests

### Template for New Test File
```python
"""
Test [Component]: Verify [What It Tests]

PURPOSE:
- [Purpose 1]
- [Purpose 2]

CRITICAL:
- [Critical point 1]
- [Critical point 2]
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pytest
from datetime import date

DB_PATH = "data/db/gold.db"

class Test[Component]:
    """Test suite for [component]"""

    @pytest.fixture
    def db_connection(self):
        """Create database connection"""
        conn = duckdb.connect(DB_PATH)
        yield conn
        conn.close()

    def test_[feature](self, db_connection):
        """Verify [feature description]"""
        # Test implementation
        assert True, "Feature works correctly"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## References

- **CANONICAL_LOGIC.txt** - Canonical formulas (lines 76-98: Realized RR Engine)
- **DUAL_TRACK_RECONCILIATION_REPORT.md** - Implementation status
- **CLAUDE.md** - Project documentation
- **pipeline/cost_model.py** - Cost model implementation
- **pipeline/populate_tradeable_metrics.py** - Tradeable metrics calculation
- **strategies/execution_engine.py** - ORB execution logic

---

## Maintenance

### When to Run Tests
- After ANY changes to:
  - `validated_setups` table
  - `pipeline/cost_model.py`
  - `pipeline/populate_tradeable_metrics.py`
  - `strategies/execution_engine.py`
  - `pipeline/build_daily_features.py`

### When to Update Tests
- After adding new ORB times
- After changing cost model parameters
- After modifying calculation formulas
- After discovering new bugs (add regression test)

### Test Coverage Goals
- 100% coverage of critical calculation paths
- 100% coverage of CANONICAL formulas
- 100% coverage of cost embedding logic
- 100% coverage of outcome classification

---

## Questions?

If tests fail and you're not sure why:
1. Read the assertion message carefully
2. Check the referenced date_local in database
3. Verify expected behavior manually
4. Consult CANONICAL_LOGIC.txt for formulas
5. Check DUAL_TRACK_RECONCILIATION_REPORT.md for known issues

**Remember:** Tests failing is GOOD - they're catching bugs before they reach production!
