# Experimental Scanner - Blocking Issues Fixed

**Date:** 2026-01-29
**Status:** ✅ ALL 3 BLOCKING ISSUES RESOLVED

---

## Issue 1: Table Name Mismatch ✅ FIXED

### Problem
- Scanner referenced non-existent `daily_features_v2` table
- Would cause runtime crashes: `Catalog Error: Table with name daily_features_v2 does not exist!`
- Violated CLAUDE.md naming convention (no v2 naming)

### Fix Applied
**File:** `trading_app/experimental_scanner.py`

Replaced all 4 occurrences:
1. Line 138: `_get_previous_trading_day` query
2. Line 186: `_get_market_conditions` previous day query
3. Line 212: `_get_market_conditions` today query
4. Line 239: `_get_market_conditions` ATR percentile query

```python
# Before
FROM daily_features_v2

# After
FROM daily_features
```

**Verification:**
```bash
grep -c "daily_features_v2" trading_app/experimental_scanner.py
# Output: 0 (all references removed)
```

---

## Issue 2: Validation Enforcement ✅ FIXED

### Problem
- No validation check before displaying strategies
- Bad data (typos like `expected_r = 2.5` instead of `0.25`) would display as tradeable
- CLAUDE.md mandates validation before production use

### Fix Applied

**File:** `trading_app/experimental_scanner.py`

**Added Method:** `validate_strategies(instrument)`
- Checks expected_r bounds (-1.0 to +2.0)
- Checks win_rate bounds (20% to 90%)
- Checks sample_size minimum (>= 15 trades)
- Validates filter_type (5 valid types)
- Validates day_of_week (Monday-Friday or NULL)

Returns: `(is_valid: bool, issues: List[str])`

**File:** `trading_app/experimental_alerts_ui.py`

**Integration in `render_experimental_alerts`:**
- Runs validation BEFORE scanning for matches
- Shows validation badge: ✅ PASS or ⚠️ FAIL
- If FAIL: displays all issues with error/warning severity
- If FAIL: blocks rendering of alerts (early return)
- Shows fix instructions: Run `python scripts/check/check_experimental_strategies.py`

```python
# Validate strategies data integrity (MANDATORY per CLAUDE.md)
is_valid, validation_issues = scanner.validate_strategies(instrument=instrument)

if not is_valid:
    # Show validation errors
    st.error(f"⚠️ Experimental Strategies Validation FAILED...")
    # Display issues
    # Block rendering
    return
```

---

## Issue 3: Error Handling Improvements ✅ FIXED

### Problem
- Silent failures: `except Exception: return []`
- No distinction between "table missing" vs "query failed"
- Users saw empty results with no explanation

### Fix Applied

**File:** `trading_app/experimental_scanner.py`

**Added Method:** `_check_table_exists()`
- Called during `__init__` (at scanner creation)
- Checks if `experimental_strategies` table exists
- Raises `RuntimeError` with user-friendly message if missing:
  - "Experimental strategies not configured yet. Run pipeline/schema_experimental_strategies.sql to create table."
- Raises `RuntimeError` if database error (not missing table)

**Improved `scan_for_matches`:**
- Changed from silent `return []` to raising `RuntimeError` on query failure
- Error messages now propagate to UI

```python
# Before
except Exception as e:
    logger.error(f"Failed to query experimental_strategies: {e}")
    return []  # Silent failure

# After
except Exception as e:
    logger.error(f"Query failed for experimental_strategies: {e}")
    raise RuntimeError(f"Failed to query experimental strategies: {e}")
```

**File:** `trading_app/app_canonical.py`

**Enhanced Error Handling:**
- Catches `RuntimeError` separately (user-friendly errors)
- Shows info icon (ℹ️) for "not configured yet"
- Shows warning icon (⚠️) for other runtime errors
- Catches generic `Exception` for unexpected errors (database connection, etc.)
- Logs appropriately (warning vs error)

```python
except RuntimeError as e:
    # User-friendly error (table missing or validation failed)
    if "not configured yet" in str(e):
        st.info(f"ℹ️ {e}")
    else:
        st.warning(f"⚠️ {e}")

except Exception as e:
    # Unexpected error
    st.error(f"❌ Unexpected error loading experimental scanner: {e}")
    st.info("Check app_errors.txt for details")
```

---

## Files Changed

### Modified Files
1. **trading_app/experimental_scanner.py**
   - Fixed 4 table name references (v2 → canonical)
   - Added `_check_table_exists()` method (24 lines)
   - Added `validate_strategies()` method (78 lines)
   - Improved error handling in `scan_for_matches()`

2. **trading_app/experimental_alerts_ui.py**
   - Added validation check before rendering (30 lines)
   - Shows validation badge and issues
   - Blocks rendering if validation fails

3. **trading_app/app_canonical.py**
   - Enhanced error handling (separate RuntimeError catch)
   - User-friendly error messages

---

## Testing Checklist

### Before Deployment

- [x] All `daily_features_v2` references removed
- [x] Scanner imports without errors
- [x] `validate_strategies` method exists
- [x] `_check_table_exists` method exists
- [ ] Test with empty `experimental_strategies` table
  - Expected: Info message "Not configured yet"
- [ ] Test with invalid data (expected_r = 5.0)
  - Expected: Validation FAIL badge with error details
- [ ] Test with valid data
  - Expected: Validation PASS badge
- [ ] Test on Monday (no previous trading day over weekend)
  - Expected: Graceful handling of NULL previous day
- [ ] Test all 5 filter types with real data
  - DAY_OF_WEEK, SESSION_CONTEXT, COMBINED, VOLATILITY_REGIME, MULTI_DAY
- [ ] Run full test suite:
  ```bash
  python test_app_sync.py
  python scripts/check/check_experimental_strategies.py
  ```

### Integration Testing

```bash
# 1. Test scanner standalone
python trading_app/experimental_scanner.py

# 2. Test validation script
python scripts/check/check_experimental_strategies.py

# 3. Launch app and check Experimental panel
streamlit run trading_app/app_canonical.py
```

---

## User Experience Improvements

### Before Fixes
1. **Silent crash** on missing table → Empty results
2. **No validation** → Bad data displays as tradeable
3. **Unclear errors** → "Failed to load" (generic)

### After Fixes
1. **Clear message**: "Experimental strategies not configured yet. Run pipeline/schema_experimental_strategies.sql"
2. **Validation badge**: Shows PASS/FAIL status before rendering
3. **Detailed errors**: "win_rate=150% outside [20%, 90%]" (specific issue with strategy ID)
4. **Appropriate icons**: ℹ️ for info, ⚠️ for warnings, ❌ for errors

---

## Implementation Notes

### Design Decisions

**1. Why check table at init vs lazy check?**
- Fail fast: Errors surface immediately when scanner created
- Clearer error context: User knows scanner can't initialize (not query failure)
- Consistent behavior: All scanner instances validated upfront

**2. Why validate in UI vs scanner?**
- Separation of concerns: Scanner scans, UI presents
- Validation method in scanner (reusable), enforcement in UI (user-facing)
- Allows scanner to be used without UI (scripts, tests)

**3. Why RuntimeError vs custom exceptions?**
- Simplicity: RuntimeError is stdlib, clear intent (operational issue)
- Differentiation: Separate from generic Exception (unexpected errors)
- User-friendly: Designed for display to end users

---

## Compliance with CLAUDE.md

✅ **Fixed v2 naming violation**
- UPDATE4_COMPLETE_CHANGELOG.md line 267: "DO NOT use v2 naming"
- All `daily_features_v2` → `daily_features`

✅ **Enforced validation requirement**
- CLAUDE.md "Experimental Strategies Validation" section
- Validation runs automatically before rendering
- Shows validation status to user

✅ **Improved error messages**
- Code Guardian principle: Clear, actionable errors
- Distinguishes between configuration vs operational errors

---

## Next Steps

1. **Test experimental scanner with real data** (Priority 1)
   - Add test coverage for scanner logic
   - Test all 5 filter types
   - Verify UI renders correctly

2. **Create experimental_strategies data** (Priority 2)
   - Run edge discovery
   - Populate experimental_strategies table
   - Validate with check script

3. **Production deployment** (Priority 3)
   - Run full test suite
   - Update BUILD_LOG.md
   - Commit and push changes

---

**All blocking issues resolved. Ready for testing and deployment.**
