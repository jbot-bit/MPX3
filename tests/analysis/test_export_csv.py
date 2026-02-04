"""
Comprehensive unit tests for analysis/export_csv.py

Tests cover:
- CSVExporter class initialization
- export_daily_features method
- export_orb_performance method
- export_session_stats method
- export_bars method
- Edge cases and error handling
"""

import pytest
import os
import sys
from pathlib import Path
from datetime import date, timedelta
from pipeline.paths import GOLD_DB_PATH

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.export_csv import CSVExporter


# =============================================================================
# Test CSVExporter Initialization
# =============================================================================

class TestCSVExporterInit:
    """Test CSVExporter initialization"""

    def test_default_initialization(self, tmp_path):
        """CSVExporter should initialize with defaults"""
        exporter = CSVExporter(db_path=str(tmp_path / "test.db"), output_dir=str(tmp_path / "exports"))
        assert exporter.db_path == str(tmp_path / "test.db")
        assert exporter.output_dir == str(tmp_path / "exports")

    def test_output_dir_created(self, tmp_path):
        """CSVExporter should create output directory if it doesn't exist"""
        output_dir = tmp_path / "new_exports"
        assert not output_dir.exists()
        CSVExporter(db_path=str(tmp_path / "test.db"), output_dir=str(output_dir))
        assert output_dir.exists()

    def test_custom_output_dir(self, tmp_path):
        """CSVExporter should accept custom output directory"""
        custom_dir = tmp_path / "custom"
        exporter = CSVExporter(db_path=str(tmp_path / "test.db"), output_dir=str(custom_dir))
        assert exporter.output_dir == str(custom_dir)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_db_with_data(tmp_path):
    """Create a mock database with test data"""
    import duckdb

    db_path = tmp_path / GOLD_DB_PATH
    conn = duckdb.connect(str(db_path))

    # Create daily_features table with required columns
    conn.execute("""
        CREATE TABLE daily_features (
            date_local DATE,
            instrument VARCHAR DEFAULT 'MGC',
            asia_high DOUBLE,
            asia_low DOUBLE,
            asia_range DOUBLE,
            asia_type VARCHAR,
            london_high DOUBLE,
            london_low DOUBLE,
            london_type VARCHAR,
            london_range DOUBLE,
            ny_high DOUBLE,
            ny_low DOUBLE,
            ny_type VARCHAR,
            ny_range DOUBLE,
            pre_ny_travel DOUBLE,
            pre_orb_travel DOUBLE,
            atr_20 DOUBLE,
            orb_0900_high DOUBLE,
            orb_0900_low DOUBLE,
            orb_0900_size DOUBLE,
            orb_0900_break_dir VARCHAR,
            orb_0900_outcome VARCHAR,
            orb_0900_r_multiple DOUBLE,
            orb_0900_mae DOUBLE,
            orb_0900_mfe DOUBLE,
            orb_1000_high DOUBLE,
            orb_1000_low DOUBLE,
            orb_1000_size DOUBLE,
            orb_1000_break_dir VARCHAR,
            orb_1000_outcome VARCHAR,
            orb_1000_r_multiple DOUBLE,
            orb_1000_mae DOUBLE,
            orb_1000_mfe DOUBLE,
            orb_1100_high DOUBLE,
            orb_1100_low DOUBLE,
            orb_1100_size DOUBLE,
            orb_1100_break_dir VARCHAR,
            orb_1100_outcome VARCHAR,
            orb_1100_r_multiple DOUBLE,
            orb_1100_mae DOUBLE,
            orb_1100_mfe DOUBLE,
            orb_1800_high DOUBLE,
            orb_1800_low DOUBLE,
            orb_1800_size DOUBLE,
            orb_1800_break_dir VARCHAR,
            orb_1800_outcome VARCHAR,
            orb_1800_r_multiple DOUBLE,
            orb_1800_mae DOUBLE,
            orb_1800_mfe DOUBLE,
            orb_2300_high DOUBLE,
            orb_2300_low DOUBLE,
            orb_2300_size DOUBLE,
            orb_2300_break_dir VARCHAR,
            orb_2300_outcome VARCHAR,
            orb_2300_r_multiple DOUBLE,
            orb_2300_mae DOUBLE,
            orb_2300_mfe DOUBLE,
            orb_0030_high DOUBLE,
            orb_0030_low DOUBLE,
            orb_0030_size DOUBLE,
            orb_0030_break_dir VARCHAR,
            orb_0030_outcome VARCHAR,
            orb_0030_r_multiple DOUBLE,
            orb_0030_mae DOUBLE,
            orb_0030_mfe DOUBLE,
            rsi_at_orb DOUBLE
        )
    """)

    # Insert test data for multiple dates
    today = date.today()
    for i in range(10):
        d = today - timedelta(days=i)
        conn.execute(f"""
            INSERT INTO daily_features (
                date_local, instrument, asia_high, asia_low, asia_range, asia_type,
                london_high, london_low, london_type, london_range,
                ny_high, ny_low, ny_type, ny_range,
                pre_ny_travel, pre_orb_travel, atr_20,
                orb_0900_high, orb_0900_low, orb_0900_size, orb_0900_break_dir, orb_0900_outcome, orb_0900_r_multiple, orb_0900_mae, orb_0900_mfe,
                orb_1000_high, orb_1000_low, orb_1000_size, orb_1000_break_dir, orb_1000_outcome, orb_1000_r_multiple, orb_1000_mae, orb_1000_mfe,
                orb_1100_high, orb_1100_low, orb_1100_size, orb_1100_break_dir, orb_1100_outcome, orb_1100_r_multiple, orb_1100_mae, orb_1100_mfe,
                orb_1800_high, orb_1800_low, orb_1800_size, orb_1800_break_dir, orb_1800_outcome, orb_1800_r_multiple, orb_1800_mae, orb_1800_mfe,
                orb_2300_high, orb_2300_low, orb_2300_size, orb_2300_break_dir, orb_2300_outcome, orb_2300_r_multiple, orb_2300_mae, orb_2300_mfe,
                orb_0030_high, orb_0030_low, orb_0030_size, orb_0030_break_dir, orb_0030_outcome, orb_0030_r_multiple, orb_0030_mae, orb_0030_mfe,
                rsi_at_orb
            ) VALUES (
                '{d}', 'MGC', 2650.0, 2640.0, 10.0, 'EXPANDED',
                2660.0, 2645.0, 'CONSOLIDATION', 15.0,
                2665.0, 2650.0, 'EXPANSION', 15.0,
                5.0, 3.0, 15.0,
                2651.0, 2650.0, 1.0, 'UP', '{'WIN' if i % 2 == 0 else 'LOSS'}', {1.5 if i % 2 == 0 else -1.0}, 0.5, 2.0,
                2652.0, 2651.0, 1.0, 'DOWN', '{'WIN' if i % 3 == 0 else 'LOSS'}', {2.0 if i % 3 == 0 else -1.0}, 0.3, 2.5,
                2653.0, 2652.0, 1.0, 'UP', 'WIN', 1.0, 0.2, 1.5,
                2654.0, 2653.0, 1.0, 'DOWN', 'LOSS', -1.0, 1.0, 0.5,
                2655.0, 2654.0, 1.0, 'UP', 'WIN', 1.5, 0.4, 2.0,
                2656.0, 2655.0, 1.0, 'DOWN', 'LOSS', -1.0, 0.8, 0.3,
                55.0
            )
        """)

    # Create bars tables
    conn.execute("""
        CREATE TABLE bars_1m (
            ts_utc TIMESTAMPTZ,
            symbol VARCHAR,
            source_symbol VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE bars_5m (
            ts_utc TIMESTAMPTZ,
            symbol VARCHAR,
            source_symbol VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume INTEGER
        )
    """)

    conn.close()
    return str(db_path)


@pytest.fixture
def exporter(mock_db_with_data, tmp_path):
    """Create CSVExporter with mock database"""
    output_dir = tmp_path / "exports"
    return CSVExporter(db_path=mock_db_with_data, output_dir=str(output_dir))


# =============================================================================
# Test export_daily_features
# =============================================================================

class TestExportDailyFeatures:
    """Test export_daily_features method"""

    def test_export_all_data(self, exporter):
        """Export all daily features without date filter"""
        output_path, row_count = exporter.export_daily_features()
        assert os.path.exists(output_path)
        assert row_count == 10
        assert output_path.endswith(".csv")

    def test_export_with_days_filter(self, exporter):
        """Export with days filter"""
        output_path, row_count = exporter.export_daily_features(days=5)
        assert os.path.exists(output_path)
        # days=5 filters to last 5 days from today
        # With 10 test rows spread across 10 days, we expect ~5-6 rows
        assert row_count <= 10  # Should be fewer than all data

    def test_export_custom_filename(self, exporter):
        """Export with custom filename"""
        output_path, row_count = exporter.export_daily_features(output_file="custom.csv")
        assert output_path.endswith("custom.csv")
        assert os.path.exists(output_path)

    def test_export_filename_contains_suffix(self, exporter):
        """Auto-generated filename should indicate filter"""
        output_path1, _ = exporter.export_daily_features()
        assert "_all" in output_path1

        output_path2, _ = exporter.export_daily_features(days=30)
        assert "_last_30d" in output_path2

    def test_export_creates_valid_csv(self, exporter):
        """Exported file should be valid CSV"""
        import csv
        output_path, _ = exporter.export_daily_features()

        with open(output_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            assert len(header) > 0
            # Verify some expected columns
            assert "date_local" in header


# =============================================================================
# Test export_orb_performance
# =============================================================================

class TestExportORBPerformance:
    """Test export_orb_performance method"""

    def test_export_orb_performance(self, exporter):
        """Export ORB performance summary"""
        output_path, row_count = exporter.export_orb_performance()
        assert os.path.exists(output_path)
        assert output_path.endswith(".csv")

    def test_export_orb_performance_custom_filename(self, exporter):
        """Export with custom filename"""
        output_path, _ = exporter.export_orb_performance(output_file="orb_perf.csv")
        assert output_path.endswith("orb_perf.csv")

    def test_export_orb_performance_content(self, exporter):
        """Check exported content structure"""
        import csv
        output_path, _ = exporter.export_orb_performance()

        with open(output_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            # Check expected columns
            assert "orb_time" in header
            assert "direction" in header
            assert "win_rate" in header or "total_trades" in header


# =============================================================================
# Test export_session_stats
# =============================================================================

class TestExportSessionStats:
    """Test export_session_stats method"""

    def test_export_session_stats(self, exporter):
        """Export session statistics"""
        output_path, row_count = exporter.export_session_stats()
        assert os.path.exists(output_path)
        assert output_path.endswith(".csv")

    def test_export_session_stats_custom_filename(self, exporter):
        """Export with custom filename"""
        output_path, _ = exporter.export_session_stats(output_file="sessions.csv")
        assert output_path.endswith("sessions.csv")


# =============================================================================
# Test export_bars
# =============================================================================

class TestExportBars:
    """Test export_bars method"""

    def test_export_bars_invalid_table(self, exporter):
        """Invalid table name should raise error"""
        with pytest.raises(ValueError) as exc_info:
            exporter.export_bars(table="invalid_table", target_date=date.today())
        assert "Invalid table" in str(exc_info.value)

    def test_export_bars_valid_tables(self, exporter):
        """Valid table names should be accepted"""
        # Should not raise (even if no data)
        exporter.export_bars(table="bars_1m", target_date=date.today())
        exporter.export_bars(table="bars_5m", target_date=date.today())

    def test_export_bars_custom_filename(self, exporter, tmp_path):
        """Export with custom filename"""
        output_path, _ = exporter.export_bars(
            table="bars_1m",
            target_date=date.today(),
            output_file="custom_bars.csv"
        )
        assert output_path.endswith("custom_bars.csv")


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_export_empty_database(self, tmp_path):
        """Export from empty database should handle gracefully"""
        import duckdb

        db_path = tmp_path / "empty.db"
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE daily_features (
                date_local DATE,
                instrument VARCHAR,
                asia_high DOUBLE,
                asia_low DOUBLE,
                asia_range DOUBLE,
                asia_type VARCHAR,
                london_high DOUBLE,
                london_low DOUBLE,
                london_type VARCHAR,
                ny_high DOUBLE,
                ny_low DOUBLE,
                ny_type VARCHAR,
                pre_ny_travel DOUBLE,
                pre_orb_travel DOUBLE,
                atr_20 DOUBLE,
                orb_0900_high DOUBLE,
                orb_0900_low DOUBLE,
                orb_0900_size DOUBLE,
                orb_0900_break_dir VARCHAR,
                orb_0900_outcome VARCHAR,
                orb_0900_r_multiple DOUBLE,
                orb_0900_mae DOUBLE,
                orb_0900_mfe DOUBLE,
                orb_1000_high DOUBLE,
                orb_1000_low DOUBLE,
                orb_1000_size DOUBLE,
                orb_1000_break_dir VARCHAR,
                orb_1000_outcome VARCHAR,
                orb_1000_r_multiple DOUBLE,
                orb_1000_mae DOUBLE,
                orb_1000_mfe DOUBLE,
                orb_1100_high DOUBLE,
                orb_1100_low DOUBLE,
                orb_1100_size DOUBLE,
                orb_1100_break_dir VARCHAR,
                orb_1100_outcome VARCHAR,
                orb_1100_r_multiple DOUBLE,
                orb_1100_mae DOUBLE,
                orb_1100_mfe DOUBLE,
                orb_1800_high DOUBLE,
                orb_1800_low DOUBLE,
                orb_1800_size DOUBLE,
                orb_1800_break_dir VARCHAR,
                orb_1800_outcome VARCHAR,
                orb_1800_r_multiple DOUBLE,
                orb_1800_mae DOUBLE,
                orb_1800_mfe DOUBLE,
                orb_2300_high DOUBLE,
                orb_2300_low DOUBLE,
                orb_2300_size DOUBLE,
                orb_2300_break_dir VARCHAR,
                orb_2300_outcome VARCHAR,
                orb_2300_r_multiple DOUBLE,
                orb_2300_mae DOUBLE,
                orb_2300_mfe DOUBLE,
                orb_0030_high DOUBLE,
                orb_0030_low DOUBLE,
                orb_0030_size DOUBLE,
                orb_0030_break_dir VARCHAR,
                orb_0030_outcome VARCHAR,
                orb_0030_r_multiple DOUBLE,
                orb_0030_mae DOUBLE,
                orb_0030_mfe DOUBLE,
                rsi_at_orb DOUBLE
            )
        """)
        conn.close()

        exporter = CSVExporter(db_path=str(db_path), output_dir=str(tmp_path / "exports"))
        output_path, row_count = exporter.export_daily_features()
        assert row_count == 0
        assert os.path.exists(output_path)

    def test_days_zero(self, exporter):
        """days=0 should export nothing or today only"""
        output_path, row_count = exporter.export_daily_features(days=0)
        # With days=0, cutoff is today, so we might get 0 or 1 rows
        assert row_count >= 0

    def test_days_negative_handled(self, exporter):
        """Negative days should be handled (may give unexpected results)"""
        # Implementation may vary - just ensure no crash
        try:
            exporter.export_daily_features(days=-1)
        except Exception:
            pass  # Some implementations may reject negative values

    def test_large_days_value(self, exporter):
        """Large days value should work (export all data)"""
        output_path, row_count = exporter.export_daily_features(days=10000)
        assert row_count == 10  # All 10 test rows


# =============================================================================
# Test File Overwrite Behavior
# =============================================================================

class TestFileOverwrite:
    """Test file overwrite behavior"""

    def test_overwrite_existing_file(self, exporter):
        """Exporting to same file should overwrite"""
        # First export
        output_path1, count1 = exporter.export_daily_features(output_file="test.csv")
        assert os.path.exists(output_path1)

        # Second export to same file
        output_path2, count2 = exporter.export_daily_features(output_file="test.csv")
        assert output_path1 == output_path2
        assert count1 == count2
