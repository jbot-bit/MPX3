# Edge Discovery Lab - TODO List

**Date:** 2026-01-27
**Status:** IN PROGRESS (60% complete)

---

## ✅ COMPLETED

### Task #1: Design Edge Discovery Lab app
**Status:** ✅ DONE
- Identified workflow: Claude chat → findings lost → need memory system
- User wants SIMPLE, FOCUSED app (no extra bloat)
- Purpose: Discover edges → validate → remember → promote to validated_setups
- Keep edge_candidates ISOLATED from validated_setups

### Task #2: Create edge_candidates table schema
**Status:** ✅ DONE
- Ran `pipeline/migrate_add_edge_candidates.py`
- Ran `pipeline/migrate_add_reproducibility_fields.py`
- Table created in `data/db/gold.db`
- 17 columns: candidate_id, instrument, name, hypothesis, filters, metrics, status, etc.
- Example row inserted (candidate_id=1)

### Task #3: Wire up AI memory integration
**Status:** ✅ DONE
- Created `trading_app/edge_memory_bridge.py`
- Functions:
  - `log_edge_test()` - Breadcrumb trail in session_state
  - `promote_to_learned_pattern()` - Validated edges → learned_patterns table
  - `query_similar_patterns()` - Prevent re-testing same thing
  - `get_testing_history()` - See what you've tested recently
  - `mark_pattern_degraded()` - Track edge decay

---

## 🔄 IN PROGRESS

### Task #4: Add conversational AI interface
**Status:** ⏳ NEXT
**What to build:**
- Simple chat interface in Research Lab app
- User types: "Test MPL 1100 with ORB size filter 0.5-1.5"
- AI understands, runs backtest, shows results
- AI suggests next tests based on what worked
- Conversational, not form-based

**Files to modify:**
- `trading_app/app_research_lab.py` (add chat tab)
- Use existing `ai_assistant.py` or similar
- Integrate with `edge_memory_bridge.py` to log tests

**Key principle:** Keep it CONVERSATIONAL like Claude chat, but with MEMORY.

---

## 📝 PENDING

### Task #5: Build experiment tracking system
**Status:** 📝 TODO
**What to build:**
- Show history of all tests in UI
- Table view: Date | Instrument | Setup | Result | Status
- Filter by instrument, date range, outcome
- "What did I test last week?" → instant answer

**Files to create/modify:**
- Add tab to `app_research_lab.py`
- Query `edge_candidates` + `session_state`
- Simple table with filters

### Task #6: Create validation pipeline
**Status:** 📝 TODO
**What to build:**
- Systematic validation before promoting edges
- Steps:
  1. Ground truth check (data exists?)
  2. Cost model validation (realistic costs?)
  3. Stress test (+25%, +50% costs)
  4. Sample size check (N >= 30?)
  5. Expectancy threshold (ExpR > +0.15R?)
- Use strategy-validator skill methodology
- Auto-run when user clicks "Validate" button

**Files to create:**
- `trading_app/edge_validator.py`
- Integrate with `edge_memory_bridge.py`
- Use formulas from `CANONICAL_LOGIC.txt`

### Task #7: Test and document complete app
**Status:** 📝 TODO
**What to do:**
1. Run full workflow:
   - Discover edge via chat
   - Validate edge
   - Promote to validated_setups
   - Verify in trading app
2. Create `EDGE_LAB_GUIDE.md` (simple how-to)
3. Test with real MGC data
4. Verify memory persists across sessions

---

## 🎯 Current State

**What works:**
- ✅ Database tables created (edge_candidates, memory tables)
- ✅ Memory bridge connects edge discovery to learned patterns
- ✅ Can log tests, promote edges, query history

**What's missing:**
- ❌ Chat interface (can't test edges conversationally yet)
- ❌ Experiment history UI (can't see past tests easily)
- ❌ Validation pipeline (no systematic validation yet)
- ❌ Documentation (no user guide)

**Next session:**
Start with Task #4 (add chat interface to Research Lab app)

---

## 📦 Files Created This Session

1. `edge_memory_bridge.py` - Memory integration layer
2. `edge_candidates` table in database
3. `EDGE_LAB_TODO.md` - This file

---

## 🚀 How to Continue

**Next time you open this:**
1. Read this TODO list
2. Check Task #4 (chat interface)
3. Run: `streamlit run trading_app/app_research_lab.py`
4. Start building chat tab

**Key files to work on:**
- `trading_app/app_research_lab.py` (main app)
- `trading_app/edge_memory_bridge.py` (memory layer)
- `trading_app/ai_assistant.py` (AI chat helper)

**Remember:** SIMPLE and FOCUSED. No extra bloat.

---

## 💡 Vision (Don't Forget)

**The problem:**
- You discover edges in chat
- Findings get lost in docs/conversations
- Re-test same things multiple times
- Never know what you've already tried

**The solution:**
- Edge Discovery Lab with MEMORY
- Test edges → Lab remembers
- Validates systematically
- Promotes to validated_setups when ready
- Never lose findings again

**Keep it simple. Ship it working.**
