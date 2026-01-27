-- MGC Trading Pipeline Database Schema
-- Created: 2026-01-26 (Phase 1: Database Rebuild)
--
-- CRITICAL: All tables have proper primary keys for upserts
--
-- Usage: python pipeline/init_db.py

-- =============================================================================
-- RAW DATA TABLES (bars)
-- =============================================================================

-- 1-minute bars (MGC continuous)
CREATE TABLE IF NOT EXISTS bars_1m (
    ts_utc TIMESTAMPTZ NOT NULL,
    symbol VARCHAR NOT NULL,
    source_symbol VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY (symbol, ts_utc)
);

-- 5-minute bars (derived from bars_1m)
CREATE TABLE IF NOT EXISTS bars_5m (
    ts_utc TIMESTAMPTZ NOT NULL,
    symbol VARCHAR NOT NULL,
    source_symbol VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY (symbol, ts_utc)
);

-- 1-minute bars (MPL continuous)
CREATE TABLE IF NOT EXISTS bars_1m_mpl (
    ts_utc TIMESTAMPTZ NOT NULL,
    symbol VARCHAR NOT NULL,
    source_symbol VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY (symbol, ts_utc)
);

-- 5-minute bars (MPL)
CREATE TABLE IF NOT EXISTS bars_5m_mpl (
    ts_utc TIMESTAMPTZ NOT NULL,
    symbol VARCHAR NOT NULL,
    source_symbol VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY (symbol, ts_utc)
);

-- 1-minute bars (NQ continuous)
CREATE TABLE IF NOT EXISTS bars_1m_nq (
    ts_utc TIMESTAMPTZ NOT NULL,
    symbol VARCHAR NOT NULL,
    source_symbol VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY (symbol, ts_utc)
);

-- 5-minute bars (NQ)
CREATE TABLE IF NOT EXISTS bars_5m_nq (
    ts_utc TIMESTAMPTZ NOT NULL,
    symbol VARCHAR NOT NULL,
    source_symbol VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY (symbol, ts_utc)
);

-- =============================================================================
-- DAILY FEATURES TABLE (MGC)
-- =============================================================================

CREATE TABLE IF NOT EXISTS daily_features (
    date_local DATE NOT NULL,
    instrument VARCHAR NOT NULL,

    -- Pre-session data
    pre_asia_high DOUBLE,
    pre_asia_low DOUBLE,
    pre_asia_range DOUBLE,
    pre_london_high DOUBLE,
    pre_london_low DOUBLE,
    pre_london_range DOUBLE,
    pre_ny_high DOUBLE,
    pre_ny_low DOUBLE,
    pre_ny_range DOUBLE,

    -- Session high/low/range
    asia_high DOUBLE,
    asia_low DOUBLE,
    asia_range DOUBLE,
    london_high DOUBLE,
    london_low DOUBLE,
    london_range DOUBLE,
    ny_high DOUBLE,
    ny_low DOUBLE,
    ny_range DOUBLE,

    -- Session classification
    asia_type_code VARCHAR,
    london_type_code VARCHAR,
    pre_ny_type_code VARCHAR,

    -- ORB 0900 (09:00-09:05)
    orb_0900_high DOUBLE,
    orb_0900_low DOUBLE,
    orb_0900_size DOUBLE,
    orb_0900_break_dir VARCHAR,
    orb_0900_outcome VARCHAR,
    orb_0900_r_multiple DOUBLE,
    orb_0900_mae DOUBLE,
    orb_0900_mfe DOUBLE,
    orb_0900_stop_price DOUBLE,
    orb_0900_risk_ticks DOUBLE,

    -- ORB 1000 (10:00-10:05)
    orb_1000_high DOUBLE,
    orb_1000_low DOUBLE,
    orb_1000_size DOUBLE,
    orb_1000_break_dir VARCHAR,
    orb_1000_outcome VARCHAR,
    orb_1000_r_multiple DOUBLE,
    orb_1000_mae DOUBLE,
    orb_1000_mfe DOUBLE,
    orb_1000_stop_price DOUBLE,
    orb_1000_risk_ticks DOUBLE,

    -- ORB 1100 (11:00-11:05)
    orb_1100_high DOUBLE,
    orb_1100_low DOUBLE,
    orb_1100_size DOUBLE,
    orb_1100_break_dir VARCHAR,
    orb_1100_outcome VARCHAR,
    orb_1100_r_multiple DOUBLE,
    orb_1100_mae DOUBLE,
    orb_1100_mfe DOUBLE,
    orb_1100_stop_price DOUBLE,
    orb_1100_risk_ticks DOUBLE,

    -- ORB 1800 (18:00-18:05)
    orb_1800_high DOUBLE,
    orb_1800_low DOUBLE,
    orb_1800_size DOUBLE,
    orb_1800_break_dir VARCHAR,
    orb_1800_outcome VARCHAR,
    orb_1800_r_multiple DOUBLE,
    orb_1800_mae DOUBLE,
    orb_1800_mfe DOUBLE,
    orb_1800_stop_price DOUBLE,
    orb_1800_risk_ticks DOUBLE,

    -- ORB 2300 (23:00-23:05)
    orb_2300_high DOUBLE,
    orb_2300_low DOUBLE,
    orb_2300_size DOUBLE,
    orb_2300_break_dir VARCHAR,
    orb_2300_outcome VARCHAR,
    orb_2300_r_multiple DOUBLE,
    orb_2300_mae DOUBLE,
    orb_2300_mfe DOUBLE,
    orb_2300_stop_price DOUBLE,
    orb_2300_risk_ticks DOUBLE,

    -- ORB 0030 (00:30-00:35, next day)
    orb_0030_high DOUBLE,
    orb_0030_low DOUBLE,
    orb_0030_size DOUBLE,
    orb_0030_break_dir VARCHAR,
    orb_0030_outcome VARCHAR,
    orb_0030_r_multiple DOUBLE,
    orb_0030_mae DOUBLE,
    orb_0030_mfe DOUBLE,
    orb_0030_stop_price DOUBLE,
    orb_0030_risk_ticks DOUBLE,

    -- Indicators
    rsi_at_0030 DOUBLE,
    rsi_at_orb DOUBLE,
    atr_20 DOUBLE,

    -- CRITICAL: Primary key for upserts
    PRIMARY KEY (date_local, instrument)
);

-- =============================================================================
-- DAILY FEATURES (MPL and NQ) - Multi-instrument support
-- =============================================================================

CREATE TABLE IF NOT EXISTS daily_features_v2_mpl (
    date_local DATE NOT NULL,
    instrument VARCHAR NOT NULL,

    -- (Same structure as daily_features)
    pre_asia_high DOUBLE,
    pre_asia_low DOUBLE,
    pre_asia_range DOUBLE,
    pre_london_high DOUBLE,
    pre_london_low DOUBLE,
    pre_london_range DOUBLE,
    pre_ny_high DOUBLE,
    pre_ny_low DOUBLE,
    pre_ny_range DOUBLE,

    asia_high DOUBLE,
    asia_low DOUBLE,
    asia_range DOUBLE,
    london_high DOUBLE,
    london_low DOUBLE,
    london_range DOUBLE,
    ny_high DOUBLE,
    ny_low DOUBLE,
    ny_range DOUBLE,

    asia_type_code VARCHAR,
    london_type_code VARCHAR,
    pre_ny_type_code VARCHAR,

    orb_0900_high DOUBLE, orb_0900_low DOUBLE, orb_0900_size DOUBLE, orb_0900_break_dir VARCHAR, orb_0900_outcome VARCHAR, orb_0900_r_multiple DOUBLE, orb_0900_mae DOUBLE, orb_0900_mfe DOUBLE, orb_0900_stop_price DOUBLE, orb_0900_risk_ticks DOUBLE,
    orb_1000_high DOUBLE, orb_1000_low DOUBLE, orb_1000_size DOUBLE, orb_1000_break_dir VARCHAR, orb_1000_outcome VARCHAR, orb_1000_r_multiple DOUBLE, orb_1000_mae DOUBLE, orb_1000_mfe DOUBLE, orb_1000_stop_price DOUBLE, orb_1000_risk_ticks DOUBLE,
    orb_1100_high DOUBLE, orb_1100_low DOUBLE, orb_1100_size DOUBLE, orb_1100_break_dir VARCHAR, orb_1100_outcome VARCHAR, orb_1100_r_multiple DOUBLE, orb_1100_mae DOUBLE, orb_1100_mfe DOUBLE, orb_1100_stop_price DOUBLE, orb_1100_risk_ticks DOUBLE,
    orb_1800_high DOUBLE, orb_1800_low DOUBLE, orb_1800_size DOUBLE, orb_1800_break_dir VARCHAR, orb_1800_outcome VARCHAR, orb_1800_r_multiple DOUBLE, orb_1800_mae DOUBLE, orb_1800_mfe DOUBLE, orb_1800_stop_price DOUBLE, orb_1800_risk_ticks DOUBLE,
    orb_2300_high DOUBLE, orb_2300_low DOUBLE, orb_2300_size DOUBLE, orb_2300_break_dir VARCHAR, orb_2300_outcome VARCHAR, orb_2300_r_multiple DOUBLE, orb_2300_mae DOUBLE, orb_2300_mfe DOUBLE, orb_2300_stop_price DOUBLE, orb_2300_risk_ticks DOUBLE,
    orb_0030_high DOUBLE, orb_0030_low DOUBLE, orb_0030_size DOUBLE, orb_0030_break_dir VARCHAR, orb_0030_outcome VARCHAR, orb_0030_r_multiple DOUBLE, orb_0030_mae DOUBLE, orb_0030_mfe DOUBLE, orb_0030_stop_price DOUBLE, orb_0030_risk_ticks DOUBLE,

    rsi_at_0030 DOUBLE,
    rsi_at_orb DOUBLE,
    atr_20 DOUBLE,

    PRIMARY KEY (date_local, instrument)
);

CREATE TABLE IF NOT EXISTS daily_features_v2_nq (
    date_local DATE NOT NULL,
    instrument VARCHAR NOT NULL,

    -- (Same structure as daily_features)
    pre_asia_high DOUBLE,
    pre_asia_low DOUBLE,
    pre_asia_range DOUBLE,
    pre_london_high DOUBLE,
    pre_london_low DOUBLE,
    pre_london_range DOUBLE,
    pre_ny_high DOUBLE,
    pre_ny_low DOUBLE,
    pre_ny_range DOUBLE,

    asia_high DOUBLE,
    asia_low DOUBLE,
    asia_range DOUBLE,
    london_high DOUBLE,
    london_low DOUBLE,
    london_range DOUBLE,
    ny_high DOUBLE,
    ny_low DOUBLE,
    ny_range DOUBLE,

    asia_type_code VARCHAR,
    london_type_code VARCHAR,
    pre_ny_type_code VARCHAR,

    orb_0900_high DOUBLE, orb_0900_low DOUBLE, orb_0900_size DOUBLE, orb_0900_break_dir VARCHAR, orb_0900_outcome VARCHAR, orb_0900_r_multiple DOUBLE, orb_0900_mae DOUBLE, orb_0900_mfe DOUBLE, orb_0900_stop_price DOUBLE, orb_0900_risk_ticks DOUBLE,
    orb_1000_high DOUBLE, orb_1000_low DOUBLE, orb_1000_size DOUBLE, orb_1000_break_dir VARCHAR, orb_1000_outcome VARCHAR, orb_1000_r_multiple DOUBLE, orb_1000_mae DOUBLE, orb_1000_mfe DOUBLE, orb_1000_stop_price DOUBLE, orb_1000_risk_ticks DOUBLE,
    orb_1100_high DOUBLE, orb_1100_low DOUBLE, orb_1100_size DOUBLE, orb_1100_break_dir VARCHAR, orb_1100_outcome VARCHAR, orb_1100_r_multiple DOUBLE, orb_1100_mae DOUBLE, orb_1100_mfe DOUBLE, orb_1100_stop_price DOUBLE, orb_1100_risk_ticks DOUBLE,
    orb_1800_high DOUBLE, orb_1800_low DOUBLE, orb_1800_size DOUBLE, orb_1800_break_dir VARCHAR, orb_1800_outcome VARCHAR, orb_1800_r_multiple DOUBLE, orb_1800_mae DOUBLE, orb_1800_mfe DOUBLE, orb_1800_stop_price DOUBLE, orb_1800_risk_ticks DOUBLE,
    orb_2300_high DOUBLE, orb_2300_low DOUBLE, orb_2300_size DOUBLE, orb_2300_break_dir VARCHAR, orb_2300_outcome VARCHAR, orb_2300_r_multiple DOUBLE, orb_2300_mae DOUBLE, orb_2300_mfe DOUBLE, orb_2300_stop_price DOUBLE, orb_2300_risk_ticks DOUBLE,
    orb_0030_high DOUBLE, orb_0030_low DOUBLE, orb_0030_size DOUBLE, orb_0030_break_dir VARCHAR, orb_0030_outcome VARCHAR, orb_0030_r_multiple DOUBLE, orb_0030_mae DOUBLE, orb_0030_mfe DOUBLE, orb_0030_stop_price DOUBLE, orb_0030_risk_ticks DOUBLE,

    rsi_at_0030 DOUBLE,
    rsi_at_orb DOUBLE,
    atr_20 DOUBLE,

    PRIMARY KEY (date_local, instrument)
);

-- =============================================================================
-- VALIDATED SETUPS (shared across instruments)
-- =============================================================================

CREATE TABLE IF NOT EXISTS validated_setups (
    id INTEGER PRIMARY KEY,
    instrument VARCHAR NOT NULL,
    orb_time VARCHAR NOT NULL,
    rr DOUBLE NOT NULL,
    sl_mode VARCHAR NOT NULL,
    orb_size_filter DOUBLE,  -- NULL or threshold (e.g., 0.05 for >5% ORB size)
    win_rate DOUBLE NOT NULL,
    expected_r DOUBLE NOT NULL,  -- Canonical R (ORB-edge anchored)
    real_expected_r DOUBLE,  -- Real R (entry-to-stop with slippage), NULL if not computed
    sample_size INTEGER NOT NULL,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(instrument, orb_time, rr, sl_mode)
);

-- =============================================================================
-- PROP FIRM ACCOUNT CONFIGURATION
-- =============================================================================

-- Account configuration (Personal Capital vs Prop Firm)
-- Supports: Personal, Topstep Express, My Funded Futures (MFFU)
-- Reference: propfirm.txt, fix.txt
CREATE TABLE IF NOT EXISTS account_config (
    id INTEGER PRIMARY KEY,
    account_name VARCHAR NOT NULL,  -- User-friendly name (e.g., "My Topstep 50K")
    account_type VARCHAR NOT NULL,  -- Personal, Topstep, MFFU
    plan_type VARCHAR NOT NULL,     -- Static, Trailing_Intraday, Trailing_EOD

    -- Capital and limits
    starting_balance DOUBLE NOT NULL,           -- e.g., $50,000
    max_drawdown_size DOUBLE NOT NULL,          -- e.g., $2,000
    daily_loss_limit DOUBLE,                    -- NULL for MFFU, set for Topstep

    -- Real-time tracking
    current_balance DOUBLE NOT NULL,            -- Closed trade balance
    high_water_mark DOUBLE NOT NULL,            -- Highest recorded equity
    previous_close_balance DOUBLE,              -- For EOD plans

    -- Prop firm specific
    benchmark_days_completed INTEGER DEFAULT 0,         -- Topstep: days with >= $150 profit
    consistency_ratio DOUBLE,                           -- MFFU: max_day_profit / total_profit
    contract_limit_mini INTEGER,                        -- MFFU position limits
    contract_limit_micro INTEGER,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_evaluation BOOLEAN DEFAULT FALSE,                -- MFFU: true during eval phase
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CHECK (account_type IN ('Personal', 'Topstep', 'MFFU')),
    CHECK (plan_type IN ('Static', 'Trailing_Intraday', 'Trailing_EOD')),
    CHECK (starting_balance > 0),
    CHECK (max_drawdown_size > 0),
    CHECK (high_water_mark >= starting_balance)
);

-- Daily P&L tracking (for consistency rules and benchmark days)
CREATE TABLE IF NOT EXISTS daily_pnl_tracking (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    date_local DATE NOT NULL,
    realized_pnl DOUBLE NOT NULL,
    unrealized_pnl_peak DOUBLE,         -- Highest unrealized during day
    is_benchmark_day BOOLEAN DEFAULT FALSE,  -- Topstep: >= $150 profit
    violates_consistency BOOLEAN DEFAULT FALSE,  -- MFFU: day_profit > 50% total
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (account_id) REFERENCES account_config(id),
    UNIQUE (account_id, date_local)
);

-- =============================================================================
-- INDEXES for performance
-- =============================================================================

-- Index on date for fast date-range queries
CREATE INDEX IF NOT EXISTS idx_daily_features_date ON daily_features(date_local);
CREATE INDEX IF NOT EXISTS idx_bars_1m_date ON bars_1m(ts_utc);
CREATE INDEX IF NOT EXISTS idx_bars_5m_date ON bars_5m(ts_utc);

-- Index on instrument for multi-instrument queries
CREATE INDEX IF NOT EXISTS idx_validated_setups_instrument ON validated_setups(instrument);

-- Indexes for account tracking
CREATE INDEX IF NOT EXISTS idx_account_config_active ON account_config(is_active);
CREATE INDEX IF NOT EXISTS idx_daily_pnl_account ON daily_pnl_tracking(account_id);
CREATE INDEX IF NOT EXISTS idx_daily_pnl_date ON daily_pnl_tracking(date_local);

-- =============================================================================
-- DONE
-- =============================================================================
