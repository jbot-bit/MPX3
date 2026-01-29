-- EXPERIMENTAL STRATEGIES TABLE
-- Stores rare/complex edges that auto-alert when conditions match
-- Separate from validated_setups to avoid unique constraint conflicts

CREATE TABLE IF NOT EXISTS experimental_strategies (
    id INTEGER PRIMARY KEY,
    instrument VARCHAR NOT NULL,
    orb_time VARCHAR NOT NULL,
    rr DOUBLE NOT NULL,
    sl_mode VARCHAR NOT NULL,

    -- Filter conditions (store as JSON or separate columns)
    filter_type VARCHAR NOT NULL,  -- 'DAY_OF_WEEK', 'COMBINED', 'SESSION_CONTEXT'
    filter_condition VARCHAR NOT NULL,  -- Human-readable condition
    filter_sql VARCHAR,  -- SQL condition for evaluation

    -- Filter parameters (for programmatic checking)
    day_of_week VARCHAR,  -- 'Monday', 'Tuesday', etc.
    orb_size_max DOUBLE,  -- Max ORB size ratio
    prev_asia_range_min DOUBLE,  -- Min previous Asia range ratio
    prev_asia_range_max DOUBLE,  -- Max previous Asia range ratio

    -- Performance metrics
    win_rate DOUBLE NOT NULL,
    expected_r DOUBLE NOT NULL,
    realized_expectancy DOUBLE,
    avg_win_r DOUBLE,
    avg_loss_r DOUBLE,
    sample_size INTEGER NOT NULL,

    -- Frequency
    annual_frequency DOUBLE,  -- Estimated trades per year

    -- Status
    status VARCHAR DEFAULT 'ACTIVE',  -- 'ACTIVE', 'TESTING', 'FAILED'
    priority INTEGER DEFAULT 2,  -- 1=high, 2=medium, 3=low

    -- Metadata
    notes VARCHAR,
    discovered_date DATE DEFAULT CURRENT_DATE,
    last_occurred_date DATE,
    total_occurrences INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint on strategy + filter combination
    UNIQUE(instrument, orb_time, rr, sl_mode, filter_type, day_of_week, orb_size_max)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_exp_strat_active ON experimental_strategies(instrument, status)
    WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_exp_strat_day ON experimental_strategies(day_of_week)
    WHERE day_of_week IS NOT NULL;
