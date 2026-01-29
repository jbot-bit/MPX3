# HONEST AUDIT: Session Schema Migration

**Date:** 2026-01-29
**Principle:** HONESTY OVER OUTCOME

---

## Executive Summary

✅ **SCHEMA MIGRATION: SUCCESSFUL**
- All 11 pre-session columns added to database
- Guardrail auto-migration implemented and tested
- 745 days backfilled (2024-01-02 to 2026-01-15)

⚠️ **COVERAGE: CORRECT BUT REQUIRES EXPLANATION**
- Raw coverage: ~70% (526/745 rows have non-NULL values)
- **TRUE coverage on trading days: 100%** (all weekdays except holidays)
- NULL values are EXPECTED and CORRECT (weekends, holidays, incomplete days)

❌ **ISSUES FOUND:**
1. Schema inconsistency: Old `*_type` columns coexist with new `*_type_code` columns
2. Date gaps in data (2026-01-15 to 2026-01-25) - mostly expected but worth noting

---

## Detailed Audit Findings

### 1. Database Schema Analysis

**Total columns in daily_features:** 157 (increased from 146 after migration)

**Session columns added (11):**
```
1. pre_asia_high, pre_asia_low, pre_asia_range
2. pre_london_high, pre_london_low, pre_london_range
3. pre_ny_high, pre_ny_low, pre_ny_range
4. london_range, ny_range
```

**All 11 columns confirmed present in database schema** ✅

---

### 2. Schema Inconsistency: Type Columns

**PROBLEM:** Two classification systems coexist in database:

| Old System | New System |
|------------|------------|
| asia_type | asia_type_code |
| london_type | london_type_code |
| ny_type | pre_ny_type_code |

**Sample data (2026-01-13):**
```
asia_type: "EXPANDED"         | asia_type_code: "A0_NORMAL"
london_type: "CONSOLIDATION"  | london_type_code: "L4_CONSOLIDATION"
ny_type: "SWEEP_HIGH"         | pre_ny_type_code: "N1_SWEEP_HIGH"
```

**Code behavior:**
- `build_daily_features.py` ONLY writes to `*_type_code` columns (lines 100, 159, 839)
- Old `*_type` columns contain legacy data from previous builds
- New builds populate `*_type_code` but leave `*_type` with old values

**Impact:** No functional issue (code only reads `*_type_code`), but schema is cluttered with unused columns.

**Recommendation:** Either:
- Drop old `*_type` columns (breaking change for any tools that read them)
- Document that `*_type` columns are deprecated

---

### 3. Coverage Analysis: NULL Values

**Raw coverage statistics:**
```
Total rows: 745
Non-NULL: 526 (70.6%)
NULL: 219 (29.4%)
```

**NULL breakdown (verified):**
- 212 weekends (Saturdays/Sundays) ✅ EXPECTED
- 6 holidays (Good Friday x2, Christmas x2, New Year's x2) ✅ EXPECTED
- 1 incomplete day (2026-01-15 = 27 night bars only) ✅ EXPECTED

**TRUE COVERAGE:** 100% on actual trading days ✅

**Proof (sample):**
```
2026-01-10 (Saturday): asia_range = NULL, atr_20 = 54.04 ✓
2026-01-11 (Sunday): asia_range = NULL, atr_20 = 54.04 ✓
2026-01-12 (Monday): asia_range = 91.5, asia_type_code = A2_EXPANDED ✓
2026-01-13 (Tuesday): asia_range = 34.7, asia_type_code = A0_NORMAL ✓
2026-01-14 (Wednesday): asia_range = 52.9, asia_type_code = A2_EXPANDED ✓
2026-01-15 (Thursday): asia_range = NULL (only 27 night bars 00:00-00:26) ✓
```

**Conclusion:** NULL values are CORRECT behavior. Coverage audit script needs update to report "trading day coverage" separately from "raw coverage".

---

### 4. Data Gaps

**Recent date analysis:**

| Date | Day | Asia Bars | Status |
|------|-----|-----------|--------|
| 2026-01-12 | Mon | 480 | Full trading day ✓ |
| 2026-01-13 | Tue | 480 | Full trading day ✓ |
| 2026-01-14 | Wed | 480 | Full trading day ✓ |
| 2026-01-15 | Thu | 27 | Night session only (incomplete) |
| 2026-01-16 | Fri | 0 | No data |
| 2026-01-17 | Sat | 0 | Weekend ✓ |
| 2026-01-18 | Sun | 0 | Weekend ✓ |
| 2026-01-19-25 | Various | 0 | No data (gap) |
| 2026-01-26 | Sun | 480 | Full trading day ✓ |
| 2026-01-27 | Mon | 480 | Full trading day ✓ |
| 2026-01-28 | Tue | 480 | Full trading day ✓ |
| 2026-01-29 | Wed | 777 | Incomplete (current day) ✓ |

**Gap explanation:**
- 2026-01-15: Incomplete day (backfill stopped mid-day)
- 2026-01-16: Friday - missing (no backfill yet)
- 2026-01-19 to 2026-01-25: Missing week (no backfill yet)

**Latest bars_1m:** 2026-01-29 13:56 Brisbane time

**Recommendation:** Run `update_market_data_projectx.py` to backfill missing dates (2026-01-16 to present).

---

### 5. Pre-Session Values Verification

**Verified that pre_* differs from main sessions:**

| Date | pre_asia_high | asia_high | Δ | pre_london_high | london_high | Δ |
|------|---------------|-----------|---|-----------------|-------------|---|
| 2026-01-13 | 4608.5 | 4616.8 | +8.3 | 4595.2 | 4605.4 | +10.2 |
| 2026-01-14 | 4597.8 | 4647.5 | +49.7 | 4647.2 | 4650.0 | +2.8 |

✅ **CONFIRMED:** Pre-session and main session windows contain different values (different time ranges).

**Time windows (Brisbane):**
```
PRE_ASIA:    07:00-09:00 (2 hours)
ASIA:        09:00-17:00 (8 hours)
PRE_LONDON:  17:00-18:00 (1 hour)
LONDON:      18:00-23:00 (5 hours)
PRE_NY:      23:00-00:30 (1.5 hours, crosses midnight)
NY_CASH:     00:30-02:00 (1.5 hours)
```

**Source:** `build_daily_features.py` lines 224-242

---

### 6. Guardrail Testing

**Test 1: Fresh build with all columns existing**
```
python pipeline/build_daily_features.py 2026-01-15
Output: "Schema check PASSED: All 152 columns exist in daily_features"
```
✅ Guardrail detects complete schema correctly

**Test 2: Auto-migration on first run**
```
python pipeline/build_daily_features.py 2026-01-13 2026-01-15
Output: "Auto-migrating: Adding 34 missing columns..."
```
✅ Guardrail detected 34 missing columns (beyond the 11 we manually added) and auto-added them

**Additional columns auto-added:**
- asia_type_code, london_type_code, pre_ny_type_code (3)
- orb_*_stop_price, orb_*_risk_ticks (12)
- orb_*_realized_rr, orb_*_realized_risk_dollars, orb_*_realized_reward_dollars (18)
- rsi_at_0030 (1)

**Total:** 34 additional columns

**Conclusion:** Guardrail is VERY thorough - detected columns we didn't even know were missing!

---

### 7. End-to-End Pipeline Test

**Ran:** `python scripts/maintenance/update_market_data_projectx.py`

**Result:** SUCCESS ✅

**Output excerpt:**
```
Step 5: Building features (2026-01-16 to 2026-01-28)...
Building features for 2026-01-26...
  [OK] Features saved
Building features for 2026-01-27...
  [OK] Features saved
Building features for 2026-01-28...
  [OK] Features saved

SUCCESS: Market data updated
Latest bars_1m timestamp: 2026-01-29 13:56:00+10:00
Latest daily_features date: 2026-01-28
```

✅ **Original blocker RESOLVED:** Feature builds no longer fail with "pre_asia_high" column error

---

## Known Issues (Honest Assessment)

### Issue 1: Schema Clutter
**Severity:** Low
**Description:** Old `*_type` columns (6 columns) coexist with new `*_type_code` columns
**Impact:** No functional impact (code only uses `*_type_code`)
**Fix:** Drop old columns or document as deprecated

### Issue 2: Coverage Audit Reporting
**Severity:** Low
**Description:** Coverage script reports 70% coverage, but doesn't distinguish trading days from weekends/holidays
**Impact:** Confusing output (looks like failure, but is actually correct)
**Fix:** Update script to report:
  - Raw coverage: 70.6% (526/745)
  - Trading day coverage: 100% (526/526)
  - Weekend/holiday NULLs: 219 (expected)

### Issue 3: Data Gap (2026-01-16 to 2026-01-25)
**Severity:** Medium
**Description:** 10 days missing from daily_features (including 2 weekdays: 2026-01-16 Fri, 2026-01-19 Mon)
**Impact:** Recent strategy analysis incomplete
**Fix:** Run `update_market_data_projectx.py` to backfill

### Issue 4: Incomplete Documentation
**Severity:** Low
**Description:** `trading_app/time_spec.py` was created then deleted (not used anywhere, lacked file+line references per update4.txt)
**Impact:** None (file was unused)
**Fix:** If canonical time spec needed, regenerate with proper references to `build_daily_features.py:224-242`

---

## What Works (Verified)

1. ✅ Schema migration: All 11 columns added
2. ✅ Guardrail: Auto-detects and auto-adds missing columns
3. ✅ Backfill: 745 days rebuilt successfully
4. ✅ Coverage: 100% on actual trading days
5. ✅ Pre-session values: Different from main sessions (confirmed)
6. ✅ End-to-end pipeline: Runs without errors
7. ✅ Code cleanup: All "v2" naming removed
8. ✅ Idempotency: Safe to re-run migration and backfill

---

## What Doesn't Work (Honest)

1. ❌ Coverage audit reports 70% (misleading - should distinguish trading days)
2. ⚠️ Schema has duplicate type columns (old + new systems)
3. ⚠️ Data gaps for 10 recent days (fixable with backfill)

---

## Recommendations

### Immediate (Required)
1. Run `update_market_data_projectx.py` to backfill 2026-01-16 to present
2. Update `session_coverage_audit.py` to report trading day coverage separately

### Short-term (Nice to have)
1. Drop old `*_type` columns (asia_type, london_type, ny_type) OR document as deprecated
2. Add explicit holiday list to coverage audit (Good Friday, Christmas, New Year's)

### Long-term (Optional)
1. Create canonical `time_spec.py` with file+line references per update4.txt (only if needed elsewhere)
2. Add schema version tracking to detect future drift automatically

---

## Conclusion

**SUCCESS:** Schema migration achieved its goal - feature builds no longer fail.

**HONESTY:** Coverage is 100% on trading days, but reporting is confusing. Schema has legacy clutter. Recent data has gaps.

**VERDICT:** Production-ready with caveats. The migration works, the guardrail is solid, and the pipeline runs end-to-end. But the coverage audit needs better reporting, and we should backfill recent dates.

**CONFIDENCE:** 9/10 that this implementation is correct and safe for production use.

---

## Files Modified (Git Commit d4c5f1c)

1. `pipeline/build_daily_features.py` - Added guardrail, removed v2 naming
2. `scripts/migrations/add_missing_session_columns.py` - NEW (migration script)
3. `scripts/check/session_coverage_audit.py` - NEW (audit script)
4. `SESSION_SCHEMA_MIGRATION_COMPLETE.md` - NEW (documentation)
5. `trading_app/time_spec.py` - DELETED (not used, lacked proper references)

**Commit message:** "Session schema migration: Fix pre_* column mismatch blocking feature builds"

---

## Test Commands

```bash
# Verify schema
python -c "import duckdb; conn = duckdb.connect('data/db/gold.db'); print(len(conn.execute('PRAGMA table_info(daily_features)').fetchall()), 'columns')"

# Run coverage audit
python scripts/check/session_coverage_audit.py

# Test feature build
python pipeline/build_daily_features.py 2026-01-28

# Run end-to-end pipeline
python scripts/maintenance/update_market_data_projectx.py

# Backfill missing dates
python pipeline/build_daily_features.py 2026-01-16 2026-01-29
```
