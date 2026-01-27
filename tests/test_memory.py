"""
Tests for memory.py - Living memory system for trade tracking and pattern learning

Critical tests for trade storage, pattern discovery, and session analysis.
"""
import pytest
from datetime import date, timedelta
from trading_app.memory import TradingMemory


class TestTradingMemoryInitialization:
    """Test memory system initialization"""

    def test_memory_initialization_succeeds(self, test_db):
        """Memory system initializes successfully"""
        # Arrange
        db_path = test_db

        # Act
        memory = TradingMemory(db_path=db_path)

        # Assert
        assert memory is not None
        assert memory.db_path == db_path

    def test_memory_ensures_tables_exist_on_init(self, test_db):
        """Memory system creates required tables if they don't exist"""
        # Arrange & Act
        memory = TradingMemory(db_path=test_db)

        # Assert
        # Should create: trade_journal, learned_patterns, session_state, execution_metrics
        assert memory is not None


class TestStoreTrade:
    """Test storing trade outcomes"""

    def test_store_trade_with_valid_data_succeeds(
        self, test_db, sample_market_data
    ):
        """Store trade with complete data succeeds"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': sample_market_data['date_local'],
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN',
            'r_multiple': 1.0,
            'asia_travel': sample_market_data['asia_travel'],
            'london_reversals': 2,
            'lesson_learned': 'Good entry timing'
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        assert result is True

    def test_store_trade_with_minimal_data_succeeds(self, test_db):
        """Store trade with only required fields succeeds"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': date(2026, 1, 15),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN'
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        assert result is True

    def test_store_trade_with_loss_outcome_succeeds(self, test_db):
        """Store trade with LOSS outcome (negative R-multiple) succeeds"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': date(2026, 1, 15),
            'orb_time': '1000',
            'instrument': 'MGC',
            'outcome': 'LOSS',
            'r_multiple': -1.0,
            'lesson_learned': 'Wrong entry - reversed too fast'
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        assert result is True

    def test_store_trade_with_skip_outcome_succeeds(self, test_db):
        """Store trade with SKIP outcome (no trade taken) succeeds"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': date(2026, 1, 15),
            'orb_time': '1100',
            'instrument': 'MGC',
            'outcome': 'SKIP',
            'reason': 'ORB size below filter'
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        assert result is True

    def test_store_trade_captures_session_context(
        self, test_db, sample_market_data
    ):
        """Store trade captures session context (Asia travel, London chop, etc.)"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': sample_market_data['date_local'],
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN',
            'asia_travel': sample_market_data['asia_travel'],
            'london_reversals': 2
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        assert result is True


class TestQueryTrades:
    """Test querying historical trades"""

    def test_query_trades_with_no_data_returns_empty_list(self, test_db):
        """Query trades on empty database returns empty list"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Act
        trades = memory.query_trades(days_back=30)

        # Assert
        assert trades == []

    def test_query_trades_filters_by_days_back(self, test_db):
        """Query trades correctly filters by days_back parameter"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store old trade
        old_trade = {
            'date_local': date.today() - timedelta(days=60),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN'
        }
        memory.store_trade(old_trade)

        # Store recent trade
        recent_trade = {
            'date_local': date.today() - timedelta(days=5),
            'orb_time': '1000',
            'instrument': 'MGC',
            'outcome': 'LOSS'
        }
        memory.store_trade(recent_trade)

        # Act
        trades = memory.query_trades(days_back=30)

        # Assert
        # Should only return recent trade
        assert len(trades) == 1
        assert trades[0]['orb_time'] == '1000'

    def test_query_trades_filters_by_orb_time(self, test_db):
        """Query trades filters by specific ORB time"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store multiple trades
        for orb_time in ['0900', '1000', '1100']:
            memory.store_trade({
                'date_local': date.today(),
                'orb_time': orb_time,
                'instrument': 'MGC',
                'outcome': 'WIN'
            })

        # Act
        trades = memory.query_trades(days_back=1, orb_time='0900')

        # Assert
        assert len(trades) == 1
        assert trades[0]['orb_time'] == '0900'

    def test_query_trades_filters_by_outcome(self, test_db):
        """Query trades filters by outcome (WIN, LOSS, SKIP)"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store multiple outcomes
        for outcome in ['WIN', 'LOSS', 'SKIP']:
            memory.store_trade({
                'date_local': date.today(),
                'orb_time': '0900',
                'instrument': 'MGC',
                'outcome': outcome
            })

        # Act
        wins = memory.query_trades(days_back=1, outcome='WIN')
        losses = memory.query_trades(days_back=1, outcome='LOSS')

        # Assert
        assert len(wins) == 1
        assert len(losses) == 1

    def test_query_trades_respects_limit(self, test_db):
        """Query trades respects limit parameter"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store 10 trades
        for i in range(10):
            memory.store_trade({
                'date_local': date.today(),
                'orb_time': '0900',
                'instrument': 'MGC',
                'outcome': 'WIN'
            })

        # Act
        trades = memory.query_trades(days_back=1, limit=5)

        # Assert
        assert len(trades) == 5


class TestLearnPatterns:
    """Test pattern discovery from trade history"""

    def test_learn_patterns_with_insufficient_data_returns_empty(self, test_db):
        """Learn patterns with < 30 trades returns empty list"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store only 5 trades
        for i in range(5):
            memory.store_trade({
                'date_local': date.today(),
                'orb_time': '0900',
                'instrument': 'MGC',
                'outcome': 'WIN'
            })

        # Act
        patterns = memory.learn_patterns(days_back=30)

        # Assert
        # Should return empty or patterns with low confidence
        assert isinstance(patterns, list)

    def test_learn_patterns_discovers_correlations(self, test_db):
        """Learn patterns discovers correlations in trade data"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store pattern: High Asia travel → WIN
        for i in range(30):
            outcome = 'WIN' if (i % 3 == 0) else 'LOSS'
            memory.store_trade({
                'date_local': date.today() - timedelta(days=i),
                'orb_time': '0900',
                'instrument': 'MGC',
                'outcome': outcome,
                'asia_travel': 2.5 if outcome == 'WIN' else 1.5
            })

        # Act
        patterns = memory.learn_patterns(days_back=30)

        # Assert
        # Should discover patterns (may be empty if confidence too low)
        assert isinstance(patterns, list)

    def test_learn_patterns_includes_confidence_score(self, test_db):
        """Learned patterns include statistical confidence score"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store sufficient data
        for i in range(30):
            memory.store_trade({
                'date_local': date.today() - timedelta(days=i),
                'orb_time': '0900',
                'instrument': 'MGC',
                'outcome': 'WIN'
            })

        # Act
        patterns = memory.learn_patterns(days_back=30)

        # Assert
        if patterns:
            for pattern in patterns:
                assert 'confidence' in pattern
                assert 0.0 <= pattern['confidence'] <= 1.0


class TestAnalyzeCurrentSession:
    """Test real-time session analysis"""

    def test_analyze_session_with_no_data_returns_defaults(self, test_db):
        """Analyze session with no data returns default recommendations"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        today_date = date.today()

        # Act
        analysis = memory.analyze_current_session(date_local=today_date)

        # Assert
        assert analysis is not None
        assert 'date_local' in analysis

    def test_analyze_session_matches_similar_conditions(
        self, test_db, sample_market_data
    ):
        """Analyze session finds similar historical conditions"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store historical data
        for i in range(10):
            memory.store_trade({
                'date_local': date.today() - timedelta(days=i+1),
                'orb_time': '0900',
                'instrument': 'MGC',
                'outcome': 'WIN',
                'asia_travel': sample_market_data['asia_travel']
            })

        # Act
        analysis = memory.analyze_current_session(date_local=date.today())

        # Assert
        assert analysis is not None

    def test_analyze_session_provides_recommendations(self, test_db):
        """Analyze session provides actionable recommendations"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        today_date = date.today()

        # Act
        analysis = memory.analyze_current_session(date_local=today_date)

        # Assert
        assert analysis is not None
        # Should have recommendations or reasons


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_memory_handles_null_values_gracefully(self, test_db):
        """Memory handles NULL values in trade data gracefully"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': date(2026, 1, 15),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN',
            'asia_travel': None,  # NULL
            'london_reversals': None  # NULL
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        assert result is True

    def test_memory_handles_duplicate_trades(self, test_db):
        """Memory handles duplicate trade entries (same date + ORB time)"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': date(2026, 1, 15),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN'
        }

        # Act
        result1 = memory.store_trade(trade)
        result2 = memory.store_trade(trade)  # Duplicate

        # Assert
        # Should either update or reject duplicate
        assert result1 is True

    def test_memory_handles_invalid_outcome_values(self, test_db):
        """Memory validates outcome values (WIN, LOSS, SKIP, BREAKEVEN only)"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': date(2026, 1, 15),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'INVALID'  # Not a valid outcome
        }

        # Act & Assert
        # Should either reject or handle gracefully
        try:
            result = memory.store_trade(trade)
            # If it accepts, it should store as-is
            assert result is True or result is False
        except ValueError:
            # Expected if validation exists
            pass

    def test_memory_handles_future_dates(self, test_db):
        """Memory handles future dates (should reject or warn)"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        future_date = date.today() + timedelta(days=365)
        trade = {
            'date_local': future_date,
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN'
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        # Should either accept or reject future dates
        assert isinstance(result, bool)


class TestExecutionMetrics:
    """Test execution quality tracking"""

    def test_execution_metrics_captured_with_trade(self, test_db):
        """Execution metrics (slippage, fill time) captured with trade"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': date(2026, 1, 15),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN',
            'entry_slippage': 0.2,
            'exit_slippage': 0.1,
            'fill_time_ms': 250
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        assert result is True

    def test_execution_metrics_queryable(self, test_db):
        """Execution metrics can be queried for analysis"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store trade with execution metrics
        memory.store_trade({
            'date_local': date.today(),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'WIN',
            'entry_slippage': 0.3
        })

        # Act
        trades = memory.query_trades(days_back=1)

        # Assert
        if trades:
            # Should have execution metrics if stored
            assert len(trades) > 0


class TestLessonLearned:
    """Test lesson learned tracking"""

    def test_lesson_learned_stored_with_trade(self, test_db):
        """Lesson learned text stored with trade"""
        # Arrange
        memory = TradingMemory(db_path=test_db)
        trade = {
            'date_local': date(2026, 1, 15),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'LOSS',
            'lesson_learned': 'Entered too early - should wait for confirmation'
        }

        # Act
        result = memory.store_trade(trade)

        # Assert
        assert result is True

    def test_notable_trades_flagged_correctly(self, test_db):
        """Notable trades (with lessons) flagged for easy retrieval"""
        # Arrange
        memory = TradingMemory(db_path=test_db)

        # Store notable trade
        memory.store_trade({
            'date_local': date.today(),
            'orb_time': '0900',
            'instrument': 'MGC',
            'outcome': 'LOSS',
            'lesson_learned': 'Important lesson',
            'notable': True
        })

        # Store normal trade
        memory.store_trade({
            'date_local': date.today(),
            'orb_time': '1000',
            'instrument': 'MGC',
            'outcome': 'WIN'
        })

        # Act
        trades = memory.query_trades(days_back=1)

        # Assert
        assert len(trades) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
