"""
SETUP SCANNER - Multi-instrument setup monitoring
Scans all validated setups across MGC, NQ, and MPL simultaneously.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

from setup_detector import SetupDetector
from config import MGC_ORB_CONFIGS, NQ_ORB_CONFIGS, MPL_ORB_CONFIGS
from config import MGC_ORB_SIZE_FILTERS, NQ_ORB_SIZE_FILTERS, MPL_ORB_SIZE_FILTERS


class SetupStatus:
    """Setup status constants"""
    WAITING = "WAITING"       # ORB window hasn't opened yet
    ACTIVE = "ACTIVE"         # ORB window is open right now
    READY = "READY"           # ORB formed, filter passed, waiting for break
    TRIGGERED = "TRIGGERED"   # Price broke ORB, setup is live
    EXPIRED = "EXPIRED"       # ORB window passed, no break
    SKIPPED = "SKIPPED"       # Setup is configured to skip


class SetupScanner:
    """
    Comprehensive setup scanner for all instruments.
    Monitors all 17 validated setups (6 MGC + 5 NQ + 6 MPL) simultaneously.
    """

    def __init__(self, db_path: Optional[str] = None):
        # Pass None for cloud-aware path detection
        self.detector = SetupDetector(db_path)
        self.tz = ZoneInfo("Australia/Brisbane")

        # ORB time definitions (hour, minute, duration)
        self.orb_times = {
            "0900": (9, 0, 5),
            "1000": (10, 0, 5),
            "1100": (11, 0, 5),
            "1800": (18, 0, 5),
            "2300": (23, 0, 5),
            "0030": (0, 30, 5),
        }

    def get_all_instruments(self) -> List[str]:
        """Get list of all instruments"""
        return ["MGC", "NQ", "MPL"]

    def get_orb_config(self, instrument: str, orb_name: str) -> Optional[Dict]:
        """Get ORB configuration for instrument"""
        if instrument == "MGC":
            return MGC_ORB_CONFIGS.get(orb_name)
        elif instrument == "NQ":
            return NQ_ORB_CONFIGS.get(orb_name)
        elif instrument == "MPL":
            return MPL_ORB_CONFIGS.get(orb_name)
        return None

    def get_orb_filter(self, instrument: str, orb_name: str) -> Optional[float]:
        """Get ORB size filter for instrument"""
        if instrument == "MGC":
            return MGC_ORB_SIZE_FILTERS.get(orb_name)
        elif instrument == "NQ":
            return NQ_ORB_SIZE_FILTERS.get(orb_name)
        elif instrument == "MPL":
            return MPL_ORB_SIZE_FILTERS.get(orb_name)
        return None

    def get_orb_window_times(self, orb_name: str, reference_time: datetime) -> Tuple[datetime, datetime]:
        """
        Get ORB window start and end times.

        Args:
            orb_name: ORB identifier (e.g., "0900")
            reference_time: Reference datetime with timezone

        Returns:
            Tuple of (start_time, end_time)
        """
        hour, minute, duration = self.orb_times[orb_name]

        start_time = reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=duration)

        # Handle midnight crossing (0030)
        if hour == 0 and reference_time.hour >= 12:
            start_time += timedelta(days=1)
            end_time += timedelta(days=1)

        # If we're past this ORB today, show tomorrow's
        if reference_time > end_time:
            start_time += timedelta(days=1)
            end_time += timedelta(days=1)

        return start_time, end_time

    def determine_setup_status(
        self,
        instrument: str,
        orb_name: str,
        now: datetime,
        current_price: Optional[float] = None,
        orb_high: Optional[float] = None,
        orb_low: Optional[float] = None,
        atr: Optional[float] = None
    ) -> str:
        """
        Determine current status of a setup.

        Args:
            instrument: Instrument symbol
            orb_name: ORB identifier
            now: Current datetime
            current_price: Current market price
            orb_high: ORB high (if formed)
            orb_low: ORB low (if formed)
            atr: Current ATR

        Returns:
            Setup status constant
        """
        # Skip contextual strategies (they don't have fixed ORB times)
        if orb_name in ["CASCADE", "SINGLE_LIQ"]:
            return SetupStatus.SKIPPED

        # Check if SKIP
        config = self.get_orb_config(instrument, orb_name)
        if config and config.get("tier") == "SKIP":
            return SetupStatus.SKIPPED

        # Get ORB window times
        start_time, end_time = self.get_orb_window_times(orb_name, now)

        # Check if in ORB window
        if start_time <= now <= end_time:
            return SetupStatus.ACTIVE

        # Check if ORB hasn't opened yet
        if now < start_time:
            return SetupStatus.WAITING

        # ORB has passed
        if orb_high is None or orb_low is None:
            return SetupStatus.EXPIRED

        # Check if setup triggered (price broke ORB)
        if current_price is not None:
            if current_price > orb_high or current_price < orb_low:
                return SetupStatus.TRIGGERED

        # Check if filter passed (ready for break)
        if atr is not None:
            orb_size = orb_high - orb_low
            filter_threshold = self.get_orb_filter(instrument, orb_name)

            if filter_threshold is None:
                # No filter, always ready
                return SetupStatus.READY

            if orb_size < (atr * filter_threshold):
                return SetupStatus.READY
            else:
                return SetupStatus.EXPIRED  # Failed filter

        return SetupStatus.READY  # Assume ready if no filter info

    def scan_all_setups(
        self,
        current_prices: Dict[str, float],
        current_atrs: Dict[str, float],
        orb_data: Dict[str, Dict[str, Dict]] = None
    ) -> pd.DataFrame:
        """
        Scan all setups across all instruments.

        Args:
            current_prices: Dict of {instrument: price}
            current_atrs: Dict of {instrument: atr}
            orb_data: Optional dict of {instrument: {orb_name: {high, low, size}}}

        Returns:
            DataFrame with all setup statuses
        """
        now = datetime.now(self.tz)
        results = []

        for instrument in self.get_all_instruments():
            # Get all setups for this instrument
            setups = self.detector.get_all_validated_setups(instrument)

            current_price = current_prices.get(instrument)
            atr = current_atrs.get(instrument)

            for setup in setups:
                orb_name = setup['orb_time']

                # Get ORB data if available
                orb_high = None
                orb_low = None
                orb_size = None

                if orb_data and instrument in orb_data and orb_name in orb_data[instrument]:
                    orb_info = orb_data[instrument][orb_name]
                    orb_high = orb_info.get('high')
                    orb_low = orb_info.get('low')
                    orb_size = orb_info.get('size')

                # Determine status
                status = self.determine_setup_status(
                    instrument, orb_name, now, current_price, orb_high, orb_low, atr
                )

                # Skip contextual strategies (they don't have fixed ORB times)
                if status == SetupStatus.SKIPPED:
                    continue

                # Get window times
                start_time, end_time = self.get_orb_window_times(orb_name, now)

                # Calculate time until/since ORB
                if status == SetupStatus.WAITING:
                    time_delta = start_time - now
                    time_str = self._format_timedelta(time_delta, prefix="-")
                elif status == SetupStatus.ACTIVE:
                    time_delta = end_time - now
                    time_str = self._format_timedelta(time_delta, prefix="")
                elif status in [SetupStatus.READY, SetupStatus.TRIGGERED]:
                    time_delta = now - end_time
                    time_str = self._format_timedelta(time_delta, prefix="+")
                else:
                    time_str = "—"

                # Check filter status
                filter_threshold = self.get_orb_filter(instrument, orb_name)
                if filter_threshold is None:
                    filter_status = "None"
                elif orb_size is not None and atr is not None:
                    if orb_size < (atr * filter_threshold):
                        filter_status = "✅ PASS"
                    else:
                        filter_status = "❌ FAIL"
                else:
                    filter_status = "Pending"

                # Price vs ORB
                if current_price and orb_high and orb_low:
                    if current_price > orb_high:
                        price_vs_orb = f"{current_price:.1f} (above)"
                    elif current_price < orb_low:
                        price_vs_orb = f"{current_price:.1f} (below)"
                    else:
                        price_vs_orb = f"{current_price:.1f} (inside)"
                elif current_price:
                    price_vs_orb = f"{current_price:.1f}"
                else:
                    price_vs_orb = "—"

                # Build result row
                results.append({
                    "Instrument": instrument,
                    "ORB": orb_name,
                    "Status": status,
                    "Time": time_str,
                    "Tier": setup['tier'],
                    "Win%": f"{setup['win_rate']:.1f}%",
                    "Exp": f"+{setup['avg_r']:.2f}R",
                    "Filter": filter_status,
                    "Price": price_vs_orb,
                    "ORB High": f"{orb_high:.1f}" if orb_high else "—",
                    "ORB Low": f"{orb_low:.1f}" if orb_low else "—",
                    "ORB Size": f"{orb_size:.1f}" if orb_size else "—",
                    "RR": f"{setup['rr']:.1f}R" if setup['rr'] else "—",
                    "SL Mode": setup['sl_mode'],
                    "Annual": setup['annual_trades'],
                    # Raw values for sorting/filtering
                    "_status_order": self._status_order(status),
                    "_tier_order": self._tier_order(setup['tier']),
                    "_setup_obj": setup
                })

        df = pd.DataFrame(results)

        # Sort by status (critical first), then tier, then instrument
        if not df.empty:
            df = df.sort_values(by=["_status_order", "_tier_order", "Instrument", "ORB"])

        return df

    def _format_timedelta(self, td: timedelta, prefix: str = "") -> str:
        """Format timedelta as human-readable string"""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{prefix}{hours}h {minutes}m"
        elif minutes > 0:
            return f"{prefix}{minutes}m {seconds}s"
        else:
            return f"{prefix}{seconds}s"

    def _status_order(self, status: str) -> int:
        """Get sort order for status"""
        order = {
            SetupStatus.TRIGGERED: 0,   # Highest priority
            SetupStatus.ACTIVE: 1,
            SetupStatus.READY: 2,
            SetupStatus.WAITING: 3,
            SetupStatus.EXPIRED: 4,
            SetupStatus.SKIPPED: 5,     # Lowest priority
        }
        return order.get(status, 99)

    def _tier_order(self, tier: str) -> int:
        """Get sort order for tier"""
        order = {
            "S+": 0,
            "S": 1,
            "A": 2,
            "B": 3,
            "C": 4,
        }
        return order.get(tier, 99)


# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_setup_scanner_tab(
    scanner: SetupScanner,
    current_prices: Dict[str, float],
    current_atrs: Dict[str, float],
    orb_data: Dict[str, Dict[str, Dict]] = None
):
    """
    Render the setup scanner tab in Streamlit.

    Args:
        scanner: SetupScanner instance
        current_prices: Dict of {instrument: price}
        current_atrs: Dict of {instrument: atr}
        orb_data: Optional ORB data
    """
    st.header("🔍 Setup Scanner")
    st.markdown("Real-time monitoring of all 17 validated setups across MGC, NQ, and MPL")

    # Scan all setups
    df = scanner.scan_all_setups(current_prices, current_atrs, orb_data)

    if df.empty:
        st.warning("No setups found")
        return

    # Filter controls
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        show_only_elite = st.checkbox("Elite Only (S+/S)", value=False, key="scanner_elite_only")

    with col2:
        show_only_active = st.checkbox("Active/Ready Only", value=False, key="scanner_active_only")

    with col3:
        hide_skipped = st.checkbox("Hide SKIP", value=True, key="scanner_hide_skip")

    with col4:
        instrument_filter = st.selectbox(
            "Instrument",
            ["All", "MGC", "NQ", "MPL"],
            key="scanner_instrument_filter"
        )

    # Apply filters
    filtered_df = df.copy()

    if show_only_elite:
        filtered_df = filtered_df[filtered_df["Tier"].isin(["S+", "S"])]

    if show_only_active:
        filtered_df = filtered_df[filtered_df["Status"].isin([SetupStatus.ACTIVE, SetupStatus.READY, SetupStatus.TRIGGERED])]

    if hide_skipped:
        filtered_df = filtered_df[filtered_df["Status"] != SetupStatus.SKIPPED]

    if instrument_filter != "All":
        filtered_df = filtered_df[filtered_df["Instrument"] == instrument_filter]

    # Summary metrics
    st.divider()
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        triggered_count = len(filtered_df[filtered_df["Status"] == SetupStatus.TRIGGERED])
        st.metric("🎯 Triggered", triggered_count)

    with col2:
        active_count = len(filtered_df[filtered_df["Status"] == SetupStatus.ACTIVE])
        st.metric("🔥 Active", active_count)

    with col3:
        ready_count = len(filtered_df[filtered_df["Status"] == SetupStatus.READY])
        st.metric("✅ Ready", ready_count)

    with col4:
        waiting_count = len(filtered_df[filtered_df["Status"] == SetupStatus.WAITING])
        st.metric("⏳ Waiting", waiting_count)

    with col5:
        elite_count = len(filtered_df[filtered_df["Tier"].isin(["S+", "S"])])
        st.metric("⭐ Elite", elite_count)

    st.divider()

    # Display table with color coding
    if not filtered_df.empty:
        # Style the dataframe
        def style_status(val):
            colors = {
                SetupStatus.TRIGGERED: "background-color: #d1e7dd; font-weight: bold;",
                SetupStatus.ACTIVE: "background-color: #fff3cd; font-weight: bold;",
                SetupStatus.READY: "background-color: #cfe2ff;",
                SetupStatus.WAITING: "background-color: #e2e3e5;",
                SetupStatus.EXPIRED: "background-color: #f8d7da;",
                SetupStatus.SKIPPED: "background-color: #e2e3e5; color: #6c757d;",
            }
            return colors.get(val, "")

        def style_tier(val):
            colors = {
                "S+": "background-color: #ffd700; font-weight: bold;",
                "S": "background-color: #c0c0c0; font-weight: bold;",
                "A": "background-color: #cd7f32;",
            }
            return colors.get(val, "")

        # Select display columns
        display_cols = [
            "Instrument", "ORB", "Status", "Time", "Tier", "Win%", "Exp",
            "Filter", "Price", "ORB High", "ORB Low", "ORB Size"
        ]

        display_df = filtered_df[display_cols].copy()

        # Apply styling
        styled_df = display_df.style.applymap(
            style_status, subset=["Status"]
        ).applymap(
            style_tier, subset=["Tier"]
        )

        st.dataframe(
            styled_df,
            width="stretch",
            height=600
        )

        # Detailed view for selected setup
        st.divider()
        st.subheader("📋 Setup Details")

        selected_idx = st.selectbox(
            "Select setup for details:",
            range(len(filtered_df)),
            format_func=lambda i: f"{filtered_df.iloc[i]['Instrument']} {filtered_df.iloc[i]['ORB']} ({filtered_df.iloc[i]['Status']})",
            key="scanner_selected_setup"
        )

        if selected_idx is not None:
            selected_row = filtered_df.iloc[selected_idx]
            setup = selected_row["_setup_obj"]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"""
                **{selected_row['Instrument']} {selected_row['ORB']} ORB**

                **Status**: {selected_row['Status']}
                **Tier**: {selected_row['Tier']}
                **Time**: {selected_row['Time']}

                **Performance**:
                - Win Rate: {setup['win_rate']:.1f}%
                - Avg R: {setup['avg_r']:+.3f}R
                - RR: {setup['rr']:.1f}R
                - SL Mode: {setup['sl_mode']}
                - Annual Trades: ~{setup['annual_trades']}
                """)

            with col2:
                st.markdown(f"""
                **Current Market**:
                - Price: {selected_row['Price']}
                - ORB High: {selected_row['ORB High']}
                - ORB Low: {selected_row['ORB Low']}
                - ORB Size: {selected_row['ORB Size']} pts

                **Filter**: {selected_row['Filter']}

                **Notes**:
                {setup.get('notes', 'No notes available')}
                """)

    else:
        st.info("No setups match current filters")

    # Auto-refresh notice
    st.caption("💡 Scanner updates automatically with chart refresh")
