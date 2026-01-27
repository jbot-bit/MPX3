"""
Initialize Trading Memory Tables

Creates 4 memory tables in gold.db:
1. trade_journal - Episodic memory (specific trades with full context)
2. learned_patterns - Semantic memory (patterns/correlations discovered)
3. session_state - Working memory (current session tracking)
4. execution_metrics - Procedural memory (execution quality tracking)

Usage:
    python pipeline/init_memory_tables.py
"""

import duckdb
from pathlib import Path

DB_PATH = "data/db/gold.db"

def init_memory_tables():
    """Create all memory tables"""

    print(f"\n{'='*70}")
    print("INITIALIZING TRADING MEMORY TABLES")
    print(f"{'='*70}\n")

    conn = duckdb.connect(DB_PATH)

    # 1. EPISODIC MEMORY: trade_journal
    print("[1/4] Creating trade_journal (episodic memory)...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY,
            date_local DATE NOT NULL,
            orb_time TEXT NOT NULL,
            instrument TEXT NOT NULL,
            setup_id TEXT,
            entry_price REAL,
            exit_price REAL,
            outcome TEXT,  -- 'WIN', 'LOSS', 'SKIP', 'BREAKEVEN'
            r_multiple REAL,
            mae REAL,  -- Maximum Adverse Excursion
            mfe REAL,  -- Maximum Favorable Excursion

            -- Session context (captured at trade time)
            asia_travel REAL,
            london_reversals INTEGER,
            pre_orb_travel REAL,
            liquidity_state TEXT,  -- 'normal', 'thin', 'holiday', 'rollover'
            contract_days_to_roll INTEGER,

            -- Context narrative
            session_context TEXT,  -- JSON blob: full session state
            lesson_learned TEXT,   -- Post-trade insight
            notable BOOLEAN DEFAULT FALSE,  -- Flag exceptional events

            -- Execution data
            theoretical_entry REAL,
            actual_entry REAL,
            slippage REAL,
            fill_time_ms INTEGER,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_journal_date ON trade_journal(date_local);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_journal_instrument ON trade_journal(instrument, orb_time);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_journal_outcome ON trade_journal(outcome);")
    # Note: Partial indexes not supported in DuckDB, so index all notable rows
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_journal_notable ON trade_journal(notable);")
    print("  [OK] trade_journal created")

    # 2. SEMANTIC MEMORY: learned_patterns
    print("[2/4] Creating learned_patterns (semantic memory)...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learned_patterns (
            pattern_id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            hypothesis TEXT,

            -- Pattern definition
            condition_sql TEXT,  -- SQL WHERE clause to identify pattern
            instruments TEXT,    -- Comma-separated: 'MGC,NQ,MPL' or 'ALL'

            -- Performance metrics
            confidence REAL,     -- 0.0 to 1.0
            sample_size INTEGER,
            win_rate REAL,
            avg_rr REAL,
            total_r REAL,

            -- Lifecycle tracking
            discovered_date DATE,
            last_validated DATE,
            status TEXT,  -- 'active', 'testing', 'degraded', 'invalidated'

            -- Supporting evidence
            example_trades TEXT,  -- JSON array of trade_journal IDs

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_learned_patterns_status ON learned_patterns(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_learned_patterns_confidence ON learned_patterns(confidence);")
    print("  [OK] learned_patterns created")

    # 3. WORKING MEMORY: session_state
    print("[3/4] Creating session_state (working memory)...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_state (
            date_local DATE PRIMARY KEY,
            instrument TEXT DEFAULT 'MGC',

            -- Session metrics (updated throughout day)
            asia_high REAL,
            asia_low REAL,
            asia_travel REAL,
            london_high REAL,
            london_low REAL,
            london_reversals INTEGER DEFAULT 0,
            ny_high REAL,
            ny_low REAL,

            -- Pre-ORB metrics
            pre_orb_0900_travel REAL,
            pre_orb_1000_travel REAL,
            pre_orb_1100_travel REAL,

            -- Market conditions
            liquidity_state TEXT,
            contract_days_to_roll INTEGER,
            notable_conditions TEXT,  -- JSON array: ['holiday_week', 'earnings', 'fed_day']

            -- Performance tracking
            recent_orb_outcomes TEXT,  -- JSON array: last 5 days outcomes

            -- Regime classification
            regime TEXT,  -- 'trending', 'range_bound', 'volatile', 'quiet'
            regime_confidence REAL,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("  [OK] session_state created")

    # 4. PROCEDURAL MEMORY: execution_metrics
    print("[4/4] Creating execution_metrics (procedural memory)...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_metrics (
            id INTEGER PRIMARY KEY,
            date_local DATE NOT NULL,
            orb_time TEXT NOT NULL,
            instrument TEXT NOT NULL,

            -- Execution quality
            theoretical_entry REAL,
            actual_entry REAL,
            slippage REAL,
            fill_time_ms INTEGER,

            -- Context
            market_condition TEXT,  -- 'fast', 'normal', 'slow', 'thin'

            -- Classification
            execution_quality TEXT,  -- 'excellent', 'good', 'acceptable', 'poor', 'failed'

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_metrics_date ON execution_metrics(date_local);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_metrics_quality ON execution_metrics(execution_quality);")
    print("  [OK] execution_metrics created")

    conn.close()

    print(f"\n{'='*70}")
    print("[OK] ALL MEMORY TABLES CREATED")
    print(f"{'='*70}\n")
    print("Database: data/db/gold.db")
    print("\nTables created:")
    print("  1. trade_journal       - Episodic memory (specific trades)")
    print("  2. learned_patterns    - Semantic memory (patterns/correlations)")
    print("  3. session_state       - Working memory (current session)")
    print("  4. execution_metrics   - Procedural memory (execution quality)")
    print("\nYou can now use trading_app/memory.py to interact with these tables.")
    print()

if __name__ == "__main__":
    init_memory_tables()
