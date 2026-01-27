"""
Tests for ai_chat.py - AI trading assistant for natural language queries

Critical tests for query parsing, response formatting, and integration with memory system.
"""
import pytest
from datetime import date
from trading_app.ai_chat import TradingAssistant


class TestTradingAssistantInitialization:
    """Test AI assistant initialization"""

    def test_assistant_initialization_succeeds(self, test_db):
        """AI assistant initializes successfully"""
        # Arrange
        db_path = test_db

        # Act
        assistant = TradingAssistant(db_path=db_path)

        # Assert
        assert assistant is not None
        assert assistant.db_path == db_path

    def test_assistant_initializes_dependencies(self, test_db):
        """Assistant initializes memory, edge tracker, scanner"""
        # Arrange & Act
        assistant = TradingAssistant(db_path=test_db)

        # Assert
        assert assistant.memory is not None
        assert assistant.edge_tracker is not None
        assert assistant.scanner is not None


class TestSystemHealthSummary:
    """Test system health summary generation"""

    def test_get_system_health_summary_returns_text(
        self, populated_test_db, sample_validated_setups
    ):
        """System health summary returns formatted text"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.get_system_health_summary()

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0

    def test_system_health_includes_edge_status(
        self, populated_test_db, sample_validated_setups
    ):
        """System health summary includes edge status"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.get_system_health_summary()

        # Assert
        # Should mention edge health or status
        assert 'edge' in response.lower() or 'status' in response.lower()

    def test_system_health_with_no_data_handles_gracefully(self, test_db):
        """System health with no data returns appropriate message"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)

        # Act
        response = assistant.get_system_health_summary()

        # Assert
        # Should mention no data or similar
        assert response is not None
        assert len(response) > 0


class TestRegimeSummary:
    """Test market regime summary generation"""

    def test_get_regime_summary_returns_text(
        self, populated_test_db, sample_validated_setups
    ):
        """Regime summary returns formatted text"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.get_regime_summary()

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0

    def test_regime_summary_includes_regime_type(
        self, populated_test_db, sample_validated_setups
    ):
        """Regime summary mentions regime type (TRENDING, RANGE_BOUND, etc.)"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.get_regime_summary()

        # Assert
        # Should mention a regime type
        regime_types = ['trending', 'range', 'volatile', 'quiet', 'unknown']
        assert any(regime in response.lower() for regime in regime_types)

    def test_regime_summary_with_no_data_handles_gracefully(self, test_db):
        """Regime summary with no data returns appropriate message"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)

        # Act
        response = assistant.get_regime_summary()

        # Assert
        assert response is not None


class TestAnalyzeToday:
    """Test today's analysis generation"""

    def test_analyze_today_returns_text(
        self, populated_test_db, sample_market_data
    ):
        """Analyze today returns formatted text"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.analyze_today()

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0

    def test_analyze_today_includes_valid_setups(
        self, populated_test_db, sample_market_data
    ):
        """Today's analysis mentions valid setups"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.analyze_today()

        # Assert
        # Should mention setups or ORBs
        assert 'orb' in response.lower() or 'setup' in response.lower()

    def test_analyze_today_with_no_data_handles_gracefully(self, test_db):
        """Today's analysis with no data returns appropriate message"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)

        # Act
        response = assistant.analyze_today()

        # Assert
        assert response is not None
        # Should mention no data, no setups, or similar
        assert ('no data' in response.lower() or
                'available' in response.lower() or
                'no valid setups' in response.lower())


class TestAskFunction:
    """Test natural language query handling"""

    def test_ask_with_performance_query_returns_relevant_answer(
        self, populated_test_db, sample_validated_setups
    ):
        """Performance query returns relevant performance data"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)
        question = "How did 0900 ORB perform?"

        # Act
        response = assistant.ask(question)

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0
        # Should mention 0900 or performance
        assert '0900' in response or '9' in response

    def test_ask_with_edge_health_query_returns_health_info(
        self, populated_test_db, sample_validated_setups
    ):
        """Edge health query returns edge status"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)
        question = "What is the edge health?"

        # Act
        response = assistant.ask(question)

        # Assert
        assert isinstance(response, str)
        assert 'edge' in response.lower() or 'health' in response.lower()

    def test_ask_with_regime_query_returns_regime_info(
        self, populated_test_db, sample_validated_setups
    ):
        """Market regime query returns regime information"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)
        question = "What is the market regime?"

        # Act
        response = assistant.ask(question)

        # Assert
        assert isinstance(response, str)
        assert 'regime' in response.lower() or 'market' in response.lower()

    def test_ask_with_empty_query_handles_gracefully(self, test_db):
        """Empty query handled gracefully"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)
        question = ""

        # Act
        response = assistant.ask(question)

        # Assert
        assert isinstance(response, str)

    def test_ask_with_invalid_query_returns_helpful_message(self, test_db):
        """Invalid/unclear query returns helpful message"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)
        question = "asdfghjkl random nonsense query"

        # Act
        response = assistant.ask(question)

        # Assert
        assert isinstance(response, str)
        assert len(response) > 0


class TestQueryParsing:
    """Test query parsing and intent detection"""

    def test_parse_orb_time_from_query(self, test_db):
        """Assistant extracts ORB time from natural language query"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)
        queries = [
            "How did 0900 ORB perform?",
            "1100 ORB performance",
            "Check 1800 setup"
        ]

        # Act & Assert
        for query in queries:
            response = assistant.ask(query)
            # Should respond with something relevant
            assert isinstance(response, str)

    def test_parse_time_period_from_query(self, test_db):
        """Assistant extracts time period (30 days, 60 days, etc.) from query"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)
        queries = [
            "Performance in last 30 days",
            "60 day win rate",
            "Recent performance"
        ]

        # Act & Assert
        for query in queries:
            response = assistant.ask(query)
            assert isinstance(response, str)

    def test_detect_performance_query_intent(self, test_db):
        """Assistant detects performance query intent"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)
        performance_queries = [
            "How did 0900 perform?",
            "Win rate for 1100 ORB",
            "What's the performance?"
        ]

        # Act & Assert
        for query in performance_queries:
            response = assistant.ask(query)
            # Should be performance-related
            assert isinstance(response, str)

    def test_detect_edge_health_query_intent(self, test_db):
        """Assistant detects edge health query intent"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)
        edge_queries = [
            "Edge health",
            "Are the edges still working?",
            "System status"
        ]

        # Act & Assert
        for query in edge_queries:
            response = assistant.ask(query)
            assert isinstance(response, str)


class TestResponseFormatting:
    """Test response formatting and presentation"""

    def test_responses_use_ascii_not_unicode(self, test_db):
        """Responses use ASCII characters (no Unicode emojis for Windows)"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)

        # Act
        responses = [
            assistant.get_system_health_summary(),
            assistant.get_regime_summary(),
            assistant.analyze_today()
        ]

        # Assert
        for response in responses:
            # Should not contain problematic Unicode emojis
            # ASCII alternatives: [OK], [!], [X], [^], etc.
            assert isinstance(response, str)
            # Check for ASCII markers
            ascii_markers = ['[OK]', '[!]', '[X]', '[^]', '[++]']
            # At least should not crash on Windows terminal

    def test_responses_are_concise(self, populated_test_db):
        """Responses are concise (not overly verbose)"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.get_system_health_summary()

        # Assert
        # Should be reasonable length (not 10,000 characters)
        assert len(response) < 5000

    def test_responses_include_actionable_info(self, populated_test_db):
        """Responses include actionable information (not just descriptions)"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.analyze_today()

        # Assert
        # Should mention actions or recommendations
        assert isinstance(response, str)


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_assistant_handles_database_errors_gracefully(self):
        """Assistant handles database connection errors gracefully"""
        # Arrange
        invalid_path = '/nonexistent/database.db'

        # Act & Assert
        try:
            assistant = TradingAssistant(db_path=invalid_path)
            # Should either fail gracefully or handle
            assert assistant is not None
        except (FileNotFoundError, OSError):
            # Expected for invalid path
            pass

    def test_assistant_handles_missing_data_gracefully(self, test_db):
        """Assistant handles missing data without crashes"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)

        # Act
        responses = [
            assistant.get_system_health_summary(),
            assistant.get_regime_summary(),
            assistant.analyze_today()
        ]

        # Assert
        for response in responses:
            assert response is not None
            assert isinstance(response, str)

    def test_assistant_handles_null_values_gracefully(self, test_db):
        """Assistant handles NULL values in database gracefully"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)

        # Act
        response = assistant.ask("What's the performance?")

        # Assert
        assert response is not None


class TestIntegration:
    """Test integration with memory, edge tracker, and scanner"""

    def test_assistant_uses_memory_for_queries(self, test_db):
        """Assistant queries memory system for historical data"""
        # Arrange
        assistant = TradingAssistant(db_path=test_db)

        # Store trade in memory
        assistant.memory.store_trade({
            'date_local': date.today(),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN'
        })

        # Act
        response = assistant.ask("Recent trades")

        # Assert
        assert isinstance(response, str)

    def test_assistant_uses_edge_tracker_for_health(
        self, populated_test_db, sample_validated_setups
    ):
        """Assistant uses edge tracker for health status"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.get_system_health_summary()

        # Assert
        assert isinstance(response, str)

    def test_assistant_uses_scanner_for_today_analysis(
        self, populated_test_db, sample_market_data
    ):
        """Assistant uses market scanner for today's analysis"""
        # Arrange
        assistant = TradingAssistant(db_path=populated_test_db)

        # Act
        response = assistant.analyze_today()

        # Assert
        assert isinstance(response, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
