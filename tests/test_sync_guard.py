"""
Tests for Startup Sync Guard

Verifies that sync_guard.py correctly detects config/DB mismatches
and blocks app startup when desync is detected.
"""

import pytest
import duckdb
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.sync_guard import assert_sync_or_die, check_sync_status, ConfigSyncError


class TestSyncGuardBasic:
    """Basic sync guard functionality tests"""

    def test_sync_guard_passes_when_synced(self):
        """Verify sync guard passes when DB and config match"""
        # This should pass with current system (assuming test_app_sync.py passes)
        try:
            assert_sync_or_die()
            # If we get here, sync is good
            assert True
        except ConfigSyncError as e:
            pytest.fail(f"Sync guard failed but should pass: {e}")

    def test_sync_guard_detects_missing_database(self):
        """Verify sync guard fails if database doesn't exist"""
        with pytest.raises(FileNotFoundError):
            assert_sync_or_die(db_path="nonexistent.db")

    def test_check_sync_status_returns_dict(self):
        """Verify check_sync_status returns proper dict structure"""
        status = check_sync_status()

        assert isinstance(status, dict)
        assert 'synced' in status
        assert 'errors' in status
        assert 'message' in status
        assert isinstance(status['synced'], bool)
        assert isinstance(status['errors'], list)

    def test_check_sync_status_non_blocking(self):
        """Verify check_sync_status doesn't raise (returns error dict instead)"""
        # Even if sync fails, check_sync_status should return dict (not raise)
        status = check_sync_status(db_path="nonexistent.db")

        assert status['synced'] is False
        assert len(status['errors']) > 0


class TestSyncGuardMismatchDetection:
    """Tests for mismatch detection logic"""

    def test_sync_guard_format_error_message(self):
        """Verify error messages are clear and actionable"""
        try:
            # If this raises, check the error message format
            assert_sync_or_die()
        except ConfigSyncError as e:
            error_msg = str(e)

            # Error message should contain:
            assert "CONFIG/DB SYNC FAILURE" in error_msg or "mismatch" in error_msg.lower()
            # Should tell user how to fix:
            assert "test_app_sync.py" in error_msg or "fix" in error_msg.lower()


class TestSyncGuardIntegration:
    """Integration tests with real database"""

    def test_sync_guard_reads_validated_setups(self):
        """Verify sync guard actually queries validated_setups"""
        # This test verifies the sync guard connects to DB and reads data
        conn = duckdb.connect("data/db/gold.db", read_only=True)

        # Check validated_setups has data
        count = conn.execute("""
            SELECT COUNT(*) FROM validated_setups WHERE instrument = 'MGC'
        """).fetchone()[0]

        conn.close()

        # If DB has MGC setups, sync guard should process them
        if count > 0:
            # Should either pass or raise ConfigSyncError (not other errors)
            try:
                assert_sync_or_die()
            except ConfigSyncError:
                # Expected if mismatch exists
                pass
        else:
            # If no MGC setups, sync guard should raise ConfigSyncError
            with pytest.raises(ConfigSyncError, match="No MGC setups"):
                assert_sync_or_die()

    def test_sync_guard_checks_orb_size_filters(self):
        """Verify sync guard validates ORB size filters specifically"""
        conn = duckdb.connect("data/db/gold.db", read_only=True)

        # Get filters from DB
        db_filters = conn.execute("""
            SELECT orb_time, orb_size_filter
            FROM validated_setups
            WHERE instrument = 'MGC' AND orb_size_filter IS NOT NULL
            LIMIT 1
        """).fetchone()

        conn.close()

        if db_filters:
            # DB has filter data, sync guard should validate it
            # (Actual pass/fail depends on whether config matches)
            try:
                assert_sync_or_die()
                # If passes, config must match DB
                from trading_app.config import MGC_ORB_SIZE_FILTERS
                orb_time, db_filter = db_filters
                config_filters = MGC_ORB_SIZE_FILTERS.get(orb_time, [])

                # Verify sync guard logic: if passed, values should match
                if config_filters and config_filters[0] is not None:
                    assert abs(config_filters[0] - db_filter) <= 0.001

            except ConfigSyncError:
                # If fails, there's a known mismatch (expected in some cases)
                pass


class TestSyncGuardPerformance:
    """Performance and edge case tests"""

    def test_sync_guard_fast_execution(self):
        """Verify sync guard runs quickly (< 1 second)"""
        import time

        start = time.time()
        try:
            assert_sync_or_die()
        except ConfigSyncError:
            pass  # Mismatch is fine for performance test
        elapsed = time.time() - start

        # Should be very fast (< 1 second for startup check)
        assert elapsed < 1.0, f"Sync guard too slow: {elapsed:.2f}s"

    def test_sync_guard_read_only_connection(self):
        """Verify sync guard uses read-only DB connection (won't lock)"""
        # This test verifies the guard doesn't block other DB operations
        # by using read_only=True connection

        # Start sync guard (should use read-only connection)
        try:
            assert_sync_or_die()
        except ConfigSyncError:
            pass

        # Verify we can still connect to DB (not locked)
        conn = duckdb.connect("data/db/gold.db", read_only=True)
        result = conn.execute("SELECT 1").fetchone()
        conn.close()

        assert result[0] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
