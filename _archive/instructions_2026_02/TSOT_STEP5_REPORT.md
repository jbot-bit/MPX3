# TSOT Step 5 - Time Literal Classification Report

**Generated:** 2026-01-30
**TSOT Program:** Time Source of Truth Migration
**Status:** READ-ONLY ANALYSIS (no code edits)

---

## Executive Summary

Analyzed **276 time literal violations** across **31 files**.

### Classification Breakdown

| Category | Count | Percentage | Action |
|----------|-------|------------|--------|
| **STRUCTURAL_MIGRATE** | 201 | 72.8% | Replace with time_spec imports |
| **UI_OPERATIONAL_ALLOW** | 75 | 27.2% | Keep as-is (display only) |
| **HISTORICAL_IGNORE** | 0 | 0.0% | Ignore (analysis scripts) |
| **TEST_DEV** | 0 | 0.0% | Keep as-is (tests) |

---

## Category Definitions

### 1. STRUCTURAL_MIGRATE (201 violations)
**Impact:** HIGH - Affects trading logic, routing, validation
**Action:** Replace with `time_spec.py` imports

**Examples:**
- ORB lists: `['0900', '1000', '1100']` → `time_spec.ORBS`
- Session times: `time(9, 0)` → `time_spec.SESSIONS['ASIA']['start']`
- ORB selectboxes: `["0900", "1000"]` → `time_spec.ORBS`
- Validation logic: `if orb_time in ['0900', '1000']` → `time_spec.is_valid_orb(orb_time)`

### 2. UI_OPERATIONAL_ALLOW (75 violations)
**Impact:** LOW - Display only, no behavioral changes
**Action:** Keep as-is (allowed)

**Examples:**
- Help text: `placeholder="How did 0900 ORB perform..."`
- Comments: `# 0900 ORB strategy`
- Print statements: `print("0900 ORB: TAKE")`
- CSS: `z-index: 1000;`
- Milliseconds: `refresh_interval * 1000`
- Dollar amounts: `daily_loss_dollars=1000.0`

### 3. HISTORICAL_IGNORE (0 violations)
**Impact:** NONE - Not production code
**Action:** Ignore

**Examples:**
- `analysis/*.py` scripts
- `_archive/` files
- Research notebooks

### 4. TEST_DEV (0 violations)
**Impact:** LOW - Test fixtures only
**Action:** Keep as-is

**Examples:**
- `test_*.py` files
- Pytest fixtures
- Mock data

---

## Top 10 Files Requiring Migration

Sorted by number of STRUCTURAL_MIGRATE violations:

1. **trading_app\market_scanner.py**: 37 structural violations
2. **trading_app\app_canonical.py**: 24 structural violations
3. **trading_app\live_scanner.py**: 18 structural violations
4. **trading_app\app_research_lab.py**: 15 structural violations
5. **trading_app\edge_tracker.py**: 14 structural violations
6. **trading_app\ai_chat.py**: 12 structural violations
7. **trading_app\chart_analyzer.py**: 12 structural violations
8. **trading_app\auto_search_engine.py**: 9 structural violations
9. **trading_app\execution_spec.py**: 8 structural violations
10. **trading_app\config.py**: 6 structural violations


---

## Critical Files Requiring Immediate Attention

### 1. trading_app/config.py
**Violations:** 6
**Priority:** CRITICAL
**Issue:** ORB_SPECS dict hardcodes time values
**Fix:** Import from `time_spec.ORB_FORMATION` and restructure

### 2. trading_app/live_scanner.py
**Violations:** 18
**Priority:** HIGH
**Issue:** Hardcoded ORB formation times dict
**Fix:** Replace with `time_spec.ORB_FORMATION`

### 3. trading_app/app_canonical.py
**Violations:** 24
**Priority:** HIGH
**Issue:** Multiple ORB lists, selectboxes, column mappings
**Fix:** Import `time_spec.ORBS` at top of file

---

## Missing Constants in time_spec.py

None found. All violations map to existing time_spec.py exports.


---

## Available time_spec.py Exports

All violations can be migrated using these existing exports:

- **ORBS**: ['0900', '1000', '1100', '1800', '2300', '0030']
- **ORB_FORMATION**: Dict with start/end/duration for each ORB
- **ORB_TRADING_WINDOWS**: Dict with form_time/end_time/window_minutes
- **SESSIONS**: Dict with ASIA/LONDON/NY definitions
- **TZ_LOCAL**: ZoneInfo("Australia/Brisbane")
- **TZ_UTC**: ZoneInfo("UTC")
- **TRADING_DAY_START**: time(9, 0)
- **TRADING_DAY_END**: time(9, 0)
- **MARKET_OPEN**: time(9, 0)
- **MARKET_CLOSE**: time(2, 0)
- **ORB_TIERS**: Dict with A/B/C tier classifications
- **get_orb_start_time()**: Helper function
- **get_orb_end_time()**: Helper function
- **get_session_start_time()**: Helper function
- **get_session_end_time()**: Helper function
- **is_valid_orb()**: Helper function
- **is_valid_session()**: Helper function


---

## Next Steps (TSOT Step 6)

1. **Review tsot_migration_map.json** - Detailed line-by-line migration plan
2. **Prioritize structural files** - Start with config.py, live_scanner.py, app_canonical.py
3. **Create migration script** - Automate simple replacements (ORB lists → time_spec.ORBS)
4. **Manual review** - Complex logic requiring careful refactoring
5. **Update CI check** - Add time_spec.py to allowed list in check_time_literals.py
6. **Test thoroughly** - Run test_app_sync.py after each migration

---

## Methodology

**Classification Rules:**
- Analysis scripts → HISTORICAL_IGNORE
- Test files → TEST_DEV
- CSS/milliseconds/dollars → UI_OPERATIONAL_ALLOW
- ORB lists/session times/validation → STRUCTURAL_MIGRATE
- Help text/comments/prints → UI_OPERATIONAL_ALLOW (unless in routing logic)
- Ambiguous cases → prefer STRUCTURAL for consistency

**Data Sources:**
- Input: time_literal_inventory.txt (26KB, 78 files)
- Canonical: trading_app/time_spec.py
- Output: tsot_migration_map.json (detailed), TSOT_STEP5_REPORT.md (summary)

---

## Contact

Questions? See `audit9.txt` for TSOT program details.
