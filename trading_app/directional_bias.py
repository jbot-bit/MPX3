"""
DIRECTIONAL BIAS DETECTOR

Predicts ORB breakout direction using contextual signals available BEFORE the break.

Based on analysis from PREDICT_DIRECTION.py showing:
- ORB position in Asia range is strongest predictor
- Price structure vs prior ORBs matters
- Momentum alignment has some signal

ZERO LOOKAHEAD - All signals available before ORB breaks.
"""

import duckdb
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DirectionalBias:
    """Container for directional bias prediction"""

    def __init__(
        self,
        preferred_direction: Optional[str] = None,
        confidence: str = "NEUTRAL",
        signals: Optional[Dict] = None,
        reasoning: Optional[str] = None
    ):
        self.preferred_direction = preferred_direction  # "UP", "DOWN", or None
        self.confidence = confidence  # "STRONG", "MODERATE", "WEAK", "NEUTRAL"
        self.signals = signals or {}
        self.reasoning = reasoning or ""

    def has_bias(self) -> bool:
        """Returns True if there's a directional preference"""
        return self.preferred_direction is not None

    def get_emoji(self) -> str:
        """Get emoji indicator for direction"""
        if not self.preferred_direction:
            return "↔️"
        return "⬆️" if self.preferred_direction == "UP" else "⬇️"

    def get_color(self) -> str:
        """Get color for UI display"""
        if not self.preferred_direction:
            return "#888888"
        return "#22c55e" if self.preferred_direction == "UP" else "#ef4444"


class DirectionalBiasDetector:
    """
    Detects directional bias for ORB setups using contextual signals.

    Specializes in 11:00 ORB (most data available), but can be extended
    to other ORB times.
    """

    def __init__(self, db_path: Optional[str] = None):
        # Cloud-aware: db_path parameter is ignored in cloud mode
        # Connections handled by get_database_connection()
        self.db_path = db_path  # Legacy parameter, kept for compatibility

        # Lazy connection - only connect when needed
        self._con = None

    def get_directional_bias(
        self,
        instrument: str,
        orb_time: str,
        orb_high: float,
        orb_low: float,
        current_date: datetime
    ) -> DirectionalBias:
        """
        Predict directional bias for an ORB setup.

        Args:
            instrument: Instrument symbol (e.g., "MGC")
            orb_time: ORB time (e.g., "1100")
            orb_high: ORB high price
            orb_low: ORB low price
            current_date: Current trading date

        Returns:
            DirectionalBias object with prediction
        """

        # Only predict for 11:00 ORB (we have strong signals for this)
        if orb_time != "1100":
            return DirectionalBias(
                confidence="NEUTRAL",
                reasoning=f"Directional prediction only available for 11:00 ORB (not {orb_time})"
            )

        # Get context from database
        context = self._get_orb_context(instrument, current_date)

        if not context:
            return DirectionalBias(
                confidence="NEUTRAL",
                reasoning="Insufficient historical context to predict direction"
            )

        # Calculate signals
        signals = self._calculate_signals(orb_high, orb_low, context)

        # Make prediction
        return self._predict_direction(signals)

    def _get_connection(self):
        """Get database connection, creating it if needed (cloud-aware)"""
        if self._con is None:
            try:
                # Use cloud-aware connection
                from cloud_mode import get_database_connection
                self._con = get_database_connection()

                if self._con is None:
                    logger.warning("Database connection unavailable. Directional bias disabled.")
                    return None

                logger.info("Connected to database for directional bias")
            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                return None

        return self._con

    def _get_orb_context(self, instrument: str, current_date: datetime) -> Optional[Dict]:
        """Get ORB context from database (Asia session, prior ORBs)"""

        try:
            con = self._get_connection()
            if con is None:
                return None

            # Get today's data (if available)
            query = """
                SELECT
                    asia_high,
                    asia_low,
                    asia_range,
                    orb_0900_high,
                    orb_0900_low,
                    orb_0900_size,
                    orb_0900_break_dir,
                    orb_1000_high,
                    orb_1000_low,
                    orb_1000_size,
                    orb_1000_break_dir
                FROM daily_features
                WHERE instrument = ?
                  AND date_local = ?
            """

            result = con.execute(query, [instrument, current_date.date()]).fetchone()

            if not result:
                return None

            return {
                'asia_high': result[0],
                'asia_low': result[1],
                'asia_range': result[2],
                'orb_0900_high': result[3],
                'orb_0900_low': result[4],
                'orb_0900_size': result[5],
                'orb_0900_break_dir': result[6],
                'orb_1000_high': result[7],
                'orb_1000_low': result[8],
                'orb_1000_size': result[9],
                'orb_1000_break_dir': result[10],
            }

        except Exception as e:
            logger.error(f"Error getting ORB context: {e}")
            return None

    def _calculate_signals(self, orb_high: float, orb_low: float, context: Dict) -> Dict:
        """Calculate directional signals from ORB and context"""

        orb_mid = (orb_high + orb_low) / 2

        signals = {}

        # Signal 1: ORB position in Asia range (STRONGEST)
        if context['asia_range'] and context['asia_range'] > 0:
            position = (orb_mid - context['asia_low']) / context['asia_range']
            signals['orb_position_in_asia'] = position

            if position < 0.4:
                signals['position_signal'] = "UP"
                signals['position_strength'] = "STRONG"
            elif position >= 0.6:
                signals['position_signal'] = "DOWN"
                signals['position_strength'] = "STRONG"
            else:
                signals['position_signal'] = None
                signals['position_strength'] = "WEAK"

        # Signal 2: ORB vs 09:00 ORB high (price structure)
        if context['orb_0900_high']:
            diff = orb_high - context['orb_0900_high']
            signals['orb_vs_0900_high'] = diff

            if diff >= 0.5:
                signals['structure_signal'] = "UP"
            elif diff <= 0.1:
                signals['structure_signal'] = "DOWN"
            else:
                signals['structure_signal'] = None

        # Signal 3: Momentum alignment (09:00 + 10:00)
        orb_0900_dir = context.get('orb_0900_break_dir')
        orb_1000_dir = context.get('orb_1000_break_dir')

        if orb_0900_dir and orb_1000_dir:
            if orb_0900_dir == "UP" and orb_1000_dir == "UP":
                signals['momentum_signal'] = "UP"
                signals['momentum_strength'] = "MODERATE"
            elif orb_0900_dir == "DOWN" and orb_1000_dir == "DOWN":
                signals['momentum_signal'] = "DOWN"
                signals['momentum_strength'] = "MODERATE"
            else:
                signals['momentum_signal'] = None
                signals['momentum_strength'] = "WEAK"

        return signals

    def _predict_direction(self, signals: Dict) -> DirectionalBias:
        """Make directional prediction from signals"""

        # Weight signals (position is strongest)
        position_signal = signals.get('position_signal')
        structure_signal = signals.get('structure_signal')
        momentum_signal = signals.get('momentum_signal')

        votes = []
        reasoning_parts = []

        # Position signal (strongest - 2 votes)
        if position_signal:
            votes.extend([position_signal, position_signal])
            pos = signals['orb_position_in_asia']
            if position_signal == "UP":
                reasoning_parts.append(f"ORB in LOWER Asia range ({pos:.1%}) - historically breaks UP")
            else:
                reasoning_parts.append(f"ORB in UPPER Asia range ({pos:.1%}) - historically breaks DOWN")

        # Structure signal (1 vote)
        if structure_signal:
            votes.append(structure_signal)
            diff = signals['orb_vs_0900_high']
            if structure_signal == "UP":
                reasoning_parts.append(f"ORB {diff:+.1f} pts above 09:00 high - bullish structure")
            else:
                reasoning_parts.append(f"ORB near/below 09:00 high ({diff:+.1f} pts) - bearish structure")

        # Momentum signal (1 vote)
        if momentum_signal:
            votes.append(momentum_signal)
            if momentum_signal == "UP":
                reasoning_parts.append("Prior ORBs (09:00 + 10:00) both broke UP - momentum continuation")
            else:
                reasoning_parts.append("Prior ORBs (09:00 + 10:00) both broke DOWN - momentum continuation")

        # Count votes
        if not votes:
            return DirectionalBias(
                confidence="NEUTRAL",
                signals=signals,
                reasoning="No clear directional signals detected"
            )

        up_votes = votes.count("UP")
        down_votes = votes.count("DOWN")
        total_votes = len(votes)

        # Determine direction and confidence
        if up_votes > down_votes:
            direction = "UP"
            vote_pct = up_votes / total_votes
        elif down_votes > up_votes:
            direction = "DOWN"
            vote_pct = down_votes / total_votes
        else:
            return DirectionalBias(
                confidence="NEUTRAL",
                signals=signals,
                reasoning="Conflicting signals - no clear directional bias"
            )

        # Confidence level
        if vote_pct >= 0.75:
            confidence = "STRONG"
        elif vote_pct >= 0.6:
            confidence = "MODERATE"
        else:
            confidence = "WEAK"

        reasoning = " | ".join(reasoning_parts)

        return DirectionalBias(
            preferred_direction=direction,
            confidence=confidence,
            signals=signals,
            reasoning=reasoning
        )


def render_directional_bias_indicator(bias: DirectionalBias):
    """Render directional bias indicator for Streamlit UI"""
    import streamlit as st

    if not bias.has_bias():
        st.info("↔️ **NEUTRAL** - No clear directional bias detected")
        if bias.reasoning:
            st.caption(bias.reasoning)
        return

    # Color based on direction
    color = bias.get_color()

    # Emoji based on confidence
    if bias.confidence == "STRONG":
        strength_emoji = "🔥"
    elif bias.confidence == "MODERATE":
        strength_emoji = "⚡"
    else:
        strength_emoji = "💡"

    # Display
    direction_emoji = bias.get_emoji()

    st.markdown(f"""
    <div style="
        padding: 15px;
        border-left: 5px solid {color};
        background: linear-gradient(90deg, {color}22, transparent);
        border-radius: 5px;
        margin: 10px 0;
    ">
        <div style="font-size: 24px; font-weight: bold; color: {color}; margin-bottom: 5px;">
            {direction_emoji} {bias.preferred_direction} Direction Preferred {strength_emoji}
        </div>
        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">
            Confidence: <strong>{bias.confidence}</strong>
        </div>
        <div style="font-size: 13px; color: #444; line-height: 1.5;">
            {bias.reasoning}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Show signals in expander
    with st.expander("📊 View Signal Details"):
        if bias.signals:
            for key, value in bias.signals.items():
                if isinstance(value, float):
                    st.write(f"**{key}**: {value:.3f}")
                else:
                    st.write(f"**{key}**: {value}")
