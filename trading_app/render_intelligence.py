"""
Render market intelligence recommendations in the UI.
"""

import streamlit as st
from market_intelligence import TradingRecommendation, RecommendationPriority


def render_intelligent_recommendation(recommendation: TradingRecommendation):
    """
    Render the intelligent trading recommendation prominently.

    Shows BEST opportunity RIGHT NOW with clear reasoning.
    """

    # Priority colors and styles
    priority_styles = {
        RecommendationPriority.CRITICAL: {
            "bg": "linear-gradient(135deg, #ff4444 0%, #cc0000 100%)",
            "border": "#ff0000",
            "text": "white",
            "icon": "🚨"
        },
        RecommendationPriority.HIGH: {
            "bg": "linear-gradient(135deg, #ff8800 0%, #ff6600 100%)",
            "border": "#ff8800",
            "text": "white",
            "icon": "⚡"
        },
        RecommendationPriority.MEDIUM: {
            "bg": "linear-gradient(135deg, #4CAF50 0%, #45a049 100%)",
            "border": "#4CAF50",
            "text": "white",
            "icon": "👀"
        },
        RecommendationPriority.LOW: {
            "bg": "linear-gradient(135deg, #2196F3 0%, #1976D2 100%)",
            "border": "#2196F3",
            "text": "white",
            "icon": "ℹ️"
        },
        RecommendationPriority.NONE: {
            "bg": "linear-gradient(135deg, #9E9E9E 0%, #757575 100%)",
            "border": "#9E9E9E",
            "text": "white",
            "icon": "⏸️"
        }
    }

    style = priority_styles.get(recommendation.priority, priority_styles[RecommendationPriority.NONE])

    # Render recommendation box
    st.markdown(f"""
    <div style="
        background: {style['bg']};
        border: 4px solid {style['border']};
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 32px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        animation: pulse 2s infinite;
    ">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="font-size: 64px; margin-bottom: 16px;">{style['icon']}</div>
            <div style="font-size: 32px; font-weight: bold; color: {style['text']}; margin-bottom: 8px;">
                {recommendation.action}
            </div>
            <div style="font-size: 20px; color: {style['text']}; opacity: 0.9;">
                {recommendation.headline}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Reasoning section
    st.subheader("🧠 WHY")
    for reason in recommendation.reasoning:
        st.write(f"• {reason}")

    st.divider()

    # Next action
    st.subheader("✅ WHAT TO DO")
    if recommendation.time_critical:
        st.error(f"⏰ **TIME CRITICAL**: {recommendation.next_action}")
    else:
        st.info(f"📋 {recommendation.next_action}")

    # Show setup details if available
    if recommendation.setup:
        st.divider()
        st.subheader("📊 Setup Details")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Tier", recommendation.setup.tier)

        with col2:
            st.metric("Win Rate", f"{recommendation.setup.win_rate:.1f}%")

        with col3:
            st.metric("Avg R", f"{recommendation.setup.avg_r:+.3f}R")

        with col4:
            st.metric("Target", f"{recommendation.setup.rr}R")

        # ORB details if active
        if recommendation.setup.orb_high and recommendation.setup.orb_low:
            st.divider()
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("ORB High", f"{recommendation.setup.orb_high:.1f}")

            with col2:
                st.metric("ORB Low", f"{recommendation.setup.orb_low:.1f}")

            with col3:
                st.metric("ORB Size", f"{recommendation.setup.orb_size:.1f}")

            if recommendation.setup.breakout_direction:
                if recommendation.setup.breakout_direction == "LONG":
                    st.success(f"🚀 **LONG** setup - Price above {recommendation.setup.orb_high:.1f}")
                elif recommendation.setup.breakout_direction == "SHORT":
                    st.error(f"📉 **SHORT** setup - Price below {recommendation.setup.orb_low:.1f}")
                else:
                    st.warning(f"⏳ **INSIDE RANGE** - Waiting for breakout")

    # Show alternatives if available
    if recommendation.alternatives:
        st.divider()
        with st.expander("🔀 Alternative Opportunities"):
            for i, alt in enumerate(recommendation.alternatives[:3], 1):
                st.write(f"**#{i+1}**: {alt.instrument} {alt.orb_time} ({alt.tier} tier) - {alt.opportunity_type.value}")
                if alt.minutes_away > 0:
                    st.write(f"   ⏰ In {alt.minutes_away} minutes")


def render_intelligence_panel(
    market_intelligence,
    instrument: str,
    current_price: float,
    current_atr: float,
    db_path: str = "../data/db/gold.db"
):
    """
    Full intelligence panel with market analysis and recommendation.
    """

    # Analyze market conditions
    market_condition = market_intelligence.analyze_market_conditions(
        instrument=instrument,
        current_price=current_price,
        current_atr=current_atr
    )

    # Get validated setups for this instrument
    from setup_detector import SetupDetector
    detector = SetupDetector(db_path)
    setups = detector.get_all_validated_setups(instrument)

    if not setups:
        st.warning(f"No validated setups found for {instrument}")
        return

    # Rank opportunities
    opportunities = market_intelligence.rank_opportunities(
        setups=setups,
        market_condition=market_condition,
        orb_data=None  # Real-time ORB data would go here
    )

    # Generate recommendation
    recommendation = market_intelligence.generate_recommendation(
        opportunities=opportunities,
        market_condition=market_condition
    )

    # Render
    render_intelligent_recommendation(recommendation)
