# Edge System Unification Audit

**Date**: 2026-01-20
**Repo**: `C:\Users\sydne\OneDrive\myprojectx2_cleanpush`
**Status**: MULTIPLE COMPETING SYSTEMS DETECTED

---

## STEP 1 — FORENSIC SCAN

### A) Entry Points Confirmed

✅ `trading_app/app_trading_hub.py` (66KB) - Main Streamlit app
✅ `trading_app/app_mobile.py` (21KB) - Mobile UI

### B) Edge-Related Inventory

| Path | What It Does | Reads DB? | Writes DB? | Depends On | Imported By App? | Classification |
|------|--------------|-----------|------------|------------|------------------|----------------|
| **PRODUCTION (Source of Truth)** |
| `validated_setups` (DB table) | **19 production strategies** - authoritative source | N/A | N/A | N/A | YES (via setup_detector.py) | **PRODUCTION** |
| `trading_app/config.py` | Strategy filters (MGC_ORB_SIZE_FILTERS, etc.) - must sync with validated_setups | NO | NO | validated_setups | YES (all apps) | **PRODUCTION** |
| `test_app_sync.py` | **SYNC ENFORCER** - validates validated_setups ↔ config.py match | YES (read) | NO | validated_setups, config.py | NO (pre-commit check) | **PRODUCTION** |
| `trading_app/setup_detector.py` | Reads validated_setups, detects live setups | YES (read) | NO | validated_setups | YES (app_trading_hub) | **PRODUCTION** |
| `trading_app/strategy_engine.py` | Executes live trades based on validated_setups | YES (read) | NO | validated_setups | YES (app_trading_hub) | **PRODUCTION** |
| **PRODUCTION (Approval/UI)** |
| `trading_app/edge_candidates_ui.py` (305 lines) | UI for reviewing/approving edge candidates | YES (read) | NO | edge_candidates | YES (app_trading_hub) | **PRODUCTION** |
| `trading_app/edge_candidate_utils.py` (263 lines) | `approve_edge_candidate()`, `set_candidate_status()` | YES | YES (writes) | edge_candidates | YES (edge_candidates_ui) | **PRODUCTION** |
| `approve_candidate.py` (64 lines) | CLI script to approve candidates | YES | YES (writes) | edge_candidates | NO (standalone CLI) | **PRODUCTION** |
| `verify_edge_candidates.py` (6 lines) | Quick DB check script | YES (read) | NO | edge_candidates | NO (dev tool) | **PRODUCTION** |
| **NEWLY CREATED (This Session)** |
| `trading_app/edge_pipeline.py` (410 lines) | **PROMOTION ENGINE** - promotes APPROVED candidates → validated_setups | YES | YES (writes) | edge_candidates, validated_setups | NO (not yet integrated) | **PRODUCTION (NEW)** |
| `tests/test_edge_promotion.py` (453 lines) | Tests for edge_pipeline promotion workflow | YES | YES (test DB) | edge_pipeline | NO (tests only) | **PRODUCTION (NEW)** |
| **REBUILD TOOLS** |
| `strategies/populate_validated_setups.py` (331 lines) | **REBUILD TOOL** - deletes + rebuilds all validated_setups from hardcoded dict | YES | YES (DELETE + INSERT) | None (hardcoded) | NO (manual admin) | **DEPRECATED** |
| `strategies/validated_strategies.py` (dict) | Hardcoded MGC/NQ/MPL strategy definitions | NO | NO | None | YES (by populate_validated_setups) | **DEPRECATED** |
| **RESEARCH (EDE System)** |
| `research/ede/init_ede_schema.py` (395 lines) | Creates 6 EDE tables (edge_candidates_raw, edge_manifest, etc.) | YES | YES (CREATE TABLE) | None | NO (research setup) | **RESEARCH** |
| `research/ede/lifecycle_manager.py` (614 lines) | EDE orchestrator - hard gate flow IDEA→SYNC | YES | YES (writes) | edge_candidates_raw, edge_manifest | NO (research) | **RESEARCH** |
| `research/ede/generator_brute.py` (509 lines) | Brute parameter search (1.78M combinations) | YES | YES (writes) | edge_candidates_raw | NO (research) | **RESEARCH** |
| `research/ede/backtest_engine.py` (670 lines) | Zero-lookahead backtesting engine | YES (read bars) | NO | bars_1m, daily_features_v2 | NO (research) | **RESEARCH** |
| `research/ede/validation_pipeline.py` (533 lines) | Cost tests + attacks + regime splits | YES | YES (writes) | edge_candidates_raw, edge_candidates_survivors | NO (research) | **RESEARCH** |
| `research/ede/ede_cli.py` (329 lines) | CLI for EDE operations (generate/validate/approve/stats) | YES | YES (writes) | EDE tables | NO (research) | **RESEARCH** |
| **RESEARCH (Other Scripts)** |
| `research/scripts/research_1800_any_edges.py` | Research script for 1800 ORB analysis | YES (read) | NO | bars_1m, daily_features | NO (research) | **RESEARCH** |
| `trading_app/strategy_discovery.py` (426 lines) | Edge discovery algorithms + StrategyDiscovery class | YES | YES (edge_candidates?) | bars_1m, edge_candidates? | NO (research tool) | **RESEARCH** |
| `analysis/export_v2_edges.py` | Export edges to CSV/JSON | YES (read) | NO (exports) | daily_features_v2 | NO (analysis) | **RESEARCH** |
| **MIGRATIONS** |
| `pipeline/migrate_add_edge_candidates.py` | Creates edge_candidates table (production schema) | YES | YES (CREATE TABLE) | None | NO (one-time migration) | **DEPRECATED** |
| `pipeline/migrate_add_reproducibility_fields.py` | Adds reproducibility fields to edge_candidates | YES | YES (ALTER TABLE) | edge_candidates | NO (one-time migration) | **DEPRECATED** |

---

## STEP 2 — CANONICAL "EDGE LIFECYCLE"

### Current Mess: 3 Competing Workflows

#### Workflow A: EDE Research System (research/ede/)
```
IDEA → GENERATION (brute/conditional/contrast/inversion/ml) →
  edge_candidates_raw table →
BACKTEST (zero-lookahead) →
ATTACK (robustness tests) →
VALIDATION (costs + regimes) →
  edge_candidates_survivors table →
APPROVAL (manual review) →
  edge_manifest table (EDE SOURCE OF TRUTH) →
SYNC (to validated_setups + config.py + docs)
```

**Tables**: edge_candidates_raw, edge_candidates_survivors, edge_manifest (6 EDE tables total)
**Entry**: Via generator_brute.py or ede_cli.py
**Exit**: Manual sync to validated_setups (NOT YET IMPLEMENTED)

#### Workflow B: Production Edge Candidates (trading_app/)
```
(Manual creation or StrategyDiscovery?) →
  edge_candidates table (PRODUCTION) →
APPROVAL (via edge_candidates_ui.py or approve_candidate.py) →
  status = APPROVED →
PROMOTION (NEW: via edge_pipeline.py) →
  validated_setups table →
SYNC CHECK (test_app_sync.py validates validated_setups ↔ config.py)
```

**Tables**: edge_candidates (production), validated_setups (production)
**Entry**: Unclear (no formal generation mechanism)
**Exit**: Promotion to validated_setups (edge_pipeline.py exists but not used)

#### Workflow C: Hardcoded Rebuild (strategies/)
```
Human writes strategies to validated_strategies.py dict →
  populate_validated_setups.py →
  DELETE FROM validated_setups + INSERT hardcoded values →
  test_app_sync.py (manual run to regenerate config.py)
```

**Tables**: validated_setups (production)
**Entry**: Human hardcodes dict
**Exit**: Production immediately (overwrites existing data)

### Proposed Canonical Lifecycle (UNIFIED)

```
┌─────────────────────────────────────────────────────────────────┐
│ RESEARCH PHASE (research/ folder)                               │
├─────────────────────────────────────────────────────────────────┤
│ 1. GENERATION: Generate candidates via EDE generators           │
│    - Tools: ede_cli.py, generator_brute.py, strategy_discovery.py│
│    - Output: edge_candidates_raw (research DB or CSV export)    │
│                                                                  │
│ 2. VALIDATION: Brutal testing (costs, attacks, regimes)        │
│    - Tools: validation_pipeline.py, backtest_engine.py         │
│    - Output: edge_candidates_survivors (research DB)            │
│                                                                  │
│ 3. EXPORT: Manual export of survivors to production format     │
│    - Tool: NEW script research/export_to_production.py         │
│    - Output: JSON manifest with complete fields                │
└─────────────────────────────────────────────────────────────────┘
          │
          │ (Manual review + JSON manifest)
          ▼
┌─────────────────────────────────────────────────────────────────┐
│ PRODUCTION PHASE (trading_app/ + strategies/)                   │
├─────────────────────────────────────────────────────────────────┤
│ 4. CANDIDATE CREATION: Import JSON manifest                     │
│    - Tool: NEW script import_research_candidate.py             │
│    - Target: edge_candidates table (production)                │
│    - Status: DRAFT initially                                    │
│                                                                  │
│ 5. APPROVAL: Manual review + approval                          │
│    - Tools: edge_candidates_ui.py, approve_candidate.py        │
│    - Action: status = APPROVED                                  │
│                                                                  │
│ 6. PROMOTION: Move to validated_setups (admin-gated)           │
│    - Tool: edge_pipeline.py (promote_candidate_to_validated_setups)│
│    - Target: validated_setups table (PRODUCTION SOURCE OF TRUTH)│
│    - Audit: Records promoted_from_candidate_id                 │
│                                                                  │
│ 7. SYNC ENFORCEMENT: Validate DB ↔ config.py match             │
│    - Tool: test_app_sync.py (MANDATORY after any promotion)    │
│    - Rule: Mismatch = rollback entire operation                │
│                                                                  │
│ 8. LIVE EXECUTION: Apps read validated_setups                  │
│    - Apps: app_trading_hub.py, app_mobile.py                   │
│    - Readers: setup_detector.py, strategy_engine.py            │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle**: Research generates candidates, production validates + approves, validated_setups is the ONLY authoritative source for live trading.

---

## STEP 3 — WHAT EXISTS ALREADY (STOP DUPLICATION)

### Promotion/Rebuild Mechanisms

| Tool | Purpose | Status |
|------|---------|--------|
| `populate_validated_setups.py` | **DANGEROUS** - deletes all validated_setups and rebuilds from hardcoded dict | **ARCHIVE** (overwrites audit trail) |
| `edge_pipeline.py` (NEW) | Promotes individual APPROVED candidates → validated_setups with audit trail | **KEEP** (Phase 1 compliant) |

**Decision**: DEPRECATE populate_validated_setups.py, USE edge_pipeline.py for all future promotions.

### Discovery Mechanisms

| Tool | Purpose | Status |
|------|---------|--------|
| `research/ede/` system | Systematic edge generation (1.78M param space) + brutal validation | **KEEP** (research) |
| `strategy_discovery.py` | Edge discovery algorithms (unclear if actively used) | **AUDIT NEEDED** |
| Manual hardcoding | Human writes to validated_strategies.py dict | **DEPRECATED** |

**Decision**: Research uses EDE, production imports survivors via formal bridge.

### Candidate Tooling

| Tool | Purpose | Status |
|------|---------|--------|
| `edge_candidates_ui.py` | Review/approve candidates in production DB | **KEEP** (production UI) |
| `edge_candidate_utils.py` | Approval functions (approve_edge_candidate, set_candidate_status) | **KEEP** (production) |
| `approve_candidate.py` | CLI approval script | **KEEP** (admin tool) |

**Decision**: All candidate approval tooling exists and works. No duplication.

---

## STEP 4 — SOURCE OF TRUTH DECISION

### A) Production Source of Truth

**AUTHORITATIVE (Single Source of Truth)**:
- **`validated_setups` table** (19 strategies currently) - PRODUCTION TRUTH
- **`trading_app/config.py`** - Must exactly match validated_setups (enforced by test_app_sync.py)

**SUPPORTING (Must Stay Synced)**:
- `test_app_sync.py` - Sync enforcer (MANDATORY after any change)
- `setup_detector.py` - Reads validated_setups for live detection
- `strategy_engine.py` - Reads validated_setups for live execution

**DEPRECATED (Archive)**:
- `strategies/populate_validated_setups.py` - Overwrites audit trail, use edge_pipeline.py instead
- `strategies/validated_strategies.py` - Hardcoded dict, use edge_candidates workflow instead

### B) Research Source of Truth

**CANONICAL RESEARCH SYSTEM**:
- **`research/ede/` system** - Institutional-grade edge discovery
  - Tables: edge_candidates_raw, edge_candidates_survivors, edge_manifest (6 tables)
  - Generators: generator_brute.py (Mode A), future modes B/C/D/E
  - Validation: validation_pipeline.py, backtest_engine.py
  - CLI: ede_cli.py

**OUTPUT FORMATS**:
- **JSON manifest** (complete field spec):
  ```json
  {
    "name": "...",
    "instrument": "MGC",
    "hypothesis_text": "...",
    "filter_spec": {"orb_size_filter": 0.05, "sl_mode": "FULL"},
    "test_config": {"test_window_start": "2024-01-01", "test_window_end": "2025-12-31"},
    "metrics": {"orb_time": "1000", "rr": 8.0, "win_rate": 33.5, "avg_r": 0.342, "annual_trades": 260, "tier": "S+"},
    "slippage_assumptions": {"slippage_ticks": 2, "commission_per_contract": 2.50},
    "code_version": "abc123",
    "data_version": "v1"
  }
  ```

**SUPPORTING**:
- `research/scripts/` - One-off analysis scripts
- `analysis/export_v2_edges.py` - Export utilities
- `strategy_discovery.py` - **AUDIT NEEDED** (unclear role, may be redundant with EDE)

### C) "Bridge Layer" (MISSING - NEEDS CREATION)

**CURRENT STATE**: No formal bridge between research → production

**REQUIRED BRIDGE MECHANISM** (ONE canonical path):

```
research/ede/edge_manifest → [BRIDGE] → trading_app/edge_candidates → validate → approve → promote → validated_setups
```

**Missing Tools**:
1. **`research/export_to_production.py`** - Export EDE survivors to production JSON manifest format
2. **`import_research_candidate.py`** - Import JSON manifest → edge_candidates table with validation

**Existing Promotion**:
- ✅ `edge_pipeline.py` - Promotes APPROVED → validated_setups (exists, not yet integrated with UI)

---

## CONFLICTS DETECTED

### Conflict 1: Multiple Edge Candidate Tables

| Table | Location | Purpose | Status |
|-------|----------|---------|--------|
| `edge_candidates` | Production DB (gold.db) | Production approval workflow | **KEEP** (production) |
| `edge_candidates_raw` | Research DB (gold.db) | EDE generation phase | **KEEP** (research) |
| `edge_candidates_survivors` | Research DB (gold.db) | EDE validation survivors | **KEEP** (research) |
| `edge_manifest` | Research DB (gold.db) | EDE approved edges | **KEEP** (research, sync to production) |

**Resolution**: These tables serve DIFFERENT purposes in different workflows. They must coexist but remain isolated.

**Rule**: Research tables (EDE) never directly feed production. Bridge layer exports/imports with manual review gate.

### Conflict 2: Multiple Promotion Mechanisms

| Tool | Approach | Risk |
|------|----------|------|
| `populate_validated_setups.py` | DELETE all, INSERT hardcoded dict | **HIGH** - Loses audit trail, overwrites everything |
| `edge_pipeline.py` (NEW) | Promote individual APPROVED candidates with audit trail | **LOW** - Incremental, auditable |

**Resolution**: DEPRECATE `populate_validated_setups.py`. Move to `_archive/` with explanation.

**Rule**: ALL future validated_setups inserts go through `edge_pipeline.py` promotion with audit trail.

### Conflict 3: strategy_discovery.py Role Unclear

`trading_app/strategy_discovery.py` (426 lines) appears to be an edge discovery mechanism but:
- Not imported by any production app
- Not part of EDE research system
- Unclear if actively used

**Resolution**: AUDIT NEEDED - Determine if this is:
- A) Redundant with EDE (archive if yes)
- B) A different discovery approach (integrate into research/ if active)
- C) Deprecated (move to _archive/)

---

## STEP 5 — MINIMAL IMPLEMENTATION PLAN

### Required Changes (Minimal)

#### 1. Create Bridge Layer (NEW)

**File: `research/export_to_production.py`** (~100 lines)
```python
"""Export EDE survivors to production JSON manifest format."""
# Reads: edge_candidates_survivors, edge_manifest (research DB)
# Writes: JSON files to research/exports/
# Output: Complete manifest with all required fields for edge_pipeline.py
```

**File: `import_research_candidate.py`** (~150 lines)
```python
"""Import research JSON manifest → edge_candidates (production)."""
# Reads: JSON manifest files
# Writes: edge_candidates table (production DB) with status=DRAFT
# Validation: Enforces complete field requirements
```

#### 2. Integrate edge_pipeline.py into UI (MODIFY)

**File: `trading_app/edge_candidates_ui.py`** (add ~20 lines)
- Add "🚀 Promote to Production" button
- Only visible for status=APPROVED AND promoted_validated_setup_id=NULL
- Calls `edge_pipeline.promote_candidate_to_validated_setups()`
- Shows success message with new setup_id

#### 3. Run Schema Migration (REQUIRED)

**Migration: Add missing column**
```sql
ALTER TABLE edge_candidates ADD COLUMN IF NOT EXISTS promoted_validated_setup_id INTEGER DEFAULT NULL;
```

#### 4. Archive Deprecated Tools (MOVE)

**Move to `_archive/` with README**:
- `strategies/populate_validated_setups.py` → `_archive/deprecated/`
- `strategies/validated_strategies.py` → `_archive/deprecated/`
- Add `_archive/deprecated/README.md` explaining why deprecated

#### 5. Create Documentation (NEW)

**File: `docs/EDGE_SYSTEM.md`** (~200 lines)
- Canonical lifecycle diagram
- Source of truth decision
- Bridge layer usage
- Integration guide

### NOT Allowed (Scope Creep)

❌ New dashboards
❌ New ML systems
❌ New frameworks
❌ Rewriting StrategyEngine / execution
❌ Auto-sync mechanisms (keep manual for Phase 1)

### Testing Requirements

**After implementation, run ONLY**:
```bash
# Core tests
pytest tests/test_edge_approval.py -q
pytest tests/test_edge_promotion.py -q  # After schema migration
pytest tests/test_ai_source_lock.py -q

# Sync enforcer (MANDATORY if validated_setups changed)
python test_app_sync.py
```

**Do NOT**:
- Run full test suite (expensive)
- Run research tests (separate from production)
- Add new test frameworks

---

## OUTPUT REQUIREMENTS

### Forensic Table
✅ Complete (see above)

### Canonical Lifecycle
✅ Defined (see STEP 2)

### Source of Truth Decision
✅ Decided (see STEP 4):
- **Production**: validated_setups table + config.py (synced)
- **Research**: EDE system (research/ede/) with 6 tables
- **Bridge**: NEW tools needed (export + import scripts)

### Minimal Plan

**Code Changes Required**:
1. Create `research/export_to_production.py` (~100 lines)
2. Create `import_research_candidate.py` (~150 lines)
3. Modify `trading_app/edge_candidates_ui.py` (+20 lines for Promote button)
4. Create `docs/EDGE_SYSTEM.md` (~200 lines)
5. Move deprecated tools to `_archive/` with explanation

**Total**: ~470 lines of new code + file moves + 1 SQL migration

**Files Modified**:
```
research/export_to_production.py          (NEW, 100 lines)
import_research_candidate.py              (NEW, 150 lines)
trading_app/edge_candidates_ui.py         (MODIFY, +20 lines)
docs/EDGE_SYSTEM.md                       (NEW, 200 lines)
_archive/deprecated/README.md             (NEW, 50 lines)
```

**Files Moved**:
```
strategies/populate_validated_setups.py   → _archive/deprecated/
strategies/validated_strategies.py        → _archive/deprecated/
```

**Schema Migration**:
```sql
ALTER TABLE edge_candidates ADD COLUMN IF NOT EXISTS promoted_validated_setup_id INTEGER DEFAULT NULL;
```

**Testing Plan**:
```bash
pytest tests/test_edge_approval.py -q
pytest tests/test_edge_promotion.py -q
pytest tests/test_ai_source_lock.py -q
python test_app_sync.py  # If validated_setups modified
```

---

## RECOMMENDATIONS

### Immediate Actions

1. **Run schema migration** (5 minutes)
2. **Archive deprecated tools** (10 minutes)
3. **Create bridge layer scripts** (2 hours)
4. **Integrate edge_pipeline.py into UI** (30 minutes)
5. **Create docs/EDGE_SYSTEM.md** (1 hour)

### Future Work (Phase 2+)

1. **Audit strategy_discovery.py** - Determine role, integrate or archive
2. **Complete EDE generators** - Modes B/C/D/E (conditional, contrast, inversion, ML)
3. **Auto-sync mechanism** - After Phase 1 stability proven
4. **Live drift monitoring** - Track edge_manifest → validated_setups performance
5. **Auto-retirement logic** - Suspend underperforming edges automatically

### Critical Rules (Non-Negotiable)

1. **validated_setups = ONLY production source of truth**
2. **test_app_sync.py MUST pass before ANY promotion**
3. **edge_pipeline.py = ONLY way to promote (no direct INSERT)**
4. **Research stays in research/ folder (no direct production writes)**
5. **Bridge layer = ONLY connection between research ↔ production**

---

## CONCLUSION

**Current State**: 3 competing workflows causing confusion and risk

**Proposed State**: 1 unified canonical lifecycle with clear boundaries:
- Research (EDE) generates and validates candidates
- Bridge layer exports survivors with manual review gate
- Production approves and promotes via edge_pipeline.py with audit trail
- validated_setups remains single authoritative source
- test_app_sync.py enforces sync integrity

**Risk**: Continuing with multiple systems increases probability of:
- Accidental overwrites (populate_validated_setups.py)
- Lost audit trails
- DB/config drift
- Production incidents

**Benefit**: Unified system provides:
- Clear ownership (research vs production)
- Audit trails preserved
- Fail-closed gates
- Institutional-grade validation before production

**Next Step**: Approve minimal implementation plan and execute in order.
