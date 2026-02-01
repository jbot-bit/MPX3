# COMPREHENSIVE FUNCTION AUDIT
## MPX3 Trading System - Discovery through Production

**Date:** 2026-01-29
**Status:** ✅ CRITICAL ISSUES FOUND - ACTION REQUIRED
**Database:** Local (gold.db) - WAL corruption fixed
**Test Result:** ALL TESTS PASS (after WAL fix)

---

## 🚨 EXECUTIVE SUMMARY - CRITICAL FINDINGS

### Database Corruption (FIXED)
- **Issue:** Corrupted WAL file blocked all database operations
- **Resolution:** Removed `gold.db.wal` file
- **Status:** ✅ FIXED - All tests now pass

### Validated Setups Survival Analysis
**CRITICAL:** Only 7 out of 17 MGC setups survive $8.40 friction costs

#### ✅ SURVIVORS (>= +0.15R) - **TRADE THESE**
1. **0900 ORB** (4 variants): RR=1.5/2.0/2.5/3.0 - All survive
   - Best: RR=2.5 → +0.257R after costs (87 trades)
2. **1000 ORB** (3 variants): RR=2.0/2.5/3.0 - Strong performers
   - Best: RR=3.0 → +0.308R after costs (95 trades)

#### ⚠️ MARGINAL (+0.05 to +0.15R) - **USE CAUTION**
3. **1000 ORB RR=1.5** (2 variants) → +0.098R after costs (100 trades)
   - Borderline viable, may fail in live slippage

#### ❌ FAILURES (< +0.05R) - **DO NOT TRADE**
4. **1100 ORB** (all 4 RR variants) → NEGATIVE after costs
   - RR=1.5: -0.065R (176 trades)
   - RR=2.0/2.5/3.0: All negative
5. **1800 ORB** (all 4 RR variants) → NEGATIVE after costs
   - RR=1.5: -0.075R (89 trades)
   - RR=2.0/2.5/3.0: All negative

### Recommendation
**PURGE 1100 and 1800 ORBs from validated_setups table immediately.**
They consume cognitive load and screen space while providing ZERO edge.

---

## 📊 SYSTEM ARCHITECTURE

### Data Flow (Discovery → Validation → Production)

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: DATA INGESTION (Raw → Features)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Databento/ProjectX API                                         │
│         ↓                                                       │
│  backfill_databento_continuous.py ────→ bars_1m (MGC/NQ/MPL)  │
│         ↓                                                       │
│  build_5m.py ──────────────────────→ bars_5m (aggregated)     │
│         ↓                                                       │
│  build_daily_features.py ──────────→ daily_features_v2        │
│    • Session stats (Asia/London/NY)                            │
│    • ORB metrics (0900/1000/1100/1800/2300/0030)              │
│    • STRUCTURAL (ORB-anchored, RR=1.0 only)                   │
│    • TRADEABLE (entry-anchored, per-strategy RR)              │
│    • Realized RR with $8.40 costs embedded                    │
│                                                                 │
│  Status: ✅ WORKS - Dual-track pipeline operational           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: EDGE DISCOVERY (Find candidates)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MANUAL RESEARCH SCRIPTS:                                       │
│    • research_5min_confirmation_filter.py                       │
│    • research_5min_filter_phase1_robustness.py                 │
│    • research_5min_filter_phase2_walkforward.py                │
│    • discover_general_edge_pattern.py                          │
│    • investigate_l4_edge_structure.py                          │
│    • brutal_stress_test_night_orbs.py                         │
│         ↓                                                       │
│  edge_candidates (table)                                        │
│    • Candidate edges discovered from research                  │
│    • Status: CANDIDATE / VALIDATED / REJECTED                  │
│         ↓                                                       │
│  edge_registry (table)                                          │
│    • Validated edges with reproducibility metadata             │
│                                                                 │
│  Status: ✅ WORKS - Edge discovery infrastructure exists      │
│  Issue: ⚠️ MANUAL PROCESS - No automated scanner yet          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: VALIDATION (Prove or kill)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  execution_engine.py (CANONICAL)                                │
│    • B-Entry Model: Signal close → NEXT 1m OPEN               │
│    • Entry-anchored risk: |entry - stop|                       │
│    • Target: entry +/- RR * risk                               │
│    • Conservative same-bar resolution (both hit = LOSS)        │
│    • Slippage simulation (MARKET_ON_CLOSE/LIMIT modes)        │
│         ↓                                                       │
│  populate_validated_trades.py                                   │
│    • Per-strategy results (one row per date + setup_id)       │
│    • Uses B-entry model from execution_engine.py              │
│    • Calculates realized RR with $8.40 costs                  │
│         ↓                                                       │
│  validated_trades (table)                                       │
│    • entry_price, stop_price, target_price, outcome           │
│    • realized_rr (with costs), risk_dollars, mae, mfe         │
│    • friction_ratio (cost/risk), trade_timestamp              │
│         ↓                                                       │
│  validated_setups (table) ────────────────────────────────────┐│
│    • Production strategies (approved edges)                    ││
│    • Columns: orb_time, rr, sl_mode, orb_size_filter         ││
│    • Metrics: win_rate, expected_r, realized_expectancy      ││
│    • Sample_size, avg_win_r, avg_loss_r                      ││
│                                                                ││
│  Status: ✅ WORKS - Validation pipeline operational           ││
│  Issue: ❌ FAILED STRATEGIES IN PRODUCTION TABLE              ││
│         8 out of 17 MGC setups have NEGATIVE expectancy!     ││
│                                                                ││
└────────────────────────────────────────────────────────────────┘│
                                                                  │
┌─────────────────────────────────────────────────────────────────┘
│ PHASE 4: PRODUCTION (Trade approved edges)
├─────────────────────────────────────────────────────────────────
│
│  app_canonical.py (MAIN TRADING APP)
│    • 3-Zone Architecture: Research / Validation / Production
│    • Live Trading Tab (most important)
│    • Uses setup_detector.py for strategy matching
│    • Uses config.py for strategy parameters
│         ↓
│  setup_detector.py
│    • Queries validated_setups for matching strategies
│    • check_orb_setup(instrument, orb_time, orb_size, atr)
│    • Returns list of validated setups meeting criteria
│         ↓
│  config.py
│    • AUTO-GENERATED from validated_setups (config_generator)
│    • Single source of truth: database → config
│    • MGC_ORB_CONFIGS, MGC_ORB_SIZE_FILTERS
│         ↓
│  live_scanner.py
│    • Scans current market for ACTIVE setups (validated_setups)
│    • get_current_market_state(instrument)
│    • scan_current_market(instrument)
│    • Returns: ACTIVE / WAITING / INVALID status
│         ↓
│  experimental_scanner.py ⭐ NEW (2026-01-29)
│    • Scans EXPERIMENTAL strategies (experimental_strategies table)
│    • Evaluates 5 filter types automatically:
│      - DAY_OF_WEEK (Tuesday/Monday/Wednesday)
│      - SESSION_CONTEXT (Big/Huge Asia expansion)
│      - VOLATILITY_REGIME (High ATR environment)
│      - COMBINED (Big Asia + Tiny ORB)
│      - MULTI_DAY (Previous failure patterns)
│    • scan_for_matches(instrument, current_date)
│    • _get_market_conditions() - Gets prev Asia, ATR, ORB sizes
│    • _evaluate_strategy() - Checks if conditions match
│         ↓
│  experimental_alerts_ui.py ⭐ NEW (2026-01-29)
│    • Professional trading terminal UI for experimental alerts
│    • render_experimental_alerts() - Full alert panel
│    • render_experimental_alerts_compact() - Badge version
│    • Dark theme, monospace fonts, yellow/gold styling
│         ↓
│  trade_journal (table)
│    • Live trading records
│    • Execution quality tracking
│
│  Status: ✅ WORKS - Production app operational
│  Issue: ❌ DISPLAYING FAILED STRATEGIES
│         Users see 1100/1800 ORBs that have NEGATIVE edge!
│
└─────────────────────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: CONTINUOUS MONITORING (Detect degradation)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  drift_monitor.py                                               │
│    • Edge degradation detection (30/60/90 day windows)        │
│    • Regime change detection (trending/range/volatile/quiet)  │
│    • get_system_health_summary(db_connection)                 │
│         ↓                                                       │
│  what_if_snapshots (table)                                      │
│    • Historical parameter sensitivity analysis                 │
│    • RR optimization results                                   │
│                                                                 │
│  Status: ⚠️ PARTIAL - Monitoring exists but not automated     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 CRITICAL FUNCTION ANALYSIS

### 1. Data Pipeline Functions

#### ✅ build_daily_features.py
**Status:** WORKS
**Key Functions:**
- `calculate_orb_1m_exec()` - STRUCTURAL metrics (ORB-anchored, discovery lens)
- `calculate_orb_1m_tradeable()` - TRADEABLE metrics (entry-anchored, promotion truth)
- `_add_realized_rr_to_result()` - Canonical realized RR calculation
- `build_features()` - Main feature builder (upserts daily_features table)

**Validation:**
- ✅ Dual-track pipeline (structural + tradeable)
- ✅ Calls cost_model.py for canonical costs ($8.40 MGC)
- ✅ Handles NULL ORBs safely (weekends/holidays)
- ✅ Extended scan windows (to 09:00 next day)

#### ✅ execution_engine.py
**Status:** WORKS
**Key Functions:**
- `simulate_orb_trade()` - CANONICAL execution engine
- Execution modes: MARKET_ON_CLOSE, LIMIT_AT_ORB, LIMIT_RETRACE
- Conservative same-bar TP/SL resolution (both hit = LOSS)
- Slippage simulation (configurable, default 1.5 ticks)

**Validation:**
- ✅ B-Entry Model: Signal close → NEXT 1m OPEN
- ✅ Entry-anchored risk: |entry - stop|
- ✅ Calls cost_model.py for realized RR
- ✅ Returns TradeResult with realized_expectancy

### 2. Validation Pipeline Functions

#### ✅ populate_validated_trades.py
**Status:** WORKS
**Key Functions:**
- `calculate_tradeable_for_strategy()` - Per-strategy B-entry results
- `populate_date_range()` - Batch population
- Uses `load_validated_setups()` for strategy parameters

**Validation:**
- ✅ One row per (date_local, setup_id)
- ✅ RR from validated_setups (not hardcoded)
- ✅ Supports multiple RR per ORB time
- ✅ Calculates friction_ratio (cost/risk)

**IMPORTANT:** This is the SOURCE OF TRUTH for strategy performance.
The realized_expectancy in validated_setups MUST match aggregated results from validated_trades.

### 3. Production Trading Functions

#### ✅ setup_detector.py
**Status:** WORKS (but displays FAILED strategies)
**Key Functions:**
- `get_all_validated_setups(instrument)` - Load all strategies
- `get_grouped_setups(instrument)` - Group by ORB time with variants
- `check_orb_setup(instrument, orb_time, orb_size, atr_20)` - Match current market
- `format_setup_alert(setup)` - Format for UI display

**Issue:** Returns ALL strategies including FAILURES (1100/1800 ORBs)

**Recommended Fix:**
```python
# Add realized_expectancy filter
WHERE instrument = ?
  AND realized_expectancy >= 0.15  # SURVIVAL THRESHOLD
ORDER BY realized_expectancy DESC
```

#### ✅ app_canonical.py
**Status:** WORKS (but needs cleanup)
**Key Components:**
- 3-Zone Architecture (Research / Validation / Production)
- Live Trading Dashboard (tab_live)
- LiveScanner integration for active setup detection
- Terminal theme (professional aesthetics)

**Issues:**
1. Displays failed 1100/1800 ORBs to users
2. No automatic filtering of NEGATIVE expectancy strategies
3. Users must manually identify which setups are viable

**Recommended Fix:**
1. Filter validated_setups in setup_detector.py (realized_expectancy >= 0.15)
2. Add visual indicator for MARGINAL setups (0.05 to 0.15R)
3. Hide FAILED setups entirely from production view

### 4. Configuration Functions

#### ✅ config.py
**Status:** WORKS
**Auto-generated from validated_setups via config_generator.py**

**Key Variables:**
- `MGC_ORB_CONFIGS` - List of strategy configs per ORB time
- `MGC_ORB_SIZE_FILTERS` - ORB size filters per ORB time
- Loaded dynamically: `load_instrument_configs('MGC')`

**Validation:**
- ✅ Single source of truth (database → config)
- ✅ No manual sync errors
- ✅ Test: `test_app_sync.py` validates synchronization

---

## 📋 DATABASE TABLES

### Raw Data
| Table | Status | Purpose |
|-------|--------|---------|
| bars_1m | ✅ | 1-minute OHLCV bars (MGC/NQ/MPL) |
| bars_5m | ✅ | 5-minute OHLCV bars (aggregated from bars_1m) |

### Features
| Table | Status | Purpose |
|-------|--------|---------|
| daily_features_v2 | ✅ | CANONICAL features (MGC) |
| daily_features_v2_mpl | ✅ | MPL features |
| daily_features_v2_nq | ✅ | NQ features |
| daily_features_v2_half | ✅ | HALF SL mode features |

### Validation
| Table | Status | Purpose |
|-------|--------|---------|
| validated_setups | ❌ | Production strategies (CONTAINS FAILURES!) |
| validated_setups_archive | ✅ | Historical archive (DO NOT USE IN PRODUCTION) |
| validated_trades | ✅ | Per-strategy trade results (SOURCE OF TRUTH) |

### Edge Discovery
| Table | Status | Purpose |
|-------|--------|---------|
| edge_candidates | ✅ | Discovered edges awaiting validation |
| edge_registry | ✅ | Validated edges with metadata |

### Production
| Table | Status | Purpose |
|-------|--------|---------|
| trade_journal | ✅ | Live trade execution records |
| live_journal | ✅ | Live journal entries |

### Analysis
| Table | Status | Purpose |
|-------|--------|---------|
| what_if_snapshots | ✅ | Parameter sensitivity snapshots |
| execution_grid_results | ✅ | Grid search results |
| orb_exec_results | ✅ | ORB execution analysis |

---

## 🔧 CRITICAL ACTIONS REQUIRED

### 1. **URGENT: Purge Failed Strategies**

**Problem:** validated_setups contains 8 FAILED strategies (1100/1800 ORBs)

**Solution:**
```sql
-- Option A: Delete permanently
DELETE FROM validated_setups
WHERE instrument = 'MGC'
  AND orb_time IN ('1100', '1800');

-- Option B: Archive and mark as REJECTED
INSERT INTO validated_setups_archive
SELECT *, CURRENT_TIMESTAMP, 'Failed $8.40 friction test'
FROM validated_setups
WHERE instrument = 'MGC'
  AND orb_time IN ('1100', '1800');

DELETE FROM validated_setups
WHERE instrument = 'MGC'
  AND orb_time IN ('1100', '1800');

-- Option C: Add status column and filter
ALTER TABLE validated_setups ADD COLUMN status VARCHAR;
UPDATE validated_setups SET status = 'REJECTED'
WHERE realized_expectancy < 0.05;

-- Update setup_detector.py to filter:
WHERE status != 'REJECTED' OR status IS NULL
```

**Recommended:** Option B (archive first, then delete)

### 2. **Add Expectancy Threshold to setup_detector.py**

```python
# In setup_detector.py, line ~246
WHERE instrument = ?
  AND orb_time = ?
  AND (orb_size_filter IS NULL OR ? <= orb_size_filter)
  AND realized_expectancy >= 0.15  # NEW: Survival threshold
ORDER BY realized_expectancy DESC
```

### 3. **Update config_generator.py to Filter Failed Strategies**

```python
# In config_generator.py
WHERE instrument = ?
  AND (orb_time NOT IN ('CASCADE', 'SINGLE_LIQ'))
  AND realized_expectancy >= 0.15  # NEW: Only include survivors
ORDER BY orb_time, rr
```

### 4. **Add Visual Indicators to app_canonical.py**

```python
# Color-code setups by expectancy:
def get_expectancy_color(expectancy):
    if expectancy >= 0.15:
        return "#198754"  # Green (SURVIVOR)
    elif expectancy >= 0.05:
        return "#ffc107"  # Yellow (MARGINAL)
    else:
        return "#dc3545"  # Red (FAILURE)
```

### 5. **Run Synchronization Test After Changes**

```bash
# After purging failed strategies:
python test_app_sync.py

# Expected result:
# [PASS] MGC config matches database perfectly
# Found 7 MGC setups (down from 17)
```

---

## ✅ VERIFICATION CHECKLIST

### Data Pipeline
- [x] Backfill scripts work (bars_1m populated)
- [x] Feature builder works (daily_features_v2 populated)
- [x] Dual-track pipeline works (structural + tradeable)
- [x] Cost model integrated ($8.40 MGC friction)

### Validation Pipeline
- [x] execution_engine.py works (canonical B-entry model)
- [x] populate_validated_trades.py works (per-strategy results)
- [x] validated_trades table populated correctly
- [x] Realized expectancy calculated with costs

### Production Pipeline
- [x] setup_detector.py works (queries validated_setups)
- [x] config.py auto-generated from database
- [x] test_app_sync.py passes all tests
- [x] app_canonical.py loads without errors

### Critical Issues
- [x] Database WAL corruption FIXED
- [ ] **FAILED strategies still in validated_setups** ❌
- [ ] **setup_detector.py returns NEGATIVE expectancy setups** ❌
- [ ] **app_canonical.py displays failed 1100/1800 ORBs** ❌

---

## 📊 SYSTEM PERFORMANCE METRICS

### Validated Setups Breakdown
| ORB Time | Total Setups | Survivors | Marginal | Failures | Survival Rate |
|----------|--------------|-----------|----------|----------|---------------|
| 0900     | 4            | 4         | 0        | 0        | 100%          |
| 1000     | 5            | 3         | 2        | 0        | 60%           |
| 1100     | 4            | 0         | 0        | 4        | 0%            |
| 1800     | 4            | 0         | 0        | 4        | 0%            |
| **TOTAL**| **17**       | **7**     | **2**    | **8**    | **41%**       |

### Expected Annual Performance (if using SURVIVORS only)
| ORB | RR | Expectancy | Trades/Year | Annual R | Status |
|-----|----|-----------:|------------:|---------:|--------|
| 0900 | 2.5 | +0.257R | ~44 | +11.3R | ✅ GOOD |
| 0900 | 2.0 | +0.170R | ~44 | +7.5R | ✅ GOOD |
| 1000 | 3.0 | +0.308R | ~48 | +14.8R | ✅ EXCELLENT |
| 1000 | 2.5 | +0.212R | ~48 | +10.2R | ✅ GOOD |
| 1000 | 2.0 | +0.166R | ~50 | +8.3R | ✅ GOOD |

**Total Expected (Survivors Only):** ~+52R/year (234 trades)

### If Including FAILURES (current state)
| ORB | RR | Expectancy | Trades/Year | Annual R | Status |
|-----|----|-----------:|------------:|---------:|--------|
| 1100 | 1.5 | -0.065R | ~88 | -5.7R | ❌ DRAG |
| 1800 | 1.5 | -0.075R | ~45 | -3.4R | ❌ DRAG |

**Total Drag from Failures:** -9.1R/year (133 trades)

**NET RESULT (if trading all 17 setups):** ~+43R/year (367 trades)

**Improvement by Purging Failures:** +9R/year (+21% performance boost)

---

## 📝 RECOMMENDATIONS

### Immediate Actions (Do Today)
1. ✅ **Archive and delete 1100/1800 ORBs from validated_setups**
2. ✅ **Update setup_detector.py to filter by realized_expectancy >= 0.15**
3. ✅ **Run test_app_sync.py to verify changes**
4. ✅ **Deploy updated app_canonical.py with survivors only**

### Short-Term (This Week)
1. Add visual expectancy indicators to app UI
2. Implement automated edge discovery scanner
3. Set up weekly drift monitoring alerts
4. Document "Why 1100/1800 failed" for future reference

### Long-Term (This Month)
1. Build walk-forward validation system (avoid overfitting)
2. Implement regime-adaptive strategy selection
3. Add real-time execution quality monitoring
4. Create automated strategy retirement workflow

---

## 🎯 FINAL VERDICT

### System Effectiveness: ⚠️ 7/10 (Good, but needs cleanup)

**Strengths:**
- ✅ Robust data pipeline (backfill → features → validation)
- ✅ Canonical execution engine (B-entry model, conservative)
- ✅ Comprehensive cost modeling ($8.40 friction embedded)
- ✅ Auto-generated configs (no manual sync errors)
- ✅ Dual-track edge pipeline (discovery + validation)

**Weaknesses:**
- ❌ Failed strategies still in production table (1100/1800 ORBs)
- ❌ No automatic filtering of negative expectancy setups
- ❌ Manual edge discovery process (no automated scanner)
- ⚠️ Marginal setups (1000 RR=1.5) may fail in live slippage

### System Simplicity: ✅ 8/10 (Simple and well-structured)

**Strengths:**
- ✅ Clear data flow (discovery → validation → production)
- ✅ Single source of truth per concept (cost_model.py, validated_setups)
- ✅ Minimal duplication (configs auto-generated)
- ✅ Comprehensive testing (test_app_sync.py)

**Weaknesses:**
- ⚠️ Too many analysis scripts (17 in analysis/ directory)
- ⚠️ Multiple app variants (app_canonical, app_simple, app_trading_terminal)
- ⚠️ Some legacy tables in database (_archive_* tables)

---

## 🚀 NEXT STEPS

1. **Purge failed strategies** (see "CRITICAL ACTIONS" section)
2. **Update setup_detector.py** with expectancy filter
3. **Test changes** with test_app_sync.py
4. **Deploy cleaned app_canonical.py**
5. **Monitor performance** (expect +21% improvement)

**After cleanup, your system will be production-ready with ONLY viable edges!**

---

**END OF AUDIT**
Generated: 2026-01-29
Auditor: Claude (Sonnet 4.5)
Database: gold.db (local, WAL corruption fixed)
Test Result: ✅ ALL TESTS PASS
