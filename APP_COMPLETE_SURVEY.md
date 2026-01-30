# APP COMPLETE SURVEY

**Generated:** 2026-01-30
**Purpose:** Complete understanding of the trading app architecture, UI surfaces, write paths, canonical rules, and drift risks

---

## 1. UI SURFACE SUMMARY

### Main Application: `trading_app/app_canonical.py` (3202 lines)

**Architecture:** 3-Zone Conveyor Belt System (Research → Validation → Production → Live)

#### Tab 1: 🚦 LIVE TRADING (Lines 310-729)

**Purpose:** Real-time market analysis and position sizing

**Inputs:**
- Instrument selection (MGC - hardcoded in current implementation)
- Account size (via `position_calculator.py`)
- Risk percentage
- Max drawdown (optional, for prop firms)

**Outputs:**
- Live price with freshness indicator (green if <60s, yellow if 60-300s, red if >300s)
- Market state: Date, ATR, session status
- ORB levels (expandable, shows all 6 ORBs: 0900/1000/1100/1800/2300/0030)
- Active setups with trade plans (filters passed, ready to trade)
- Waiting setups (expandable, filters not met)
- Invalid setups (expandable, quality issues)
- Position calculator showing:
  - Recommended position size
  - Risk per contract
  - Total dollar risk
  - True risk % (for prop firm drawdown tracking)
  - Cost breakdown (commission, slippage, spread)

**Actions Triggered:**
- None (read-only zone)

**DB Tables Read:**
- `validated_setups` (active strategies)
- `bars_1m` or `bars_5m` (latest price)
- `daily_features` (ORB levels, session stats)

**DB Tables Written:**
- None

**Key Components:**
- `LiveScanner` (from `live_scanner.py`) - Scans validated_setups against current market
- `position_calculator.py` - Calculates position sizing using `cost_model.py`
- `orb_time_logic.py` - Time-aware status (ACTIVE/UPCOMING/STANDBY)

---

#### Tab 2: 🔴 RESEARCH LAB (Lines 730-1380)

**Purpose:** Discover promising candidate setups ("What might be worth testing?")

**Inputs:**
- Instrument selection (MGC, NQ, MPL)
- ORB times (multi-select from 0900/1000/1100/1800/2300/0030)
- Filter configuration (collapsible, hidden by default):
  - Entry rule (limit_at_orb, 1st_close_outside, 5m_close_outside)
  - ORB size filter (min/max)
  - RSI filter (range)
  - Date range (start/end)

**Outputs:**
- Scan results showing:
  - Number of candidates found
  - Preview table with key metrics (ExpR, N, Win%, RR)
  - Stress test results (+25%, +50%)
  - Status chip (PASS/WEAK/FAIL - derived on-the-fly)
- Next-step rail showing: "Next: Send candidates to Validation Gate"

**Actions Triggered:**
1. **"Scan for Candidates"** → Calls `auto_search_engine.py` → Reads `bars_1m`, `daily_features` → Writes to `search_candidates`
2. **"Send to Validation"** (with checkboxes) → Uses `attempt_write_action()` wrapper → Writes to `validation_queue`

**DB Tables Read:**
- `bars_1m` or `bars_5m` (price data for backtesting)
- `daily_features` (ORB outcomes, session stats)
- `search_candidates` (previous scan results)
- `validation_queue` (pending validation candidates)

**DB Tables Written:**
- `search_candidates` (scan results)
- `validation_queue` (selected candidates for validation)

**Safety Wrapper:**
- ✅ "Send to Validation" uses `attempt_write_action()` (runs `app_preflight.py` + `test_app_sync.py`)

---

#### Tab 3: 🟡 VALIDATION GATE (Lines 1381-2072)

**Purpose:** Prove or kill candidates ("Does this edge survive stress tests?")

**Inputs:**
- Candidate selection (from `validation_queue` or `edge_candidates`)
- Candidate ID to validate

**Outputs:**
- Candidate details (ID, name, instrument, status, test window)
- Validation status (PASS/WEAK/FAIL - derived on-the-fly from metrics):
  - **PASS** (🟢): ExpR ≥ 0.15R AND survives +50% stress
  - **WEAK** (🟡): ExpR ≥ 0.15R AND survives +25% stress only
  - **FAIL** (🔴): ExpR < 0.15R OR both stress tests fail
- Stress test results:
  - Baseline ExpR
  - +25% stress test (PASS/FAIL)
  - +50% stress test (PASS/FAIL)
  - Walk-forward test (PASS/FAIL)
- Recent validation runs (last 10)
- Next-step rail showing: "Next: Approve/Reject → Production"

**Actions Triggered:**
1. **"Run Stress Tests"** → Calls `edge_utils.run_validation_stub()` → Writes to `experiment_run`, updates `edge_candidates.metrics_json`
2. **"Approve"** → Uses `attempt_write_action()` → Calls `edge_pipeline.promote_candidate_to_validated_setups()` → Writes to `validated_setups`, updates `edge_candidates.status` to 'APPROVED'
3. **"Reject"** → Uses `attempt_write_action()` → Updates `edge_candidates.status` to 'REJECTED'

**DB Tables Read:**
- `validation_queue` (pending candidates)
- `edge_candidates` (candidate details, metrics_json, robustness_json)
- `experiment_run` (validation history)

**DB Tables Written:**
- `validated_setups` (promoted strategies - CRITICAL)
- `edge_candidates` (status updates: APPROVED/REJECTED, metrics updates)
- `experiment_run` (validation results)

**Safety Wrappers:**
- ✅ "Approve" uses `attempt_write_action()` (runs `app_preflight.py` + `test_app_sync.py`)
- ✅ "Reject" uses `attempt_write_action()` (runs `app_preflight.py` + `test_app_sync.py`)

**CRITICAL WRITE PATH:**
- `Approve` → `edge_pipeline.promote_candidate_to_validated_setups()` → `INSERT INTO validated_setups`
- This is the ONLY path to write new production strategies
- Must maintain sync with `trading_app/config.py` (enforced by `test_app_sync.py`)

---

#### Tab 4: 🟢 PRODUCTION (Lines 2073-2330)

**Purpose:** Monitor approved strategies in real-time ("Are my strategies healthy?")

**Inputs:**
- None (read-only zone)

**Outputs:**
- Hero card showing current/upcoming ORB setup:
  - Time-aware status (ACTIVE now, UPCOMING in Xm Ys, STANDBY)
  - Strategy details (instrument, ORB time, RR, filters)
  - Performance metrics (ExpR, Win%, N)
  - Visual countdown timer (pulses when urgent)
- Strategy grid showing all active setups:
  - Setup cards with health indicators:
    - 🟢 HEALTHY: Recent ExpR within 10% of baseline
    - 🟡 WATCH: Recent ExpR degraded 10-25%
    - 🔴 FAILING: Recent ExpR degraded >25%
  - Performance summary (ExpR, Win%, Sample Size)
  - Trade plan (entry, SL, TP levels)
- Next-step rail showing: "Next: Use active setups in Live Trading"

**Actions Triggered:**
- None (read-only zone)

**DB Tables Read:**
- `validated_setups` (approved strategies)
- `daily_features` (recent performance for health derivation)

**DB Tables Written:**
- None

**Health Derivation Logic:**
- Implemented in `redesign_components.derive_strategy_health()`
- NEVER stored in database
- Always computed on-the-fly from recent performance data

---

### Other Applications

#### `trading_app/app_trading_terminal.py`

**Status:** Alternative UI (Terminal theme with Matrix aesthetic)
**Tabs:** Command, Monitor, Analysis, Intelligence
**Write Operations:** None documented in file
**Integration:** Uses same backend as app_canonical.py

#### `trading_app/app_simple.py`

**Purpose:** Simplified single-page app
**Write Operations:** Data update via `data_bridge.update_to_current()`
**Note:** Less feature-complete than app_canonical.py

#### `trading_app/app_research_lab.py`

**Purpose:** Research-focused interface (may be deprecated)
**Write Operations:** Not surveyed (older design)

---

## 2. DATA TABLES & REFERENCES

### Tables Present in DuckDB (`data/db/gold.db`)

**Raw Data Tables:**
- `bars_1m` - 1-minute OHLCV bars (MGC)
- `bars_1m_mpl` - 1-minute bars (MPL)
- `bars_1m_nq` - 1-minute bars (NQ)
- `bars_5m` - 5-minute bars (MGC, derived from bars_1m)
- `bars_5m_mpl` - 5-minute bars (MPL)
- `bars_5m_nq` - 5-minute bars (NQ)

**Feature Tables:**
- `daily_features` - Legacy daily feature table (replaced)
- `daily_features_v2` - Daily ORBs, session stats, indicators (MGC)
- `daily_features_v2_half` - Half-size SL tracking
- `daily_features_v2_mpl` - Daily features (MPL)
- `daily_features_v2_nq` - Daily features (NQ)
- `day_state_features` - Session state tracking

**Strategy Management Tables:**
- ✅ `validated_setups` - **CANONICAL PRODUCTION STRATEGIES** (id, instrument, orb_time, rr, sl_mode, orb_size_filter, win_rate, expected_r, sample_size, notes, created_at, updated_at, real_expected_r, realized_expectancy, avg_win_r, avg_loss_r, status)
- ✅ `validated_setups_archive` - Historical strategy versions (archive only, DO NOT USE in production)
- ✅ `validated_trades` - Trade journal
- ✅ `validation_queue` - Candidates pending validation

**Edge Discovery Tables:**
- ✅ `edge_registry` - Edge candidate registry (edge_id, status, instrument, session, orb_time, direction, trigger_definition, filters_applied, rr, sl_mode, test_window, failure_reason_code, last_tested_at, test_count, parent_edge_id, similarity_fingerprint, notes, created_by, created_at, updated_at)
- ✅ `edge_candidates` - Promoted edge candidates (candidate_id, name, instrument, hypothesis_text, filter_spec_json, test_config_json, metrics_json, robustness_json, slippage_assumptions_json, code_version, data_version, status, created_at_utc, approved_at, approved_by, promoted_validated_setup_id, notes)
- ✅ `search_candidates` - Search results cache
- ✅ `search_knowledge` - Parameter learning
- ✅ `search_memory` - Search history
- ✅ `search_runs` - Search execution tracking

**Execution & Testing Tables:**
- `execution_grid_configs` - Execution configuration presets
- `execution_grid_results` - Execution test results
- `execution_metrics` - Execution quality tracking
- `orb_exec_results` - ORB execution results
- `orb_robustness_results` - Robustness test results
- `orb_robustness_results_OLD` - Legacy robustness results
- `post_outcomes` - Post-trade outcome analysis
- `experiment_run` - Validation experiment tracking
- `experiment_run_backup` - Experiment backup

**Experimental Tables:**
- ✅ `experimental_strategies` - Parallel strategy source (bypasses config.py)

**AI & Memory Tables:**
- ✅ `ai_chat_history` - AI assistant chat log
- ✅ `ai_memory` - AI assistant memory
- ✅ `chat_history` - User chat history
- ✅ `learned_patterns` - Pattern learning (trading-memory skill)
- ✅ `session_state` - Session state tracking
- ✅ `trade_journal` - Trade execution journal

**ML Tables:**
- `ml_performance` - ML model performance
- `ml_predictions` - ML predictions

**Live Trading Tables:**
- `live_bars` - Live bar feed
- `live_journal` - Live trading journal
- `session_labels` - Session labels

**Archive Tables:**
- `_archive_orb_trades_1m_exec` - Archived 1m execution results
- `_archive_orb_trades_1m_exec_nofilters` - Archived 1m no-filter results
- `_archive_orb_trades_5m_exec` - Archived 5m execution results
- `_archive_orb_trades_5m_exec_nofilters` - Archived 5m no-filter results
- `_archive_orb_trades_5m_exec_nomax` - Archived 5m no-max results
- `_archive_orb_trades_5m_exec_orbr` - Archived 5m ORBR results

**Views:**
- `v_orb_trades` - ORB trades view
- `v_orb_trades_half` - Half-size ORB trades view

**What-If Analysis:**
- `what_if_snapshots` - What-if scenario snapshots

### Tables Referenced in Code (From `sql_schema_verify.py` output)

**Status:** ✅ ALL PASS - No orphaned table references found

**Verification:**
- 68 files scanned
- 274 SQL queries found
- All table references valid against database schema

---

### Missing Tables (None Found)

**Result:** No queries reference non-existent tables

**Method:** Ran `scripts/check/sql_schema_verify.py` - returned `[PASS] All table references are valid!`

---

## 3. WRITE PATH INVENTORY

### Write Operations by Function

#### **CRITICAL PRODUCTION WRITE:**

**1. Promote Candidate to validated_setups**
- **Function:** `edge_pipeline.promote_candidate_to_validated_setups()` (`trading_app/edge_pipeline.py:150+`)
- **UI Trigger:** Validation Gate → "Approve" button → `attempt_write_action()` wrapper
- **Table Written:** `validated_setups` (INSERT)
- **Safety Wrapper:** ✅ YES - Uses `attempt_write_action()` (runs `app_preflight.py` + `test_app_sync.py`)
- **Preflight Checks:**
  - `app_preflight.py` - Runs `forbidden_pattern_scan.py` + `execution_spec` checks
  - `test_app_sync.py` - Validates `validated_setups` ↔ `trading_app/config.py` sync
- **Sync Requirement:** MANDATORY - Must update `trading_app/config.py` immediately after
- **Risk:** 🔴 CRITICAL - Wrong values = real money loss in live trading

---

#### **CANDIDATE LIFECYCLE WRITES:**

**2. Create Edge Candidate**
- **Function:** `edge_utils.create_candidate()` (`trading_app/edge_utils.py:62`)
- **UI Trigger:** Research Lab (indirect - via auto_search_engine)
- **Table Written:** `edge_registry` (INSERT)
- **Safety Wrapper:** ❌ NO - Direct DB write
- **Risk:** 🟡 MEDIUM - Creates duplicates if edge_id collision

**3. Update Candidate Status (APPROVED/REJECTED)**
- **Function:** `edge_candidate_utils.set_candidate_status()` (`trading_app/edge_candidate_utils.py`)
- **UI Trigger:** Validation Gate → "Approve"/"Reject" → `attempt_write_action()` wrapper
- **Table Written:** `edge_candidates` (UPDATE status)
- **Safety Wrapper:** ✅ YES - Uses `attempt_write_action()`
- **Risk:** 🟢 LOW - Status change only, not production-impacting

**4. Send Candidate to Validation Queue**
- **Function:** Direct SQL INSERT in `app_canonical.py` (line ~1150)
- **UI Trigger:** Research Lab → "Send to Validation" → `attempt_write_action()` wrapper
- **Table Written:** `validation_queue` (INSERT)
- **Safety Wrapper:** ✅ YES - Uses `attempt_write_action()`
- **Risk:** 🟢 LOW - Queue management only

---

#### **SEARCH & DISCOVERY WRITES:**

**5. Auto Search Engine**
- **Function:** `auto_search_engine.py` - Multiple write paths
  - `_create_run_record()` → `search_runs` (INSERT)
  - `_update_run_record()` → `search_runs` (UPDATE)
  - `_remember_params()` → `search_memory` (INSERT ON CONFLICT UPDATE)
  - `_update_knowledge()` → `search_knowledge` (INSERT ON CONFLICT UPDATE)
  - Candidate creation → `search_candidates` (INSERT)
- **UI Trigger:** Research Lab → "Scan for Candidates"
- **Tables Written:** `search_runs`, `search_memory`, `search_knowledge`, `search_candidates`
- **Safety Wrapper:** ❌ NO - Direct DB writes
- **Risk:** 🟢 LOW - Research data only, not production-impacting

---

#### **AI ASSISTANT WRITES:**

**6. AI Chat History**
- **Function:** `ai_memory.save_message()` (`trading_app/ai_memory.py:53`)
- **UI Trigger:** AI chat interactions
- **Table Written:** `ai_chat_history` (INSERT)
- **Safety Wrapper:** ❌ NO - Direct DB write
- **Risk:** 🟢 LOW - Chat log only

**7. AI Memory Clear**
- **Function:** `ai_memory.clear_session()` (`trading_app/ai_memory.py:175`)
- **UI Trigger:** User-initiated clear
- **Table Written:** `ai_chat_history` (DELETE)
- **Safety Wrapper:** ❌ NO - Direct DB write
- **Risk:** 🟢 LOW - User-controlled data cleanup

---

#### **DATA MANAGEMENT WRITES:**

**8. Data Bridge Update**
- **Function:** `data_bridge.update_to_current()` (`trading_app/data_bridge.py:315`)
- **UI Trigger:** app_simple.py → "UPDATE DATA NOW" button
- **Tables Written:** `bars_1m`, `bars_5m`, `daily_features` (via backfill pipeline)
- **Safety Wrapper:** ❌ NO - Direct subprocess call to backfill scripts
- **Risk:** 🟡 MEDIUM - Can corrupt data if backfill fails mid-stream

---

#### **EXPERIMENTAL STRATEGIES (PARALLEL WRITE PATH):**

**9. Experimental Strategies Insert**
- **Function:** Direct SQL INSERT (not in app_canonical.py - in other tools)
- **UI Trigger:** Not in main app (external script)
- **Table Written:** `experimental_strategies`
- **Safety Wrapper:** ⚠️ PARTIAL - Has validation script (`check_experimental_strategies.py`) but NOT enforced in write path
- **Risk:** 🟡 MEDIUM - Bypasses config.py sync, can mislead users if bad data

---

### Write Path Summary Table

| # | Function | Table | UI Trigger | Safety Wrapper | Risk |
|---|----------|-------|------------|----------------|------|
| 1 | `promote_candidate_to_validated_setups()` | `validated_setups` | Validation Gate → Approve | ✅ YES | 🔴 CRITICAL |
| 2 | `create_candidate()` | `edge_registry` | Research Lab (indirect) | ❌ NO | 🟡 MEDIUM |
| 3 | `set_candidate_status()` | `edge_candidates` | Validation Gate → Approve/Reject | ✅ YES | 🟢 LOW |
| 4 | Direct INSERT | `validation_queue` | Research Lab → Send to Validation | ✅ YES | 🟢 LOW |
| 5 | `auto_search_engine` writes | `search_*` tables | Research Lab → Scan | ❌ NO | 🟢 LOW |
| 6 | `ai_memory.save_message()` | `ai_chat_history` | AI chat | ❌ NO | 🟢 LOW |
| 7 | `ai_memory.clear_session()` | `ai_chat_history` | User clear | ❌ NO | 🟢 LOW |
| 8 | `data_bridge.update_to_current()` | `bars_*`, `daily_features` | app_simple → Update Data | ❌ NO | 🟡 MEDIUM |
| 9 | External script | `experimental_strategies` | External | ⚠️ PARTIAL | 🟡 MEDIUM |

---

### Unprotected Write Paths (Require Safety Wrappers)

**CRITICAL:**
- ✅ `validated_setups` promotion - **PROTECTED** (uses `attempt_write_action()`)

**MEDIUM PRIORITY:**
- ❌ `edge_registry` creation - NO wrapper (can create duplicates)
- ❌ `data_bridge.update_to_current()` - NO wrapper (can corrupt data)
- ⚠️ `experimental_strategies` - PARTIAL validation (not enforced)

**LOW PRIORITY:**
- ❌ `search_*` table writes - NO wrapper (research data only)
- ❌ AI chat writes - NO wrapper (chat log only)

---

## 4. CANONICAL & CONTRACT INVENTORY

### CLAUDE.md (Main Canonical Document)

**Key Invariants:**

1. **LIVE TRADING TEST REQUIREMENTS (Lines 14-42)**
   - ANY code in LIVE mode MUST pass boundary + state tests
   - 80%+ test coverage for live trading code
   - Tests: `tests/boundary/`, `tests/state/`
   - NON-NEGOTIABLE

2. **STRATEGY FAMILY ISOLATION (Lines 46-78)**
   - All analysis applies ONLY to active STRATEGY_FAMILY
   - Cross-family inference FORBIDDEN
   - Families: ORB_L4, ORB_BOTH_LOST, ORB_RSI, ORB_NIGHT

3. **DATABASE AND CONFIG SYNCHRONIZATION (Lines 845-976)**
   - MANDATORY: NEVER update `validated_setups` without IMMEDIATELY updating `config.py`
   - Test command: `python test_app_sync.py` (MUST run after ANY strategy changes)
   - Zero tolerance for mismatches
   - Database filter value MUST equal config.py filter value (within 0.001 tolerance)

4. **CANONICAL REALIZED RR (Lines 637-696)**
   - System uses **realized RR with costs embedded**, not theoretical RR
   - Single source of truth: `pipeline/cost_model.py`
   - MGC: $10/point, $8.40 friction (commission $2.40 + spread $2.00 + slippage $4.00)
   - Apps read from `validated_setups.realized_expectancy` (NOT daily_features)

5. **EXECUTIONSPEC CHECKS (Lines 531-560)**
   - After ANY changes to execution spec system, run:
     - `python scripts/check/check_execution_spec.py`
     - `python test_app_sync.py`
     - `python scripts/check/app_preflight.py`

6. **EXPERIMENTAL STRATEGIES VALIDATION (Lines 953-976)**
   - When updating `experimental_strategies` table:
     - Run `python scripts/check/check_experimental_strategies.py`
     - Test scanner: `python trading_app/experimental_scanner.py`
     - ONLY PROCEED if validation passes

7. **DATABASE SCHEMA (Lines 711-756)**
   - **validated_setups** - ONLY table to query for trading decisions
   - **validated_setups_archive** - Archive only, DO NOT USE in production
   - Primary tables: bars_1m, bars_5m, daily_features, validated_setups

---

### REDESIGN_COMPLETE.md (UI Redesign Specification)

**Design Principles Applied (Lines 177-209):**

1. **Fail-Closed Safety**
   - ALL write actions use `attempt_write_action()`
   - Pre-flight checks run automatically (app_preflight.py + test_app_sync.py)
   - Red banner blocks unsafe actions

2. **UI-Derived Status**
   - Status NEVER stored in database
   - Always computed on-the-fly from metrics
   - PASS/WEAK/FAIL logic consistent

3. **Single Focus**
   - One candidate at a time in Validation Gate
   - No batch grids (overwhelm pattern removed)
   - Clear numbered steps (1→2→3)

4. **Guided Navigation**
   - Next-step rail shows where to go
   - Pipeline flow: RESEARCH → VALIDATION → PRODUCTION → LIVE

5. **CANONICAL Cost Model**
   - Position calculator reads from `cost_model.py`
   - NO hard-coded costs anywhere

**Forbidden Patterns REMOVED (Lines 211-218):**
- ❌ Tabs-within-tabs → ✅ Single-column layout
- ❌ Batch grids → ✅ One candidate at a time
- ❌ Hidden write paths → ✅ ALL use `attempt_write_action()`
- ❌ Stored status → ✅ UI-derived on-the-fly
- ❌ Hard-coded costs → ✅ Read from `cost_model.py`

---

### TERMINAL_REDESIGN_COMPLETE.md (Terminal Theme Specification)

**Aesthetic Direction (Lines 9-40):**
- Industrial/Utilitarian + Retro-Futuristic
- Bloomberg Terminal meets refined Cyberpunk
- Matrix-inspired green accents (#00ff41) on deep space black (#0a0e15)
- JetBrains Mono (terminal font) + Rajdhani (display font)
- Scan lines, glows, pulses for visual feedback

**Design System:**
- Monospace fonts for tabular alignment
- Dark theme (non-negotiable for 24/7 trading)
- Green/red for P&L, blue for neutral, yellow for warnings
- Information density without clutter

**Components:**
- `terminal_theme.py` - 1000+ lines CSS
- `terminal_components.py` - Reusable UI components
- `app_trading_terminal.py` - Complete redesigned app

---

### Extracted Invariants (Bulleted)

**Database:**
- ✅ `validated_setups` is THE canonical source for production strategies
- ✅ `validated_setups_archive` is archive only - NEVER use in production
- ✅ Database and config.py MUST sync (enforced by `test_app_sync.py`)
- ✅ All timestamps in UTC, session windows in Australia/Brisbane time

**Trading Logic:**
- ✅ ORB break detected when CLOSE outside range (not touch)
- ✅ Entry at FIRST 1-minute close outside ORB range
- ✅ RR values include transaction costs ($8.40 for MGC)
- ✅ Strategy family isolation - no cross-family inference

**UI/UX:**
- ✅ Write actions MUST use `attempt_write_action()` wrapper
- ✅ Status derived on-the-fly, NEVER stored
- ✅ Single focus (one candidate at a time)
- ✅ Fail-closed enforcement (block on safety check failure)

**Testing:**
- ✅ Live trading code requires 80%+ test coverage
- ✅ Boundary + state tests mandatory
- ✅ `test_app_sync.py` after ANY strategy changes
- ✅ `app_preflight.py` before ANY write action

**Cost Model:**
- ✅ `pipeline/cost_model.py` is ONLY source for friction values
- ✅ NO hard-coded costs anywhere
- ✅ MGC: $8.40 RT (commission $2.40 + spread $2.00 + slippage $4.00)

---

### Contradictions Within Documents

**None Found** - Documents are consistent.

**Potential Ambiguity:**
- CLAUDE.md mentions "daily_features (canonical table)" (line 725) but also says "Apps read from validated_setups.realized_expectancy (NOT daily_features)" (line 665)
  - **Resolution:** `daily_features` is canonical for historical ORB data (1R cache), but production apps read strategy-level metrics from `validated_setups`

---

## 5. TRADE LOGIC BOUNDARIES

### Where Trading Logic Is Implemented

**Core Trading Logic (DO NOT TOUCH IN UI/UX):**

1. **`pipeline/cost_model.py`**
   - Contract specifications (MGC: $10/point, $8.40 friction)
   - Honest accounting formulas
   - Realized RR calculations
   - **UI MUST NEVER:** Hard-code costs, override cost calculations

2. **`strategies/execution_engine.py`**
   - ORB entry/exit logic
   - Position sizing
   - R-multiple calculations
   - Trade execution simulation
   - **UI MUST NEVER:** Implement entry/exit rules, calculate R-multiples

3. **`pipeline/build_daily_features.py`**
   - ORB detection (high/low/size)
   - Break direction detection
   - Session statistics (Asia/London/NY)
   - RSI calculation
   - **UI MUST NEVER:** Calculate ORBs, compute indicators

4. **`trading_app/entry_rules.py`**
   - Entry rule implementations (limit_at_orb, 1st_close_outside, 5m_close_outside)
   - Entry price validation
   - Lookahead prevention
   - **UI MUST NEVER:** Implement entry logic

5. **`trading_app/execution_spec.py`**
   - ExecutionSpec system (orb_time, entry_rule, rr, sl_mode, confirm_tf)
   - Spec validation and hashing
   - Contract enforcement
   - **UI MUST NEVER:** Override spec validation

6. **`trading_app/execution_contract.py`**
   - Required columns/tables validation
   - Universal invariants (no lookahead, entry after ORB)
   - Structural consistency checks
   - **UI MUST NEVER:** Bypass contract validation

---

### Where Trade Logic Should NOT Be Touched By UI/UX

**Forbidden UI Actions:**

1. **Modifying Trade Calculations:**
   - ❌ Changing R-multiple formulas
   - ❌ Overriding transaction costs
   - ❌ Recalculating ORB levels
   - ❌ Adjusting realized expectancy

2. **Bypassing Safety Checks:**
   - ❌ Skipping `attempt_write_action()` wrapper
   - ❌ Ignoring preflight check failures
   - ❌ Writing directly to `validated_setups` without sync check

3. **Implementing Trading Rules:**
   - ❌ Adding entry logic in UI code
   - ❌ Creating exit rules in UI components
   - ❌ Computing position sizes without `cost_model.py`

4. **Database Integrity:**
   - ❌ Updating `validated_setups` without updating `config.py`
   - ❌ Writing to `validated_setups_archive` from UI
   - ❌ Manually setting status fields (status must be derived)

---

### Possible Overlaps (Areas of Concern)

**1. Position Calculator (`trading_app/position_calculator.py`)**
- **Status:** ✅ SAFE - Reads from `cost_model.py`, does not implement logic
- **Risk:** 🟢 LOW - Read-only calculator

**2. Live Scanner (`trading_app/live_scanner.py`)**
- **Status:** ⚠️ REVIEW NEEDED - Scans validated_setups and applies filters
- **Risk:** 🟡 MEDIUM - Could duplicate filter logic if not careful
- **Mitigation:** Should read filters from `validated_setups`, not reimplement

**3. Strategy Engine (`trading_app/strategy_engine.py`)**
- **Status:** ⚠️ REVIEW NEEDED - Evaluates strategies in real-time
- **Risk:** 🟡 MEDIUM - Could bypass canonical calculations
- **Mitigation:** Must delegate to `execution_engine.py` for trade logic

**4. Experimental Scanner (`trading_app/experimental_scanner.py`)**
- **Status:** ⚠️ REVIEW NEEDED - Parallel strategy source
- **Risk:** 🟡 MEDIUM - Bypasses config.py sync
- **Mitigation:** Has validation script but NOT enforced in write path

---

## 6. DRIFT & RISK SCAN

### TODO/FIXME/MOCK References

**Found 44 occurrences across 13 files:**

**Distribution:**
- `rule_engine.py`: 6 TODOs
- `risk_engine.py`: 5 TODOs
- `research_runner.py`: 10 TODOs
- `app_trading_terminal.py`: 3 TODOs (mock data placeholders)
- `strategy_discovery.py`: 5 TODOs
- `strategy_evaluation.py`: 2 TODOs
- `ml_dashboard.py`: 3 TODOs
- `mobile_ui.py`: 1 TODO
- `memory_integration.py`: 2 TODOs
- `market_scanner.py`: 2 TODOs
- `drift_monitor.py`: 1 FIXME
- `edge_utils.py`: 3 TODOs
- `data_loader.py`: 1 TODO

**High-Risk TODOs:**
1. `app_trading_terminal.py:542` - "Update P&L" - Uses `st.session_state.risk_manager.update_position_pnl()` (may bypass canonical P&L calculation)
2. `strategy_evaluation.py` - TODOs around evaluation logic (may duplicate trading logic)
3. `market_scanner.py` - TODOs around market scanning (may reimplement filter logic)

---

### Queries Referencing Non-Existent Tables

**Found:** 0 (zero)

**Method:** Ran `scripts/check/sql_schema_verify.py` - returned `[PASS] All table references are valid!`

---

### Code Paths Unprotected By Preflight Gates

**CRITICAL UNPROTECTED PATHS:**

1. **`edge_registry` Creation**
   - **Function:** `edge_utils.create_candidate()` (line 62)
   - **Write:** `INSERT INTO edge_registry`
   - **Protection:** ❌ NONE - Direct DB write
   - **Risk:** 🟡 MEDIUM - Can create duplicate candidates

2. **Data Bridge Update**
   - **Function:** `data_bridge.update_to_current()` (line 315)
   - **Write:** Subprocess calls to backfill scripts → `bars_*`, `daily_features`
   - **Protection:** ❌ NONE - Direct subprocess call
   - **Risk:** 🟡 MEDIUM - Can corrupt data if backfill fails

3. **Auto Search Engine Writes**
   - **Functions:** Multiple in `auto_search_engine.py`
   - **Writes:** `search_runs`, `search_memory`, `search_knowledge`, `search_candidates`
   - **Protection:** ❌ NONE - Direct DB writes
   - **Risk:** 🟢 LOW - Research data only

4. **AI Memory Writes**
   - **Functions:** `ai_memory.save_message()`, `ai_memory.clear_session()`
   - **Writes:** `ai_chat_history`
   - **Protection:** ❌ NONE - Direct DB writes
   - **Risk:** 🟢 LOW - Chat log only

5. **Experimental Strategies**
   - **Write:** Direct SQL INSERT (external script)
   - **Table:** `experimental_strategies`
   - **Protection:** ⚠️ PARTIAL - Has validation script (`check_experimental_strategies.py`) but NOT enforced
   - **Risk:** 🟡 MEDIUM - Bypasses config.py sync

---

### UI Logic That Bypasses Canonical Checks

**NONE FOUND** - All production write paths use `attempt_write_action()` wrapper.

**Verified:**
- ✅ Research Lab → "Send to Validation" uses `attempt_write_action()`
- ✅ Validation Gate → "Approve" uses `attempt_write_action()`
- ✅ Validation Gate → "Reject" uses `attempt_write_action()`

**Potential Bypass Risk:**
- ⚠️ If future UI modifications add write paths without using `attempt_write_action()`, they will bypass safety checks
- ⚠️ `experimental_strategies` table is a parallel write path that bypasses config.py sync (documented but not enforced)

---

### Forbidden Patterns Found

**From `scripts/check/forbidden_pattern_scan.py`:**

**Result:** ✅ PASS - No forbidden patterns detected

**Scanned Patterns (19 total):**
- Tabs-within-tabs
- Batch processing grids
- Hard-coded costs
- Stored status values
- Hidden write paths
- Direct database mutations
- Unsafe SQL concatenation
- Unvalidated user input
- Missing error handling
- Lookahead bias
- Overfitting indicators
- Data snooping
- Survivorship bias
- Magic numbers
- God objects
- Circular dependencies
- Global state mutation
- Thread-unsafe code
- SQL injection vectors

---

## 7. GAPS & BLOCKERS

### Gaps Preventing Safe Automation

**1. Experimental Strategies Validation Not Enforced**
- **Gap:** `experimental_strategies` table has validation script (`check_experimental_strategies.py`) but it's NOT called in write path
- **Risk:** Bad data can enter production UI (e.g., ExpR = 2.5R typo instead of 0.25R)
- **Blocker:** No pre-flight check for experimental strategy writes
- **Solution:** Add `attempt_write_action()` wrapper to experimental strategy insertion flow

**2. Data Bridge Update Has No Safety Wrapper**
- **Gap:** `data_bridge.update_to_current()` calls backfill scripts without validation
- **Risk:** Partial backfill failure can corrupt database (missing days, wrong ORBs)
- **Blocker:** No rollback mechanism if backfill fails mid-stream
- **Solution:** Add transaction wrapper + validation checks before/after backfill

**3. Edge Registry Creation Has No Deduplication Check**
- **Gap:** `edge_utils.create_candidate()` checks for existing edge_id but doesn't prevent race conditions
- **Risk:** Parallel candidate creation can insert duplicates
- **Blocker:** No database-level UNIQUE constraint on edge_id
- **Solution:** Add UNIQUE constraint to edge_registry.edge_id column

**4. No Test Coverage for UI Write Paths**
- **Gap:** Write paths tested manually, no automated UI test suite
- **Risk:** Regressions can break safety wrappers without detection
- **Blocker:** No CI/CD pipeline for UI tests
- **Solution:** Add Streamlit UI tests using `st.testing` framework

**5. Status Derivation Logic Not Tested**
- **Gap:** `redesign_components.derive_candidate_status()` and `derive_strategy_health()` have no unit tests
- **Risk:** Status logic bugs can mislead users (e.g., showing PASS when should be FAIL)
- **Blocker:** No test coverage for derivation functions
- **Solution:** Add unit tests for all status derivation logic

---

### Things That MUST Exist Before Safe Automation

**1. Automated UI Test Suite**
- **Required:** Streamlit UI tests for all write paths
- **Coverage:** All buttons, all forms, all validation flows
- **Enforcement:** CI/CD blocks merge if UI tests fail
- **Status:** ❌ MISSING

**2. Database Transaction Wrappers**
- **Required:** All multi-step write operations must be wrapped in transactions
- **Example:** Promote candidate → INSERT validated_setups + UPDATE edge_candidates (must be atomic)
- **Status:** ⚠️ PARTIAL - Some functions use transactions, not all

**3. Rollback Mechanisms**
- **Required:** Ability to rollback failed writes (especially data backfills)
- **Example:** If backfill fails on day 5 of 10, rollback days 1-4
- **Status:** ❌ MISSING

**4. Write Path Monitoring**
- **Required:** Logging + alerting for all database writes
- **Example:** Log every INSERT/UPDATE/DELETE to audit trail
- **Status:** ⚠️ PARTIAL - Logging exists but not comprehensive

**5. Config Sync Enforcement at Database Level**
- **Required:** Database trigger or constraint to prevent validated_setups writes without config.py sync
- **Example:** Trigger that checks if config.py was updated in last 60 seconds
- **Status:** ❌ MISSING (currently relies on test_app_sync.py being run manually)

**6. Experimental Strategies Pre-Flight Check**
- **Required:** `attempt_write_action()` wrapper for experimental_strategies writes
- **Example:** Run `check_experimental_strategies.py` before allowing INSERT
- **Status:** ❌ MISSING

**7. Live Scanner Filter Validation**
- **Required:** Test suite verifying `live_scanner.py` uses validated_setups filters (not reimplementing)
- **Example:** Unit tests comparing live_scanner filter results vs validated_setups specs
- **Status:** ❌ MISSING

**8. Strategy Engine Delegation Tests**
- **Required:** Tests verifying `strategy_engine.py` delegates to `execution_engine.py` (not reimplementing)
- **Example:** Mock execution_engine, verify strategy_engine calls it with correct params
- **Status:** ❌ MISSING

---

### Recommended Mitigations (Priority Order)

**P0 - CRITICAL (Must fix before any automation):**
1. Add UNIQUE constraint to `edge_registry.edge_id`
2. Add transaction wrapper to `edge_pipeline.promote_candidate_to_validated_setups()`
3. Add automated UI tests for all write paths (Research Lab, Validation Gate)
4. Add unit tests for status derivation logic

**P1 - HIGH (Should fix before production deployment):**
5. Add `attempt_write_action()` wrapper to experimental_strategies writes
6. Add rollback mechanism to `data_bridge.update_to_current()`
7. Add write path monitoring (audit trail logging)
8. Add delegation tests for `strategy_engine.py` and `live_scanner.py`

**P2 - MEDIUM (Nice to have):**
9. Add database trigger to enforce config.py sync
10. Add CI/CD pipeline for UI tests
11. Add comprehensive error handling for all DB writes
12. Add health checks for all write paths

---

## SUMMARY

**App Maturity Assessment:**

✅ **GOOD:**
- Clean 3-zone architecture (Research → Validation → Production → Live)
- Safety wrappers in place for critical write paths (`attempt_write_action()`)
- No SQL injection vulnerabilities (uses parameterized queries)
- All table references valid (no orphaned queries)
- No forbidden patterns detected
- Database/config sync enforced by `test_app_sync.py`

⚠️ **NEEDS IMPROVEMENT:**
- 5 unprotected write paths (edge_registry, data_bridge, auto_search, ai_memory, experimental_strategies)
- No automated UI test suite
- Status derivation logic not tested
- No database-level sync enforcement
- No rollback mechanisms for multi-step writes

🔴 **CRITICAL GAPS:**
- Experimental strategies bypass config.py sync (documented but not enforced)
- Data backfill has no transaction wrapper (can corrupt database)
- No race condition protection for edge candidate creation
- Live scanner and strategy engine may reimplement logic (needs delegation tests)

**Recommendation:**
- ✅ Safe for MANUAL use (with `test_app_sync.py` discipline)
- ❌ NOT safe for AUTOMATED deployment without fixes
- 🚧 Requires P0 mitigations before production automation

**Next Steps:**
1. Fix P0 mitigations (UNIQUE constraint, transaction wrappers, UI tests, status tests)
2. Add delegation tests for live_scanner and strategy_engine
3. Implement write path monitoring
4. Add rollback mechanisms
5. Deploy automated test suite in CI/CD
6. Consider database trigger for config sync enforcement

---

**Document End**
