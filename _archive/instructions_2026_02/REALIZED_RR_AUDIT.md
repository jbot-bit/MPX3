# REALIZED_RR AUDIT - Step 3

**Date**: 2026-01-29
**Goal**: Ensure ALL UI/scanner/validation uses `realized_rr` for decisions/scoring/metrics

---

## AUDIT TABLE

| File | Lines | Context | Should Use | Fix Needed |
|------|-------|---------|------------|------------|
| **CRITICAL FIXES (Used for Decisions/Scoring)** |||||
| `trading_app/edge_utils.py` | 496, 523-524, 538, 550, 559 | Uses `r_multiple` for backtest calculations, avg_win/loss, cumulative R, stress testing | `realized_rr` | **YES** |
| `trading_app/app_simple.py` | 427 | Displays `r_multiple` in UI | `realized_rr` | **YES** |
| `trading_app/ml_dashboard.py` | 95, 118, 199, 244 | Uses `avg_r_multiple` for ML performance metrics | `realized_rr` | **YES** |
| `trading_app/memory.py` | 65, 91, 105, 118, 144, 151, 188, 213, 246, 282, 444-445, 476-477, 609-610, 746 | Trade journal stores `r_multiple` | `realized_rr` | **YES** |
| **ACCEPTABLE (Raw Data/Debug/Schema)** |||||
| `trading_app/edge_tracker.py` | 111 | Reads `r_multiple` column from daily_features (raw data) | `r_multiple_ok` | **NO** |
| `strategies/execution_engine.py` | 92, 132-162 | Dataclass field definition + initialization (stores BOTH) | `r_multiple_ok` | **NO** |
| `tests/conftest.py` | 322-352, 373, 381 | Schema definition (historical column) | `r_multiple_ok` | **NO** |
| `tests/test_build_daily_features.py` | 353, 369, 385, 401 | Tests r_multiple column (schema validation) | `r_multiple_ok` | **NO** |
| `discover_all_orb_patterns.py` | 62-82, 139 | Research script reads raw daily_features columns | `r_multiple_ok` | **NO** |
| `analysis/research_night_orb_comprehensive.py` | 73, 77 | Research script reads raw columns | `r_multiple_ok` | **NO** |
| **ALREADY CORRECT (Uses realized_rr)** |||||
| `trading_app/app_canonical.py` | 1270-1373, 2437-2438 | Uses `realized_rr_col` for validation metrics | ✅ | **NO** |
| `trading_app/auto_search_engine.py` | 350-384 | Uses `tradeable_realized_rr` for edge discovery | ✅ | **NO** |
| `trading_app/setup_detector.py` | 77-308 | Uses `realized_expectancy` from validated_setups | ✅ | **NO** |
| `trading_app/strategy_engine.py` | 60, 861, 911, 1034 | Uses `realized_expectancy` for strategy evaluation | ✅ | **NO** |
| `trading_app/experimental_scanner.py` | 89-482 | Uses `realized_expectancy` throughout | ✅ | **NO** |
| `pipeline/cost_model.py` | All | Calculates `realized_rr` correctly | ✅ | **NO** |
| `strategies/populate_realized_metrics.py` | All | Populates `realized_expectancy` to validated_setups | ✅ | **NO** |
| `scratchpad/validate_missing_orbs.py` | 64-84 | Uses `tradeable_realized_rr` for validation | ✅ | **NO** |
| `analysis/what_if_engine.py` | 494-513 | Uses `r_multiple - cost_r` (equivalent to realized) | ✅ | **NO** |
| `analysis/test_honest_filters.py` | 37-158 | Uses `realized_rr` from validated_trades | ✅ | **NO** |

---

## SUMMARY

### Critical Fixes Needed: 4 Files

1. **trading_app/edge_utils.py** (HIGH PRIORITY)
   - **Problem**: Backtest engine uses `r_multiple` for all calculations
   - **Impact**: Strategy validation shows OPTIMISTIC results (costs not included)
   - **Fix**: Replace all `r_multiple` references with `realized_rr` or calculate from execution_engine

2. **trading_app/app_simple.py** (MEDIUM PRIORITY)
   - **Problem**: UI displays `r_multiple` to user
   - **Impact**: Users see theoretical R, not realized R (misleading)
   - **Fix**: Change display to use `realized_rr`

3. **trading_app/ml_dashboard.py** (MEDIUM PRIORITY)
   - **Problem**: ML metrics use `avg_r_multiple`
   - **Impact**: Model trained on optimistic data (wrong predictions)
   - **Fix**: Change to `realized_rr` or `realized_expectancy`

4. **trading_app/memory.py** (MEDIUM PRIORITY)
   - **Problem**: Trade journal stores `r_multiple`
   - **Impact**: Historical analysis uses optimistic R values
   - **Fix**: Add `realized_rr` field, populate from execution_engine

### Files Already Correct: 10 Files
- All validated_setups consumers use `realized_expectancy` ✅
- All tradeable metrics use `realized_rr` columns ✅
- Cost model correctly calculates `realized_rr` ✅

### Acceptable Raw Data Usage: 6 Files
- Schema definitions (conftest.py)
- Research scripts reading raw daily_features
- Execution engine (stores BOTH r_multiple and realized_rr)

---

## NEXT STEPS

1. Implement fixes for 4 critical files
2. Create check script: `scripts/check/check_realized_rr_usage.py`
3. Update `test_app_sync.py` to include realized_rr check
4. Update CLAUDE.md with realized_rr mandate

---
