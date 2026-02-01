# PASS 1 AUDIT REPORT — MPX3 Phase 3B “Get to Green” (Guarded)

ACKNOWLEDGEMENT
- ACKNOWLEDGED — MPX3 Guarded Execution Prompt. PASS 1 only.

---

## Repo State (Self-Detected)
- `git status --porcelain`:
```
<clean>
```
- `git diff`:
```
<no local diff>
```
- `git log -n 15 --oneline --decorate`:
```
663f903 (HEAD -> work) pass1: refresh PASS1_AUDIT_REPORT.md — updated gates, findings, and PASS2 plan
425951a feat(phase3b): Security & reliability hardening - subprocess timeouts and SQL allowlists
5b96782 feat(phase3a): Replace silent failures with explicit logging and DEGRADED state
070b3c7 fix(phase2): Fix schema mismatch in Research Lab queries
92d557c perf(phase2): Add pagination and reduce query payloads in Research Lab
75e3918 feat(phase0+1): Complete data layer fixes and UI simplification
502b18e chore: Add code-guardian to approved tools
7f29bf9 chore: Add audit logs, update files, and project documentation
c50c45c fix(audit24): Remove DuckDB connection conflicts - enforce singleton pattern
58b85ee feat(update21): Complete PASS 2 - Strategy naming + TSOT enforcement
5e68396 feat(audit): Step 1 - Add startup sync guard (C5 fix)
0de89a4 fix(preflight): Fix scope guard and import errors
bb17bca UPDATE19a: DB-backed lifecycle + smoke tests (fail-closed)
3cb9ca8 UPDATE15-18: Tooling-level drift protection + Guardian framework
43d035f FINAL FIXES: Use edge_candidates ONLY, remove all forbidden tables
```
- Repo-root guard/update docs present:
```
GUARDIAN.md
APP_COMPLETE_SURVEY.md
update15.txt
update16.txt
update17.txt
update18.txt
update19.txt
update19a.txt
update20.txt
update21.txt
update22.txt
update23a.txt
```
- Tags / last known “green” commit: **No tags found.** Unable to identify a known green baseline from tags.

---

# GATE CHECK RESULTS (Raw Output + Exit Codes)

## 1) `python scripts/check/app_preflight.py` (exit code: 1)
```
==========================================================================================
MPX APP PREFLIGHT
==========================================================================================

--- canonical_guard ---
================================================================================
CANONICAL GUARD (UPDATE18)
================================================================================

Protected files: CLAUDE.md, CANONICAL_LOGIC.txt, GUARDIAN.md

[92m[PASS] No unauthorized canonical file changes[0m

--- forbidden_paths_modified ---
================================================================================
FORBIDDEN PATHS MODIFIED CHECK (UPDATE18)
================================================================================

Forbidden directories:
  - strategies/
  - pipeline/
  - schema/migrations/

Forbidden files:
  - trading_app/cost_model.py
  - trading_app/entry_rules.py
  - trading_app/execution_engine.py

[92m[PASS] No forbidden paths modified[0m

--- scope_guard ---
================================================================================
SCOPE GUARD (UPDATE18)
================================================================================

Current scope: UI_ONLY

UI_ONLY scope allows changes to:
  - trading_app/ui/*
  - trading_app/app_*
  - trading_app/redesign_components.py*
  - trading_app/position_calculator.py*
  - trading_app/ui_contract.py*
  - trading_app/sync_guard.py*
  - trading_app/db_health_check.py*
  - trading_app/edge_utils.py*
  - trading_app/edge_pipeline.py*
  - trading_app/pb_grid_generator.py*
  - trading_app/time_spec.py*
  - trading_app/orb_time_logic.py*
  - tests/*
  - scripts/check/*
  - artifacts/*
  - docs/*
  - WORKFLOW_GUARDRAILS.md*
  - GUARDIAN.md*
  - APP_COMPLETE_SURVEY.md*
  - .claude/*

[92m[PASS] Scope respected (UI_ONLY)[0m

--- ui_fail_closed ---
[1m============================= test session starts ==============================[0m
platform linux -- Python 3.10.19, pytest-9.0.2, pluggy-1.6.0
rootdir: /workspace/MPX3/tests
configfile: pytest.ini
plugins: anyio-4.12.1
collected 24 items

tests/test_ui_fail_closed.py [32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.[0m[32m.                    [100%][0m

[32m============================== [32m[1m24 passed[0m[32m in 0.10s[0m[32m ==============================[0m
================================================================================
PYTEST SMOKE TESTS (UI FAIL-CLOSED CONTRACT)
================================================================================

Running tests: test_ui_fail_closed.py


[92m[PASS] All UI contract tests passed[0m

--- forbidden_patterns ---
================================================================================
FORBIDDEN PATTERN SCANNER (UPDATE16)
================================================================================

Repo root: /workspace/MPX3
Patterns: 19

Scanning for forbidden patterns...

[92m[PASS] No forbidden patterns detected[0m

Repository is clean!

--- execution_spec ---
======================================================================
EXECUTION SPEC VERIFICATION (UPDATE14 Step 5)
======================================================================
Project root: /workspace/MPX3

======================================================================
TEST 1: ExecutionSpec Creation
======================================================================
[PASS] Created valid spec: 9292fc83174a
[PASS] Caught invalid orb_time: orb_time must be 4 digits (e.g., '0900', '1000'), got: 999
[PASS] Caught incompatible combo: entry_rule='5m_close_outside' requires confirm_tf='5m', got confirm_tf='1m'

======================================================================
TEST 2: Serialization & Hashing
======================================================================
[PASS] Hash matches after serialization: 9292fc83174a
[PASS] Specs with different RR are compatible
[PASS] Specs with different entry_rule are not compatible

======================================================================
TEST 3: Contract Validation
======================================================================
[PASS] Contract validation passed for valid spec
[PASS] Caught unknown entry_rule: Unknown entry_rule: nonexistent_rule. Available: limit_at_orb, 1st_close_outside, 2nd_close_outside, 5m_close_outside

======================================================================
TEST 4: Entry Rule Implementations
======================================================================
[PASS] limit_at_orb: LONG @ 100.60
[PASS] 1st_close_outside: LONG @ 100.70
[PASS] 5m_close_outside: LONG @ 101.00

======================================================================
TEST 5: Universal Invariants
======================================================================
[PASS] Invariant: entry_timestamp > orb_end
[PASS] Invariant: no lookahead (entry >= confirm)
[PASS] Invariant: ORB window complete (5 bars)
[PASS] Invariant: limit entry <= tradeable entry (longs)

======================================================================
TEST 6: Pre-defined Presets
======================================================================
[PASS] Loaded preset: MGC 1000 ORB, tradeable entry (1st close outside)
[PASS] Caught unknown preset: "Preset 'nonexistent' not found. Available presets: mgc_1000_tradeable, mgc_1000_limit, mgc_1000_5m_close"

======================================================================
SUMMARY
======================================================================
[PASS]: Spec Creation
[PASS]: Serialization
[PASS]: Contracts
[PASS]: Entry Rules
[PASS]: Invariants
[PASS]: Presets

Passed: 6/6

[PASS] ALL TESTS PASSED - Execution specs verified!

--- sql_schema_verify ---
================================================================================
SQL SCHEMA REFERENCE CHECKER (UPDATE15)
================================================================================

[91m[FAIL]: Database not found[0m

--- auto_search_tables ---
Traceback (most recent call last):
  File "/workspace/MPX3/scripts/check/check_auto_search_tables.py", line 242, in <module>
    sys.exit(main())
  File "/workspace/MPX3/scripts/check/check_auto_search_tables.py", line 235, in main
    success = check_auto_search_tables()
  File "/workspace/MPX3/scripts/check/check_auto_search_tables.py", line 27, in check_auto_search_tables
    conn = duckdb.connect(db_path)
_duckdb.IOException: IO Error: Cannot open file "/workspace/MPX3/data/db/gold.db": No such file or directory

--- validation_queue_integration ---
Traceback (most recent call last):
  File "/workspace/MPX3/scripts/check/check_validation_queue_integration.py", line 221, in <module>
    sys.exit(main())
  File "/workspace/MPX3/scripts/check/check_validation_queue_integration.py", line 214, in main
    success = check_validation_queue_integration()
  File "/workspace/MPX3/scripts/check/check_validation_queue_integration.py", line 28, in check_validation_queue_integration
    conn = duckdb.connect(db_path)
_duckdb.IOException: IO Error: Cannot open file "/workspace/MPX3/data/db/gold.db": No such file or directory

--- live_terminal_fields ---
======================================================================
LIVE TRADING TERMINAL VERIFICATION (update8.txt)
======================================================================

Test 1: Fetch latest bar for MGC
----------------------------------------------------------------------
  [FAIL] IO Error: Cannot open database "/workspace/MPX3/data/db/gold.db" in read-only mode: database does not exist

Test 2: Fetch ORB levels from daily_features
----------------------------------------------------------------------
  [FAIL] IO Error: Cannot open database "/workspace/MPX3/data/db/gold.db" in read-only mode: database does not exist

Test 3: Verify entry/stop/target prices exist
----------------------------------------------------------------------
  [FAIL] IO Error: Cannot open database "/workspace/MPX3/data/db/gold.db" in read-only mode: database does not exist

Test 4 & 5: LiveScanner integration
----------------------------------------------------------------------
  [FAIL] IO Error: Cannot open database "/workspace/MPX3/data/db/gold.db" in read-only mode: database does not exist

Test 6: Verify weekend fallback (check historical data exists)
----------------------------------------------------------------------
  [FAIL] IO Error: Cannot open database "/workspace/MPX3/data/db/gold.db" in read-only mode: database does not exist

======================================================================
SUMMARY
======================================================================
[FAIL] - Test 1: Latest bar fetch
[FAIL] - Test 2: ORB levels fetch
[FAIL] - Test 3: Entry/stop/target calc
[FAIL] - Test 4 & 5: LiveScanner integration
[FAIL] - Test 6: Weekend fallback

SOME TESTS FAILED!

Fix failures before using Live Trading Terminal.

==========================================================================================
PREFLIGHT: FAIL (4 failing checks)
 - sql_schema_verify
 - auto_search_tables
 - validation_queue_integration
 - live_terminal_fields
```

## 2) `python test_app_sync.py` (exit code: 1)
```
MOTHERDUCK_TOKEN not found in cloud deployment
Could not connect to database. Returning empty configs.
MOTHERDUCK_TOKEN not found in cloud deployment
Could not connect to database. Returning empty configs.
MOTHERDUCK_TOKEN not found in cloud deployment
Could not connect to database. Returning empty configs.
Error getting validated setups: Catalog Error: Table with name validated_setups does not exist!
Did you mean "sqlite_temp_schema"?

LINE 21:                 FROM validated_setups
                              ^
Error loading configs for MGC: Catalog Error: Table with name validated_setups does not exist!
Did you mean "sqlite_temp_schema"?

LINE 7:             FROM validated_setups
                         ^
Error loading configs for NQ: Catalog Error: Table with name validated_setups does not exist!
Did you mean "sqlite_temp_schema"?

LINE 7:             FROM validated_setups
                         ^
Error loading configs for MPL: Catalog Error: Table with name validated_setups does not exist!
Did you mean "sqlite_temp_schema"?

LINE 7:             FROM validated_setups
                         ^
======================================================================
TESTING APP SYNCHRONIZATION
======================================================================

TEST 1: Config.py matches validated_setups database
----------------------------------------------------------------------
[FAIL] FAILED: gold.db not found
   Expected: /workspace/MPX3/data/db/gold.db

TEST 2: SetupDetector loads from database
----------------------------------------------------------------------
[FAIL] FAILED: SetupDetector couldn't load MGC setups

TEST 3: Data loader filter checking
----------------------------------------------------------------------
[PASS] ORB size filters ENABLED
   MGC filters: {}

TEST 4: Strategy engine config loading
----------------------------------------------------------------------
[FAIL] FAILED: MGC_ORB_CONFIGS is empty

TEST 5: ExecutionSpec system (UPDATE14)
----------------------------------------------------------------------

======================================================================
EXECUTION SPEC VERIFICATION (UPDATE14 Step 5)
======================================================================
Project root: /workspace/MPX3

======================================================================
TEST 1: ExecutionSpec Creation
======================================================================
[PASS] Created valid spec: 9292fc83174a
[PASS] Caught invalid orb_time: orb_time must be 4 digits (e.g., '0900', '1000'), got: 999
[PASS] Caught incompatible combo: entry_rule='5m_close_outside' requires confirm_tf='5m', got confirm_tf='1m'

======================================================================
TEST 2: Serialization & Hashing
======================================================================
[PASS] Hash matches after serialization: 9292fc83174a
[PASS] Specs with different RR are compatible
[PASS] Specs with different entry_rule are not compatible

======================================================================
TEST 3: Contract Validation
======================================================================
[PASS] Contract validation passed for valid spec
[PASS] Caught unknown entry_rule: Unknown entry_rule: nonexistent_rule. Available: limit_at_orb, 1st_close_outside, 2nd_close_outside, 5m_close_outside

======================================================================
TEST 4: Entry Rule Implementations
======================================================================
[PASS] limit_at_orb: LONG @ 100.60
[PASS] 1st_close_outside: LONG @ 100.70
[PASS] 5m_close_outside: LONG @ 101.00

======================================================================
TEST 5: Universal Invariants
======================================================================
[PASS] Invariant: entry_timestamp > orb_end
[PASS] Invariant: no lookahead (entry >= confirm)
[PASS] Invariant: ORB window complete (5 bars)
[PASS] Invariant: limit entry <= tradeable entry (longs)

======================================================================
TEST 6: Pre-defined Presets
======================================================================
[PASS] Loaded preset: MGC 1000 ORB, tradeable entry (1st close outside)
[PASS] Caught unknown preset: "Preset 'nonexistent' not found. Available presets: mgc_1000_tradeable, mgc_1000_limit, mgc_1000_5m_close"

======================================================================
SUMMARY
======================================================================
[PASS]: Spec Creation
[PASS]: Serialization
[PASS]: Contracts
[PASS]: Entry Rules
[PASS]: Invariants
[PASS]: Presets

Passed: 6/6

[PASS] ALL TESTS PASSED - Execution specs verified!

[PASS] ExecutionSpec checks passed

======================================================================
Test 6: Verify realized_rr usage (not r_multiple)
======================================================================
Running: scripts/check/check_realized_rr_usage.py

======================================================================
REALIZED_RR USAGE CHECK - Step 3 Verification
======================================================================

Checking critical files (must use realized_rr for decisions/scoring):

  [OK] trading_app/edge_utils.py
  [OK] trading_app/setup_detector.py
  [OK] trading_app/strategy_engine.py
  [OK] trading_app/auto_search_engine.py
  [OK] trading_app/experimental_scanner.py
  [OK] trading_app/app_canonical.py

Checking allowed files (can use r_multiple for raw data/schema):

  [ALLOWED] tests/conftest.py (raw data/schema usage OK)
  [ALLOWED] tests/test_build_daily_features.py (raw data/schema usage OK)
  [ALLOWED] strategies/execution_engine.py (raw data/schema usage OK)
  [ALLOWED] trading_app/edge_tracker.py (raw data/schema usage OK)
  [ALLOWED] discover_all_orb_patterns.py (raw data/schema usage OK)
  [ALLOWED] analysis/research_night_orb_comprehensive.py (raw data/schema usage OK)

======================================================================
COVERAGE SUMMARY
======================================================================

Total files scanned: 12/12

Files scanned:

  Critical files (must use realized_rr for decisions):
    - trading_app/edge_utils.py (2 r_multiple occurrences)
    - trading_app/setup_detector.py (0 r_multiple occurrences)
    - trading_app/strategy_engine.py (0 r_multiple occurrences)
    - trading_app/auto_search_engine.py (0 r_multiple occurrences)
    - trading_app/experimental_scanner.py (0 r_multiple occurrences)
    - trading_app/app_canonical.py (0 r_multiple occurrences)

  Allowed files (can use r_multiple for raw data/schema):
    - tests/conftest.py (1 r_multiple occurrences)
    - tests/test_build_daily_features.py (4 r_multiple occurrences)
    - strategies/execution_engine.py (11 r_multiple occurrences)
    - trading_app/edge_tracker.py (0 r_multiple occurrences)
    - discover_all_orb_patterns.py (0 r_multiple occurrences)
    - analysis/research_night_orb_comprehensive.py (0 r_multiple occurrences)

r_multiple occurrences found: 18 total
  - In critical files (blocked for decisions): 2
  - In allowed files (OK for raw data/schema): 16

Context breakdown:
  - BLOCKED (decision/scoring): 0 violations
  - ALLOWED (display-only/legacy): 16 occurrences

======================================================================
[OK] ALL CHECKS PASSED
======================================================================

Summary:
  [OK] 6 critical files checked
  [OK] 6 allowed files noted
  [OK] No r_multiple usage in decision/scoring paths
  [OK] All performance metrics use realized_rr

REALIZED_RR USAGE IS CORRECT



======================================================================
[FAIL] TESTS FAILED!

[WARN]  DO NOT USE THE APPS UNTIL MISMATCHES ARE FIXED

Fix the issues above and run this test again.
```

## 3) `pytest -q` (exit code: 3)
```
Usage: python test_filters_comprehensive.py <orb_time> <stop_frac> <rr>
Example: python test_filters_comprehensive.py 1000 0.75 8.0
mainloop: caught unexpected SystemExit!
INTERNALERROR> Traceback (most recent call last):
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 318, in wrap_session
INTERNALERROR>     session.exitstatus = doit(config, session) or 0
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 371, in _main
INTERNALERROR>     config.hook.pytest_collection(session=session)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_hooks.py", line 512, in __call__
INTERNALERROR>     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_manager.py", line 120, in _hookexec
INTERNALERROR>     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_callers.py", line 167, in _multicall
INTERNALERROR>     raise exception
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_callers.py", line 139, in _multicall
INTERNALERROR>     teardown.throw(exception)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/logging.py", line 788, in pytest_collection
INTERNALERROR>     return (yield)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_callers.py", line 139, in _multicall
INTERNALERROR>     teardown.throw(exception)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/warnings.py", line 98, in pytest_collection
INTERNALERROR>     return (yield)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_callers.py", line 139, in _multicall
INTERNALERROR>     teardown.throw(exception)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/config/__init__.py", line 1403, in pytest_collection
INTERNALERROR>     return (yield)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_callers.py", line 121, in _multicall
INTERNALERROR>     res = hook_impl.function(*args)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 382, in pytest_collection
INTERNALERROR>     session.perform_collect()
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 857, in perform_collect
INTERNALERROR>     self.items.extend(self.genitems(node))
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 1023, in genitems
INTERNALERROR>     yield from self.genitems(subnode)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 1023, in genitems
INTERNALERROR>     yield from self.genitems(subnode)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 1023, in genitems
INTERNALERROR>     yield from self.genitems(subnode)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 1020, in genitems
INTERNALERROR>     rep, duplicate = self._collect_one_node(node, handle_dupes)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/main.py", line 883, in _collect_one_node
INTERNALERROR>     rep = collect_one_node(node)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/runner.py", line 576, in collect_one_node
INTERNALERROR>     rep: CollectReport = ihook.pytest_make_collect_report(collector=collector)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_hooks.py", line 512, in __call__
INTERNALERROR>     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_manager.py", line 120, in _hookexec
INTERNALERROR>     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_callers.py", line 167, in _multicall
INTERNALERROR>     raise exception
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_callers.py", line 139, in _multicall
INTERNALERROR>     teardown.throw(exception)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/capture.py", line 880, in pytest_make_collect_report
INTERNALERROR>     rep = yield
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/pluggy/_callers.py", line 121, in _multicall
INTERNALERROR>     res = hook_impl.function(*args)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/runner.py", line 400, in pytest_make_collect_report
INTERNALERROR>     call = CallInfo.from_call(
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/runner.py", line 353, in from_call
INTERNALERROR>     result: TResult | None = func()
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/runner.py", line 398, in collect
INTERNALERROR>     return list(collector.collect())
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/python.py", line 563, in collect
INTERNALERROR>     self._register_setup_module_fixture()
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/python.py", line 576, in _register_setup_module_fixture
INTERNALERROR>     self.obj, ("setUpModule", "setup_module")
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/python.py", line 289, in obj
INTERNALERROR>     self._obj = obj = self._getobj()
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/python.py", line 560, in _getobj
INTERNALERROR>     return importtestmodule(self.path, self.config)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/python.py", line 507, in importtestmodule
INTERNALERROR>     mod = import_path(
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/pathlib.py", line 587, in import_path
INTERNALERROR>     importlib.import_module(module_name)
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py", line 126, in import_module
INTERNALERROR>     return _bootstrap._gcd_import(name[level:], package, level)
INTERNALERROR>   File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
INTERNALERROR>   File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
INTERNALERROR>   File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
INTERNALERROR>   File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
INTERNALERROR>   File "/root/.pyenv/versions/3.10.19/lib/python3.10/site-packages/_pytest/assertion/rewrite.py", line 197, in exec_module
INTERNALERROR>     exec(co, module.__dict__)
INTERNALERROR>   File "/workspace/MPX3/scripts/test/test_filters_comprehensive.py", line 91, in <module>
INTERNALERROR>     sys.exit(1)
INTERNALERROR> SystemExit: 1

no tests ran in 0.41s
```

## 4) `python scripts/check/check_time_literals.py` (exit code: 1)
```
================================================================================
TIME LITERALS CHECKER (H1 Enforcement + NEW-only)
================================================================================

Repo root: /workspace/MPX3

Scanning 138 Python files...

[92m[INFO][0m Loaded baseline: 876 known violations
  Files: 78

Current violations: 876 in 78 files

[91m[FAIL][0m Found 72 NEW STRUCTURAL violations

[91m[X][0m trading_app/priority_engine.py:314
  'orb_time': '1000',
  Pattern: \b1000\b

[91m[X][0m trading_app/priority_engine.py:321
  print(f"  ORB: 1000, RR: 2.0, Filters: none")
  Pattern: \b1000\b

[91m[X][0m trading_app/app_research_lab.py:247
  ["0900", "1000", "1100", "1800", "2300", "0030"],
  Pattern: \b0900\b

[91m[X][0m trading_app/app_research_lab.py:247
  ["0900", "1000", "1100", "1800", "2300", "0030"],
  Pattern: \b1000\b

[91m[X][0m trading_app/app_research_lab.py:247
  ["0900", "1000", "1100", "1800", "2300", "0030"],
  Pattern: \b1100\b

[91m[X][0m trading_app/app_research_lab.py:247
  ["0900", "1000", "1100", "1800", "2300", "0030"],
  Pattern: \b1800\b

[91m[X][0m trading_app/app_research_lab.py:247
  ["0900", "1000", "1100", "1800", "2300", "0030"],
  Pattern: \b2300\b

[91m[X][0m trading_app/app_research_lab.py:247
  ["0900", "1000", "1100", "1800", "2300", "0030"],
  Pattern: \b0030\b

[91m[X][0m trading_app/app_research_lab.py:248
  default=["0900", "1000", "1100"],
  Pattern: \b0900\b

[91m[X][0m trading_app/app_research_lab.py:248
  default=["0900", "1000", "1100"],
  Pattern: \b1000\b

[91m[X][0m trading_app/app_research_lab.py:248
  default=["0900", "1000", "1100"],
  Pattern: \b1100\b

[91m[X][0m trading_app/app_research_lab.py:446
  - **ORBs:** 0900, 1000, 1100 (daytime)
  Pattern: \b0900\b

[91m[X][0m trading_app/app_research_lab.py:446
  - **ORBs:** 0900, 1000, 1100 (daytime)
  Pattern: \b1000\b

[91m[X][0m trading_app/app_research_lab.py:446
  - **ORBs:** 0900, 1000, 1100 (daytime)
  Pattern: \b1100\b

[91m[X][0m trading_app/app_canonical.py:519
  for orb_name in ['0900', '1000', '1100', '1800', '2300', '0030']:
  Pattern: \b0900\b

[91m[X][0m trading_app/app_canonical.py:519
  for orb_name in ['0900', '1000', '1100', '1800', '2300', '0030']:
  Pattern: \b1000\b

[91m[X][0m trading_app/app_canonical.py:519
  for orb_name in ['0900', '1000', '1100', '1800', '2300', '0030']:
  Pattern: \b1100\b

[91m[X][0m trading_app/app_canonical.py:519
  for orb_name in ['0900', '1000', '1100', '1800', '2300', '0030']:
  Pattern: \b1800\b

[91m[X][0m trading_app/app_canonical.py:519
  for orb_name in ['0900', '1000', '1100', '1800', '2300', '0030']:
  Pattern: \b2300\b

[91m[X][0m trading_app/app_canonical.py:519
  for orb_name in ['0900', '1000', '1100', '1800', '2300', '0030']:
  Pattern: \b0030\b

[91m[X][0m trading_app/app_canonical.py:731
  all_orbs = ['0900', '1000', '1100', '1800', '2300', '0030']
  Pattern: \b0900\b

[91m[X][0m trading_app/app_canonical.py:731
  all_orbs = ['0900', '1000', '1100', '1800', '2300', '0030']
  Pattern: \b1000\b

[91m[X][0m trading_app/app_canonical.py:731
  all_orbs = ['0900', '1000', '1100', '1800', '2300', '0030']
  Pattern: \b1100\b

[91m[X][0m trading_app/app_canonical.py:731
  all_orbs = ['0900', '1000', '1100', '1800', '2300', '0030']
  Pattern: \b1800\b

[91m[X][0m trading_app/app_canonical.py:731
  all_orbs = ['0900', '1000', '1100', '1800', '2300', '0030']
  Pattern: \b2300\b

[91m[X][0m trading_app/app_canonical.py:731
  all_orbs = ['0900', '1000', '1100', '1800', '2300', '0030']
  Pattern: \b0030\b

[91m[X][0m trading_app/app_canonical.py:813
  (col1, '0900'),
  Pattern: \b0900\b

[91m[X][0m trading_app/app_canonical.py:814
  (col2, '1000'),
  Pattern: \b1000\b

[91m[X][0m trading_app/app_canonical.py:815
  (col3, '1100'),
  Pattern: \b1100\b

[91m[X][0m trading_app/app_canonical.py:816
  (col4, '1800'),
  Pattern: \b1800\b

[91m[X][0m trading_app/app_canonical.py:817
  (col5, '2300'),
  Pattern: \b2300\b

[91m[X][0m trading_app/app_canonical.py:818
  (col6, '0030')
  Pattern: \b0030\b

[91m[X][0m trading_app/edge_utils.py:21
  VALID_ORB_TIMES = frozenset({'0900', '1000', '1100', '1800', '2300', '0030'})
  Pattern: \b0900\b

[91m[X][0m trading_app/edge_utils.py:21
  VALID_ORB_TIMES = frozenset({'0900', '1000', '1100', '1800', '2300', '0030'})
  Pattern: \b1000\b

[91m[X][0m trading_app/edge_utils.py:21
  VALID_ORB_TIMES = frozenset({'0900', '1000', '1100', '1800', '2300', '0030'})
  Pattern: \b1100\b

[91m[X][0m trading_app/edge_utils.py:21
  VALID_ORB_TIMES = frozenset({'0900', '1000', '1100', '1800', '2300', '0030'})
  Pattern: \b1800\b

[91m[X][0m trading_app/edge_utils.py:21
  VALID_ORB_TIMES = frozenset({'0900', '1000', '1100', '1800', '2300', '0030'})
  Pattern: \b2300\b

[91m[X][0m trading_app/edge_utils.py:21
  VALID_ORB_TIMES = frozenset({'0900', '1000', '1100', '1800', '2300', '0030'})
  Pattern: \b0030\b

[91m[X][0m trading_app/edge_utils.py:47
  orb_time: 0900, 1000, etc.
  Pattern: \b0900\b

[91m[X][0m trading_app/edge_utils.py:47
  orb_time: 0900, 1000, etc.
  Pattern: \b1000\b

[91m[X][0m trading_app/app_simple.py:241
  - "How did 0900 ORB perform recently?"
  Pattern: \b0900\b

[91m[X][0m trading_app/app_simple.py:242
  - "1100 ORB performance last 60 days"
  Pattern: \b1100\b

[91m[X][0m trading_app/live_scanner.py:51
  '0900': time(9, 5),   # 09:00-09:05
  Pattern: \b0900\b

[91m[X][0m trading_app/live_scanner.py:52
  '1000': time(10, 5),  # 10:00-10:05
  Pattern: \b1000\b

[91m[X][0m trading_app/live_scanner.py:53
  '1100': time(11, 5),  # 11:00-11:05
  Pattern: \b1100\b

[91m[X][0m trading_app/live_scanner.py:54
  '1800': time(18, 5),  # 18:00-18:05
  Pattern: \b1800\b

[91m[X][0m trading_app/live_scanner.py:55
  '2300': time(23, 5),  # 23:00-23:05
  Pattern: \b2300\b

[91m[X][0m trading_app/live_scanner.py:56
  '0030': time(0, 35)   # 00:30-00:35
  Pattern: \b0030\b

[91m[X][0m trading_app/live_scanner.py:91
  ('0900', row[2], row[3], row[4], row[5], row[6], row[7], row[8]),
  Pattern: \b0900\b

[91m[X][0m trading_app/live_scanner.py:92
  ('1000', row[9], row[10], row[11], row[12], row[13], row[14], row[15]),
  Pattern: \b1000\b

[91m[X][0m trading_app/live_scanner.py:93
  ('1100', row[16], row[17], row[18], row[19], row[20], row[21], row[22]),
  Pattern: \b1100\b

[91m[X][0m trading_app/live_scanner.py:94
  ('1800', row[23], row[24], row[25], row[26], row[27], row[28], row[29]),
  Pattern: \b1800\b

[91m[X][0m trading_app/live_scanner.py:95
  ('2300', row[30], row[31], row[32], row[33], row[34], row[35], row[36]),
  Pattern: \b2300\b

[91m[X][0m trading_app/live_scanner.py:96
  ('0030', row[37], row[38], row[39], row[40], row[41], row[42], row[43])
  Pattern: \b0030\b

[91m[X][0m trading_app/live_scanner.py:536
  ('0900', row[2], row[3], row[4], row[5], row[6], row[7], row[8]),
  Pattern: \b0900\b

[91m[X][0m trading_app/live_scanner.py:537
  ('1000', row[9], row[10], row[11], row[12], row[13], row[14], row[15]),
  Pattern: \b1000\b

[91m[X][0m trading_app/live_scanner.py:538
  ('1100', row[16], row[17], row[18], row[19], row[20], row[21], row[22]),
  Pattern: \b1100\b

[91m[X][0m trading_app/live_scanner.py:539
  ('1800', row[23], row[24], row[25], row[26], row[27], row[28], row[29]),
  Pattern: \b1800\b

[91m[X][0m trading_app/live_scanner.py:540
  ('2300', row[30], row[31], row[32], row[33], row[34], row[35], row[36]),
  Pattern: \b2300\b

[91m[X][0m trading_app/live_scanner.py:541
  ('0030', row[37], row[38], row[39], row[40], row[41], row[42], row[43])
  Pattern: \b0030\b

[91m[X][0m trading_app/experimental_scanner.py:194
  - prev_0900_outcome: Previous trading day's 0900 ORB outcome
  Pattern: \b0900\b

[91m[X][0m trading_app/experimental_scanner.py:251
  '0900': orb_0900_size,
  Pattern: \b0900\b

[91m[X][0m trading_app/experimental_scanner.py:252
  '1000': orb_1000_size,
  Pattern: \b1000\b

[91m[X][0m trading_app/experimental_scanner.py:253
  '1100': orb_1100_size
  Pattern: \b1100\b

[91m[X][0m trading_app/experimental_scanner.py:259
  '0900': orb_0900_size / current_atr if orb_0900_size else None,
  Pattern: \b0900\b

[91m[X][0m trading_app/experimental_scanner.py:260
  '1000': orb_1000_size / current_atr if orb_1000_size else None,
  Pattern: \b1000\b

[91m[X][0m trading_app/experimental_scanner.py:261
  '1100': orb_1100_size / current_atr if orb_1100_size else None
  Pattern: \b1100\b

[91m[X][0m trading_app/experimental_scanner.py:366
  return (False, "No previous 0900 outcome data")
  Pattern: \b0900\b

[91m[X][0m trading_app/experimental_scanner.py:371
  return (True, "Previous 0900 ORB failed (mean reversion setup)")
  Pattern: \b0900\b

[91m[X][0m trading_app/experimental_scanner.py:372
  return (False, f"Previous 0900 was {prev_0900_outcome}, not LOSS")
  Pattern: \b0900\b

[91m[X][0m trading_app/app_trading_terminal.py:707
  <p>0900 ORB strategy performing well. 1000 ORB showing strong results in trendin
  Pattern: \b0900\b

[91m[X][0m trading_app/app_trading_terminal.py:707
  <p>0900 ORB strategy performing well. 1000 ORB showing strong results in trendin
  Pattern: \b1000\b

================================================================================
FIX REQUIRED - NEW STRUCTURAL VIOLATIONS
================================================================================

All time constants must be in trading_app/time_spec.py
Import from time_spec instead of hardcoding:

  # WRONG:
  ORB_TIMES = ['0900', '1000', '1100']

  # CORRECT:
  from trading_app.time_spec import ORBS
```

---

# RECENT-CHANGE AUDIT SCOPE
- No tags available to identify a “last green” commit; unable to diff against a green baseline. Defaulted to current HEAD-based scan.

---

# INCOMPLETE CODE FINDINGS (file:line + snippet)

## TODO/FIXME/HACK/TEMP
- `trading_app/app_simple.py:29` — `# TODO: Add singleton connection and run sync_guard after connection creation`
- `trading_app/app_trading_terminal.py:28-29` — `# TODO: Add singleton connection and run sync_guard after connection creation`
- `trading_app/app_trading_terminal.py:343` — `# TODO: Add ORB boxes from strategy engine`
- `trading_app/app_trading_terminal.py:429` — `# TODO: Implement actual trade execution`
- `trading_app/drift_monitor.py:258-261` — `# TODO: Check recent actual performance`
- `trading_app/market_scanner.py:160` — `# TODO: Add london_reversals when available in daily_features`
- `trading_app/market_scanner.py:535` — `# TODO: Add pattern matching from learned_patterns`
- `trading_app/ml_dashboard.py:93` — `# TODO: ml_performance table should store realized_rr (with costs), not r_multiple (theoretical)`
- `trading_app/ml_dashboard.py:115` — `# TODO: ml_performance table should use realized_rr instead of avg_r_multiple`
- `trading_app/ml_dashboard.py:198` — `# TODO: Should use realized_rr instead of avg_r_multiple (costs not included)`
- `scripts/discovery/walkforward_discovery.py:33` — `# TODO: Import remaining stages when implemented`
- `scripts/discovery/walkforward_discovery.py:181` — `# STAGE 4-9: TODO - Implement remaining stages`

## Placeholders / Not Implemented / Template Tokens
- `trading_app/edge_pipeline.py:6` — `Evaluate candidates (placeholder for backtesting integration)`
- `trading_app/pb_grid_generator.py:216-231` — placeholder test_config/metrics to be filled during backtesting
- `trading_app/position_tracker.py:311` — `# Quick action buttons (placeholder - would need actual button handlers)`
- `trading_app/market_hours_monitor.py:278` — `# Check spread warning (placeholder - would need real spread data)`
- `trading_app/auto_search_engine.py:556-559` — `not implemented` flags for stability/cost/tail risk
- `trading_app/app_canonical.py:1026-1029` — template tokens `orb_{{time}}`, `{{orb_time}}`
- `trading_app/edge_candidate_utils.py:79-118` — large commented example block (>3 lines)

## Pass Statements in Non-Abstract Paths
- `trading_app/live_scanner.py:197-207` — `pass` for pre_orb_travel and asia_types checks

---

# LOGIC ERRORS (file:line + impact)
- `trading_app/drift_monitor.py:226-243` — query selects `(candidate_id, name)` but loop unpacks `for (edge_id,) in promoted`, raising `ValueError` when promoted rows exist. Impact: health check crash when promoted edges exist.

---

# HALLUCINATED CODE (Phantom Schema) CHECK
- **Blocked**: DB introspection failed due to missing `data/db/gold.db` in this environment (see gate outputs). Schema verification against live DuckDB tables cannot be proven here.
- `schema.sql` exists but is not authoritative for a live DB in this environment; marked **UNKNOWN/BLOCKED** until DB is present.

---

# CONSTRAINT VIOLATIONS (file:line + rule)
- **TSOT**: 72 NEW STRUCTURAL time-literal violations (see `check_time_literals.py` output).
- **No mock/simulated/example data**: `trading_app/app_trading_terminal.py:694-709` contains “Recent insights (mock data)” block; `trading_app/cloud_mode.py:244-279` returns demo/placeholder data when MotherDuck is absent.

---

# LOGGING / ERROR HANDLING GAPS
- `trading_app/live_scanner.py:197-207` — condition branches skipped with `pass` and no logging.

---

# DUCKDB SINGLETON CHECK
- Canonical app (`app_canonical.py`) uses centralized AppState/connection logic (not re-verified here beyond file presence).
- Non-canonical apps note missing singleton + sync_guard injection (TODOs in `app_simple.py` and `app_trading_terminal.py`).

---

# TSOT VERIFICATION
- Canonical source for ORB times is `trading_app/time_spec.py` (`ORBS`, `ORB_FORMATION`, `ORB_TRADING_WINDOWS`).
- Allowed replacement pattern: iterate over `ORBS` or `ORB_FORMATION` keys, and use helpers (e.g., `get_orb_start_time`) instead of hardcoded literals.

---

# Subprocess Hardening Verification
- No `shell=True` use detected in Phase 3B targets (data_bridge.py, app_canonical.py, redesign_components.py). Subprocess usage already uses `sys.executable` and timeouts.

---

# RECOMMENDED FIX PLAN (PASS 2 — Minimal / Gate-Driven)

**Scope is limited to gate failures + explicitly enumerated hardening items.**

1) **pytest collection failure**
   - File: `scripts/test/test_filters_comprehensive.py`
   - Change: move CLI-only usage/`sys.exit(1)` under `if __name__ == "__main__"` to avoid pytest collection abort.

2) **drift_monitor tuple unpack crash**
   - File: `trading_app/drift_monitor.py`
   - Change: select only `candidate_id` or unpack `(edge_id, name)` properly.

3) **TSOT structural violations (NEW)**
   - Files: listed by `check_time_literals.py` output (app_simple, app_canonical, app_research_lab, live_scanner, experimental_scanner, edge_utils, priority_engine, app_trading_terminal).
   - Change: replace hardcoded ORB time strings with `time_spec.ORBS` or helpers; remove `orb_{{time}}` template tokens.

4) **Remove mock data blocks**
   - Files: `trading_app/app_trading_terminal.py` (“Recent insights” mock block), `trading_app/cloud_mode.py` demo data helpers.
   - Change: remove or replace with “no data available” states tied to real data sources only.

5) **Gate environment coupling (missing DB)**
   - Files: `scripts/check/sql_schema_verify.py`, `scripts/check/check_auto_search_tables.py`, `scripts/check/check_validation_queue_integration.py`, `scripts/check/check_live_terminal_fields.py`, `test_app_sync.py`
   - Change: detect missing `gold.db` and either fail with explicit actionable message or skip DB-dependent sections safely (fail-closed policy preserved; do NOT fabricate DB).

6) **Phase 3B hardening items (audit14)**
   - Files: `trading_app/data_bridge.py`, `trading_app/edge_utils.py`, `trading_app/utils.py`, `trading_app/app_canonical.py`, `trading_app/ai_memory.py`, `trading_app/redesign_components.py`
   - Change: align with Phase 3B requirements (timeouts, allowlists, placeholder consistency, accessibility control).

**Note:** No schema or trading logic changes. No new files or duplicate UI flows.

---

EVIDENCE FOOTER
===============

Files Modified:
- PASS1_AUDIT_REPORT.md: (PASS 1 report only)

Tables Read:
- None in PASS 1 (read-only audit).

Tables Written:
- None.

Write Actions Invoked:
- None.

Canonical Modules Touched:
- NONE ✅

Forbidden Paths Verified Unchanged:
- strategies/ ✅
- pipeline/ ✅
- trading_app/cost_model.py ✅
- trading_app/entry_rules.py ✅
- trading_app/execution_engine.py ✅

Gates Run:
- app_preflight.py: FAIL (missing DB)
- test_app_sync.py: FAIL (missing DB)
- pytest -q: FAIL (SystemExit on import)
- check_time_literals.py: FAIL (NEW structural violations)

---

APPROVAL REQUIRED — reply exactly: APPROVED PASS 2: <scope>
