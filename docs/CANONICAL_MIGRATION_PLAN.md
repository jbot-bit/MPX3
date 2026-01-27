# CANONICAL RR MIGRATION PLAN - MGC ONLY

**Date:** 2026-01-26
**Status:** Phase 1 COMPLETE, Phase 2 READY TO BEGIN
**Scope:** MGC instrument only (6 setups)

---

## CHECKPOINT CREATED

**Git Commit:** 1ecc314
**Database Backup:** `gold.db.backup_pre_canonical_20260126_165453`
**Backup Size:** 690MB

**Rollback Instructions (if needed):**
```bash
# Restore database
cp gold.db.backup_pre_canonical_20260126_165453 gold.db

# Revert code
git revert 1ecc314
```

---

## PHASE 1 VALIDATION - COMPLETED ✅

**Script:** `scripts/analyze/theoretical_vs_realized_analysis.py`

**MGC Results (ALL SURVIVE):**
- 0900 ORB RR=1.5: +0.245R (was +0.120R)
- 1000 ORB RR=1.5: +0.369R (was +0.257R)
- 1000 ORB RR=2.0: +0.643R (was +0.215R)
- 1000 ORB RR=2.5: +0.916R (was +0.132R)
- 1000 ORB RR=3.0: +1.190R (was +0.132R) ⭐ **Best**
- 1800 ORB RR=1.5: +0.256R (was +0.125R)

**Key Finding:** Realized RR drops 33% on average, BUT expectancy IMPROVES because old system underestimated edge strength.

**NQ/MPL Results:** BLOCKED - need instrument-specific cost models (NQ has $0.50/point, not $10/point)

---

## PHASE 2 IMPLEMENTATION - IN PROGRESS 🚧

### Task 2.1: Create cost_model.py Module

**Location:** `pipeline/cost_model.py`

**Purpose:**
- Centralized cost definitions per instrument
- Canonical realized RR calculation
- Support for multiple instruments (MGC now, NQ/MPL future)

**Functions:**
```python
get_instrument_specs(instrument: str) -> dict
get_cost_model(instrument: str) -> dict
calculate_realized_rr(instrument: str, stop_points: float, rr_theoretical: float) -> dict
calculate_expectancy(win_rate: float, realized_rr: float) -> float
```

---

### Task 2.2: Update execution_engine.py

**File:** `execution_engine.py`

**Changes:**
1. Import cost_model module
2. Add `realized_rr` calculation alongside theoretical RR
3. Store both theoretical + realized RR in results
4. Use realized RR for expectancy calculations
5. Add `realized_risk_$` and `realized_reward_$` to output

**Backward compatibility:** Keep theoretical RR columns, add new realized columns

---

### Task 2.3: Update Database Schema

**Table:** `daily_features`

**New Columns (for each ORB time: 0900, 1000, 1100, 1800, 2300, 0030):**
```sql
ALTER TABLE daily_features ADD COLUMN orb_XXXX_realized_rr DOUBLE;
ALTER TABLE daily_features ADD COLUMN orb_XXXX_realized_risk_dollars DOUBLE;
ALTER TABLE daily_features ADD COLUMN orb_XXXX_realized_reward_dollars DOUBLE;
```

**Total:** 18 new columns (3 columns × 6 ORB times)

**Note:** Initial migration added `orb_XXXX_realized_expectancy` columns, but these are **DEPRECATED** and remain NULL. Expectancy is a **strategy-level metric** (requires win rate across multiple trades), not a trade-level metric. Expectancy is calculated and stored in `validated_setups` table instead.

---

### Task 2.4: Rebuild Daily Features

**Script:** `pipeline/build_daily_features.py`

**Changes:**
1. Import cost_model module
2. Calculate realized metrics for each ORB
3. Store realized_rr, risk_$, reward_$, expectancy
4. Rebuild for MGC only (745 days, 2024-01-02 to 2026-01-15)

**Command:**
```bash
python pipeline/build_daily_features.py 2024-01-02
```

---

### Task 2.5: Update validated_setups Table

**Changes:**
- Add `realized_rr` column
- Add `realized_expectancy` column
- Populate for 6 MGC setups with Phase 1 results

**Keep:** theoretical RR in `rr` column (backward compatibility)

---

### Task 2.6: Update Trading Apps

**Files to update:**
- `trading_app/config.py` - Add realized RR thresholds
- `trading_app/setup_detector.py` - Use realized RR for filtering
- `trading_app/strategy_engine.py` - Display realized metrics
- `trading_app/app_trading_hub.py` - Show realized RR in UI
- `unified_trading_app.py` - Update displays
- `MGC_NOW.py` - Show realized expectancy

**Test:** `python test_app_sync.py` (ensure sync maintained)

---

### Task 2.7: Update Documentation

**Files:**
- `CANONICAL_LOGIC.txt` - Mark as ACTIVE
- `COST_MODEL_MGC_TRADOVATE.txt` - Mark as PRODUCTION
- `CLAUDE.md` - Update feature building section
- `PROJECT_STRUCTURE.md` - Document new cost_model.py

---

## PHASE 3 RE-VALIDATION - TODO 📋

**After implementation:**
1. Run `python scripts/analyze/theoretical_vs_realized_analysis.py` again
2. Verify realized RR stored correctly in database
3. Compare results: analysis vs database (should match exactly)
4. Run full backtest with realized RR
5. Verify expectancy calculations correct

---

## PHASE 4 DEPLOYMENT - TODO 📋

1. Run test_app_sync.py (MUST PASS)
2. Test all trading apps with new data
3. Verify UI displays realized metrics correctly
4. Update strategy documentation
5. Create operator guide for realized RR
6. Mark as production-ready

---

## FUTURE: NQ/MPL MIGRATION - BLOCKED 🛑

**Prerequisites:**
1. Get NQ contract specs (point value, tick size, tick value)
2. Get MPL contract specs (point value, tick size, tick value)
3. Get NQ cost model (real broker data if available)
4. Get MPL cost model (real broker data if available)
5. Update cost_model.py with NQ/MPL specs
6. Re-run Phase 1 validation
7. Proceed if edges survive

**Until then:** NQ/MPL setups remain in validated_setups with theoretical RR only

---

## MIGRATION SAFETY CHECKLIST

Before deploying to production:

- [x] Git checkpoint created
- [x] Database backup created
- [x] Phase 1 validation complete (MGC survives)
- [x] cost_model.py created
- [x] execution_engine.py updated
- [x] Schema updated with realized columns (18 active, 6 deprecated)
- [x] Daily features rebuilt (745 days, 99.6%+ coverage)
- [x] Architectural clarification: expectancy belongs in validated_setups (not daily_features)
- [ ] validated_setups updated with realized expectancy
- [ ] Trading apps updated to display realized metrics
- [ ] test_app_sync.py passes
- [ ] UI displays realized metrics
- [ ] Documentation updated
- [ ] Operator guide created

**Current Status:** 8/14 complete (57%)

---

## ROLLBACK PLAN

If canonical migration causes issues:

**Step 1: Restore database**
```bash
cp gold.db.backup_pre_canonical_20260126_165453 gold.db
```

**Step 2: Revert code**
```bash
git revert HEAD
```

**Step 3: Verify rollback**
```bash
python test_app_sync.py
python pipeline/check_db.py
```

**Step 4: Resume from checkpoint**
- Review what went wrong
- Fix issues
- Re-run validation
- Try again

---

## CONTACT / QUESTIONS

**Migration Owner:** User + Claude Code
**Technical Docs:** CANONICAL_LOGIC.txt, COST_MODEL_MGC_TRADOVATE.txt
**Validation Script:** scripts/analyze/theoretical_vs_realized_analysis.py
**Checkpoint Commit:** 1ecc314

**Status Updates:** Track progress in this document
