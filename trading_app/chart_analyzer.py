"""
Chart Analyzer - Vision-based chart analysis for strategy testing

Uses guarded Vision API through ai_guard.py (AI Source Lock enforced).
"""

import base64
import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from config import TZ_LOCAL
from setup_detector import SetupDetector
from ai_guard import guarded_vision_answer

logger = logging.getLogger(__name__)


class ChartAnalyzer:
    """Analyzes trading charts using Claude Vision (guarded through ai_guard.py)."""

    def __init__(self, instrument: str = "MGC"):
        """
        Initialize chart analyzer.

        Args:
            instrument: Trading instrument (MGC, NQ, MPL)
        """
        self.instrument = instrument
        self.setup_detector = SetupDetector()

    def is_available(self) -> bool:
        """Check if chart analysis is available (API key configured)."""
        # Check if API key is set (vision calls go through ai_guard.py)
        return os.getenv("ANTHROPIC_API_KEY") is not None

    def analyze_chart_image(self, image_bytes: bytes, image_type: str = "image/png") -> Optional[Dict]:
        """
        Analyze a chart image using guarded Vision API.

        Args:
            image_bytes: Image file bytes
            image_type: MIME type (image/png, image/jpeg)

        Returns:
            Dictionary with analysis results or None if error
        """
        if not self.is_available():
            logger.error("Chart analysis unavailable - no API key")
            return None

        try:
            # Encode image to base64
            image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

            # Construct vision prompt
            prompt = self._build_analysis_prompt()

            # Call guarded vision API (through ai_guard.py - AI Source Lock enforced)
            analysis_text = guarded_vision_answer(
                image_data_base64=image_data,
                image_type=image_type,
                user_prompt=prompt,
                instrument=self.instrument,
                visual_only=True  # No DB access, visual observations only
            )

            # Check for refusal/error messages
            if "AI LOCK MISCONFIGURED" in analysis_text or "not available" in analysis_text:
                logger.error(f"Vision guard refusal: {analysis_text}")
                return None

            # Parse response into structured format
            analysis = self._parse_analysis_response(analysis_text)

            return analysis

        except Exception as e:
            logger.error(f"Chart analysis failed: {e}")
            return None

    def _build_analysis_prompt(self) -> str:
        """Build the analysis prompt for Claude Vision."""
        return """Analyze this trading chart and extract the following information:

1. **Current Price**: What is the current/latest price shown?

2. **ORB Levels** (if visible):
   - Is there an Opening Range Breakout (ORB) marked on the chart?
   - If yes, what are the ORB high and low levels?
   - What is the ORB size (difference)?

3. **Timeframe**: What timeframe is this chart? (1m, 5m, 15m, 1h, etc.)

4. **Session Context**: Based on the time shown, what trading session is this?
   - Asia session (09:00-18:00 Brisbane time)
   - London session (18:00-23:00 Brisbane time)
   - NY session (23:00-02:00 next day Brisbane time)

5. **Market Structure**:
   - Is price trending or ranging?
   - Are there clear support/resistance levels visible?
   - Is price above or below the ORB (if ORB exists)?

6. **Potential Setups**: Based on what you see, what trading setups might be applicable?
   - ORB breakout (long or short)?
   - Range bound (wait for breakout)?
   - Inside ORB range (preparing)?

Format your response as:
```
CURRENT_PRICE: $XXXX.XX
ORB_HIGH: $XXXX.XX (or "Not visible")
ORB_LOW: $XXXX.XX (or "Not visible")
ORB_SIZE: X.XX pts (or "N/A")
TIMEFRAME: Xm/Xh
SESSION: Asia/London/NY
STRUCTURE: Trending up/down / Ranging
PRICE_VS_ORB: Above ORB / Below ORB / Inside ORB / No ORB visible
POTENTIAL_SETUPS: [List applicable setups]
NOTES: [Any other relevant observations]
```

Be precise with price levels. If you can't clearly see something, say "Not visible" or "Unclear"."""

    def _parse_analysis_response(self, response_text: str) -> Dict:
        """
        Parse Claude's analysis response into structured format.

        Args:
            response_text: Raw response from Claude

        Returns:
            Dictionary with parsed analysis
        """
        analysis = {
            "current_price": None,
            "orb_high": None,
            "orb_low": None,
            "orb_size": None,
            "timeframe": None,
            "session": None,
            "structure": None,
            "price_vs_orb": None,
            "potential_setups": [],
            "notes": None,
            "raw_response": response_text
        }

        try:
            lines = response_text.split('\n')

            for line in lines:
                line = line.strip()

                if line.startswith("CURRENT_PRICE:"):
                    price_str = line.split(":", 1)[1].strip().replace("$", "").replace(",", "")
                    try:
                        analysis["current_price"] = float(price_str)
                    except ValueError:
                        pass

                elif line.startswith("ORB_HIGH:"):
                    level_str = line.split(":", 1)[1].strip().replace("$", "").replace(",", "")
                    if "Not visible" not in level_str and "Unclear" not in level_str:
                        try:
                            analysis["orb_high"] = float(level_str)
                        except ValueError:
                            pass

                elif line.startswith("ORB_LOW:"):
                    level_str = line.split(":", 1)[1].strip().replace("$", "").replace(",", "")
                    if "Not visible" not in level_str and "Unclear" not in level_str:
                        try:
                            analysis["orb_low"] = float(level_str)
                        except ValueError:
                            pass

                elif line.startswith("ORB_SIZE:"):
                    size_str = line.split(":", 1)[1].strip().replace("pts", "").strip()
                    if "N/A" not in size_str:
                        try:
                            analysis["orb_size"] = float(size_str)
                        except ValueError:
                            pass

                elif line.startswith("TIMEFRAME:"):
                    analysis["timeframe"] = line.split(":", 1)[1].strip()

                elif line.startswith("SESSION:"):
                    analysis["session"] = line.split(":", 1)[1].strip()

                elif line.startswith("STRUCTURE:"):
                    analysis["structure"] = line.split(":", 1)[1].strip()

                elif line.startswith("PRICE_VS_ORB:"):
                    analysis["price_vs_orb"] = line.split(":", 1)[1].strip()

                elif line.startswith("POTENTIAL_SETUPS:"):
                    setups_str = line.split(":", 1)[1].strip()
                    # Parse list (could be comma-separated or bulleted)
                    if setups_str and setups_str != "[]":
                        analysis["potential_setups"] = [s.strip() for s in setups_str.replace("[", "").replace("]", "").split(",")]

                elif line.startswith("NOTES:"):
                    analysis["notes"] = line.split(":", 1)[1].strip()

        except Exception as e:
            logger.error(f"Failed to parse analysis response: {e}")

        return analysis

    def recommend_strategies(self, analysis: Dict, top_n: int = 5) -> List[Dict]:
        """
        Recommend strategies based on chart analysis.

        Args:
            analysis: Chart analysis dictionary
            top_n: Number of top strategies to return

        Returns:
            List of strategy recommendations (dicts with setup info + reasoning)
        """
        if not analysis:
            return []

        recommendations = []

        try:
            # Get all validated setups for this instrument
            all_setups = self.setup_detector.get_all_validated_setups(self.instrument)

            if not all_setups:
                logger.warning(f"No validated setups found for {self.instrument}")
                return []

            # Score and rank setups
            for setup in all_setups:
                score = self._score_setup(setup, analysis)

                if score > 0:
                    reasoning = self._generate_reasoning(setup, analysis)

                    recommendations.append({
                        "setup": setup,
                        "score": score,
                        "reasoning": reasoning
                    })

            # Sort by score (descending)
            recommendations.sort(key=lambda x: x["score"], reverse=True)

            # Return top N
            return recommendations[:top_n]

        except Exception as e:
            logger.error(f"Failed to recommend strategies: {e}")
            return []

    def _score_setup(self, setup: Dict, analysis: Dict) -> float:
        """
        Score a setup based on how well it matches the chart analysis.

        Higher score = better match.

        Args:
            setup: Setup dict from validated_setups
            analysis: Chart analysis dict

        Returns:
            Score (0-100)
        """
        score = 0.0

        # Base score from tier
        tier_scores = {
            "S+": 50,
            "S": 40,
            "A": 30,
            "B": 20,
            "C": 10
        }
        score += tier_scores.get(setup.get("tier", "C"), 10)

        # Bonus for expectancy
        avg_r = setup.get("avg_r", 0)
        if avg_r > 0.4:
            score += 15
        elif avg_r > 0.3:
            score += 10
        elif avg_r > 0.2:
            score += 5

        # Bonus for high win rate
        win_rate = setup.get("win_rate", 0)
        if win_rate > 50:
            score += 10
        elif win_rate > 40:
            score += 5

        # Bonus for session match
        orb_time = setup.get("orb_time", "")
        session_from_analysis = analysis.get("session", "").upper()

        if session_from_analysis:
            if orb_time in ["0900", "1000", "1100"] and "ASIA" in session_from_analysis:
                score += 10
            elif orb_time == "1800" and "LONDON" in session_from_analysis:
                score += 10
            elif orb_time in ["2300", "0030"] and "NY" in session_from_analysis:
                score += 10

        # Bonus if ORB is visible in chart
        if analysis.get("orb_high") and analysis.get("orb_low"):
            score += 10

            # Check if setup matches the visible ORB
            orb_size_analysis = analysis.get("orb_size")
            if orb_size_analysis:
                # If there's a filter, check if it would pass
                orb_filter = setup.get("orb_size_filter")
                if orb_filter:
                    # Need ATR to calculate, assume ~16 points for MGC
                    assumed_atr = 16.0
                    ratio = orb_size_analysis / assumed_atr
                    if ratio < orb_filter:
                        score += 15  # Bonus for passing filter

        # Bonus if price position matches potential entry
        price_vs_orb = analysis.get("price_vs_orb", "").lower()
        if "above orb" in price_vs_orb:
            score += 5  # Could be LONG breakout
        elif "below orb" in price_vs_orb:
            score += 5  # Could be SHORT breakout
        elif "inside orb" in price_vs_orb:
            score += 3  # Preparing for breakout

        return score

    def _generate_reasoning(self, setup: Dict, analysis: Dict) -> str:
        """
        Generate human-readable reasoning for why this setup is recommended.

        Args:
            setup: Setup dict
            analysis: Chart analysis dict

        Returns:
            Reasoning string
        """
        reasons = []

        # Setup quality
        tier = setup.get("tier", "C")
        win_rate = setup.get("win_rate", 0)
        avg_r = setup.get("avg_r", 0)
        annual_trades = setup.get("annual_trades", 0)

        reasons.append(f"{tier} tier setup with {win_rate:.1f}% win rate")

        # Expectancy
        if avg_r > 0:
            annual_exp = avg_r * annual_trades
            reasons.append(f"Expectancy: +{avg_r:.2f}R per trade (+{annual_exp:.0f}R/year)")

        # Session match
        orb_time = setup.get("orb_time", "")
        session_from_analysis = analysis.get("session", "")
        if session_from_analysis:
            orb_times_by_session = {
                "ASIA": ["0900", "1000", "1100"],
                "LONDON": ["1800"],
                "NY": ["2300", "0030"]
            }
            for session_name, times in orb_times_by_session.items():
                if orb_time in times and session_name.upper() in session_from_analysis.upper():
                    reasons.append(f"Matches current {session_name} session")
                    break

        # ORB visibility
        if analysis.get("orb_high") and analysis.get("orb_low"):
            reasons.append("ORB levels visible on chart")

            # Filter status
            orb_filter = setup.get("orb_size_filter")
            if orb_filter:
                reasons.append(f"Has size filter ({orb_filter:.3f} × ATR) for quality control")
            else:
                reasons.append("No size filter (trades all ORBs)")

        # Price position
        price_vs_orb = analysis.get("price_vs_orb", "").lower()
        if "above orb" in price_vs_orb:
            reasons.append("Price above ORB - potential LONG breakout setup")
        elif "below orb" in price_vs_orb:
            reasons.append("Price below ORB - potential SHORT breakout setup")
        elif "inside orb" in price_vs_orb:
            reasons.append("Price inside ORB - wait for breakout signal")

        # Frequency
        reasons.append(f"Frequency: ~{annual_trades} trades/year")

        return " | ".join(reasons)


def analyze_and_recommend(image_bytes: bytes, instrument: str = "MGC", image_type: str = "image/png", top_n: int = 5) -> Tuple[Optional[Dict], List[Dict]]:
    """
    Convenience function to analyze chart and recommend strategies.

    Args:
        image_bytes: Chart image bytes
        instrument: Trading instrument
        image_type: Image MIME type
        top_n: Number of recommendations

    Returns:
        Tuple of (analysis dict, recommendations list)
    """
    analyzer = ChartAnalyzer(instrument=instrument)

    if not analyzer.is_available():
        return None, []

    analysis = analyzer.analyze_chart_image(image_bytes, image_type)
    recommendations = analyzer.recommend_strategies(analysis, top_n) if analysis else []

    return analysis, recommendations
