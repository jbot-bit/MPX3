# UPDATE22 PASS 1 AUDIT REPORT
## PB Family Grid Generation - Infrastructure Assessment

**Date:** 2026-01-31
**Scope:** Self-detect existing PB-related support, confirm naming/time helpers, produce Impact Map
**Mode:** AUDIT ONLY - NO CODE CHANGES

---

## 1. EXISTING CANDIDATE GENERATION INFRASTRUCTURE

### 1.1 Entry Points (Where Candidates Are Created)

**Primary Path:** `edge_pipeline.py::create_edge_candidate()`
- **Location:** `trading_app/edge_pipeline.py:349`
- **Function:** Creates new candidate in `edge_candidates` table with DRAFT status
- **Schema:** Requires name, instrument, hypothesis_text, filter_spec, test_config, metrics, slippage_assumptions, code_version, data_version, actor
- **Write Method:** Direct DB write with `conn.execute()` + `conn.commit()`
- **⚠️ CRITICAL:** Does NOT use `attempt_write_action()` wrapper (inconsistency with UI writes)

**Alternative Path:** `auto_search_engine.py::AutoSearchEngine`
- **Location:** `trading_app/auto_search_engine.py`
- **Function:** Generates parameter grid, scores candidates, writes to `search_candidates` table
- **Write Method:** Direct DB writes (no wrapper)
- **Note:** `search_candidates` is staging area, candidates must be manually promoted to `edge_candidates`

**UI Path:** `app_research_lab.py` (calls `edge_pipeline.create_edge_candidate()`)
- **Location:** `trading_app/app_research_lab.py`
- **Function:** Manual candidate creation from UI
- **Write Method:** Calls `edge_pipeline.create_edge_candidate()` directly

### 1.2 Write Wrapper Usage Analysis

**Wrapper Definition:** `redesign_components.py::attempt_write_action()`
- **Location:** `trading_app/redesign_components.py:28`
- **Signature:** `attempt_write_action(action_name, callback, *args, **kwargs) -> bool`
- **Function:** Fail-closed wrapper that runs preflight checks before writes
- **Checks:** app_preflight.py, test_app_sync.py
- **Blocks:** If either check fails, shows red banner and blocks write

**Current Usage:**
- ✅ Used in `app_canonical.py` for UI write operations
- ❌ NOT used in `edge_pipeline.create_edge_candidate()`
- ❌ NOT used in `auto_search_engine` writes
- ❌ NOT used in `app_research_lab.py` candidate creation

**⚠️ CONSISTENCY GAP:** Some writes are wrapped (UI buttons), some are not (programmatic candidate creation)

**RECOMMENDATION:** For UPDATE22, continue existing pattern (no wrapper for edge_pipeline) since:
1. Edge candidates are DRAFT status (not production)
2. Approval gate happens later (promotion to validated_setups uses wrappers)
3. Changing wrapper usage is scope creep (not part of UPDATE22)

### 1.3 Deduplication Strategy

**Existing Mechanisms:**
1. `auto_search_engine.py::compute_param_hash()` - SHA256 hash of params
2. `edge_utils.py::generate_edge_id()` - SHA256 hash for edge_registry
3. `search_memory` table - Tracks tested parameter combinations

**For PB Grid:**
- Use `generate_edge_id()` from edge_utils
- Hash inputs: instrument, orb_time, direction, trigger_definition (built from tokens), filters_applied, rr, sl_mode
- Check if edge_id exists in `edge_candidates` before insert
- Skip if exists (no duplicates)

---

## 2. TIME USAGE CONFIRMATION

### 2.1 time_spec.py (Canonical Time Source)

**Location:** `trading_app/time_spec.py` (created in UPDATE21)

**ORBS List:**
```python
ORBS = ['0900', '1000', '1100', '1800', '2300', '0030']
```

**For PB Grid:**
- ✅ Import from `time_spec.ORBS`
- ✅ Filter to subset: `['0900', '1000', '1100']` (as specified in UPDATE22)
- ✅ No hardcoding required

**Code Pattern:**
```python
from trading_app.time_spec import ORBS

# Use subset for PB grid
pb_orb_times = [orb for orb in ORBS if orb in ['0900', '1000', '1100']]
```

---

## 3. NAMING HELPERS CONFIRMATION

### 3.1 generate_strategy_name() (UPDATE21)

**Location:** `trading_app/edge_utils.py:61`

**Current Signature:**
```python
def generate_strategy_name(
    instrument: str,
    orb_time: str,
    direction: str,
    entry_rule: str,
    sl_mode: str,
    version: int = 1
) -> str
```

**Current Format:** `{INSTRUMENT}_{ORB}_{DIR}_{ENTRY}_{STOP}_v{VER}`
- Example: `"MGC_1000_LONG_1ST_ORB_LOW_v1"`

**PB Family Format (UPDATE22 requirement):**
- Format: `"{INSTR}_{ORB}_{DIR}_PB_{ENTRY}_{STOP}_v1"`
- Example: `"MGC_1000_LONG_PB_RETEST_ORB_STOP_ORB_OPP_v1"`

**⚠️ REQUIRED CHANGE:** Extend `generate_strategy_name()` to support PB family
- Add optional `family` parameter (default None for backward compatibility)
- If `family == 'PB'`, insert `_PB_` after direction
- Map PB entry_token to short form (RETEST_ORB → RETEST, MID_PULLBACK → MID)
- Map PB stop_token to short form (STOP_ORB_OPP → ORB_OPP, STOP_SWING → SWING)

**Backward Compatibility:** ✅ Existing calls work unchanged (family=None)

### 3.2 generate_edge_id() (Deterministic Hashing)

**Location:** `trading_app/edge_utils.py:21`

**Current Signature:**
```python
def generate_edge_id(
    instrument: str,
    orb_time: str,
    direction: str,
    trigger_definition: str,
    filters_applied: Dict,
    rr: float,
    sl_mode: str
) -> str
```

**For PB Grid:**
- ✅ Use as-is (no changes needed)
- `trigger_definition` = human-readable description built from PB tokens
- Example: `"Pullback to ORB mid, close confirmation, stop at ORB opposite"`

---

## 4. PB TOKEN STORAGE STRATEGY

### 4.1 edge_candidates Schema

**Relevant Fields:**
```sql
filter_spec_json JSON NOT NULL,     -- Entry/stop/target rules, filters, thresholds
feature_spec_json JSON,             -- Feature definitions, ORB params, indicators
metrics_json JSON,                  -- Win rate, avg R, total R, n, drawdown, etc.
```

**PB Tokens to Store:**
- `entry_token`: RETEST_ORB, MID_PULLBACK
- `confirm_token`: CLOSE_CONFIRM, WICK_REJECT
- `stop_token`: STOP_ORB_OPP, STOP_SWING
- `tp_token`: TP_FIXED_R_1_0, TP_FIXED_R_1_5, TP_FIXED_R_2_0

**Storage Options:**

**Option A (RECOMMENDED): Store in filter_spec_json**
```json
{
  "entry_token": "RETEST_ORB",
  "confirm_token": "CLOSE_CONFIRM",
  "stop_token": "STOP_ORB_OPP",
  "tp_token": "TP_FIXED_R_1_5",
  "sl_mode": "ORB_LOW",
  "orb_size_filter": null,
  "atr_filter": null
}
```

**Pros:**
- Semantically correct (entry/stop/target ARE filters)
- No schema changes required
- Backward compatible (existing code ignores unknown keys)

**Cons:**
- Mixing legacy fields (sl_mode) with new tokens (entry_token)

**Option B: Store in feature_spec_json**
```json
{
  "family": "PB",
  "entry_token": "RETEST_ORB",
  ...
}
```

**Pros:**
- Cleaner separation

**Cons:**
- Semantically wrong (tokens define strategy, not features)
- feature_spec_json is optional (NULL allowed)

**Option C: Add new columns**
- ❌ FORBIDDEN by UPDATE22 constraints (no schema changes)

**DECISION: Use Option A (filter_spec_json)**

### 4.2 Hypothesis Text Format

**Template:**
```
"PB Family: {ENTRY_TOKEN} entry, {CONFIRM_TOKEN} confirmation, {STOP_TOKEN} stop, {TP_TOKEN} target. Grid-generated candidate for {INSTRUMENT} {ORB_TIME} ORB."
```

**Example:**
```
"PB Family: RETEST_ORB entry, CLOSE_CONFIRM confirmation, STOP_ORB_OPP stop, TP_FIXED_R_1_5 target. Grid-generated candidate for MGC 1000 ORB."
```

---

## 5. IMPACT MAP

### 5.1 Files to Modify

#### **File 1: trading_app/edge_utils.py** (EXTEND)
**Changes:**
- Extend `generate_strategy_name()` to support PB family
- Add `family` parameter (default None)
- Add token-to-short-form mappings for PB entry/stop tokens

**Expected Diff:** ~40 lines (maps + conditional logic)

**Risk:** LOW (backward compatible, no breaking changes)

#### **File 2: trading_app/pb_grid_generator.py** (NEW)
**Purpose:** Generate 144 PB parameter combinations

**Functions:**
- `generate_pb_grid(instrument, orb_times) -> List[Dict]`
- `create_pb_candidate(combo, actor) -> Optional[int]`
- `generate_pb_batch(actor) -> Dict[str, Any]`

**Expected Size:** ~200 lines

**Risk:** LOW (new file, no dependencies on existing code)

**Components:**
1. Token definitions (entry/confirm/stop/tp)
2. Grid generation (3 ORBs × 2 dirs × 2 entry × 2 confirm × 2 stop × 3 tp = 144)
3. Deduplication check (via generate_edge_id)
4. Candidate creation (calls edge_pipeline.create_edge_candidate)
5. Batch reporting (generated vs skipped counts)

#### **File 3: trading_app/app_canonical.py** (OPTIONAL UI HOOK)
**Purpose:** Add "Generate PB Grid" button to Research tab

**Changes:**
- Import `pb_grid_generator`
- Add button in Research section
- Call `generate_pb_batch(actor='user')`
- Display results (candidates created, duplicates skipped)

**Expected Diff:** ~30 lines

**Risk:** LOW (isolated UI addition)

**Note:** Can be deferred to manual script invocation if UI work is out of scope

### 5.2 Tables Written

**Primary Table:** `edge_candidates`
- Inserts: Up to 144 rows (minus duplicates)
- Status: All set to 'DRAFT'
- Write Method: `edge_pipeline.create_edge_candidate()` (no wrapper)

**No New Tables:** ✅ Uses existing lifecycle tables

### 5.3 Write Wrappers

**Decision:** Continue existing pattern (no wrapper for edge_pipeline)

**Rationale:**
1. edge_pipeline.create_edge_candidate() does not currently use attempt_write_action
2. Candidates are DRAFT status (not production-critical)
3. Promotion to validated_setups happens later with full validation
4. Changing wrapper pattern is out of scope for UPDATE22

**Alternative (if user requires wrapper):**
- Wrap batch operation in attempt_write_action at UI level (app_canonical.py button)
- Pass pb_grid_generator.generate_pb_batch as callback
- This adds fail-closed protection at invocation point

---

## 6. VALIDATION QUEUE SHORT-LIST RULE

### 6.1 Current Scoring Infrastructure

**auto_search_engine.py has:**
- `_score_candidate()` - Uses daily_features for fast proxy scoring
- Metrics: profitable_trade_rate, target_hit_rate, expected_r, sample_size
- Thresholds: min_sample_size=30, min_expected_r=0.15

### 6.2 PB Grid Scoring Options

**Option A (CONSERVATIVE - RECOMMENDED):** Queue NONE
- Generate all 144 candidates as DRAFT
- Manual selection in UI (user reviews and queues best)
- No automatic scoring (PB patterns not yet backtested)

**Option B (OPTIMISTIC):** Queue top N based on proxy
- Use daily_features ORB outcomes as proxy
- Filter to candidates with sample_size >= 30, expected_r >= 0.15
- Queue top 5 by expected_r
- Risk: Proxy may not reflect PB-specific behavior

**RECOMMENDATION: Option A**
- PB family is NEW (no historical validation)
- entry_token/confirm_token mechanics require backtest validation
- Better to generate as DRAFT and let user queue manually after review

### 6.3 Implementation

**For PASS 2:**
- Generate all 144 candidates
- Set all to status='DRAFT'
- Queue count: 0 (manual queuing via UI)
- Report: "Generated N candidates (M duplicates skipped), 0 queued for validation"

---

## 7. STOP CONDITIONS CHECK

### 7.1 Forbidden Paths

**Constraints:** Do NOT edit:
- `strategies/` ❌
- `pipeline/` ❌
- `trading_app/cost_model.py` ❌
- `trading_app/entry_rules.py` ❌
- `trading_app/execution_engine.py` ❌
- `schema/migrations/` ❌

**Proposed Changes:**
- ✅ `trading_app/edge_utils.py` (UI_ONLY scope, allowed)
- ✅ `trading_app/pb_grid_generator.py` (new file, UI_ONLY scope)
- ✅ `trading_app/app_canonical.py` (UI file, allowed)

**Status:** ✅ NO FORBIDDEN PATHS TOUCHED

### 7.2 Schema Changes

**Constraints:** No new DB tables or migrations

**Proposed Changes:**
- ✅ Uses existing `edge_candidates` table
- ✅ Stores PB tokens in existing `filter_spec_json` field (JSON flexibility)

**Status:** ✅ NO SCHEMA CHANGES

### 7.3 Time Literals

**Constraints:** Must import from time_spec.py

**Proposed Changes:**
- ✅ Import `time_spec.ORBS`
- ✅ Filter to subset `['0900', '1000', '1100']`

**Status:** ✅ NO HARDCODED TIME LITERALS

### 7.4 File Diff Size

**Constraints:** No file > 200 lines diff

**Proposed Changes:**
- `edge_utils.py`: ~40 lines (extend function)
- `pb_grid_generator.py`: ~200 lines (new file, total size)
- `app_canonical.py`: ~30 lines (optional UI hook)

**Status:** ✅ ALL DIFFS < 200 LINES

---

## 8. EXPECTED GRID SIZE

**Parameters:**
- instrument: MGC (1)
- orb_time: 3 (['0900', '1000', '1100'])
- direction: 2 (LONG, SHORT)
- entry_token: 2 (RETEST_ORB, MID_PULLBACK)
- confirm_token: 2 (CLOSE_CONFIRM, WICK_REJECT)
- stop_token: 2 (STOP_ORB_OPP, STOP_SWING)
- tp_token: 3 (TP_FIXED_R_1_0, TP_FIXED_R_1_5, TP_FIXED_R_2_0)

**Total Combinations:** 1 × 3 × 2 × 2 × 2 × 2 × 3 = **144 candidates**

**Expected Dedupe Rate:** Unknown (depends on existing candidates)
- First run: 144 inserts
- Re-run: 0 inserts (all skipped as duplicates)

---

## 9. FILTERS (OPTIONAL DIMENSIONS)

### 9.1 Requested Optional Filters

**From UPDATE22:**
- atr_bucket: LOW/MID/HIGH
- min_orb_range_bucket: MID/HIGH

**Constraint:** Only if existing feature exists; otherwise skip (fail-closed)

### 9.2 Feature Availability Check

**daily_features Schema:**
- ✅ `orb_{time}_size` exists (can derive range buckets)
- ✅ `atr_20d` exists (can derive ATR buckets)

**Bucket Definitions (if implemented):**

**ATR Buckets:**
- LOW: atr_20d < 50
- MID: 50 <= atr_20d < 70
- HIGH: atr_20d >= 70

**ORB Range Buckets:**
- MID: 0.04 <= orb_size < 0.08 (40-80 points)
- HIGH: orb_size >= 0.08 (80+ points)

### 9.3 Implementation Decision

**For PASS 2:**
- **SKIP FILTERS** (keep grid simple, 144 candidates)
- Rationale: PB family is exploratory, filters add 2-3x candidates (288-432 total)
- Filters can be added later if PB family proves promising

**Alternative (if user requires filters):**
- Add as 2nd phase after base 144 candidates validated
- Regenerate grid with filter dimensions
- Expected size: 144 × 3 (ATR) × 2 (range) = 864 candidates

---

## 10. GATES TO RUN (PASS 2)

**Mandatory Checks (in order):**
1. `python scripts/check/app_preflight.py`
2. `python test_app_sync.py`
3. `pytest -q`
4. `python scripts/check/check_time_literals.py` (confirm 0 NEW structural violations)

**Expected Results:**
- app_preflight: PASS (scope_guard allows edge_utils.py, pb_grid_generator.py, app_canonical.py)
- test_app_sync: PASS (no validated_setups changes)
- pytest: PASS (no test changes)
- check_time_literals: PASS (imports from time_spec, no new hardcoded literals)

---

## 11. PASS 2 IMPLEMENTATION PLAN (PREVIEW)

### Phase 1: Extend Naming Helper (~15 min)
1. Modify `edge_utils.py::generate_strategy_name()`
2. Add `family` parameter (default None)
3. Add PB token mappings
4. Test: `generate_strategy_name('MGC', '1000', 'LONG', 'RETEST', 'ORB_OPP', family='PB')`
5. Expected output: `"MGC_1000_LONG_PB_RETEST_ORB_OPP_v1"`

### Phase 2: Create PB Grid Generator (~45 min)
1. Create `trading_app/pb_grid_generator.py`
2. Define token constants
3. Implement `generate_pb_grid()` (144 combinations)
4. Implement `create_pb_candidate()` (with dedupe check)
5. Implement `generate_pb_batch()` (batch orchestration)
6. Test: Generate grid, print first 5 candidates

### Phase 3: Wire into UI (OPTIONAL) (~15 min)
1. Modify `app_canonical.py` Research tab
2. Add "Generate PB Grid" button
3. Call `pb_grid_generator.generate_pb_batch(actor='user')`
4. Display results (N generated, M skipped)
5. Test: Click button, verify candidates appear in edge_candidates table

### Phase 4: Run Gates (~10 min)
1. Run all 4 mandatory checks
2. Fix any issues
3. Verify PASS on all

### Phase 5: Evidence Report (~10 min)
1. Query `SELECT COUNT(*) FROM edge_candidates WHERE instrument='MGC' AND name LIKE '%PB%'`
2. Document: N candidates generated, M skipped (dedupe), 0 queued
3. List files changed with line counts
4. Confirm tables written (edge_candidates only)
5. Confirm gates passed

**Total Estimated Time:** 95 minutes (~1.5 hours)

---

## 12. RECOMMENDATIONS

### 12.1 Primary Recommendations

1. ✅ **PROCEED with PASS 2** - All infrastructure exists, no forbidden changes required
2. ✅ **Use edge_pipeline.create_edge_candidate()** - Existing function works, no wrapper needed
3. ✅ **Store tokens in filter_spec_json** - No schema changes, backward compatible
4. ✅ **Extend generate_strategy_name()** - Add PB family support, maintain backward compatibility
5. ✅ **Skip filters for first pass** - Keep grid at 144 candidates (simple validation)
6. ✅ **Queue NONE for validation** - Manual selection by user (PB patterns untested)

### 12.2 Optional Enhancements (Out of Scope)

1. ⚠️ Add attempt_write_action wrapper to edge_pipeline (consistency fix, not required)
2. ⚠️ Add ATR/range filters (expands grid to 864 candidates, defer)
3. ⚠️ Auto-queue top N (requires proxy validation, risky)

### 12.3 Risk Assessment

**Overall Risk:** ✅ LOW

**Risk Factors:**
- ✅ No forbidden paths touched
- ✅ No schema changes
- ✅ No formula changes
- ✅ Uses existing write patterns
- ✅ All diffs < 200 lines
- ✅ Backward compatible naming helper

**Confidence:** HIGH - Implementation is straightforward extension of existing patterns

---

## 13. APPROVAL REQUEST

**PASS 1 AUDIT COMPLETE.**

**Ready for PASS 2 (BUILD)?**

**If YES:**
- Proceed with Phase 1-5 implementation plan
- Expected duration: ~1.5 hours
- Expected output: 144 PB candidates in edge_candidates table (DRAFT status)

**If NO:**
- Please specify concerns or required changes
- Will adjust plan accordingly

**Awaiting user approval to proceed to PASS 2.**
