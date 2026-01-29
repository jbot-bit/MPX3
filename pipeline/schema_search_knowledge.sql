-- search_knowledge Table Schema
-- Stores versioned results from parameter space exploration
-- Version: 1.0 (audit3 - deterministic priority engine)

CREATE TABLE IF NOT EXISTS search_knowledge (
    -- Primary key
    knowledge_id INTEGER PRIMARY KEY,

    -- Parameter hash (unique identifier for this combination)
    param_hash VARCHAR NOT NULL UNIQUE,
    param_hash_version VARCHAR NOT NULL,  -- e.g., "2.0"

    -- Parameters (denormalized for fast queries)
    instrument VARCHAR NOT NULL,
    setup_family VARCHAR NOT NULL,
    orb_time VARCHAR NOT NULL,
    rr_target DOUBLE NOT NULL,
    filters_json JSON,

    -- Results (from validation or backtest)
    result_class VARCHAR NOT NULL,  -- "GOOD" | "NEUTRAL" | "BAD"
    expectancy_r DOUBLE,
    sample_size INTEGER,
    robust_flags INTEGER,

    -- Versioning
    ruleset_version VARCHAR NOT NULL,   -- e.g., "1.0"
    priority_version VARCHAR NOT NULL,  -- e.g., "1.0"

    -- Provenance
    git_commit VARCHAR,
    db_path VARCHAR,
    created_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,

    -- Notes
    notes VARCHAR
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_search_knowledge_result_class
    ON search_knowledge(result_class);

CREATE INDEX IF NOT EXISTS idx_search_knowledge_orb_time
    ON search_knowledge(orb_time);

CREATE INDEX IF NOT EXISTS idx_search_knowledge_rr_target
    ON search_knowledge(rr_target);

CREATE INDEX IF NOT EXISTS idx_search_knowledge_instrument
    ON search_knowledge(instrument);

CREATE INDEX IF NOT EXISTS idx_search_knowledge_setup_family
    ON search_knowledge(setup_family);

-- Composite index for priority calculation
CREATE INDEX IF NOT EXISTS idx_search_knowledge_priority
    ON search_knowledge(result_class, orb_time, rr_target);
