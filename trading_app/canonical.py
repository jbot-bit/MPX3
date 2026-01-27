"""
CANONICAL ENFORCEMENT MODULE

Single source of truth for all canonical paths and runtime environment validation.
Loads from CANONICAL.json and provides functions to:
- Get canonical database paths
- Get canonical documentation paths
- Validate environment setup
- Assert no duplicate/shadow databases exist

Usage:
    from trading_app.canonical import get_canon_db_path, assert_canonical_environment

    # Get canonical database path
    db_path = get_canon_db_path()

    # Validate environment (raises exception if violations found)
    assert_canonical_environment()
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Path to CANONICAL.json (repo root)
CANONICAL_FILE = Path(__file__).parent.parent / "CANONICAL.json"


def load_canonical_config() -> Dict:
    """Load CANONICAL.json configuration."""
    if not CANONICAL_FILE.exists():
        raise FileNotFoundError(
            f"CANONICAL.json not found at {CANONICAL_FILE}. "
            "This file is required for canonical enforcement."
        )

    with open(CANONICAL_FILE, 'r') as f:
        return json.load(f)


def get_canon_db_path() -> str:
    """
    Get canonical main database path.

    Returns:
        str: Path to gold.db or MotherDuck connection string
    """
    config = load_canonical_config()

    # Check if running in cloud mode
    from trading_app.cloud_mode import is_cloud_deployment

    if is_cloud_deployment():
        # Cloud mode - use MotherDuck
        from trading_app.cloud_mode import get_database_connection
        # Return connection string (not path)
        token = os.getenv("MOTHERDUCK_TOKEN")
        if token:
            return f"md:projectx_prod?motherduck_token={token}"
        else:
            logger.warning("Cloud mode but MOTHERDUCK_TOKEN not set")
            return config["databases"]["main"]
    else:
        # Local mode - use gold.db
        return config["databases"]["main"]


def get_canon_cache_db_path() -> str:
    """Get canonical cache database path."""
    config = load_canonical_config()
    return config["databases"]["cache"]


def get_canon_docs() -> Dict[str, str]:
    """
    Get canonical documentation paths.

    Returns:
        Dict with keys: schema, trading_rules, zero_lookahead, etc.
    """
    config = load_canonical_config()
    return config["documentation"]


def get_canon_app_entry(platform: str = "mobile") -> str:
    """
    Get canonical app entry point path.

    Args:
        platform: "mobile" or "desktop"

    Returns:
        str: Path to app entry point
    """
    config = load_canonical_config()
    if platform not in config["entry_points"]:
        raise ValueError(f"Unknown platform: {platform}. Valid: mobile, desktop")
    return config["entry_points"][platform]


def get_allowed_tables() -> List[str]:
    """Get list of allowed database tables."""
    config = load_canonical_config()
    return config["database_tables"]["persistent"] + config["database_tables"]["cache"]


def assert_canonical_environment():
    """
    Assert canonical environment is valid.

    Checks:
    1. CANONICAL.json exists
    2. Required files exist
    3. No shadow databases outside canonical locations
    4. Canonical database is accessible

    Raises:
        Exception: If any check fails
    """
    config = load_canonical_config()
    repo_root = CANONICAL_FILE.parent

    # Check 1: Required files exist
    logger.info("Checking required files...")
    missing_files = []
    for required_file in config.get("required_files", []):
        file_path = repo_root / required_file
        if not file_path.exists():
            missing_files.append(required_file)

    if missing_files:
        raise FileNotFoundError(
            f"Missing required canonical files: {', '.join(missing_files)}"
        )

    # Check 2: No shadow databases
    logger.info("Checking for shadow databases...")
    shadow_dbs = []

    # Check forbidden locations
    for forbidden_pattern in config["databases"]["forbidden_locations"]:
        if "*" in forbidden_pattern:
            # Glob pattern
            for match in repo_root.glob(forbidden_pattern):
                if match.exists() and match.suffix == ".db":
                    shadow_dbs.append(str(match.relative_to(repo_root)))

    if shadow_dbs:
        raise Exception(
            f"Shadow database files found (violates canonical enforcement):\n"
            f"{chr(10).join(f'  - {db}' for db in shadow_dbs)}\n"
            f"Remove these files or add to backups/"
        )

    # Check 3: Canonical database accessible (local mode only)
    from trading_app.cloud_mode import is_cloud_deployment

    if not is_cloud_deployment():
        logger.info("Checking canonical database access...")
        main_db = repo_root / config["databases"]["main"]
        if not main_db.exists():
            raise FileNotFoundError(
                f"Canonical database not found: {main_db}\n"
                f"Run backfill scripts to populate database."
            )

    # Check 4: Connection module exists
    logger.info("Checking connection module...")
    connection_module = repo_root / config["connection_module"]["canonical"]
    if not connection_module.exists():
        raise FileNotFoundError(
            f"Canonical connection module not found: {connection_module}"
        )

    # All checks passed
    logger.info("OK: CANONICAL ENVIRONMENT VALIDATED")
    return True


def print_canonical_banner():
    """Print canonical environment banner (for startup)."""
    try:
        config = load_canonical_config()

        print("=" * 70)
        print("CANONICAL ENVIRONMENT")
        print("=" * 70)

        # Database
        db_path = get_canon_db_path()
        if "motherduck" in db_path.lower() or db_path.startswith("md:"):
            print(f"DB: MotherDuck (projectx_prod)")
        else:
            print(f"DB: {db_path}")

        # Documentation
        docs = get_canon_docs()
        print(f"Schema: {docs['schema']}")
        print(f"Rules: {docs['trading_rules']}")

        # Connection module
        conn_module = config["connection_module"]["canonical"]
        print(f"Connection: {conn_module}")

        print("=" * 70)

    except Exception as e:
        logger.error(f"Error printing canonical banner: {e}")


if __name__ == "__main__":
    # Test the canonical module
    print("\n" + "=" * 70)
    print("CANONICAL MODULE TEST")
    print("=" * 70)

    try:
        print("\n1. Loading CANONICAL.json...")
        config = load_canonical_config()
        print(f"   [OK] Loaded config (version {config['version']})")

        print("\n2. Getting canonical paths...")
        print(f"   DB: {get_canon_db_path()}")
        print(f"   Cache DB: {get_canon_cache_db_path()}")
        print(f"   Mobile app: {get_canon_app_entry('mobile')}")
        print(f"   Desktop app: {get_canon_app_entry('desktop')}")

        print("\n3. Getting canonical docs...")
        docs = get_canon_docs()
        for key, path in docs.items():
            print(f"   {key}: {path}")

        print("\n4. Running canonical environment checks...")
        assert_canonical_environment()

        print("\n5. Canonical banner:")
        print_canonical_banner()

        print("\n" + "=" * 70)
        print("[OK] ALL TESTS PASSED")
        print("=" * 70)

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
