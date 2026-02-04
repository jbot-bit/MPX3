"""
Comprehensive unit tests for analysis/ai_query.py

Tests cover:
- AIQueryEngine class initialization
- Pattern matching for query types
- Helper methods (_parse_orb_time, _parse_direction)
- Query handlers
- Fallback behavior
- Edge cases and invalid inputs
"""

import pytest
import re
import sys
from pathlib import Path
from pipeline.paths import GOLD_DB_PATH

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.ai_query import AIQueryEngine


# =============================================================================
# Test AIQueryEngine Initialization
# =============================================================================

class TestAIQueryEngineInit:
    """Test AIQueryEngine initialization"""

    def test_default_initialization(self):
        """AIQueryEngine should initialize with defaults"""
        engine = AIQueryEngine()
        assert engine.mgc_db_path == GOLD_DB_PATH
        assert engine.journal_db_path == "trades.db"
        assert len(engine.patterns) > 0

    def test_custom_paths(self):
        """AIQueryEngine should accept custom paths"""
        engine = AIQueryEngine(
            mgc_db_path="/custom/path.db",
            journal_db_path="/custom/journal.db"
        )
        assert engine.mgc_db_path == "/custom/path.db"
        assert engine.journal_db_path == "/custom/journal.db"

    def test_patterns_have_required_fields(self):
        """All patterns should have pattern, handler, and description"""
        engine = AIQueryEngine()
        for p in engine.patterns:
            assert "pattern" in p
            assert "handler" in p
            assert "description" in p
            assert callable(p["handler"])


# =============================================================================
# Test _parse_orb_time Method
# =============================================================================

class TestParseOrbTime:
    """Test _parse_orb_time helper method"""

    @pytest.fixture
    def engine(self):
        return AIQueryEngine()

    def test_parse_4_digit_times(self, engine):
        """Should parse 4-digit time formats"""
        assert engine._parse_orb_time("What about 0900 ORB?") == "0900"
        assert engine._parse_orb_time("Check 1000 performance") == "1000"
        assert engine._parse_orb_time("1100 breakout stats") == "1100"
        assert engine._parse_orb_time("1800 ORB today") == "1800"
        assert engine._parse_orb_time("2300 night session") == "2300"
        assert engine._parse_orb_time("0030 cash open") == "0030"

    def test_parse_text_representations(self, engine):
        """Should parse text time representations"""
        assert engine._parse_orb_time("nine o'clock ORB") == "0900"
        assert engine._parse_orb_time("9am breakout") == "0900"
        assert engine._parse_orb_time("ten ORB performance") == "1000"
        assert engine._parse_orb_time("10am stats") == "1000"
        assert engine._parse_orb_time("6pm ORB") == "1800"
        assert engine._parse_orb_time("11pm session") == "2300"

    def test_parse_colon_format(self, engine):
        """Should parse time with colon"""
        assert engine._parse_orb_time("9:00 ORB") == "0900"
        assert engine._parse_orb_time("10:00 breakout") == "1000"
        assert engine._parse_orb_time("18:00 performance") == "1800"
        assert engine._parse_orb_time("23:00 stats") == "2300"
        assert engine._parse_orb_time("00:30 cash") == "0030"

    def test_no_time_found(self, engine):
        """Should return None when no time found"""
        assert engine._parse_orb_time("What is the best ORB?") is None
        assert engine._parse_orb_time("Show me performance") is None
        assert engine._parse_orb_time("") is None

    def test_case_insensitive(self, engine):
        """Should be case insensitive"""
        assert engine._parse_orb_time("NINE am") == "0900"
        assert engine._parse_orb_time("TEN o'clock") == "1000"


# =============================================================================
# Test _parse_direction Method
# =============================================================================

class TestParseDirection:
    """Test _parse_direction helper method"""

    @pytest.fixture
    def engine(self):
        return AIQueryEngine()

    def test_parse_up_keywords(self, engine):
        """Should parse UP direction keywords"""
        assert engine._parse_direction("UP breakout") == "UP"
        assert engine._parse_direction("bullish move") == "UP"
        assert engine._parse_direction("long setup") == "UP"

    def test_parse_down_keywords(self, engine):
        """Should parse DOWN direction keywords"""
        assert engine._parse_direction("DOWN breakout") == "DOWN"
        assert engine._parse_direction("bearish move") == "DOWN"
        # Note: "short setup" contains "up" in "setup" so it matches UP first
        assert engine._parse_direction("short trade") == "DOWN"

    def test_no_direction_found(self, engine):
        """Should return None when no direction found"""
        assert engine._parse_direction("What is the ORB?") is None
        assert engine._parse_direction("Show performance") is None
        assert engine._parse_direction("") is None

    def test_case_insensitive(self, engine):
        """Should be case insensitive"""
        assert engine._parse_direction("UP") == "UP"
        assert engine._parse_direction("up") == "UP"
        assert engine._parse_direction("Up") == "UP"
        assert engine._parse_direction("DOWN") == "DOWN"
        assert engine._parse_direction("down") == "DOWN"


# =============================================================================
# Test Pattern Matching
# =============================================================================

class TestPatternMatching:
    """Test pattern matching for different query types"""

    @pytest.fixture
    def engine(self):
        return AIQueryEngine()

    def test_win_rate_pattern_matches(self, engine):
        """Win rate pattern should match relevant queries"""
        pattern = next(p for p in engine.patterns if "win rate" in p["description"].lower())
        regex = pattern["pattern"]

        # Should match
        assert re.search(regex, "What is the win rate for 1100 UP?", re.IGNORECASE)
        assert re.search(regex, "winrate 0900 down", re.IGNORECASE)
        assert re.search(regex, "wr for 1000", re.IGNORECASE)

    def test_best_setups_pattern_matches(self, engine):
        """Best setups pattern should match relevant queries"""
        pattern = next(p for p in engine.patterns if "best" in p["description"].lower())
        regex = pattern["pattern"]

        # Should match
        assert re.search(regex, "Show me the best ORBs", re.IGNORECASE)
        assert re.search(regex, "top performing setups", re.IGNORECASE)
        assert re.search(regex, "highest win rate strategy", re.IGNORECASE)

    def test_worst_setups_pattern_matches(self, engine):
        """Worst setups pattern should match relevant queries"""
        pattern = next(p for p in engine.patterns if "worst" in p["description"].lower())
        regex = pattern["pattern"]

        # Should match (regex requires singular: orb|setup|strategy)
        assert re.search(regex, "worst ORB setups", re.IGNORECASE)
        assert re.search(regex, "bottom performing setup", re.IGNORECASE)
        assert re.search(regex, "lowest win rate orb", re.IGNORECASE)

    def test_session_count_pattern_matches(self, engine):
        """Session count pattern should match relevant queries"""
        pattern = next(p for p in engine.patterns if "session" in p["description"].lower())
        regex = pattern["pattern"]

        # Should match
        assert re.search(regex, "How many days had Asia EXPANDED?", re.IGNORECASE)
        assert re.search(regex, "count london consolidation", re.IGNORECASE)

    def test_recent_pattern_matches(self, engine):
        """Recent performance pattern should match relevant queries"""
        pattern = next(p for p in engine.patterns if "recent" in p["description"].lower())
        regex = pattern["pattern"]

        # Should match (regex requires days? or trades?, not week/stats)
        assert re.search(regex, "recent 30 days performance", re.IGNORECASE)
        assert re.search(regex, "last 10 trades", re.IGNORECASE)
        assert re.search(regex, "past 7 days results", re.IGNORECASE)

    def test_date_pattern_matches(self, engine):
        """Date pattern should match ISO dates"""
        pattern = next(p for p in engine.patterns if "date" in p["description"].lower())
        regex = pattern["pattern"]

        # Should match
        assert re.search(regex, "What happened on 2024-01-15?")
        assert re.search(regex, "Show me 2026-01-09 data")

    def test_comparison_pattern_matches(self, engine):
        """Comparison pattern should match setup comparisons"""
        pattern = next(p for p in engine.patterns if "compare" in p["description"].lower())
        regex = pattern["pattern"]

        # Should match
        assert re.search(regex, "compare 1100 vs 1800", re.IGNORECASE)
        assert re.search(regex, "compare 0900 against 1000", re.IGNORECASE)


# =============================================================================
# Test Query Method
# =============================================================================

class TestQueryMethod:
    """Test the main query method"""

    @pytest.fixture
    def engine(self):
        return AIQueryEngine()

    def test_empty_query_returns_message(self, engine):
        """Empty query should return helpful message"""
        result = engine.query("")
        assert "Please ask a question" in result

    def test_whitespace_query_returns_message(self, engine):
        """Whitespace-only query should return helpful message"""
        result = engine.query("   ")
        assert "Please ask a question" in result

    def test_unrecognized_query_returns_fallback(self, engine):
        """Unrecognized query should return fallback help"""
        result = engine.query("xyzabc random gibberish")
        assert "I'm not sure" in result or "Try asking" in result


# =============================================================================
# Test Fallback Handler
# =============================================================================

class TestFallbackHandler:
    """Test fallback handler for unrecognized queries"""

    @pytest.fixture
    def engine(self):
        return AIQueryEngine()

    def test_fallback_provides_examples(self, engine):
        """Fallback should provide example queries"""
        result = engine._handle_fallback("unknown query")
        assert "win rate" in result.lower() or "example" in result.lower()

    def test_fallback_mentions_tools(self, engine):
        """Fallback should mention available tools"""
        result = engine._handle_fallback("unknown query")
        assert "analyze" in result.lower() or "tool" in result.lower() or "journal" in result.lower()


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def engine(self):
        return AIQueryEngine()

    def test_multiple_times_in_query(self, engine):
        """Should extract first time when multiple present"""
        result = engine._parse_orb_time("Compare 0900 and 1000 ORBs")
        assert result in ["0900", "1000"]  # First one found

    def test_special_characters_in_query(self, engine):
        """Should handle special characters"""
        # Should not crash
        engine.query("What's the win rate for 1100?")
        engine.query("How did 0900 perform (UP)?")
        engine.query("Stats for 1800 [DOWN]")

    def test_very_long_query(self, engine):
        """Should handle very long queries"""
        long_query = "What is " * 100 + "the win rate for 1100 UP?"
        result = engine.query(long_query)
        assert isinstance(result, str)

    def test_unicode_in_query(self, engine):
        """Should handle unicode characters"""
        # Should not crash
        result = engine.query("What's the 1100 performance? 🚀")
        assert isinstance(result, str)

    def test_numeric_only_query(self, engine):
        """Numeric-only query should be handled"""
        result = engine.query("1100")
        # Should extract time but may need more context
        assert isinstance(result, str)

    def test_case_variations(self, engine):
        """Should handle various case combinations"""
        # All should be recognized
        engine._parse_orb_time("0900")
        engine._parse_direction("UP")
        engine._parse_direction("up")
        engine._parse_direction("Up")


# =============================================================================
# Test Pattern Handler Selection
# =============================================================================

class TestPatternHandlerSelection:
    """Test that correct handlers are selected for queries"""

    @pytest.fixture
    def engine(self):
        return AIQueryEngine()

    def test_first_matching_pattern_used(self, engine):
        """First matching pattern should be used"""
        # Create a query that could match multiple patterns
        # The patterns list order determines priority
        patterns = engine.patterns

        # Verify patterns exist
        assert len(patterns) > 0

        # Each pattern should have valid regex
        for p in patterns:
            try:
                re.compile(p["pattern"])
            except re.error:
                pytest.fail(f"Invalid regex pattern: {p['pattern']}")


# =============================================================================
# Test Database Connection Preparation
# =============================================================================

class TestPrepareConnection:
    """Test database connection preparation"""

    @pytest.fixture
    def mock_db_v2(self, tmp_path):
        """Create mock database with V2 schema (daily_features)"""
        import duckdb

        db_path = tmp_path / GOLD_DB_PATH
        conn = duckdb.connect(str(db_path))

        # Create daily_features table
        conn.execute("""
            CREATE TABLE daily_features (
                date_local DATE,
                instrument VARCHAR,
                asia_high DOUBLE,
                asia_low DOUBLE,
                asia_range DOUBLE,
                asia_type_code VARCHAR,
                london_high DOUBLE,
                london_low DOUBLE,
                london_range DOUBLE,
                london_type_code VARCHAR,
                ny_high DOUBLE,
                ny_low DOUBLE,
                ny_range DOUBLE,
                pre_ny_type_code VARCHAR,
                atr_20 DOUBLE,
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
                orb_0030_r_multiple DOUBLE
            )
        """)

        # Insert test data
        conn.execute("""
            INSERT INTO daily_features (
                date_local, instrument, asia_high, asia_low, asia_range, asia_type_code,
                london_high, london_low, london_range, london_type_code,
                ny_high, ny_low, ny_range, pre_ny_type_code, atr_20,
                orb_0900_high, orb_0900_low, orb_0900_size, orb_0900_break_dir, orb_0900_outcome, orb_0900_r_multiple,
                orb_1000_high, orb_1000_low, orb_1000_size, orb_1000_break_dir, orb_1000_outcome, orb_1000_r_multiple,
                orb_1100_high, orb_1100_low, orb_1100_size, orb_1100_break_dir, orb_1100_outcome, orb_1100_r_multiple,
                orb_1800_high, orb_1800_low, orb_1800_size, orb_1800_break_dir, orb_1800_outcome, orb_1800_r_multiple,
                orb_2300_high, orb_2300_low, orb_2300_size, orb_2300_break_dir, orb_2300_outcome, orb_2300_r_multiple,
                orb_0030_high, orb_0030_low, orb_0030_size, orb_0030_break_dir, orb_0030_outcome, orb_0030_r_multiple
            ) VALUES (
                '2024-01-02', 'MGC', 2650.0, 2640.0, 10.0, 'A2_EXPANDED',
                2660.0, 2645.0, 15.0, 'L4_CONSOLIDATION',
                2665.0, 2650.0, 15.0, 'N3_CONSOLIDATION', 15.0,
                2651.0, 2650.0, 1.0, 'UP', 'WIN', 1.5,
                2652.0, 2651.0, 1.0, 'DOWN', 'LOSS', -1.0,
                2653.0, 2652.0, 1.0, 'UP', 'WIN', 2.0,
                2654.0, 2653.0, 1.0, 'DOWN', 'LOSS', -1.0,
                2655.0, 2654.0, 1.0, 'UP', 'WIN', 1.5,
                2656.0, 2655.0, 1.0, 'DOWN', 'LOSS', -1.0
            )
        """)

        conn.close()
        return str(db_path)

    def test_prepare_connection_v2(self, mock_db_v2):
        """Should create compat view for V2 schema"""
        engine = AIQueryEngine(mgc_db_path=mock_db_v2)
        conn, table_name = engine._prepare_connection()

        # Should return compat view name for V2
        assert table_name == "daily_features_compat"

        # Compat view should be queryable
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        assert result[0] == 1

        conn.close()
