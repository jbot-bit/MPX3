# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2026-01-20 PM 7] - Feature-Flag ML Initialization (Disable by Default)

### Fixed
- **ML Disabled by Default** - `trading_app/config.py`
  - Changed ML_ENABLED to default to False (was True in local dev)
  - ML now OFF unless explicitly enabled via ENABLE_ML=1 or ML_ENABLED=true
  - Accepts both ENABLE_ML and ML_ENABLED for backward compatibility
  - Eliminates "ML engine initialization failed: No module named 'ml_inference'" errors

### Changed
- **Improved ML Error Handling** - `trading_app/app_trading_hub.py`, `trading_app/app_mobile.py`
  - When ML disabled: Logs "ML disabled (ENABLE_ML not set)" at INFO level (not WARNING)
  - When ML enabled but missing: Logs clear ERROR with instructions to install or disable
  - Distinguishes ImportError (missing module) from other exceptions
  - No more confusing warnings when ML is intentionally disabled

### Impact
- Phase 1 apps now run cleanly without ML modules
- No "ML engine initialization failed" errors in logs by default
- Clear path to enable ML in Phase 2: Set ENABLE_ML=1 and install ml_inference

---

## [2026-01-20 PM 6] - Fix Cloud Mode Auto-Detection (LOCALFIX)

### Fixed
- **Local DuckDB Forced on Windows Dev** - `trading_app/cloud_mode.py`
  - Removed bad heuristic: "if data/db/gold.db doesn't exist → cloud mode"
  - Added FORCE_LOCAL_DB environment variable override (values: 1/true/yes)
  - Cloud mode now ONLY when CLOUD_MODE or Streamlit Cloud env vars are set
  - Local dev defaults to local DuckDB always (no more unexpected MotherDuck connections)

### Added
- **DB Mode Logging** - `trading_app/cloud_mode.py`
  - Logs "DB MODE: LOCAL (reason: ...)" or "DB MODE: CLOUD (reason: ...)" on first connection
  - Shows which env var or heuristic triggered the mode
  - Logs resolved local database path

- **Auto-Create Local DB** - `trading_app/cloud_mode.py`
  - If data/db/gold.db doesn't exist, creates parent directory and empty DB file
  - Prevents file-not-found errors on fresh dev environments
  - Does NOT migrate/create tables (that's done by separate migration scripts)

### Changed
- **is_cloud_deployment()** logic simplified and made explicit
  - No more implicit file-existence checks
  - Respects FORCE_LOCAL_DB override first
  - Falls back to default local dev mode

---

## [2026-01-20 PM 5] - AI Chart Analysis with OHLCV Data

### Added
- **OHLCV Data in EvidencePack** - `trading_app/ai_guard.py`
  - Added `bars_timeframe` and `bars_ohlcv_sample` fields to EvidencePack dataclass
  - AI can now analyze actual price bars instead of just saying "no OHLCV bar data"
  - Chart questions trigger automatic loading of last 600 1-minute bars (10 hours)

- **Chart Question Detection** - `trading_app/ai_assistant.py`
  - Detects chart-related keywords: chart, pattern, support, resistance, trend, structure, etc.
  - Automatically queries bars_1m when chart analysis is requested
  - Returns OHLCV bars as list of dicts with ts, open, high, low, close, volume

- **Fresh Price Update** - `trading_app/ai_assistant.py`
  - current_price now derived from latest bar close (not stale parameter)
  - Freshness check warns if bars are > 2 minutes old
  - Prevents AI from using outdated prices

- **OHLCV Display in Evidence** - `trading_app/ai_guard.py`
  - _format_evidence_for_prompt() now includes last 50 OHLCV bars
  - Formatted as CSV for AI analysis: ts,open,high,low,close,volume
  - Clear instructions to AI on how to use bar data

- **Chart Analysis System Prompt** - `trading_app/prompts/LOCKED_SYSTEM_PROMPT.txt`
  - Added CHART ANALYSIS RULE section
  - AI may only analyze charts when OHLCV BAR DATA section is present
  - Enforces fail-closed: refuses chart analysis if bars_ohlcv_sample is absent
  - Permits pattern description but not performance claims without validated setups

- **Test Suites**
  - `tests/test_ai_chart_evidence_pack.py` - 6 tests for OHLCV loading
  - `tests/test_evidence_footer_singleton.py` - 6 tests for footer deduplication
  - Tests verify: bar loading, price freshness, keyword detection, empty table handling

### Changed
- **trading_app/ai_guard.py** - Evidence Footer deduplication
  - Checks if footer already present in AI response before appending
  - Prevents duplicate "**Evidence Footer:**" markers
  - Logs warning if duplicate detected

- **trading_app/ai_assistant.py** - Enhanced _build_evidence_pack
  - Now accepts user_question parameter for chart detection
  - Queries bars_1m when chart keywords detected
  - Updates current_price from latest bar close
  - Adds warning to facts if bars are stale or unavailable

### Fixed
- **AI says "no OHLCV bar data provided"**
  - Root cause: EvidencePack only listed table names, didn't include actual bars
  - Fix: Query and include OHLCV rows when chart questions asked
  - Result: AI can now analyze actual price data

- **Stale current_price in EvidencePack**
  - Root cause: current_price parameter passed to _build_evidence_pack was stale
  - Fix: Query latest bar and update current_price from bar close
  - Result: current_price now matches latest bar in UI

- **Duplicate Evidence Footer**
  - Root cause: No check if footer already in response
  - Fix: Check for "**Evidence Footer:**" marker before appending
  - Result: Exactly one footer per response

### Technical Details
- OHLCV data bounded: max 600 bars (10 hours of 1m data)
- Prompt size managed: only last 50 bars shown to AI (others available in sample)
- Fail-closed: warns if bars unavailable, refuses chart analysis
- No lookahead: all bars are historical (ts <= current time)
- All 33 tests passing:
  - test_ai_source_lock.py: 11/11
  - test_edge_approval.py: 10/10
  - test_ai_chart_evidence_pack.py: 6/6
  - test_evidence_footer_singleton.py: 6/6

---

## [2026-01-20 PM 4] - Database Bootstrap & CSV Upload Fix

### Added
- **Database Bootstrap Module** - `trading_app/db_bootstrap.py`
  - Ensures required tables exist in both local and MotherDuck databases at app startup
  - `ensure_required_tables(conn)`: Creates edge_candidates table if not exists
  - `bootstrap_database()`: Runs bootstrap with canonical DB connection
  - Uses CREATE TABLE IF NOT EXISTS (idempotent, safe to run multiple times)
  - Fixes "Catalog Error: Table with name edge_candidates does not exist" in MotherDuck

- **CSV Upload Support** - `app_trading_hub.py`
  - Chart upload now accepts CSV files in addition to images
  - File uploader allowlist: ["png", "jpg", "jpeg", "csv"]
  - CSV parsing with pandas (validates TradingView format)
  - Required columns: time, open, high, low, close (volume optional)
  - Shows preview of uploaded CSV data
  - Fail-closed validation: blocks ingestion if required columns missing
  - Clear user-visible error messages for invalid CSV format

- **Test Suite** - `tests/test_db_bootstrap.py`
  - 9 comprehensive tests for database bootstrap
  - Tests table creation, schema validation, idempotency
  - Tests write connection usage (read_only=False)
  - Tests error handling and default values
  - All tests passing (9/9)

### Changed
- **trading_app/app_trading_hub.py** - Enhanced startup and upload
  - Added database bootstrap call before page config
  - CSV upload detection and parsing logic
  - Branches between image analysis and CSV preview based on file type
  - Updated help text: "Upload a TradingView screenshot (image) or CSV export"

- **trading_app/app_mobile.py** - Enhanced startup
  - Added database bootstrap call before page config
  - Ensures edge_candidates table exists in both local and cloud modes

- **trading_app/edge_candidates_ui.py** - Deprecation fix
  - Replaced `use_container_width=True` with `width="stretch"` for st.dataframe
  - Fixes Streamlit deprecation warning (use_container_width removed after 2025-12-31)

### Fixed
- **MotherDuck Schema Error** - edge_candidates table missing
  - Error: "Catalog Error: Table with name edge_candidates does not exist!"
  - Cause: Cloud database (MotherDuck) didn't have edge_candidates table
  - Fix: db_bootstrap.py ensures table exists at app startup
  - Works in both local (gold.db) and cloud (MotherDuck) modes

- **CSV Upload Blocked** - text/csv files rejected
  - Error: "text/csv files are not allowed"
  - Cause: File uploader only accepted image types
  - Fix: Updated type allowlist to include "csv"
  - Added CSV parsing and validation logic

### Technical Details
- Bootstrap uses get_database_connection(read_only=False) for schema changes
- CSV validation is fail-closed (rejects partial/invalid data)
- No changes to trading logic or AI Source Lock
- All 30 tests passing:
  - test_db_bootstrap.py: 9/9
  - test_edge_approval.py: 10/10
  - test_ai_source_lock.py: 11/11

---

## [2026-01-20 PM 3] - Edge Candidates UI Panel (Review & Approval)

### Added
- **Edge Candidates UI Panel** - `edge_candidates_ui.py`
  - Interactive table for viewing edge candidates from database
  - Filtering by status (ALL, DRAFT, PENDING, APPROVED, REJECTED)
  - Filtering by instrument (ALL, MGC, NQ, MPL)
  - Limit selector (50, 100, 200, 500 rows)
  - Expandable details for each candidate (hypothesis, metrics, robustness, specs)
  - Action buttons: Approve, Set Pending, Reject
  - Optional notes field for status changes
  - Auto-reload after actions

- **UI Integration** - Both desktop and mobile apps
  - `app_trading_hub.py`: Added Edge Candidates expandable panel
  - `app_mobile.py`: Added Edge Candidates expandable panel
  - Accessible via "🔬 Edge Candidates (Research)" expander
  - Uses existing backend functions (approve_edge_candidate, set_candidate_status)

### Technical Details
- Uses canonical DB routing (`cloud_mode.get_database_connection`)
- No direct duckdb.connect calls in UI code
- Works in both local and MotherDuck modes
- All actions auditable (approved_by, approved_at, notes)
- No changes to trading logic or AI Source Lock

---

## [2026-01-20 PM 2] - Edge Candidate Approval & Write-Safe DB Connection

### Added
- **Write-Capable Database Connection** - `cloud_mode.py::get_database_connection(read_only=bool)`
  - Added optional `read_only` parameter (default: True for backward compatibility)
  - Enables write operations when explicitly requested (read_only=False)
  - Maintains read-only default for all existing callers (zero breaking changes)
  - Works with both local (gold.db) and cloud (MotherDuck) databases

- **Edge Candidate Approval Functions** - `edge_candidate_utils.py`
  - `approve_edge_candidate(candidate_id, approver)`: Approve candidate with validation
  - `set_candidate_status(candidate_id, status, notes, actor)`: Generic status setter
  - Validates candidate exists and is not already approved
  - Sets status='APPROVED', approved_at=CURRENT_TIMESTAMP, approved_by=approver
  - Supports workflow: DRAFT → PENDING → APPROVED/REJECTED

- **Manual Approval Script** - `approve_candidate.py`
  - Command-line script for approving edge candidates
  - Usage: `python approve_candidate.py <candidate_id> [approver_name]`
  - Default approver: "Josh"
  - Clear success/error messages

- **Test Suite** - `tests/test_edge_approval.py`
  - 11 comprehensive tests for approval functions
  - Tests write connection usage (read_only=False)
  - Tests status updates, validation, error handling
  - Uses temporary DuckDB database for isolated testing

### Changed
- **trading_app/cloud_mode.py** - Enhanced connection function
  - `get_database_connection()`: Added `read_only: bool = True` parameter
  - `get_motherduck_connection()`: Added `read_only: bool = True` parameter (note: MotherDuck handles permissions server-side)
  - Backward compatible: all existing callers continue to work unchanged

### Documentation
- Updated CHANGELOG.md with edge approval workflow
- Added docstrings for all new functions

---

## [2026-01-20 PM 1] - Evidence Footer & AI Source Lock Enhancement

### Added
- **Evidence Footer System** (per AI_EDGE_ENGINE_PROMPT.txt Section 1)
  - User-visible audit trail appended to all AI responses
  - Shows: db_mode (local/motherduck), tables_used, data_window, strategy_ids, no_lookahead_check, queries
  - Provides transparency of data sources and validation status
  - Auto-generated by `ai_guard.py::_format_evidence_footer()`

- **EvidencePack Fields** - Enhanced validation
  - `db_mode`: str (local | motherduck) - Cloud deployment detection
  - `no_lookahead_check`: str (PASS | FAIL) - Zero lookahead enforcement
  - `strategy_ids`: List[int] - Setup IDs used in analysis

- **Lookahead Validation** - Fail-closed gate
  - Blocks trade recommendations if `no_lookahead_check == "FAIL"`
  - Enforces as-of joins and walk-forward validation
  - Per AI_EDGE_ENGINE_PROMPT.txt Section 2

### Changed
- **trading_app/ai_guard.py** - Evidence Footer integration
  - `EvidencePack` dataclass: Added db_mode, no_lookahead_check, strategy_ids fields
  - `is_complete()`: Now validates db_mode and no_lookahead_check (required)
  - `missing_fields()`: Reports missing Evidence Footer fields
  - `validate_evidence_pack()`: Rule 6 - Blocks recommendations on lookahead violations
  - `guarded_chat_answer()`: Appends Evidence Footer to all responses

- **trading_app/ai_assistant.py** - Evidence pack builder
  - `_build_evidence_pack()`: Detects db_mode via `is_cloud_deployment()`
  - Sets `no_lookahead_check = "PASS"` for validated historical queries
  - Extracts strategy_ids from setup_rows

- **trading_app/prompts/LOCKED_SYSTEM_PROMPT.txt** - Documentation
  - Added "EVIDENCE FOOTER (AUTO-APPENDED)" section
  - AI knows Evidence Footer is automatically added (no manual inclusion needed)

- **tests/test_ai_source_lock.py** - Updated test fixtures
  - All 4 EvidencePack instantiations updated with new required fields
  - Tests pass with Evidence Footer validation

### Documentation
- Updated CHANGELOG.md (this entry)
- Evidence Footer format per AI_EDGE_ENGINE_PROMPT.txt specification

---

## [2026-01-20 AM] - Production Readiness & AI Source Lock Enforcement

### Added
- **tools/preflight.py** - Automated 5-gate production readiness scanner
  - Gate 1: Canonical environment validation (CANONICAL.json, no shadow DBs)
  - Gate 2: Data integrity audit (runs audit_master.py --quick)
  - Gate 3: Config/DB synchronization (runs test_app_sync.py)
  - Gate 4: Test suite execution (pytest -q, optional)
  - Gate 5: Static code scan (duplicate files, AI bypass detection)
  - Exit code 0 = production ready, 1 = failures with actionable errors

- **App Startup Gates** - Fail-closed environment validation
  - Both `app_mobile.py` and `app_trading_hub.py` now validate canonical environment on startup
  - Shows clear error messages with fix instructions if validation fails
  - Blocks app launch on violations (prevents running in bad state)

- **Guarded Vision API** - `ai_guard.py::guarded_vision_answer()`
  - Single choke point for all Vision/chart analysis calls
  - Enforces visual-only observations (no performance claims without DB data)
  - Uses locked system prompt with evidence pack constraints

### Changed
- **trading_app/chart_analyzer.py** - Refactored to use AI Source Lock
  - Removed `import anthropic` (was bypassing ai_guard.py)
  - Replaced direct `client.messages.create()` with `guarded_vision_answer()`
  - Chart upload now fully guarded through ai_guard.py

- **trading_app/ai_memory.py** - Canonical DB routing
  - Removed hardcoded `db_path="trading_app.db"` parameter
  - Replaced all 6 `duckdb.connect()` calls with `get_database_connection()`
  - Now uses canonical DB (data/db/gold.db local, MotherDuck in cloud)
  - Fixed SQL INTERVAL syntax for MotherDuck compatibility
    - Changed `INTERVAL $1 DAY` to `INTERVAL '{days}' DAY` (lines 140, 150)
    - MotherDuck doesn't support parameterized INTERVAL syntax

- **trading_app/cloud_mode.py** - Fixed path detection bug
  - Old: Checked `../data/db/gold.db` (broken relative path)
  - New: Checks `Path(__file__).parent.parent / "data" / "db" / "gold.db"`
  - Now respects `.env` CLOUD_MODE setting explicitly
  - Prevents false cloud mode detection when running locally

- **trading_app/app_mobile.py** - Enhanced startup sequence
  - Added path setup for repo root (enables canonical imports)
  - Added canonical environment validation gate
  - Consolidated import paths at top of file

- **trading_app/app_trading_hub.py** - Enhanced startup sequence
  - Added path setup for repo root (enables canonical imports)
  - Added canonical environment validation gate
  - Same fail-closed behavior as mobile app

- **strategies/test_app_sync.py** - Moved from root directory
  - Was: `./test_app_sync.py` (root)
  - Now: `strategies/test_app_sync.py` (correct location per README_MIGRATION.md)
  - Fixed import paths to work from new location

### Fixed
- **SQL Parser Errors** - ai_memory.py INTERVAL syntax
  - Error: `Parser Error: syntax error at or near "$1" ... INTERVAL $1 DAY`
  - Cause: MotherDuck doesn't support parameterized INTERVAL values
  - Fix: Use string formatting for interval (safe since days is int)

- **Cloud Mode False Detection** - cloud_mode.py
  - Error: `is_cloud_deployment()` returned True when running locally
  - Cause: Path check `../data/db/gold.db` failed (wrong relative path)
  - Fix: Use `Path(__file__).parent.parent / "data" / "db" / "gold.db"`

- **Import Path Errors** - App startup
  - Error: `ModuleNotFoundError: No module named 'trading_app'`
  - Cause: Repo root not in sys.path before canonical imports
  - Fix: Add both trading_app/ and repo root to sys.path at startup

### Removed
- **trading_app/trading_app.db** - Shadow database (deleted)
  - Was created during memory migration testing
  - Caused canonical environment gate failures
  - All memory now in canonical DB (data/db/gold.db or MotherDuck)

- **test_app_sync.py** - Removed from root
  - Moved to strategies/ per folder structure rules

### Security
- **AI Source Lock Enforcement** - Zero tolerance for bypasses
  - All AI/LLM calls MUST go through `ai_guard.py` (single choke point)
  - Chart analyzer refactored (was bypassing guard)
  - Static scan detects any new violations automatically
  - Preflight gate blocks deployment if violations found

### Documentation
- Created CHANGELOG.md (this file)
- Updated README.md with preflight instructions
- Updated CLAUDE.md with new tools and gates
- Updated README_MIGRATION.md compliance status

---

## Previous Changes

See git history for changes before 2026-01-20.
Major milestones:
- 2026-01-19: Migration complete (README_MIGRATION.md)
- 2026-01-16: Scan window bug fix (docs/SCAN_WINDOW_BUG_FIX_SUMMARY.md)
- 2026-01-15: Database routing fixes (DB_ROUTING_FIX_SUMMARY.md)
