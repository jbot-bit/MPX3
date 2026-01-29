# NEW STANDING RULE ADDED - MPX3

**Date**: 2026-01-29
**Status**: ✅ IMPLEMENTED
**Effective**: Immediately for all new code

---

## RULE: BOUNDARY + STATE TEST SUITE MANDATORY

**Any code that runs in LIVE mode must pass a "boundary + state" test suite.**

This is now a **STANDING RULE** for the MPX3 project and applies to all live trading code.

---

## WHAT WAS ADDED

### 1. Comprehensive Rule Document
**File**: `LIVE_TRADING_TEST_REQUIREMENTS.md`
- 13 pages of detailed requirements
- Test requirements by code type (entry/exit, position sizing, data validation, P&L, state management)
- Examples of violations and correct implementations
- Enforcement procedures
- Test suite structure

### 2. Updated CLAUDE.md
**Added**: Critical section at top of file
- Highlights boundary + state test requirement
- Links to full documentation
- Explains rationale (53 bugs found, 40% boundary/state issues)
- Makes rule visible to all future work

### 3. Test Templates Created
**Files**:
- `tests/templates/boundary_test_template.py` - Template for writing boundary tests
- `tests/templates/state_test_template.py` - Template for writing state tests

**Test directories created**:
- `tests/boundary/` - For boundary tests
- `tests/state/` - For state tests

---

## ENFORCEMENT

### Pull Request Requirements:
- [ ] Boundary tests added for all edge cases
- [ ] State tests added for all state transitions
- [ ] All tests pass locally
- [ ] Coverage > 80% for modified code
- [ ] Manual testing completed in staging

### Automated Checks (To Be Added):
```yaml
# .github/workflows/live-trading-tests.yml
name: Live Trading Tests
on: [pull_request]
jobs:
  boundary-state-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run boundary tests
        run: pytest tests/boundary/ -v
      - name: Run state tests
        run: pytest tests/state/ -v
      - name: Check coverage
        run: pytest tests/boundary/ tests/state/ --cov=trading_app --cov-fail-under=80
```

---

## WHAT TESTS ARE REQUIRED

### Boundary Tests (Edge Cases):
- ✅ Empty DataFrames
- ✅ Single row DataFrames
- ✅ Null/None values
- ✅ Missing columns
- ✅ Zero values
- ✅ Negative values
- ✅ Exact boundaries
- ✅ Floating point precision
- ✅ Very large values
- ✅ Out-of-order data

### State Tests (State Transitions):
- ✅ Symbol changes (MGC → NQ → MGC)
- ✅ Connection loss and recovery
- ✅ Concurrent modifications (TOCTOU)
- ✅ Partial data availability
- ✅ Stale cache invalidation
- ✅ Error rollback
- ✅ Resource cleanup on errors
- ✅ Idempotent operations
- ✅ State consistency
- ✅ Concurrent session isolation

---

## EXAMPLES FROM TEMPLATES

### Boundary Test Example:
```python
def test_empty_dataframe(self):
    """Test that function handles empty DataFrame without crashing"""
    # Arrange
    empty_df = pd.DataFrame()

    # Act
    result = your_function(empty_df)

    # Assert
    assert result is None or isinstance(result, expected_type)
    # Should not crash - returning None or empty result is acceptable
```

### State Test Example:
```python
def test_symbol_change_cleanup(self):
    """Test that changing symbol cleans up old state"""
    # Arrange
    obj = YourClass("MGC")
    old_symbol = obj.symbol

    # Act - Change symbol
    obj.change_symbol("NQ")

    # Assert - Old state cleaned up, new state initialized
    assert obj.symbol == "NQ"
    assert obj.symbol != old_symbol
    assert obj.data is not None  # New data loaded
```

---

## RATIONALE

### Why This Rule Exists:
1. **Ghost Audit Found 53 Bugs**
   - 17 empty DataFrame crashes
   - 1 TOCTOU race condition
   - 1 state corruption on symbol change
   - 1 NULL parameter bug
   - 5+ other boundary/state issues

2. **Production Safety**
   - Live trading requires zero tolerance for crashes
   - Bugs cause financial losses
   - Real money at risk

3. **Prevent Regressions**
   - Tests catch bugs before deployment
   - Automated checks prevent bad code from merging
   - Documentation ensures future code follows best practices

### What This Rule Prevents:
- Empty DataFrame crashes → **System downtime during live trading**
- TOCTOU race conditions → **Random crashes in multi-threaded environment**
- State corruption → **Trading wrong instrument with wrong data**
- NULL parameter bugs → **Zero trades on first day**
- Float comparison errors → **Wrong filter decisions**
- Resource leaks → **Connection pool exhaustion**

---

## APPLIES TO

### ✅ MUST Have Tests:
- `*entry_rules.py` - Entry/exit logic
- `*execution_*.py` - Trade execution
- `*strategy_*.py` - Strategy evaluation
- `*risk_*.py` - Risk management
- `*position_*.py` - Position sizing
- `*data_loader.py` - Data fetching/validation
- `*pnl_*.py` - P&L calculations
- `*app_trading_*.py` - Live trading apps
- `*setup_detector.py` - Setup detection
- `*validator*.py` - Validation logic

### ❌ Optional (Not Live Trading):
- `analysis/` - Research/analysis scripts
- `scripts/` - One-off utilities
- Visualization code
- Historical backtesting (non-live)

---

## NEXT STEPS

### For Existing Code:
1. **Audit Priority**: Identify live trading code paths without tests
2. **Write Tests**: Use templates to add boundary + state tests
3. **Achieve Coverage**: Target 80%+ for all live trading modules
4. **Document**: Add test rationale in docstrings

### For New Code:
1. **Read Requirements**: `LIVE_TRADING_TEST_REQUIREMENTS.md` BEFORE coding
2. **Write Tests First**: TDD approach (test-driven development)
3. **Use Templates**: Copy from `tests/templates/`
4. **Run Before PR**: `pytest tests/boundary/ tests/state/ -v`

### For Code Review:
1. **Check Tests Exist**: Every PR touching live trading code must include tests
2. **Review Test Quality**: Tests must actually test edge cases (not just happy path)
3. **Verify Coverage**: Run coverage report, ensure 80%+
4. **Block Merges**: No tests = no merge (non-negotiable)

---

## IMPLEMENTATION STATUS

### ✅ Completed:
- [x] Created comprehensive requirements document
- [x] Updated CLAUDE.md with rule
- [x] Created test templates (boundary + state)
- [x] Created test directory structure
- [x] Documented rationale and examples

### 🔄 In Progress:
- [ ] Add CI/CD pipeline checks (GitHub Actions)
- [ ] Write initial test suite for existing code
- [ ] Achieve 80% coverage for live trading modules

### 📋 TODO:
- [ ] Add pre-commit hooks to enforce test presence
- [ ] Create test generation tool (auto-generate test stubs)
- [ ] Train team on boundary + state testing
- [ ] Quarterly review of test coverage

---

## RESOURCES

### Documentation:
- `LIVE_TRADING_TEST_REQUIREMENTS.md` - Full specification (13 pages)
- `CLAUDE.md` - Project guidelines (includes rule at top)
- `GHOST_AUDIT_COMPLETE.md` - Original 44 bugs found
- `DEEP_AUDIT_ADDENDUM.md` - Additional 9 logic bugs
- `TOP_4_BUGS_FIXED.md` - Examples of fixes

### Templates:
- `tests/templates/boundary_test_template.py` - Boundary test template
- `tests/templates/state_test_template.py` - State test template

### Tools:
- pytest - Test runner
- pytest-cov - Coverage reporting
- hypothesis - Property-based testing
- pytest-timeout - Prevent infinite loops

---

## APPROVAL

This standing rule is **approved and mandatory** for all MPX3 live trading code.

**Effective**: 2026-01-29
**Enforced By**: Code review + CI/CD pipeline (when implemented)
**Exception Authority**: Project owner only
**Review Cadence**: Quarterly

---

## SUMMARY

**New Rule**: Any code that runs in LIVE mode must pass boundary + state tests.

**Rationale**: Ghost audit found 53 bugs (40% boundary/state issues). Live trading requires zero tolerance for crashes. Real money at risk.

**Enforcement**: All PRs must include tests. Coverage > 80% required. No exceptions.

**Resources**: Full documentation, test templates, and examples provided.

**Status**: Rule active immediately. Existing code to be retrofitted with tests. New code must have tests from day 1.
