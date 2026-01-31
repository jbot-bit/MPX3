# Phase 3A Complete: Live Cockpit Reliability & Visibility

**Completed**: 2026-01-31
**Branch**: feature/ui-redesign-conveyor-belt

## Summary

Phase 3A replaced silent failures with explicit logging and degraded states. The live system now fails closed with operator visibility.

## Files Changed

| File | Change | Risk Level |
|------|--------|------------|
| `trading_app/live_scanner.py` | DEGRADED status + error logging | HIGH (primary fix) |
| `trading_app/experimental_scanner.py` | Warning logging for date lookup | MEDIUM |
| `trading_app/priority_engine.py` | Debug logging for malformed JSON | LOW |
| `trading_app/provenance.py` | Debug logging for git/path failures | LOW |

## Silent Failures Eliminated

### 1. live_scanner.py:_load_promoted_conditions() [CRITICAL]

**Before**: DB exception returned `None`, caller interpreted as "no conditions", strategy appeared healthy

**After**:
- Logs error: `logger.error(f"DEGRADED: Failed to load promoted conditions...")`
- Caches degraded state: `{'_load_error': str(e), '_degraded': True}`
- Returns `None` (same behavior)
- Scan logic checks for degraded state and sets `status = 'DEGRADED'`

**UI Impact**: Strategy shows "DEGRADED" status with reason instead of appearing healthy

### 2. experimental_scanner.py:_find_prev_trading_day() [MEDIUM]

**Before**: Silent `continue` on exception, possibly returned wrong date

**After**:
- Logs warning: `logger.warning(f"Error checking trading day {candidate}...")`
- Continues loop (same behavior, now visible)

### 3. priority_engine.py:_calculate_filter_priorities() [LOW]

**Before**: Silent skip of malformed `filters_json`

**After**:
- Logs debug: `logger.debug(f"Skipping malformed filters_json: {e}")`
- Continues processing (same behavior, now visible)

### 4. provenance.py utilities [LOW]

**Before**: Silent exceptions in `get_git_commit()`, `get_git_branch()`, `get_db_path()`

**After**:
- Logs debug: `logger.debug(f"Could not get git commit: {e}")`
- Returns `None` or fallback (same behavior, now visible)

## New Visibility Surfaces

1. **DEGRADED Status**: New strategy status visible in UI when condition loading fails
2. **Error Logs**: All failures now logged at appropriate levels (error/warning/debug)
3. **Reason Propagation**: Degraded state includes error message for operator diagnosis

## Constraints Honored

- No schema changes
- No new DB writes
- No trading logic changes
- Fail-closed behavior (degrade, don't auto-disable)
- Minimal surface-area changes

## Validation

```
test_app_sync.py: ALL TESTS PASSED
Module imports: All 4 files import successfully
Syntax check: All files pass Python compilation
```

## Statement

**Live system now fails closed with operator visibility.**

Silent failures that could mask data issues have been replaced with explicit logging and degraded states. Operators can now see when strategies are degraded and why, rather than trusting a system that may be running with incomplete data.
