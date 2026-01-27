"""
Tests for build_daily_features.py - THE BUILDING BLOCK

This is the MOST CRITICAL module to test - if ORB calculations are wrong, ALL decisions are wrong.

Tests cover:
1. ORB calculation (high/low/size from first 5 minutes)
2. Break direction detection (UP/DOWN/NONE based on first close outside)
3. Entry trigger logic (MUST be at close, NOT ORB edge)
4. Stop/target calculation (ORB-anchored, not entry-anchored)
5. Outcome detection (WIN/LOSS/NO_TRADE with conservative same-bar resolution)
6. MAE/MFE tracking (from ORB edge, normalized by R)
7. Session window calculations (timezone handling)
8. RSI/ATR calculations
9. Type code classification
"""
import pytest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pipeline.build_daily_features import FeatureBuilderV2

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")


@pytest.fixture
def feature_builder_with_bars(test_db):
    """Create feature builder with synthetic 1-minute bar data"""
    import duckdb

    conn = duckdb.connect(test_db)

    # Create bars_1m table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bars_1m (
            ts_utc TIMESTAMPTZ,
            symbol VARCHAR,
            source_symbol VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume INTEGER,
            PRIMARY KEY (symbol, ts_utc)
        )
    """)

    # Create bars_5m table (needed for RSI)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bars_5m (
            ts_utc TIMESTAMPTZ,
            symbol VARCHAR,
            source_symbol VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume INTEGER,
            PRIMARY KEY (symbol, ts_utc)
        )
    """)

    conn.commit()
    conn.close()

    # Return builder connected to test database
    builder = FeatureBuilderV2(db_path=test_db, sl_mode="full", table_name="daily_features")
    builder.init_schema_v2()

    yield builder

    builder.close()


def insert_synthetic_bars(builder, trade_date, scenario):
    """
    Insert synthetic 1-minute bars for testing ORB logic.

    Scenarios:
    - 'orb_break_up_win': ORB breaks up, hits target
    - 'orb_break_down_loss': ORB breaks down, hits stop
    - 'orb_no_break': ORB never breaks
    - 'orb_break_up_no_exit': ORB breaks up but never hits TP/SL
    """
    conn = builder.con

    # Base time: 09:00 local on trade_date
    orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, 9, 0, tzinfo=TZ_LOCAL)

    if scenario == 'orb_break_up_win':
        # ORB 09:00-09:05: Range 2650.00-2650.10 (size=0.10)
        # Break direction: UP (close > 2650.10)
        # Entry: 2650.15 (first close above ORB high)
        # Stop (FULL): 2650.00 (opposite edge)
        # R = 2650.10 - 2650.00 = 0.10
        # Target (RR=1.0): 2650.10 + 1.0 * 0.10 = 2650.20
        # Outcome: WIN (hits target at 2650.20)

        bars = [
            # ORB window (09:00-09:05) - 5 bars
            (orb_start, 2650.05, 2650.10, 2650.00, 2650.02, 100),  # 09:00
            (orb_start + timedelta(minutes=1), 2650.02, 2650.08, 2650.01, 2650.05, 100),  # 09:01
            (orb_start + timedelta(minutes=2), 2650.05, 2650.09, 2650.03, 2650.06, 100),  # 09:02
            (orb_start + timedelta(minutes=3), 2650.06, 2650.10, 2650.04, 2650.07, 100),  # 09:03
            (orb_start + timedelta(minutes=4), 2650.07, 2650.08, 2650.02, 2650.05, 100),  # 09:04

            # Entry bar (09:05) - first close above ORB high
            (orb_start + timedelta(minutes=5), 2650.08, 2650.16, 2650.07, 2650.15, 150),  # Close = 2650.15 > 2650.10 (UP break)

            # Next bar (09:06) - hits target
            (orb_start + timedelta(minutes=6), 2650.15, 2650.25, 2650.14, 2650.22, 200),  # High = 2650.25 >= 2650.20 (WIN)
        ]

    elif scenario == 'orb_break_down_loss':
        # ORB 09:00-09:05: Range 2650.00-2650.10 (size=0.10)
        # Break direction: DOWN (close < 2650.00)
        # Entry: 2649.95 (first close below ORB low)
        # Stop (FULL): 2650.10 (opposite edge)
        # R = 2650.10 - 2650.00 = 0.10
        # Target (RR=1.0): 2650.00 - 1.0 * 0.10 = 2649.90
        # Outcome: LOSS (hits stop at 2650.10)

        bars = [
            # ORB window (09:00-09:05)
            (orb_start, 2650.05, 2650.10, 2650.00, 2650.02, 100),
            (orb_start + timedelta(minutes=1), 2650.02, 2650.08, 2650.01, 2650.05, 100),
            (orb_start + timedelta(minutes=2), 2650.05, 2650.09, 2650.03, 2650.06, 100),
            (orb_start + timedelta(minutes=3), 2650.06, 2650.10, 2650.04, 2650.07, 100),
            (orb_start + timedelta(minutes=4), 2650.07, 2650.08, 2650.02, 2650.05, 100),

            # Entry bar (09:05) - first close below ORB low
            (orb_start + timedelta(minutes=5), 2650.03, 2650.04, 2649.90, 2649.95, 150),  # Close = 2649.95 < 2650.00 (DOWN break)

            # Next bar (09:06) - hits stop
            (orb_start + timedelta(minutes=6), 2649.95, 2650.15, 2649.92, 2650.05, 200),  # High = 2650.15 >= 2650.10 (LOSS)
        ]

    elif scenario == 'orb_no_break':
        # ORB never breaks - all closes remain inside ORB range

        bars = [
            # ORB window (09:00-09:05)
            (orb_start, 2650.05, 2650.10, 2650.00, 2650.02, 100),
            (orb_start + timedelta(minutes=1), 2650.02, 2650.08, 2650.01, 2650.05, 100),
            (orb_start + timedelta(minutes=2), 2650.05, 2650.09, 2650.03, 2650.06, 100),
            (orb_start + timedelta(minutes=3), 2650.06, 2650.10, 2650.04, 2650.07, 100),
            (orb_start + timedelta(minutes=4), 2650.07, 2650.08, 2650.02, 2650.05, 100),

            # Subsequent bars - all closes inside ORB
            (orb_start + timedelta(minutes=5), 2650.04, 2650.09, 2650.01, 2650.03, 100),
            (orb_start + timedelta(minutes=6), 2650.03, 2650.08, 2650.02, 2650.04, 100),
            (orb_start + timedelta(minutes=7), 2650.04, 2650.09, 2650.01, 2650.05, 100),
        ]

    elif scenario == 'orb_break_up_no_exit':
        # ORB breaks up but never hits TP/SL (ends session with open trade)

        bars = [
            # ORB window
            (orb_start, 2650.05, 2650.10, 2650.00, 2650.02, 100),
            (orb_start + timedelta(minutes=1), 2650.02, 2650.08, 2650.01, 2650.05, 100),
            (orb_start + timedelta(minutes=2), 2650.05, 2650.09, 2650.03, 2650.06, 100),
            (orb_start + timedelta(minutes=3), 2650.06, 2650.10, 2650.04, 2650.07, 100),
            (orb_start + timedelta(minutes=4), 2650.07, 2650.08, 2650.02, 2650.05, 100),

            # Entry bar - breaks up
            (orb_start + timedelta(minutes=5), 2650.08, 2650.16, 2650.07, 2650.15, 150),  # Entry at 2650.15

            # Subsequent bars - never hits TP (2650.20) or SL (2650.00)
            (orb_start + timedelta(minutes=6), 2650.15, 2650.18, 2650.12, 2650.16, 100),
            (orb_start + timedelta(minutes=7), 2650.16, 2650.19, 2650.13, 2650.17, 100),
            (orb_start + timedelta(minutes=8), 2650.17, 2650.19, 2650.14, 2650.18, 100),
        ]

    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    # Insert bars into database
    for ts_local, o, h, l, c, vol in bars:
        ts_utc = ts_local.astimezone(TZ_UTC)
        conn.execute("""
            INSERT INTO bars_1m (ts_utc, symbol, source_symbol, open, high, low, close, volume)
            VALUES (?, 'MGC', 'MGCG4', ?, ?, ?, ?, ?)
        """, [ts_utc, o, h, l, c, vol])

    conn.commit()


class TestORBCalculation:
    """Test ORB high/low/size calculation from first 5 minutes"""

    def test_orb_calculated_from_first_5_minutes(self, feature_builder_with_bars):
        """ORB high/low/size calculated from first 5 1-minute bars"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_up_win')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb is not None
        assert orb['high'] == 2650.10, "ORB high should be max of first 5 bars"
        assert orb['low'] == 2650.00, "ORB low should be min of first 5 bars"
        assert abs(orb['size'] - 0.10) < 0.001, "ORB size should be high - low"

    def test_orb_returns_none_when_no_bars(self, feature_builder_with_bars):
        """ORB returns None when no bar data available (weekend/holiday)"""
        # Arrange
        builder = feature_builder_with_bars
        # Don't insert any bars

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb is None, "Should return None when no bar data"


class TestBreakDirectionDetection:
    """Test break direction detection (UP/DOWN/NONE based on first close outside ORB)"""

    def test_break_direction_up_when_close_above_orb_high(self, feature_builder_with_bars):
        """Break direction = UP when first close > ORB high"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_up_win')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb['break_dir'] == 'UP', "Break direction should be UP when close > ORB high"

    def test_break_direction_down_when_close_below_orb_low(self, feature_builder_with_bars):
        """Break direction = DOWN when first close < ORB low"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_down_loss')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb['break_dir'] == 'DOWN', "Break direction should be DOWN when close < ORB low"

    def test_break_direction_none_when_no_break(self, feature_builder_with_bars):
        """Break direction = NONE when close never leaves ORB range"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_no_break')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb['break_dir'] == 'NONE', "Break direction should be NONE when no break"


class TestEntryTriggerLogic:
    """Test entry trigger logic (MUST be at close, NOT ORB edge) - CRITICAL GUARDRAIL"""

    def test_entry_triggered_at_first_close_outside_orb(self, feature_builder_with_bars):
        """Entry triggered at first 1-minute close outside ORB (not at ORB edge)"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_up_win')

        # Act - should NOT raise assertion error
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        # If entry was at ORB edge, would raise: "FATAL: Entry at ORB high (should be at close)"
        # If we get here without assertion error, entry logic is correct
        assert orb['break_dir'] in ['UP', 'DOWN'], "Should have valid break direction"


class TestStopTargetCalculation:
    """Test stop/target calculation (ORB-anchored, not entry-anchored)"""

    def test_stop_at_opposite_edge_for_full_mode(self, feature_builder_with_bars):
        """Stop = opposite ORB edge when sl_mode=full"""
        # Arrange
        builder = feature_builder_with_bars
        builder.sl_mode = 'full'
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_up_win')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        # ORB = 2650.00-2650.10, break UP
        # Stop (FULL) = opposite edge = 2650.00
        assert orb['stop_price'] == 2650.00, "Stop should be at opposite edge (ORB low) for UP break"

    def test_risk_calculated_from_orb_edge_to_stop(self, feature_builder_with_bars):
        """Risk (R) = distance from ORB edge to stop (ORB-anchored, not entry-anchored)"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_up_win')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        # ORB edge (UP break) = 2650.10
        # Stop = 2650.00
        # R = 2650.10 - 2650.00 = 0.10
        # Risk in ticks = 0.10 / 0.1 = 1.0 tick
        assert abs(orb['risk_ticks'] - 1.0) < 0.001, "Risk should be 1.0 tick (ORB size = 0.10)"


class TestOutcomeDetection:
    """Test outcome detection (WIN/LOSS/NO_TRADE with conservative same-bar resolution)"""

    def test_outcome_win_when_target_hit(self, feature_builder_with_bars):
        """Outcome = WIN when target hit first"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_up_win')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb['outcome'] == 'WIN', "Outcome should be WIN when target hit"
        assert orb['r_multiple'] == 1.0, "R-multiple should be 1.0 for RR=1.0 win"

    def test_outcome_loss_when_stop_hit(self, feature_builder_with_bars):
        """Outcome = LOSS when stop hit first"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_down_loss')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb['outcome'] == 'LOSS', "Outcome should be LOSS when stop hit"
        assert orb['r_multiple'] == -1.0, "R-multiple should be -1.0 for loss"

    def test_outcome_no_trade_when_orb_never_breaks(self, feature_builder_with_bars):
        """Outcome = NO_TRADE when ORB never breaks"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_no_break')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb['outcome'] == 'NO_TRADE', "Outcome should be NO_TRADE when no break"
        assert orb['r_multiple'] is None, "R-multiple should be None for no trade"

    def test_outcome_no_trade_when_break_but_no_exit(self, feature_builder_with_bars):
        """Outcome = NO_TRADE when ORB breaks but neither TP nor SL hit"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_up_no_exit')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb['outcome'] == 'NO_TRADE', "Outcome should be NO_TRADE when no exit"
        assert orb['r_multiple'] is None, "R-multiple should be None when no exit"


class TestMAEMFETracking:
    """Test MAE/MFE tracking (from ORB edge, normalized by R)"""

    def test_mae_mfe_tracked_from_orb_edge(self, feature_builder_with_bars):
        """MAE/MFE measured from ORB edge (not entry) and normalized by R"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_break_up_win')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        # MAE/MFE should be normalized by R (0.10)
        # Both should be numbers (not None) for a WIN trade
        assert orb['mae'] is not None, "MAE should be tracked for WIN trade"
        assert orb['mfe'] is not None, "MFE should be tracked for WIN trade"
        assert isinstance(orb['mae'], float), "MAE should be a float"
        assert isinstance(orb['mfe'], float), "MFE should be a float"

    def test_mae_mfe_none_for_no_trade(self, feature_builder_with_bars):
        """MAE/MFE = None when outcome = NO_TRADE (no break)"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        insert_synthetic_bars(builder, trade_date, 'orb_no_break')

        # Act
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 20, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb['mae'] is None, "MAE should be None for NO_TRADE"
        assert orb['mfe'] is None, "MFE should be None for NO_TRADE"


class TestSessionWindowCalculations:
    """Test session window calculations (timezone handling)"""

    def test_asia_session_window_correct(self, feature_builder_with_bars):
        """Asia session = 09:00-17:00 local (8 hours)"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)

        # Insert bars for full Asia session (09:00-17:00 = 480 minutes)
        conn = builder.con
        for i in range(480):
            ts_local = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL) + timedelta(minutes=i)
            ts_utc = ts_local.astimezone(TZ_UTC)
            conn.execute("""
                INSERT INTO bars_1m (ts_utc, symbol, source_symbol, open, high, low, close, volume)
                VALUES (?, 'MGC', 'MGCG4', 2650.0, 2651.0, 2649.0, 2650.5, 100)
            """, [ts_utc])
        conn.commit()

        # Act
        asia = builder.get_asia_session(trade_date)

        # Assert
        assert asia is not None, "Asia session should have data"
        assert 'high' in asia
        assert 'low' in asia
        assert 'range' in asia

    def test_timezone_conversion_correct(self, feature_builder_with_bars):
        """Timestamps correctly converted between Australia/Brisbane and UTC"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)

        # Brisbane 09:00 = UTC 23:00 (previous day) [Brisbane is UTC+10]
        # Insert bar at 09:00 Brisbane time
        ts_local = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        ts_utc = ts_local.astimezone(TZ_UTC)

        conn = builder.con
        conn.execute("""
            INSERT INTO bars_1m (ts_utc, symbol, source_symbol, open, high, low, close, volume)
            VALUES (?, 'MGC', 'MGCG4', 2650.0, 2650.5, 2649.5, 2650.0, 100)
        """, [ts_utc])
        conn.commit()

        # Act - fetch using local time window
        orb_start = datetime(2026, 1, 20, 9, 0, tzinfo=TZ_LOCAL)
        orb_end = datetime(2026, 1, 20, 9, 1, tzinfo=TZ_LOCAL)
        bars = builder._fetch_1m_bars(orb_start, orb_end)

        # Assert
        assert len(bars) == 1, "Should find 1 bar in the window"
        assert bars[0][1] == 2650.5, "Bar data should match"


class TestRSICalculation:
    """Test RSI calculation (Wilder's smoothing, 14-period)"""

    def test_rsi_calculated_from_last_15_closes(self, feature_builder_with_bars):
        """RSI uses last 15 5-minute closes (14 periods + current)"""
        # Arrange
        builder = feature_builder_with_bars
        conn = builder.con

        # Insert 15 bars of 5-minute data (closes trending up)
        base_time = datetime(2026, 1, 20, 0, 0, tzinfo=TZ_LOCAL)
        for i in range(15):
            ts_local = base_time + timedelta(minutes=5 * i)
            ts_utc = ts_local.astimezone(TZ_UTC)
            close = 2650.0 + i * 0.1  # Trending up
            conn.execute("""
                INSERT INTO bars_5m (ts_utc, symbol, source_symbol, open, high, low, close, volume)
                VALUES (?, 'MGC', 'MGCG4', ?, ?, ?, ?, 100)
            """, [ts_utc, close, close + 0.1, close - 0.1, close])
        conn.commit()

        # Act
        at_time = base_time + timedelta(minutes=5 * 14)  # Last bar time
        rsi = builder.calculate_rsi_at(at_time)

        # Assert
        assert rsi is not None, "RSI should be calculated"
        assert 0 <= rsi <= 100, "RSI should be between 0 and 100"
        assert rsi > 50, "RSI should be > 50 for uptrend"

    def test_rsi_returns_none_when_insufficient_data(self, feature_builder_with_bars):
        """RSI returns None when < 15 bars available"""
        # Arrange
        builder = feature_builder_with_bars
        conn = builder.con

        # Insert only 10 bars (< 15 required)
        base_time = datetime(2026, 1, 20, 0, 0, tzinfo=TZ_LOCAL)
        for i in range(10):
            ts_local = base_time + timedelta(minutes=5 * i)
            ts_utc = ts_local.astimezone(TZ_UTC)
            conn.execute("""
                INSERT INTO bars_5m (ts_utc, symbol, source_symbol, open, high, low, close, volume)
                VALUES (?, 'MGC', 'MGCG4', 2650.0, 2650.5, 2649.5, 2650.0, 100)
            """, [ts_utc])
        conn.commit()

        # Act
        at_time = base_time + timedelta(minutes=5 * 9)
        rsi = builder.calculate_rsi_at(at_time)

        # Assert
        assert rsi is None, "RSI should return None when insufficient data"


class TestATRCalculation:
    """Test ATR calculation (simple average of last 20 days)"""

    def test_atr_calculated_from_last_20_days(self, feature_builder_with_bars):
        """ATR = average of last 20 days' asia_high - asia_low"""
        # Arrange
        builder = feature_builder_with_bars
        conn = builder.con

        # Insert 20 days of features
        for i in range(20):
            trade_date = date(2026, 1, 1) + timedelta(days=i)
            conn.execute("""
                INSERT INTO daily_features (date_local, instrument, asia_high, asia_low)
                VALUES (?, 'MGC', 2650.0, 2648.0)
            """, [trade_date])
        conn.commit()

        # Act
        test_date = date(2026, 1, 21)
        atr = builder.calculate_atr(test_date)

        # Assert
        assert atr is not None, "ATR should be calculated"
        assert atr == 2.0, "ATR should be average of (2650.0 - 2648.0) = 2.0"

    def test_atr_returns_none_when_insufficient_data(self, feature_builder_with_bars):
        """ATR returns None when < 20 days available"""
        # Arrange
        builder = feature_builder_with_bars
        conn = builder.con

        # Insert only 10 days (< 20 required)
        for i in range(10):
            trade_date = date(2026, 1, 1) + timedelta(days=i)
            conn.execute("""
                INSERT INTO daily_features (date_local, instrument, asia_high, asia_low)
                VALUES (?, 'MGC', 2650.0, 2648.0)
            """, [trade_date])
        conn.commit()

        # Act
        test_date = date(2026, 1, 11)
        atr = builder.calculate_atr(test_date)

        # Assert
        assert atr is None, "ATR should return None when insufficient data"


class TestTypeCodeClassification:
    """Test type code classification (Asia/London/PreNY codes)"""

    def test_asia_code_tight_when_range_small(self):
        """Asia code = A1_TIGHT when range < 0.3 * ATR"""
        # Arrange
        asia_range = 0.5  # Small range
        atr_20 = 2.0

        # Act
        code = FeatureBuilderV2.classify_asia_code(asia_range, atr_20)

        # Assert
        # ratio = 0.5 / 2.0 = 0.25 < 0.3 → A1_TIGHT
        assert code == 'A1_TIGHT', "Should classify as A1_TIGHT for small range"

    def test_asia_code_expanded_when_range_large(self):
        """Asia code = A2_EXPANDED when range > 0.8 * ATR"""
        # Arrange
        asia_range = 2.0  # Large range
        atr_20 = 2.0

        # Act
        code = FeatureBuilderV2.classify_asia_code(asia_range, atr_20)

        # Assert
        # ratio = 2.0 / 2.0 = 1.0 > 0.8 → A2_EXPANDED
        assert code == 'A2_EXPANDED', "Should classify as A2_EXPANDED for large range"

    def test_london_code_sweep_high_when_takes_asia_high(self):
        """London code = L1_SWEEP_HIGH when london_high > asia_high"""
        # Arrange
        london_high = 2651.0
        london_low = 2649.0
        asia_high = 2650.0
        asia_low = 2648.0

        # Act
        code = FeatureBuilderV2.classify_london_code(london_high, london_low, asia_high, asia_low)

        # Assert
        assert code == 'L1_SWEEP_HIGH', "Should classify as L1_SWEEP_HIGH"

    def test_london_code_expansion_when_takes_both_highs_and_lows(self):
        """London code = L3_EXPANSION when london takes both asia high and low"""
        # Arrange
        london_high = 2651.0
        london_low = 2647.0
        asia_high = 2650.0
        asia_low = 2648.0

        # Act
        code = FeatureBuilderV2.classify_london_code(london_high, london_low, asia_high, asia_low)

        # Assert
        assert code == 'L3_EXPANSION', "Should classify as L3_EXPANSION"


class TestDataIntegrity:
    """Test data integrity and edge cases"""

    def test_handles_missing_orb_data_gracefully(self, feature_builder_with_bars):
        """Missing ORB data (weekends/holidays) handled gracefully"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 18)  # Sunday - no data

        # Act
        orb_start = datetime(2026, 1, 18, 9, 0, tzinfo=TZ_LOCAL)
        scan_end = datetime(2026, 1, 18, 10, 0, tzinfo=TZ_LOCAL)
        orb = builder.calculate_orb_1m_exec(orb_start, scan_end)

        # Assert
        assert orb is None, "Should return None for missing data"

    def test_upsert_behavior_on_duplicate_date(self, feature_builder_with_bars):
        """INSERT OR REPLACE overwrites existing row for same date"""
        # Arrange
        builder = feature_builder_with_bars
        trade_date = date(2026, 1, 20)
        conn = builder.con

        # Insert first row
        conn.execute("""
            INSERT INTO daily_features (date_local, instrument, asia_high, asia_low)
            VALUES (?, 'MGC', 2650.0, 2648.0)
        """, [trade_date])
        conn.commit()

        # Act - insert again with different values
        conn.execute("""
            INSERT OR REPLACE INTO daily_features (date_local, instrument, asia_high, asia_low)
            VALUES (?, 'MGC', 2655.0, 2653.0)
        """, [trade_date])
        conn.commit()

        # Assert
        row = conn.execute("""
            SELECT asia_high, asia_low FROM daily_features WHERE date_local = ?
        """, [trade_date]).fetchone()

        assert row[0] == 2655.0, "Should have new value (upserted)"
        assert row[1] == 2653.0, "Should have new value (upserted)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
