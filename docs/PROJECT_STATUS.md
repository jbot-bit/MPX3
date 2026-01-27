# PROJECT STATUS - CANONICAL VERSION

**Date:** 2026-01-25 12:06 PM
**Location:** `C:\Users\sydne\OneDrive\Desktop\MPX2_fresh`
**Status:** ✅ **THIS IS THE CANONICAL VERSION**

---

## ✅ Confirmed: This is the correct project

### Git History:
```
78e4b59 Clean up: Remove temp_gemini directory
4cfd921 Fix batch files to run from correct directory and show progress timestamps
2202e1e Add comprehensive edge discovery documentation
23e4e1b Add database-design skill and complete database restoration
22f2664 Add Research Lab, Trading Terminal, and Skills integration
8737167 Remove secrets file and ignore env files
a53a7bf Initial commit
```

### Database:
- **Location:** `data/db/gold.db`
- **Size:** 690 MB
- **Restored:** Jan 25, 2026 11:52 AM
- **Contents:** 720,227 bars, 740 daily features, 19 validated setups
- **Status:** ✅ All sync tests passing

### Skills Integrated:
1. ✅ `skills/frontend-design/` - Trading UI design patterns
2. ✅ `skills/mcp-builder/` - MCP server development
3. ✅ `skills/mobile-android-design/` - Android Material Design 3
4. ✅ `skills/database-design/` - Database schema design & migrations

### New Features (Jan 25):
1. ✅ Edge Discovery Engine (`edge_discovery_live.py`)
2. ✅ Research Lab App (`trading_app/app_research_lab.py`)
3. ✅ Trading Terminal App (`trading_app/app_trading_terminal.py`)
4. ✅ Database migration tools
5. ✅ Auto-restarting batch files

---

## 🗑️ MPX2_clean Status: ARCHIVED/DELETED

**Reason:** Outdated version with no unique content

**Last commit:** `0733b3a Sync local MPX2_fresh` (literally syncing FROM this project!)

**What it had:**
- Older database (Jan 24)
- Only 2 commits
- NO unique files
- Missing all Jan 25 work

**Decision:** Safe to delete

---

## 📊 Current System Status

### Database:
```
✅ bars_1m: 720,227 rows (2024-01-02 to 2026-01-15)
✅ daily_features_v2: 740 rows
✅ validated_setups: 19 setups (8 MGC, 6 MPL, 5 NQ)
✅ All tables: 32 tables loaded
```

### Sync Status:
```
✅ test_app_sync.py: ALL TESTS PASSED
✅ config.py ↔ validated_setups: SYNCHRONIZED
✅ SetupDetector: Loaded 8 MGC setups
✅ Apps: Safe to use
```

### Git Status:
```
✅ Clean working tree
✅ All changes committed
✅ 7 commits total
✅ No uncommitted files
```

---

## 🚀 Ready to Use

### Launch Edge Discovery:
```powershell
cd C:\Users\sydne\OneDrive\Desktop\MPX2_fresh
python edge_discovery_live.py

# Or double-click:
RUN_EDGE_DISCOVERY.bat
```

### Launch Apps:
```powershell
# Research Lab (Primary)
streamlit run trading_app/app_research_lab.py

# Trading Terminal (Secondary)
streamlit run trading_app/app_trading_terminal.py
```

### Run Tests:
```powershell
# Critical sync test
python test_app_sync.py

# Database check
python pipeline/check_db.py

# Query features
python analysis/query_features.py
```

---

## 📁 Project Structure

### Core Directories:
- `trading_app/` - Main apps (46 Python files)
- `pipeline/` - Data backfill & processing (14 files)
- `analysis/` - Analysis tools (6 files)
- `audits/` - Validation scripts (11 files)
- `research/` - Research & backtesting (8 files)
- `strategies/` - Strategy execution (2 files)
- `ml/` - Machine learning (training, inference, monitoring)
- `skills/` - Anthropic skills (4 skills)
- `data/` - Database & exports
- `docs/` - Documentation

### Key Files:
- `CLAUDE.md` - Main project guide
- `test_app_sync.py` - Critical sync validator
- `edge_discovery_live.py` - Edge discovery engine
- `migrate_database_schema.py` - Database migration tool

---

## 🎯 Top Strategies (Validated)

| Rank | Setup | RR | SL | E[R] | Trades | Annual R |
|------|-------|----|----|------|--------|----------|
| 1 | MGC CASCADE | 4.0 | DYNAMIC | +1.950 | 69 | ~135R |
| 2 | MGC SINGLE_LIQ | 3.0 | DYNAMIC | +1.440 | 118 | ~170R |
| 3 | MGC 2300 ORB | 1.5 | HALF | +0.403 | 522 | ~105R |
| 4 | MGC 1000 ORB | 8.0 | FULL | +0.378 | 516 | ~98R |
| 5 | MPL 1100 ORB | 1.0 | FULL | +0.346 | 254 | ~88R |

**Total System:** ~600R/year (up from 400R/year after scan window bug fix)

---

## ⚠️ Critical Reminders

### ALWAYS Run After Database Changes:
```bash
python test_app_sync.py
```

This validates config.py ↔ validated_setups synchronization.

### Never:
- ❌ Edit validated_setups without updating config.py
- ❌ Edit config.py without running test_app_sync.py
- ❌ Skip the sync test after ANY strategy changes
- ❌ Use MPX2_clean (it's outdated)

### Always:
- ✅ Work in THIS directory (MPX2_fresh)
- ✅ Run test_app_sync.py after changes
- ✅ Commit changes to git
- ✅ Use skills for specialized tasks

---

## 📚 Documentation

**Getting Started:**
- `README_START_HERE.md` - Quick start guide
- `QUICK_START_EDGE_DISCOVERY.md` - Edge discovery guide
- `RESEARCH_LAB_GUIDE.md` - Research Lab usage

**Technical:**
- `DATABASE_RESTORED.md` - Database restoration details
- `MERGE_COMPLETE.md` - Project merge analysis
- `docs/SCAN_WINDOW_BUG_FIX_SUMMARY.md` - System improvement history
- `docs/MCP_INTEGRATION_PLAN.md` - API integration plan

**Skills:**
- `skills/*/SKILL.md` - Each skill has detailed documentation

---

**Last Updated:** 2026-01-25 12:06 PM
**Status:** ✅ READY FOR PRODUCTION USE
**Version:** Canonical (MPX2_fresh)
