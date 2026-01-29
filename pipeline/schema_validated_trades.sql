-- ============================================================================
-- VALIDATED_TRADES TABLE SCHEMA
-- ============================================================================
--
-- PURPOSE: Store per-strategy tradeable results using B-entry model
--
-- ARCHITECTURE:
-- - daily_features = STRUCTURAL metrics (ORB-anchored, market structure)
-- - validated_trades = TRADEABLE metrics (entry-anchored, strategy execution)
--
-- KEY PRINCIPLES:
-- 1. One row per (date_local, setup_id) combination
-- 2. RR comes ONLY from validated_setups (via setup_id FK)
-- 3. Fail closed if RR missing in validated_setups
-- 4. No RR defaults, no hardcoded values
-- 5. Supports multiple strategies per ORB time (e.g., 1000 ORB with RR=1.5/2.0/2.5/3.0)
--
-- EXAMPLE DATA:
-- date_local  | setup_id | orb_time | rr  | outcome | realized_rr
-- 2025-01-10  | 20       | 1000     | 1.5 | WIN     | +1.238
-- 2025-01-10  | 21       | 1000     | 2.0 | WIN     | +1.643
-- 2025-01-10  | 22       | 1000     | 2.5 | WIN     | +2.048
-- 2025-01-10  | 23       | 1000     | 3.0 | WIN     | +2.453
--
-- ============================================================================

CREATE TABLE IF NOT EXISTS validated_trades (
    -- Primary Key (composite)
    date_local DATE NOT NULL,
    setup_id INTEGER NOT NULL,

    -- Foreign Key to validated_setups (source of truth for RR/sl_mode/filter)
    -- ON DELETE RESTRICT: Cannot delete setup if trades exist (data integrity)
    FOREIGN KEY (setup_id) REFERENCES validated_setups(id) ON DELETE RESTRICT,

    -- Metadata (denormalized for query performance)
    instrument VARCHAR NOT NULL,
    orb_time VARCHAR NOT NULL,

    -- B-Entry Tradeable Metrics
    entry_price DOUBLE,              -- NEXT 1m OPEN after signal close
    stop_price DOUBLE,               -- ORB edge (full) or midpoint (half)
    target_price DOUBLE,             -- entry +/- RR * risk
    exit_price DOUBLE,               -- Actual exit (if resolved)

    -- Risk/Reward (entry-anchored)
    risk_points DOUBLE,              -- |entry - stop| in price points
    target_points DOUBLE,            -- |target - entry| in price points (RR * risk)
    risk_dollars DOUBLE,             -- risk_points * point_value + friction

    -- Outcome Classification
    outcome VARCHAR,                 -- WIN, LOSS, OPEN, NO_TRADE, RISK_TOO_SMALL
    realized_rr DOUBLE,              -- Actual R-multiple after costs

    -- Excursion Metrics
    mae DOUBLE,                      -- Maximum Adverse Excursion (R)
    mfe DOUBLE,                      -- Maximum Favorable Excursion (R)

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    PRIMARY KEY (date_local, setup_id),
    CHECK (outcome IN ('WIN', 'LOSS', 'OPEN', 'NO_TRADE', 'RISK_TOO_SMALL')),
    CHECK (risk_points >= 0 OR risk_points IS NULL),
    CHECK (target_points >= 0 OR target_points IS NULL)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Query patterns:
-- 1. Validator: SELECT * FROM validated_trades WHERE setup_id = ? ORDER BY date_local
-- 2. Date range: SELECT * FROM validated_trades WHERE date_local BETWEEN ? AND ?
-- 3. Instrument: SELECT * FROM validated_trades WHERE instrument = ?
-- 4. ORB time: SELECT * FROM validated_trades WHERE orb_time = ?

CREATE INDEX IF NOT EXISTS idx_validated_trades_setup ON validated_trades(setup_id, date_local);
CREATE INDEX IF NOT EXISTS idx_validated_trades_date ON validated_trades(date_local);
CREATE INDEX IF NOT EXISTS idx_validated_trades_instrument ON validated_trades(instrument);
CREATE INDEX IF NOT EXISTS idx_validated_trades_orb ON validated_trades(orb_time);
CREATE INDEX IF NOT EXISTS idx_validated_trades_outcome ON validated_trades(outcome);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Count trades per strategy:
-- SELECT setup_id, COUNT(*) as trade_count
-- FROM validated_trades
-- GROUP BY setup_id
-- ORDER BY setup_id;

-- Compare RR values per ORB time:
-- SELECT vs.orb_time, vs.rr, COUNT(vt.date_local) as trades,
--        AVG(vt.realized_rr) as avg_realized_rr
-- FROM validated_setups vs
-- LEFT JOIN validated_trades vt ON vs.id = vt.setup_id
-- WHERE vs.instrument = 'MGC'
-- GROUP BY vs.orb_time, vs.rr
-- ORDER BY vs.orb_time, vs.rr;

-- Sample trades for strategy:
-- SELECT date_local, entry_price, outcome, realized_rr, risk_points, target_points
-- FROM validated_trades
-- WHERE setup_id = 20
-- ORDER BY date_local
-- LIMIT 10;
