"""
MEMORY INTEGRATION - AI Learning Layer for Prop Firm Account Manager

Connects DrawdownEngine (pure math) with trading-memory skill (learning/patterns).

This module:
1. Records drawdown events to memory (HWM changes, effective capital, breach warnings)
2. Queries historical patterns (similar situations, breach probability)
3. Learns user-specific behavior (when they breach, which setups are dangerous)
4. Produces intelligent warnings (not just thresholds, but learned risk)

Architecture:
    DrawdownEngine → DrawdownResult (pure math)
           │
           ▼
    MemoryIntegration → Enhanced insights (AI layer)
           │
           ▼
    UI Display → Shows math + learned patterns

Reference: skills/trading-memory/SKILL.md
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Literal
import duckdb
from pathlib import Path

# Import DrawdownEngine types (we consume its output)
from trading_app.drawdown_engine import DrawdownResult, DrawdownRequest

# Import RiskEngine types (we enhance its output with AI)
from trading_app.risk_engine import RiskResult, RiskRequest


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

MemoryEventType = Literal[
    'EFFECTIVE_CAPITAL_CHANGE',
    'HWM_UPDATE',
    'BREACH_WARNING',
    'FLOOR_TRAIL',
    'ACCOUNT_BREACH'
]

PatternConfidence = Literal['HIGH', 'MEDIUM', 'LOW']


# =============================================================================
# INPUT CONTRACT (What we consume from DrawdownEngine)
# =============================================================================

@dataclass(frozen=True)
class DrawdownEvent:
    """
    Event to record in memory (from DrawdownEngine output).

    This is the bridge between pure calculation (DrawdownEngine)
    and learning (MemoryIntegration).
    """
    # Core identifiers
    account_id: int
    timestamp: datetime
    event_type: MemoryEventType

    # Drawdown metrics (from DrawdownResult)
    effective_capital: float
    distance_to_breach: float
    breach_risk_level: str
    drawdown_floor: float
    high_water_mark: float
    current_balance: float

    # Context (what caused this event)
    setup_name: str | None = None          # e.g., "1000 ORB MGC RR=1.5"
    trade_direction: str | None = None     # 'LONG' | 'SHORT' | None
    position_size: int | None = None

    # Metadata
    notes: str | None = None


# =============================================================================
# OUTPUT CONTRACT (What we produce - Enhanced Insights)
# =============================================================================

@dataclass(frozen=True)
class MemoryInsight:
    """
    AI-generated insight from historical patterns.

    Enhances pure math warnings with learned behavior.
    """
    insight_type: str                      # 'BREACH_PROBABILITY' | 'SETUP_IMPACT' | 'BEHAVIORAL_PATTERN'
    message: str                           # Human-readable warning
    confidence: PatternConfidence
    severity: str                          # 'INFO' | 'WARNING' | 'CRITICAL'

    # Supporting data
    pattern_details: dict = field(default_factory=dict)
    recommendation: str | None = None
    historical_context: str | None = None


@dataclass(frozen=True)
class EnhancedDrawdownResult:
    """
    DrawdownResult + AI insights.

    This is what gets displayed to user (math + intelligence).
    """
    # Original pure math result (passthrough)
    drawdown_result: DrawdownResult

    # AI-generated insights
    memory_insights: list[MemoryInsight]
    breach_probability: float | None       # 0.0 to 1.0 (learned from history)
    similar_situations_count: int
    last_breach_date: date | None
    avg_capital_degradation_rate: float | None  # $/trade

    # Behavioral warnings
    user_breach_pattern: str | None        # "You breach 80% of time in this zone"
    setup_history: dict | None             # Past outcomes with this setup


# =============================================================================
# RISK ENGINE INTEGRATION (AI-enhanced risk calculations)
# =============================================================================

@dataclass(frozen=True)
class RiskEvent:
    """
    Risk calculation event to record in memory (from RiskEngine output).

    Records every position size calculation, RoR assessment, and Kelly decision.
    """
    # Core identifiers
    account_id: int
    timestamp: datetime
    event_type: str  # 'POSITION_CALCULATED' | 'ROR_WARNING' | 'KELLY_VIOLATION' | 'EDGE_DETECTED'

    # Risk metrics (from RiskResult)
    effective_capital: float
    position_size: int
    risk_dollars: float
    risk_of_ruin: float
    kelly_fraction: float
    risk_level: str

    # Setup context
    setup_name: str | None = None
    win_rate: float | None = None
    payoff_ratio: float | None = None

    # Trade outcome (recorded after trade completes)
    trade_outcome: str | None = None  # 'WIN' | 'LOSS' | 'BREAKEVEN' | None (if pending)
    actual_pnl: float | None = None

    # Metadata
    notes: str | None = None


@dataclass(frozen=True)
class EnhancedRiskResult:
    """
    RiskResult + AI insights.

    Combines pure math risk calculation with learned patterns.
    """
    # Original pure math result (passthrough)
    risk_result: RiskResult

    # AI-generated insights
    memory_insights: list[MemoryInsight]
    historical_ror_accuracy: float | None  # How accurate is our RoR prediction?
    setup_specific_ror: float | None       # RoR for THIS setup specifically
    user_risk_pattern: str | None          # "You typically over-risk when..."

    # Behavioral warnings
    kelly_violation_history: dict | None   # Past times user violated Kelly
    similar_trades_count: int
    avg_outcome_for_similar: float | None  # Avg P&L for similar risk profiles


# =============================================================================
# MEMORY STORAGE (Database Schema)
# =============================================================================

MEMORY_SCHEMA = """
-- Sequences for auto-incrementing IDs
CREATE SEQUENCE IF NOT EXISTS seq_drawdown_events START 1;
CREATE SEQUENCE IF NOT EXISTS seq_learned_drawdown_patterns START 1;
CREATE SEQUENCE IF NOT EXISTS seq_risk_events START 1;

-- Drawdown event history (for pattern learning)
CREATE TABLE IF NOT EXISTS drawdown_events (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_drawdown_events'),
    account_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR NOT NULL,

    -- Drawdown metrics
    effective_capital DOUBLE NOT NULL,
    distance_to_breach DOUBLE NOT NULL,
    breach_risk_level VARCHAR NOT NULL,
    drawdown_floor DOUBLE NOT NULL,
    high_water_mark DOUBLE NOT NULL,
    current_balance DOUBLE NOT NULL,

    -- Context
    setup_name VARCHAR,
    trade_direction VARCHAR,
    position_size INTEGER,
    notes VARCHAR
);

-- Learned patterns (discovered from event analysis)
CREATE TABLE IF NOT EXISTS learned_drawdown_patterns (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_learned_drawdown_patterns'),
    account_id INTEGER NOT NULL,
    pattern_type VARCHAR NOT NULL,
    pattern_description VARCHAR NOT NULL,
    confidence DOUBLE NOT NULL,      -- 0.0 to 1.0
    sample_size INTEGER NOT NULL,

    -- Pattern metadata
    trigger_conditions VARCHAR,      -- JSON string of conditions
    outcome_probability DOUBLE,       -- Probability of breach/success
    avg_capital_impact DOUBLE,        -- Avg $/capital change

    -- Lifecycle
    first_observed DATE NOT NULL,
    last_observed DATE NOT NULL,
    times_observed INTEGER NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Risk event history (for RiskEngine learning)
CREATE TABLE IF NOT EXISTS risk_events (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_risk_events'),
    account_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR NOT NULL,

    -- Risk metrics (from RiskEngine)
    effective_capital DOUBLE NOT NULL,
    position_size INTEGER NOT NULL,
    risk_dollars DOUBLE NOT NULL,
    risk_of_ruin DOUBLE NOT NULL,
    kelly_fraction DOUBLE NOT NULL,
    risk_level VARCHAR NOT NULL,

    -- Setup context
    setup_name VARCHAR,
    win_rate DOUBLE,
    payoff_ratio DOUBLE,

    -- Trade outcome (NULL until trade completes)
    trade_outcome VARCHAR,
    actual_pnl DOUBLE,

    notes VARCHAR
);

-- Indexes for drawdown_events
CREATE INDEX IF NOT EXISTS idx_account_timestamp ON drawdown_events(account_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_breach_risk ON drawdown_events(account_id, breach_risk_level);
CREATE INDEX IF NOT EXISTS idx_effective_capital ON drawdown_events(account_id, effective_capital);

-- Indexes for risk_events
CREATE INDEX IF NOT EXISTS idx_account_timestamp_risk ON risk_events(account_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_risk_level ON risk_events(account_id, risk_level);
CREATE INDEX IF NOT EXISTS idx_setup_name_risk ON risk_events(account_id, setup_name);
"""


# =============================================================================
# CORE MEMORY INTEGRATION CLASS
# =============================================================================

class MemoryIntegration:
    """
    AI learning layer for prop firm account management.

    Records events, learns patterns, produces intelligent warnings.
    """

    def __init__(self, db_path: str = "gold.db"):
        self.db_path = Path(db_path)
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure memory tables exist in database"""
        conn = duckdb.connect(str(self.db_path))

        try:
            # Check if tables exist
            tables = conn.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'main'
                AND table_name IN ('drawdown_events', 'learned_drawdown_patterns', 'risk_events')
            """).fetchall()

            if len(tables) < 3:
                # Create tables
                for statement in MEMORY_SCHEMA.split(';'):
                    if statement.strip():
                        conn.execute(statement)
                conn.commit()

        finally:
            conn.close()

    def record_drawdown_event(self, event: DrawdownEvent) -> int:
        """
        Record a drawdown event to memory.

        Returns event ID for reference.
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                INSERT INTO drawdown_events (
                    account_id, timestamp, event_type,
                    effective_capital, distance_to_breach, breach_risk_level,
                    drawdown_floor, high_water_mark, current_balance,
                    setup_name, trade_direction, position_size, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, [
                event.account_id, event.timestamp, event.event_type,
                event.effective_capital, event.distance_to_breach, event.breach_risk_level,
                event.drawdown_floor, event.high_water_mark, event.current_balance,
                event.setup_name, event.trade_direction, event.position_size, event.notes
            ]).fetchone()

            conn.commit()
            return result[0]

        finally:
            conn.close()

    def enhance_drawdown_result(
        self,
        account_id: int,
        drawdown_result: DrawdownResult,
        current_context: dict | None = None
    ) -> EnhancedDrawdownResult:
        """
        Enhance pure math result with AI insights.

        Args:
            account_id: Account identifier
            drawdown_result: Pure calculation from DrawdownEngine
            current_context: Optional context (setup, position, etc.)

        Returns:
            EnhancedDrawdownResult with memory insights
        """
        insights = []

        # Query 1: Calculate breach probability from history
        breach_probability = self._calculate_breach_probability(
            account_id,
            drawdown_result.effective_capital,
            drawdown_result.breach_risk_level
        )

        if breach_probability is not None and breach_probability > 0.5:
            insights.append(MemoryInsight(
                insight_type='BREACH_PROBABILITY',
                message=f"HIGH BREACH RISK: {breach_probability*100:.0f}% probability based on your history",
                confidence='HIGH' if breach_probability > 0.7 else 'MEDIUM',
                severity='CRITICAL' if breach_probability > 0.8 else 'WARNING',
                pattern_details={
                    'probability': breach_probability,
                    'based_on_samples': self._get_sample_size(account_id, drawdown_result.effective_capital)
                },
                recommendation="Reduce position size or wait for better conditions"
            ))

        # Query 2: Find similar situations
        similar_situations = self._find_similar_situations(
            account_id,
            drawdown_result.effective_capital,
            drawdown_result.breach_risk_level
        )

        if similar_situations['breach_count'] > 0:
            breach_rate = similar_situations['breach_count'] / similar_situations['total_count']
            if breach_rate > 0.3:
                insights.append(MemoryInsight(
                    insight_type='BEHAVIORAL_PATTERN',
                    message=f"PATTERN ALERT: You breached {similar_situations['breach_count']}/{similar_situations['total_count']} times in similar situations",
                    confidence='HIGH',
                    severity='WARNING',
                    pattern_details=similar_situations,
                    historical_context=f"Last occurrence: {similar_situations.get('last_date')}"
                ))

        # Query 3: Setup-specific impact (if context provided)
        setup_history = None
        if current_context and 'setup_name' in current_context:
            setup_history = self._get_setup_impact_history(
                account_id,
                current_context['setup_name']
            )

            if setup_history and setup_history['avg_capital_degradation'] < -500:
                insights.append(MemoryInsight(
                    insight_type='SETUP_IMPACT',
                    message=f"SETUP WARNING: {current_context['setup_name']} historically reduces your effective capital by ${abs(setup_history['avg_capital_degradation']):.0f}",
                    confidence='MEDIUM',
                    severity='WARNING',
                    pattern_details=setup_history,
                    recommendation="Consider skipping or reducing position size"
                ))

        # Query 4: Capital degradation rate
        degradation_rate = self._calculate_capital_degradation_rate(
            account_id,
            days_lookback=30
        )

        if degradation_rate and degradation_rate < -100:  # Losing >$100/trade
            insights.append(MemoryInsight(
                insight_type='BEHAVIORAL_PATTERN',
                message=f"TREND ALERT: Your effective capital is degrading at ${abs(degradation_rate):.0f} per trade (30-day avg)",
                confidence='MEDIUM',
                severity='WARNING',
                pattern_details={'rate': degradation_rate, 'period': '30 days'},
                recommendation="Review trade selection and position sizing"
            ))

        # Query 5: Last breach date
        last_breach_date = self._get_last_breach_date(account_id)

        # Query 6: User breach pattern (time-based)
        user_pattern = self._detect_user_breach_pattern(account_id)

        return EnhancedDrawdownResult(
            drawdown_result=drawdown_result,
            memory_insights=insights,
            breach_probability=breach_probability,
            similar_situations_count=similar_situations.get('total_count', 0),
            last_breach_date=last_breach_date,
            avg_capital_degradation_rate=degradation_rate,
            user_breach_pattern=user_pattern,
            setup_history=setup_history
        )

    def _calculate_breach_probability(
        self,
        account_id: int,
        current_effective_capital: float,
        current_risk_level: str
    ) -> float | None:
        """
        Calculate probability of breach based on historical patterns.

        Logic:
        - Find all past events with similar effective capital (±$200)
        - Count how many led to breach within 5 trades
        - Return breach_count / total_count
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            # Find similar situations
            capital_range = 200
            result = conn.execute("""
                WITH similar_events AS (
                    SELECT
                        id,
                        timestamp,
                        effective_capital,
                        breach_risk_level
                    FROM drawdown_events
                    WHERE account_id = ?
                    AND effective_capital BETWEEN ? AND ?
                    ORDER BY timestamp
                ),
                future_breaches AS (
                    SELECT
                        e1.id,
                        CASE WHEN EXISTS (
                            SELECT 1 FROM drawdown_events e2
                            WHERE e2.account_id = ?
                            AND e2.timestamp > e1.timestamp
                            AND e2.timestamp <= e1.timestamp + INTERVAL '5 trades'
                            AND e2.event_type = 'ACCOUNT_BREACH'
                        ) THEN 1 ELSE 0 END as breached
                    FROM similar_events e1
                )
                SELECT
                    COUNT(*) as total,
                    SUM(breached) as breaches
                FROM future_breaches
            """, [
                account_id,
                current_effective_capital - capital_range,
                current_effective_capital + capital_range,
                account_id
            ]).fetchone()

            if result and result[0] >= 5:  # Need at least 5 samples
                total, breaches = result
                return breaches / total if total > 0 else None

            return None

        finally:
            conn.close()

    def _find_similar_situations(
        self,
        account_id: int,
        effective_capital: float,
        risk_level: str
    ) -> dict:
        """Find historical situations with similar effective capital and risk level"""
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                SELECT
                    COUNT(*) as total_count,
                    SUM(CASE WHEN event_type = 'ACCOUNT_BREACH' THEN 1 ELSE 0 END) as breach_count,
                    MAX(timestamp) as last_date
                FROM drawdown_events
                WHERE account_id = ?
                AND effective_capital BETWEEN ? AND ?
                AND breach_risk_level = ?
            """, [
                account_id,
                effective_capital - 200,
                effective_capital + 200,
                risk_level
            ]).fetchone()

            if result:
                return {
                    'total_count': result[0] or 0,
                    'breach_count': result[1] or 0,
                    'last_date': result[2]
                }

            return {'total_count': 0, 'breach_count': 0, 'last_date': None}

        finally:
            conn.close()

    def _get_setup_impact_history(self, account_id: int, setup_name: str) -> dict | None:
        """Get historical impact of a specific setup on effective capital"""
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                WITH setup_events AS (
                    SELECT
                        timestamp,
                        effective_capital,
                        LAG(effective_capital) OVER (ORDER BY timestamp) as prev_capital
                    FROM drawdown_events
                    WHERE account_id = ?
                    AND setup_name = ?
                    ORDER BY timestamp
                )
                SELECT
                    COUNT(*) as trade_count,
                    AVG(effective_capital - prev_capital) as avg_capital_change,
                    MIN(effective_capital - prev_capital) as worst_trade,
                    MAX(effective_capital - prev_capital) as best_trade
                FROM setup_events
                WHERE prev_capital IS NOT NULL
            """, [account_id, setup_name]).fetchone()

            if result and result[0] >= 3:  # Need at least 3 trades
                return {
                    'trade_count': result[0],
                    'avg_capital_degradation': result[1],
                    'worst_impact': result[2],
                    'best_impact': result[3]
                }

            return None

        finally:
            conn.close()

    def _calculate_capital_degradation_rate(
        self,
        account_id: int,
        days_lookback: int = 30
    ) -> float | None:
        """Calculate average effective capital change per trade over period"""
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                WITH recent_events AS (
                    SELECT
                        effective_capital,
                        LAG(effective_capital) OVER (ORDER BY timestamp) as prev_capital
                    FROM drawdown_events
                    WHERE account_id = ?
                    AND timestamp >= CURRENT_DATE - INTERVAL ? DAY
                    ORDER BY timestamp
                )
                SELECT AVG(effective_capital - prev_capital) as avg_change
                FROM recent_events
                WHERE prev_capital IS NOT NULL
            """, [account_id, days_lookback]).fetchone()

            return result[0] if result else None

        finally:
            conn.close()

    def _get_last_breach_date(self, account_id: int) -> date | None:
        """Get date of last account breach"""
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                SELECT MAX(timestamp::DATE) as last_breach
                FROM drawdown_events
                WHERE account_id = ?
                AND event_type = 'ACCOUNT_BREACH'
            """, [account_id]).fetchone()

            return result[0] if result and result[0] else None

        finally:
            conn.close()

    def _detect_user_breach_pattern(self, account_id: int) -> str | None:
        """
        Detect user-specific breach patterns.

        Examples:
        - "You breach on Fridays after 3 wins"
        - "Morning trades breach 2x more"
        - "You ignore warnings until $200 from breach"
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            # Check for day-of-week pattern
            dow_result = conn.execute("""
                SELECT
                    DAYNAME(timestamp) as day_name,
                    COUNT(*) as breach_count
                FROM drawdown_events
                WHERE account_id = ?
                AND event_type = 'ACCOUNT_BREACH'
                GROUP BY DAYNAME(timestamp)
                HAVING COUNT(*) >= 2
                ORDER BY breach_count DESC
                LIMIT 1
            """, [account_id]).fetchone()

            if dow_result and dow_result[1] >= 3:
                return f"You breach more on {dow_result[0]}s ({dow_result[1]} times)"

            # Check for time-of-day pattern
            tod_result = conn.execute("""
                SELECT
                    CASE
                        WHEN EXTRACT(HOUR FROM timestamp) < 12 THEN 'morning'
                        WHEN EXTRACT(HOUR FROM timestamp) < 17 THEN 'afternoon'
                        ELSE 'evening'
                    END as time_period,
                    COUNT(*) as breach_count
                FROM drawdown_events
                WHERE account_id = ?
                AND event_type = 'ACCOUNT_BREACH'
                GROUP BY time_period
                ORDER BY breach_count DESC
                LIMIT 1
            """, [account_id]).fetchone()

            if tod_result and tod_result[1] >= 3:
                return f"You breach more in {tod_result[0]} ({tod_result[1]} times)"

            return None

        finally:
            conn.close()

    def _get_sample_size(self, account_id: int, effective_capital: float) -> int:
        """Get sample size for breach probability calculation"""
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                SELECT COUNT(*) FROM drawdown_events
                WHERE account_id = ?
                AND effective_capital BETWEEN ? AND ?
            """, [account_id, effective_capital - 200, effective_capital + 200]).fetchone()

            return result[0] if result else 0

        finally:
            conn.close()

    # =========================================================================
    # RISK ENGINE INTEGRATION METHODS
    # =========================================================================

    def record_risk_event(self, event: RiskEvent) -> int:
        """
        Record a risk calculation event to memory.

        Returns:
            Event ID (for tracking)
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                INSERT INTO risk_events (
                    account_id, timestamp, event_type,
                    effective_capital, position_size, risk_dollars,
                    risk_of_ruin, kelly_fraction, risk_level,
                    setup_name, win_rate, payoff_ratio,
                    trade_outcome, actual_pnl, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, [
                event.account_id, event.timestamp, event.event_type,
                event.effective_capital, event.position_size, event.risk_dollars,
                event.risk_of_ruin, event.kelly_fraction, event.risk_level,
                event.setup_name, event.win_rate, event.payoff_ratio,
                event.trade_outcome, event.actual_pnl, event.notes
            ]).fetchone()

            conn.commit()

            return result[0] if result else 0

        finally:
            conn.close()

    def enhance_risk_result(
        self,
        account_id: int,
        risk_result: RiskResult,
        current_context: dict | None = None
    ) -> EnhancedRiskResult:
        """
        Enhance pure math risk result with AI insights.

        Queries:
        1. Calculate RoR accuracy from past predictions
        2. Find similar risk profiles (same RoR, kelly, capital)
        3. Get setup-specific RoR (this setup's historical breach rate)
        4. Detect user risk patterns (when do they over-risk?)
        5. Calculate avg outcome for similar trades

        Args:
            account_id: Account ID
            risk_result: Pure math result from RiskEngine
            current_context: Optional context (setup name, etc.)

        Returns:
            EnhancedRiskResult with AI insights
        """
        insights = []

        # Extract context
        setup_name = current_context.get('setup_name') if current_context else None

        # 1. Calculate historical RoR accuracy
        ror_accuracy = self._calculate_ror_accuracy(account_id)

        # 2. Calculate setup-specific RoR
        setup_specific_ror = None
        if setup_name:
            setup_specific_ror = self._calculate_setup_specific_ror(account_id, setup_name)

            if setup_specific_ror and setup_specific_ror > risk_result.risk_of_ruin * 1.5:
                insights.append(MemoryInsight(
                    insight_type='SETUP_SPECIFIC_RISK',
                    message=f"WARNING: {setup_name} has {setup_specific_ror:.1%} actual breach rate (higher than theoretical {risk_result.risk_of_ruin:.1%})",
                    confidence='HIGH',
                    severity='WARNING',
                    pattern_details={'actual_ror': setup_specific_ror, 'theoretical_ror': risk_result.risk_of_ruin},
                    recommendation="Consider reducing position size or skipping this setup",
                    historical_context=f"Based on your historical breach rate with this setup"
                ))

        # 3. Find similar risk profiles
        similar_trades = self._find_similar_risk_profiles(
            account_id=account_id,
            risk_level=risk_result.risk_level,
            kelly_fraction=risk_result.kelly_fraction,
            effective_capital=risk_result.calculation_metadata['effective_capital']
        )

        similar_count = similar_trades['trade_count'] if similar_trades else 0
        avg_outcome = similar_trades['avg_pnl'] if similar_trades and 'avg_pnl' in similar_trades else None

        # 4. Detect user risk patterns
        user_risk_pattern = self._detect_user_risk_pattern(account_id)

        # 5. Kelly violation history
        kelly_violation_history = self._get_kelly_violation_history(account_id)

        if kelly_violation_history and kelly_violation_history['violation_count'] >= 3:
            insights.append(MemoryInsight(
                insight_type='KELLY_VIOLATION',
                message=f"PATTERN: You've violated Kelly {kelly_violation_history['violation_count']} times (avg loss: ${kelly_violation_history['avg_loss']:.2f})",
                confidence='HIGH',
                severity='WARNING',
                pattern_details=kelly_violation_history,
                recommendation="Stick to Kelly fraction for optimal long-term growth",
                historical_context="Your past Kelly violations resulted in losses"
            ))

        # 6. Check if current position violates Kelly
        if not risk_result.using_fractional_kelly and risk_result.position_size > risk_result.kelly_position_size:
            insights.append(MemoryInsight(
                insight_type='KELLY_VIOLATION',
                message=f"DANGER: Position size ({risk_result.position_size}) exceeds Kelly ({risk_result.kelly_position_size})",
                confidence='HIGH',
                severity='CRITICAL',
                pattern_details={'position': risk_result.position_size, 'kelly': risk_result.kelly_position_size},
                recommendation="Reduce position to Kelly size or lower",
                historical_context="Over-betting Kelly increases risk of ruin"
            ))

        # 7. Check for no-edge warning
        if risk_result.kelly_fraction <= 0:
            insights.append(MemoryInsight(
                insight_type='NO_EDGE',
                message="CRITICAL: No statistical edge - expected value is negative",
                confidence='HIGH',
                severity='CRITICAL',
                pattern_details={'kelly': risk_result.kelly_fraction, 'edge': risk_result.calculation_metadata['edge']},
                recommendation="DO NOT TRADE - This setup has negative expectancy",
                historical_context="Trading negative expectancy setups guarantees long-term losses"
            ))

        return EnhancedRiskResult(
            risk_result=risk_result,
            memory_insights=insights,
            historical_ror_accuracy=ror_accuracy,
            setup_specific_ror=setup_specific_ror,
            user_risk_pattern=user_risk_pattern,
            kelly_violation_history=kelly_violation_history,
            similar_trades_count=similar_count,
            avg_outcome_for_similar=avg_outcome
        )

    def _calculate_ror_accuracy(self, account_id: int) -> float | None:
        """
        Calculate how accurate our RoR predictions have been.

        Compares predicted RoR vs actual breach rate.
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                WITH risk_with_outcome AS (
                    SELECT
                        risk_of_ruin as predicted_ror,
                        CASE WHEN trade_outcome = 'BREACH' THEN 1.0 ELSE 0.0 END as actual_breach
                    FROM risk_events
                    WHERE account_id = ?
                    AND trade_outcome IS NOT NULL
                )
                SELECT
                    AVG(predicted_ror) as avg_predicted,
                    AVG(actual_breach) as avg_actual
                FROM risk_with_outcome
            """, [account_id]).fetchone()

            if result and result[0] and result[1]:
                # Accuracy = 1 - abs(predicted - actual)
                accuracy = 1.0 - abs(result[0] - result[1])
                return max(0.0, min(1.0, accuracy))

            return None

        finally:
            conn.close()

    def _calculate_setup_specific_ror(self, account_id: int, setup_name: str) -> float | None:
        """
        Calculate actual Risk of Ruin for a specific setup (from history).

        Returns:
            Actual breach rate for this setup
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN trade_outcome = 'BREACH' THEN 1 ELSE 0 END) as breaches
                FROM risk_events
                WHERE account_id = ?
                AND setup_name = ?
                AND trade_outcome IS NOT NULL
            """, [account_id, setup_name]).fetchone()

            if result and result[0] >= 10:  # Minimum 10 trades for confidence
                breach_rate = result[1] / result[0]
                return breach_rate

            return None

        finally:
            conn.close()

    def _find_similar_risk_profiles(
        self,
        account_id: int,
        risk_level: str,
        kelly_fraction: float,
        effective_capital: float,
        tolerance: float = 0.1
    ) -> dict | None:
        """
        Find trades with similar risk profiles.

        Args:
            tolerance: Kelly fraction tolerance (e.g., 0.1 = ±10%)

        Returns:
            Dict with trade_count, avg_pnl, win_rate
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                SELECT
                    COUNT(*) as trade_count,
                    AVG(actual_pnl) as avg_pnl,
                    SUM(CASE WHEN actual_pnl > 0 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) as win_rate
                FROM risk_events
                WHERE account_id = ?
                AND risk_level = ?
                AND kelly_fraction BETWEEN ? AND ?
                AND effective_capital BETWEEN ? AND ?
                AND trade_outcome IS NOT NULL
            """, [
                account_id,
                risk_level,
                kelly_fraction * (1 - tolerance),
                kelly_fraction * (1 + tolerance),
                effective_capital * 0.8,
                effective_capital * 1.2
            ]).fetchone()

            if result and result[0] >= 5:  # Minimum 5 trades
                return {
                    'trade_count': result[0],
                    'avg_pnl': result[1],
                    'win_rate': result[2]
                }

            return None

        finally:
            conn.close()

    def _detect_user_risk_pattern(self, account_id: int) -> str | None:
        """
        Detect user-specific risk patterns.

        Examples:
        - "You over-risk after 2 wins in a row"
        - "You violate Kelly on Fridays"
        - "You ignore HIGH risk warnings"
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            # Check if user ignores CRITICAL warnings
            critical_ignored = conn.execute("""
                SELECT COUNT(*) FROM risk_events
                WHERE account_id = ?
                AND risk_level = 'CRITICAL'
                AND trade_outcome IS NOT NULL
            """, [account_id]).fetchone()

            if critical_ignored and critical_ignored[0] >= 3:
                return f"You traded {critical_ignored[0]} times despite CRITICAL risk warnings"

            return None

        finally:
            conn.close()

    def _get_kelly_violation_history(self, account_id: int) -> dict | None:
        """
        Get history of Kelly Criterion violations.

        Returns:
            Dict with violation_count, avg_loss
        """
        conn = duckdb.connect(str(self.db_path))

        try:
            result = conn.execute("""
                SELECT
                    COUNT(*) as violation_count,
                    AVG(actual_pnl) as avg_pnl
                FROM risk_events
                WHERE account_id = ?
                AND kelly_fraction > 0
                AND position_size > kelly_fraction * effective_capital / (risk_dollars / position_size)
                AND trade_outcome IS NOT NULL
            """, [account_id]).fetchone()

            if result and result[0] >= 1:
                return {
                    'violation_count': result[0],
                    'avg_loss': result[1] if result[1] else 0.0
                }

            return None

        finally:
            conn.close()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_drawdown_event_from_result(
    account_id: int,
    drawdown_result: DrawdownResult,
    current_balance: float,
    event_type: MemoryEventType = 'EFFECTIVE_CAPITAL_CHANGE',
    context: dict | None = None
) -> DrawdownEvent:
    """
    Create a DrawdownEvent from DrawdownEngine result.

    Helper to bridge DrawdownEngine output → Memory input.
    """
    return DrawdownEvent(
        account_id=account_id,
        timestamp=datetime.now(),
        event_type=event_type,
        effective_capital=drawdown_result.effective_capital,
        distance_to_breach=drawdown_result.distance_to_breach,
        breach_risk_level=drawdown_result.breach_risk_level,
        drawdown_floor=drawdown_result.drawdown_floor,
        high_water_mark=drawdown_result.new_high_water_mark,
        current_balance=current_balance,
        setup_name=context.get('setup_name') if context else None,
        trade_direction=context.get('trade_direction') if context else None,
        position_size=context.get('position_size') if context else None,
        notes=context.get('notes') if context else None
    )


def create_risk_event_from_result(
    account_id: int,
    risk_result: RiskResult,
    event_type: str = 'POSITION_CALCULATED',
    context: dict | None = None
) -> RiskEvent:
    """
    Create a RiskEvent from RiskEngine result.

    Helper to bridge RiskEngine output → Memory input.

    Args:
        account_id: Account ID
        risk_result: RiskResult from RiskEngine
        event_type: 'POSITION_CALCULATED' | 'ROR_WARNING' | 'KELLY_VIOLATION'
        context: Optional context (setup_name, trade_outcome, etc.)

    Returns:
        RiskEvent ready to record
    """
    return RiskEvent(
        account_id=account_id,
        timestamp=datetime.now(),
        event_type=event_type,
        effective_capital=risk_result.calculation_metadata['effective_capital'],
        position_size=risk_result.position_size,
        risk_dollars=risk_result.risk_dollars,
        risk_of_ruin=risk_result.risk_of_ruin,
        kelly_fraction=risk_result.kelly_fraction,
        risk_level=risk_result.risk_level,
        setup_name=context.get('setup_name') if context else None,
        win_rate=context.get('win_rate') if context else None,
        payoff_ratio=context.get('payoff_ratio') if context else None,
        trade_outcome=context.get('trade_outcome') if context else None,
        actual_pnl=context.get('actual_pnl') if context else None,
        notes=context.get('notes') if context else None
    )


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

def example_integration():
    """
    Example of how to integrate DrawdownEngine + MemoryIntegration.

    This shows the full flow:
    1. Calculate drawdown (pure math)
    2. Enhance with AI insights (memory)
    3. Display to user (UI)
    """
    from trading_app.drawdown_engine import calculate_drawdown

    # Step 1: Pure calculation (DrawdownEngine)
    request = DrawdownRequest(
        drawdown_model='TRAILING_INTRADAY',
        starting_balance=50000,
        max_drawdown_size=2000,
        current_balance=49500,  # Down $500
        high_water_mark=51000   # Was at $51k
    )

    drawdown_result = calculate_drawdown(request)

    print("=" * 70)
    print("PURE MATH (DrawdownEngine)")
    print("=" * 70)
    print(f"Effective Capital: ${drawdown_result.effective_capital:.2f}")
    print(f"Distance to Breach: ${drawdown_result.distance_to_breach:.2f}")
    print(f"Risk Level: {drawdown_result.breach_risk_level}")

    # Step 2: Enhance with AI insights (MemoryIntegration)
    memory = MemoryIntegration()

    # Record event
    event = create_drawdown_event_from_result(
        account_id=1,
        drawdown_result=drawdown_result,
        current_balance=49500,
        event_type='EFFECTIVE_CAPITAL_CHANGE',
        context={'setup_name': '1000 ORB MGC RR=1.5'}
    )
    memory.record_drawdown_event(event)

    # Get enhanced insights
    enhanced = memory.enhance_drawdown_result(
        account_id=1,
        drawdown_result=drawdown_result,
        current_context={'setup_name': '1000 ORB MGC RR=1.5'}
    )

    print("\n" + "=" * 70)
    print("AI INSIGHTS (MemoryIntegration)")
    print("=" * 70)

    if enhanced.breach_probability:
        print(f"Breach Probability: {enhanced.breach_probability*100:.0f}%")

    print(f"Similar Situations: {enhanced.similar_situations_count}")

    if enhanced.avg_capital_degradation_rate:
        print(f"Capital Degradation: ${enhanced.avg_capital_degradation_rate:.2f}/trade")

    if enhanced.user_breach_pattern:
        print(f"Pattern: {enhanced.user_breach_pattern}")

    print(f"\nInsights Generated: {len(enhanced.memory_insights)}")
    for insight in enhanced.memory_insights:
        print(f"\n[{insight.severity}] {insight.message}")
        if insight.recommendation:
            print(f"  → {insight.recommendation}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_integration()
