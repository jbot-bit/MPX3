"""
Comprehensive unit tests for analysis/query_engine.py

Tests cover:
- Filters dataclass and serialization
- StrategyConfig dataclass and serialization
- PRESETS dictionary
- Helper functions (filters_key, strategy_key, serialize/deserialize)
- _build_where_clause SQL generation
- _sanitize DataFrame cleaning
- Edge cases, boundary conditions, and invalid inputs
"""

import pytest
import numpy as np
import pandas as pd
from dataclasses import asdict
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.query_engine import (
    Filters,
    StrategyConfig,
    PRESETS,
    ORB_TIMES,
    OUTCOME_OPTIONS,
    BREAK_DIR_OPTIONS,
    ENTRY_MODELS,
    default_strategy,
    filters_key,
    strategy_key,
    serialize_filters,
    filters_from_dict,
    serialize_strategy,
    strategy_from_dict,
    _build_where_clause,
    _sanitize,
    _required_closes,
)


# =============================================================================
# Test Constants
# =============================================================================

class TestConstants:
    """Test that module constants are properly defined"""

    def test_orb_times_tuple(self):
        """ORB_TIMES should be a tuple with 6 valid times"""
        assert isinstance(ORB_TIMES, tuple)
        assert len(ORB_TIMES) == 6
        expected = ("0900", "1000", "1100", "1800", "2300", "0030")
        assert ORB_TIMES == expected

    def test_outcome_options(self):
        """OUTCOME_OPTIONS should contain valid outcomes"""
        assert isinstance(OUTCOME_OPTIONS, tuple)
        assert "WIN" in OUTCOME_OPTIONS
        assert "LOSS" in OUTCOME_OPTIONS
        assert "NO_TRADE" in OUTCOME_OPTIONS

    def test_break_dir_options(self):
        """BREAK_DIR_OPTIONS should contain valid directions"""
        assert isinstance(BREAK_DIR_OPTIONS, tuple)
        assert "ANY" in BREAK_DIR_OPTIONS
        assert "UP" in BREAK_DIR_OPTIONS
        assert "DOWN" in BREAK_DIR_OPTIONS

    def test_entry_models_dict(self):
        """ENTRY_MODELS should be a dict with label and desc"""
        assert isinstance(ENTRY_MODELS, dict)
        assert len(ENTRY_MODELS) >= 1
        for key, value in ENTRY_MODELS.items():
            assert "label" in value
            assert "desc" in value


# =============================================================================
# Test Filters Dataclass
# =============================================================================

class TestFiltersDataclass:
    """Test Filters dataclass creation and behavior"""

    def test_filters_creation_minimal(self):
        """Create Filters with minimal required fields"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        assert filters.start_date is None
        assert filters.break_dir == "ANY"
        assert filters.enable_atr_filter is False

    def test_filters_creation_full(self):
        """Create Filters with all fields populated"""
        filters = Filters(
            start_date="2024-01-01",
            end_date="2024-12-31",
            orb_times=("0900", "1000"),
            break_dir="UP",
            outcomes=("WIN", "LOSS"),
            asia_type_code="A1_TIGHT",
            include_null_asia=False,
            london_type_code="L4_CONSOLIDATION",
            include_null_london=False,
            pre_ny_type_code="N3_CONSOLIDATION",
            include_null_pre_ny=False,
            enable_atr_filter=True,
            atr_min=10.0,
            atr_max=30.0,
            enable_asia_range_filter=True,
            asia_range_min=0.5,
            asia_range_max=2.0,
        )
        assert filters.start_date == "2024-01-01"
        assert filters.orb_times == ("0900", "1000")
        assert filters.atr_min == 10.0

    def test_filters_is_frozen(self):
        """Filters should be immutable (frozen=True)"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            filters.start_date = "2024-01-01"


# =============================================================================
# Test StrategyConfig Dataclass
# =============================================================================

class TestStrategyConfigDataclass:
    """Test StrategyConfig dataclass creation and behavior"""

    def test_strategy_config_creation(self):
        """Create StrategyConfig with all fields"""
        config = StrategyConfig(
            level_basis="orb_boundary",
            entry_model="1m_close_break",
            confirm_closes=1,
            retest_required=False,
            retest_rule="touch",
            pierce_ticks=None,
            rejection_tf="1m",
            stop_rule="ORB_opposite_boundary",
            max_stop_ticks=None,
            cutoff_minutes=None,
            one_trade_per_orb=True,
        )
        assert config.level_basis == "orb_boundary"
        assert config.entry_model == "1m_close_break"
        assert config.confirm_closes == 1

    def test_strategy_config_is_frozen(self):
        """StrategyConfig should be immutable"""
        config = StrategyConfig(
            level_basis="orb_boundary",
            entry_model="1m_close_break",
            confirm_closes=1,
            retest_required=False,
            retest_rule="touch",
            pierce_ticks=None,
            rejection_tf="1m",
            stop_rule="ORB_opposite_boundary",
            max_stop_ticks=None,
            cutoff_minutes=None,
            one_trade_per_orb=True,
        )
        with pytest.raises(Exception):
            config.level_basis = "orb_half"


# =============================================================================
# Test PRESETS Dictionary
# =============================================================================

class TestPresets:
    """Test PRESETS dictionary structure and content"""

    def test_presets_not_empty(self):
        """PRESETS should contain strategy configurations"""
        assert len(PRESETS) > 0

    def test_presets_values_are_strategy_configs(self):
        """All PRESETS values should be StrategyConfig instances"""
        for name, config in PRESETS.items():
            assert isinstance(config, StrategyConfig), f"Preset '{name}' is not StrategyConfig"

    def test_preset_keys_are_descriptive(self):
        """PRESETS keys should be descriptive strings"""
        for key in PRESETS.keys():
            assert isinstance(key, str)
            assert len(key) > 0

    def test_default_strategy_returns_preset(self):
        """default_strategy() should return a valid StrategyConfig"""
        default = default_strategy()
        assert isinstance(default, StrategyConfig)
        assert default.level_basis in ("orb_boundary", "orb_half")


# =============================================================================
# Test filters_key Function
# =============================================================================

class TestFiltersKey:
    """Test filters_key hash function"""

    def test_filters_key_returns_tuple(self):
        """filters_key should return a tuple"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        key = filters_key(filters)
        assert isinstance(key, tuple)

    def test_filters_key_deterministic(self):
        """Same filters should produce same key"""
        filters1 = Filters(
            start_date="2024-01-01",
            end_date="2024-12-31",
            orb_times=("0900",),
            break_dir="UP",
            outcomes=("WIN",),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        filters2 = Filters(
            start_date="2024-01-01",
            end_date="2024-12-31",
            orb_times=("0900",),
            break_dir="UP",
            outcomes=("WIN",),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        assert filters_key(filters1) == filters_key(filters2)

    def test_filters_key_different_for_different_filters(self):
        """Different filters should produce different keys"""
        filters1 = Filters(
            start_date="2024-01-01",
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        filters2 = Filters(
            start_date="2024-06-01",
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        assert filters_key(filters1) != filters_key(filters2)


# =============================================================================
# Test strategy_key Function
# =============================================================================

class TestStrategyKey:
    """Test strategy_key hash function"""

    def test_strategy_key_returns_tuple(self):
        """strategy_key should return a tuple"""
        config = default_strategy()
        key = strategy_key(config)
        assert isinstance(key, tuple)

    def test_strategy_key_deterministic(self):
        """Same strategy should produce same key"""
        config1 = default_strategy()
        config2 = default_strategy()
        assert strategy_key(config1) == strategy_key(config2)


# =============================================================================
# Test Serialization Functions
# =============================================================================

class TestSerialization:
    """Test serialize/deserialize functions"""

    def test_serialize_filters_returns_dict(self):
        """serialize_filters should return a dict"""
        filters = Filters(
            start_date="2024-01-01",
            end_date=None,
            orb_times=("0900", "1000"),
            break_dir="UP",
            outcomes=("WIN", "LOSS"),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        result = serialize_filters(filters)
        assert isinstance(result, dict)
        # Tuples should be converted to lists for JSON
        assert isinstance(result["orb_times"], list)
        assert isinstance(result["outcomes"], list)

    def test_filters_roundtrip(self):
        """Filters should survive serialize/deserialize roundtrip"""
        original = Filters(
            start_date="2024-01-01",
            end_date="2024-12-31",
            orb_times=("0900", "1000"),
            break_dir="UP",
            outcomes=("WIN", "LOSS"),
            asia_type_code="A1_TIGHT",
            include_null_asia=False,
            london_type_code="L4_CONSOLIDATION",
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=True,
            atr_min=10.0,
            atr_max=30.0,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        serialized = serialize_filters(original)
        restored = filters_from_dict(serialized)

        assert restored.start_date == original.start_date
        assert restored.end_date == original.end_date
        assert restored.orb_times == original.orb_times
        assert restored.break_dir == original.break_dir
        assert restored.asia_type_code == original.asia_type_code
        assert restored.atr_min == original.atr_min

    def test_filters_from_dict_defaults(self):
        """filters_from_dict should use defaults for missing keys"""
        minimal_dict = {"start_date": "2024-01-01"}
        filters = filters_from_dict(minimal_dict)

        assert filters.start_date == "2024-01-01"
        assert filters.break_dir == "ANY"  # default
        assert filters.include_null_asia is True  # default
        assert filters.enable_atr_filter is False  # default

    def test_serialize_strategy_returns_dict(self):
        """serialize_strategy should return a dict"""
        config = default_strategy()
        result = serialize_strategy(config)
        assert isinstance(result, dict)
        assert "level_basis" in result
        assert "entry_model" in result

    def test_strategy_roundtrip(self):
        """StrategyConfig should survive serialize/deserialize roundtrip"""
        original = StrategyConfig(
            level_basis="orb_half",
            entry_model="5m_close_break",
            confirm_closes=2,
            retest_required=True,
            retest_rule="pierce_by_ticks",
            pierce_ticks=5,
            rejection_tf="5m",
            stop_rule="ORB_opposite_boundary",
            max_stop_ticks=20,
            cutoff_minutes=60,
            one_trade_per_orb=False,
        )
        serialized = serialize_strategy(original)
        restored = strategy_from_dict(serialized)

        assert restored.level_basis == original.level_basis
        assert restored.entry_model == original.entry_model
        assert restored.confirm_closes == original.confirm_closes
        assert restored.pierce_ticks == original.pierce_ticks
        assert restored.max_stop_ticks == original.max_stop_ticks

    def test_strategy_from_dict_defaults(self):
        """strategy_from_dict should use defaults for missing keys"""
        minimal_dict = {}
        config = strategy_from_dict(minimal_dict)

        assert config.level_basis == "orb_boundary"  # default
        assert config.entry_model == "1m_close_break"  # default
        assert config.confirm_closes == 1  # default


# =============================================================================
# Test _build_where_clause Function
# =============================================================================

class TestBuildWhereClause:
    """Test SQL WHERE clause generation"""

    def test_empty_filters_no_where(self):
        """Empty filters should produce no WHERE clause"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert where_sql == ""
        assert params == []

    def test_date_filters(self):
        """Date filters should produce correct WHERE conditions"""
        filters = Filters(
            start_date="2024-01-01",
            end_date="2024-12-31",
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "date_local >= ?" in where_sql
        assert "date_local <= ?" in where_sql
        assert "2024-01-01" in params
        assert "2024-12-31" in params

    def test_orb_times_filter(self):
        """ORB times filter should use IN clause"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=("0900", "1000", "1100"),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "orb_time IN (?,?,?)" in where_sql
        assert "0900" in params
        assert "1000" in params
        assert "1100" in params

    def test_break_dir_filter(self):
        """Break direction filter should work for UP/DOWN"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="UP",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "break_dir = ?" in where_sql
        assert "UP" in params

    def test_break_dir_any_ignored(self):
        """Break direction 'ANY' should not add condition"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "break_dir" not in where_sql

    def test_atr_filter_enabled(self):
        """ATR filter should add conditions when enabled"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=True,
            atr_min=10.0,
            atr_max=30.0,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "atr_20 >= ?" in where_sql
        assert "atr_20 <= ?" in where_sql
        assert 10.0 in params
        assert 30.0 in params

    def test_atr_filter_disabled_ignored(self):
        """ATR filter values should be ignored when disabled"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=10.0,
            atr_max=30.0,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "atr_20" not in where_sql

    def test_table_alias(self):
        """Table alias should be prepended to column names"""
        filters = Filters(
            start_date="2024-01-01",
            end_date=None,
            orb_times=(),
            break_dir="UP",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters, table_alias="v")
        assert "v.date_local" in where_sql
        assert "v.break_dir" in where_sql

    def test_trades_only_flag(self):
        """trades_only flag should add WIN/LOSS filter"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters, trades_only=True)
        assert "outcome IN ('WIN','LOSS')" in where_sql

    def test_asia_type_with_null_include(self):
        """Asia type filter should handle null inclusion"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code="A1_TIGHT",
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "asia_type_code = ?" in where_sql or "(asia_type_code = ? OR asia_type_code IS NULL)" in where_sql


# =============================================================================
# Test _sanitize Function
# =============================================================================

class TestSanitize:
    """Test DataFrame sanitization for JSON safety"""

    def test_sanitize_replaces_inf(self):
        """_sanitize should replace inf with None"""
        df = pd.DataFrame({"a": [1.0, np.inf, -np.inf, 2.0]})
        result = _sanitize(df)
        assert pd.isna(result["a"].iloc[1])
        assert pd.isna(result["a"].iloc[2])

    def test_sanitize_replaces_nan(self):
        """_sanitize should replace NaN with null-like value"""
        df = pd.DataFrame({"a": [1.0, np.nan, 2.0]})
        result = _sanitize(df)
        # The value should be null-like (None, NaN, or pd.NA)
        assert pd.isna(result["a"].iloc[1])

    def test_sanitize_preserves_valid_values(self):
        """_sanitize should preserve valid numeric values"""
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4, 5, 6]})
        result = _sanitize(df)
        assert result["a"].iloc[0] == 1.0
        assert result["b"].iloc[2] == 6

    def test_sanitize_empty_dataframe(self):
        """_sanitize should handle empty DataFrame"""
        df = pd.DataFrame()
        result = _sanitize(df)
        assert result.empty


# =============================================================================
# Test _required_closes Function
# =============================================================================

class TestRequiredCloses:
    """Test _required_closes calculation"""

    def test_1m_close_break_requires_1(self):
        """1m_close_break entry model requires 1 close"""
        config = StrategyConfig(
            level_basis="orb_boundary",
            entry_model="1m_close_break",
            confirm_closes=1,
            retest_required=False,
            retest_rule="touch",
            pierce_ticks=None,
            rejection_tf="1m",
            stop_rule="ORB_opposite_boundary",
            max_stop_ticks=None,
            cutoff_minutes=None,
            one_trade_per_orb=True,
        )
        assert _required_closes(config) == 1

    def test_1m_close_break_confirmed_uses_confirm_closes(self):
        """1m_close_break_confirmed uses confirm_closes field"""
        config = StrategyConfig(
            level_basis="orb_boundary",
            entry_model="1m_close_break_confirmed",
            confirm_closes=3,
            retest_required=False,
            retest_rule="touch",
            pierce_ticks=None,
            rejection_tf="1m",
            stop_rule="ORB_opposite_boundary",
            max_stop_ticks=None,
            cutoff_minutes=None,
            one_trade_per_orb=True,
        )
        assert _required_closes(config) == 3

    def test_5m_close_break_requires_1(self):
        """5m_close_break entry model requires 1 close"""
        config = StrategyConfig(
            level_basis="orb_boundary",
            entry_model="5m_close_break",
            confirm_closes=5,  # Should be ignored
            retest_required=False,
            retest_rule="touch",
            pierce_ticks=None,
            rejection_tf="1m",
            stop_rule="ORB_opposite_boundary",
            max_stop_ticks=None,
            cutoff_minutes=None,
            one_trade_per_orb=True,
        )
        assert _required_closes(config) == 1

    def test_minimum_of_1_close(self):
        """_required_closes should return at least 1"""
        config = StrategyConfig(
            level_basis="orb_boundary",
            entry_model="1m_close_break_confirmed",
            confirm_closes=0,  # Invalid but should return 1
            retest_required=False,
            retest_rule="touch",
            pierce_ticks=None,
            rejection_tf="1m",
            stop_rule="ORB_opposite_boundary",
            max_stop_ticks=None,
            cutoff_minutes=None,
            one_trade_per_orb=True,
        )
        assert _required_closes(config) >= 1


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_orb_times_tuple(self):
        """Empty orb_times should not cause errors"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "orb_time IN" not in where_sql

    def test_single_orb_time(self):
        """Single orb_time should work correctly"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=("1000",),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "orb_time IN (?)" in where_sql
        assert "1000" in params

    def test_all_orb_times(self):
        """All 6 ORB times should be handled"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=ORB_TIMES,
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=False,
            atr_min=None,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "orb_time IN (?,?,?,?,?,?)" in where_sql
        assert len([p for p in params if p in ORB_TIMES]) == 6

    def test_atr_min_only(self):
        """ATR filter with only min value"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=True,
            atr_min=10.0,
            atr_max=None,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert "atr_20 >= ?" in where_sql
        assert "atr_20 <= ?" not in where_sql

    def test_zero_atr_values(self):
        """Zero ATR values should be handled"""
        filters = Filters(
            start_date=None,
            end_date=None,
            orb_times=(),
            break_dir="ANY",
            outcomes=(),
            asia_type_code=None,
            include_null_asia=True,
            london_type_code=None,
            include_null_london=True,
            pre_ny_type_code=None,
            include_null_pre_ny=True,
            enable_atr_filter=True,
            atr_min=0.0,
            atr_max=0.0,
            enable_asia_range_filter=False,
            asia_range_min=None,
            asia_range_max=None,
        )
        where_sql, params = _build_where_clause(filters)
        assert 0.0 in params


# =============================================================================
# Test Invalid Inputs
# =============================================================================

class TestInvalidInputs:
    """Test handling of invalid inputs"""

    def test_sanitize_non_numeric_columns(self):
        """_sanitize should handle non-numeric columns"""
        df = pd.DataFrame({"a": ["x", "y", "z"], "b": [1.0, np.inf, 2.0]})
        result = _sanitize(df)
        # String column should be preserved
        assert result["a"].iloc[0] == "x"
        # Inf should be replaced
        assert pd.isna(result["b"].iloc[1])

    def test_filters_from_dict_unknown_keys_ignored(self):
        """Unknown keys in dict should be ignored"""
        payload = {
            "start_date": "2024-01-01",
            "unknown_field": "value",
            "another_unknown": 123,
        }
        filters = filters_from_dict(payload)
        assert filters.start_date == "2024-01-01"
        # Should not raise error

    def test_strategy_from_dict_type_conversion(self):
        """strategy_from_dict should convert types correctly"""
        payload = {
            "confirm_closes": "3",  # String instead of int
            "retest_required": 1,  # Int instead of bool
            "one_trade_per_orb": "yes",  # String
        }
        config = strategy_from_dict(payload)
        assert config.confirm_closes == 3
        assert config.retest_required is True
        assert config.one_trade_per_orb is True
