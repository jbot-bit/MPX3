"""
Research Workbench - Unified interface for strategy research and validation

Combines:
- Strategy Discovery: Find new edge opportunities
- Pipeline Dashboard: Track candidate status at a glance
- Testing: Run backtests on candidates
- Approval: Review and promote to production

Usage:
    from research_workbench import render_research_workbench
    render_research_workbench()
"""

import streamlit as st
import pandas as pd
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from cloud_mode import get_database_connection
from strategy_discovery import StrategyDiscovery, DiscoveryConfig, BacktestResult, add_setup_to_production
from edge_candidate_utils import approve_edge_candidate, set_candidate_status
from edge_pipeline import promote_candidate_to_validated_setups, create_edge_candidate
from research_runner import ResearchRunner

logger = logging.getLogger(__name__)


def _load_pipeline_summary() -> Dict[str, int]:
    """Load quick summary of candidates by status."""
    try:
        conn = get_database_connection(read_only=True)
        
        df = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM edge_candidates
            GROUP BY status
        """).df()
        
        summary = {"DRAFT": 0, "TESTED": 0, "PENDING": 0, "APPROVED": 0, "REJECTED": 0, "PROMOTED": 0}
        for _, row in df.iterrows():
            summary[row['status']] = int(row['count'])
        
        promoted = conn.execute("""
            SELECT COUNT(*) FROM edge_candidates WHERE promoted_validated_setup_id IS NOT NULL
        """).fetchone()[0]
        summary["PROMOTED"] = promoted
        
        conn.close()
        return summary
    except Exception as e:
        logger.error(f"Error loading pipeline summary: {e}")
        return {"DRAFT": 0, "TESTED": 0, "PENDING": 0, "APPROVED": 0, "REJECTED": 0, "PROMOTED": 0}


def _load_candidates(status_filter: str = "ALL", instrument_filter: str = "ALL", limit: int = 50) -> Optional[pd.DataFrame]:
    """Load edge candidates from database."""
    try:
        conn = get_database_connection(read_only=True)
        
        sql = """
            SELECT
                candidate_id, created_at_utc, instrument, name, hypothesis_text,
                status, test_window_start, test_window_end,
                approved_at, approved_by, promoted_validated_setup_id,
                metrics_json, robustness_json, filter_spec_json, notes
            FROM edge_candidates
            WHERE 1=1
        """
        params = []
        
        if status_filter != "ALL":
            sql += " AND status = ?"
            params.append(status_filter)
        
        if instrument_filter != "ALL":
            sql += " AND instrument = ?"
            params.append(instrument_filter)
        
        sql += " ORDER BY created_at_utc DESC LIMIT ?"
        params.append(limit)
        
        df = conn.execute(sql, params).df()
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Error loading candidates: {e}")
        return None


def _parse_metrics(metrics_json: Any) -> Dict:
    """Parse metrics JSON field."""
    if metrics_json is None:
        return {}
    if isinstance(metrics_json, dict):
        return metrics_json
    try:
        return json.loads(metrics_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse metrics JSON: {e}")
        return {}


def render_pipeline_dashboard():
    """Render pipeline status dashboard with visual summary."""
    st.subheader("Pipeline Overview")
    
    summary = _load_pipeline_summary()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Draft", summary.get("DRAFT", 0), help="New candidates awaiting testing")
    with col2:
        st.metric("Tested", summary.get("TESTED", 0), help="Backtested, ready for review")
    with col3:
        st.metric("Pending", summary.get("PENDING", 0), help="Under review")
    with col4:
        st.metric("Approved", summary.get("APPROVED", 0), help="Ready for production")
    with col5:
        st.metric("Promoted", summary.get("PROMOTED", 0), help="Live in production")
    
    st.markdown("---")
    
    st.caption("**Workflow:** Draft → Tested → Pending → Approved → Promoted to Production")


def render_discovery_tab():
    """Render strategy discovery interface."""
    st.subheader("Discover New Edges")
    st.caption("Scan for profitable ORB configurations across instruments and timeframes")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        instrument = st.selectbox("Instrument", ["MGC", "NQ", "MPL"], key="disc_instrument")
    
    with col2:
        orb_time = st.selectbox(
            "ORB Time",
            ["0900", "1000", "1100", "1800", "2300", "0030"],
            key="disc_orb_time"
        )
    
    with col3:
        min_trades = st.number_input("Min Trades", min_value=10, value=50, key="disc_min_trades")
    
    with st.expander("Advanced Parameters", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            rr_values = st.multiselect(
                "Risk:Reward Ratios",
                [1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0],
                default=[1.5, 2.0, 3.0, 6.0],
                key="disc_rr"
            )
        with col2:
            sl_modes = st.multiselect(
                "Stop Loss Modes",
                ["FULL", "HALF"],
                default=["FULL", "HALF"],
                key="disc_sl"
            )
        
        filter_values = st.multiselect(
            "ORB Size Filters (% of ATR)",
            [None, 0.10, 0.15, 0.20, 0.25],
            default=[None, 0.15],
            key="disc_filters",
            format_func=lambda x: "No Filter" if x is None else f"{x*100:.0f}%"
        )
    
    if st.button("Run Discovery Scan", type="primary", use_container_width=True):
        with st.spinner(f"Scanning {instrument} {orb_time} configurations..."):
            try:
                discovery = st.session_state.get('strategy_discovery')
                if discovery is None:
                    discovery = StrategyDiscovery()
                
                results = discovery.discover_best_setups(
                    instrument=instrument,
                    orb_time=orb_time,
                    rr_values=rr_values if rr_values else [1.0, 1.5, 2.0, 3.0],
                    sl_modes=sl_modes if sl_modes else ["FULL", "HALF"],
                    filter_values=filter_values if filter_values else [None, 0.15]
                )
                
                results = [r for r in results if r.total_trades >= min_trades]
                
                st.session_state['discovery_results'] = results
                st.success(f"Found {len(results)} configurations with {min_trades}+ trades")
                
            except Exception as e:
                st.error(f"Discovery failed: {e}")
                logger.error(f"Discovery error: {e}", exc_info=True)
    
    if 'discovery_results' in st.session_state and st.session_state['discovery_results']:
        results = st.session_state['discovery_results']
        
        st.subheader(f"Discovery Results ({len(results)} configs)")
        
        results_df = pd.DataFrame([r.to_dict() for r in results])
        
        st.dataframe(
            results_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tier": st.column_config.TextColumn("Tier", width="small"),
                "Win Rate": st.column_config.TextColumn("Win Rate"),
                "Avg R": st.column_config.TextColumn("Avg R"),
            }
        )
        
        st.divider()
        st.subheader("Create Hypothesis from Result")
        
        result_idx = st.selectbox(
            "Select Configuration",
            range(len(results)),
            format_func=lambda i: f"{results[i].config.instrument} {results[i].config.orb_time} RR={results[i].config.rr} {results[i].config.sl_mode} → {results[i].tier}",
            key="selected_discovery_result"
        )
        
        if result_idx is not None:
            selected = results[result_idx]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Win Rate", f"{selected.win_rate:.1f}%")
                st.metric("Total Trades", selected.total_trades)
            with col2:
                st.metric("Avg R", f"{selected.avg_r:+.3f}R")
                st.metric("Annual Trades", selected.annual_trades)
            
            hypothesis_text = st.text_area(
                "Hypothesis Description",
                value=f"{selected.config.instrument} {selected.config.orb_time} ORB breakout with {selected.config.rr}R target, {selected.config.sl_mode} stop. Filter: {selected.config.orb_size_filter or 'None'}",
                key="new_hypothesis_text"
            )
            
            if st.button("Create Edge Candidate", type="primary"):
                try:
                    filter_spec = {
                        "orb_time": selected.config.orb_time,
                        "rr": selected.config.rr,
                        "sl_mode": selected.config.sl_mode,
                        "orb_size_filter": selected.config.orb_size_filter
                    }
                    
                    metrics = {
                        "win_rate": selected.win_rate,
                        "avg_r": selected.avg_r,
                        "total_r": selected.total_r,
                        "n_trades": selected.total_trades,
                        "annual_trades": selected.annual_trades,
                        "tier": selected.tier
                    }
                    
                    candidate_id = create_edge_candidate(
                        name=f"{selected.config.instrument}_{selected.config.orb_time}_RR{selected.config.rr}",
                        instrument=selected.config.instrument,
                        hypothesis_text=hypothesis_text,
                        filter_spec=filter_spec,
                        test_config={"source": "discovery_scan", "min_trades": min_trades},
                        metrics=metrics,
                        slippage_assumptions={"slippage_ticks": 1, "commission": 0.62},
                        code_version="discovery-v1",
                        data_version=datetime.now().strftime("%Y-%m-%d"),
                        actor="ResearchWorkbench"
                    )
                    
                    st.success(f"Created edge candidate #{candidate_id}")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Failed to create candidate: {e}")


def render_candidates_tab():
    """Render candidates review and approval interface."""
    st.subheader("Edge Candidates Pipeline")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["ALL", "DRAFT", "TESTED", "PENDING", "APPROVED", "REJECTED"],
            key="wb_status_filter"
        )
    
    with col2:
        instrument_filter = st.selectbox(
            "Instrument",
            ["ALL", "MGC", "NQ", "MPL"],
            key="wb_instrument_filter"
        )
    
    with col3:
        limit = st.selectbox("Limit", [25, 50, 100], key="wb_limit")
    
    df = _load_candidates(status_filter, instrument_filter, limit)
    
    if df is None or len(df) == 0:
        st.info("No candidates found. Use the Discovery tab to find new edges!")
        return
    
    st.metric("Total Candidates", len(df))
    
    display_cols = ['candidate_id', 'instrument', 'name', 'status', 'created_at_utc']
    available_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(df[available_cols], use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("Candidate Details")
    
    candidate_ids = df['candidate_id'].tolist()
    selected_id = st.selectbox("Select Candidate", candidate_ids, key="wb_selected_id")
    
    if selected_id:
        candidate = df[df['candidate_id'] == selected_id].iloc[0]
        
        with st.expander("Hypothesis", expanded=True):
            st.write(candidate.get('hypothesis_text', 'N/A'))
        
        metrics = _parse_metrics(candidate.get('metrics_json'))
        if metrics:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Win Rate", f"{metrics.get('win_rate', 0)*100:.1f}%" if metrics.get('win_rate', 0) < 1 else f"{metrics.get('win_rate', 0):.1f}%")
            with col2:
                st.metric("Avg R", f"{metrics.get('avg_r', 0):+.3f}R")
            with col3:
                st.metric("Trades", metrics.get('n_trades', 0))
            with col4:
                st.metric("Tier", metrics.get('tier', 'N/A'))
        
        current_status = candidate.get('status', 'UNKNOWN')
        st.info(f"Current Status: **{current_status}**")
        
        if current_status == "DRAFT":
            if st.button("Run Backtest", type="primary", use_container_width=True):
                with st.spinner("Running backtest..."):
                    try:
                        runner = ResearchRunner()
                        success = runner.run_candidate(selected_id)
                        if success:
                            st.success("Backtest complete! Status updated to TESTED.")
                            st.rerun()
                        else:
                            st.error("Backtest failed. Check logs for details.")
                    except Exception as e:
                        st.error(f"Backtest error: {e}")
        
        notes = st.text_area("Notes", key="wb_notes", placeholder="Add notes...")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Approve", type="primary", disabled=(current_status == "APPROVED")):
                try:
                    approve_edge_candidate(selected_id, "Josh")
                    st.success(f"Approved #{selected_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col2:
            if st.button("Set Pending", disabled=(current_status == "PENDING")):
                try:
                    set_candidate_status(selected_id, "PENDING", notes=notes or None, actor="Josh")
                    st.success(f"Set #{selected_id} to PENDING")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col3:
            if st.button("Reject", disabled=(current_status == "REJECTED")):
                try:
                    set_candidate_status(selected_id, "REJECTED", notes=notes or None, actor="Josh")
                    st.success(f"Rejected #{selected_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        promoted_id = candidate.get('promoted_validated_setup_id')
        is_approved = current_status == "APPROVED"
        already_promoted = promoted_id is not None and pd.notna(promoted_id)
        
        if already_promoted:
            st.success(f"Already promoted to production: {promoted_id}")
        elif is_approved:
            st.warning("Ready for promotion to production")
            if st.button("Promote to Production", type="primary"):
                try:
                    setup_id = promote_candidate_to_validated_setups(selected_id, "Josh")
                    st.success(f"Promoted to validated_setups: {setup_id}")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Promotion failed: {e}")


def render_research_workbench():
    """Main entry point for the Research Workbench."""
    st.header("Research Workbench")
    st.caption("Discover, test, and deploy trading strategies")
    
    render_pipeline_dashboard()
    
    tab1, tab2 = st.tabs(["Discovery", "Pipeline"])
    
    with tab1:
        render_discovery_tab()
    
    with tab2:
        render_candidates_tab()
