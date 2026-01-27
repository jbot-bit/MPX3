"""
ML Performance Monitoring Dashboard

Streamlit page for monitoring ML model performance.

Usage:
    streamlit run trading_app/ml_dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml_monitoring.outcome_logger import OutcomeLogger
from config import ML_ENABLED, ML_SHADOW_MODE

# Page config
st.set_page_config(
    page_title="ML Performance Dashboard",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 ML Performance Monitoring Dashboard")

if not ML_ENABLED:
    st.error("ML system is disabled. Enable ML_ENABLED in config.py to use this dashboard.")
    st.stop()

# Initialize logger
logger = OutcomeLogger()

# Sidebar controls
st.sidebar.title("Controls")
lookback_days = st.sidebar.slider("Lookback Period (days)", 1, 90, 30)
instrument = st.sidebar.selectbox("Instrument", ["MGC", "NQ", "MPL"], index=0)

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown("### Model Info")
st.sidebar.info(f"""
**Model**: Directional Classifier v2
**Status**: {'Shadow Mode' if ML_SHADOW_MODE else 'Active'}
**Trained**: Jan 17, 2026
**Accuracy**: 50% (balanced)
""")

# Main content
tabs = st.tabs(["📊 Performance", "📈 Predictions", "🎯 Accuracy", "⚙️ Model Info"])

# ============================================================================
# TAB 1: PERFORMANCE OVERVIEW
# ============================================================================
with tabs[0]:
    st.header("Performance Overview")

    # Get recent performance
    performance = logger.get_recent_performance(days=lookback_days, instrument=instrument)

    if performance['total_predictions'] == 0:
        st.warning(f"No predictions found for {instrument} in the last {lookback_days} days.")
        st.info("ML predictions will appear here once the system starts making predictions in the trading app.")
    else:
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Directional Accuracy",
                f"{performance['avg_accuracy']:.1%}",
                delta=f"{performance['avg_accuracy'] - 0.50:.1%} vs baseline",
                help="Percentage of correct directional predictions"
            )

        with col2:
            st.metric(
                "Win Rate",
                f"{performance['avg_win_rate']:.1%}",
                delta=f"{performance['avg_win_rate'] - 0.50:.1%} vs 50%",
                help="Percentage of profitable trades"
            )

        with col3:
            st.metric(
                "Avg R-Multiple",
                f"{performance['avg_r_multiple']:.2f}R",
                help="Average R-multiple achieved"
            )

        with col4:
            st.metric(
                "Total Predictions",
                f"{int(performance['total_predictions'])}",
                help="Number of predictions made"
            )

        st.divider()

        # Get daily performance data for charts
        try:
            import duckdb
            conn = duckdb.connect("../data/db/gold.db")

            daily_data = conn.execute("""
                SELECT
                    date_local,
                    directional_accuracy,
                    win_rate,
                    avg_r_multiple,
                    total_predictions
                FROM ml_performance
                WHERE date_local >= CURRENT_DATE - INTERVAL ? DAY
                  AND instrument = ?
                ORDER BY date_local ASC
            """, [lookback_days, instrument]).fetchdf()

            conn.close()

            if not daily_data.empty:
                # Accuracy over time
                st.subheader("Directional Accuracy Over Time")
                fig_accuracy = go.Figure()

                fig_accuracy.add_trace(go.Scatter(
                    x=daily_data['date_local'],
                    y=daily_data['directional_accuracy'] * 100,
                    mode='lines+markers',
                    name='Accuracy',
                    line=dict(color='#0066cc', width=2),
                    marker=dict(size=8)
                ))

                # Add baseline
                fig_accuracy.add_hline(
                    y=50,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text="50% Baseline",
                    annotation_position="right"
                )

                fig_accuracy.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Accuracy (%)",
                    yaxis_range=[0, 100],
                    height=300,
                    margin=dict(l=0, r=0, t=0, b=0)
                )

                st.plotly_chart(fig_accuracy, use_container_width=True)

                # Win rate and R-multiple
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Win Rate Over Time")
                    fig_winrate = go.Figure()

                    fig_winrate.add_trace(go.Scatter(
                        x=daily_data['date_local'],
                        y=daily_data['win_rate'] * 100,
                        mode='lines+markers',
                        name='Win Rate',
                        line=dict(color='#28a745', width=2),
                        marker=dict(size=8)
                    ))

                    fig_winrate.add_hline(
                        y=50,
                        line_dash="dash",
                        line_color="gray"
                    )

                    fig_winrate.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Win Rate (%)",
                        yaxis_range=[0, 100],
                        height=300,
                        margin=dict(l=0, r=0, t=0, b=0)
                    )

                    st.plotly_chart(fig_winrate, use_container_width=True)

                with col2:
                    st.subheader("Average R-Multiple Over Time")
                    fig_r = go.Figure()

                    fig_r.add_trace(go.Scatter(
                        x=daily_data['date_local'],
                        y=daily_data['avg_r_multiple'],
                        mode='lines+markers',
                        name='Avg R',
                        line=dict(color='#fd7e14', width=2),
                        marker=dict(size=8)
                    ))

                    fig_r.add_hline(
                        y=0,
                        line_dash="dash",
                        line_color="gray"
                    )

                    fig_r.update_layout(
                        xaxis_title="Date",
                        yaxis_title="R-Multiple",
                        height=300,
                        margin=dict(l=0, r=0, t=0, b=0)
                    )

                    st.plotly_chart(fig_r, use_container_width=True)

        except Exception as e:
            st.error(f"Error loading daily performance data: {e}")


# ============================================================================
# TAB 2: PREDICTION LOG
# ============================================================================
with tabs[1]:
    st.header("Recent Predictions")

    try:
        import duckdb
        conn = duckdb.connect("../data/db/gold.db")

        predictions = conn.execute("""
            SELECT
                timestamp_utc,
                orb_time,
                strategy_name,
                predicted_direction,
                confidence,
                confidence_level,
                actual_direction,
                actual_r_multiple,
                win,
                orb_size,
                rsi_14
            FROM ml_predictions
            WHERE instrument = ?
              AND DATE(timestamp_utc) >= CURRENT_DATE - INTERVAL ? DAY
            ORDER BY timestamp_utc DESC
            LIMIT 100
        """, [instrument, lookback_days]).fetchdf()

        conn.close()

        if predictions.empty:
            st.info("No predictions logged yet. Predictions will appear here once the trading app makes its first ML prediction.")
        else:
            # Summary stats
            col1, col2, col3 = st.columns(3)

            with col1:
                correct = (predictions['predicted_direction'] == predictions['actual_direction']).sum()
                total = len(predictions[predictions['actual_direction'].notna()])
                accuracy = 100 * correct / total if total > 0 else 0
                st.metric("Predictions", len(predictions), help="Total predictions in period")

            with col2:
                completed = len(predictions[predictions['actual_direction'].notna()])
                st.metric("Completed", completed, help="Predictions with outcomes logged")

            with col3:
                pending = len(predictions[predictions['actual_direction'].isna()])
                st.metric("Pending", pending, help="Awaiting outcome")

            st.divider()

            # Display predictions table
            display_df = predictions.copy()
            display_df['timestamp_utc'] = pd.to_datetime(display_df['timestamp_utc']).dt.strftime('%Y-%m-%d %H:%M')
            display_df['confidence'] = (display_df['confidence'] * 100).round(1).astype(str) + '%'

            # Color code outcomes
            def color_outcome(row):
                if pd.isna(row['actual_direction']):
                    return ['background-color: #f8f9fa'] * len(row)
                elif row['predicted_direction'] == row['actual_direction']:
                    return ['background-color: #d1e7dd'] * len(row)
                else:
                    return ['background-color: #f8d7da'] * len(row)

            styled_df = display_df.style.apply(color_outcome, axis=1)

            st.dataframe(
                styled_df,
                width="stretch",
                height=400
            )

            # Download button
            csv = predictions.to_csv(index=False)
            st.download_button(
                label="📥 Download Predictions CSV",
                data=csv,
                file_name=f"ml_predictions_{instrument}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error loading predictions: {e}")


# ============================================================================
# TAB 3: ACCURACY ANALYSIS
# ============================================================================
with tabs[2]:
    st.header("Accuracy Analysis")

    try:
        import duckdb
        conn = duckdb.connect("../data/db/gold.db")

        # Get completed predictions
        predictions = conn.execute("""
            SELECT
                predicted_direction,
                actual_direction,
                confidence,
                confidence_level,
                orb_time,
                win
            FROM ml_predictions
            WHERE instrument = ?
              AND actual_direction IS NOT NULL
              AND DATE(timestamp_utc) >= CURRENT_DATE - INTERVAL ? DAY
        """, [instrument, lookback_days]).fetchdf()

        conn.close()

        if predictions.empty:
            st.info("No completed predictions yet for accuracy analysis.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                # Accuracy by confidence level
                st.subheader("Accuracy by Confidence Level")

                accuracy_by_conf = predictions.groupby('confidence_level').apply(
                    lambda x: 100 * (x['predicted_direction'] == x['actual_direction']).sum() / len(x)
                ).reset_index(name='accuracy')

                fig_conf = px.bar(
                    accuracy_by_conf,
                    x='confidence_level',
                    y='accuracy',
                    labels={'confidence_level': 'Confidence Level', 'accuracy': 'Accuracy (%)'},
                    color='accuracy',
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 100]
                )

                fig_conf.add_hline(y=50, line_dash="dash", line_color="gray")
                fig_conf.update_layout(height=300, showlegend=False)

                st.plotly_chart(fig_conf, use_container_width=True)

            with col2:
                # Accuracy by ORB time
                st.subheader("Accuracy by ORB Time")

                accuracy_by_orb = predictions.groupby('orb_time').apply(
                    lambda x: 100 * (x['predicted_direction'] == x['actual_direction']).sum() / len(x)
                ).reset_index(name='accuracy')

                fig_orb = px.bar(
                    accuracy_by_orb,
                    x='orb_time',
                    y='accuracy',
                    labels={'orb_time': 'ORB Time', 'accuracy': 'Accuracy (%)'},
                    color='accuracy',
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 100]
                )

                fig_orb.add_hline(y=50, line_dash="dash", line_color="gray")
                fig_orb.update_layout(height=300, showlegend=False)

                st.plotly_chart(fig_orb, use_container_width=True)

            # Confusion matrix
            st.subheader("Confusion Matrix")

            confusion = pd.crosstab(
                predictions['predicted_direction'],
                predictions['actual_direction'],
                margins=True
            )

            st.dataframe(confusion, width="stretch")

    except Exception as e:
        st.error(f"Error in accuracy analysis: {e}")


# ============================================================================
# TAB 4: MODEL INFO
# ============================================================================
with tabs[3]:
    st.header("Model Information")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Model")
        st.markdown("""
        **Model Type**: LightGBM Multi-class Classifier
        **Version**: v_20260117_023515 (Balanced)
        **Training Date**: January 17, 2026
        **Training Data**: 3,136 samples (740 days)
        **Features**: 58 engineered features
        **Target**: Break direction (UP/DOWN/NONE)
        """)

        st.subheader("Performance Metrics")
        st.markdown("""
        **Test Accuracy**: 50.0%
        **UP Precision**: 55% | **Recall**: 62%
        **DOWN Precision**: 45% | **Recall**: 35%

        *Note: 50% accuracy is good for a balanced binary classifier.
        This model improved DOWN recall from 4% to 35% vs unbalanced version.*
        """)

    with col2:
        st.subheader("Top Features")
        st.markdown("""
        1. **orb_size** - Absolute ORB size
        2. **orb_size_pct_atr** - ORB / ATR ratio
        3. **avg_r_last_3d** - 3-day rolling R
        4. **orb_time** - Time of day
        5. **rsi_14** - RSI indicator
        6. **pre_ny_range** - Pre-NY range
        7. **ny_range** - NY session range
        8. **pre_london_range** - Pre-London range
        9. **london_asia_range_ratio** - Session comparison
        10. **atr_14** - Average True Range
        """)

        st.subheader("Configuration")
        st.markdown(f"""
        **ML Enabled**: {ML_ENABLED}
        **Shadow Mode**: {ML_SHADOW_MODE}
        **Status**: {'Predictions logged only' if ML_SHADOW_MODE else 'Active trading'}

        *Shadow mode means predictions are shown and logged but don't affect trading decisions.*
        """)

    st.divider()

    st.subheader("Model History")
    st.markdown("""
    | Version | Date | Accuracy | Notes |
    |---------|------|----------|-------|
    | v2 (Current) | 2026-01-17 | 50.0% | Balanced with class weights, improved DOWN recall |
    | v1 | 2026-01-17 | 53.98% | Unbalanced, heavily biased toward UP (96% recall) |
    """)

    st.info("""
    **Next Steps:**
    - Continue monitoring performance in shadow mode
    - Collect 90+ days of predictions for validation
    - Build entry quality and R-multiple models (Phase 3)
    - Enable automated retraining (Phase 4)
    """)

st.sidebar.divider()
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
