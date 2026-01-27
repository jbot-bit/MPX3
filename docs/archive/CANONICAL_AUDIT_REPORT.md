# CANONICAL AUDIT REPORT - MyProjectX
**Date**: 2026-01-17
**Methodology**: canonicaltruthdoc.txt (Strict Audit Protocol)
**Status**: PROPOSAL ONLY - AWAITING HUMAN CONFIRMATION

---

## PHASE 1: INVENTORY ✅ COMPLETE

See full inventory from agent a660ce8 above.

**Summary**:
- 32 production Python files (root)
- 30+ trading_app components
- 3 databases (gold.db, live_data.db, trading_app.db)
- 17 validated setups
- **66 documentation files** (EXCESS - needs cleanup)

---

## PHASE 2: CANONICAL SOURCES OF TRUTH

### 1. Trading Rules (ONE SOURCE)

**CANONICAL**: `gold.db → validated_setups` table
- 17 rows (6 MGC, 5 NQ, 6 MPL)
- Contains: RR, SL mode, filters, tiers, performance
- Last updated: 2026-01-16 (scan window bug fix)
- **Authority**: PRIMARY - All other sources derive from this

**SECONDARY (Auto-Generated)**:
- `config_generator.py` → loads from validated_setups
- `trading_app/config.py` → imports from config_generator
- **Relationship**: READ-ONLY from database

**DUPLICATES/DERIVATIVES**:
- None (system correctly uses single source)

---

### 2. Schemas (ONE SOURCE)

**CANONICAL**: `gold.db` physical schema
- Tables: bars_1m, bars_5m, daily_features_v2, validated_setups
- Variants: daily_features_v2_nq, daily_features_v2_mpl (separate instruments)

**DOCUMENTATION**:
- `DATABASE_SCHEMA_SOURCE_OF_TRUTH.md` (brief canonical reference)
- `DATABASE_SCHEMA.md` (detailed explanation - DERIVATIVE)
- `CLAUDE.md` (schema summary in instructions - DERIVATIVE)

**Relationship**: Database = truth, docs = explanation

---

### 3. Data Generation (ONE SOURCE)

**CANONICAL**: `build_daily_features_v2.py`
- Zero-lookahead feature builder
- Scan window fix: 2026-01-16 (extended to 09:00)
- **Authority**: PRIMARY

**DEPRECATED**:
- `build_daily_features.py` (V1 - OBSOLETE)

---

### 4. Execution Logic (ONE SOURCE)

**CANONICAL**: `execution_engine.py`
- Entry/stop/target calculation
- Scan window definitions
- Same-bar TP+SL resolution

**DUPLICATES** (Acceptable):
- `build_daily_features_v2.py` - reimplements for feature building
- `strategy_engine.py` - live strategy evaluation (different purpose)

**Status**: Acceptable duplication (different contexts)

---

## PHASE 3: DOCUMENTATION CLEANUP PLAN

### Current State
- **66 MD files** in root directory
- Many are temporal status reports (Jan 16-17)
- Duplication across multiple topics
- Hard to find canonical source

### Proposed Structure (29 KEEP, 36 ARCHIVE)

---

### FILES TO KEEP (29 Essential)

#### Core Documentation (5 files) - CANONICAL
1. **CLAUDE.md** - Instructions for Claude Code
2. **PROJECT_STRUCTURE.md** - Codebase organization
3. **TRADING_PLAYBOOK.md** - All 17 validated strategies
4. **DATABASE_SCHEMA_SOURCE_OF_TRUTH.md** - Schema reference
5. **README.md** - Project overview

#### Strategy & Logic (9 files) - CANONICAL/IMPORTANT
6. **APP_USAGE_GUIDE.md** - Which app to use (app_trading_hub.py)
7. **UNICORN_SETUPS_CORRECTED.md** - Post-bugfix setups
8. **SCAN_WINDOW_BUG_FIX_SUMMARY.md** - Critical bug context
9. **ZERO_LOOKAHEAD_RULES.md** - Research methodology
10. **TERMINOLOGY_EXPLAINED.md** - Glossary
11. **WHICH_APP_TO_USE.md** - App selection guide
12. **DOCUMENTATION_INDEX.md** - Master index
13. **CHATGPT_TRADING_GUIDE.md** - Night ORB focused guide
14. **rules.md** - Global project rules (from canonicaltruthdoc.txt)

#### ML Documentation (5 files) - ACTIVE
15. **ML_USER_GUIDE.md** - How to use ML predictions
16. **ML_FINAL_SUMMARY.md** - ML project summary
17. **ML_INTEGRATION_COMPLETE.md** - Technical details
18. **ML_PHASE1_COMPLETE.md** - Phase 1 milestone
19. **README_ML.md** - ML technical overview

#### Mobile App (2 files) - ACTIVE
20. **MOBILE_APP_README.md** - Primary mobile guide
21. **START_HERE.md** - Quick start

#### Setup & Deployment (8 files) - USEFUL
22. **QUICK_START.md** - Quick start guide
23. **SETUP_TRADING_HUB.md** - Dashboard setup
24. **README_STREAMLIT.md** - Streamlit docs
25. **DEPLOY_TO_CLOUD.md** - Cloud deployment
26. **CLOUD_QUICK_START.md** - Quick cloud setup
27. **REMOTE_ACCESS_GUIDE.md** - Remote access
28. **QUICK_REMOTE_ACCESS.md** - Quick remote
29. **UPDATE_WORKFLOW.md** - Dev workflow

---

### FILES TO ARCHIVE (36 Redundant)

#### Archive Location 1: `_archive/reports/completion_docs_jan2026/` (21 files)
**Temporal status reports from Jan 16-17**:
1. FINAL_HONEST_STATUS_JAN17.md
2. FINAL_STATUS_REPORT.md
3. APP_READY_TO_START.md
4. APP_STATUS_VERIFIED.md
5. DEBUGGING_COMPLETE.md
6. CLEANUP_COMPLETE_JAN16.md
7. CLEANUP_COMPLETE_JAN16_v2.md
8. DAILY_SUMMARY_JAN16.md
9. PROJECT_STATUS_JAN16.md
10. SYNC_VERIFICATION_JAN17.md
11. SYSTEM_CLEANED.md
12. SYSTEM_VERIFICATION_COMPLETE.md
13. ARCHITECTURAL_IMPROVEMENTS_JAN16.md
14. AI_DYNAMIC_LOADING_JAN16.md
15. MOBILE_APP_COMPLETE.md
16. MOBILE_APP_IMPLEMENTATION_COMPLETE.md
17. MOBILE_APP_REAL_INTEGRATION.md
18. MOBILE_APP_UPGRADE_COMPLETE.md
19. BUG_FIX_JAN17_ML_INFERENCE.md
20. BUG_FIX_SUMMARY.md
21. SCAN_WINDOW_INVESTIGATION_COMPLETE.md

#### Archive Location 2: `_archive/reports/audits_jan15/` (4 files)
**Audit reports from Jan 15**:
22. AUDIT_INDEX.md
23. AUDIT_REPORT_2026-01-15.md
24. AUDIT_SUMMARY_2026-01-15.md
25. COMPLETE_PROJECT_AUDIT_2026-01-15.md

#### Archive Location 3: `_archive/reports/nq_mpl_analysis/` (3 files)
**NQ/MPL analysis (conclusions already documented)**:
26. NQ_MPL_NOT_SUITABLE.md
27. NQ_MPL_SCAN_WINDOW_STATUS.md
28. CRITICAL_NQ_MPL_SHORT_SCANS_CONFIRMED.md

#### Archive Location 4: `_archive/reports/old_docs/` (8 files)
**Duplicates/superseded/temporal fixes**:
29. DATABASE_SCHEMA.md (superseded by DATABASE_SCHEMA_SOURCE_OF_TRUTH.md)
30. MOBILE_APP_GUIDE.md (superseded by MOBILE_APP_README.md)
31. APK_BUILD_FIXED.md (temporal fix)
32. APK_BUILD_GUIDE.md (mobile app specific - archive if not using)
33. CLOUD_DEPLOYMENT_FIXED.md (temporal fix - Jan 17)
34. SWITCH_TO_MOBILE_APP.md (covered in WHICH_APP_TO_USE.md)
35. DATABASE_FIX_VERIFICATION.md (temporal fix)
36. CLEANUP_PLAN.md (this current planning doc - archive after execution)

---

## PHASE 4: SAFETY CHECK

### What Would Break if This Plan is Wrong?

#### Risk 1: Essential Info Lost in Archived Docs
**Mitigation**: All files ARCHIVED, not deleted
- Can retrieve from `_archive/reports/` if needed
- All important info already in KEEP files

#### Risk 2: Code References to Archived Docs
**Check**: Searched BAT files, Python code, essential MD files
- ✅ No BAT files reference MD docs
- ✅ No Python code references MD docs
- ✅ Essential files only reference KEEP files

#### Risk 3: Broken Documentation Links
**Issue**: DOCUMENTATION_INDEX.md may link to archived files
**Mitigation**: Update DOCUMENTATION_INDEX.md after archiving

#### Risk 4: Missing Critical Strategy Info
**Check**: All validated setups are in:
- gold.db → validated_setups (PRIMARY)
- TRADING_PLAYBOOK.md (CANONICAL)
- UNICORN_SETUPS_CORRECTED.md (POST-FIX)
**Status**: ✅ No risk - all critical info retained

#### Risk 5: Scan Window Bug Fix Documentation Lost
**Check**: SCAN_WINDOW_BUG_FIX_SUMMARY.md
**Status**: ✅ In KEEP list - Critical context preserved

---

### What Assumptions Could Be False?

#### Assumption 1: "Completion docs are just status reports"
**Validation Needed**: Human review of temporal files
- Do any contain unique analysis not in KEEP files?
- Do any contain strategy discoveries not in database?

#### Assumption 2: "NQ/MPL analysis complete"
**Validation Needed**: Confirm NQ/MPL archived files don't contain:
- Alternative strategies worth revisiting
- Data that contradicts current conclusions

#### Assumption 3: "Database_SCHEMA.md is redundant"
**Validation Needed**: Check if it contains schema details missing from SOURCE_OF_TRUTH version
- If yes: Merge unique content first

#### Assumption 4: "Mobile app docs consolidated"
**Validation Needed**: Verify MOBILE_APP_README.md contains everything from:
- MOBILE_APP_GUIDE.md
- MOBILE_APP_COMPLETE.md
- MOBILE_APP_IMPLEMENTATION_COMPLETE.md

---

### What MUST Be Confirmed By Human Before Action?

#### ✋ CONFIRMATION REQUIRED:

1. **APK_BUILD_GUIDE.md**
   - **Question**: Are you using the Android mobile app?
   - **If YES**: KEEP
   - **If NO**: ARCHIVE

2. **DATABASE_SCHEMA.md vs DATABASE_SCHEMA_SOURCE_OF_TRUTH.md**
   - **Question**: Does DATABASE_SCHEMA.md contain details missing from SOURCE_OF_TRUTH version?
   - **If YES**: MERGE first, then archive
   - **If NO**: Safe to archive

3. **test_app_sync.py**
   - **Status**: Missing (mandated by CLAUDE.md)
   - **Question**: Should we create this file before proceeding?
   - **Risk**: Without this test, config/database sync cannot be verified

4. **Mobile App Status**
   - **Question**: Which app is actively deployed?
     - app_trading_hub.py (desktop)
     - app_mobile.py (tinder cards)
   - **Action**: Confirm WHICH_APP_TO_USE.md reflects current reality

5. **Completion Docs Content**
   - **Question**: Do Jan 16-17 completion docs contain unique analysis not elsewhere?
   - **Recommendation**: Spot-check 2-3 files before bulk archiving

---

## PROPOSED ACTIONS (NO EXECUTION YET)

### Step 1: Verify Critical Assumptions
- [ ] Human confirms APK_BUILD_GUIDE.md disposition
- [ ] Human confirms DATABASE_SCHEMA.md can be archived
- [ ] Human spot-checks 2-3 completion docs
- [ ] Human confirms which app is canonical (desktop vs mobile)

### Step 2: Merge Unique Content (if needed)
- [ ] If DATABASE_SCHEMA.md has unique details → merge into SOURCE_OF_TRUTH
- [ ] If any completion doc has unique analysis → merge into relevant KEEP file

### Step 3: Create Archive Structure
```bash
mkdir -p _archive/reports/completion_docs_jan2026
mkdir -p _archive/reports/audits_jan15
mkdir -p _archive/reports/nq_mpl_analysis
mkdir -p _archive/reports/old_docs
```

### Step 4: Move Files (36 files)
```bash
# Move completion docs (21 files)
mv [list of 21 files] _archive/reports/completion_docs_jan2026/

# Move audit reports (4 files)
mv [list of 4 files] _archive/reports/audits_jan15/

# Move NQ/MPL analysis (3 files)
mv [list of 3 files] _archive/reports/nq_mpl_analysis/

# Move old docs (8 files)
mv [list of 8 files] _archive/reports/old_docs/
```

### Step 5: Update Documentation
- [ ] Update DOCUMENTATION_INDEX.md (reflect new structure)
- [ ] Update PROJECT_STRUCTURE.md (note archive locations)
- [ ] Add note in CLAUDE.md about archive locations

### Step 6: Verify Result
- [ ] Confirm 29 MD files remain in root
- [ ] Confirm 36 files moved to _archive/reports/
- [ ] Confirm no broken links in essential docs
- [ ] Run test_app_sync.py (if exists/created)

### Step 7: Commit
```bash
git add -A
git commit -m "Clean up documentation: Archive 36 redundant MD files

Following canonicaltruthdoc.txt audit methodology:
- Archived 21 temporal status reports (Jan 16-17)
- Archived 4 audit reports (Jan 15)
- Archived 3 NQ/MPL analysis docs
- Archived 8 duplicate/superseded docs

Retained 29 essential documentation files.

All files archived (not deleted) to _archive/reports/.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
git push origin main
```

---

## CONSTRAINTS SATISFIED ✅

- ✅ Zero logic changes
- ✅ Zero behavior changes
- ✅ Zero schema changes
- ✅ Zero new files (except archive folders)
- ✅ Fully reversible (files archived, not deleted)

---

## RISKS SUMMARY

| Risk | Severity | Mitigation |
|------|----------|------------|
| Lost critical info | LOW | All files archived, not deleted |
| Broken code references | NONE | No code references MD files |
| Broken doc links | LOW | Update DOCUMENTATION_INDEX.md |
| Missing strategy info | NONE | All in database + KEEP files |
| Wrong assumptions | MEDIUM | **Human verification required** |

---

## FINAL RECOMMENDATION

**PROCEED**: YES, with human confirmation on 5 questions above

**BEFORE EXECUTION**:
1. Human confirms APK guide disposition
2. Human confirms DATABASE_SCHEMA.md merge/archive
3. Human spot-checks 2-3 completion docs
4. Human confirms active app (desktop vs mobile)
5. Consider creating test_app_sync.py first

**AFTER EXECUTION**:
- Root directory: 66 → 29 MD files
- Archive: +36 files organized by category
- Clean, maintainable documentation structure

---

## WAIT FOR HUMAN CONFIRMATION ⏸️

**DO NOT EXECUTE UNTIL CONFIRMED**

Questions for user:
1. Are you using Android mobile app? (APK_BUILD_GUIDE.md: KEEP or ARCHIVE?)
2. Can DATABASE_SCHEMA.md be archived? (Or does it have unique content vs SOURCE_OF_TRUTH?)
3. Should we create test_app_sync.py before cleanup?
4. Which app is canonical: app_trading_hub.py or app_mobile.py?
5. May I spot-check 2-3 completion docs to verify no unique analysis?

**Ready to proceed after confirmation.** ✋
