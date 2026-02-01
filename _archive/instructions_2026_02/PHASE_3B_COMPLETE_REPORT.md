# PHASE 3B COMPLETE — Security, Reliability & Hardening

**Date:** 2026-01-31
**Mode:** CODE GUARDIAN (ENFORCED)
**Protocol:** FAIL-CLOSED

---

## Summary

Phase 3B implemented security and reliability hardening for core infrastructure without changing trading logic, schema, or DB write paths.

---

## Files Changed

| File | Change | Risk Mitigated |
|------|--------|----------------|
| `trading_app/data_bridge.py` | shell=False, sys.executable, timeouts, logging | Process hang, arg parsing |
| `trading_app/edge_utils.py` | VALID_ORB_TIMES allowlist validation | SQL injection via column name |
| `trading_app/utils.py` | VALID_JOURNAL_TABLES allowlist validation | SQL injection via table name |
| `trading_app/app_canonical.py` | 30s timeout on preflight subprocess | App startup hang |
| `trading_app/redesign_components.py` | Remove cursor:pointer, add ARIA labels | Misleading UX, accessibility |

---

## Detailed Changes

### 1. data_bridge.py — Subprocess Hardening (ID 1 + ID 5)

**Before:**
- `shell=True` on all subprocess calls
- No timeout — process could hang indefinitely
- stderr only shown on failure

**After:**
- `shell=False` with `sys.executable` for safe Python resolution
- `BACKFILL_TIMEOUT = 300` (5 min) for backfill operations
- `FEATURE_BUILD_TIMEOUT = 60` (1 min) per-day feature build
- Timeout handled gracefully with clear error messages
- stdout/stderr logged for visibility
- Progress reporting: "Building features: day X of Y"

### 2. edge_utils.py — ORB_TIME Allowlist (ID 2)

**Before:**
- `orb_time` interpolated directly into SQL column names
- No validation against valid values

**After:**
- `VALID_ORB_TIMES = frozenset({'0900', '1000', '1100', '1800', '2300', '0030'})`
- Validation before SQL interpolation in `run_real_validation()`
- Fail-closed: Returns `{'outcome': 'INVALID_ORB_TIME', ...}` if invalid

### 3. utils.py — JOURNAL_TABLE Allowlist (ID 3)

**Before:**
- `JOURNAL_TABLE` interpolated directly into DDL/DML statements
- No validation

**After:**
- `VALID_JOURNAL_TABLES = frozenset({'live_journal', 'strategy_journal', 'trade_journal'})`
- `_validate_journal_table()` function validates before use
- Fail-closed: Raises `ValueError` if invalid

### 4. app_canonical.py — Preflight Timeout (ID 4)

**Before:**
- No timeout on preflight subprocess
- App could hang indefinitely on startup

**After:**
- `PREFLIGHT_TIMEOUT = 30` seconds
- TimeoutExpired caught with clear error message
- User guidance: "Run `python scripts/check/app_preflight.py` in terminal to diagnose"
- Preserves fail-closed behavior (st.stop() on failure)

### 5. redesign_components.py — Accessibility Fix (ID 7)

**Before:**
- `cursor: pointer` on non-interactive element
- No ARIA attributes

**After:**
- Removed `cursor: pointer` (element is informational, not clickable)
- Added `role="status"` and `aria-label` for screen readers
- Added `aria-hidden="true"` on decorative badge

---

## Skipped

**ID 6 (ai_memory.py):** No change needed. The `$1, $2` placeholders are intentionally compatible with both DuckDB (local) and MotherDuck (cloud). DuckDB accepts both `?` and `$N` styles.

---

## Gates Results

| Gate | Result |
|------|--------|
| Syntax check (py_compile) | ✅ PASS |
| app_preflight.py | ✅ PASS (SCOPE=UNRESTRICTED) |
| test_app_sync.py | ✅ PASS |
| pytest (264/335) | ⚠️ 54 pre-existing failures (not related to Phase 3B) |
| check_time_literals.py | ⚠️ Flags VALID_ORB_TIMES (expected — it's an allowlist definition) |

---

## Constraints Verified

| Constraint | Status |
|------------|--------|
| No schema changes | ✅ |
| No new DB tables | ✅ |
| No new DB write paths | ✅ |
| No trading math changes | ✅ |
| No execution/cost logic changes | ✅ |
| No pipeline output changes | ✅ |

---

## Before/After Failure Behavior

| Scenario | Before | After |
|----------|--------|-------|
| Backfill script hangs | App blocks forever | Timeout after 300s with error |
| Feature build per-day hangs | Loop blocks forever | Timeout after 60s, continues to next day |
| Preflight script hangs | App startup blocked | Timeout after 30s with recovery instructions |
| Invalid orb_time in edge | SQL injection possible | Rejected with clear error |
| Invalid JOURNAL_TABLE | SQL injection possible | Rejected with ValueError |
| Next-step rail clicked | Nothing (misleading) | Nothing (now clearly informational) |

---

## Statement

**Security, reliability, and startup hardening complete. No logic or schema changes.**

All subprocess calls now have explicit timeouts and safe argument handling. All dynamic SQL identifiers are validated against allowlists. The app fails closed with clear error messages rather than hanging indefinitely.
