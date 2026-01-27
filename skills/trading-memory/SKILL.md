---
name: trading-memory
description: Maintains living memory of trading patterns, session contexts, and learned insights. Use when analyzing trade outcomes, querying historical patterns, learning from execution, or understanding why setups work/fail. Stores episodic (specific trades), semantic (patterns/correlations), working (current session), and procedural (execution skills) memory.
allowed-tools: Read, Bash(python:*, duckdb:*), Grep, Glob
context: fork
agent: general-purpose
---

# Trading Memory Skill

**Institutional-grade living memory system for adaptive trading intelligence.**

This skill maintains contextual memory of your trading activity, learns patterns from outcomes, and provides intelligent insights based on historical experience. Unlike static rule engines, this creates an AI trading partner that remembers, learns, and evolves.

---

## Memory Architecture

### 1. Episodic Memory (Specific Events)
**Table: `trade_journal`**

Stores individual trades with complete session context.

```sql
-- Schema (to be added to gold.db)
CREATE TABLE IF NOT EXISTS trade_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

CREATE INDEX idx_trade_journal_date ON trade_journal(date_local);
CREATE INDEX idx_trade_journal_instrument ON trade_journal(instrument, orb_time);
CREATE INDEX idx_trade_journal_outcome ON trade_journal(outcome);
CREATE INDEX idx_trade_journal_notable ON trade_journal(notable) WHERE notable = TRUE;
```

**What it remembers:**
- "2025-12-18: 0900 ORB failed despite perfect setup - Asia had false breakout pattern (lesson: check Asia quality)"
- "2026-01-15: 1100 ORB massive 3.2R winner - low volatility morning → explosive NY open"
- "Contract rollover March 2025: Spread widened 3 days before roll, avoid trading in rollover window"

### 2. Semantic Memory (Conceptual Understanding)
**Table: `learned_patterns`**

Learns relationships, correlations, and causality.

```sql
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

CREATE INDEX idx_learned_patterns_status ON learned_patterns(status);
CREATE INDEX idx_learned_patterns_confidence ON learned_patterns(confidence);
```

**Examples of learned patterns:**

```python
{
    "pattern_id": "asia_high_travel_london_quiet_ny_explosive",
    "description": "When Asia travel > 2.0 AND London shows < 3 reversals, NY session tends to produce explosive ORB breaks",
    "hypothesis": "High Asia travel = energy buildup, quiet London = coiling, NY releases the spring",
    "condition_sql": "asia_travel > 2.0 AND london_reversals < 3",
    "confidence": 0.82,
    "sample_size": 67,
    "win_rate": 68.5,
    "avg_rr": 1.4,
    "status": "active"
}

{
    "pattern_id": "thursday_0900_orb_degraded_q4_2025",
    "description": "0900 ORB on Thursdays stopped working in Q4 2025",
    "hypothesis": "Institutional order flow changed (possibly large fund rebalancing on Thursdays)",
    "confidence": 0.71,
    "sample_size": 42,
    "status": "degraded"
}

{
    "pattern_id": "mpl_mgc_correlation_1100",
    "description": "When MPL moves > 3.0 points in Asia session, MGC 1100 ORB has 15% higher win rate",
    "hypothesis": "Metals correlation - strong MPL signals institutional precious metals positioning",
    "confidence": 0.76,
    "sample_size": 54,
    "avg_rr": 1.3,
    "status": "active"
}
```

### 3. Working Memory (Real-Time Context)
**Table: `session_state`**

Tracks current session as it unfolds.

```sql
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
```

**What it tracks:**
- How today is unfolding (choppy? trending? quiet?)
- Whether current conditions match historical patterns where edges work
- Unusual factors (low liquidity, holiday week, contract roll approaching)
- Your recent performance (3 losses in a row? Suggest caution)

### 4. Procedural Memory (Execution Skills)
**Table: `execution_metrics`**

Learns from your actual execution.

```sql
CREATE TABLE IF NOT EXISTS execution_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER REFERENCES trade_journal(id),

    -- Execution quality
    theoretical_entry REAL,
    actual_entry REAL,
    slippage REAL,
    slippage_pct REAL,
    fill_time_ms INTEGER,

    -- Market conditions at execution
    market_conditions TEXT,  -- 'fast', 'normal', 'thin', 'volatile'
    session TEXT,  -- 'asia', 'london', 'ny'

    -- Psychological state
    psychological_state TEXT,  -- 'confident', 'cautious', 'tilted', 'fatigued'
    recent_pnl REAL,  -- P&L in last 5 trades

    -- Performance categorization
    execution_quality TEXT,  -- 'excellent', 'good', 'acceptable', 'poor'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_execution_metrics_quality ON execution_metrics(execution_quality);
CREATE INDEX idx_execution_metrics_conditions ON execution_metrics(market_conditions);
```

**What it learns:**
- Your typical slippage in different market conditions (fast: 0.3, normal: 0.1, thin: 0.5)
- Best execution timing (first 5min after ORB break = lowest slippage)
- Psychological patterns:
  - Tend to exit early after 3 consecutive losses
  - Overconfident after big win (take too much risk)
  - Best performance in morning session (fatigue impacts afternoon trades)

---

## Core Functions

### Function 1: Store Trade with Context

When a trade completes, store full context:

```python
# Example invocation
# /trading-memory store "Date: 2026-01-25, ORB: 0900, Instrument: MGC, Outcome: WIN, R: 1.2, Entry: 2654.4, Exit: 2655.8, Asia travel: 2.3, London reversals: 2, Liquidity: normal, Slippage: 0.1"
```

**Process:**
1. Parse trade data
2. Query daily_features_v2 for session context (Asia travel, London stats, etc.)
3. Calculate execution metrics (slippage, fill quality)
4. Insert into trade_journal
5. Update session_state with latest performance
6. Check if trade validates/invalidates any learned_patterns

### Function 2: Query Similar Sessions

Find historical sessions matching current conditions:

```python
# Example invocation
# /trading-memory query "Asia travel > 2.0, London choppy, liquidity normal, what's the expected win rate for 0900 ORB?"
```

**Process:**
1. Parse current conditions
2. Query trade_journal with matching context
3. Calculate aggregate statistics (win rate, avg R, sample size)
4. Return confidence-weighted results
5. Include specific examples (episodic memory)

**Example output:**
```
Query: Asia travel > 2.0, London choppy (>4 reversals), 0900 ORB

Found 34 matching historical sessions:
- Win Rate: 38.2% (below validated edge of 62%)
- Avg R: +0.15R (below threshold)
- Sample confidence: MEDIUM (34 trades)

Pattern match: "asia_high_travel_london_choppy_0900_fail" (71% confidence)
- This pattern emerged in Q4 2025
- Hypothesis: Institutional flow change

RECOMMENDATION: SKIP 0900 ORB
ALTERNATIVE: Wait for 1000 ORB (72% WR in these conditions, 28 trades)

Example trades:
- 2025-12-03: LOSS (-1.0R) - similar conditions
- 2025-11-21: LOSS (-1.0R) - asia_travel=2.4, london_reversals=5
- 2025-10-15: WIN (+1.0R) - outlier (post-breakout continuation)
```

### Function 3: Learn Pattern

Discover and validate new patterns from trade history:

```python
# Example invocation (typically called weekly or after significant data accumulation)
# /trading-memory learn-patterns
```

**Process:**
1. Scan trade_journal for correlations:
   - Session characteristics → outcomes
   - Multi-instrument correlations (MPL/MGC, NQ/MGC)
   - Time-based patterns (day of week, time of day)
   - Execution patterns (slippage → outcome)
2. Calculate confidence scores (chi-square test, confidence intervals)
3. Filter for statistical significance (min 30 trades, p < 0.05)
4. Insert new patterns into learned_patterns
5. Flag existing patterns as "degraded" if performance dropped

**Example discovered pattern:**
```
NEW PATTERN DISCOVERED!

Pattern: "nq_strong_mgc_weak_asia_divergence"
Description: When NQ shows strong Asia breakout (>1%) but MGC is flat (<0.5%), MGC 0900 ORB fails 72% of time
Sample: 41 trades
Confidence: 0.78
Win Rate: 28% (vs 62% baseline)
Avg R: -0.3R

Hypothesis: Index strength without metals confirmation = false signal for gold

RECOMMENDATION: Add to filter logic - skip 0900 ORB when this divergence occurs
```

### Function 4: Track Edge Degradation

Monitor validated_setups performance over time:

```python
# Example invocation (weekly or on-demand)
# /trading-memory check-edge-health
```

**Process:**
1. For each setup in validated_setups:
   - Query trade_journal for recent performance (last 30/60/90 days)
   - Compare to historical baseline (from daily_features_v2)
   - Calculate performance drift
2. Flag edges with >10% win rate degradation
3. Update learned_patterns status if edge has degraded
4. Generate alerts for review

**Example output:**
```
EDGE HEALTH REPORT
==================

🚨 DEGRADED EDGE DETECTED:

Setup: MGC 0900 ORB (RR=8.0)
Baseline Win Rate: 62.5% (150 trades, 2024-2025)
Recent Win Rate (90 days): 48.2% (22 trades)
Degradation: -14.3% (CRITICAL)

Analysis:
- Degradation started: October 2025
- Pattern identified: "thursday_0900_degraded" (71% confidence)
- Hypothesis: Institutional order flow changed

RECOMMENDATION: Reduce position size or skip 0900 ORB until edge stabilizes
INVESTIGATE: Run edge discovery with updated filters


✅ HEALTHY EDGES:

Setup: MGC 1100 ORB (RR=8.0)
Recent WR: 64.1% (stable, +1.6% vs baseline)
Sample: 31 trades (90 days)
Status: ACTIVE

Setup: MGC 2300 ORB (RR=2.5)
Recent WR: 58.3% (stable, -2.2% vs baseline)
Sample: 18 trades (90 days)
Status: ACTIVE
```

### Function 5: Analyze Current Session

Real-time intelligence for today's trading:

```python
# Example invocation (during trading session)
# /trading-memory analyze-today
```

**Process:**
1. Query session_state for today's metrics
2. Compare to learned_patterns
3. Query trade_journal for similar historical days
4. Calculate expected performance for upcoming ORBs
5. Provide actionable recommendations

**Example output:**
```
SESSION ANALYSIS: 2026-01-25
==============================

Current Conditions:
- Asia travel: 2.7 (HIGH - above 75th percentile)
- London reversals: 2 (LOW - quiet session)
- Pre-0900 travel: 0.8 (normal)
- Liquidity: normal
- Contract days to roll: 12 (safe zone)

Pattern Matches:
✅ "asia_high_travel_london_quiet" (82% confidence, 67 trades)
   → Indicates strong NY session potential
   → Expected ORB performance: +15% WR boost

❌ "recent_losses_psychological" (YOUR last 2 trades were losses)
   → Historical data shows you tend to exit early after losses
   → Recommendation: Hold winners to full target today

Historical Similar Days (top 5):
1. 2025-12-18: 0900 ORB WIN (+1.2R) - very similar conditions
2. 2025-11-04: 1100 ORB WIN (+8.0R) - explosive NY session
3. 2025-10-22: 0900 ORB WIN (+1.0R) - asia_travel=2.8, london_quiet
4. 2025-09-15: 1000 ORB WIN (+2.5R) - similar pattern
5. 2025-08-11: 0900 ORB LOSS (-1.0R) - outlier (news event)

UPCOMING ORBS:

0900 ORB (15 minutes):
- Expected WR: 74% (baseline 62% + pattern boost)
- Confidence: HIGH (pattern match + historical precedent)
- Risk factors: Your recent losses (psychological caution)
- RECOMMENDATION: TAKE TRADE (high confidence setup)

1100 ORB (3 hours 15 minutes):
- Expected WR: 72% (benefits from asia_high_travel pattern)
- Confidence: VERY HIGH (best pattern match historically)
- RECOMMENDATION: PRIMARY SETUP - prepare for explosive move
```

---

## Integration with Existing System

### Uses Existing Tables:
- `daily_features_v2` - Historical session data, ORB outcomes
- `validated_setups` - Baseline edges for comparison
- `bars_1m`, `bars_5m` - Intraday price action analysis

### New Tables Required:
- `trade_journal` - Episodic memory
- `learned_patterns` - Semantic memory
- `session_state` - Working memory
- `execution_metrics` - Procedural memory

### Database Setup:

```bash
# Initialize trading memory tables
python scripts/init_trading_memory.py
```

---

## Use Cases

### Use Case 1: Post-Trade Analysis
After each trade, store outcome with context to build memory:

```
User: "I took 0900 ORB today, entered at 2654.4, exited at 2655.8 for +1.2R win"

Claude (uses trading-memory skill):
- Queries daily_features_v2 for session context
- Stores trade in trade_journal
- Checks if this validates any patterns
- Provides insight: "This trade validates the 'asia_high_travel' pattern (confidence now 83%)"
```

### Use Case 2: Pre-Trade Intelligence
Before taking a trade, query memory for similar conditions:

```
User: "Should I take 0900 ORB today?"

Claude (uses trading-memory skill):
- Analyzes current session_state
- Queries learned_patterns for matches
- Searches trade_journal for similar days
- Returns confidence-weighted recommendation with specific examples
```

### Use Case 3: Edge Discovery Enhancement
Discover new filters from execution data:

```
User: "Run pattern discovery"

Claude (uses trading-memory skill):
- Scans trade_journal for correlations
- Tests hypotheses (session flow, cross-instrument, psychological)
- Calculates statistical confidence
- Creates new learned_patterns
- Suggests filter additions to edge_discovery_live.py
```

### Use Case 4: Psychological Awareness
Track execution quality and psychological patterns:

```
User: "How's my execution quality lately?"

Claude (uses trading-memory skill):
- Queries execution_metrics for recent trades
- Identifies patterns: "After losses, your slippage increases 40% (likely rushing entries)"
- Provides awareness: "You're on a 2-loss streak - historical data shows you exit early in this state"
- Suggests: "Today's setup is high confidence - trust your system and hold to target"
```

---

## Weekly Maintenance Tasks

### 1. Pattern Validation (Weekly)
```bash
/trading-memory validate-patterns
```
- Checks each learned_pattern against recent data
- Updates confidence scores
- Flags degraded patterns
- Archives invalidated patterns

### 2. Edge Health Check (Weekly)
```bash
/trading-memory check-edge-health
```
- Compares validated_setups performance to baseline
- Alerts on degradation
- Suggests edge discovery with new filters

### 3. Execution Analysis (Monthly)
```bash
/trading-memory analyze-execution
```
- Summarizes slippage trends
- Identifies optimal execution windows
- Flags psychological patterns
- Provides improvement recommendations

---

## Success Metrics

**This skill is working if:**
- Memory captures context for 100% of trades
- Pattern discovery finds 2+ new edges per quarter
- Edge degradation detected 30+ days before critical failure
- Pre-trade queries provide actionable intelligence (75%+ accuracy)
- Execution quality improves over time (slippage reduction)
- Psychological awareness prevents tilted trading

**Red flags:**
- Patterns never trigger or have <50% accuracy
- Edge degradation not detected until major loss
- Session analysis provides generic advice (not using memory)
- Database queries slow (>1 second)
- Memory tables not growing (trades not being stored)

---

## Technical Notes

**Performance:**
- All queries use indexed columns (sub-100ms latency)
- session_state updates throughout day (not just EOD)
- learned_patterns cached in memory for fast lookup
- trade_journal grows ~500-1000 rows/year (manageable)

**Data Quality:**
- Session context auto-populated from daily_features_v2 (no manual entry)
- Execution metrics captured from actual fills (not theoretical)
- Patterns validated with statistical tests (chi-square, confidence intervals)
- Regular pruning of low-confidence patterns (quarterly)

**Security:**
- Trade data never leaves local database
- No cloud sync (institutional data privacy)
- Patterns are statistical, not strategy rules (don't expose edge logic)

---

## Example Workflow: Living Memory in Action

**Monday Morning:**
```
User: "Analyze today's session"

Claude:
Checking session_state for 2026-01-27...
- Asia travel: 1.9 (normal)
- London reversals: 4 (choppy)
- Liquidity: normal

Querying learned_patterns...
⚠️ Pattern match: "london_choppy_0900_underperform" (68% confidence, 45 trades)
- When London shows >4 reversals, 0900 ORB WR drops to 52% (vs 62% baseline)

Checking recent performance...
- Last 3 trades: WIN, LOSS, LOSS (2-trade losing streak)
- Execution_metrics shows: You tend to cut winners early after losses

RECOMMENDATION for 0900 ORB:
- Edge is MARGINAL today (52% WR, below optimal)
- Psychological state: CAUTION (recent losses)
- SUGGEST: Skip 0900, wait for 1000 ORB (better conditions expected)

Alternative: 1100 ORB historically performs better when London is choppy (64% WR, 38 trades)
```

**After trade:**
```
User: "Took 1100 ORB, entered 2655.1, exited 2663.1 for +8.0R"

Claude:
Excellent execution! Storing trade in memory...

Trade stored:
- Date: 2026-01-27
- ORB: 1100
- Outcome: WIN
- R: +8.0R
- Session context captured (Asia travel, London chop, etc.)

This trade VALIDATES pattern "london_choppy_1100_outperform":
- Confidence increased: 68% → 71%
- Sample size: 38 → 39 trades
- Pattern remains ACTIVE

Execution quality: EXCELLENT
- Slippage: 0.1 (10% better than your average)
- Fill time: 280ms (fast)
- Psychological state: Overcame recent losses (maintained discipline)

Memory updated. This experience will inform future recommendations.
```

---

## Installation

1. Initialize database tables:
```bash
python scripts/init_trading_memory.py
```

2. (Optional) Backfill historical trades from daily_features_v2:
```bash
python scripts/backfill_trade_journal.py
```

3. Skill is now active - Claude will use it automatically when analyzing trades or querying patterns.

---

## Related Skills

- **edge-evolution-tracker** - Extends edge discovery with adaptive learning
- **market-anomaly-detection** - Detects unusual market conditions
- **code-review-pipeline** - Ensures memory system code is bug-free

---

**This is your AI trading partner with perfect memory. Every trade teaches it. Every pattern discovered makes it smarter. Every execution refines its understanding of your style.**

**Bloomberg terminals have data. You have data + memory + learning.**
