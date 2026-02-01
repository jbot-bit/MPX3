# TSOT PHASE 1 - IMPACT MAP (PASS 1 AUDIT)

**Generated:** 2026-01-30
**Mode:** GUARDIAN-compliant (PASS 1 - AUDIT ONLY, NO CODE EDITS)
**Scope:** Phase 1 migration only (live_scanner.py, config.py, execution_spec.py)

---

## EXECUTIVE SUMMARY

**Total Phase 1 Violations:** 32 structural (18 + 6 + 8)
**Files to modify:** 3
**Estimated total diff:** ~150 lines (+imports, -literals, ~neutral)
**Risk level:** LOW (no trading logic changes, no DB writes, UI-only migrations)
**Forbidden paths touched:** NONE ✅

---

## FORBIDDEN PATH VERIFICATION ✅

**Phase 1 files checked against GUARDIAN.md forbidden list:**

| File | Status | Notes |
|------|--------|-------|
| `trading_app/live_scanner.py` | ✅ SAFE | Not in forbidden list |
| `trading_app/config.py` | ✅ SAFE | Not in forbidden list (config is allowed) |
| `trading_app/execution_spec.py` | ✅ SAFE | Not in forbidden list (spec definitions allowed) |

**Forbidden paths (confirmed NOT touched):**
- ❌ `strategies/` - NOT touched
- ❌ `pipeline/` - NOT touched
- ❌ `trading_app/cost_model.py` - NOT touched
- ❌ `trading_app/entry_rules.py` - NOT touched
- ❌ `trading_app/execution_engine.py` - NOT touched
- ❌ `schema/migrations/` - NOT touched

---

## FILE 1: trading_app/live_scanner.py

**Violations:** 18 structural (100% structural, 0% UI/display)
**Estimated diff:** ~60 lines (+3 imports, -0, ~57 replacements)
**Risk:** LOW (scanner logic only, no DB writes)

### Changes Required

**1. Add imports (line ~10):**
```python
from trading_app.time_spec import (
    ORB_FORMATION,
    ORBS,
    get_orb_end_time
)
```

**2. Replace hardcoded ORB_FORMATION_TIMES dict (lines 47-52):**

**BEFORE:**
```python
ORB_FORMATION_TIMES = {
    '0900': time(9, 5),   # 09:00-09:05
    '1000': time(10, 5),  # 10:00-10:05
    '1100': time(11, 5),  # 11:00-11:05
    '1800': time(18, 5),  # 18:00-18:05
    '2300': time(23, 5),  # 23:00-23:05
    '0030': time(0, 35)   # 00:30-00:35
}
```

**AFTER:**
```python
# Import ORB formation times from canonical source
ORB_FORMATION_TIMES = {
    orb: ORB_FORMATION[orb]['end']
    for orb in ORBS
}
```

**3. Replace ORB tuple literals (lines 87-92, 514-519):**

**BEFORE (lines 87-92):**
```python
orbs = [
    ('0900', row[2], row[3], row[4], row[5], row[6], row[7], row[8]),
    ('1000', row[9], row[10], row[11], row[12], row[13], row[14], row[15]),
    ('1100', row[16], row[17], row[18], row[19], row[20], row[21], row[22]),
    ('1800', row[23], row[24], row[25], row[26], row[27], row[28], row[29]),
    ('2300', row[30], row[31], row[32], row[33], row[34], row[35], row[36]),
    ('0030', row[37], row[38], row[39], row[40], row[41], row[42], row[43])
]
```

**AFTER (use ORBS list):**
```python
orbs = [
    (ORBS[0], row[2], row[3], row[4], row[5], row[6], row[7], row[8]),   # 0900
    (ORBS[1], row[9], row[10], row[11], row[12], row[13], row[14], row[15]),  # 1000
    (ORBS[2], row[16], row[17], row[18], row[19], row[20], row[21], row[22]),  # 1100
    (ORBS[3], row[23], row[24], row[25], row[26], row[27], row[28], row[29]),  # 1800
    (ORBS[4], row[30], row[31], row[32], row[33], row[34], row[35], row[36]),  # 2300
    (ORBS[5], row[37], row[38], row[39], row[40], row[41], row[42], row[43])   # 0030
]
```

*(Same pattern for lines 514-519)*

**Tables Read:** `daily_features` (existing, no changes)
**Tables Written:** NONE
**Justification:** UI-only (scanner display logic), no behavioral changes

---

## FILE 2: trading_app/config.py

**Violations:** 6 structural (100% structural, 0% UI/display)
**Estimated diff:** ~40 lines (+3 imports, -0, ~37 replacements)
**Risk:** MEDIUM (config affects all apps, but changes are backwards-compatible)

### Changes Required

**1. Add imports (line ~10):**
```python
from trading_app.time_spec import (
    ORBS,
    ORB_FORMATION
)
```

**2. Restructure ORB_SPECS dict (lines 46-51):**

**BEFORE:**
```python
ORB_SPECS = [
    {"hour": 9, "min": 0, "name": "0900"},
    {"hour": 10, "min": 0, "name": "1000"},
    {"hour": 11, "min": 0, "name": "1100"},
    {"hour": 18, "min": 0, "name": "1800"},   # London open (Asia close)
    {"hour": 23, "min": 0, "name": "2300"},
    {"hour": 0, "min": 30, "name": "0030"},  # Next day
]
```

**AFTER:**
```python
# Build ORB_SPECS from canonical time_spec
ORB_SPECS = [
    {
        "hour": ORB_FORMATION[orb]['start'].hour,
        "min": ORB_FORMATION[orb]['start'].minute,
        "name": orb
    }
    for orb in ORBS
]
```

**Tables Read:** NONE
**Tables Written:** NONE
**Justification:** Config restructuring only, no logic changes, backwards-compatible

---

## FILE 3: trading_app/execution_spec.py

**Violations:** 8 structural (57% structural, 43% UI/display)
**Estimated diff:** ~50 lines (+2 imports, -0, ~48 replacements)
**Risk:** LOW (preset examples only, no execution logic)

### Changes Required

**1. Add imports (line ~10):**
```python
from trading_app.time_spec import (
    ORBS,
    is_valid_orb
)
```

**2. Replace hardcoded "1000" in presets (lines 32, 201, 214, 227, 272, 291):**

**BEFORE:**
```python
orb_time="1000",
```

**AFTER:**
```python
orb_time=ORBS[1],  # 1000 ORB (use canonical constant)
```

**3. Update validation error message (line 80):**

**BEFORE:**
```python
f"orb_time must be 4 digits (e.g., '0900', '1000'), got: {self.orb_time}"
```

**AFTER:**
```python
f"orb_time must be one of {ORBS}, got: {self.orb_time}"
```

**4. UI/Display literals (lines with examples/help text):**
- **KEEP AS-IS:** Lines containing example text like `'0900'` in docstrings/comments (6 violations marked UI_OPERATIONAL_ALLOW)

**Tables Read:** NONE
**Tables Written:** NONE
**Justification:** Preset/example code only, no execution logic changes

---

## DIFF SIZE ESTIMATES

| File | Lines Changed | Additions | Deletions | Net | Risk |
|------|---------------|-----------|-----------|-----|------|
| `live_scanner.py` | ~60 | +15 (imports + comprehension) | -12 (old dict) | +3 | LOW |
| `config.py` | ~40 | +10 (imports + comprehension) | -6 (old list) | +4 | MEDIUM |
| `execution_spec.py` | ~50 | +8 (imports + constants) | -8 (old literals) | 0 | LOW |
| **TOTAL** | **~150** | **+33** | **-26** | **+7** | **LOW** |

**All files under 200-line limit:** ✅ PASS

---

## DATABASE OPERATIONS

### Tables Read
- `daily_features` (live_scanner.py only, existing read path)

### Tables Written
- **NONE** ✅

### Write Actions Invoked
- **NONE** ✅

---

## IMPORT DEPENDENCY TREE

```
trading_app/time_spec.py (canonical source)
  ├── ORBS = ['0900', '1000', '1100', '1800', '2300', '0030']
  ├── ORB_FORMATION = {...}  # start/end/duration for each ORB
  ├── get_orb_end_time(orb_name) -> time
  └── is_valid_orb(orb_name) -> bool

trading_app/live_scanner.py
  ├── imports: ORBS, ORB_FORMATION, get_orb_end_time
  └── uses: ORB_FORMATION_TIMES (derived from ORB_FORMATION)

trading_app/config.py
  ├── imports: ORBS, ORB_FORMATION
  └── uses: ORB_SPECS (derived from ORB_FORMATION)

trading_app/execution_spec.py
  ├── imports: ORBS, is_valid_orb
  └── uses: orb_time presets (replaced with ORBS[index])
```

---

## BACKWARDS COMPATIBILITY

**All changes are backwards-compatible:**
- ORB_SPECS format unchanged (still dict with hour/min/name)
- ORB_FORMATION_TIMES format unchanged (still dict {str: time})
- Preset orb_time values unchanged (still strings like "1000")
- No API changes, no function signature changes

**Apps using these files will see NO BREAKING CHANGES** ✅

---

## STOP CONDITIONS CHECKED

| Condition | Status | Notes |
|-----------|--------|-------|
| Forbidden paths touched? | ❌ NO | All Phase 1 files are allowed |
| Any file diff > 200 lines? | ❌ NO | Max 60 lines (live_scanner.py) |
| Missing symbols in time_spec? | ❌ NO | All exports exist (verified) |
| Trading logic modified? | ❌ NO | Scanner/config only |
| DB writes added? | ❌ NO | Read-only migrations |
| Schema changes? | ❌ NO | No schema modifications |

**All stop conditions: CLEAR ✅**

---

## PASS 2 GATE SEQUENCE

After edits are applied, run gates in this exact order:

1. **app_preflight.py** - Verify scope, forbidden paths, canonical guard
2. **test_app_sync.py** - Verify config/DB sync, ExecutionSpec system
3. **pytest -q** - Run full test suite

**If any gate fails:** STOP, fix, rerun all gates from beginning.

---

## EVIDENCE FOOTER (GUARDIAN.md COMPLIANT)

**CANONICAL FILES READ:**
- ✅ GUARDIAN.md (authority confirmed)
- ✅ CLAUDE.md (invariants confirmed)
- ✅ trading_app/time_spec.py (canonical source verified)
- ✅ tsot_migration_map.json (migration plan verified)
- ✅ TSOT_STEP5_REPORT.md (classification verified)

**FORBIDDEN PATHS VERIFICATION:**
- ✅ strategies/ - NOT touched
- ✅ pipeline/ - NOT touched
- ✅ cost_model.py - NOT touched
- ✅ entry_rules.py - NOT touched
- ✅ execution_engine.py - NOT touched
- ✅ schema/migrations/ - NOT touched

**IMPACT SUMMARY:**
- Files modified: 3
- Lines changed: ~150 (under 200-line limit per file)
- DB writes: NONE
- Trading logic changes: NONE
- Backwards compatibility: PRESERVED

**TSOT DETECTOR STATUS:**
- Remains WARN-only (no CI breaks)
- Will show reduced violations after migration
- Phase 1 will eliminate 32 structural violations

**READY FOR PASS 2:** ✅ YES

---

## NEXT STEPS (PASS 2)

1. Apply planned edits to 3 files (surgical, minimal diffs)
2. Run gate 1: `python scripts/check/app_preflight.py`
3. Run gate 2: `python test_app_sync.py`
4. Run gate 3: `pytest -q`
5. Generate git diff summary
6. Confirm detector remains WARN-only
7. Provide evidence footer per GUARDIAN.md

**DO NOT PROCEED TO PASS 2 WITHOUT USER APPROVAL OF THIS IMPACT MAP.**
