"""
Test canonical environment setup.

Tests:
- CANONICAL.json loads correctly
- Required files exist
- Database connections work
- No shadow databases exist
- Canonical module functions work

Run:
    pytest tests/test_canonical_env.py -v
"""

import pytest
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.canonical import (
    load_canonical_config,
    get_canon_db_path,
    get_canon_cache_db_path,
    get_canon_docs,
    get_canon_app_entry,
    get_allowed_tables,
    assert_canonical_environment,
)


def test_canonical_json_exists():
    """Test that CANONICAL.json exists."""
    canonical_file = Path(__file__).parent.parent / "CANONICAL.json"
    assert canonical_file.exists(), "CANONICAL.json not found in repo root"


def test_canonical_json_loads():
    """Test that CANONICAL.json is valid JSON."""
    config = load_canonical_config()
    assert isinstance(config, dict), "CANONICAL.json should be a dictionary"
    assert "version" in config, "CANONICAL.json should have version field"
    assert "databases" in config, "CANONICAL.json should have databases section"


def test_canonical_json_structure():
    """Test that CANONICAL.json has required fields."""
    config = load_canonical_config()

    # Required top-level fields
    required_fields = ["version", "databases", "documentation", "entry_points"]
    for field in required_fields:
        assert field in config, f"CANONICAL.json missing required field: {field}"

    # Database section
    assert "main" in config["databases"], "databases.main missing"
    assert "allowed_locations" in config["databases"], "databases.allowed_locations missing"

    # Documentation section
    assert "schema" in config["documentation"], "documentation.schema missing"
    assert "trading_rules" in config["documentation"], "documentation.trading_rules missing"


def test_get_canon_db_path():
    """Test getting canonical database path."""
    db_path = get_canon_db_path()
    assert db_path is not None, "Canonical DB path should not be None"
    assert isinstance(db_path, str), "Canonical DB path should be string"


def test_get_canon_cache_db_path():
    """Test getting canonical cache database path."""
    cache_db = get_canon_cache_db_path()
    assert cache_db == "live_data.db", f"Expected live_data.db, got {cache_db}"


def test_get_canon_docs():
    """Test getting canonical documentation paths."""
    docs = get_canon_docs()
    assert isinstance(docs, dict), "Canonical docs should be dictionary"

    # Check required docs exist
    required_docs = ["schema", "trading_rules", "zero_lookahead"]
    for doc_key in required_docs:
        assert doc_key in docs, f"Missing required doc: {doc_key}"

        # Check files exist
        doc_path = Path(__file__).parent.parent / docs[doc_key]
        assert doc_path.exists(), f"Documentation file not found: {docs[doc_key]}"


def test_get_canon_app_entry():
    """Test getting canonical app entry points."""
    # Mobile app
    mobile_app = get_canon_app_entry("mobile")
    assert mobile_app == "trading_app/app_mobile.py"
    mobile_path = Path(__file__).parent.parent / mobile_app
    assert mobile_path.exists(), f"Mobile app not found: {mobile_app}"

    # Desktop app
    desktop_app = get_canon_app_entry("desktop")
    assert desktop_app == "trading_app/app_trading_hub.py"
    desktop_path = Path(__file__).parent.parent / desktop_app
    assert desktop_path.exists(), f"Desktop app not found: {desktop_app}"

    # Invalid platform should raise error
    with pytest.raises(ValueError):
        get_canon_app_entry("invalid_platform")


def test_get_allowed_tables():
    """Test getting allowed database tables."""
    tables = get_allowed_tables()
    assert isinstance(tables, list), "Allowed tables should be a list"
    assert len(tables) > 0, "Should have at least one allowed table"

    # Check for expected tables
    expected_tables = ["bars_1m", "bars_5m", "daily_features", "validated_setups"]
    for table in expected_tables:
        assert table in tables, f"Expected table missing: {table}"


def test_required_files_exist():
    """Test that all required files exist."""
    config = load_canonical_config()
    repo_root = Path(__file__).parent.parent

    missing_files = []
    for required_file in config.get("required_files", []):
        file_path = repo_root / required_file
        if not file_path.exists():
            missing_files.append(required_file)

    assert len(missing_files) == 0, f"Missing required files: {', '.join(missing_files)}"


def test_connection_module_exists():
    """Test that canonical connection module exists."""
    config = load_canonical_config()
    repo_root = Path(__file__).parent.parent

    conn_module = repo_root / config["connection_module"]["canonical"]
    assert conn_module.exists(), f"Connection module not found: {conn_module}"


def test_no_shadow_databases():
    """Test that no shadow databases exist outside canonical locations."""
    config = load_canonical_config()
    repo_root = Path(__file__).parent.parent

    violations = []

    # Check forbidden patterns
    for pattern in config["databases"]["forbidden_locations"]:
        matches = list(repo_root.glob(pattern))
        for match in matches:
            if match.suffix == ".db":
                violations.append(str(match.relative_to(repo_root)))

    assert len(violations) == 0, (
        f"Shadow databases found (forbidden):\n" +
        "\n".join(f"  - {v}" for v in violations)
    )


def test_assert_canonical_environment():
    """Test canonical environment assertion."""
    # This should not raise an exception
    try:
        result = assert_canonical_environment()
        assert result is True, "Canonical environment check should return True"
    except Exception as e:
        pytest.fail(f"Canonical environment check failed: {e}")


def test_canonical_database_accessible():
    """Test that canonical database is accessible (local mode only)."""
    from trading_app.cloud_mode import is_cloud_deployment

    if is_cloud_deployment():
        pytest.skip("Skipping database access test in cloud mode")

    config = load_canonical_config()
    repo_root = Path(__file__).parent.parent

    main_db = repo_root / config["databases"]["main"]
    assert main_db.exists(), f"Canonical database not found: {main_db}"
    assert main_db.stat().st_size > 0, "Canonical database is empty"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
