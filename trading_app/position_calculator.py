"""
POSITION SIZE CALCULATOR - Live Trading Component
==================================================

Read-only position sizing calculator for Live Trading tab.

CRITICAL RULES:
- Read from cost_model.py ONLY
- NO writes to database
- NO configuration changes
- Show true risk % (for prop firms)

CANONICAL: Uses cost_model.py for all costs
"""

import streamlit as st
import logging
from typing import Dict, Optional
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.cost_model import get_cost_model

logger = logging.getLogger(__name__)


def render_position_calculator(active_setups: list):
    """
    Render position size calculator for Live Trading.

    Reads from cost_model.py for all costs (CANONICAL).

    Args:
        active_setups: List of active setup dicts with:
            - instrument
            - orb_time
            - entry_price
            - stop_price
            - rr
            - sl_mode
    """
    st.subheader("💰 Position Size Calculator")

    st.caption("""
    Calculate position size based on risk tolerance.
    All costs read from canonical cost_model.py.
    """)

    # Account inputs
    col1, col2 = st.columns(2)

    with col1:
        account_size = st.number_input(
            "Account Size ($)",
            min_value=1000.0,
            max_value=1000000.0,
            value=50000.0,
            step=1000.0,
            help="Total account equity"
        )

        risk_pct = st.number_input(
            "Risk %",
            min_value=0.1,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Percentage of account to risk per trade"
        )

    with col2:
        max_drawdown = st.number_input(
            "Max Drawdown ($) - Optional",
            min_value=0.0,
            max_value=account_size,
            value=0.0,
            step=100.0,
            help="For prop firms: max allowed drawdown (leave 0 for standard account)"
        )

    st.divider()

    # Setup selection
    if not active_setups:
        st.warning("⚠️ No active setups available. Go to Live Trading tab to see active setups.")
        return

    # Create setup dropdown options
    setup_options = []
    for idx, setup in enumerate(active_setups):
        label = f"{setup['instrument']} {setup['orb_time']} RR={setup['rr']} {setup.get('direction', 'BOTH')}"
        setup_options.append(label)

    selected_setup_idx = st.selectbox(
        "Select Active Setup",
        range(len(setup_options)),
        format_func=lambda i: setup_options[i]
    )

    setup = active_setups[selected_setup_idx]

    st.divider()

    # Calculate position size
    try:
        result = calculate_position_size(
            account_size=account_size,
            risk_pct=risk_pct,
            setup=setup,
            max_drawdown=max_drawdown if max_drawdown > 0 else None
        )

        # Display results
        st.markdown("#### 📊 Results")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Position Size",
                f"{result['contracts']} contract{'s' if result['contracts'] != 1 else ''}",
                help="Number of contracts to trade"
            )

        with col2:
            st.metric(
                "Risk per Contract",
                f"${result['risk_per_contract']:.2f}",
                help="Total risk (stop distance + costs)"
            )

        with col3:
            st.metric(
                "Total Risk",
                f"${result['total_risk']:.2f}",
                delta=f"{result['total_risk_pct']:.2f}% of account"
            )

        # Prop firm true risk %
        if result['true_risk_pct'] is not None:
            st.info(f"🏢 **Prop Firm True Risk**: {result['true_risk_pct']:.2f}% of max drawdown")

        # Cost breakdown
        with st.expander("💵 Cost Breakdown", expanded=False):
            st.markdown(f"""
            **Instrument**: {setup['instrument']}

            **Stop Distance**: ${result['stop_distance_dollars']:.2f}
            - Entry: ${setup.get('entry_price', 0):.2f}
            - Stop: ${setup.get('stop_price', 0):.2f}
            - Points: {abs(setup.get('entry_price', 0) - setup.get('stop_price', 0)):.2f}

            **Transaction Costs** (from cost_model.py):
            - Commission RT: ${result['commission']:.2f}
            - Slippage: ${result['slippage']:.2f}
            - Spread: ${result['spread']:.2f}
            - **Total Costs**: ${result['total_costs']:.2f}

            **Risk Calculation**:
            - Stop Loss: ${result['stop_distance_dollars']:.2f}
            - Costs: ${result['total_costs']:.2f}
            - **Total Risk per Contract**: ${result['risk_per_contract']:.2f}
            """)

    except Exception as e:
        st.error(f"❌ Calculation failed: {e}")
        logger.error(f"Position calculator error: {e}", exc_info=True)


def calculate_position_size(
    account_size: float,
    risk_pct: float,
    setup: Dict,
    max_drawdown: Optional[float] = None
) -> Dict[str, float]:
    """
    Calculate position size using canonical cost_model.py.

    Args:
        account_size: Total account equity ($)
        risk_pct: Risk percentage (1.0 = 1%)
        setup: Active setup dict
        max_drawdown: Optional max drawdown for prop firms

    Returns:
        Dict with:
            - contracts: Number of contracts
            - risk_per_contract: Risk per contract ($)
            - total_risk: Total risk ($)
            - total_risk_pct: Total risk as % of account
            - true_risk_pct: True risk % (for prop firms)
            - stop_distance_dollars: Stop distance in $
            - commission: Commission cost
            - slippage: Slippage cost
            - spread: Spread cost
            - total_costs: Total transaction costs
    """
    instrument = setup['instrument']

    # Get canonical cost model
    cost_model = get_cost_model(instrument)

    # Calculate stop distance in dollars
    entry_price = setup.get('entry_price', 0)
    stop_price = setup.get('stop_price', 0)
    stop_distance_points = abs(entry_price - stop_price)
    stop_distance_dollars = stop_distance_points * cost_model['point_value']

    # Calculate transaction costs (CANONICAL)
    commission = cost_model['commission_rt']
    slippage = cost_model['slippage_ticks'] * cost_model['tick_value'] * 2  # Entry + exit
    spread = cost_model.get('spread_double', 0)  # Already doubled in cost_model
    total_costs = commission + slippage + spread

    # Risk per contract = stop loss + costs
    risk_per_contract = stop_distance_dollars + total_costs

    # Calculate position size
    risk_amount = account_size * (risk_pct / 100)
    contracts = int(risk_amount / risk_per_contract)

    # Ensure at least 1 contract if risk allows
    if contracts == 0 and risk_amount >= risk_per_contract:
        contracts = 1

    # Calculate total risk
    total_risk = contracts * risk_per_contract
    total_risk_pct = (total_risk / account_size) * 100

    # Calculate true risk % for prop firms
    true_risk_pct = None
    if max_drawdown and max_drawdown > 0:
        true_risk_pct = (total_risk / max_drawdown) * 100

    return {
        'contracts': contracts,
        'risk_per_contract': risk_per_contract,
        'total_risk': total_risk,
        'total_risk_pct': total_risk_pct,
        'true_risk_pct': true_risk_pct,
        'stop_distance_dollars': stop_distance_dollars,
        'commission': commission,
        'slippage': slippage,
        'spread': spread,
        'total_costs': total_costs
    }
