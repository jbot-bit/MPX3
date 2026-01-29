# MGC Production Clean Branch

This branch contains **ONLY the 57 essential foundation files** for production deployment.

## What's Included

### Pipeline (16 files)
- `pipeline/cost_model.py` ⭐ CRITICAL - All cost formulas
- `pipeline/build_daily_features.py` ⭐ CRITICAL - Feature builder
- `pipeline/backfill_databento_continuous.py` - MGC data ingestion
- `pipeline/backfill_databento_continuous_mpl.py` - MPL data ingestion
- `pipeline/backfill_range.py` - ProjectX backfill
- `pipeline/build_5m.py` - 5-minute aggregation
- `pipeline/check_db.py` - Database inspection
- `pipeline/check_dbn_symbols.py` - DBN file checking
- `pipeline/init_db.py` - Schema initialization
- `pipeline/init_memory_tables.py` - Memory table schema
- `pipeline/inspect_dbn.py` - DBN inspection
- `pipeline/validate_data.py` - Data validation
- `pipeline/wipe_mgc.py` - MGC data reset
- `pipeline/wipe_mpl.py` - MPL data reset
- `pipeline/migrate_add_edge_candidates.py` - Schema migration
- `pipeline/migrate_add_reproducibility_fields.py` - Schema migration

### Strategies (6 files)
- `strategies/execution_engine.py` ⭐ CRITICAL - Entry/exit logic
- `strategies/execution_modes.py` - FULL/HALF SL modes
- `strategies/archive_strategy.py` - Strategy archival
- `strategies/populate_realized_from_phase1.py` - Realized metrics
- `strategies/populate_realized_metrics.py` - Realized metrics
- `strategies/test_app_sync.py` ⭐ CRITICAL - Sync validation

### Tests (22 files)
All test files in `tests/` directory including:
- `test_cost_model_sync.py` ⭐ CRITICAL
- `test_realized_rr_sync.py` ⭐ CRITICAL
- `test_calculation_consistency.py` - Determinism checks
- Plus 19 more test files

### Trading App (2 files)
- `trading_app/config.py` ⭐ CRITICAL - Filter settings (SYNC CRITICAL)
- `trading_app/setup_detector.py` - Setup detection

### Critical Docs (6 files)
- `CLAUDE.md` - Master instructions
- `CANONICAL_LOGIC.txt` - RR calculation formulas
- `COST_MODEL_MGC_TRADOVATE.txt` - $8.40 friction spec
- `TCA.txt` - Transaction cost analysis
- `FINDINGS_LOG.md` - Knowledge journal
- `BUGS.md` - Bug tracking

### Configuration (3 files)
- `.env` - Environment variables
- `.gitignore` - Version control exclusions
- `requirements.txt` - Python dependencies

### Schema (1 file)
- `schema.sql` - Database table definitions

---

## ⚠️ NOT INCLUDED (Copy Manually)

### gold.db (690MB - TOO LARGE FOR GITHUB)
**Location in source:** `MPX2_fresh/gold.db`

**Contains:**
- 720,000+ bars (bars_1m, bars_5m)
- 18 validated setups (validated_setups table)
- Daily features (daily_features_v2 table)
- Historical data from 2020-12-20 to 2026-01-10

**How to get it:**
1. Copy from source: `cp /path/to/MPX2_fresh/gold.db .`
2. Or rebuild from scratch:
   ```bash
   python pipeline/init_db.py
   python pipeline/backfill_databento_continuous.py 2020-12-20 2026-01-10
   ```

---

## Deployment Steps

1. **Clone this branch:**
   ```bash
   git clone -b MGC_Production_Clean https://github.com/jbot-bit/MPX2.git
   cd MPX2
   ```

2. **Copy gold.db manually:**
   ```bash
   # From source directory
   cp /path/to/MPX2_fresh/gold.db .
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   - Edit `.env` with your API keys

5. **Verify sync:**
   ```bash
   python strategies/test_app_sync.py
   ```

6. **Ready to build apps!**
   - All foundation files present
   - All formulas documented in CANONICAL_LOGIC.txt
   - Reference CLAUDE.md for architecture

---

## What's NOT Here (By Design)

❌ No skills/ directory (221 duplicate files across 5 IDEs)
❌ No agents/ directory (refactor artifacts)
❌ No research/ directory (historical experiments)
❌ No _archive/ directory (deprecated code)
❌ No trading_app/ UI files (to be rebuilt fresh)
❌ No analysis/ scripts (not foundation)

**This is intentional.** This branch is for **clean production deployment only.**

---

## Key Principles

✅ **44 core files** - The essential foundation
✅ **Zero bloat** - No duplicate or experimental code
✅ **Production-ready** - Tested and validated
✅ **Documented** - All formulas in CANONICAL_LOGIC.txt
✅ **Portable** - Copy these files to any environment

**Reference:** `CLAUDE.md` for complete architecture details
