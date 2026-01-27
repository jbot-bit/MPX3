"""
STRATEGY EVALUATION ENGINE
Evaluates all known strategies and determines state + next action.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from enum import Enum
import logging

from config import *
from data_loader import LiveDataLoader

logger = logging.getLogger(__name__)


class StrategyState(Enum):
    """Strategy states (lifecycle)."""
    INVALID = "INVALID"          # Strategy not applicable right now
    PREPARING = "PREPARING"      # Structure forming, watch
    READY = "READY"             # All conditions met, can enter
    ACTIVE = "ACTIVE"           # Position open, managing
    EXITED = "EXITED"           # Trade closed


class ActionType(Enum):
    """What to do right now."""
    STAND_DOWN = "STAND_DOWN"   # Do nothing, wait
    PREPARE = "PREPARE"         # Get ready, structure forming
    ENTER = "ENTER"             # Execute entry
    MANAGE = "MANAGE"           # Manage open position
    EXIT = "EXIT"               # Close position


@dataclass
class StrategyEvaluation:
    """Result of evaluating a single strategy."""
    strategy_name: str
    priority: int
    state: StrategyState
    action: ActionType
    reasons: List[str]  # Max 3-5 factual bullets (expanded for better explanations)
    next_instruction: str  # ONE explicit instruction
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    risk_pct: Optional[float] = None

    # NEW FIELDS: For complete trade explanations (Phase 1 enhancement)
    setup_name: Optional[str] = None          # Specific setup: "2300 ORB HALF", "1000 ORB FULL"
    setup_tier: Optional[str] = None          # Quality tier: "S+", "S", "A", "B", "C"
    orb_high: Optional[float] = None          # ORB high level (for verification)
    orb_low: Optional[float] = None           # ORB low level (for verification)
    direction: Optional[str] = None           # Trade direction: "LONG" or "SHORT"
    position_size: Optional[int] = None       # Number of contracts
    rr: Optional[float] = None                # Reward:risk ratio (1.5, 3.0, 8.0)
    win_rate: Optional[float] = None          # Historical win rate % (56.1, 15.3)
    avg_r: Optional[float] = None             # Average R-multiple (theoretical)
    realized_expectancy: Optional[float] = None  # Realized expectancy (with costs)
    avg_win_r: Optional[float] = None         # Average win R-multiple (realized)
    avg_loss_r: Optional[float] = None        # Average loss R-multiple (realized)
    annual_trades: Optional[int] = None       # Annual trade frequency (260, 52)


class StrategyEngine:
    """
    Evaluates all strategies and enforces hierarchy.
    """

    def __init__(self, data_loader: LiveDataLoader, ml_engine=None):
        self.loader = data_loader
        self.current_position = None  # Track if in a trade
        self.ml_engine = ml_engine  # Optional ML inference engine

        # Load instrument-specific configs
        self.instrument = data_loader.symbol
        self._load_instrument_configs()

        if self.ml_engine and ML_ENABLED:
            logger.info("ML engine enabled for strategy evaluation")

    def _load_instrument_configs(self):
        """Load instrument-specific configuration parameters."""
        if self.instrument in ["NQ", "MNQ"]:
            # Load NQ configs
            self.orb_configs = NQ_ORB_CONFIGS
            self.orb_size_filters = NQ_ORB_SIZE_FILTERS
            self.cascade_min_gap = 15.0  # NQ needs larger gaps (13x more volatile)
            logger.info(f"Loaded NQ-specific configs: CASCADE gap={self.cascade_min_gap}pts")
        elif self.instrument in ["MPL", "PL"]:
            # Load MPL configs
            self.orb_configs = MPL_ORB_CONFIGS
            self.orb_size_filters = MPL_ORB_SIZE_FILTERS
            self.cascade_min_gap = CASCADE_MIN_GAP_POINTS  # 9.5pts for MPL (similar to MGC)
            logger.info(f"Loaded MPL-specific configs: CASCADE gap={self.cascade_min_gap}pts")
        else:
            # Default to MGC configs
            self.orb_configs = MGC_ORB_CONFIGS
            self.orb_size_filters = MGC_ORB_SIZE_FILTERS
            self.cascade_min_gap = CASCADE_MIN_GAP_POINTS  # 9.5pts for MGC
            logger.info(f"Loaded MGC-specific configs: CASCADE gap={self.cascade_min_gap}pts")

    # ========================================================================
    # MAIN EVALUATION LOOP
    # ========================================================================

    def evaluate_all(self) -> StrategyEvaluation:
        """
        Evaluate all strategies in priority order.
        Return the highest-priority actionable strategy.
        """
        evaluations = []

        # Evaluate each strategy
        for idx, strategy_name in enumerate(STRATEGY_PRIORITY):
            if strategy_name == "MULTI_LIQUIDITY_CASCADE":
                eval_result = self._evaluate_cascade()
            elif strategy_name == "PROXIMITY_PRESSURE":
                eval_result = self._evaluate_proximity()
            elif strategy_name == "NIGHT_ORB":
                eval_result = self._evaluate_night_orb()
            elif strategy_name == "SINGLE_LIQUIDITY":
                eval_result = self._evaluate_single_liquidity()
            elif strategy_name == "DAY_ORB":
                eval_result = self._evaluate_day_orb()
            else:
                continue

            eval_result.priority = idx
            evaluations.append(eval_result)

        # Apply hierarchy: highest priority wins
        # If higher-tier is PREPARING or ACTIVE, disable all lower tiers
        active_eval = None

        for eval_result in evaluations:
            if eval_result.state in [StrategyState.PREPARING, StrategyState.ACTIVE, StrategyState.READY]:
                active_eval = eval_result
                break

        if active_eval:
            # Enhance with ML insights before returning
            return self._enhance_with_ml_insights(active_eval)

        # If nothing active, return first INVALID (STAND_DOWN)
        fallback = evaluations[0] if evaluations else StrategyEvaluation(
            strategy_name="NONE",
            priority=999,
            state=StrategyState.INVALID,
            action=ActionType.STAND_DOWN,
            reasons=["No strategies active"],
            next_instruction="Wait for setup to form"
        )
        return fallback

    # ========================================================================
    # STRATEGY EVALUATORS
    # ========================================================================

    def _evaluate_cascade(self) -> StrategyEvaluation:
        """
        Evaluate Multi-Liquidity Cascade strategy.

        Structure:
        1. London swept Asia level (first sweep)
        2. At 23:00, second sweep of London level
        3. Acceptance failure (close back inside within 3 bars)
        4. Entry on retrace to level

        Returns validated edge: +1.95R avg, 9.3% frequency
        """
        now_local = datetime.now(TZ_LOCAL)

        # Get today's session levels
        asia_hl = self._get_today_asia_levels()
        london_hl = self._get_today_london_levels()

        # Check if we're in the right time window (23:00+)
        if now_local.hour < 23:
            return StrategyEvaluation(
                strategy_name="CASCADE",
                priority=0,
                state=StrategyState.PREPARING,
                action=ActionType.PREPARE,
                reasons=[
                    "Waiting for 23:00 window",
                    f"Asia High: {asia_hl['high']:.1f}" if asia_hl else "Asia session incomplete",
                    f"London High: {london_hl['high']:.1f}" if london_hl else "London session incomplete"
                ],
                next_instruction="Wait for 23:00 NY futures open"
            )

        # Check first sweep (London vs Asia)
        if not asia_hl or not london_hl:
            return StrategyEvaluation(
                strategy_name="CASCADE",
                priority=0,
                state=StrategyState.INVALID,
                action=ActionType.STAND_DOWN,
                reasons=["Missing session data"],
                next_instruction="Wait for session completion"
            )

        # UPSIDE cascade check
        if london_hl["high"] > asia_hl["high"]:
            gap = london_hl["high"] - asia_hl["high"]

            if gap < self.cascade_min_gap:
                return StrategyEvaluation(
                    strategy_name="CASCADE",
                    priority=0,
                    state=StrategyState.INVALID,
                    action=ActionType.STAND_DOWN,
                    reasons=[
                        f"Gap too small ({gap:.1f}pts < {self.cascade_min_gap}pts)",
                        "Large gap required for cascade edge"
                    ],
                    next_instruction="Wait for larger gap setup"
                )

            # Check for second sweep at 23:00+
            ny_hl = self._get_today_ny_levels()

            if not ny_hl:
                # NY session hasn't started yet or no data
                return StrategyEvaluation(
                    strategy_name="CASCADE",
                    priority=0,
                    state=StrategyState.PREPARING,
                    action=ActionType.PREPARE,
                    reasons=[
                        f"London swept Asia high (gap {gap:.1f}pts)",
                        f"Gap > {self.cascade_min_gap}pts (LARGE GAP)",
                        "Watching for second sweep at 23:00"
                    ],
                    next_instruction=f"Watch for close > {london_hl['high']:.1f} (London high)",
                    entry_price=london_hl["high"],
                    risk_pct=RISK_LIMITS["CASCADE"]["default"]
                )

            # Check if NY swept London high (second sweep)
            if ny_hl["high"] > london_hl["high"]:
                # Second sweep detected! Check for acceptance failure
                acceptance_failed = self._check_acceptance_failure(
                    level=london_hl["high"],
                    direction="UP",
                    bars_to_check=CASCADE_FAILURE_BARS
                )

                if acceptance_failed:
                    # CASCADE ACTIVE - Entry opportunity!
                    # Stop/Target logic: Gap-based (not pure R-based)
                    # - Entry: at swept level (london_hl["high"])
                    # - Stop: 0.5 gaps above entry (protects against re-sweep)
                    # - Target: 2.0 gaps below entry (multi-level retracement target)
                    # This gives effective RR = (2.0 gaps) / (0.5 gaps) = 4R
                    return StrategyEvaluation(
                        strategy_name="CASCADE",
                        priority=0,
                        state=StrategyState.READY,
                        action=ActionType.ENTER,
                        reasons=[
                            f"Double sweep: Asia→London ({gap:.1f}pts) → NY",
                            "Acceptance failure detected (close back inside)",
                            "Trapped participants above, liquidity cascade edge"
                        ],
                        next_instruction=f"ENTER SHORT on retrace to {london_hl['high']:.1f}",
                        entry_price=london_hl["high"],
                        stop_price=london_hl["high"] + gap * 0.5,  # Stop 0.5 gaps above entry
                        target_price=london_hl["high"] - gap * 2.0,  # Target 2 gaps below entry (4R)
                        risk_pct=RISK_LIMITS["CASCADE"]["default"]
                    )
                else:
                    # Second sweep but no acceptance failure yet
                    return StrategyEvaluation(
                        strategy_name="CASCADE",
                        priority=0,
                        state=StrategyState.PREPARING,
                        action=ActionType.PREPARE,
                        reasons=[
                            f"Second sweep detected at NY open",
                            f"Monitoring for acceptance failure (next {CASCADE_FAILURE_BARS} bars)",
                            "Need close back inside level"
                        ],
                        next_instruction=f"Watch for close < {london_hl['high']:.1f}",
                        entry_price=london_hl["high"],
                        risk_pct=RISK_LIMITS["CASCADE"]["default"]
                    )

            # First sweep only, waiting for second sweep
            return StrategyEvaluation(
                strategy_name="CASCADE",
                priority=0,
                state=StrategyState.PREPARING,
                action=ActionType.PREPARE,
                reasons=[
                    f"London swept Asia high (gap {gap:.1f}pts)",
                    f"Gap > {self.cascade_min_gap}pts (LARGE GAP)",
                    "Watching for second sweep at 23:00"
                ],
                next_instruction=f"Watch for NY to sweep {london_hl['high']:.1f}",
                entry_price=london_hl["high"],
                risk_pct=RISK_LIMITS["CASCADE"]["default"]
            )

        # DOWNSIDE cascade check
        if london_hl["low"] < asia_hl["low"]:
            gap = asia_hl["low"] - london_hl["low"]

            if gap < self.cascade_min_gap:
                return StrategyEvaluation(
                    strategy_name="CASCADE",
                    priority=0,
                    state=StrategyState.INVALID,
                    action=ActionType.STAND_DOWN,
                    reasons=[
                        f"Gap too small ({gap:.1f}pts < {self.cascade_min_gap}pts)"
                    ],
                    next_instruction="Wait for larger gap setup"
                )

            # Check for second sweep at 23:00+
            ny_hl = self._get_today_ny_levels()

            if not ny_hl:
                # NY session hasn't started yet or no data
                return StrategyEvaluation(
                    strategy_name="CASCADE",
                    priority=0,
                    state=StrategyState.PREPARING,
                    action=ActionType.PREPARE,
                    reasons=[
                        f"London swept Asia low (gap {gap:.1f}pts)",
                        f"Gap > {self.cascade_min_gap}pts (LARGE GAP)",
                        "Watching for second sweep at 23:00"
                    ],
                    next_instruction=f"Watch for close < {london_hl['low']:.1f} (London low)",
                    entry_price=london_hl["low"],
                    risk_pct=RISK_LIMITS["CASCADE"]["default"]
                )

            # Check if NY swept London low (second sweep)
            if ny_hl["low"] < london_hl["low"]:
                # Second sweep detected! Check for acceptance failure
                acceptance_failed = self._check_acceptance_failure(
                    level=london_hl["low"],
                    direction="DOWN",
                    bars_to_check=CASCADE_FAILURE_BARS
                )

                if acceptance_failed:
                    # CASCADE ACTIVE - Entry opportunity!
                    # Stop/Target logic: Gap-based (not pure R-based)
                    # - Entry: at swept level (london_hl["low"])
                    # - Stop: 0.5 gaps below entry (protects against re-sweep)
                    # - Target: 2.0 gaps above entry (multi-level retracement target)
                    # This gives effective RR = (2.0 gaps) / (0.5 gaps) = 4R
                    return StrategyEvaluation(
                        strategy_name="CASCADE",
                        priority=0,
                        state=StrategyState.READY,
                        action=ActionType.ENTER,
                        reasons=[
                            f"Double sweep: Asia→London ({gap:.1f}pts) → NY",
                            "Acceptance failure detected (close back inside)",
                            "Trapped participants below, liquidity cascade edge"
                        ],
                        next_instruction=f"ENTER LONG on retrace to {london_hl['low']:.1f}",
                        entry_price=london_hl["low"],
                        stop_price=london_hl["low"] - gap * 0.5,  # Stop 0.5 gaps below entry
                        target_price=london_hl["low"] + gap * 2.0,  # Target 2 gaps above entry (4R)
                        risk_pct=RISK_LIMITS["CASCADE"]["default"]
                    )
                else:
                    # Second sweep but no acceptance failure yet
                    return StrategyEvaluation(
                        strategy_name="CASCADE",
                        priority=0,
                        state=StrategyState.PREPARING,
                        action=ActionType.PREPARE,
                        reasons=[
                            f"Second sweep detected at NY open",
                            f"Monitoring for acceptance failure (next {CASCADE_FAILURE_BARS} bars)",
                            "Need close back inside level"
                        ],
                        next_instruction=f"Watch for close > {london_hl['low']:.1f}",
                        entry_price=london_hl["low"],
                        risk_pct=RISK_LIMITS["CASCADE"]["default"]
                    )

            # First sweep only, waiting for second sweep
            return StrategyEvaluation(
                strategy_name="CASCADE",
                priority=0,
                state=StrategyState.PREPARING,
                action=ActionType.PREPARE,
                reasons=[
                    f"London swept Asia low (gap {gap:.1f}pts)",
                    f"Gap > {self.cascade_min_gap}pts (LARGE GAP)",
                    "Watching for second sweep at 23:00"
                ],
                next_instruction=f"Watch for NY to sweep {london_hl['low']:.1f}",
                entry_price=london_hl["low"],
                risk_pct=RISK_LIMITS["CASCADE"]["default"]
            )

        # No first sweep
        return StrategyEvaluation(
            strategy_name="CASCADE",
            priority=0,
            state=StrategyState.INVALID,
            action=ActionType.STAND_DOWN,
            reasons=["London did not sweep Asia level"],
            next_instruction="Wait for first sweep"
        )

    def _evaluate_proximity(self) -> StrategyEvaluation:
        """
        Evaluate Proximity Pressure strategy.

        NOTE: This strategy FAILED testing (-0.50R avg, 1.1% freq).
        Included for structure but should be disabled by default.
        """
        return StrategyEvaluation(
            strategy_name="PROXIMITY",
            priority=1,
            state=StrategyState.INVALID,
            action=ActionType.STAND_DOWN,
            reasons=[
                "Strategy FAILED testing (-0.50R)",
                "Disabled by default",
                "No edge validated"
            ],
            next_instruction="Skip - use higher/lower tier strategies"
        )

    def _evaluate_night_orb(self) -> StrategyEvaluation:
        """
        Evaluate Night ORB strategies (23:00, 00:30).

        Validated edge (RR=1.0, HALF SL, realistic entry):
        - 23:00 ORB: +0.387R avg, 100% days, 48.9% WR
        - 00:30 ORB: +0.231R avg, 100% days, 43.5% WR

        Entry: First 1-minute close outside ORB (NOT ORB edge)
        Stop: HALF (ORB midpoint)
        Target: Entry + 1.0R
        """
        now_local = datetime.now(TZ_LOCAL)
        current_hour = now_local.hour
        current_min = now_local.minute

        # Check 00:30 ORB (BEST ORB)
        if current_hour == 0 and current_min >= 30:
            orb_result = self._check_orb("0030")
            if orb_result:
                return orb_result

        # Check 23:00 ORB
        if current_hour == 23:
            orb_result = self._check_orb("2300")
            if orb_result:
                return orb_result

        return StrategyEvaluation(
            strategy_name="NIGHT_ORB",
            priority=2,
            state=StrategyState.INVALID,
            action=ActionType.STAND_DOWN,
            reasons=["Outside night ORB windows (23:00, 00:30)"],
            next_instruction="Wait for 23:00 or 00:30"
        )

    def _evaluate_single_liquidity(self) -> StrategyEvaluation:
        """
        Evaluate Single Liquidity Reaction strategy.

        Validated edge: +1.44R avg, 16% freq, 33.7% WR
        Pattern: London level swept at 23:00, fails to hold
        """
        now_local = datetime.now(TZ_LOCAL)

        # Only active at 23:00+ (NY futures open)
        if now_local.hour < 23:
            return StrategyEvaluation(
                strategy_name="SINGLE_LIQUIDITY",
                priority=3,
                state=StrategyState.INVALID,
                action=ActionType.STAND_DOWN,
                reasons=["Waiting for 23:00 NY futures open"],
                next_instruction="Wait for NY session"
            )

        # Get London levels
        london_hl = self._get_today_london_levels()

        if not london_hl:
            return StrategyEvaluation(
                strategy_name="SINGLE_LIQUIDITY",
                priority=3,
                state=StrategyState.INVALID,
                action=ActionType.STAND_DOWN,
                reasons=["London session incomplete or no data"],
                next_instruction="Wait for London session completion"
            )

        # Get NY levels
        ny_hl = self._get_today_ny_levels()

        if not ny_hl:
            return StrategyEvaluation(
                strategy_name="SINGLE_LIQUIDITY",
                priority=3,
                state=StrategyState.PREPARING,
                action=ActionType.PREPARE,
                reasons=[
                    "NY session starting",
                    f"Watching London high: {london_hl['high']:.1f}",
                    f"Watching London low: {london_hl['low']:.1f}"
                ],
                next_instruction="Monitor for London level sweep"
            )

        # Check UPSIDE sweep (NY sweeps London high)
        if ny_hl["high"] > london_hl["high"]:
            # Check for acceptance failure
            acceptance_failed = self._check_acceptance_failure(
                level=london_hl["high"],
                direction="UP",
                bars_to_check=SINGLE_LIQ_FAILURE_BARS
            )

            if acceptance_failed:
                # SINGLE LIQUIDITY ACTIVE
                return StrategyEvaluation(
                    strategy_name="SINGLE_LIQUIDITY",
                    priority=3,
                    state=StrategyState.READY,
                    action=ActionType.ENTER,
                    reasons=[
                        f"NY swept London high ({london_hl['high']:.1f})",
                        "Acceptance failure detected (close back inside)",
                        "Single liquidity reaction edge active"
                    ],
                    next_instruction=f"ENTER SHORT on retrace to {london_hl['high']:.1f}",
                    entry_price=london_hl["high"],
                    stop_price=ny_hl["high"] + 2.0,  # 2pts above NY high
                    target_price=london_hl["low"],  # Target London low
                    risk_pct=RISK_LIMITS["SINGLE_LIQ"]["default"]
                )
            else:
                # Sweep detected, monitoring for failure
                return StrategyEvaluation(
                    strategy_name="SINGLE_LIQUIDITY",
                    priority=3,
                    state=StrategyState.PREPARING,
                    action=ActionType.PREPARE,
                    reasons=[
                        f"NY swept London high ({london_hl['high']:.1f})",
                        f"Monitoring for acceptance failure (next {SINGLE_LIQ_FAILURE_BARS} bars)",
                        "Need close back inside level"
                    ],
                    next_instruction=f"Watch for close < {london_hl['high']:.1f}"
                )

        # Check DOWNSIDE sweep (NY sweeps London low)
        if ny_hl["low"] < london_hl["low"]:
            # Check for acceptance failure
            acceptance_failed = self._check_acceptance_failure(
                level=london_hl["low"],
                direction="DOWN",
                bars_to_check=SINGLE_LIQ_FAILURE_BARS
            )

            if acceptance_failed:
                # SINGLE LIQUIDITY ACTIVE
                return StrategyEvaluation(
                    strategy_name="SINGLE_LIQUIDITY",
                    priority=3,
                    state=StrategyState.READY,
                    action=ActionType.ENTER,
                    reasons=[
                        f"NY swept London low ({london_hl['low']:.1f})",
                        "Acceptance failure detected (close back inside)",
                        "Single liquidity reaction edge active"
                    ],
                    next_instruction=f"ENTER LONG on retrace to {london_hl['low']:.1f}",
                    entry_price=london_hl["low"],
                    stop_price=ny_hl["low"] - 2.0,  # 2pts below NY low
                    target_price=london_hl["high"],  # Target London high
                    risk_pct=RISK_LIMITS["SINGLE_LIQ"]["default"]
                )
            else:
                # Sweep detected, monitoring for failure
                return StrategyEvaluation(
                    strategy_name="SINGLE_LIQUIDITY",
                    priority=3,
                    state=StrategyState.PREPARING,
                    action=ActionType.PREPARE,
                    reasons=[
                        f"NY swept London low ({london_hl['low']:.1f})",
                        f"Monitoring for acceptance failure (next {SINGLE_LIQ_FAILURE_BARS} bars)",
                        "Need close back inside level"
                    ],
                    next_instruction=f"Watch for close > {london_hl['low']:.1f}"
                )

        # No sweep yet
        return StrategyEvaluation(
            strategy_name="SINGLE_LIQUIDITY",
            priority=3,
            state=StrategyState.PREPARING,
            action=ActionType.PREPARE,
            reasons=[
                "NY session active, no sweep yet",
                f"London high: {london_hl['high']:.1f}",
                f"London low: {london_hl['low']:.1f}"
            ],
            next_instruction="Monitor for London level sweep"
        )

    def _evaluate_day_orb(self) -> StrategyEvaluation:
        """
        Evaluate Day ORB strategies (09:00, 10:00, 11:00).

        Validated edge: +0.27-0.34R avg, 64-66% freq (tertiary)
        """
        now_local = datetime.now(TZ_LOCAL)
        current_hour = now_local.hour

        # Check each day ORB
        for orb_name in ["0900", "1000", "1100"]:
            orb_hour = int(orb_name[:2])
            if current_hour == orb_hour:
                orb_result = self._check_orb(orb_name)
                if orb_result:
                    return orb_result

        return StrategyEvaluation(
            strategy_name="DAY_ORB",
            priority=4,
            state=StrategyState.INVALID,
            action=ActionType.STAND_DOWN,
            reasons=["Outside day ORB windows"],
            next_instruction="Wait for 09:00, 10:00, or 11:00"
        )

    # ========================================================================
    # HELPER FUNCTIONS
    # ========================================================================

    def _get_today_asia_levels(self) -> Optional[Dict]:
        """Get today's Asia session high/low."""
        now = datetime.now(TZ_LOCAL)
        asia_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        asia_end = now.replace(hour=17, minute=0, second=0, microsecond=0)

        return self.loader.get_session_high_low(asia_start, asia_end)

    def _get_today_london_levels(self) -> Optional[Dict]:
        """Get today's London session high/low."""
        now = datetime.now(TZ_LOCAL)
        london_start = now.replace(hour=18, minute=0, second=0, microsecond=0)
        london_end = now.replace(hour=23, minute=0, second=0, microsecond=0)

        return self.loader.get_session_high_low(london_start, london_end)

    def _get_today_ny_levels(self) -> Optional[Dict]:
        """Get today's NY session high/low (23:00-02:00 next day)."""
        now = datetime.now(TZ_LOCAL)
        ny_start = now.replace(hour=23, minute=0, second=0, microsecond=0)

        # NY session goes until 02:00 next day
        if now.hour < 23:
            # Before NY open, no data yet
            return None

        ny_end = (now + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)

        # If we're past 02:00, use yesterday's NY session
        if now.hour >= 2 and now.hour < 23:
            ny_start = (now - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
            ny_end = now.replace(hour=2, minute=0, second=0, microsecond=0)

        return self.loader.get_session_high_low(ny_start, ny_end)

    def _check_acceptance_failure(self, level: float, direction: str, bars_to_check: int) -> bool:
        """
        Check if price swept a level but closed back inside (acceptance failure).

        Args:
            level: Price level that was swept
            direction: "UP" or "DOWN" (sweep direction)
            bars_to_check: Number of recent bars to check (typically 3)

        Returns:
            True if acceptance failure detected (close back inside level)
        """
        # Get recent bars
        recent_bars = self.loader.fetch_latest_bars(lookback_minutes=bars_to_check * 5)

        if recent_bars.empty or len(recent_bars) < bars_to_check:
            return False

        # Check last N bars
        last_n_bars = recent_bars.tail(bars_to_check)

        if direction == "UP":
            # For upside sweep: check if any bar has high > level AND close < level
            for _, bar in last_n_bars.iterrows():
                if bar["high"] > level and bar["close"] < level:
                    return True
        elif direction == "DOWN":
            # For downside sweep: check if any bar has low < level AND close > level
            for _, bar in last_n_bars.iterrows():
                if bar["low"] < level and bar["close"] > level:
                    return True

        return False

    def _check_orb(self, orb_name: str) -> Optional[StrategyEvaluation]:
        """
        Check ORB status for a specific time.

        Args:
            orb_name: "0900", "1000", "1100", "2300", "0030"

        Returns:
            StrategyEvaluation if ORB is active, None otherwise
        """
        now = datetime.now(TZ_LOCAL)
        config = self.orb_configs.get(orb_name)

        if not config:
            return None

        # Check if this ORB is skipped for this instrument (e.g., NQ 2300)
        if config.get("tier") == "SKIP":
            return StrategyEvaluation(
                strategy_name=f"{orb_name}_ORB",
                priority=2 if orb_name in ["2300", "0030"] else 4,
                state=StrategyState.INVALID,
                action=ActionType.STAND_DOWN,
                reasons=[
                    f"{orb_name} ORB SKIPPED for {self.instrument}",
                    "Negative expectancy on this instrument",
                    "Strategy disabled by config"
                ],
                next_instruction=f"Skip {orb_name} - use other ORB times or strategies"
            )

        # Find ORB time
        orb_time = None
        for orb in ORB_TIMES:
            if orb["name"] == orb_name:
                orb_time = orb
                break

        if not orb_time:
            return None

        # Calculate ORB window
        orb_start = now.replace(hour=orb_time["hour"], minute=orb_time["min"], second=0, microsecond=0)
        orb_end = orb_start + timedelta(minutes=ORB_DURATION_MIN)

        # Are we in ORB formation window?
        if now < orb_end:
            return StrategyEvaluation(
                strategy_name=f"{orb_name}_ORB",
                priority=2 if config["tier"] == "NIGHT" else 4,
                state=StrategyState.PREPARING,
                action=ActionType.PREPARE,
                reasons=[
                    f"{orb_name} ORB forming",
                    f"Window: {orb_start.strftime('%H:%M')}-{orb_end.strftime('%H:%M')}"
                ],
                next_instruction=f"Wait for ORB completion at {orb_end.strftime('%H:%M')}"
            )

        # ORB complete, check for breakout
        orb_hl = self.loader.get_session_high_low(orb_start, orb_end)

        if not orb_hl:
            return None

        orb_high = orb_hl["high"]
        orb_low = orb_hl["low"]
        orb_mid = (orb_high + orb_low) / 2
        orb_size = orb_high - orb_low

        # Apply ORB size filter (NO LOOKAHEAD - computed at ORB close)
        filter_result = self.loader.check_orb_size_filter(orb_high, orb_low, orb_name)

        if not filter_result["pass"]:
            # ORB too large - reject trade
            return StrategyEvaluation(
                strategy_name=f"{orb_name}_ORB",
                priority=2 if config["tier"] == "NIGHT" else 4,
                state=StrategyState.INVALID,
                action=ActionType.STAND_DOWN,
                reasons=[
                    f"ORB SIZE FILTER REJECTED",
                    filter_result["reason"],
                    "Large ORB = exhaustion pattern"
                ],
                next_instruction=f"Stand down - wait for next ORB or smaller ORB setup"
            )

        latest_bar = self.loader.get_latest_bar()
        if not latest_bar:
            return None

        current_price = latest_bar["close"]

        # Check for breakout
        if current_price > orb_high:
            # LONG breakout
            # Entry: First close outside ORB (aligned with canonical engine)
            entry = current_price
            stop = orb_mid if config["sl_mode"] == "HALF" else orb_low
            risk = abs(entry - stop)  # Risk from ENTRY to STOP (not ORB high to stop)
            target = entry + (config["rr"] * risk)

            # Calculate position sizing with Kelly multiplier
            base_risk_pct = RISK_LIMITS["NIGHT_ORB" if config["tier"] == "NIGHT" else "DAY_ORB"]["default"]
            size_multiplier = self.loader.get_position_size_multiplier(orb_name, filter_result["pass"])
            adjusted_risk_pct = base_risk_pct * size_multiplier

            size_note = f" | {size_multiplier:.2f}x size" if size_multiplier > 1.0 else ""

            # Get setup info from database (for tier, win_rate, etc.)
            setup_info = self._get_setup_info(orb_name)

            return StrategyEvaluation(
                strategy_name=f"{orb_name}_ORB",
                priority=2 if config["tier"] == "NIGHT" else 4,
                state=StrategyState.READY,
                action=ActionType.ENTER,
                reasons=[
                    f"{orb_name} ORB formed (High: ${orb_high:.2f}, Low: ${orb_low:.2f}, Size: {orb_size:.2f} pts)",
                    f"ORB size filter PASSED ({orb_size:.2f} pts / {filter_result.get('atr', 0):.1f} ATR < threshold)" if filter_result["pass"] else f"ORB filter N/A (no filter on {orb_name})",
                    f"First close outside ORB detected (Close: ${current_price:.2f} > High: ${orb_high:.2f})",
                    f"{setup_info.get('tier', 'N/A')} tier setup ({setup_info.get('win_rate', 0):.1f}% win rate, {setup_info.get('annual_expectancy', 0):.0f}R/year expectancy)" if setup_info else f"Config: RR={config['rr']}, SL={config['sl_mode']}{size_note}"
                ],
                next_instruction=f"Enter long at ${entry:.2f}, stop at ${stop:.2f} (ORB {config['sl_mode'].lower()}), target at ${target:.2f} ({config['rr']}R)",
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                risk_pct=adjusted_risk_pct,
                # NEW FIELDS
                setup_name=f"{orb_name} ORB {config['sl_mode']}",
                setup_tier=setup_info.get('tier') if setup_info else None,
                orb_high=orb_high,
                orb_low=orb_low,
                direction="LONG",
                position_size=None,  # Will be calculated by UI/position sizing module
                rr=config["rr"],
                win_rate=setup_info.get('win_rate') if setup_info else None,
                avg_r=setup_info.get('avg_r') if setup_info else None,
                realized_expectancy=setup_info.get('realized_expectancy') if setup_info else None,
                avg_win_r=setup_info.get('avg_win_r') if setup_info else None,
                avg_loss_r=setup_info.get('avg_loss_r') if setup_info else None,
                annual_trades=setup_info.get('annual_trades') if setup_info else None
            )

        elif current_price < orb_low:
            # SHORT breakout
            # Entry: First close outside ORB (aligned with canonical engine)
            entry = current_price
            stop = orb_mid if config["sl_mode"] == "HALF" else orb_high
            risk = abs(entry - stop)  # Risk from ENTRY to STOP (not ORB low to stop)
            target = entry - (config["rr"] * risk)

            # Calculate position sizing with Kelly multiplier
            base_risk_pct = RISK_LIMITS["NIGHT_ORB" if config["tier"] == "NIGHT" else "DAY_ORB"]["default"]
            size_multiplier = self.loader.get_position_size_multiplier(orb_name, filter_result["pass"])
            adjusted_risk_pct = base_risk_pct * size_multiplier

            size_note = f" | {size_multiplier:.2f}x size" if size_multiplier > 1.0 else ""

            # Get setup info from database (for tier, win_rate, etc.)
            setup_info = self._get_setup_info(orb_name)

            return StrategyEvaluation(
                strategy_name=f"{orb_name}_ORB",
                priority=2 if config["tier"] == "NIGHT" else 4,
                state=StrategyState.READY,
                action=ActionType.ENTER,
                reasons=[
                    f"{orb_name} ORB formed (High: ${orb_high:.2f}, Low: ${orb_low:.2f}, Size: {orb_size:.2f} pts)",
                    f"ORB size filter PASSED ({orb_size:.2f} pts / {filter_result.get('atr', 0):.1f} ATR < threshold)" if filter_result["pass"] else f"ORB filter N/A (no filter on {orb_name})",
                    f"First close outside ORB detected (Close: ${current_price:.2f} < Low: ${orb_low:.2f})",
                    f"{setup_info.get('tier', 'N/A')} tier setup ({setup_info.get('win_rate', 0):.1f}% win rate, {setup_info.get('annual_expectancy', 0):.0f}R/year expectancy)" if setup_info else f"Config: RR={config['rr']}, SL={config['sl_mode']}{size_note}"
                ],
                next_instruction=f"Enter short at ${entry:.2f}, stop at ${stop:.2f} (ORB {config['sl_mode'].lower()}), target at ${target:.2f} ({config['rr']}R)",
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                risk_pct=adjusted_risk_pct,
                # NEW FIELDS
                setup_name=f"{orb_name} ORB {config['sl_mode']}",
                setup_tier=setup_info.get('tier') if setup_info else None,
                orb_high=orb_high,
                orb_low=orb_low,
                direction="SHORT",
                position_size=None,  # Will be calculated by UI/position sizing module
                rr=config["rr"],
                win_rate=setup_info.get('win_rate') if setup_info else None,
                avg_r=setup_info.get('avg_r') if setup_info else None,
                realized_expectancy=setup_info.get('realized_expectancy') if setup_info else None,
                avg_win_r=setup_info.get('avg_win_r') if setup_info else None,
                avg_loss_r=setup_info.get('avg_loss_r') if setup_info else None,
                annual_trades=setup_info.get('annual_trades') if setup_info else None
            )

        else:
            # Inside ORB range, waiting
            return StrategyEvaluation(
                strategy_name=f"{orb_name}_ORB",
                priority=2 if config["tier"] == "NIGHT" else 4,
                state=StrategyState.PREPARING,
                action=ActionType.PREPARE,
                reasons=[
                    f"{orb_name} ORB: {orb_low:.2f} - {orb_high:.2f}",
                    f"Current: {current_price:.2f} (inside range)"
                ],
                next_instruction=f"Wait for breakout above {orb_high:.2f} or below {orb_low:.2f}"
            )

    # ========================================================================
    # ML INTEGRATION
    # ========================================================================

    def _enhance_with_ml_insights(self, evaluation: StrategyEvaluation) -> StrategyEvaluation:
        """
        Enhance strategy evaluation with ML predictions.

        This adds ML confidence, directional bias, and reasoning to the evaluation.
        In shadow mode, ML insights are added but don't affect decisions.

        Args:
            evaluation: Rule-based strategy evaluation

        Returns:
            Enhanced evaluation with ML insights
        """
        if not self.ml_engine or not ML_ENABLED:
            return evaluation

        # Only add ML insights for PREPARING and READY states
        if evaluation.state not in [StrategyState.PREPARING, StrategyState.READY]:
            return evaluation

        try:
            # Get current features from data loader
            features = self._get_ml_features()

            # Get ML prediction
            ml_recommendation = self.ml_engine.generate_trade_recommendation(
                features,
                rule_evaluation={'direction': evaluation.strategy_name}
            )

            ml_pred = ml_recommendation['ml_prediction']
            confidence_level = ml_recommendation['confidence_level']

            # In shadow mode, only add insights to reasons (don't change behavior)
            if ML_SHADOW_MODE:
                # Prepend ML insights to reasons
                ml_reason = f"ML: {ml_pred['predicted_direction']} ({ml_pred['confidence']*100:.0f}% confidence)"
                evaluation.reasons = [ml_reason] + evaluation.reasons[:2]  # Keep max 3 reasons

                logger.info(f"ML Shadow: {ml_pred['predicted_direction']} @ {ml_pred['confidence']:.1%} confidence")

            else:
                # Active mode: adjust risk based on ML confidence
                if ML_RISK_ADJUSTMENT_ENABLED and evaluation.risk_pct:
                    risk_adjustment = ml_recommendation['risk_adjustment']
                    original_risk = evaluation.risk_pct
                    evaluation.risk_pct *= risk_adjustment

                    logger.info(f"ML Risk Adjustment: {original_risk:.2%} → {evaluation.risk_pct:.2%} ({risk_adjustment:.1f}x)")

                # Add ML reasoning
                ml_reason = f"ML: {confidence_level} confidence {ml_pred['predicted_direction']}"
                evaluation.reasons = [ml_reason] + evaluation.reasons[:2]

        except Exception as e:
            logger.error(f"ML inference failed: {e}")
            # Don't fail the evaluation if ML fails

        return evaluation

    def _get_setup_info(self, orb_name: str) -> Optional[Dict]:
        """
        Get setup information from validated_setups database.

        Args:
            orb_name: ORB time ("0900", "1000", "1100", "2300", "0030")

        Returns:
            Dictionary with tier, win_rate, avg_r, annual_trades, annual_expectancy
            None if setup not found in database
        """
        try:
            from setup_detector import SetupDetector

            # Get config for this ORB
            config = self.orb_configs.get(orb_name)
            if not config:
                return None

            rr = config.get("rr")
            sl_mode = config.get("sl_mode")

            # Query database for this setup
            detector = SetupDetector(instrument=self.instrument)
            all_setups = detector.get_all_validated_setups(self.instrument)

            # Find matching setup
            for setup in all_setups:
                if (setup["orb_time"] == orb_name and
                    setup["rr"] == rr and
                    setup["sl_mode"] == sl_mode):

                    # Calculate annual expectancy
                    annual_expectancy = setup["avg_r"] * setup["annual_trades"]

                    return {
                        "tier": setup["tier"],
                        "win_rate": setup["win_rate"],
                        "avg_r": setup["avg_r"],
                        "realized_expectancy": setup.get("realized_expectancy"),
                        "avg_win_r": setup.get("avg_win_r"),
                        "avg_loss_r": setup.get("avg_loss_r"),
                        "annual_trades": setup["annual_trades"],
                        "annual_expectancy": annual_expectancy
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to get setup info for {orb_name}: {e}")
            return None

    def _get_ml_features(self) -> Dict:
        """
        Extract features from data loader for ML inference.

        Returns:
            Dictionary of features ready for ML model
        """
        from datetime import datetime

        now_local = datetime.now(TZ_LOCAL)

        # Get session levels
        asia_hl = self._get_today_asia_levels()
        london_hl = self._get_today_london_levels()

        # Get ORB data if available
        orb_data = {}
        # Note: LiveDataLoader doesn't have get_orb() method
        # ORB data comes from state variables instead
        # Skip this section for now - ML will use available features

        # Determine current ORB context
        current_hour = now_local.hour
        current_orb_time = None
        if 9 <= current_hour < 10:
            current_orb_time = "0900"
        elif 10 <= current_hour < 11:
            current_orb_time = "1000"
        elif 11 <= current_hour < 18:
            current_orb_time = "1100"
        elif 18 <= current_hour < 23:
            current_orb_time = "1800"
        elif 23 <= current_hour or current_hour < 1:
            current_orb_time = "2300"
        else:
            current_orb_time = "0030"

        # Build feature dictionary
        features = {
            'date_local': now_local.strftime('%Y-%m-%d'),
            'instrument': self.instrument,
            'orb_time': current_orb_time,
            'session_context': 'ASIA' if 9 <= current_hour < 18 else 'LONDON' if 18 <= current_hour < 23 else 'NY',
        }

        # Add session data
        if asia_hl:
            features['asia_high'] = asia_hl['high']
            features['asia_low'] = asia_hl['low']
            features['asia_range'] = asia_hl['high'] - asia_hl['low']

        if london_hl:
            features['london_high'] = london_hl['high']
            features['london_low'] = london_hl['low']
            features['london_range'] = london_hl['high'] - london_hl['low']

        # Add current ORB if available
        if current_orb_time and current_orb_time in orb_data:
            orb = orb_data[current_orb_time]
            features['orb_high'] = orb['high']
            features['orb_low'] = orb['low']
            features['orb_size'] = orb['high'] - orb['low']

        features['atr_14'] = 0.0
        features['rsi_14'] = 50.0

        return features


if __name__ == "__main__":
    # Test strategy engine
    logging.basicConfig(level=logging.INFO)

    from data_loader import LiveDataLoader

    loader = LiveDataLoader("MGC")
    loader.backfill_from_gold_db("../data/db/gold.db", days=2)

    engine = StrategyEngine(loader)

    evaluation = engine.evaluate_all()

    print("\n" + "="*80)
    print("STRATEGY EVALUATION")
    print("="*80)
    print(f"Strategy: {evaluation.strategy_name}")
    print(f"State: {evaluation.state.value}")
    print(f"Action: {evaluation.action.value}")
    print(f"\nReasons:")
    for reason in evaluation.reasons:
        print(f"  - {reason}")
    print(f"\nNext Instruction: {evaluation.next_instruction}")
    print("="*80)

    loader.close()
