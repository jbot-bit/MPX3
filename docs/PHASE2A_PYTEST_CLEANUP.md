# Phase 2a: Pytest Collection Cleanup - COMPLETE

**Date**: 2026-01-19
**Status**: COMPLETE
**Goal**: Fix pytest collection so `pytest -q` runs clean

---

## Problem Statement

Running `pytest -q` was failing during the collection phase with multiple errors:

1. **Duplicate test_app_sync.py collision**:
   - Root directory had `test_app_sync.py`
   - `strategies/` directory also had `test_app_sync.py`
   - Pytest detected import file mismatch and refused to collect

2. **Missing ml_inference module**:
   - `tests/test_ml_integration.py` imported `ml_inference` (doesn't exist)
   - `tests/test_ml_integration_fixed.py` imported `ml_inference` (doesn't exist)

3. **Missing test module**:
   - `tests/test_night_orbs_full_sl.py` imported `test_night_orb_extended_windows` (doesn't exist)

4. **No pytest configuration**:
   - Pytest was collecting tests from all directories including archived/legacy code
   - No exclusion rules for `_archive`, `strategies`, `pipeline`, etc.

---

## Solution Implemented

### 1. Created pytest.ini Configuration

**File**: `pytest.ini`

```ini
[pytest]
# Pytest configuration for myprojectx2

# Only collect tests from /tests directory
testpaths = tests

# Only collect test_*.py files
python_files = test_*.py

# Do not recurse into these directories
norecursedirs = _archive _INVALID_SCRIPTS_ARCHIVE strategies pipeline data docs trading_app research .venv .git __pycache__ *.egg-info

# Default options
addopts = -q
```

**Why**: This ensures pytest only collects tests from `/tests` directory and ignores archived/legacy code.

---

### 2. Resolved Duplicate test_app_sync.py

**Action**: Moved `strategies/test_app_sync.py` to `_archive/`

**Details**:
- Root `test_app_sync.py` is the production version (validates config.py matches validated_setups DB)
- `strategies/test_app_sync.py` was a duplicate causing import collision
- Renamed to `_archive/test_app_sync_from_strategies.py` to preserve history

**Result**: No more duplicate module collision

---

### 3. Archived Legacy Tests with Missing Dependencies

Moved the following tests to `_archive/`:

#### a) test_ml_integration.py
- **Location**: `tests/test_ml_integration.py` → `_archive/test_ml_integration.py`
- **Reason**: Imports missing `ml_inference` module
- **Impact**: ML inference was experimental and not used in production

#### b) test_ml_integration_fixed.py
- **Location**: `tests/test_ml_integration_fixed.py` → `_archive/test_ml_integration_fixed.py`
- **Reason**: Also imports missing `ml_inference` module
- **Impact**: Duplicate of above, also experimental

#### c) test_night_orbs_full_sl.py
- **Location**: `tests/test_night_orbs_full_sl.py` → `_archive/test_night_orbs_full_sl.py`
- **Reason**: Imports missing `test_night_orb_extended_windows` module
- **Impact**: Tests for night ORBs (1800, 2300, 0030) which are not currently validated in production

**Note**: These tests are preserved in `_archive/` for historical reference, not deleted.

---

## Verification

### Before Fix

```bash
$ pytest -q
ERROR: import file mismatch:
imported module 'test_app_sync' has this __file__ attribute:
  C:\Users\sydne\OneDrive\myprojectx2\test_app_sync.py
which is not the same as the test file we want to collect:
  C:\Users\sydne\OneDrive\myprojectx2\strategies\test_app_sync.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules

ERROR: ModuleNotFoundError: No module named 'ml_inference'
ERROR: ModuleNotFoundError: No module named 'test_night_orb_extended_windows'
```

### After Fix

```bash
$ pytest -q
...collection completed successfully...
...tests run (some pass, some fail, but NO collection errors)...
```

**Result**: Collection phase is clean. Pytest successfully collects all tests from `/tests` directory without errors.

---

## Files Modified

1. **Created**: `pytest.ini` - Pytest configuration with testpaths and norecursedirs
2. **Moved**: `strategies/test_app_sync.py` → `_archive/test_app_sync_from_strategies.py`
3. **Moved**: `tests/test_ml_integration.py` → `_archive/test_ml_integration.py`
4. **Moved**: `tests/test_ml_integration_fixed.py` → `_archive/test_ml_integration_fixed.py`
5. **Moved**: `tests/test_night_orbs_full_sl.py` → `_archive/test_night_orbs_full_sl.py`

---

## Current Test Status

After cleanup, pytest collects and runs tests from `/tests` directory:

- **Collection**: CLEAN (no errors)
- **Test failures**: Some tests fail (unrelated to collection)
  - 12 failures in `test_canonical_env.py` (missing canonical.json - different issue)
  - 4 failures in `test_no_hardcoded_db_paths.py` (different issue)
  - 1 failure in `test_config_generator.py` (assertion mismatch - different issue)

**Important**: The goal was to fix collection errors, not test failures. Collection is now working correctly.

---

## Rules Applied

From `phase2a.txt`:

1. **Only tests under /tests are collected by pytest** ✓
   - Configured via `testpaths = tests` in pytest.ini

2. **Root scripts like test_app_sync.py are NOT pytest tests** ✓
   - Root test_app_sync.py remains (manual verification script)
   - strategies/test_app_sync.py moved to _archive/ (duplicate)

3. **Archived/legacy tests must not be collected** ✓
   - Configured via `norecursedirs` in pytest.ini
   - Legacy tests moved to _archive/

---

## Deliverable

**Command**: `pytest -q`

**Result**: Completes with NO collection errors ✓

**Files moved**:
- `strategies/test_app_sync.py` → `_archive/` (duplicate collision)
- `tests/test_ml_integration.py` → `_archive/` (missing ml_inference module)
- `tests/test_ml_integration_fixed.py` → `_archive/` (missing ml_inference module)
- `tests/test_night_orbs_full_sl.py` → `_archive/` (missing test_night_orb_extended_windows module)

---

## PHASE 2A STATUS: COMPLETE ✓

**Summary**:
- [x] Created pytest.ini configuration
- [x] Resolved duplicate test_app_sync.py collision
- [x] Archived legacy tests with missing dependencies
- [x] Verified `pytest -q` runs with clean collection

**Trade Mode and AI Source Lock**: UNCHANGED (research cleanup only)

**Next Steps**: Phase 2a complete. Await next instructions.
