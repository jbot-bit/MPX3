"""
Edge Candidates UI - Review and approval panel for edge candidates

Provides UI for viewing, filtering, and approving/rejecting edge candidates
from the edge_candidates table.

Usage:
    from edge_candidates_ui import render_edge_candidates_panel
    render_edge_candidates_panel()
"""

import streamlit as st
import pandas as pd
import json
from typing import Optional, Dict, Any
import logging

from cloud_mode import get_database_connection
from edge_candidate_utils import approve_edge_candidate, set_candidate_status

logger = logging.getLogger(__name__)


def _format_json_field(json_str: Any) -> str:
    """Format JSON field for display."""
    if json_str is None:
        return "None"

    # If already a dict, format it
    if isinstance(json_str, dict):
        return json.dumps(json_str, indent=2)

    # If string, try to parse and format
    if isinstance(json_str, str):
        try:
            data = json.loads(json_str)
            return json.dumps(data, indent=2)
        except:
            return json_str

    return str(json_str)


def _load_candidates(
    status_filter: str = "ALL",
    instrument_filter: str = "ALL",
    limit: int = 50
) -> Optional[pd.DataFrame]:
    """
    Load edge candidates from database with filters.

    Args:
        status_filter: Status filter (ALL, DRAFT, PENDING, APPROVED, REJECTED)
        instrument_filter: Instrument filter (ALL, MGC, NQ, MPL)
        limit: Maximum number of rows to return

    Returns:
        DataFrame with candidate data, or None if error
    """
    try:
        conn = get_database_connection(read_only=True)

        # Build SQL query with filters
        sql = """
            SELECT
                candidate_id,
                created_at_utc,
                instrument,
                name,
                hypothesis_text,
                status,
                test_window_start,
                test_window_end,
                approved_at,
                approved_by,
                promoted_validated_setup_id,
                promoted_by,
                promoted_at,
                notes,
                metrics_json,
                robustness_json,
                slippage_assumptions_json,
                filter_spec_json,
                feature_spec_json,
                code_version,
                data_version,
                test_config_json
            FROM edge_candidates
            WHERE 1=1
        """

        params = []

        # Add status filter
        if status_filter != "ALL":
            sql += " AND status = ?"
            params.append(status_filter)

        # Add instrument filter
        if instrument_filter != "ALL":
            sql += " AND instrument = ?"
            params.append(instrument_filter)

        # Add order and limit
        sql += " ORDER BY created_at_utc DESC LIMIT ?"
        params.append(limit)

        # Execute query
        if params:
            df = conn.execute(sql, params).df()
        else:
            df = conn.execute(sql).df()

        conn.close()

        return df

    except Exception as e:
        logger.error(f"Error loading edge candidates: {e}")
        st.error(f"Error loading candidates: {e}")
        return None


def render_edge_candidates_panel():
    """
    Render the Edge Candidates review and approval panel.

    Displays edge candidates table with filtering and action buttons
    for approving/rejecting candidates.
    """
    st.header("🔬 Edge Candidates")
    st.caption("Review and approve edge candidate strategies from research")

    # Filters row
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "Status",
            ["ALL", "DRAFT", "PENDING", "APPROVED", "REJECTED"],
            index=0,
            key="edge_status_filter"
        )

    with col2:
        instrument_filter = st.selectbox(
            "Instrument",
            ["ALL", "MGC", "NQ", "MPL"],
            index=0,
            key="edge_instrument_filter"
        )

    with col3:
        limit = st.selectbox(
            "Limit",
            [50, 100, 200, 500],
            index=0,
            key="edge_limit"
        )

    # Load button
    if st.button("🔄 Load Candidates", use_container_width=True):
        st.session_state.edge_candidates_df = _load_candidates(
            status_filter=status_filter,
            instrument_filter=instrument_filter,
            limit=limit
        )

    # Display candidates table
    if 'edge_candidates_df' not in st.session_state:
        st.info("Click 'Load Candidates' to view edge candidates from database")
        return

    df = st.session_state.edge_candidates_df

    if df is None or len(df) == 0:
        st.warning("No candidates found matching filters")
        return

    # Summary stats
    st.metric("Total Candidates", len(df))

    # Display table (subset of columns for main view)
    display_cols = [
        'candidate_id', 'created_at_utc', 'instrument', 'name',
        'status', 'test_window_start', 'test_window_end',
        'approved_at', 'approved_by'
    ]

    available_cols = [col for col in display_cols if col in df.columns]

    st.dataframe(
        df[available_cols],
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Candidate selection for actions
    st.subheader("📋 Candidate Details & Actions")

    candidate_ids = df['candidate_id'].tolist()

    selected_id = st.selectbox(
        "Select Candidate ID",
        candidate_ids,
        key="selected_candidate_id"
    )

    if selected_id:
        # Get candidate row
        candidate = df[df['candidate_id'] == selected_id].iloc[0]

        # Show details in expandable sections
        with st.expander("📄 Hypothesis", expanded=True):
            st.write(candidate.get('hypothesis_text', 'N/A'))

        col1, col2 = st.columns(2)

        with col1:
            with st.expander("📊 Metrics"):
                st.code(_format_json_field(candidate.get('metrics_json')), language='json')

        with col2:
            with st.expander("🔒 Robustness"):
                st.code(_format_json_field(candidate.get('robustness_json')), language='json')

        with st.expander("⚙️ Filter Spec"):
            st.code(_format_json_field(candidate.get('filter_spec_json')), language='json')

        with st.expander("🎯 Feature Spec"):
            st.code(_format_json_field(candidate.get('feature_spec_json')), language='json')

        with st.expander("🧪 Test Config"):
            col1, col2 = st.columns(2)
            with col1:
                st.text(f"Code Version: {candidate.get('code_version', 'N/A')}")
                st.text(f"Data Version: {candidate.get('data_version', 'N/A')}")
            with col2:
                st.code(_format_json_field(candidate.get('test_config_json')), language='json')

        # Action buttons
        st.divider()
        st.subheader("⚡ Actions")

        current_status = candidate.get('status', 'UNKNOWN')
        st.info(f"Current Status: **{current_status}**")

        # Optional notes field
        notes = st.text_area(
            "Notes (optional)",
            placeholder="Add notes for this status change...",
            key="action_notes"
        )

        # Action buttons in columns
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Approve", type="primary", use_container_width=True, disabled=(current_status == "APPROVED")):
                try:
                    approve_edge_candidate(selected_id, "Josh")
                    st.success(f"✅ Candidate {selected_id} approved!")
                    # Reload data
                    st.session_state.edge_candidates_df = _load_candidates(
                        status_filter=status_filter,
                        instrument_filter=instrument_filter,
                        limit=limit
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error approving candidate: {e}")

        with col2:
            if st.button("⏸️ Set Pending", use_container_width=True, disabled=(current_status == "PENDING")):
                try:
                    set_candidate_status(selected_id, "PENDING", notes=notes or None, actor="Josh")
                    st.success(f"⏸️ Candidate {selected_id} set to PENDING!")
                    # Reload data
                    st.session_state.edge_candidates_df = _load_candidates(
                        status_filter=status_filter,
                        instrument_filter=instrument_filter,
                        limit=limit
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error setting status: {e}")

        with col3:
            if st.button("❌ Reject", use_container_width=True, disabled=(current_status == "REJECTED")):
                try:
                    set_candidate_status(selected_id, "REJECTED", notes=notes or None, actor="Josh")
                    st.success(f"❌ Candidate {selected_id} rejected!")
                    # Reload data
                    st.session_state.edge_candidates_df = _load_candidates(
                        status_filter=status_filter,
                        instrument_filter=instrument_filter,
                        limit=limit
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error rejecting candidate: {e}")

        # Promote button (only for APPROVED candidates that haven't been promoted)
        promoted_id = candidate.get('promoted_validated_setup_id')
        is_approved = current_status == "APPROVED"
        already_promoted = promoted_id is not None and pd.notna(promoted_id)

        st.divider()

        if already_promoted:
            st.success(f"🎉 Already promoted to validated_setups.setup_id = {promoted_id}")
            if candidate.get('promoted_by'):
                st.caption(f"Promoted by: {candidate.get('promoted_by')} at {candidate.get('promoted_at', 'N/A')}")
        elif is_approved:
            st.warning("⚠️ This candidate is APPROVED and ready for promotion to production")
            if st.button("🚀 Promote to Production", type="primary", use_container_width=True):
                try:
                    # Import promotion function
                    from edge_pipeline import promote_candidate_to_validated_setups

                    # Promote candidate
                    setup_id = promote_candidate_to_validated_setups(selected_id, "Josh")

                    st.success(f"✅ Promoted candidate {selected_id} → validated_setups.setup_id = {setup_id}")
                    st.info("Next step: Run python test_app_sync.py to verify sync")

                    # Reload data
                    st.session_state.edge_candidates_df = _load_candidates(
                        status_filter=status_filter,
                        instrument_filter=instrument_filter,
                        limit=limit
                    )
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ Promotion failed: {e}")
                    st.caption("Fix: Ensure candidate has all required fields for promotion")
                except Exception as e:
                    st.error(f"❌ Promotion failed: {e}")
                    logger.error(f"Promotion error for candidate {selected_id}: {e}", exc_info=True)
        else:
            st.info(f"ℹ️ Candidate must be APPROVED before promotion (current status: {current_status})")

        # Show current notes if any
        if candidate.get('notes'):
            with st.expander("📝 Existing Notes"):
                st.text(candidate.get('notes'))
