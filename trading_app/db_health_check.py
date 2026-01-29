"""
Database Health Check - Auto-fix WAL corruption on startup

Runs before app loads to ensure database is in good state.
"""

import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def check_and_fix_wal_corruption(db_path: str) -> bool:
    """
    Check for WAL corruption and auto-fix if needed

    Args:
        db_path: Path to database file

    Returns:
        True if database is healthy (or was fixed)
        False if unable to fix
    """
    db_file = Path(db_path)
    wal_file = Path(f"{db_path}.wal")

    # If no WAL file exists, database is fine
    if not wal_file.exists():
        logger.info(f"Database healthy: no WAL file present")
        return True

    # Try to connect to database to test if WAL is corrupt
    try:
        import duckdb
        conn = duckdb.connect(str(db_path))
        conn.execute("SELECT 1").fetchone()
        conn.close()
        logger.info(f"Database healthy: WAL file valid")
        return True

    except Exception as e:
        error_str = str(e)

        # Check if it's WAL corruption
        if "WAL file" in error_str or "INTERNAL Error" in error_str:
            logger.warning(f"WAL corruption detected: {error_str}")
            logger.info(f"Auto-fixing: Deleting corrupt WAL file")

            try:
                # Delete corrupt WAL file
                wal_file.unlink()
                logger.info(f"[OK] Deleted corrupt WAL file: {wal_file}")

                # Verify database works now
                conn = duckdb.connect(str(db_path))
                conn.execute("SELECT 1").fetchone()
                conn.close()

                logger.info(f"[OK] Database recovered successfully")
                return True

            except Exception as fix_error:
                logger.error(f"Failed to fix WAL corruption: {fix_error}")
                return False
        else:
            # Different error, not WAL related
            logger.error(f"Database error (not WAL): {e}")
            return False


def run_startup_health_check(db_path: str) -> bool:
    """
    Run all health checks on database at startup

    Args:
        db_path: Path to database file

    Returns:
        True if all checks pass
        False if database is unhealthy
    """
    logger.info(f"Running database health check: {db_path}")

    # Check 1: File exists
    if not Path(db_path).exists():
        logger.error(f"Database file not found: {db_path}")
        return False

    # Check 2: WAL corruption
    if not check_and_fix_wal_corruption(db_path):
        logger.error(f"WAL corruption could not be fixed")
        return False

    logger.info(f"[OK] Database health check passed")
    return True


if __name__ == "__main__":
    # Test the health check
    db_path = Path(__file__).parent.parent / "data" / "db" / "gold.db"
    result = run_startup_health_check(str(db_path))

    if result:
        print("[OK] Database is healthy")
    else:
        print("[ERROR] Database has issues")
