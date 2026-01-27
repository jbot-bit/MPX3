# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gold (MGC) Data Pipeline for building a clean, replayable local dataset of Micro Gold futures (MGC / MGC1!) for ORB-based discretionary trading, systematic backtesting, and session statistics analysis.

**Primary Focus**: 09:00, 10:00, 11:00 ORBs
**Secondary**: 18:00, 23:00, 00:30 ORBs

---

## ⚠️ CRITICAL REMINDER - ALWAYS DO THIS AFTER CHANGES

**After ANY changes to strategies, database, or config files, ALWAYS run:**

```bash
python strategies/test_app_sync.py
```

This validates that `trading_app/config.py` matches `data/db/data/db/gold.db` → `validated_setups` table.

**DO NOT PROCEED if this test fails.** Fix the mismatch immediately.

**When to run this test:**
- After updating validated_setups database
- After modifying trading_app/config.py
- After running strategies/populate_validated_setups.py
- After adding new MGC/NQ/MPL setups
- After changing ORB filters or RR values

See full details in section: "CRITICAL: Database and Config Synchronization"

---

## Key Commands

### Backfilling Data

**Databento (primary source for historical data):**
```bash
python pipeline/backfill_databento_continuous.py YYYY-MM-DD YYYY-MM-DD
```
- Example: `python pipeline/backfill_databento_continuous.py 2024-01-01 2026-01-10`
- Automatically selects front/most liquid contract per day
- Stitches contracts into continuous series
- Safe to interrupt and re-run (idempotent)
- Can run forward or backward
- Automatically calls `build_daily_features.py` after backfill

**ProjectX (alternative source, not used for deep history):**
```bash
python pipeline/backfill_range.py YYYY-MM-DD YYYY-MM-DD
```
- Example: `python pipeline/backfill_range.py 2025-12-01 2026-01-09`
- Handles contract rollovers automatically
- Also calls `build_daily_features.py` after backfill

### Feature Building

```bash
python pipeline/build_daily_features.py YYYY-MM-DD
```
- Example: `python pipeline/build_daily_features.py 2025-01-10`
- Automatically called by backfill scripts
- Computes session stats (Asia/London/NY), ORBs, RSI
- Safe to re-run (upserts)

### Database Operations

**Initialize database schema:**
```bash
python pipeline/init_db.py
```

**Wipe all MGC data (bars_1m, bars_5m, daily_features):**
```bash
python pipeline/wipe_mgc.py
```

**Check database contents:**
```bash
python pipeline/check_db.py
```

**Query features:**
```bash
python analysis/query_features.py
```

### Testing & Inspection

**Inspect DBN files:**
```bash
python pipeline/inspect_dbn.py
```
- Configured to read from `dbn/` folder
- Shows schema, dataset, symbols, record counts

**Validate data:**
```bash
python pipeline/validate_data.py
```
- Validates data integrity and completeness

## Architecture

### Data Flow

```
Source → Normalize → Store → Aggregate → Feature Build
```

1. **Source**: Databento (GLBX.MDP3) or ProjectX API
2. **Normalize**: Convert to standard format with timezone handling
3. **Store**: Insert into DuckDB (`data/db/gold.db`)
4. **Aggregate**: Build 5-minute bars from 1-minute bars
5. **Feature Build**: Calculate daily ORBs, session stats, indicators

### Database Schema (DuckDB)

**bars_1m** (primary raw data):
- Columns: `ts_utc`, `symbol`, `source_symbol`, `open`, `high`, `low`, `close`, `volume`
- Primary key: `(symbol, ts_utc)`
- `symbol`: 'MGC' (continuous logical symbol)
- `source_symbol`: actual contract (e.g., 'MGCG4', 'MGCM4')

**bars_5m** (derived):
- Same columns as bars_1m
- Deterministically aggregated from bars_1m
- Bucket = floor(epoch(ts)/300)*300
- Fully rebuildable at any time

**daily_features**:
- One row per local trading day
- Primary key: `(date_local, instrument)` - ready for multi-instrument support
  - Currently: instrument always = 'MGC'
- Session high/low (Asia 09:00-17:00, London 18:00-23:00, NY 23:00-02:00)
- Pre-move travel (pre_ny_travel, pre_orb_travel)
- **All 6 ORBs stored**: Each ORB has 4 columns (high, low, size, break_dir)
  - `orb_0900_*`: 09:00-09:05 ORB
  - `orb_1000_*`: 10:00-10:05 ORB
  - `orb_1100_*`: 11:00-11:05 ORB
  - `orb_1800_*`: 18:00-18:05 ORB
  - `orb_2300_*`: 23:00-23:05 ORB
  - `orb_0030_*`: 00:30-00:35 ORB
- RSI at ORB (RSI_LEN=14, computed for 00:30 ORB)
- Missing ORBs stored as NULL (no crashes on weekends/holidays)

### Time & Calendar Model (CRITICAL)

**Trading Day Definition:**
- Local timezone: `Australia/Brisbane` (UTC+10, no DST)
- Trading day window: **09:00 local → next 09:00 local**
- All session windows (Asia/London/NY/ORBs) are evaluated inside that trading-day cycle
- Consistent across backfills, aggregations, and feature building

**Expected 1-Minute Counts:**
- Full weekday: ~1440 rows
- Partial holidays/roll days: fewer
- Weekends: 0 rows (expected)

### Futures Contract Handling

**Why you see MGCG4, MGCM4 when you trade MGC1!:**
- **MGC1!** = continuous front-month symbol (charting/broker convention)
- Databento returns **real contracts** (MGCG4, MGCM4, MGCV4, MGCG6, etc.)
- Pipeline automatically:
  - Selects front/most liquid contract per day (highest volume, excludes spreads)
  - Stitches them into continuous series
  - Stores under `symbol='MGC'` with `source_symbol=actual contract`
- This builds a tradeable continuous series required for proper historical backtesting

### ORB Break Rules

- Break detected when CLOSE is outside the ORB range (not touch)
- Direction: UP, DOWN, or NONE
- Uses 5-minute closes for detection (from bars_5m)

### Idempotency & Resume Behavior

All operations are safe to re-run:
- Backfills use `INSERT OR REPLACE` on primary key (will overwrite same timestamps, not duplicate)
- 5m aggregation: DELETE then INSERT for date range
- Feature building: upserts on `(date_local)`
- No duplicate rows possible

**Resume / Backwards backfill:**
- Re-running the same date range overwrites existing data (safe)
- To continue from where you stopped, run a new date range that picks up after the last successful day
- Backward backfill: run earlier start/end date ranges
- No automatic checkpoint - you control the date range on each invocation

## Configuration (.env)

Required environment variables:
- `DATABENTO_API_KEY`: Databento API key
- `DATABENTO_DATASET`: Default "GLBX.MDP3"
- `DATABENTO_SCHEMA`: Default "ohlcv-1m"
- `DATABENTO_SYMBOLS`: Default "MGC.FUT"
- `DUCKDB_PATH`: Default "data/db/gold.db"
- `SYMBOL`: Default "MGC"
- `TZ_LOCAL`: Default "Australia/Brisbane"
- `PROJECTX_USERNAME`, `PROJECTX_API_KEY`, `PROJECTX_BASE_URL`: For ProjectX backfills
- `PROJECTX_LIVE`: "false" for historical data

## Important Notes

1. **Databento availability**: `backfill_databento_continuous.py` has a hardcoded `AVAILABLE_END_UTC` to prevent 422 errors. Update this when Databento extends the dataset.

2. **Contract selection**: The pipeline automatically handles futures contract rolls by selecting the most liquid contract (highest volume, excluding spreads with '-' in symbol).

3. **5-minute bars**: Always rebuilt from 1-minute bars after backfill. Never manually edit bars_5m.

4. **Weekend/holiday handling**: Missing ORBs are stored as NULL. Scripts will not crash on days without data.

5. **Timezone awareness**: All timestamps in database are UTC (`TIMESTAMPTZ`). Session windows are defined in local time (Australia/Brisbane) then converted to UTC for queries.

6. **RSI calculation**: Uses Wilder's smoothing method with 14-period lookback. Calculated on 5-minute closes at 00:30 ORB.

7. **Data sources**:
   - Databento: Used for all historical backfill (recommended)
   - ProjectX: Optional, not used for deep history (limited historical range)
   - Raw DBN files stored in `dbn/` folder

8. **Schema migration**: The database has been migrated to store all 6 ORBs. If you have old data with the wrong trading day definition (00:00→00:00), you should wipe and rebuild:
   ```bash
   python pipeline/wipe_mgc.py
   python pipeline/backfill_databento_continuous.py 2020-12-20 2026-01-10
   ```

9. **Trading day change**: All backfill scripts now use 09:00→09:00 trading days (previously 00:00→00:00). This aligns with ORB strategy and session analysis. Old data will be incorrect.

10. **Project structure**: The codebase was comprehensively cleaned on Jan 15, 2026. See `PROJECT_STRUCTURE.md` for current file organization. All test/experiment files are in `_archive/` - the root directory contains only production-ready code (29 Python files, 11 markdown docs).

## ⚠️ CRITICAL: Database and Config Synchronization (NEVER VIOLATE THIS)

**MANDATORY RULE: NEVER update validated_setups database without IMMEDIATELY updating config.py in the same operation.**

### ⚠️ ALWAYS RUN THIS TEST AFTER ANY CHANGES:

```bash
python strategies/test_app_sync.py
```

**Run this test EVERY TIME after:**
- Updating `validated_setups` database
- Modifying `trading_app/config.py`
- Adding new MGC/NQ/MPL setups
- Changing ORB filters
- Running `populate_validated_setups.py`
- Updating RR values or SL modes

**If you forget to run this test, the apps will use WRONG values and cause REAL MONEY LOSSES in live trading.**

### Why This Is Critical

Mismatches between database and config.py cause:
- Apps use WRONG filters
- Accept trades that should be rejected
- Reject trades that should be accepted
- **REAL MONEY LOSSES in live trading**
- Dangerous and unacceptable

### Synchronization Protocol

When updating MGC setups in validated_setups table:

1. **FIRST**: Update `data/db/gold.db` → `validated_setups` table
2. **IMMEDIATELY AFTER**: Update `trading_app/config.py` → `MGC_ORB_SIZE_FILTERS` dictionary
3. **VERIFY**: Run `python strategies/test_app_sync.py` to confirm synchronization
4. **ONLY PROCEED**: If ALL TESTS PASS

**NEVER skip step 2. NEVER skip step 3. NEVER proceed if tests fail.**

### Files That Must Always Match Exactly

- `data/db/gold.db` → `validated_setups.orb_size_filter` (for MGC rows)
- `trading_app/config.py` → `MGC_ORB_SIZE_FILTERS` dictionary values

For each ORB time (0900, 1000, 1100, 1800, 2300, 0030):
- Database filter value MUST equal config.py filter value (within 0.001 tolerance)
- If database has NULL filter, config.py must have None
- If database has 0.05, config.py must have 0.05
- Zero tolerance for mismatches

### Verification Command

```bash
python strategies/test_app_sync.py
```

Expected output:
```
ALL TESTS PASSED!

Your apps are now synchronized:
- config.py has optimized MGC filters
- validated_setups database has 17 setups (6 MGC, 5 NQ, 6 MPL)
- setup_detector.py works with all instruments
- data_loader.py filter checking works
- All components load without errors

Your apps are SAFE TO USE!
```

**If this fails: STOP ALL WORK and fix the mismatch before proceeding.**

**REMINDER: This test is your safety net. Always run it after changes to database or config.**

### Other Synchronized Components

These files also depend on config.py and must be tested:
- `trading_app/setup_detector.py` - Reads validated_setups
- `trading_app/data_loader.py` - Uses config.py filters
- `trading_app/strategy_engine.py` - Uses config.py
- `trading_app/app_trading_hub.py` - Main app
- `unified_trading_app.py` - Unified app
- `MGC_NOW.py` - Quick helper

All must work with synchronized data.

### When Updating Any Instrument (MGC, NQ, MPL)

Same rules apply:
- Update database first
- Update corresponding config section immediately (MGC_ORB_SIZE_FILTERS, NQ_ORB_SIZE_FILTERS, or MPL_ORB_SIZE_FILTERS)
- **Run `python strategies/test_app_sync.py`**
- Verify all tests pass
- **Do NOT skip this step**

### Historical Context

On 2026-01-16, a critical error was discovered:
- `validated_setups` was updated with CORRECTED MGC values (after scan window bug fix)
- `config.py` was NOT updated (still had OLD audit values)
- This created a dangerous mismatch
- Apps would have used wrong RR values and filters in live trading (e.g., 1000 ORB RR=1.0 instead of 8.0!)
- Emergency fix required updating config.py and creating test_app_sync.py
- **System now has test_app_sync.py to prevent this from ever happening again**

**Lesson learned:** ALWAYS run `python strategies/test_app_sync.py` after ANY changes to strategies, filters, or configs.
