---
name: python-testing
description: Pytest best practices for trading app. Use when writing tests, ensuring code quality, or preventing regressions. Focuses on atomic tests, fixtures, mocking, and async patterns.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
context: fork
agent: general-purpose
---

# Python Testing Skill

**Purpose:** Write effective pytest tests for trading application.

Use this skill when:
- Writing new tests
- Fixing failing tests
- Testing critical trading logic
- Ensuring code quality

---

## Key Principles

### 1. Atomic and Self-Contained

**Each test verifies ONE behavior.**

❌ **Bad:**
```python
def test_market_scanner():
    # Tests data loading, scanning, filtering, and output
    # If this fails, which part broke?
    ...
```

✅ **Good:**
```python
def test_scanner_detects_valid_orb():
    # Tests ONLY valid ORB detection
    ...

def test_scanner_filters_small_orbs():
    # Tests ONLY filtering logic
    ...

def test_scanner_handles_missing_data():
    # Tests ONLY missing data handling
    ...
```

**Why:** When a test fails, you know EXACTLY what broke.

---

### 2. Test Naming Convention

**Format:** `test_<what>_<condition>_<expected>`

✅ **Good names:**
```python
def test_orb_detection_when_size_above_filter_returns_valid()
def test_edge_tracker_when_no_data_returns_degraded()
def test_memory_store_trade_with_valid_data_succeeds()
```

❌ **Bad names:**
```python
def test_scanner()  # What does it test?
def test_1()  # Meaningless
def test_edge_stuff()  # Vague
```

**When test fails, name tells you what broke.**

---

### 3. Arrange-Act-Assert Pattern

```python
def test_scanner_detects_valid_setup():
    # ARRANGE: Set up test data
    scanner = MarketScanner()
    test_date = date(2026, 1, 15)

    # ACT: Execute the code
    results = scanner.scan_all_setups(date_local=test_date)

    # ASSERT: Verify expectations
    assert results['valid_count'] > 0
    assert '0900' in [s['orb_time'] for s in results['valid_setups']]
```

---

## Structural Guidelines

### Parameterization

Use `@pytest.mark.parametrize` for variations of same concept:

✅ **Good use:**
```python
@pytest.mark.parametrize("orb_time,expected_rr", [
    ("0900", 8.0),
    ("1000", 8.0),
    ("1100", 8.0),
])
def test_orb_configs_have_correct_rr(orb_time, expected_rr):
    assert MGC_ORB_CONFIGS[orb_time]['rr'] == expected_rr
```

❌ **Bad use (different functionality):**
```python
@pytest.mark.parametrize("test_type,input,expected", [
    ("valid_orb", {...}, True),
    ("invalid_orb", {...}, False),
    ("missing_data", None, Exception),  # Different functionality!
])
```

**Rule:** Parameterize variations of same test. Different functionality = separate tests.

---

### Fixtures

**Use fixtures for shared setup.**

```python
@pytest.fixture
def sample_market_data():
    """Provides sample market data for tests"""
    return {
        'date_local': date(2026, 1, 15),
        'orb_0900_size': 0.08,
        'asia_travel': 1.8,
        'london_reversals': 2
    }

def test_scanner_with_valid_data(sample_market_data):
    scanner = MarketScanner()
    # Use sample_market_data
    ...
```

**Fixture scope:**
- `function` (default) - New instance per test
- `module` - Shared across module tests
- `session` - Shared across all tests

**Prefer function scope unless expensive setup.**

---

### Temporary Files

Use pytest's `tmp_path` fixture:

```python
def test_database_operations(tmp_path):
    db_path = tmp_path / "test.db"

    # Create test database
    conn = duckdb.connect(str(db_path))
    # ... test operations ...
    conn.close()

    # tmp_path automatically cleaned up after test
```

**Never write to real database paths in tests!**

---

## Testing Patterns

### Mocking External Dependencies

**Mock at the boundary** (external services, not internal code).

✅ **Good:**
```python
def test_tradovate_sync_handles_api_failure(mocker):
    # Mock the external API call
    mock_requests = mocker.patch('trading_app.tradovate_integration.requests.post')
    mock_requests.return_value.status_code = 500

    tv = TradovateIntegration()
    success = tv.authenticate()

    assert success is False
```

❌ **Bad:**
```python
def test_tradovate_sync(mocker):
    # Mocking internal methods - tests implementation, not behavior
    mock_internal_method = mocker.patch('trading_app.tradovate_integration.TradovateIntegration._parse_response')
    ...
```

**Rule:** Mock external boundaries (APIs, databases, files). Don't mock internal code.

---

### Error Testing

Use `pytest.raises()` for expected errors:

```python
def test_data_bridge_with_invalid_date_raises_error():
    bridge = DataBridge()

    with pytest.raises(ValueError, match="Invalid date"):
        bridge.fill_gap(start_date=date(2026, 1, 1), end_date=date(2025, 1, 1))
```

---

### Async Testing

**For this project:** No decorators needed (uses `asyncio_mode = "auto"`)

✅ **Good:**
```python
async def test_async_data_fetch():
    result = await fetch_data()
    assert result is not None
```

❌ **Bad (don't use):**
```python
@pytest.mark.asyncio  # NOT NEEDED
async def test_async_data_fetch():
    ...
```

---

## Project-Specific Guidelines

### Database Tests

Use in-memory DuckDB:

```python
@pytest.fixture
def test_db():
    """In-memory test database"""
    conn = duckdb.connect(':memory:')

    # Create test schema
    conn.execute("""
        CREATE TABLE daily_features (
            date_local DATE,
            instrument VARCHAR,
            orb_0900_size DOUBLE,
            ...
        )
    """)

    yield conn
    conn.close()

def test_market_scanner_with_test_db(test_db):
    # Insert test data
    test_db.execute("""
        INSERT INTO daily_features VALUES (?, ?, ?, ...)
    """, [...])

    # Test scanner
    scanner = MarketScanner(db_path=':memory:')
    results = scanner.scan_all_setups()

    assert results['valid_count'] > 0
```

---

### Import Organization

**ALL imports at module level. NEVER inside test functions.**

✅ **Good:**
```python
import pytest
from trading_app.market_scanner import MarketScanner
from trading_app.config import MGC_ORB_CONFIGS

def test_scanner():
    scanner = MarketScanner()
    ...
```

❌ **Bad:**
```python
def test_scanner():
    from trading_app.market_scanner import MarketScanner  # NO!
    ...
```

---

## Critical Tests for Trading App

### Must Test:

1. **Market Scanner**
   - Valid ORB detection
   - Filter application
   - Missing data handling
   - Anomaly detection

2. **Edge Tracker**
   - Performance calculations
   - Degradation detection
   - Regime classification

3. **Data Bridge**
   - Gap detection
   - Script path resolution
   - Update logic

4. **Memory**
   - Trade storage
   - Pattern discovery
   - Query functions

5. **AI Chat**
   - Query parsing
   - Response formatting
   - Error handling

---

## Execution

### Run tests:
```bash
pytest                    # Run all tests
pytest tests/test_scanner.py  # Specific file
pytest -v                 # Verbose
pytest -n auto            # Parallel execution
pytest -k "scanner"       # Match pattern
pytest --cov              # Coverage report
```

### Configuration (pytest.ini):
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

---

## Quality Checklist

Before submitting tests:

✅ **Single responsibility** - Each test verifies one behavior
✅ **No async decorators** - Uses `asyncio_mode = "auto"`
✅ **Module-level imports** - All imports at top
✅ **Descriptive names** - Clear what breaks when fails
✅ **In-memory databases** - No writes to real DB
✅ **Proper parameterization** - Variations only, not different functionality
✅ **Mocked boundaries** - External services only
✅ **AAA pattern** - Arrange-Act-Assert
✅ **Isolated** - Tests don't depend on each other
✅ **Fast** - Each test < 1 second

---

## Anti-Patterns (Don't Do This)

❌ **Testing multiple things:**
```python
def test_everything():
    # Tests 10 different things
    # When it fails, which part broke?
```

❌ **Vague assertions:**
```python
assert results  # What does this test?
```

✅ **Specific assertions:**
```python
assert results['valid_count'] == 1
assert '0900' in [s['orb_time'] for s in results['valid_setups']]
```

❌ **Testing implementation details:**
```python
assert scanner._internal_method() == "something"  # Private method
```

✅ **Testing public API:**
```python
assert scanner.scan_all_setups()['valid_count'] > 0  # Public method
```

❌ **Dependent tests:**
```python
def test_step_1():
    global result
    result = do_something()

def test_step_2():
    # Depends on test_step_1 running first!
    assert result == "expected"
```

✅ **Independent tests:**
```python
def test_step_1():
    result = do_something()
    assert result == "expected"

def test_step_2():
    result = do_something_else()
    assert result == "other_expected"
```

---

## Example Test File

```python
"""
Tests for market scanner functionality
"""
import pytest
from datetime import date
from trading_app.market_scanner import MarketScanner
from trading_app.config import MGC_ORB_CONFIGS


@pytest.fixture
def scanner():
    """Market scanner instance"""
    return MarketScanner()


@pytest.fixture
def sample_conditions():
    """Sample market conditions for testing"""
    return {
        'date_local': date(2026, 1, 15),
        'orb_sizes': {
            '0900': 0.08,
            '1000': 0.05,
            '1100': 0.03
        },
        'asia_travel': 1.8,
        'london_reversals': 2
    }


class TestMarketScanner:
    """Market scanner test suite"""

    def test_scanner_initialization_succeeds(self, scanner):
        """Scanner initializes with valid config"""
        assert scanner is not None
        assert scanner.db_path is not None

    def test_valid_orb_detection_with_large_size_returns_valid(
        self, scanner, sample_conditions
    ):
        """ORB above filter threshold detected as valid"""
        # Arrange
        orb_time = '0900'
        orb_size = sample_conditions['orb_sizes'][orb_time]
        orb_filter = MGC_ORB_CONFIGS[orb_time].get('orb_size_filter', 0.0)

        # Act
        is_valid = orb_size > orb_filter

        # Assert
        assert is_valid is True

    def test_invalid_orb_detection_with_small_size_returns_invalid(
        self, scanner, sample_conditions
    ):
        """ORB below filter threshold detected as invalid"""
        # Arrange
        orb_time = '1100'
        orb_size = sample_conditions['orb_sizes'][orb_time]
        orb_filter = MGC_ORB_CONFIGS[orb_time].get('orb_size_filter', 0.0)

        # Act
        is_valid = orb_size > orb_filter

        # Assert
        assert is_valid is False

    @pytest.mark.parametrize("orb_time", ['0900', '1000', '1100'])
    def test_orb_configs_have_required_fields(self, orb_time):
        """All ORB configs contain required fields"""
        config = MGC_ORB_CONFIGS[orb_time]

        assert 'rr' in config
        assert 'sl_mode' in config
        assert config['rr'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Success Criteria

✅ All tests pass
✅ Each test is atomic (tests one thing)
✅ Names are descriptive
✅ No flaky tests (tests are deterministic)
✅ Fast execution (< 1 second per test)
✅ Good coverage (>80% for critical modules)
✅ Tests document expected behavior
