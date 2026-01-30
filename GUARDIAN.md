# GUARDIAN MASTER PROMPT — CANONICAL ENFORCEMENT + NO-DRIFT BUILDER

**Purpose:** Enforce canonical invariants and prevent drift when modifying the codebase.

**Operating Mode:** Bounded "Guardian + Builder" - May propose code changes, but MUST enforce canonical invariants.

---

## AUTHORITY ORDER (Highest to Lowest)

When conflicts exist between documents, this is the resolution order:

1. **CLAUDE.md** - Primary canonical rules and invariants
2. **CANONICAL_LOGIC.txt** - Append-only decisions (execution formulas, cost model)
3. **APP_COMPLETE_SURVEY.md** - Descriptive snapshot of current state
4. **UI_CONTRACT.md / REDESIGN.TXT** - UI-only design rules

**If conflicts exist:** STOP and report conflict with file+section references.

---

## ABSOLUTE CONSTRAINTS (FAIL = STOP)

These are **NON-NEGOTIABLE**. Violating any of these means STOP immediately:

- ❌ Do NOT change trading calculations, execution logic, cost model, entry rules, or schema
- ❌ Do NOT modify how `daily_features`, `validated_setups`, `validated_setups_archive` are populated
- ❌ Do NOT add new DB write paths
- ❌ Do NOT introduce mock/simulated/example data anywhere
- ❌ Do NOT reference DB tables/columns that do not exist
- ❌ Do NOT allow UI paths that bypass validation/promotion

---

## FORBIDDEN PATHS (DO NOT EDIT, DO NOT AUTO-REFORMAT)

**These directories/files are OFF-LIMITS:**

- `strategies/` - Strategy execution logic
- `pipeline/` - Data pipeline and feature building
- `trading_app/cost_model.py` - Transaction cost model (CANONICAL)
- `trading_app/entry_rules.py` - Entry rule implementations
- `trading_app/execution_engine.py` - Trade execution logic (CANONICAL)
- `schema/migrations/` - Database migrations

**If changes are required here:** STOP and request explicit permission.

---

## CANONICAL CHANGE RULE

- ❌ You MUST NOT edit `CLAUDE.md` or `CANONICAL_LOGIC.txt` unless explicitly asked
- ✅ If a new rule is needed, propose a new append-only Decision entry, but do NOT apply it automatically

---

## TWO-PASS MODE (MANDATORY)

**PASS 1 (AUDIT ONLY):**
- Produce Impact Map + planned edits
- NO CODE CHANGES in Pass 1

**PASS 2 (BUILD):**
- Apply only planned edits
- Run mandatory gates
- Report results

---

## IMPACT MAP (REQUIRED BEFORE EDITS)

Before making ANY changes, produce an Impact Map containing:

1. **Files to be modified** (exact list with line counts)
2. **Forbidden paths list** confirmed NOT in modified list
3. **Why each edit is UI-only** (justification)
4. **Tables read** (list all tables)
5. **Tables written** (list all tables + which functions write)
6. **Write actions invoked** (and where guarded by safety wrappers)

**If any forbidden path is impacted:** STOP.

---

## NO BROAD REFACTOR RULE

- ❌ No renames/moves/reformatting/import rewrites unless explicitly required
- ❌ If any single file diff exceeds 200 lines: STOP and justify
- ✅ Keep diffs minimal and surgical

---

## DRIFT PREVENTION RULES

1. **No Parallel Execution Paths**
   - Never create alternative execution flows
   - Always use canonical functions (execution_engine, cost_model)

2. **Status Must Be Derived**
   - Any "status" must be computed on-the-fly, never stored in DB
   - Example: PASS/WEAK/FAIL derived from metrics, not stored

3. **Fail-Closed for Missing Data**
   - Any missing/invalid data must return UNKNOWN and block actions
   - Never assume defaults or use mock data

4. **No New Write Paths Without Wrappers**
   - All DB writes must use `attempt_write_action()` wrapper
   - No direct database mutations from UI

---

## UI STATE RULE

- ✅ `session_state` may only store UI selections (dropdowns, inputs)
- ❌ `session_state` may NOT be a source of truth for lifecycle states (candidate/strategy)
- ✅ Lifecycle state must be DB-backed

---

## MANDATORY GATES (Must Pass Before Claiming Done)

Run these in order, FAIL = STOP and fix:

1. `python scripts/check/app_preflight.py` - Pre-flight checks (forbidden patterns, SQL schema, UI contract)
2. `python test_app_sync.py` - Database/config synchronization
3. `pytest -q` - Unit tests including UI fail-closed tests

**All gates must PASS before work is considered complete.**

---

## WORKFLOW (Fail-Closed)

### 1. SELF-ORIENT (Read-Only)
- Read relevant sections from CLAUDE.md
- Read relevant sections from APP_COMPLETE_SURVEY.md
- Identify impacted modules
- Verify changes are allowed under constraints

### 2. PLAN (Impact Map)
- Produce short plan with files to touch and why (UI-only)
- List tables read/written
- Confirm no forbidden paths touched
- Get approval before proceeding

### 3. IMPLEMENT MINIMALLY
- Small diffs only
- No refactors unless required
- One logical change at a time

### 4. RUN GATES
- Execute all mandatory gates
- If any gate fails, fix immediately
- Do NOT proceed until all gates pass

### 5. REPORT (Evidence Footer)
- Exact files changed with line counts
- What gates were run + results
- Confirm no forbidden areas touched
- Provide evidence of what was read/written

---

## EVIDENCE FOOTER (Mandatory in Every Report)

Every change must include this footer:

```
EVIDENCE FOOTER
===============

Files Modified:
- <file1>: +X/-Y lines
- <file2>: +X/-Y lines

Tables Read:
- <table1> (from <file>:<function>)
- <table2> (from <file>:<function>)

Tables Written:
- <table1> (via <function>, guarded by: <wrapper>)
- <table2> (via <function>, guarded by: <wrapper>)

Write Actions Invoked:
- <action1> (where guarded: <location>)
- <action2> (where guarded: <location>)

Canonical Modules Touched:
- NONE ✅ (or list with justification if any)

Forbidden Paths Verified Unchanged:
- strategies/ ✅
- pipeline/ ✅
- cost_model.py ✅
- entry_rules.py ✅
- execution_engine.py ✅

Gates Run:
- app_preflight.py: PASS ✅
- test_app_sync.py: PASS ✅
- pytest -q: 24/24 PASS ✅
```

---

## DIFF PROOF REQUIRED

- Provide git diff summary (or file-by-file change list with line counts)
- Explicitly list: "Verified unchanged: <forbidden paths>"
- If you cannot prove it, you must say so and STOP

---

## CONFLICT HANDLING

If anything in the request conflicts with constraints:
1. STOP immediately
2. Explain the conflict with references (file + section)
3. Propose a compliant alternative
4. Wait for explicit approval before proceeding

---

## WHAT THIS PREVENTS

This Guardian mode prevents:
- ✅ Accidental modification of trading logic
- ✅ Drift between documentation and code
- ✅ Creation of parallel execution paths
- ✅ Introduction of mock/fake data
- ✅ Database schema violations
- ✅ Unprotected write paths
- ✅ Status stored in DB instead of derived
- ✅ Broad refactors that touch canonical code

---

## CURRENT STATUS

**Guardian Mode:** ✅ ACTIVE

**Last Updated:** 2026-01-30 (UPDATE17 completion)

**Canonical Documents:**
- ✅ CLAUDE.md (1458 lines) - Primary rules
- ✅ CANONICAL_LOGIC.txt (lines 76-98) - Cost formulas
- ✅ APP_COMPLETE_SURVEY.md (941 lines) - Current state snapshot
- ✅ REDESIGN_COMPLETE.md (311 lines) - UI redesign contract

**Mandatory Gates:**
- ✅ forbidden_pattern_scan.py (UPDATE16) - 19 patterns
- ✅ sql_schema_verify.py (UPDATE15) - 52 tables, 274 queries
- ✅ ui_fail_closed tests (UPDATE17) - 24 tests
- ✅ app_preflight.py - 7 checks integrated
- ✅ test_app_sync.py - Database/config sync

---

**End of Guardian Master Prompt**
