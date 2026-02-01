# WORKFLOW GUARDRAILS

**Purpose:** Define Builder vs Auditor workflow with Guardian mode enforcement.

**Created:** 2026-01-30 (UPDATE18)

---

## BUILDER → AUDITOR → GATES WORKFLOW

### Builder Step (Implement Change)

**Role:** Make minimal, surgical code changes.

**Constraints:**
- ✅ Make only planned changes from Impact Map
- ✅ Keep diffs small (<200 lines per file)
- ✅ No refactors unless explicitly required
- ✅ No changes to forbidden paths
- ✅ No changes to canonical documents

**Builder Checklist:**
- [ ] Read Impact Map (from PASS 1)
- [ ] Implement only planned changes
- [ ] Keep diffs minimal
- [ ] No forbidden paths touched
- [ ] No canonical documents modified

---

### Auditor Step (Review & Verify)

**Role:** Verify changes respect constraints and pass gates.

**Auditor Checklist:**
- [ ] Review git diff summary
- [ ] Verify no forbidden paths modified
- [ ] Verify no canonical documents modified
- [ ] Run all mandatory gates
- [ ] Confirm all gates pass
- [ ] Produce Evidence Footer

**Git Diff Review:**
```bash
git diff --stat HEAD
git diff HEAD -- strategies/ pipeline/ trading_app/cost_model.py trading_app/entry_rules.py trading_app/execution_engine.py
# Expected: No output (forbidden paths unchanged)
```

---

### Gates Step (Run Mandatory Checks)

**Role:** Execute all mandatory gates and ensure PASS.

**Mandatory Gates (in order):**

1. **Canonical Guard**
   ```bash
   python scripts/check/canonical_guard.py
   ```
   - Checks: CLAUDE.md, CANONICAL_LOGIC.txt, GUARDIAN.md unchanged
   - PASS required: Yes

2. **Forbidden Paths Modified**
   ```bash
   python scripts/check/forbidden_paths_modified.py
   ```
   - Checks: strategies/, pipeline/, cost_model.py, entry_rules.py, execution_engine.py unchanged
   - PASS required: Yes

3. **Scope Guard**
   ```bash
   SCOPE=UI_ONLY python scripts/check/scope_guard.py
   ```
   - Checks: Changes limited to UI code (trading_app/ui/, app_*.py, tests/)
   - PASS required: Yes (or use SCOPE=UNRESTRICTED with permission)

4. **App Preflight** (runs all checks)
   ```bash
   python scripts/check/app_preflight.py
   ```
   - Includes: canonical_guard, forbidden_paths_modified, scope_guard, ui_fail_closed, forbidden_patterns, execution_spec, sql_schema_verify, and more
   - PASS required: Yes (all checks except pre-existing failures)

5. **Database/Config Sync**
   ```bash
   python test_app_sync.py
   ```
   - Checks: validated_setups ↔ trading_app/config.py synchronization
   - PASS required: Yes

6. **UI Fail-Closed Tests**
   ```bash
   pytest tests/test_ui_fail_closed.py -v
   ```
   - Checks: UI contract enforcement (24 tests)
   - PASS required: Yes (24/24)

**Gate Failure Protocol:**
- ❌ If ANY gate fails → FIX immediately
- ❌ Do NOT bypass or disable checks
- ❌ Do NOT proceed until all gates PASS

---

## EVIDENCE FOOTER TEMPLATE

Every change must include this evidence:

```
EVIDENCE FOOTER
===============

Files Modified:
- scripts/check/canonical_guard.py: +120/-0 lines (NEW)
- scripts/check/forbidden_paths_modified.py: +140/-0 lines (NEW)
- scripts/check/scope_guard.py: +130/-0 lines (NEW)
- WORKFLOW_GUARDRAILS.md: +200/-0 lines (NEW)
- scripts/check/app_preflight.py: +3/-0 lines (integration)

New Checks Added:
- canonical_guard.py: Blocks accidental canonical document edits
- forbidden_paths_modified.py: Hard blocks forbidden path modifications
- scope_guard.py: Enforces UI_ONLY scope (prevents refactors)

Forbidden Paths Verified Unchanged:
- strategies/ ✅
- pipeline/ ✅
- schema/migrations/ ✅
- trading_app/cost_model.py ✅
- trading_app/entry_rules.py ✅
- trading_app/execution_engine.py ✅

Canonical Files Verified Unchanged:
- CLAUDE.md ✅
- CANONICAL_LOGIC.txt ✅
- GUARDIAN.md ✅ (now protected by canonical_guard.py)

Gates Run:
- canonical_guard.py: PASS ✅
- forbidden_paths_modified.py: PASS ✅
- scope_guard.py: PASS ✅ (SCOPE=UI_ONLY)
- app_preflight.py: PASS ✅ (6/7 checks, 1 pre-existing failure)
- test_app_sync.py: PASS ✅
- pytest -q: 24/24 PASS ✅

Tables Read: NONE (pure git diff checking)
Tables Written: NONE (pure git diff checking)

Write Actions Invoked: NONE
```

---

## SCOPE MODES

### UI_ONLY (Default)

**Allowed changes:**
- `trading_app/ui/` - UI components
- `trading_app/app_*.py` - UI pages (app_canonical.py, app_trading_hub.py, etc.)
- `trading_app/*_components.py` - UI component modules
- `tests/` - UI tests
- `scripts/check/` - Preflight checks
- `docs/` - Documentation

**Forbidden:**
- Everything else (especially canonical logic)

**Usage:**
```bash
SCOPE=UI_ONLY python scripts/check/app_preflight.py
```

### UNRESTRICTED

**Allowed changes:**
- All files (use with caution)

**When to use:**
- Explicitly approved changes to canonical logic
- Schema migrations
- Pipeline modifications
- **REQUIRES EXPLICIT PERMISSION**

**Usage:**
```bash
SCOPE=UNRESTRICTED python scripts/check/app_preflight.py
```

---

## OVERRIDE FLAGS

### ALLOW_CANONICAL=1

**Purpose:** Allow editing canonical documents (CLAUDE.md, CANONICAL_LOGIC.txt, GUARDIAN.md)

**When to use:**
- Explicitly appending to CANONICAL_LOGIC.txt
- Updating CLAUDE.md with new invariants
- Modifying Guardian protocol

**Usage:**
```bash
ALLOW_CANONICAL=1 python scripts/check/canonical_guard.py
```

### SCOPE=UNRESTRICTED

**Purpose:** Disable scope restrictions

**When to use:**
- Changes to canonical logic (with permission)
- Pipeline modifications
- Schema migrations

**Usage:**
```bash
SCOPE=UNRESTRICTED python scripts/check/scope_guard.py
```

---

## DRIFT PREVENTION CHECKLIST

Before making ANY change:

- [ ] Read relevant sections from CLAUDE.md
- [ ] Read relevant sections from APP_COMPLETE_SURVEY.md
- [ ] Produce Impact Map (PASS 1)
- [ ] Confirm no forbidden paths touched
- [ ] Confirm no canonical documents modified
- [ ] Get approval if needed
- [ ] Implement changes (PASS 2)
- [ ] Run all mandatory gates
- [ ] Produce Evidence Footer
- [ ] Confirm all gates PASS

---

## WHAT THESE GUARDRAILS PREVENT

✅ **Accidental modification of trading logic** during UI work
✅ **Drift between canonical documents and code**
✅ **Creation of parallel execution paths**
✅ **Introduction of mock/fake data**
✅ **Unprotected database writes**
✅ **"Helpful refactors"** that touch canonical code
✅ **Scope creep** during focused UI work

---

## CURRENT ENFORCEMENT STATUS

**Active Guards:**
- ✅ canonical_guard.py (UPDATE18)
- ✅ forbidden_paths_modified.py (UPDATE18)
- ✅ scope_guard.py (UPDATE18)
- ✅ forbidden_pattern_scan.py (UPDATE16)
- ✅ sql_schema_verify.py (UPDATE15)
- ✅ ui_fail_closed tests (UPDATE17)

**Integration:**
- ✅ All guards run in app_preflight.py
- ✅ CI/test runner executes app_preflight.py
- ✅ Fail-closed: Any gate failure blocks deployment

---

**End of Workflow Guardrails**
