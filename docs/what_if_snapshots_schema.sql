-- What-If Analyzer Snapshot Storage
-- Stores immutable snapshots of What-If analysis results
-- for reproducibility and auditability

CREATE TABLE IF NOT EXISTS what_if_snapshots (
    -- Identity
    snapshot_id TEXT PRIMARY KEY,  -- UUID
    cache_key TEXT NOT NULL,  -- From engine (deterministic)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Setup definition
    instrument TEXT NOT NULL,
    orb_time TEXT NOT NULL,  -- '0900', '1000', etc.
    direction TEXT NOT NULL,  -- 'UP', 'DOWN', 'BOTH'
    rr DOUBLE NOT NULL,
    sl_mode TEXT NOT NULL,  -- 'FULL' or 'HALF'

    -- Condition definition (JSON)
    conditions JSON NOT NULL,  -- Full ConditionSet

    -- Date range
    date_start DATE,  -- NULL = all dates
    date_end DATE,

    -- Baseline metrics
    baseline_sample_size INTEGER NOT NULL,
    baseline_win_rate DOUBLE NOT NULL,
    baseline_expected_r DOUBLE NOT NULL,
    baseline_avg_win DOUBLE NOT NULL,
    baseline_avg_loss DOUBLE NOT NULL,
    baseline_max_dd DOUBLE NOT NULL,
    baseline_sharpe_ratio DOUBLE NOT NULL,
    baseline_total_r DOUBLE NOT NULL,
    baseline_stress_25_exp_r DOUBLE NOT NULL,
    baseline_stress_50_exp_r DOUBLE NOT NULL,
    baseline_stress_25_pass BOOLEAN NOT NULL,
    baseline_stress_50_pass BOOLEAN NOT NULL,

    -- Conditional metrics (with conditions applied)
    conditional_sample_size INTEGER NOT NULL,
    conditional_win_rate DOUBLE NOT NULL,
    conditional_expected_r DOUBLE NOT NULL,
    conditional_avg_win DOUBLE NOT NULL,
    conditional_avg_loss DOUBLE NOT NULL,
    conditional_max_dd DOUBLE NOT NULL,
    conditional_sharpe_ratio DOUBLE NOT NULL,
    conditional_total_r DOUBLE NOT NULL,
    conditional_stress_25_exp_r DOUBLE NOT NULL,
    conditional_stress_50_exp_r DOUBLE NOT NULL,
    conditional_stress_25_pass BOOLEAN NOT NULL,
    conditional_stress_50_pass BOOLEAN NOT NULL,

    -- Non-matched metrics (excluded by conditions)
    non_matched_sample_size INTEGER NOT NULL,
    non_matched_win_rate DOUBLE NOT NULL,
    non_matched_expected_r DOUBLE NOT NULL,

    -- Delta metrics
    delta_sample_size INTEGER NOT NULL,
    delta_win_rate_pct DOUBLE NOT NULL,
    delta_expected_r DOUBLE NOT NULL,
    delta_avg_win DOUBLE NOT NULL,
    delta_avg_loss DOUBLE NOT NULL,
    delta_max_dd DOUBLE NOT NULL,
    delta_sharpe_ratio DOUBLE NOT NULL,
    delta_total_r DOUBLE NOT NULL,

    -- Data versioning (for reproducibility)
    data_version TEXT,  -- E.g., 'daily_features_2026-01-28'
    engine_version TEXT NOT NULL DEFAULT 'v1',  -- What-If engine version

    -- Metadata
    notes TEXT,  -- User notes
    promoted_to_candidate BOOLEAN DEFAULT FALSE,  -- Promoted to validation?
    candidate_edge_id TEXT,  -- Reference to edge_registry if promoted

    -- Audit
    created_by TEXT  -- User or system that created snapshot
);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_what_if_snapshots_instrument_orb
    ON what_if_snapshots(instrument, orb_time);

CREATE INDEX IF NOT EXISTS idx_what_if_snapshots_cache_key
    ON what_if_snapshots(cache_key);

CREATE INDEX IF NOT EXISTS idx_what_if_snapshots_created_at
    ON what_if_snapshots(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_what_if_snapshots_promoted
    ON what_if_snapshots(promoted_to_candidate, candidate_edge_id);

-- Comments
COMMENT ON TABLE what_if_snapshots IS 'Immutable snapshots of What-If Analyzer results for reproducibility';
COMMENT ON COLUMN what_if_snapshots.cache_key IS 'Deterministic cache key (setup + conditions + dates + version)';
COMMENT ON COLUMN what_if_snapshots.conditions IS 'Full ConditionSet as JSON (orb_size_min, asia_travel_max, etc.)';
COMMENT ON COLUMN what_if_snapshots.data_version IS 'Snapshot of data state for re-evaluation';
COMMENT ON COLUMN what_if_snapshots.promoted_to_candidate IS 'TRUE if this snapshot was promoted to edge_registry for validation';
