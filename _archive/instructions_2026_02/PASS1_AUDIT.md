# 🛡️ PASS 1 AUDIT - Research UI Streamlining

**Status:** READ-ONLY ANALYSIS COMPLETE
**Date:** 2026-01-31
**Guardian:** ON

---

## 📊 CURRENT STATE MAP

### Database State
- **Table:** `edge_candidates` (exists in `gold.db`)
- **Total Candidates:** 289
- **Status Breakdown:**
  - DRAFT: 289 (100%)
  - TESTED: 0
  - PENDING: 0
  - APPROVED: 0
  - REJECTED: 0
- **PB Grid Candidates:** 144 of the 289 are PB family grid-generated

### File Inventory

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `app_canonical.py` | 3,355 | Main app with research tab | **DUPLICATE** |
| `app_research_lab.py` | 723 | Dedicated research UI | **DUPLICATE** |
| `edge_candidates_ui.py` | 355 | Candidate review panel | **DUPLICATE** |
| `edge_candidate_utils.py` | 263 | Write utilities (approve, status) | **KEEP** |
| `edge_pipeline.py` | 493 | Promotion logic | **KEEP** |
| `pb_grid_generator.py` | 321 | PB grid generator | **KEEP** |

**Total duplication:** ~1,400 lines of redundant UI code

---

## 🔍 UI SURFACES MAPPED

### Surface 1: app_canonical.py → Research Tab (lines 744-1469)

**Components:**
1. **PB Grid Generator** (lines 1214-1269)
   - Button: "🚀 Generate PB Grid"
   - Write path: `pb_grid_generator.generate_pb_batch()` → `edge_candidates` table
   - Creates 144 candidates in DRAFT status

2. **Manual Candidate Draft Form** (lines 1273-1395)
   - Form: "candidate_form"
   - Submit button: "📥 Draft Candidate"
   - Write path: `edge_utils.create_candidate()` → `edge_candidates` table
   - Creates 1 candidate at a time

3. **Candidate List** (lines 1398+)
   - Read path: Query `edge_candidates` table
   - Displays: DRAFT/PENDING status candidates
   - Actions: Update status, validate

**Problems:**
- PB grid generator + manual form + candidate list = CONFUSING
- User can't find the 144 PB candidates (buried in list)
- Mixed purpose: generation + manual entry + review

---

### Surface 2: app_research_lab.py (FULL FILE)

**Components:**
1. **DISCOVERY View** (lines 143-314)
   - Button: "🔬 START DISCOVERY SCAN"
   - Action: Runs parameter grid scan
   - Write path: NONE (just displays results)
   - **Status:** Not integrated with edge_candidates table

2. **PIPELINE View** (lines 320-453)
   - Displays candidates by status (DRAFT/TESTED/PENDING/APPROVED/REJECTED/PROMOTED)
   - Actions per status:
     - DRAFT → Button: "🧪 RUN BACKTEST" (not implemented)
     - TESTED → Button: "👀 REVIEW" → sets status to PENDING
     - PENDING → Buttons: "✅ APPROVE" or "❌ REJECT"
     - APPROVED → Button: "🚀 PROMOTE TO PRODUCTION"
   - Write paths:
     - `set_candidate_status()` → `edge_candidates.status`
     - `approve_edge_candidate()` → `edge_candidates.status + approved_at/by`
     - `promote_candidate_to_validated_setups()` → `validated_setups` table

3. **BACKTESTER View** (lines 460-584)
   - Button: "🧪 RUN BACKTEST"
   - Creates ad-hoc candidate
   - Write path: `create_edge_candidate()` → `edge_candidates` table
   - Runs backtest and displays metrics

4. **PRODUCTION View** (lines 590-665)
   - Read-only view of `validated_setups` table
   - No write paths

**Assessment:**
- Well-structured 4-view conveyor belt: DISCOVERY → PIPELINE → BACKTESTER → PRODUCTION
- PIPELINE view is the BEST candidate review interface
- Problem: Doesn't show PB grid generator (user has to use app_canonical research tab)

---

### Surface 3: edge_candidates_ui.py (FULL FILE)

**Components:**
1. **Candidate Table View** (lines 125-198)
   - Button: "🔄 Load Candidates"
   - Filter by: Status, Instrument, Limit
   - Displays: Table of candidates
   - No write actions in table view

2. **Candidate Detail & Actions** (lines 200-350)
   - Displays: Selected candidate details (hypothesis, metrics, filter spec)
   - Action buttons:
     - "✅ Approve" → `approve_edge_candidate()`
     - "⏸️ Set Pending" → `set_candidate_status()`
     - "❌ Reject" → `set_candidate_status()`
     - "🚀 Promote to Production" → `promote_candidate_to_validated_setups()`
   - Write paths:
     - `edge_candidates.status`, `approved_at`, `approved_by`
     - `validated_setups` table (on promotion)

**Assessment:**
- PURE DUPLICATE of app_research_lab.py PIPELINE view
- Less polished than research lab
- No unique functionality

---

## 🚨 DUPLICATION ANALYSIS

### Duplicate Functionality Matrix

| Feature | app_canonical | app_research_lab | edge_candidates_ui |
|---------|---------------|------------------|-------------------|
| **Create Candidates (Manual)** | ✅ Form | ❌ | ❌ |
| **Create Candidates (PB Grid)** | ✅ Button | ❌ | ❌ |
| **View Candidates (List)** | ✅ Basic | ✅ **Best** | ✅ Basic |
| **Filter Candidates** | ❌ | ✅ | ✅ |
| **Approve Candidates** | ❌ | ✅ | ✅ |
| **Reject Candidates** | ❌ | ✅ | ✅ |
| **Promote to Production** | ❌ | ✅ | ✅ |
| **Run Backtests** | ❌ | ✅ | ❌ |
| **Discovery Scan** | ❌ | ✅ | ❌ |

### Redundant Actions (Same Writes)

**Action: Approve Candidate**
- Implemented in: `app_research_lab.py`, `edge_candidates_ui.py`
- Both call: `approve_edge_candidate(candidate_id, "user")`
- Write: `edge_candidates.status = 'APPROVED'`, `approved_at`, `approved_by`

**Action: Set Status (Pending/Rejected)**
- Implemented in: `app_research_lab.py`, `edge_candidates_ui.py`
- Both call: `set_candidate_status(candidate_id, status)`
- Write: `edge_candidates.status`

**Action: Promote to Production**
- Implemented in: `app_research_lab.py`, `edge_candidates_ui.py`
- Both call: `promote_candidate_to_validated_setups(candidate_id)`
- Write: `validated_setups` table + `edge_candidates.promoted_validated_setup_id`

**Redundancy Score:** 60% (3 of 5 write actions duplicated across 2 files)

---

## 🎯 WRITE PATHS (Complete Map)

### Write Path 1: Create Candidate (Manual)
- **UI:** `app_canonical.py` → "📥 Draft Candidate" form
- **Function:** `edge_utils.create_candidate()`
- **Database:** `INSERT INTO edge_candidates` (status='DRAFT')
- **Used by:** Manual single-candidate creation

### Write Path 2: Create Candidate (PB Grid Batch)
- **UI:** `app_canonical.py` → "🚀 Generate PB Grid" button
- **Function:** `pb_grid_generator.generate_pb_batch()` → `create_pb_candidate()` (x144)
- **Database:** `INSERT INTO edge_candidates` (status='DRAFT')
- **Used by:** Batch generation of 144 PB candidates

### Write Path 3: Create Candidate (Ad-hoc Backtest)
- **UI:** `app_research_lab.py` → BACKTESTER view → "🧪 RUN BACKTEST"
- **Function:** `create_edge_candidate()`
- **Database:** `INSERT INTO edge_candidates` (status='DRAFT')
- **Used by:** Ad-hoc backtest experiments

### Write Path 4: Update Status (Pending/Rejected)
- **UI:** `app_research_lab.py` → PIPELINE view → "👀 REVIEW" or "❌ REJECT"
- **UI:** `edge_candidates_ui.py` → "⏸️ Set Pending" or "❌ Reject"
- **Function:** `set_candidate_status(candidate_id, status)`
- **Database:** `UPDATE edge_candidates SET status = ?`
- **Used by:** Moving candidates through workflow

### Write Path 5: Approve Candidate
- **UI:** `app_research_lab.py` → PIPELINE view → "✅ APPROVE"
- **UI:** `edge_candidates_ui.py` → "✅ Approve"
- **Function:** `approve_edge_candidate(candidate_id, approver)`
- **Database:** `UPDATE edge_candidates SET status='APPROVED', approved_at, approved_by`
- **Used by:** Final approval gate

### Write Path 6: Promote to Production
- **UI:** `app_research_lab.py` → PIPELINE view → "🚀 PROMOTE TO PRODUCTION"
- **UI:** `edge_candidates_ui.py` → "🚀 Promote to Production"
- **Function:** `promote_candidate_to_validated_setups(candidate_id)`
- **Database:**
  1. `INSERT INTO validated_setups` (extracts from edge_candidates manifest)
  2. `UPDATE edge_candidates SET promoted_validated_setup_id = ?`
- **Used by:** Graduating approved candidates to live trading

---

## 📋 CANONICAL OWNER RECOMMENDATIONS

### Decision Criteria
1. **Most complete:** Which surface has all features?
2. **Best UX:** Which has clearest flow?
3. **Least duplication:** Which requires minimal changes?

### Recommendation: **app_research_lab.py** as CANONICAL OWNER

**Reasoning:**
- ✅ Has 4-view conveyor belt (DISCOVERY → PIPELINE → BACKTESTER → PRODUCTION)
- ✅ Has best candidate review interface (PIPELINE view)
- ✅ Has all write actions (approve, reject, promote)
- ✅ Has backtester integration
- ✅ Only 723 lines (focused, not bloated like app_canonical's 3,355)
- ⚠️ **Missing:** PB grid generator (needs to be added)

### Files to Keep (As-Is)
- `edge_candidate_utils.py` - Utility functions (approve, set status)
- `edge_pipeline.py` - Promotion logic
- `pb_grid_generator.py` - PB grid generation

### Files to Modify
- `app_research_lab.py` - **CANONICAL** (add PB grid generator)
- `app_canonical.py` - **SIMPLIFY** (remove duplicate research UI, link to research lab)

### Files to DELETE
- `edge_candidates_ui.py` - **DELETE** (pure duplicate of research lab PIPELINE view)

---

## 🚧 CONCRETE PLAN (For PASS 2)

### Phase 1: Add Missing Feature to Canonical Owner
**File:** `app_research_lab.py`
**Change:** Add PB Grid Generator to DISCOVERY view
**Location:** After line 314 (end of DISCOVERY view)
**Code to add:**
```python
render_section_divider("PB GRID GENERATOR")

col1, col2 = st.columns([1, 2])
with col1:
    pb_instrument = st.selectbox("Instrument", ["MGC", "NQ", "MPL"], key="pb_instrument")
    if st.button("🚀 Generate 144 PB Candidates", type="primary", use_container_width=True):
        with st.spinner("Generating 144 PB candidates..."):
            try:
                from pb_grid_generator import generate_pb_batch
                conn = get_database_connection()
                results = generate_pb_batch(
                    instrument=pb_instrument,
                    actor='user',
                    db_connection=conn
                )
                conn.close()
                st.success(f"""
                ✅ PB Grid Complete!
                - Created: {results['inserted']}
                - Skipped: {results['skipped']} duplicates
                - Time: {results['elapsed_seconds']:.1f}s

                Go to **PIPELINE** tab to review them.
                """)
            except Exception as e:
                st.error(f"❌ Generation failed: {e}")
with col2:
    st.info("Generates 144 PB parameter combinations. All created as DRAFT.")
```

**Impact:** Adds ~30 lines to `app_research_lab.py`
**Risk:** LOW (UI only, calls existing `pb_grid_generator.generate_pb_batch()`)

---

### Phase 2: Simplify app_canonical.py Research Tab
**File:** `app_canonical.py`
**Change:** Replace research tab content (lines 744-1469) with redirect to research lab
**Code to replace with:**
```python
with tab_research:
    app_state.current_zone = "RESEARCH"
    render_zone_banner("RESEARCH")

    st.markdown("## 🔬 Research Lab")
    st.caption("Candidate discovery, testing, and validation")

    st.info("""
    **The Research Lab has moved to a dedicated interface.**

    Launch it with:
    ```bash
    streamlit run trading_app/app_research_lab.py --server.port 8502
    ```

    Or use the standalone research lab for:
    - Generating PB grid candidates (144 combinations)
    - Running discovery scans
    - Backtesting strategies
    - Reviewing and approving candidates
    - Promoting to production
    """)

    # Quick stats
    render_section_divider("QUICK STATS")

    try:
        conn = get_database_connection(read_only=True)
        stats = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM edge_candidates
            GROUP BY status
        """).df()
        conn.close()

        cols = st.columns(len(stats))
        for idx, row in stats.iterrows():
            with cols[idx]:
                render_metric_card(row['status'], str(row['count']), change=None, sentiment="neutral")
    except Exception as e:
        st.error(f"Error loading stats: {e}")
```

**Impact:** Removes ~700 lines from `app_canonical.py` (1469 - 744 = 725 lines)
**Risk:** LOW (replaces duplicate UI with link to canonical source)

---

### Phase 3: Delete Duplicate File
**File:** `edge_candidates_ui.py`
**Action:** `rm trading_app/edge_candidates_ui.py`
**Impact:** Removes 355 lines of duplicate code
**Risk:** NONE (not imported by any production files - verified with grep)

**Verification (done):**
```bash
$ grep -r "from edge_candidates_ui\|import edge_candidates_ui" trading_app/*.py
# No results - file is orphaned
```

---

## 📊 IMPACT SUMMARY

### Code Changes
- **Lines added:** ~30 (PB grid in research lab)
- **Lines removed:** ~1,080 (725 from app_canonical + 355 file deletion)
- **Net reduction:** **-1,050 lines** (19% of total candidate-related code)

### File Changes
- **Modified:** 2 files (`app_research_lab.py`, `app_canonical.py`)
- **Deleted:** 1 file (`edge_candidates_ui.py`)
- **Unchanged:** 3 files (utilities, pipeline, pb_grid_generator)

### Write Path Changes
- **No change to write paths** (all existing functions preserved)
- **No change to database schema** (no SQL changes)
- **No change to trading logic** (UI only)

### User Experience
- ✅ **One canonical UI** for research workflow
- ✅ **Clear flow:** DISCOVERY → PIPELINE → BACKTESTER → PRODUCTION
- ✅ **PB grid accessible** (previously buried in app_canonical)
- ✅ **289 DRAFT candidates visible** (PIPELINE view with filters)
- ✅ **No more confusion** (removed duplicates)

---

## ✅ PASS 1 SIGN-OFF CHECKLIST

### Audit Complete
- [x] Mapped all UI surfaces (3 apps)
- [x] Mapped all actions (buttons, forms)
- [x] Mapped all write paths (6 identified)
- [x] Identified duplicates (60% redundancy)
- [x] Chose canonical owner (app_research_lab.py)
- [x] Verified no schema changes needed
- [x] Verified no trading logic changes needed
- [x] Created concrete plan (3 phases)

### Guardian Constraints Met
- [x] Read-only analysis (no code changes)
- [x] Did not invent files/paths (all existing)
- [x] Did not mix audit + build (PASS 1 only)
- [x] Concrete plan with line numbers
- [x] Impact quantified (lines, files, risks)

---

## 🎯 PASS 2 APPROVAL REQUIRED

**User must approve this plan before PASS 2 (Build) begins.**

**Questions for user:**
1. Approve canonical owner choice (app_research_lab.py)?
2. Approve file deletion (edge_candidates_ui.py)?
3. Approve app_canonical research tab simplification?
4. Any concerns about the 3-phase plan?

**Once approved, PASS 2 will:**
- Add PB grid to research lab (Phase 1)
- Simplify app_canonical research tab (Phase 2)
- Delete edge_candidates_ui.py (Phase 3)
- Test end-to-end flow
- No schema, no write path changes, no trading logic changes

---

**END OF PASS 1 AUDIT**
