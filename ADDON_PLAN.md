# ADDON PLAN - Wire UPDATE14 into Sync Suite

**Goal**: Make ExecutionSpec checks "unskippable" by integrating into existing verification suite

**Status**: ✅ COMPLETE (All 5 tasks + audit done)

---

## ✅ TASK 1: Self-Identify Existing Verification Entrypoints (COMPLETE)

### Find:
- `test_app_sync.py` (root level)
- `scripts/check/app_preflight.py`
- `CLAUDE.md` section on required checks

### Understand:
- How test_app_sync runs checks (subprocess vs imports)
- What app_preflight's check list looks like
- Where to append in CLAUDE.md

---

## ✅ TASK 2: Wire Into Suite (COMPLETE)

### Actions:
- Add check_execution_spec to test_app_sync.py
- Add check_execution_spec to app_preflight.py
- Follow existing patterns (logging, fail-closed behavior)
- Clear error messages if missing/fails

---

## ✅ TASK 3: Sync Guard (Fail-Closed) (COMPLETE)

### Logic:
```python
if execution_spec.py exists:
    if check_execution_spec.py missing OR not executed:
        FAIL with clear message
```

Prevents silent drift.

---

## ✅ TASK 4: Update Docs (Append-Only) (COMPLETE)

### Append to CLAUDE.md:
- "UPDATE14 ExecutionSpec checks are mandatory"
- Commands to run
- Do NOT delete older sections

---

## ✅ TASK 5: Verification (COMPLETE)

### Run:
```bash
python scripts/check/check_execution_spec.py
python test_app_sync.py
python scripts/check/app_preflight.py
```

All must pass.

---

## COMPLETION SUMMARY

✅ All 5 tasks completed successfully
✅ All verification tests pass (6/6, 5/5, 4/4)
✅ Comprehensive audit performed
✅ Logic verified, edge cases tested
✅ Documentation updated

**See**: ADDON_COMPLETE.md for full audit report and verification results
