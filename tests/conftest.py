"""
Pytest configuration and shared fixtures for testing framework.

This file provides reusable test fixtures for all test modules.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# Add project root and trading_app to Python path
PROJECT_ROOT = Path(__file__).parent.parent
TRADING_APP_PATH = PROJECT_ROOT / "trading_app"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TRADING_APP_PATH))

# Import trading app modules
from strategy_engine import StrategyEngine, StrategyEvaluation, ActionType, StrategyState
from setup_detector import SetupDetector
from data_loader import LiveDataLoader
import config


@pytest.fixture
def local_tz():
    """Brisbane timezone for all tests."""
    return pytz.timezone(config.TZ_LOCAL)


@pytest.fixture
def sample_date():
    """Sample trading date for tests."""
    return datetime(2025, 1, 15, tzinfo=pytz.UTC)


@pytest.fixture
def sample_orb_2300():
    """Sample 2300 ORB that passes filter (S+ tier setup)."""
    return {
        "orb_time": "2300",
        "orb_high": 2687.50,
        "orb_low": 2685.00,
        "orb_size": 2.50,
        "atr_20": 16.0,
        "filter_threshold": 0.155,  # 2.50 / 16.0 = 0.156 > 0.155 (FAILS by default, use 0.150 to pass)
        "current_price": 2688.00,
        "sl_mode": "HALF",
        "rr": 1.5,
        "expected_tier": "S+",
        "expected_win_rate": 56.1,
        "expected_avg_r": 0.403,
    }


@pytest.fixture
def sample_orb_2300_passing():
    """Sample 2300 ORB that PASSES filter."""
    return {
        "orb_time": "2300",
        "orb_high": 2687.50,
        "orb_low": 2685.00,
        "orb_size": 2.50,
        "atr_20": 17.0,  # Higher ATR so ratio passes: 2.50/17.0 = 0.147 < 0.155
        "filter_threshold": 0.155,
        "current_price": 2688.00,
        "sl_mode": "HALF",
        "rr": 1.5,
        "expected_tier": "S+",
        "expected_win_rate": 56.1,
        "expected_avg_r": 0.403,
    }


@pytest.fixture
def sample_orb_1000():
    """Sample 1000 ORB (Crown Jewel - S+ tier, no filter)."""
    return {
        "orb_time": "1000",
        "orb_high": 2687.50,
        "orb_low": 2685.00,
        "orb_size": 2.50,
        "atr_20": 16.0,
        "filter_threshold": None,  # No filter on day ORBs
        "current_price": 2688.00,
        "sl_mode": "FULL",
        "rr": 8.0,
        "expected_tier": "S+",
        "expected_win_rate": 15.3,
        "expected_avg_r": 0.378,
    }


@pytest.fixture
def sample_orb_0900():
    """Sample 0900 ORB (A tier, no filter)."""
    return {
        "orb_time": "0900",
        "orb_high": 2687.50,
        "orb_low": 2685.00,
        "orb_size": 2.50,
        "atr_20": 16.0,
        "filter_threshold": None,
        "current_price": 2688.00,
        "sl_mode": "FULL",
        "rr": 6.0,
        "expected_tier": "A",
        "expected_win_rate": 17.1,
        "expected_avg_r": 0.198,
    }


@pytest.fixture
def sample_orb_0030():
    """Sample 0030 ORB (S tier with filter)."""
    return {
        "orb_time": "0030",
        "orb_high": 2687.50,
        "orb_low": 2685.00,
        "orb_size": 2.50,
        "atr_20": 23.0,  # 2.50/23.0 = 0.109 < 0.112 (PASSES)
        "filter_threshold": 0.112,
        "current_price": 2688.00,
        "sl_mode": "HALF",
        "rr": 3.0,
        "expected_tier": "S",
        "expected_win_rate": 31.3,
        "expected_avg_r": 0.254,
    }


@pytest.fixture
def sample_cascade_setup():
    """Sample multi-liquidity cascade setup."""
    return {
        "asia_high": 2690.00,
        "asia_low": 2680.00,
        "london_high": 2695.00,  # Gap up: 2695 - 2690 = 5.0 pts (fails 9.5 requirement)
        "london_low": 2688.00,
        "ny_high": 2705.00,  # Gap up: 2705 - 2695 = 10.0 pts (PASSES 9.5 requirement)
        "ny_low": 2700.00,
        "current_price": 2694.00,  # Close back inside London range (acceptance failure)
        "expected_cascade": True,
        "expected_gaps": [10.0],  # Only NY gap qualifies
    }


@pytest.fixture
def mock_validated_setup_2300():
    """Mock validated_setups row for 2300 ORB."""
    return {
        "setup_id": "MGC_2300_HALF_1.5_0C_0B",
        "instrument": "MGC",
        "orb_time": "2300",
        "rr": 1.5,
        "sl_mode": "HALF",
        "close_confirmations": 0,
        "buffer_ticks": 0,
        "orb_size_filter": 0.155,
        "atr_filter": None,
        "trades": 262,
        "win_rate": 56.1,
        "avg_r": 0.403,
        "annual_trades": 260,
        "tier": "S+",
        "notes": "Best overall setup - high win rate, excellent expectancy",
        "source_table": "orb_trades_1m_exec",
    }


@pytest.fixture
def mock_validated_setup_1000():
    """Mock validated_setups row for 1000 ORB."""
    return {
        "setup_id": "MGC_1000_FULL_8.0_0C_0B",
        "instrument": "MGC",
        "orb_time": "1000",
        "rr": 8.0,
        "sl_mode": "FULL",
        "close_confirmations": 0,
        "buffer_ticks": 0,
        "orb_size_filter": None,
        "atr_filter": None,
        "trades": 262,
        "win_rate": 15.3,
        "avg_r": 0.378,
        "annual_trades": 260,
        "tier": "S+",
        "notes": "Crown jewel - massive RR, best expectancy per trade",
        "source_table": "orb_trades_1m_exec",
    }


@pytest.fixture
def mock_strategy_evaluation_enter():
    """Mock StrategyEvaluation with ENTER action."""
    return StrategyEvaluation(
        strategy_name="NIGHT_ORB",
        priority=2,
        state=StrategyState.READY,
        action=ActionType.ENTER,
        reasons=[
            "2300 ORB formed (High: $2,687.50, Low: $2,685.00, Size: 2.50 pts)",
            "ORB size filter PASSED (2.50 pts / 17.0 ATR = 0.147 < 0.155 threshold)",
            "First close outside ORB detected (Close: $2,688.00 > High: $2,687.50)",
            "S+ tier setup (56.1% win rate, +105R/year expectancy)",
        ],
        next_instruction="Enter long at $2,688.00, stop at $2,686.25 (ORB midpoint), target at $2,690.63 (1.5R)",
        entry_price=2688.00,
        stop_price=2686.25,  # Midpoint (HALF mode)
        target_price=2690.625,  # Entry + (Stop × 1.5 RR)
        risk_pct=1.0,
        setup_name="2300 ORB HALF",
        setup_tier="S+",
        orb_high=2687.50,
        orb_low=2685.00,
        direction="LONG",
        position_size=2,
        rr=1.5,
        win_rate=56.1,
        avg_r=0.403,
        annual_trades=260,
    )


@pytest.fixture
def mock_strategy_evaluation_stand_down():
    """Mock StrategyEvaluation with STAND_DOWN action."""
    return StrategyEvaluation(
        strategy_name="NIGHT_ORB",
        priority=2,
        state=StrategyState.INVALID,
        action=ActionType.STAND_DOWN,
        reasons=[
            "2300 ORB formed (High: $2,687.50, Low: $2,685.00, Size: 2.50 pts)",
            "ORB size filter FAILED (2.50 pts / 16.0 ATR = 0.156 > 0.155 threshold)",
            "ORB too large relative to ATR - setup has poor historical performance",
        ],
        next_instruction="Wait for next ORB or better setup (current ORB failed size filter)",
        entry_price=None,
        stop_price=None,
        target_price=None,
        risk_pct=None,
        setup_name="2300 ORB HALF",
        setup_tier=None,
        orb_high=2687.50,
        orb_low=2685.00,
        direction=None,
        position_size=None,
        rr=None,
        win_rate=None,
        avg_r=None,
        annual_trades=None,
    )


@pytest.fixture
def setup_detector():
    """Create SetupDetector instance."""
    return SetupDetector(instrument="MGC")


@pytest.fixture
def config_mgc_orb_2300():
    """MGC 2300 ORB config from config.py."""
    return {
        "rr": 1.5,
        "sl_mode": "HALF",
        "orb_size_filter": 0.155,
    }


@pytest.fixture
def config_mgc_orb_1000():
    """MGC 1000 ORB config from config.py."""
    return {
        "rr": 8.0,
        "sl_mode": "FULL",
        "orb_size_filter": None,
    }


# Test database connection (for integration tests)
@pytest.fixture(scope="session")
def test_db_path():
    """Path to test database (uses production database for now)."""
    return config.DUCKDB_PATH


# ==============================================================================
# NEW FIXTURES FOR TRADING APP TESTS
# ==============================================================================

import duckdb
from datetime import date, timedelta


@pytest.fixture
def test_db(tmp_path):
    """Temporary DuckDB test database with schema"""
    # Use temporary file so multiple connections share the same database
    db_file = tmp_path / "test.db"
    conn = duckdb.connect(str(db_file))

    # Create daily_features table
    conn.execute("""
        CREATE TABLE daily_features (
            date_local DATE,
            instrument VARCHAR,
            asia_high DOUBLE,
            asia_low DOUBLE,
            london_high DOUBLE,
            london_low DOUBLE,
            ny_high DOUBLE,
            ny_low DOUBLE,
            orb_0900_high DOUBLE,
            orb_0900_low DOUBLE,
            orb_0900_size DOUBLE,
            orb_0900_break_dir VARCHAR,
            orb_0900_outcome VARCHAR,
            orb_0900_r_multiple DOUBLE,
            orb_1000_high DOUBLE,
            orb_1000_low DOUBLE,
            orb_1000_size DOUBLE,
            orb_1000_break_dir VARCHAR,
            orb_1000_outcome VARCHAR,
            orb_1000_r_multiple DOUBLE,
            orb_1100_high DOUBLE,
            orb_1100_low DOUBLE,
            orb_1100_size DOUBLE,
            orb_1100_break_dir VARCHAR,
            orb_1100_outcome VARCHAR,
            orb_1100_r_multiple DOUBLE,
            orb_1800_high DOUBLE,
            orb_1800_low DOUBLE,
            orb_1800_size DOUBLE,
            orb_1800_break_dir VARCHAR,
            orb_1800_outcome VARCHAR,
            orb_1800_r_multiple DOUBLE,
            orb_2300_high DOUBLE,
            orb_2300_low DOUBLE,
            orb_2300_size DOUBLE,
            orb_2300_break_dir VARCHAR,
            orb_2300_outcome VARCHAR,
            orb_2300_r_multiple DOUBLE,
            orb_0030_high DOUBLE,
            orb_0030_low DOUBLE,
            orb_0030_size DOUBLE,
            orb_0030_break_dir VARCHAR,
            orb_0030_outcome VARCHAR,
            orb_0030_r_multiple DOUBLE,
            PRIMARY KEY (date_local, instrument)
        )
    """)

    # Create validated_setups table
    conn.execute("""
        CREATE TABLE validated_setups (
            instrument VARCHAR,
            orb_time VARCHAR,
            rr DOUBLE,
            sl_mode VARCHAR,
            orb_size_filter DOUBLE,
            win_rate DOUBLE,
            expected_r DOUBLE,
            sample_size INTEGER,
            PRIMARY KEY (instrument, orb_time)
        )
    """)

    # Create trade_journal table
    conn.execute("""
        CREATE SEQUENCE trade_journal_id_seq;
        CREATE TABLE trade_journal (
            id INTEGER PRIMARY KEY DEFAULT nextval('trade_journal_id_seq'),
            date_local DATE,
            orb_time VARCHAR,
            instrument VARCHAR,
            outcome VARCHAR,
            r_multiple DOUBLE,
            entry_price DOUBLE,
            exit_price DOUBLE,
            mae DOUBLE,
            mfe DOUBLE,
            asia_travel DOUBLE,
            london_reversals INTEGER,
            pre_orb_travel DOUBLE,
            liquidity_state VARCHAR DEFAULT 'normal',
            session_context VARCHAR,
            lesson_learned VARCHAR,
            notable BOOLEAN DEFAULT FALSE
        )
    """)

    # Create learned_patterns table
    conn.execute("""
        CREATE TABLE learned_patterns (
            id INTEGER PRIMARY KEY,
            pattern_name VARCHAR,
            confidence DOUBLE,
            discovered_at TIMESTAMP
        )
    """)

    conn.close()
    yield str(db_file)


@pytest.fixture
def sample_market_data():
    """Sample market conditions for testing"""
    return {
        'date_local': date(2026, 1, 15),
        'instrument': 'MGC',
        'asia_travel': 2.0,
        'london_reversals': 2,
        'orb_0900_size': 0.08,
        'orb_1000_size': 0.05,
        'orb_1100_size': 0.03,
        'orb_1800_size': 0.06,
        'orb_2300_size': 0.07,
        'orb_0030_size': 0.04,
    }


@pytest.fixture
def sample_validated_setups():
    """Sample validated setup data"""
    return [
        {
            'instrument': 'MGC',
            'orb_time': '0900',
            'rr': 8.0,
            'sl_mode': 'FULL',
            'orb_size_filter': 0.05,
            'win_rate': 15.0,
            'expected_r': 0.20,
            'sample_size': 100
        },
        {
            'instrument': 'MGC',
            'orb_time': '1000',
            'rr': 8.0,
            'sl_mode': 'FULL',
            'orb_size_filter': None,
            'win_rate': 15.3,
            'expected_r': 0.378,
            'sample_size': 262
        },
        {
            'instrument': 'MGC',
            'orb_time': '1100',
            'rr': 8.0,
            'sl_mode': 'FULL',
            'orb_size_filter': None,
            'win_rate': 14.5,
            'expected_r': 0.15,
            'sample_size': 150
        }
    ]


@pytest.fixture
def populated_test_db(test_db, sample_market_data, sample_validated_setups):
    """Test database pre-populated with sample data"""
    # test_db is now a path string, so reconnect
    conn = duckdb.connect(test_db)

    # Insert sample market data
    conn.execute("""
        INSERT INTO daily_features VALUES (
            ?, ?,
            2650.0, 2648.0,  -- asia_high, asia_low
            2651.0, 2649.0,  -- london_high, london_low
            2652.0, 2650.0,  -- ny_high, ny_low
            2650.0, 2649.92, ?, 'NONE', NULL, NULL,  -- 0900 ORB
            2650.5, 2650.45, ?, 'NONE', NULL, NULL,  -- 1000 ORB
            2651.0, 2650.97, ?, 'NONE', NULL, NULL,  -- 1100 ORB
            2651.5, 2651.44, ?, 'NONE', NULL, NULL,  -- 1800 ORB
            2652.0, 2651.93, ?, 'NONE', NULL, NULL,  -- 2300 ORB
            2652.5, 2652.46, ?, 'NONE', NULL, NULL   -- 0030 ORB
        )
    """, [
        sample_market_data['date_local'],
        sample_market_data['instrument'],
        sample_market_data['orb_0900_size'],
        sample_market_data['orb_1000_size'],
        sample_market_data['orb_1100_size'],
        sample_market_data['orb_1800_size'],
        sample_market_data['orb_2300_size'],
        sample_market_data['orb_0030_size']
    ])

    # Insert validated setups
    for setup in sample_validated_setups:
        conn.execute("""
            INSERT INTO validated_setups VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            setup['instrument'],
            setup['orb_time'],
            setup['rr'],
            setup['sl_mode'],
            setup['orb_size_filter'],
            setup['win_rate'],
            setup['expected_r'],
            setup['sample_size']
        ])

    conn.close()
    yield test_db  # Return the db path
    # Database cleanup handled by test_db fixture
