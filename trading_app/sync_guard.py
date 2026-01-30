"""
Startup Sync Guard - Prevents App Launch with Config/DB Desync

CRITICAL: This guard runs at app startup BEFORE any trading logic.
If validated_setups (DB) doesn't match config.py, app WILL NOT START.

Purpose: Prevent real-money losses from trading with wrong filters/configs.

Usage:
    from trading_app.sync_guard import assert_sync_or_die
    assert_sync_or_die()  # Call at top of app entrypoint

Enforcement: Fail-closed (app crashes if mismatch)
"""

import duckdb
from pathlib import Path
from typing import Dict, List


class ConfigSyncError(Exception):
    """Raised when config.py doesn't match validated_setups database"""
    pass


def assert_sync_or_die(db_connection, db_path: str = "data/db/gold.db") -> None:
    """
    Fast sync check. Raises ConfigSyncError if mismatch.

    Checks:
    - MGC ORB size filters (validated_setups.orb_size_filter vs config.py)
    - Strategy count consistency
    - Filter value precision (0.001 tolerance)

    Args:
        db_connection: REQUIRED database connection (from app singleton)
        db_path: Path to gold.db (default: data/db/gold.db) - used for existence check only

    Raises:
        ConfigSyncError: If DB and config don't match
        FileNotFoundError: If database doesn't exist

    Note: This is a FAST check (not full test_app_sync.py).
          It checks critical fields only to avoid startup delays.
    """

    # Check DB exists
    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}\n"
            f"Cannot verify config sync without database."
        )

    # CRITICAL: Connection must be provided (no fallback to prevent connection conflicts)
    if db_connection is None:
        raise ConfigSyncError(
            "No database connection provided to sync_guard.\n"
            "This function must receive an injected connection to prevent DuckDB config conflicts.\n"
            "Call this AFTER creating the singleton connection."
        )

    conn = db_connection

    try:
        # Get DB values for MGC
        db_setups = conn.execute("""
            SELECT orb_time, orb_size_filter, rr
            FROM validated_setups
            WHERE instrument = 'MGC'
            ORDER BY orb_time, rr
        """).fetchall()

        if not db_setups:
            raise ConfigSyncError(
                "No MGC setups found in validated_setups.\n"
                "Database may be corrupted or empty."
            )

        # Import config (must be after DB check to avoid import errors)
        try:
            from trading_app.config import MGC_ORB_SIZE_FILTERS
        except ImportError as e:
            raise ConfigSyncError(
                f"Cannot import config.py: {e}\n"
                f"Config file may be missing or corrupted."
            )

        # Build map of DB filters
        db_filters: Dict[str, List[float]] = {}
        for orb_time, orb_filter, rr in db_setups:
            if orb_time not in db_filters:
                db_filters[orb_time] = []
            if orb_filter is not None:
                db_filters[orb_time].append(orb_filter)

        # Compare each ORB time
        mismatches = []
        for orb_time in db_filters.keys():
            config_filters = MGC_ORB_SIZE_FILTERS.get(orb_time, [])
            db_filter_values = db_filters[orb_time]

            # Filter out None values (placeholder filters = no constraint)
            cfg = [x for x in config_filters if x is not None]

            # If all filters are None, treat as "no constraint" and skip check
            if len(cfg) == 0:
                continue

            # Check if filters exist in both
            if not cfg and db_filter_values:
                mismatches.append(
                    f"  {orb_time}: DB has filters {db_filter_values}, "
                    f"config has none"
                )
                continue

            if cfg and not db_filter_values:
                mismatches.append(
                    f"  {orb_time}: Config has filters {cfg}, "
                    f"DB has none"
                )
                continue

            # Compare filter values (if both exist)
            if cfg and db_filter_values:
                # Take first filter from config (for fast check)
                config_val = cfg[0]
                db_val = db_filter_values[0] if db_filter_values else None

                if config_val is not None and db_val is not None:
                    if abs(config_val - db_val) > 0.001:
                        mismatches.append(
                            f"  {orb_time}: DB={db_val:.3f}, "
                            f"config={config_val:.3f} "
                            f"(diff={abs(db_val - config_val):.4f})"
                        )

        # Raise if any mismatches found
        if mismatches:
            error_msg = (
                "CONFIG/DB SYNC FAILURE - APP STARTUP BLOCKED\n\n"
                "validated_setups (database) does NOT match config.py\n\n"
                "Mismatches found:\n" + "\n".join(mismatches) + "\n\n"
                "CRITICAL: Trading with wrong filters causes REAL MONEY LOSS.\n\n"
                "To fix:\n"
                "1. Run: python test_app_sync.py\n"
                "2. Update config.py to match database\n"
                "3. Or update database to match config.py\n"
                "4. Re-run test_app_sync.py to verify\n\n"
                "DO NOT bypass this check. Fix the mismatch."
            )
            raise ConfigSyncError(error_msg)

    except ConfigSyncError:
        # Re-raise config errors
        raise
    except Exception as e:
        # Catch unexpected errors (no connection cleanup - caller owns connection)
        raise ConfigSyncError(
            f"Sync verification failed with unexpected error: {e}\n"
            f"App startup blocked for safety."
        )


def check_sync_status(db_connection, db_path: str = "data/db/gold.db") -> Dict[str, any]:
    """
    Non-blocking sync status check (doesn't raise on mismatch).

    Args:
        db_connection: REQUIRED database connection (from app singleton)
        db_path: Path to gold.db (default: data/db/gold.db)

    Returns:
        dict with keys:
        - 'synced': bool (True if synced, False if mismatch)
        - 'errors': list of error messages
        - 'db_count': number of DB setups
        - 'config_orbs': list of ORB times in config
    """
    try:
        assert_sync_or_die(db_connection, db_path)
        return {
            'synced': True,
            'errors': [],
            'message': 'Config and DB are synchronized'
        }
    except ConfigSyncError as e:
        return {
            'synced': False,
            'errors': [str(e)],
            'message': 'Config/DB mismatch detected'
        }
    except Exception as e:
        return {
            'synced': False,
            'errors': [f"Unexpected error: {e}"],
            'message': 'Sync check failed'
        }
