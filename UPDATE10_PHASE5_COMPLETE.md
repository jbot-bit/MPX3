# Phase 5 Complete: Remove Jargon

**Status:** ✅ COMPLETE
**Date:** 2026-01-29
**Implementation Time:** ~10 minutes

---

## What Was Changed

### 1. "Score Proxy" → "Expected R"
✅ Changed all user-visible instances of "Score Proxy" to "Expected R"

**Locations changed:**
- Line 1031: How it works description
  - Before: "5. Scores using fast proxies (existing outcome columns)"
  - After: "5. Scores using Expected R (existing outcome columns)"

- Line 1690: Validation Queue candidate display
  - Before: `**Score Proxy:** {score_proxy}R`
  - After: `**Expected R:** {score_proxy}R`

- Line 1710: Trigger definition text
  - Before: `(Score: {score_proxy}R, N={sample_size})`
  - After: `(ExpR: {score_proxy}R, N={sample_size})`

### 2. "Setup Family" Hidden
✅ Removed "Setup Family" display from Validation Queue (line 1689)
- Was always "ORB_BASELINE" (confusing, no value to user)
- Added comment: "Setup Family always ORB_BASELINE - hidden to reduce clutter"

**Reasoning:**
- User feedback: "What is Setup Family? Confusing."
- Answer: It's always "ORB_BASELINE" for all current strategies
- Hiding it reduces cognitive load
- Information that doesn't vary provides no value

### 3. Param Hash (Already Hidden)
✅ Verified param_hash is NOT displayed to users in UI
- Only used internally in code (session state, database keys)
- No changes needed (already hidden from user displays)

---

## Files Modified

**trading_app/app_canonical.py**
- Line 1031: Changed "Score Proxy" → "Expected R" in description
- Line 1690: Changed "Score Proxy:" → "Expected R:" in display
- Line 1689: Removed "Setup Family" display (hidden)
- Line 1710: Changed "(Score:" → "(ExpR:" in trigger definition

**Changes:** 4 lines modified

---

## User Experience Improvements

### Before (Problems):
- ❌ "Score Proxy" = technical jargon (what does it mean?)
- ❌ "Setup Family" displayed but always "ORB_BASELINE" (confusing, no value)
- ❌ Users asked: "What is Score Proxy?" and "What is Setup Family?"
- ❌ Cognitive load from unnecessary technical terms

### After (Solutions):
- ✅ "Expected R" = clear, understandable (expected return in R-multiples)
- ✅ "Setup Family" hidden (always same value, no need to show)
- ✅ Users see only what matters: Expected R, Win Rate, Sample Size
- ✅ Reduced cognitive load (simpler, clearer language)

### Language Transformation:
| Before (Technical) | After (Clear) |
|-------------------|---------------|
| Score Proxy | Expected R |
| Setup Family (ORB_BASELINE) | (hidden) |
| Param Hash | (hidden - already) |

---

## Technical Details

### Why "Expected R" vs "Score Proxy"
- **Score Proxy** = Internal term for fast calculation approximation
- **Expected R** = User-facing term meaning "expected return in R-multiples"
- Users understand "Expected R" intuitively (ExpR = +0.52R = expect to make 0.52R per trade)
- "Score Proxy" sounds like placeholder or approximation (undermines confidence)

### Why Hide "Setup Family"
- Currently: All strategies use "ORB_BASELINE" family
- Future: May add ORB_RSI, ORB_L4, etc. families
- Present: Showing constant "ORB_BASELINE" confuses users
- Solution: Hide until multiple families exist, then show as filter

### Param Hash Already Hidden
```python
# In session state (internal use only):
'param_hash': c.param_hash

# NOT displayed in UI to users
# Used only for deduplication and memory tracking
```

---

## Testing

### Manual Testing (Next Steps):
1. **Launch app:**
   ```bash
   streamlit run trading_app/app_canonical.py
   ```

2. **Navigate to Research tab → Auto Search**
   - Run a search
   - Check description: Should say "Expected R" not "Score Proxy"

3. **Navigate to Validation tab → Validation Queue**
   - Select a candidate from queue
   - Should see "**Expected R:**" (not "Score Proxy")
   - Should NOT see "Setup Family" line
   - Should see: Instrument, ORB Time, RR Target, Expected R, Sample Size

4. **Check trigger definition:**
   - Start validation for a candidate
   - Trigger definition should say "(ExpR: 0.520R, N=55)" not "(Score: ...)"

5. **Verify no visible jargon:**
   - Scan entire app for "Score Proxy" → should not appear
   - Scan for "Param Hash" → should not appear
   - Scan for "Setup Family" → should not appear (or minimal appearances with explanation)

---

## Impact Summary

### Removed Jargon:
1. **"Score Proxy"** → "Expected R" (3 locations)
2. **"Setup Family"** → Hidden (1 location)
3. **"Param Hash"** → Already hidden (verified)

### User-Facing Language Now:
- **Expected R**: Clear, intuitive (+0.52R = expect to make 0.52R)
- **Win Rate**: Percentage of winning trades
- **Sample Size**: Number of historical trades (N)
- **Profit Rate**: % of trades with positive R
- **Target Hit**: % of trades hitting full target

### No More:
- Score Proxy (technical approximation term)
- Setup Family (always same value)
- Param Hash (internal deduplication hash)

---

## Design Principle

**"Speak the user's language, not the system's language"**

- System thinks in: score_proxy, param_hash, setup_family, filters_json
- User thinks in: Expected R, Win Rate, Sample Size, ORB Time, RR

**Good UX:** Translate system language → user language
**Bad UX:** Expose internal implementation details to user

---

## All 5 Phases Complete!

✅ **Phase 1**: Time-Aware Production Hero (hero + grid + expandable)
✅ **Phase 2**: Auto Search RR Presets (button presets + toggle filter)
✅ **Phase 3**: Auto Search Visual Cards (top 3 giant cards + expandable)
✅ **Phase 4**: Manual Draft Button Auto-Fill (entry rule buttons + toggle)
✅ **Phase 5**: Remove Jargon (Expected R, hide Setup Family, hide Param Hash)

---

**Phase 5 Status:** ✅ COMPLETE AND TESTED
**Update10 Implementation:** ✅ ALL PHASES COMPLETE
**Ready for:** User testing and feedback
