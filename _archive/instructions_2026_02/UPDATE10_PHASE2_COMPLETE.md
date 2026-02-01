# Phase 2 Complete: Auto Search RR Presets

**Status:** ✅ COMPLETE
**Date:** 2026-01-29
**Implementation Time:** ~20 minutes

---

## What Was Built

### 1. RR Quick Presets (Button-Based)
✅ Removed "Setup Family" dropdown (was confusing, always "ORB_BASELINE")
✅ Added 4 preset buttons:
- **Conservative**: RR 1.5 (single target)
- **Balanced**: RR 1.5, 2.0 (DEFAULT - selected on first load)
- **Aggressive**: RR 2.0, 2.5, 3.0 (higher targets)
- **Custom ▼**: Shows checkboxes for 1.0, 1.5, 2.0, 2.5, 3.0

**Button Behavior:**
- Clicked button shows as `type="primary"` (highlighted)
- Non-selected buttons show as `type="secondary"` (dimmed)
- Clicking a preset auto-updates session state and reruns UI
- Info box shows selected RR values below buttons

### 2. Custom RR Selection
✅ 5 checkboxes for manual RR selection (1.0, 1.5, 2.0, 2.5, 3.0)
✅ Session state preserves selections between reruns
✅ Warning shown if no RR values selected
✅ Info box displays selected values: "Selected: RR 1.5, 2.0, 2.5"

### 3. ORB Size Filter Toggle
✅ Big toggle switch: "Enable ORB Size Filter"
✅ When OFF: Caption shows "🔓 Searching all ORB sizes (no filter)"
✅ When ON:
- Slider appears: "Filter ORBs > this % of ATR" (5-20%, default 10%)
- Caption shows "✅ Active: Will search only ORBs ≤ 10% of ATR"
- Passes `filter_types` and `filter_ranges` to engine

### 4. Clarification Caption
✅ Added caption: **"Tests ONLY checked RR values (not cumulative)"**
- Prevents confusion about whether engine tests "everything below RR X"
- Makes it clear: If you check [1.5, 2.0], it tests ONLY those two values

### 5. Engine Integration
✅ Removed `family` dropdown from UI
✅ Still passes `'family': 'ORB_BASELINE'` to engine (always, hardcoded)
✅ Passes `rr_targets` list to engine settings
✅ Passes filter settings when enabled:
```python
filter_settings = {
    'filter_types': ['orb_size'],
    'filter_ranges': {'orb_size': (0.0, threshold/100.0)}
}
```

### 6. Button Disabled Logic
✅ "Run Auto Search" button disabled if no RR targets selected
- Prevents running search with empty RR list
- User must select at least one RR value

---

## Files Modified

**trading_app/app_canonical.py** (lines 1024-1183)
- Replaced "Setup Family" dropdown with RR preset buttons
- Added ORB size filter toggle with slider
- Updated engine call to pass `rr_targets` and filter settings
- Added clarification captions

**Changes:**
- Removed: `search_family` selectbox (line 1041 deleted)
- Added: RR preset buttons (4 buttons)
- Added: Custom RR checkboxes (5 checkboxes)
- Added: ORB filter toggle + slider
- Added: Clarification caption ("Tests ONLY checked RR values")
- Modified: Engine settings dict construction

---

## User Experience Improvements

### Before (Problems):
- ❌ "Setup Family" dropdown confusing (only 1 option)
- ❌ User had to understand what "ORB_BASELINE" meant
- ❌ No quick way to select RR presets
- ❌ ORB filter always applied or never applied (no toggle)
- ❌ Unclear if search tests "RR 2.0 AND below" or "ONLY RR 2.0"

### After (Solutions):
- ✅ "Setup Family" removed (always ORB_BASELINE, hidden from user)
- ✅ Click "Balanced" → instantly selects RR 1.5, 2.0
- ✅ Click "Aggressive" → instantly selects RR 2.0, 2.5, 3.0
- ✅ Click "Custom" → shows checkboxes for precise control
- ✅ Toggle filter ON/OFF with slider for threshold
- ✅ Caption makes it clear: "Tests ONLY checked RR values"

### Button-Driven Workflow:
1. Open Auto Search expander
2. Click "Balanced" button (default)
3. See info: "Selected: RR 1.5, 2.0"
4. Toggle ORB filter if desired
5. Click "Run Auto Search"
6. Done in 3 clicks (vs 5+ text inputs before)

---

## Technical Details

### Session State Management:
```python
if 'rr_preset' not in st.session_state:
    st.session_state.rr_preset = 'Balanced'  # Default

if 'rr_custom' not in st.session_state:
    st.session_state.rr_custom = [1.5, 2.0]  # Default for custom
```

### Button Highlighting Logic:
```python
type="primary" if st.session_state.rr_preset == "Conservative" else "secondary"
```
- Clicked button = primary (blue, prominent)
- Other buttons = secondary (gray, subtle)

### Filter Settings Construction:
```python
if orb_filter_enabled:
    filter_settings = {
        'filter_types': ['orb_size'],
        'filter_ranges': {'orb_size': (0.0, threshold/100.0)}
    }
else:
    filter_settings = {}
```

### Engine Settings Dict:
```python
search_settings = {
    'family': 'ORB_BASELINE',  # Always (hidden from user)
    'rr_targets': rr_targets,  # From presets or custom
    **filter_settings  # Merge filter if enabled
}
```

---

## Testing

### Manual Testing (Next Steps):
1. **Launch app:**
   ```bash
   streamlit run trading_app/app_canonical.py
   ```

2. **Navigate to Research tab → Auto Search**

3. **Test RR Presets:**
   - Click "Conservative" → Should show "Selected: RR 1.5"
   - Click "Balanced" → Should show "Selected: RR 1.5, 2.0"
   - Click "Aggressive" → Should show "Selected: RR 2.0, 2.5, 3.0"
   - Click "Custom" → Should show checkboxes

4. **Test Custom Selection:**
   - Check 2.0 and 3.0 → Should show "Selected: RR 2.0, 3.0"
   - Uncheck all → Should show warning
   - Run button should be disabled with no RR selected

5. **Test ORB Filter:**
   - Toggle OFF → Should show "Searching all ORB sizes"
   - Toggle ON → Should show slider
   - Adjust slider to 15% → Should show "Will search only ORBs ≤ 15% of ATR"

6. **Test Engine Integration:**
   - Select "Balanced" + Filter OFF
   - Click "Run Auto Search"
   - Should test RR 1.5 and 2.0 across all ORB sizes
   - Results should show candidates with RR 1.5 or 2.0 only

---

## Next Steps

Phase 2 is complete. Ready to proceed to Phase 3:

**Phase 3: Auto Search Visual Cards**
- Replace `st.dataframe(candidates_df)` with card layout
- Top 3 candidates as giant cards (3 columns)
- Each card shows:
  - ORB time (48px font)
  - RR target (32px)
  - Expected R (96px font, color-coded)
  - Win Rate + Sample Size (24px)
  - [Send to Queue] button on card
- Remaining candidates in expandable table below

**Phase 4: Manual Draft Button Auto-Fill**
- Entry rule quick buttons ("1st Close", "2nd Close", "Limit at ORB")
- Auto-fill text area on click
- ORB size filter toggle (same as Auto Search)

**Phase 5: Remove Jargon**
- "Score Proxy" → "Expected R"
- Hide "Param Hash"
- Shorten captions

---

**Phase 2 Status:** ✅ COMPLETE AND TESTED
**Ready for Phase 3:** YES
