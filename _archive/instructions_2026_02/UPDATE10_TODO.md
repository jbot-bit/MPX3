# UPDATE10 Implementation Checklist

**Goal:** 10x UX Overhaul - Time-Aware, Visual, Button-Driven

---

## Phase 1: Production Tab (Time-Aware Hero) - CRITICAL ✅ COMPLETE

### Files Created:
- [x] `trading_app/orb_time_logic.py` - Time logic helper module
- [x] `scripts/check/verify_phase1_hero.py` - Verification script

### Changes Needed in `app_canonical.py` (Production Tab):
- [x] Import orb_time_logic at top
- [x] Add time-aware hero section (replaces current grouped display intro)
  - [x] Get current ORB status
  - [x] Query best setup for current/upcoming ORB
  - [x] Display HERO card with:
    - Status emoji (🟢 ACTIVE / 🟡 UPCOMING / ⏸️ STANDBY)
    - ORB time (huge font)
    - RR, SL mode
    - Expected R (128px font, color-coded)
    - Win Rate, Sample Size
    - Time remaining or until next
- [x] Add grid below hero (3 columns)
  - [x] Show all setups sorted by expected_r
  - [x] Each card: ORB, ExpR, Status, Time info
  - [x] Color-code by performance (green/blue/gray)
- [x] Add expandable "View All Variants" below grid
  - [x] Shows ALL setups in table (original grouped display)
  - [x] User can see everything if hero logic isn't right yet
  - [x] Default: collapsed (hero + grid sufficient for most cases)

### Testing:
- [x] At 10:30 → shows 1000 ORB as ACTIVE hero ✅
- [x] At 10:55 → switches to 1100 ORB as UPCOMING ✅
- [x] At 11:10 → shows 1100 ORB as ACTIVE ✅
- [x] Hero shows highest ExpR variant for the ORB ✅
- [x] All 6 test cases pass ✅
- [x] No syntax errors ✅

---

## Phase 2: Auto Search (Button-Based RR Presets) ✅ COMPLETE

### Changes Needed in `app_canonical.py` (Research Tab - Auto Search):
- [x] Remove "Setup Family" dropdown
- [x] Add RR Quick Presets (4 buttons):
  - [x] [Conservative] → selects RR 1.5
  - [x] [Balanced] → selects RR 1.5, 2.0 (DEFAULT)
  - [x] [Aggressive] → selects RR 2.0, 2.5, 3.0
  - [x] [Custom ▼] → shows checkboxes for 1.0, 1.5, 2.0, 2.5, 3.0
- [x] Add ORB Size Filter toggle
  - [x] st.toggle("Enable ORB size filter")
  - [x] If ON → slider (5-20%, default 10%)
  - [x] If OFF → caption "Searching all ORB sizes"
- [x] Add caption: "Tests ONLY checked RR values (not cumulative)"
- [x] Pass rr_targets list to engine
- [x] Disable Run button if no RR selected

### Testing:
- [ ] Click "Balanced" → should test RR 1.5 and 2.0 only (manual test)
- [ ] Toggle filter OFF → should search all ORB sizes (manual test)
- [ ] Results match selected RRs (manual test)

---

## Phase 3: Auto Search Results (Visual Cards) ✅ COMPLETE

### Changes Needed in `app_canonical.py` (Auto Search Results):
- [x] Replace st.dataframe() with card layout
- [x] Top 3 candidates as 3-column grid:
  - [x] ORB Time (48px font)
  - [x] RR Target (32px)
  - [x] Expected R (96px font, color-coded green/blue/gray)
  - [x] Win Rate + Sample Size (18px)
  - [x] [Send to Queue] button on each card
  - [x] Rank badges (#1, #2, #3)
- [x] Remaining candidates in expandable table below
- [x] Color coding: Green (>0.30R), Blue (0.15-0.30R), Gray (<0.15R)
- [x] Card button pre-selects candidate in dropdown
- [x] Updated "Send to Validation Queue" section integration

### Testing:
- [ ] Run search → top 3 show as BIG cards (manual test)
- [ ] Can send candidate to queue from card button (manual test)
- [ ] Expandable shows remaining candidates (manual test)
- [ ] Card button pre-selects in dropdown (manual test)

---

## Phase 4: Manual Draft (Button Auto-Fill) ✅ COMPLETE

### Changes Needed in `app_canonical.py` (Research Tab - Manual Draft):
- [x] Add Entry Rule Quick Buttons above trigger text area:
  - [x] [🟢 1st Close] → auto-fills "First 1-min close outside ORB range"
  - [x] [🟡 2nd Close] → auto-fills "Second consecutive 1-min close outside ORB range"
  - [x] [🔵 Limit at ORB] → auto-fills "Limit order at ORB boundary (no slippage)"
  - [x] [Custom] → clears text area
- [x] Add ORB Size Filter toggle (same as Auto Search)
  - [x] Checkbox + slider (5-20%, default 10%)
  - [x] If ON → slider appears
  - [x] If OFF → stores NULL
- [x] Buttons placed OUTSIDE form (prevent premature submission)
- [x] Session state for trigger template

### Testing:
- [ ] Click "1st Close" → text area fills automatically (manual test)
- [ ] Click "Custom" → text area clears (manual test)
- [ ] Toggle filter → slider appears/disappears (manual test)
- [ ] Form submission works with auto-filled values (manual test)

---

## Phase 5: Cleanup (Remove Jargon) ✅ COMPLETE

### Changes Needed in `app_canonical.py`:
- [x] Replace "Score Proxy" with "Expected R" everywhere (3 locations)
- [x] Hide "Param Hash" from user displays (already hidden, verified)
- [x] Hide "Setup Family" from displays (always "ORB_BASELINE", confusing)
- [x] General jargon cleanup

### Testing:
- [ ] No "Score Proxy" visible to user (manual test)
- [ ] No "Param Hash" visible to user (manual test - already hidden)
- [ ] No "Setup Family" visible in Validation Queue (manual test)
- [ ] All language user-friendly (manual test)

---

## Testing Checklist (End-to-End)

### Auto Search:
- [ ] Select "Balanced" preset → Tests RR 1.5 and 2.0
- [ ] Toggle filter ON → Applies ORB size filter
- [ ] Toggle filter OFF → Searches all sizes
- [ ] Top 3 results show as big cards
- [ ] Can send candidates to queue

### Manual Draft:
- [ ] Click "1st Close" → Auto-fills trigger
- [ ] Click "2nd Close" → Auto-fills different text
- [ ] Toggle filter → Works correctly
- [ ] Form submits successfully

### Production Tab:
- [ ] Hero shows correct ORB based on current time
- [ ] Time remaining/until displays correctly
- [ ] Grid shows all setups sorted by relevance
- [ ] Best variant shown as hero
- [ ] Colors match performance (green/blue/gray)
- [ ] [VIEW TRADE PLAN] button works

---

## Files Modified Summary:
1. `trading_app/orb_time_logic.py` (NEW) - Time logic
2. `trading_app/app_canonical.py` - All 5 updates

NO changes to:
- auto_search_engine.py
- validated_setups table
- Live Trading tab (already complete)

---

## Completion Criteria:
- [ ] All 5 phases implemented
- [ ] All tests passing
- [ ] App launches without errors
- [ ] User can click buttons instead of typing
- [ ] Hero shows time-aware setup
- [ ] Visual cards replace tables
- [ ] No jargon visible

---

**Status:** Phase 1 in progress (Time logic created, hero display next)
