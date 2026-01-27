"""
0030 NY OPEN ORB - VISUAL TRADING DASHBOARD

Quick visual reference for trading the 0030 ORB.
Shows ORB range, entry, stop, target with clear chart.

Usage: streamlit run orb_0030_visual.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time

st.set_page_config(page_title="0030 ORB Visual", layout="wide")

st.title("📊 0030 NY OPEN ORB - VISUAL TRADING DASHBOARD")

# Sidebar inputs
st.sidebar.header("📝 INPUT ORB DETAILS")

instrument = st.sidebar.selectbox("Instrument", ["MGC", "NQ", "MPL"], index=0)
orb_high = st.sidebar.number_input("ORB High", value=2650.0, step=0.1, format="%.1f")
orb_low = st.sidebar.number_input("ORB Low", value=2648.0, step=0.1, format="%.1f")
current_price = st.sidebar.number_input("Current Price", value=2651.0, step=0.1, format="%.1f")

# Get validated setup info
tick_sizes = {"MGC": 0.1, "NQ": 0.25, "MPL": 0.1}
tick_values = {"MGC": 1.0, "NQ": 0.50, "MPL": 0.50}
point_values = {"MGC": 10.0, "NQ": 2.0, "MPL": 5.0}

tick_size = tick_sizes[instrument]
tick_value = tick_values[instrument]
point_value = point_values[instrument]

# Validated setup details
setup_info = {
    "MGC": {"win_rate": 68.7, "avg_r": 0.202, "tier": "A", "sl_mode": "HALF",
            "filter": "ORB<11.2% ATR", "notes": "NY cash open - filter ORBs <11.2% ATR"},
    "NQ": {"win_rate": 66.0, "avg_r": 0.320, "tier": "S+", "sl_mode": "HALF",
           "filter": "Large ORBs (>=149 ticks)", "notes": "BEST NQ ORB - Large ORBs only"},
    "MPL": {"win_rate": 60.6, "avg_r": 0.211, "tier": "A", "sl_mode": "FULL",
            "filter": "No filter", "notes": "NY cash open - Full-size contract ($50/pt)"}
}

setup = setup_info[instrument]

# Calculate ORB details
orb_size = orb_high - orb_low
orb_mid = (orb_high + orb_low) / 2

# Determine if ORB broken
if current_price > orb_high:
    direction = "UP (LONG)"
    entry_price = current_price
    if setup["sl_mode"] == "HALF":
        stop_price = orb_mid
    else:
        stop_price = orb_low
    target_price = entry_price + (entry_price - stop_price)
    color = "green"
    broken = True
elif current_price < orb_low:
    direction = "DOWN (SHORT)"
    entry_price = current_price
    if setup["sl_mode"] == "HALF":
        stop_price = orb_mid
    else:
        stop_price = orb_high
    target_price = entry_price - (stop_price - entry_price)
    color = "red"
    broken = True
else:
    direction = "FORMING (Wait for break)"
    entry_price = None
    stop_price = None
    target_price = None
    color = "yellow"
    broken = False

# Display setup info
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Tier", f"{setup['tier']}")
    st.metric("Win Rate", f"{setup['win_rate']}%")

with col2:
    st.metric("Avg R", f"+{setup['avg_r']:.3f}R")
    st.metric("SL Mode", setup['sl_mode'])

with col3:
    st.metric("ORB Size", f"{orb_size:.1f}")
    st.metric("Direction", direction)

with col4:
    risk_amount = abs(entry_price - stop_price) if entry_price else orb_size
    st.metric("Risk (pts)", f"{risk_amount:.1f}")
    st.metric("Filter", setup['filter'])

st.info(f"ℹ️ {setup['notes']}")

# Chart
st.header("📈 VISUAL CHART")

fig = go.Figure()

# ORB High line
fig.add_trace(go.Scatter(
    x=[0, 1], y=[orb_high, orb_high],
    mode='lines',
    name='ORB High',
    line=dict(color='blue', width=3, dash='dash')
))

# ORB Low line
fig.add_trace(go.Scatter(
    x=[0, 1], y=[orb_low, orb_low],
    mode='lines',
    name='ORB Low',
    line=dict(color='blue', width=3, dash='dash')
))

# ORB Mid line (if HALF SL mode)
if setup["sl_mode"] == "HALF":
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[orb_mid, orb_mid],
        mode='lines',
        name='ORB Mid (Stop)',
        line=dict(color='purple', width=2, dash='dot')
    ))

# Current price
fig.add_trace(go.Scatter(
    x=[0.5], y=[current_price],
    mode='markers+text',
    name='Current Price',
    marker=dict(size=20, color=color, symbol='star'),
    text=[f"${current_price:.1f}"],
    textposition="top center"
))

# If broken, show entry/stop/target
if broken:
    # Entry
    fig.add_trace(go.Scatter(
        x=[0.3], y=[entry_price],
        mode='markers+text',
        name='Entry',
        marker=dict(size=15, color=color),
        text=[f"Entry: ${entry_price:.1f}"],
        textposition="middle right"
    ))

    # Stop
    fig.add_trace(go.Scatter(
        x=[0.3], y=[stop_price],
        mode='markers+text',
        name='Stop',
        marker=dict(size=15, color='red', symbol='x'),
        text=[f"Stop: ${stop_price:.1f}"],
        textposition="middle right"
    ))

    # Target
    fig.add_trace(go.Scatter(
        x=[0.7], y=[target_price],
        mode='markers+text',
        name='Target',
        marker=dict(size=15, color='gold', symbol='diamond'),
        text=[f"Target: ${target_price:.1f}"],
        textposition="middle left"
    ))

# Layout
fig.update_layout(
    title=f"{instrument} 0030 ORB Visual Reference",
    xaxis=dict(showticklabels=False, showgrid=False),
    yaxis=dict(title="Price", side="right"),
    height=600,
    showlegend=True,
    hovermode='y'
)

st.plotly_chart(fig, use_container_width=True)

# Trade execution details
if broken:
    st.header("🎯 TRADE EXECUTION")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Entry Details")
        st.write(f"**Direction**: {direction}")
        st.write(f"**Entry Price**: ${entry_price:.1f}")
        st.write(f"**Stop Price**: ${stop_price:.1f}")
        st.write(f"**Target Price**: ${target_price:.1f}")
        st.write(f"**Risk**: {abs(entry_price - stop_price):.1f} points")
        st.write(f"**Reward**: {abs(target_price - entry_price):.1f} points")
        st.write(f"**R:R**: 1.0 (1:1)")

    with col2:
        st.subheader("Position Sizing ($25k Account)")

        # Calculate position size for 0.5% risk
        account_size = 25000
        risk_pct = 0.5
        risk_dollars = account_size * (risk_pct / 100)

        risk_points = abs(entry_price - stop_price)
        risk_per_contract = risk_points * point_value

        contracts = int(risk_dollars / risk_per_contract)
        actual_risk = contracts * risk_per_contract

        st.write(f"**Account Size**: ${account_size:,}")
        st.write(f"**Risk %**: {risk_pct}%")
        st.write(f"**Risk $**: ${risk_dollars:.0f}")
        st.write(f"**Risk/Contract**: ${risk_per_contract:.0f}")
        st.write(f"**Contracts**: {contracts}")
        st.write(f"**Actual Risk**: ${actual_risk:.0f} ({actual_risk/account_size*100:.2f}%)")

        if contracts > 0:
            potential_profit = contracts * (abs(target_price - entry_price) * point_value)
            st.success(f"**Potential Profit**: ${potential_profit:.0f}")
else:
    st.warning("⏳ ORB NOT BROKEN YET - Wait for close outside range")
    st.write(f"**ORB Range**: ${orb_low:.1f} - ${orb_high:.1f}")
    st.write(f"**Current Price**: ${current_price:.1f}")
    st.write("**Action**: Wait for FIRST 1-min close above {:.1f} (LONG) or below {:.1f} (SHORT)".format(orb_high, orb_low))

# Performance stats
st.header("📊 VALIDATED PERFORMANCE")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Historical Win Rate", f"{setup['win_rate']}%")

with col2:
    st.metric("Average Return", f"+{setup['avg_r']:.3f}R")

with col3:
    annual_trades = {"MGC": 33, "NQ": 100, "MPL": 246}
    st.metric("Annual Trades", f"~{annual_trades[instrument]}")

# Quick reference
st.header("📋 QUICK REFERENCE")
st.write("""
**0030 ORB Rules:**
1. Wait for 00:30-00:35 range to form (5 minutes)
2. Enter on first 5-min CLOSE outside range
3. Stop: ORB midpoint (MGC/NQ) or opposite edge (MPL)
4. Target: 1R (same distance as risk)
5. Risk: 0.25-0.50% of account

**Filters:**
- MGC: Skip if ORB > 11.2% of ATR(20)
- NQ: Prefer large ORBs (≥149 ticks)
- MPL: No filter needed

**Contract Specs:**
- MGC: $10/point, $1/tick
- NQ: $2/point, $0.50/tick
- MPL: $5/point, $0.50/tick (FULL-SIZE $50/point contract!)
""")
