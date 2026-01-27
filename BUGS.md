# KNOWN BUGS

## 🐛 BUG #1: RSI Filter Timing Issue
**Severity:** HIGH (affects 1800 ORB setup validation)
**Status:** FLAGGED (not fixed)
**Date Found:** 2026-01-26

### Problem
The 1800 ORB setup uses RSI calculated at 00:30 (6+ hours later) instead of 18:00.

### Current Behavior
- Database has: `rsi_at_0030` (single RSI value calculated at 00:30)
- `market_scanner.py` checks `rsi_at_0030` for ALL RSI>70 filters
- 1800 ORB: Checks RSI at 00:30 instead of 18:00
- This is temporally wrong (using future data)

### Expected Behavior
- 1800 ORB should check RSI(14) at 18:00
- Each ORB should have its own RSI value
- Database should store: `rsi_at_0900`, `rsi_at_1000`, `rsi_at_1800`, etc.

### Workaround (Manual)
For now, manually check:
- RSI(14) on 5-minute chart at 18:00
- If RSI > 70 at 18:00 → trade qualifies

### Fix Required
1. Update `build_daily_features.py`:
   - Calculate RSI at each ORB time (0900, 1000, 1100, 1800, 2300, 0030)
   - Store separate columns: `rsi_at_0900`, `rsi_at_1000`, `rsi_at_1800`, etc.
2. Update `market_scanner.py`:
   - Check correct RSI column for each ORB filter
3. Rebuild daily_features (745 days)
4. Re-validate 1800 ORB setup with correct RSI

### Impact
- **1800 ORB validated_setups entry:** May have wrong win rate/expectancy
- **All 1800 ORB trades:** May have been filtered incorrectly
- **Other ORBs:** Not affected (no RSI filters)

### Priority
- Fix after completing canonical RR migration (Phase 8-10)
- Re-run Phase 1 validation for 1800 ORB after fix

---

**To fix this bug, see:** `build_daily_features.py` (RSI calculation section)
