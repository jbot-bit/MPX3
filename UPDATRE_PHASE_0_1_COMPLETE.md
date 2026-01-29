# updatre.txt PHASE 0-1 Complete

**Timestamp:** 2026-01-29 12:33:00

---

## PHASE 0 — LOCATE & BASELINE ✅

### Repo Root
```
C:\Users\sydne\OneDrive\Desktop\MPX3
.git present: Yes
```

### Database File
```
Path: C:\Users\sydne\OneDrive\Desktop\MPX3\data\db\gold.db
Size: 725.26 MB
Exists: Yes
```

### Database Facts

**bars_1m (MGC):**
- MAX(ts_utc): `2026-01-29 12:23:00+10:00`
- COUNT(*): `724,570`
- Schema: (ts_utc, symbol, source_symbol, open, high, low, close, volume)

**daily_features (MGC):**
- MAX(date_local): `2026-01-15` ⚠️ **14 DAYS BEHIND**
- COUNT(*): `745`
- Schema: 112 columns (date_local, instrument, asia_high/low, london_high/low, orb_0900_*, orb_1000_*, etc.)

**Current Time:**
- UTC: `2026-01-29 02:32:35`
- Brisbane: `2026-01-29 12:32:35`
- **Data lag: 9.8 minutes** ✅ (acceptable, near real-time)

---

## PHASE 1 — IDENTIFY THE REAL UPDATE SCRIPT ✅

### Scripts Found
```
scripts/maintenance/update_market_data.py (Databento - BROKEN, API key invalid)
scripts/maintenance/update_market_data_projectx.py (ProjectX - WORKING) ✅
scripts/maintenance/test_update_script.py (test suite)
```

### The Working Script: `update_market_data_projectx.py`

**What it does:**

1. **Health check** - Auto-fixes WAL corruption
2. **Queries MAX(ts_utc)** - Gets latest bar timestamp from bars_1m
3. **Calculates range** - (latest + 1 min) to now (as Brisbane local dates)
4. **Calls ProjectX backfill** - `pipeline/backfill_range.py start_date end_date`
5. **Calls feature builder** - `pipeline/build_daily_features.py start_date end_date`
6. **Prints status** - Shows latest timestamps

**Source/API:** ProjectX API (via backfill_range.py)

**Write mode:** INSERT OR REPLACE (idempotent)

**Feature builder:** Yes, it DOES call `run_feature_builder()` at Step 4
- But likely failing (feature date is 14 days behind)
- Need to verify why

**Exit codes:**
- 0 = Success
- 1 = Failure (backfill or feature build failed)

---

## KEY FINDINGS

### ✅ What's Working
- Bars data is CURRENT (9.8 minute lag - acceptable)
- ProjectX API working
- Health check auto-fixing WAL corruption
- Update script has proper structure

### ⚠️ What's BROKEN
- **daily_features is 14 DAYS BEHIND** (2026-01-15 vs 2026-01-29)
- Feature builder is called but not updating
- Gap: 2026-01-16 to 2026-01-29 missing from daily_features

### Root Cause (Hypothesis)
Feature builder likely failing silently or being skipped. Need to:
1. Check build_daily_features.py CLI args
2. Verify it can handle the date range
3. Check for errors in feature build step

---

## NEXT: PHASE 2

**Goal:** Make daily_features auto-update reliably

**Requirements from updatre.txt:**
1. Compute feature build range safely (MAX date from daily_features)
2. Implement "honesty rule": REBUILD_TAIL_DAYS = 3 (catch late bars)
3. Make idempotent (INSERT OR REPLACE or DELETE+INSERT)
4. Exit non-zero on failure
5. Print status after: MAX(date_local) now

**Implementation target:** `scripts/maintenance/update_market_data_projectx.py`
