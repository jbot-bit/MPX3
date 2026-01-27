"""
MARKET INTELLIGENCE ENGINE
Live trading copilot that analyzes conditions and recommends best opportunities.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OpportunityType(Enum):
    """Types of trading opportunities"""
    ACTIVE_BREAKOUT = "ACTIVE_BREAKOUT"  # ORB broke, enter now
    ACTIVE_FORMING = "ACTIVE_FORMING"    # ORB forming, watch
    UPCOMING_SOON = "UPCOMING_SOON"       # < 30 min away
    UPCOMING_LATER = "UPCOMING_LATER"     # 30-120 min away
    NO_OPPORTUNITY = "NO_OPPORTUNITY"     # Nothing happening


class RecommendationPriority(Enum):
    """Priority levels for recommendations"""
    CRITICAL = "CRITICAL"  # Act immediately
    HIGH = "HIGH"          # Prepare now
    MEDIUM = "MEDIUM"      # Watch soon
    LOW = "LOW"            # Informational
    NONE = "NONE"          # No action needed


@dataclass
class MarketCondition:
    """Current market state"""
    current_time: datetime
    session: str  # ASIA, LONDON, NY
    active_orbs: List[str]  # ORBs in 0-30 min window
    forming_orbs: List[str]  # ORBs in 0-5 min formation window
    upcoming_orbs: List[Tuple[str, int]]  # (orb_name, minutes_away)

    # Market metrics
    instrument: str
    current_price: float
    current_atr: float
    volatility_level: str  # LOW, NORMAL, HIGH


@dataclass
class SetupOpportunity:
    """A trading opportunity with context"""
    instrument: str
    orb_time: str
    tier: str
    win_rate: float
    avg_r: float
    rr: float
    sl_mode: str
    orb_size_filter: Optional[float]

    # Opportunity context
    opportunity_type: OpportunityType
    minutes_away: int  # 0 for active, negative for passed
    filter_status: Optional[str]  # PASS, FAIL, PENDING

    # ORB details (if active)
    orb_high: Optional[float] = None
    orb_low: Optional[float] = None
    orb_size: Optional[float] = None
    current_price: Optional[float] = None
    breakout_direction: Optional[str] = None  # LONG, SHORT, INSIDE


@dataclass
class TradingRecommendation:
    """The AI's recommended action"""
    priority: RecommendationPriority
    action: str  # "GO LONG", "PREPARE", "WAIT", "SKIP", "STAND DOWN"
    setup: Optional[SetupOpportunity]

    # Reasoning
    headline: str  # "BEST OPPORTUNITY NOW" or "NO OPPORTUNITIES"
    reasoning: List[str]  # Bullet points explaining WHY
    next_action: str  # Clear instruction
    time_critical: bool  # If user needs to act in < 5 minutes

    # Alternatives
    alternatives: List[SetupOpportunity] = None


class MarketIntelligence:
    """
    Live trading copilot that analyzes market conditions and recommends actions.

    Thinks like: "What's the BEST opportunity RIGHT NOW and WHY?"
    """

    def __init__(self, tz_local):
        self.tz_local = tz_local
        self.orb_times = {
            "0900": (9, 0),
            "1000": (10, 0),
            "1100": (11, 0),
            "1800": (18, 0),
            "2300": (23, 0),
            "0030": (0, 30),
        }

    def analyze_market_conditions(
        self,
        instrument: str,
        current_price: float,
        current_atr: float,
        now: Optional[datetime] = None
    ) -> MarketCondition:
        """Analyze current market state"""
        if now is None:
            now = datetime.now(self.tz_local)

        # Determine session
        hour = now.hour
        if 9 <= hour < 18:
            session = "ASIA"
        elif 18 <= hour < 23:
            session = "LONDON"
        else:
            session = "NY"

        # Find active, forming, and upcoming ORBs
        active_orbs = []
        forming_orbs = []
        upcoming_orbs = []

        for orb_name, (orb_hour, orb_min) in self.orb_times.items():
            orb_start = now.replace(hour=orb_hour, minute=orb_min, second=0, microsecond=0)
            orb_end = orb_start + timedelta(minutes=5)
            orb_window_end = orb_start + timedelta(minutes=30)

            # Handle midnight crossing
            if orb_hour == 0 and now.hour >= 12:
                orb_start += timedelta(days=1)
                orb_end += timedelta(days=1)
                orb_window_end += timedelta(days=1)

            # If in past, check tomorrow
            if now > orb_window_end:
                orb_start += timedelta(days=1)
                orb_end += timedelta(days=1)
                orb_window_end += timedelta(days=1)

            # Check status
            if orb_start <= now <= orb_end:
                forming_orbs.append(orb_name)
            elif orb_end < now <= orb_window_end:
                active_orbs.append(orb_name)
            elif now < orb_start:
                minutes_away = int((orb_start - now).total_seconds() / 60)
                if minutes_away <= 120:  # Within 2 hours
                    upcoming_orbs.append((orb_name, minutes_away))

        # Sort upcoming by time
        upcoming_orbs.sort(key=lambda x: x[1])

        # Volatility level
        # High volatility = ATR > typical, Low = ATR < typical
        # For MGC: typical ATR ~35-45
        typical_atr = {"MGC": 40, "NQ": 400, "MPL": 20}
        atr_threshold = typical_atr.get(instrument, 40)

        if current_atr > atr_threshold * 1.2:
            volatility_level = "HIGH"
        elif current_atr < atr_threshold * 0.8:
            volatility_level = "LOW"
        else:
            volatility_level = "NORMAL"

        return MarketCondition(
            current_time=now,
            session=session,
            active_orbs=active_orbs,
            forming_orbs=forming_orbs,
            upcoming_orbs=upcoming_orbs,
            instrument=instrument,
            current_price=current_price,
            current_atr=current_atr,
            volatility_level=volatility_level
        )

    def rank_opportunities(
        self,
        setups: List[Dict],
        market_condition: MarketCondition,
        orb_data: Optional[Dict[str, Dict]] = None
    ) -> List[SetupOpportunity]:
        """
        Rank all setups by opportunity quality right now.

        Considers:
        - Timing (active > forming > upcoming soon > later)
        - Tier quality (S+ > S > A > B > C)
        - Filter status (pass > pending > fail)
        - Session fit
        """
        opportunities = []

        for setup in setups:
            if setup['instrument'] != market_condition.instrument:
                continue

            orb_time = setup['orb_time']

            # Determine opportunity type and timing
            if orb_time in market_condition.forming_orbs:
                opp_type = OpportunityType.ACTIVE_FORMING
                minutes_away = 0
            elif orb_time in market_condition.active_orbs:
                opp_type = OpportunityType.ACTIVE_BREAKOUT
                minutes_away = 0
            else:
                # Find in upcoming
                for upcoming_orb, mins in market_condition.upcoming_orbs:
                    if upcoming_orb == orb_time:
                        minutes_away = mins
                        if mins <= 30:
                            opp_type = OpportunityType.UPCOMING_SOON
                        else:
                            opp_type = OpportunityType.UPCOMING_LATER
                        break
                else:
                    continue  # Skip setups that already passed

            # Check filter status if we have ORB data
            filter_status = None
            orb_high = None
            orb_low = None
            orb_size = None
            current_price = None
            breakout_direction = None

            if orb_data and orb_time in orb_data:
                orb_info = orb_data[orb_time]
                orb_high = orb_info.get('high')
                orb_low = orb_info.get('low')
                orb_size = orb_info.get('size')
                current_price = market_condition.current_price

                # Check filter
                if orb_size and setup.get('orb_size_filter'):
                    filter_threshold = market_condition.current_atr * setup['orb_size_filter']
                    filter_status = "PASS" if orb_size <= filter_threshold else "FAIL"
                elif orb_size:
                    filter_status = "PASS"  # No filter = always pass
                else:
                    filter_status = "PENDING"

                # Check breakout
                if orb_high and orb_low and current_price:
                    if current_price > orb_high:
                        breakout_direction = "LONG"
                    elif current_price < orb_low:
                        breakout_direction = "SHORT"
                    else:
                        breakout_direction = "INSIDE"

            opportunities.append(SetupOpportunity(
                instrument=setup['instrument'],
                orb_time=orb_time,
                tier=setup['tier'],
                win_rate=setup['win_rate'],
                avg_r=setup['avg_r'],
                rr=setup['rr'],
                sl_mode=setup['sl_mode'],
                orb_size_filter=setup.get('orb_size_filter'),
                opportunity_type=opp_type,
                minutes_away=minutes_away,
                filter_status=filter_status,
                orb_high=orb_high,
                orb_low=orb_low,
                orb_size=orb_size,
                current_price=current_price,
                breakout_direction=breakout_direction
            ))

        # Sort by priority
        def priority_score(opp: SetupOpportunity) -> tuple:
            # Priority: breakout > forming > upcoming soon > later
            type_priority = {
                OpportunityType.ACTIVE_BREAKOUT: 1000,
                OpportunityType.ACTIVE_FORMING: 900,
                OpportunityType.UPCOMING_SOON: 800,
                OpportunityType.UPCOMING_LATER: 700,
                OpportunityType.NO_OPPORTUNITY: 0
            }

            # Tier score
            tier_score = {"S+": 100, "S": 80, "A": 60, "B": 40, "C": 20}.get(opp.tier, 0)

            # Filter penalty
            filter_penalty = 0
            if opp.filter_status == "FAIL":
                filter_penalty = -500  # Big penalty for filter fails

            # Time penalty (closer = better)
            time_penalty = opp.minutes_away

            return (
                type_priority.get(opp.opportunity_type, 0) + tier_score + filter_penalty - time_penalty,
                -opp.minutes_away,  # Tie-breaker: sooner wins
                tier_score
            )

        opportunities.sort(key=priority_score, reverse=True)

        return opportunities

    def generate_recommendation(
        self,
        opportunities: List[SetupOpportunity],
        market_condition: MarketCondition
    ) -> TradingRecommendation:
        """
        Generate clear trading recommendation with reasoning.

        Returns the BEST action to take RIGHT NOW.
        """
        if not opportunities:
            # No opportunities at all
            return TradingRecommendation(
                priority=RecommendationPriority.NONE,
                action="STAND DOWN",
                setup=None,
                headline="NO OPPORTUNITIES",
                reasoning=[
                    f"No setups available for {market_condition.instrument}",
                    f"Current session: {market_condition.session}",
                    "Check other instruments or wait"
                ],
                next_action="Review other instruments or take a break",
                time_critical=False
            )

        best = opportunities[0]

        # Determine action based on opportunity type
        if best.opportunity_type == OpportunityType.ACTIVE_BREAKOUT:
            if best.breakout_direction and best.filter_status != "FAIL":
                # GO TRADE NOW!
                return self._create_breakout_recommendation(best, opportunities[1:3])
            elif best.filter_status == "FAIL":
                # Skip this one
                return self._create_skip_recommendation(best, opportunities[1:3])
            else:
                # Wait for breakout
                return self._create_wait_recommendation(best, opportunities[1:3])

        elif best.opportunity_type == OpportunityType.ACTIVE_FORMING:
            return self._create_forming_recommendation(best, opportunities[1:3])

        elif best.opportunity_type == OpportunityType.UPCOMING_SOON:
            return self._create_upcoming_recommendation(best, opportunities[1:3])

        else:
            return self._create_standby_recommendation(best, opportunities[1:3])

    def _create_breakout_recommendation(self, setup: SetupOpportunity, alternatives: List) -> TradingRecommendation:
        """Recommend entering a breakout trade"""
        direction = setup.breakout_direction

        reasoning = [
            f"✅ {setup.orb_time} ORB broke {direction}",
            f"🏆 {setup.tier} tier setup ({setup.win_rate:.1f}% WR, {setup.avg_r:+.2f}R avg)",
            f"📊 Filter: {setup.filter_status}",
            f"🎯 Target: {setup.rr}R using {setup.sl_mode} stop"
        ]

        return TradingRecommendation(
            priority=RecommendationPriority.CRITICAL,
            action=f"GO {direction}",
            setup=setup,
            headline=f"🚀 BEST OPPORTUNITY: {setup.instrument} {setup.orb_time} {direction}",
            reasoning=reasoning,
            next_action=f"Enter {direction} at {setup.current_price:.1f}, set stop and target per TRADE PLAN tab",
            time_critical=True,
            alternatives=alternatives
        )

    def _create_skip_recommendation(self, setup: SetupOpportunity, alternatives: List) -> TradingRecommendation:
        """Recommend skipping a setup due to filter fail"""
        reasoning = [
            f"❌ {setup.orb_time} ORB filter FAILS",
            f"ORB size {setup.orb_size:.1f} too large for ATR",
            "Historical data shows poor performance with large ORBs",
            f"Next best opportunity: {alternatives[0].orb_time if alternatives else 'None'}"
        ]

        return TradingRecommendation(
            priority=RecommendationPriority.HIGH,
            action="SKIP THIS",
            setup=setup,
            headline=f"⏭️ SKIP {setup.instrument} {setup.orb_time} - Filter Fails",
            reasoning=reasoning,
            next_action=f"Wait for {alternatives[0].orb_time if alternatives else 'next'} ORB",
            time_critical=False,
            alternatives=alternatives
        )

    def _create_wait_recommendation(self, setup: SetupOpportunity, alternatives: List) -> TradingRecommendation:
        """Recommend waiting for breakout"""
        reasoning = [
            f"⏳ {setup.orb_time} ORB active - price inside range",
            f"🏆 {setup.tier} tier setup ready",
        ]

        # Add ORB levels if available
        if setup.orb_high is not None and setup.orb_low is not None:
            reasoning.append(f"High: {setup.orb_high:.1f}, Low: {setup.orb_low:.1f}")

        if setup.current_price is not None:
            reasoning.append(f"Current: {setup.current_price:.1f}")

        reasoning.append("Wait for CLOSE outside range")

        # Build next action text
        if setup.orb_high is not None and setup.orb_low is not None:
            next_action = f"Set alerts at {setup.orb_high:.1f} (long) and {setup.orb_low:.1f} (short)"
        else:
            next_action = "Wait for ORB to form"

        return TradingRecommendation(
            priority=RecommendationPriority.HIGH,
            action="WAIT FOR BREAKOUT",
            setup=setup,
            headline=f"⏳ WATCH {setup.instrument} {setup.orb_time} ORB",
            reasoning=reasoning,
            next_action=next_action,
            time_critical=True,
            alternatives=alternatives
        )

    def _create_forming_recommendation(self, setup: SetupOpportunity, alternatives: List) -> TradingRecommendation:
        """Recommend watching ORB formation"""
        reasoning = [
            f"📊 {setup.orb_time} ORB forming NOW (0-5 min window)",
            f"🏆 {setup.tier} tier setup ({setup.win_rate:.1f}% WR)",
            "Note the high and low in next 5 minutes",
            "Then wait for breakout confirmation"
        ]

        return TradingRecommendation(
            priority=RecommendationPriority.HIGH,
            action="WATCH FORMING",
            setup=setup,
            headline=f"📊 {setup.instrument} {setup.orb_time} ORB FORMING",
            reasoning=reasoning,
            next_action="Note high/low in next 5 minutes, then wait for breakout",
            time_critical=True,
            alternatives=alternatives
        )

    def _create_upcoming_recommendation(self, setup: SetupOpportunity, alternatives: List) -> TradingRecommendation:
        """Recommend preparing for upcoming ORB"""
        reasoning = [
            f"⏰ {setup.orb_time} ORB in {setup.minutes_away} minutes",
            f"🏆 {setup.tier} tier setup ({setup.win_rate:.1f}% WR, {setup.avg_r:+.2f}R avg)",
            "Prepare charts and alerts now",
            "Be ready at start time"
        ]

        priority = RecommendationPriority.HIGH if setup.minutes_away <= 10 else RecommendationPriority.MEDIUM

        return TradingRecommendation(
            priority=priority,
            action="PREPARE",
            setup=setup,
            headline=f"🔜 NEXT: {setup.instrument} {setup.orb_time} ORB in {setup.minutes_away}min",
            reasoning=reasoning,
            next_action=f"Set alert for {setup.minutes_away} minutes from now",
            time_critical=setup.minutes_away <= 10,
            alternatives=alternatives
        )

    def _create_standby_recommendation(self, setup: SetupOpportunity, alternatives: List) -> TradingRecommendation:
        """Recommend standing by"""
        reasoning = [
            f"⏰ Next opportunity: {setup.orb_time} in {setup.minutes_away} minutes",
            f"Current session: {setup.tier} tier",
            "No immediate action required"
        ]

        return TradingRecommendation(
            priority=RecommendationPriority.LOW,
            action="STAND BY",
            setup=setup,
            headline=f"⏸️ NEXT: {setup.instrument} {setup.orb_time} in {setup.minutes_away}min",
            reasoning=reasoning,
            next_action=f"Set reminder for {setup.minutes_away - 5} minutes",
            time_critical=False,
            alternatives=alternatives
        )
