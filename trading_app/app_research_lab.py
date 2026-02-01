"""
RESEARCH LAB - Strategy Discovery & Backtesting Command Center

The MAIN app for:
- Discovering new profitable edge setups
- Running comprehensive backtests
- Validating strategies with robustness checks
- Promoting winners to production

This is where the real work happens.
"""

import sys
import os
from pathlib import Path

# Force local database (avoid MotherDuck)
os.environ['FORCE_LOCAL_DB'] = '1'

# Add paths for imports
if __name__ == "__main__" or "streamlit" in sys.modules:
    current_dir = Path(__file__).parent
    repo_root = current_dir.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any

# Import research infrastructure
from cloud_mode import get_database_connection, get_database_path
from research_runner import ResearchRunner, BacktestMetrics
from edge_candidate_utils import parse_json_field, approve_edge_candidate, set_candidate_status
from edge_pipeline import promote_candidate_to_validated_setups, create_edge_candidate
from strategy_discovery import StrategyDiscovery, DiscoveryConfig

# Import terminal theme
from terminal_theme import inject_terminal_theme
from terminal_components import *
from time_spec import ORBS  # TSOT: Canonical ORB time source

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="RESEARCH LAB",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inject terminal theme
inject_terminal_theme()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# ----------------------------------------------------------------------------
# DISCOVERY CHECKPOINT HELPERS (timeboxed scans)
# ----------------------------------------------------------------------------

def _get_checkpoint_dir() -> Path:
    """Get checkpoint directory (artifacts/ in repo root)."""
    return Path(__file__).parent.parent / "artifacts"

def _get_checkpoint_path() -> Path:
    """Get path to discovery checkpoint JSONL file."""
    return _get_checkpoint_dir() / "discovery_checkpoint.jsonl"

def _get_meta_path() -> Path:
    """Get path to discovery metadata JSON file."""
    return _get_checkpoint_dir() / "discovery_meta.json"

def _get_params_hash(instrument: str, orb_times: List[str], rr_targets: List[float],
                     sl_modes: List[str], orb_filters: List[Optional[float]]) -> str:
    """Hash of scan parameters to detect if settings changed."""
    params_str = f"{instrument}|{sorted(orb_times)}|{sorted(rr_targets)}|{sorted(sl_modes)}|{sorted(str(f) for f in orb_filters)}"
    return hashlib.md5(params_str.encode()).hexdigest()[:12]

def _load_checkpoint() -> tuple[List[Dict], Dict]:
    """
    Load checkpoint data.
    Returns (results_list, meta_dict).
    """
    results = []
    meta = {}

    checkpoint_path = _get_checkpoint_path()
    meta_path = _get_meta_path()

    if checkpoint_path.exists():
        try:
            with open(checkpoint_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        results.append(json.loads(line))
        except Exception as e:
            logger.warning(f"Error loading checkpoint: {e}")
            results = []

    if meta_path.exists():
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading meta: {e}")
            meta = {}

    return results, meta

def _save_checkpoint_line(idx: int, config: 'DiscoveryConfig', result: 'BacktestResult'):
    """Append one result line to checkpoint file."""
    checkpoint_path = _get_checkpoint_path()
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    line = {
        "idx": idx,
        "config": {
            "instrument": config.instrument,
            "orb_time": config.orb_time,
            "rr": config.rr,
            "sl_mode": config.sl_mode,
            "orb_size_filter": config.orb_size_filter
        },
        "result": {
            "total_trades": result.total_trades,
            "wins": result.wins,
            "losses": result.losses,
            "win_rate": result.win_rate,
            "avg_r": result.avg_r,
            "total_r": result.total_r,
            "tier": result.tier
        },
        "ts": datetime.now().isoformat()
    }

    with open(checkpoint_path, 'a') as f:
        f.write(json.dumps(line) + "\n")

def _save_meta(total_configs: int, processed: int, hits: int, params_hash: str,
               started: str, elapsed_seconds: float):
    """Save checkpoint metadata."""
    meta_path = _get_meta_path()
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "total_configs": total_configs,
        "processed": processed,
        "hits": hits,
        "params_hash": params_hash,
        "started": started,
        "updated": datetime.now().isoformat(),
        "elapsed_seconds": elapsed_seconds
    }

    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

def _clear_checkpoint():
    """Delete checkpoint files to start fresh."""
    checkpoint_path = _get_checkpoint_path()
    meta_path = _get_meta_path()

    if checkpoint_path.exists():
        checkpoint_path.unlink()
    if meta_path.exists():
        meta_path.unlink()

# ----------------------------------------------------------------------------

def load_pipeline_summary() -> Dict[str, int]:
    """Load candidate pipeline status summary (P2-5: single query optimization)"""
    try:
        conn = get_database_connection(read_only=True)

        # P2-5: Combined into single query with conditional aggregation
        # Schema uses status column for all states including PROMOTED
        result = conn.execute("""
            SELECT
                SUM(CASE WHEN status = 'DRAFT' THEN 1 ELSE 0 END) as draft,
                SUM(CASE WHEN status = 'TESTED' THEN 1 ELSE 0 END) as tested,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'PROMOTED' THEN 1 ELSE 0 END) as promoted
            FROM edge_candidates
        """).fetchone()

        conn.close()

        return {
            "DRAFT": result[0] or 0,
            "TESTED": result[1] or 0,
            "PENDING": result[2] or 0,
            "APPROVED": result[3] or 0,
            "REJECTED": result[4] or 0,
            "PROMOTED": result[5] or 0
        }
    except Exception as e:
        logger.error(f"Error loading pipeline summary: {e}")
        return {"DRAFT": 0, "TESTED": 0, "PENDING": 0, "APPROVED": 0, "REJECTED": 0, "PROMOTED": 0}


def load_candidates(
    status_filter: str = "ALL",
    instrument_filter: str = "ALL",
    limit: int = 50,
    offset: int = 0
) -> Optional[pd.DataFrame]:
    """
    Load edge candidates from database (list view - scalar columns only).

    P2-1/P2-2: Pagination + reduced payload for performance.
    JSON columns fetched separately on detail view.
    """
    try:
        conn = get_database_connection(read_only=True)

        # P2-2: Reduced payload - scalar columns only for list view
        # Schema: candidate_id, created_at_utc, instrument, name, status, notes (scalar only)
        sql = """
            SELECT
                candidate_id, created_at_utc, instrument, name, status
            FROM edge_candidates
            WHERE status != 'REJECTED'
        """
        params = []

        # Allow explicit viewing of rejected candidates
        if status_filter == "REJECTED":
            sql = sql.replace("WHERE status != 'REJECTED'", "WHERE status = 'REJECTED'")
        elif status_filter != "ALL":
            sql += " AND status = ?"
            params.append(status_filter)

        if instrument_filter != "ALL":
            sql += " AND instrument = ?"
            params.append(instrument_filter)

        # P2-1: Pagination with LIMIT/OFFSET
        sql += f" ORDER BY created_at_utc DESC LIMIT {limit} OFFSET {offset}"

        df = conn.execute(sql, params).df()
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Error loading candidates: {e}")
        return None


def load_candidate_detail(candidate_id: int) -> Optional[Dict]:
    """
    Load full candidate detail including JSON fields.

    P2-2: Fetch heavy JSON columns only when needed (detail view).
    """
    try:
        conn = get_database_connection(read_only=True)

        # Convert numpy.int32/int64 to Python int for DuckDB compatibility
        cid = int(candidate_id)

        # Fetch all columns that exist in the schema
        row = conn.execute("""
            SELECT
                candidate_id, created_at_utc, instrument, name, hypothesis_text,
                status, test_window_start, test_window_end,
                metrics_json, robustness_json, filter_spec_json, notes
            FROM edge_candidates
            WHERE candidate_id = ?
        """, [cid]).fetchone()

        conn.close()

        if row:
            columns = [
                'candidate_id', 'created_at_utc', 'instrument', 'name', 'hypothesis_text',
                'status', 'test_window_start', 'test_window_end',
                'metrics_json', 'robustness_json', 'filter_spec_json', 'notes'
            ]
            return dict(zip(columns, row))
        return None
    except Exception as e:
        logger.error(f"Error loading candidate detail: {e}")
        return None


def get_candidate_count(status_filter: str = "ALL", instrument_filter: str = "ALL") -> int:
    """Get total count of candidates matching filters (for pagination)."""
    try:
        conn = get_database_connection(read_only=True)

        sql = "SELECT COUNT(*) FROM edge_candidates WHERE status != 'REJECTED'"
        params = []

        if status_filter == "REJECTED":
            sql = sql.replace("WHERE status != 'REJECTED'", "WHERE status = 'REJECTED'")
        elif status_filter != "ALL":
            sql += " AND status = ?"
            params.append(status_filter)

        if instrument_filter != "ALL":
            sql += " AND instrument = ?"
            params.append(instrument_filter)

        count = conn.execute(sql, params).fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error getting candidate count: {e}")
        return 0


def parse_metrics(metrics_json: Any) -> Dict:
    """Parse metrics JSON field"""
    if metrics_json is None:
        return {}
    if isinstance(metrics_json, dict):
        return metrics_json
    try:
        return json.loads(metrics_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse metrics JSON: {e}")
        return {}


# ============================================================================
# VIEW: DISCOVERY
# ============================================================================

def render_discovery_view():
    """Strategy discovery - find new profitable setups"""
    render_terminal_header("STRATEGY DISCOVERY", "SCAN FOR PROFITABLE EDGES")

    st.markdown("""
    <div class="info-panel">
        <p>Systematically scan for profitable ORB configurations across instruments, timeframes, and filter combinations.
        Discovery engine will test hundreds of variations and surface the best performers.</p>
    </div>
    """, unsafe_allow_html=True)

    render_section_divider("SCAN PARAMETERS")

    col1, col2, col3 = st.columns(3)

    with col1:
        instrument = st.selectbox("INSTRUMENT", ["MGC", "NQ", "MPL"], key="disc_instrument")

    with col2:
        orb_times = st.multiselect(
            "ORB TIMES",
            ORBS,
            default=ORBS[:3],  # First 3 ORBs as default
            key="disc_orb_times"
        )

    with col3:
        min_trades = st.number_input("MIN TRADES", min_value=10, value=50, key="disc_min_trades")

    render_section_divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        min_win_rate = st.slider("MIN WIN RATE", 0.0, 1.0, 0.50, 0.01)
    with col2:
        min_avg_r = st.slider("MIN AVG R", -1.0, 2.0, 0.0, 0.05)  # Realistic range: edges are 0.05-0.30R
    with col3:
        max_drawdown = st.slider("MAX DRAWDOWN R", 0.0, 10.0, 5.0, 0.5)
    with col4:
        min_sharpe = st.slider("MIN SHARPE", 0.0, 3.0, 0.5, 0.1)

    render_section_divider("FILTER TESTING")

    st.markdown("""
    <div style="font-family: var(--font-mono); color: var(--text-secondary); margin-bottom: 16px;">
        Test multiple filter combinations to find optimal entry conditions:
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        test_orb_size = st.checkbox("Test ORB Size Filters", value=True, help="Scan for optimal min/max ORB size")
        test_atr = st.checkbox("Test ATR Filters", value=True, help="Filter by average true range")
        test_rsi = st.checkbox("Test RSI Filters", value=False, help="Filter by RSI levels")

    with col2:
        test_session_move = st.checkbox("Test Session Travel", value=True, help="Filter by prior session movement")
        test_time_windows = st.checkbox("Test Extended Windows", value=False, help="Test longer profit windows")
        test_rr_targets = st.checkbox("Test R:R Ratios", value=True, help="Optimize reward:risk targets")

    render_section_divider("TIMEBOXED SCAN")

    # Chunk duration slider
    chunk_seconds = st.slider("SCAN CHUNK (seconds)", 30, 300, 120, 30,
                              help="Run scan in chunks to avoid timeouts. Results saved between chunks.")

    # Generate configs for hash calculation (needed for checkpoint validation)
    rr_targets = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0] if test_rr_targets else [4.0]
    sl_modes = ["FULL", "HALF"]
    orb_filters = [None, 0.10, 0.15, 0.20] if test_orb_size else [None]
    params_hash = _get_params_hash(instrument, orb_times, rr_targets, sl_modes, orb_filters)

    # Load existing checkpoint
    checkpoint_results, checkpoint_meta = _load_checkpoint()
    checkpoint_valid = (checkpoint_meta.get("params_hash") == params_hash)

    # Status panel
    if checkpoint_valid and checkpoint_meta:
        processed = checkpoint_meta.get("processed", 0)
        total = checkpoint_meta.get("total_configs", 0)
        hits = checkpoint_meta.get("hits", 0)
        elapsed = checkpoint_meta.get("elapsed_seconds", 0)
        pct = (processed / total * 100) if total > 0 else 0

        if processed >= total and total > 0:
            status_color = "var(--profit-green)"
            status_text = "✅ COMPLETE"
        else:
            status_color = "var(--text-warning)"
            status_text = "⏸️ PAUSED"

        st.markdown(f"""
        <div style="font-family: var(--font-mono); padding: 12px; border: 1px solid {status_color};
                    border-radius: 4px; margin-bottom: 16px;">
            <div style="color: {status_color}; font-weight: bold; margin-bottom: 8px;">{status_text}</div>
            <div>Processed: {processed}/{total} ({pct:.0f}%)</div>
            <div>Hits found: {hits}</div>
            <div>Elapsed: {elapsed:.0f}s</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="font-family: var(--font-mono); padding: 12px; border: 1px solid var(--text-secondary);
                    border-radius: 4px; margin-bottom: 16px; color: var(--text-secondary);">
            <div>No checkpoint or settings changed. Ready for new scan.</div>
        </div>
        """, unsafe_allow_html=True)

    # Three buttons: Run/Continue, View Results, Reset
    btn_col1, btn_col2, btn_col3 = st.columns(3)

    with btn_col1:
        run_label = "▶️ Continue Scan" if (checkpoint_valid and checkpoint_meta.get("processed", 0) > 0) else "▶️ Run Scan"
        run_clicked = st.button(run_label, type="primary", use_container_width=True)

    with btn_col2:
        view_clicked = st.button("📊 View Results", use_container_width=True,
                                 disabled=(not checkpoint_valid or len(checkpoint_results) == 0))

    with btn_col3:
        reset_clicked = st.button("🗑️ Reset", use_container_width=True)

    # Handle Reset
    if reset_clicked:
        _clear_checkpoint()
        st.success("✅ Checkpoint cleared. Ready for fresh scan.")
        st.rerun()

    # Handle View Results
    if view_clicked and checkpoint_results:
        # Filter checkpoint results by current criteria
        filtered_results = []
        for r in checkpoint_results:
            res = r.get("result", {})
            if res.get("total_trades", 0) >= min_trades:
                if (res.get("win_rate", 0) / 100) >= min_win_rate:
                    if res.get("avg_r", -999) >= min_avg_r:
                        filtered_results.append(r)

        if filtered_results:
            st.success(f"✅ Showing {len(filtered_results)} strategies matching current filters")

            results_data = []
            for r in filtered_results:
                cfg = r.get("config", {})
                res = r.get("result", {})
                results_data.append({
                    "Instrument": cfg.get("instrument", "?"),
                    "ORB Time": cfg.get("orb_time", "?"),
                    "R:R": cfg.get("rr", 0),
                    "SL Mode": cfg.get("sl_mode", "?"),
                    "Filter": f"{cfg.get('orb_size_filter', 0)*100:.0f}%" if cfg.get("orb_size_filter") else "None",
                    "Trades": res.get("total_trades", 0),
                    "Win Rate": f"{res.get('win_rate', 0):.1f}%",
                    "Avg R": res.get("avg_r", 0),
                    "Total R": res.get("total_r", 0),
                    "Tier": res.get("tier", "?")
                })

            df = pd.DataFrame(results_data)
            df = df.sort_values('Total R', ascending=False)
            st.dataframe(df.head(30), use_container_width=True)
        else:
            st.warning("⚠ No strategies match current filter criteria.", icon="⚠️")

    # Handle Run/Continue
    if run_clicked:
        with st.spinner(f"Running {chunk_seconds}s scan chunk..."):
            try:
                discovery = StrategyDiscovery()

                # Generate all configs (deterministic order)
                configs = []
                for orb_time in orb_times:
                    for rr in rr_targets:
                        for sl_mode in sl_modes:
                            for orb_filter in orb_filters:
                                config = DiscoveryConfig(
                                    instrument=instrument,
                                    orb_time=orb_time,
                                    rr=rr,
                                    sl_mode=sl_mode,
                                    orb_size_filter=orb_filter
                                )
                                configs.append(config)

                total_configs = len(configs)

                # Determine start index from checkpoint
                if checkpoint_valid:
                    start_idx = checkpoint_meta.get("processed", 0)
                    prior_elapsed = checkpoint_meta.get("elapsed_seconds", 0)
                    started = checkpoint_meta.get("started", datetime.now().isoformat())
                else:
                    # New scan - clear old checkpoint
                    _clear_checkpoint()
                    start_idx = 0
                    prior_elapsed = 0.0
                    started = datetime.now().isoformat()

                # Check if already complete
                if start_idx >= total_configs:
                    st.info("✅ Scan already complete! Use 'View Results' or 'Reset' to start fresh.")
                else:
                    st.info(f"Testing configs {start_idx + 1} to {total_configs}...")

                    # Run timeboxed loop
                    progress_bar = st.progress(start_idx / total_configs)
                    hits_this_chunk = 0
                    processed_this_chunk = 0
                    chunk_start = time.monotonic()

                    for i in range(start_idx, total_configs):
                        config = configs[i]
                        result = discovery.backtest_configuration(config)

                        # Save to checkpoint (every result, not just hits)
                        _save_checkpoint_line(i, config, result)
                        processed_this_chunk += 1

                        # Count hits
                        if result.total_trades >= min_trades:
                            if (result.win_rate / 100) >= min_win_rate:
                                if result.avg_r >= min_avg_r:
                                    hits_this_chunk += 1

                        progress_bar.progress((i + 1) / total_configs)

                        # Check timebox
                        elapsed_chunk = time.monotonic() - chunk_start
                        if elapsed_chunk >= chunk_seconds:
                            break

                    progress_bar.empty()

                    # Update meta
                    total_processed = start_idx + processed_this_chunk
                    total_elapsed = prior_elapsed + (time.monotonic() - chunk_start)

                    # Count total hits from checkpoint
                    all_results, _ = _load_checkpoint()
                    total_hits = sum(1 for r in all_results
                                     if r.get("result", {}).get("total_trades", 0) >= min_trades
                                     and (r.get("result", {}).get("win_rate", 0) / 100) >= min_win_rate
                                     and r.get("result", {}).get("avg_r", -999) >= min_avg_r)

                    _save_meta(total_configs, total_processed, total_hits, params_hash, started, total_elapsed)

                    # Status message
                    if total_processed >= total_configs:
                        st.success(f"✅ Scan complete! {total_configs} configs tested, {total_hits} hits found.")
                    else:
                        remaining = total_configs - total_processed
                        st.warning(f"⏸️ Chunk done. {total_processed}/{total_configs} processed, {remaining} remaining. Click 'Continue Scan' to resume.", icon="⏸️")

                    st.rerun()

            except Exception as e:
                logger.error(f"Discovery error: {e}")
                st.error(f"❌ Discovery failed: {str(e)}")

    # ========================================================================
    # PB GRID GENERATOR (Single Owner - moved from app_canonical)
    # ========================================================================
    render_section_divider("PB FAMILY GRID GENERATOR")

    st.markdown("""
    <div style="font-family: var(--font-mono); color: var(--text-secondary); margin-bottom: 16px;">
        Generate 144 PB (Pullback) parameter combinations for systematic testing.
        Grid: 3 ORBs × 2 directions × 2 entry × 2 confirm × 2 stop × 3 target = 144 candidates
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        pb_instrument = st.selectbox("Instrument", ["MGC", "NQ", "MPL"], key="pb_grid_instrument")

        if st.button("🚀 Generate 144 PB Candidates", type="primary", use_container_width=True):
            with st.spinner("Generating 144 PB candidates..."):
                try:
                    from pb_grid_generator import generate_pb_batch

                    conn = get_database_connection()
                    results = generate_pb_batch(
                        instrument=pb_instrument,
                        actor='user',
                        db_connection=conn
                    )
                    conn.close()

                    st.success(f"""
                    ✅ **PB Grid Complete!**

                    - Total combinations: {results['total']}
                    - Candidates created: {results['inserted']}
                    - Duplicates skipped: {results['skipped']}
                    - Elapsed time: {results['elapsed_seconds']:.1f}s

                    Go to **PIPELINE** tab to review candidates.
                    """)

                except Exception as e:
                    logger.error(f"PB grid error: {e}")
                    st.error(f"❌ PB grid generation failed: {str(e)}")

    with col2:
        st.info(f"""
        **💡 PB Grid Parameters:**

        - **ORBs:** {', '.join(ORBS[:3])} (daytime)
        - **Directions:** LONG, SHORT
        - **Entry:** RETEST_ORB, MID_PULLBACK
        - **Confirmation:** CLOSE_CONFIRM, WICK_REJECT
        - **Stop:** STOP_ORB_OPP, STOP_SWING
        - **Target:** 1.0R, 1.5R, 2.0R

        All candidates created as DRAFT status.
        Duplicates automatically skipped via spec-hash dedupe.
        """)


# ============================================================================
# VIEW: PIPELINE
# ============================================================================

def render_pipeline_view():
    """Pipeline dashboard - manage candidates through workflow"""
    render_terminal_header("RESEARCH PIPELINE", "CANDIDATE WORKFLOW MANAGEMENT")

    # Load summary
    summary = load_pipeline_summary()

    # Status overview
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        render_metric_card("DRAFT", str(summary.get("DRAFT", 0)), change="Awaiting test", sentiment="neutral")
    with col2:
        render_metric_card("TESTED", str(summary.get("TESTED", 0)), change="Ready for review", sentiment="neutral")
    with col3:
        render_metric_card("PENDING", str(summary.get("PENDING", 0)), change="Under review", sentiment="neutral")
    with col4:
        render_metric_card("APPROVED", str(summary.get("APPROVED", 0)), change="Ready for prod", sentiment="positive")
    with col5:
        render_metric_card("REJECTED", str(summary.get("REJECTED", 0)), change="Failed validation", sentiment="negative")
    with col6:
        render_metric_card("PROMOTED", str(summary.get("PROMOTED", 0)), change="Live in prod", sentiment="positive")

    render_section_divider()

    st.markdown("""
    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); text-align: center;">
        WORKFLOW: Draft → Tested → Pending → Approved → Promoted to Production
    </div>
    """, unsafe_allow_html=True)

    render_section_divider("FILTER & VIEW")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        status_filter = st.selectbox(
            "STATUS",
            ["ALL", "DRAFT", "TESTED", "PENDING", "APPROVED", "REJECTED"],
            key="pipeline_status_filter"
        )

    with col2:
        instrument_filter = st.selectbox(
            "INSTRUMENT",
            ["ALL", "MGC", "NQ", "MPL"],
            key="pipeline_instrument_filter"
        )

    with col3:
        page_size = st.selectbox(
            "PER PAGE",
            [25, 50, 100],
            index=1,
            key="pipeline_page_size"
        )

    # P2-1: Pagination state
    if "pipeline_page" not in st.session_state:
        st.session_state.pipeline_page = 0

    # Get total count for pagination
    total_count = get_candidate_count(status_filter, instrument_filter)
    total_pages = max(1, (total_count + page_size - 1) // page_size)

    # Ensure page is valid
    if st.session_state.pipeline_page >= total_pages:
        st.session_state.pipeline_page = 0

    # Load candidates with pagination (P2-1 + P2-2: reduced payload)
    offset = st.session_state.pipeline_page * page_size
    df = load_candidates(status_filter, instrument_filter, limit=page_size, offset=offset)

    if df is not None and not df.empty:
        # P2-1: Pagination controls
        render_section_divider(f"CANDIDATES (Page {st.session_state.pipeline_page + 1}/{total_pages} • {total_count} total)")

        pg_col1, pg_col2, pg_col3, pg_col4 = st.columns([1, 1, 1, 1])
        with pg_col1:
            if st.button("⏮️ First", disabled=(st.session_state.pipeline_page == 0), use_container_width=True):
                st.session_state.pipeline_page = 0
                st.rerun()
        with pg_col2:
            if st.button("◀️ Prev", disabled=(st.session_state.pipeline_page == 0), use_container_width=True):
                st.session_state.pipeline_page -= 1
                st.rerun()
        with pg_col3:
            if st.button("Next ▶️", disabled=(st.session_state.pipeline_page >= total_pages - 1), use_container_width=True):
                st.session_state.pipeline_page += 1
                st.rerun()
        with pg_col4:
            if st.button("Last ⏭️", disabled=(st.session_state.pipeline_page >= total_pages - 1), use_container_width=True):
                st.session_state.pipeline_page = total_pages - 1
                st.rerun()

        # P2-2: List view with scalar columns only
        for idx, row in df.iterrows():
            # Show summary line (no JSON parsing yet)
            name_display = row['name'] if row['name'] else f"Candidate {row['candidate_id']}"
            status_icon = {"DRAFT": "📝", "TESTED": "🧪", "PENDING": "⏳", "APPROVED": "✅", "REJECTED": "❌"}.get(row['status'], "📊")

            with st.expander(f"{status_icon} {name_display} ({row['instrument']}) - {row['status']}", expanded=False):
                # P2-2: Load full detail ONLY when expander is opened (lazy load)
                detail = load_candidate_detail(row['candidate_id'])

                if detail:
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**ID:** {detail['candidate_id']}")
                        st.markdown(f"**Hypothesis:** {detail.get('hypothesis_text', 'N/A')}")
                        st.markdown(f"**Test Window:** {detail.get('test_window_start', 'N/A')} to {detail.get('test_window_end', 'N/A')}")

                        # P2-2: Parse JSON only in detail view (not list)
                        metrics = parse_metrics(detail.get('metrics_json'))
                        if metrics:
                            st.markdown("**Performance Metrics:**")
                            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                            with m_col1:
                                st.metric("Win Rate", f"{metrics.get('win_rate', 0)*100:.1f}%")
                            with m_col2:
                                st.metric("Avg R", f"{metrics.get('avg_r', 0):.2f}")
                            with m_col3:
                                st.metric("Total R", f"{metrics.get('total_r', 0):.1f}")
                            with m_col4:
                                st.metric("Trades", metrics.get('n_trades', 0))

                    with col2:
                        st.markdown(f"**Created:** {detail['created_at_utc']}")
                        st.markdown(f"**Status:** `{detail['status']}`")

                        if detail.get('notes'):
                            st.markdown(f"**Notes:** {detail['notes'][:100]}...")

                        # Action buttons
                        st.markdown("---")

                        if detail['status'] == "DRAFT":
                            if st.button("🧪 RUN BACKTEST", key=f"test_{detail['candidate_id']}"):
                                with st.spinner("Running backtest..."):
                                    try:
                                        runner = ResearchRunner()
                                        runner.run_candidate(candidate_id=detail['candidate_id'])
                                        st.success("✅ Backtest complete")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Backtest failed: {str(e)}")

                        elif detail['status'] == "TESTED":
                            if st.button("👀 REVIEW", key=f"review_{detail['candidate_id']}"):
                                set_candidate_status(detail['candidate_id'], "PENDING")
                                st.success("✅ Moved to PENDING")
                                st.rerun()

                        elif detail['status'] == "PENDING":
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                if st.button("✅ APPROVE", key=f"approve_{detail['candidate_id']}", type="primary"):
                                    approve_edge_candidate(detail['candidate_id'], approved_by="user")
                                    st.success("✅ Approved!")
                                    st.rerun()
                            with btn_col2:
                                if st.button("❌ REJECT", key=f"reject_{detail['candidate_id']}"):
                                    set_candidate_status(detail['candidate_id'], "REJECTED")
                                    st.success("❌ Rejected")
                                    st.rerun()

                        elif detail['status'] == "APPROVED":
                            if st.button("🚀 PROMOTE TO PRODUCTION", key=f"promote_{detail['candidate_id']}", type="primary"):
                                with st.spinner("Promoting to production..."):
                                    try:
                                        setup_id = promote_candidate_to_validated_setups(detail['candidate_id'])
                                        st.success(f"✅ Promoted! Setup ID: {setup_id}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Promotion failed: {str(e)}")
                else:
                    st.error("Failed to load candidate details")
    else:
        st.info("⚡ No candidates found. Start a discovery scan to create new candidates.", icon="ℹ️")


# ============================================================================
# VIEW: BACKTESTER
# ============================================================================

def render_backtester_view():
    """Interactive backtest runner"""
    render_terminal_header("BACKTEST ENGINE", "TEST STRATEGIES ON HISTORICAL DATA")

    st.markdown("""
    <div class="info-panel">
        <p>Run comprehensive backtests on any strategy configuration. Test different instruments, ORB times,
        filter combinations, and R:R targets to validate edge profitability.</p>
    </div>
    """, unsafe_allow_html=True)

    render_section_divider("BACKTEST CONFIGURATION")

    col1, col2, col3 = st.columns(3)

    with col1:
        instrument = st.selectbox("INSTRUMENT", ["MGC", "NQ", "MPL"], key="bt_instrument")
    with col2:
        orb_time = st.selectbox("ORB TIME", ["0900", "1000", "1100", "1800", "2300", "0030"], key="bt_orb_time")
    with col3:
        rr_target = st.number_input("R:R TARGET", min_value=1.0, max_value=20.0, value=8.0, step=0.5, key="bt_rr")

    render_section_divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ENTRY FILTERS")
        orb_min = st.number_input("Min ORB Size", min_value=0.0, max_value=10.0, value=0.0, step=0.05)
        orb_max = st.number_input("Max ORB Size", min_value=0.0, max_value=20.0, value=99.0, step=0.05)
        atr_min = st.number_input("Min ATR", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
        atr_max = st.number_input("Max ATR", min_value=0.0, max_value=20.0, value=99.0, step=0.1)

    with col2:
        st.markdown("### TEST WINDOW")
        start_date = st.date_input("Start Date", value=datetime(2021, 1, 1))
        end_date = st.date_input("End Date", value=datetime.now())

        st.markdown("### ADVANCED")
        half_sl = st.checkbox("Use Half Stop Loss", value=False, help="Use 50% of ORB as stop")
        extended_window = st.checkbox("Extended Profit Window", value=False, help="Allow 24h for targets")

    render_section_divider()

    if st.button("🧪 RUN BACKTEST", type="primary", use_container_width=True):
        with st.spinner("Running backtest..."):
            try:
                # Create candidate for this backtest
                filter_spec = {
                    "orb_time": orb_time,
                    "orb_min_size": orb_min,
                    "orb_max_size": orb_max,
                    "atr_min": atr_min,
                    "atr_max": atr_max,
                    "half_sl": half_sl,
                    "extended_window": extended_window,
                    "rr_target": rr_target
                }

                candidate_id = create_edge_candidate(
                    instrument=instrument,
                    name=None,  # Auto-generate using naming policy
                    hypothesis_text=f"Ad-hoc backtest: {instrument} {orb_time} ORB with {rr_target}R target",
                    feature_spec={},
                    filter_spec=filter_spec,
                    test_window_start=start_date.strftime('%Y-%m-%d'),
                    test_window_end=end_date.strftime('%Y-%m-%d')
                )

                # Run backtest
                runner = ResearchRunner()
                runner.run_candidate(candidate_id=candidate_id)

                # Load results
                conn = get_database_connection(read_only=True)
                result = conn.execute("""
                    SELECT metrics_json, robustness_json
                    FROM edge_candidates
                    WHERE candidate_id = ?
                """, [candidate_id]).fetchone()
                conn.close()

                if result and result[0]:
                    metrics = parse_metrics(result[0])

                    st.success("✅ Backtest complete!")

                    render_section_divider("RESULTS")

                    # Metrics display
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        render_metric_card("WIN RATE", f"{metrics.get('win_rate', 0)*100:.1f}%", change=None, sentiment="positive" if metrics.get('win_rate', 0) > 0.5 else "negative")
                    with col2:
                        render_metric_card("AVG R", f"{metrics.get('avg_r', 0):.2f}", change=None, sentiment="positive" if metrics.get('avg_r', 0) > 1 else "negative")
                    with col3:
                        render_metric_card("TOTAL R", f"{metrics.get('total_r', 0):.1f}", change=None, sentiment="positive" if metrics.get('total_r', 0) > 0 else "negative")
                    with col4:
                        render_metric_card("TRADES", str(metrics.get('n_trades', 0)), change=None, sentiment="neutral")
                    with col5:
                        render_metric_card("MAX DD", f"{metrics.get('max_drawdown_r', 0):.1f}R", change=None, sentiment="negative" if metrics.get('max_drawdown_r', 0) > 5 else "neutral")

                    # Additional metrics
                    st.markdown("### DETAILED METRICS")
                    detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)
                    with detail_col1:
                        st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
                    with detail_col2:
                        st.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
                    with detail_col3:
                        st.metric("MAE (Avg)", f"{metrics.get('mae_avg', 0):.2f}R")
                    with detail_col4:
                        st.metric("MFE (Avg)", f"{metrics.get('mfe_avg', 0):.2f}R")

                    # Verdict
                    is_profitable = metrics.get('total_r', 0) > 0
                    verdict = "✅ PROFITABLE EDGE DETECTED" if is_profitable else "❌ NO EDGE DETECTED"
                    render_alert_message(verdict, alert_type="success" if is_profitable else "error", slide_in=False)

                else:
                    st.error("❌ No results returned from backtest")

            except Exception as e:
                logger.error(f"Backtest error: {e}")
                st.error(f"❌ Backtest failed: {str(e)}")


# ============================================================================
# VIEW: PRODUCTION
# ============================================================================

def render_production_view():
    """View promoted strategies in production"""
    render_terminal_header("PRODUCTION STRATEGIES", "LIVE VALIDATED SETUPS")

    try:
        conn = get_database_connection(read_only=True)

        # Load validated setups
        df = conn.execute("""
            SELECT
                id, instrument, orb_time, break_direction,
                rr_target, orb_size_filter, stop_loss_mode,
                win_rate, avg_r, total_r, n_trades, max_drawdown_r,
                promoted_from_candidate_id, promoted_at_utc
            FROM validated_setups
            ORDER BY instrument, orb_time
        """).df()

        conn.close()

        if not df.empty:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                render_metric_card("TOTAL SETUPS", str(len(df)), change=None, sentiment="neutral")
            with col2:
                mgc_count = len(df[df['instrument'] == 'MGC'])
                render_metric_card("MGC SETUPS", str(mgc_count), change=None, sentiment="neutral")
            with col3:
                nq_count = len(df[df['instrument'] == 'NQ'])
                render_metric_card("NQ SETUPS", str(nq_count), change=None, sentiment="neutral")
            with col4:
                mpl_count = len(df[df['instrument'] == 'MPL'])
                render_metric_card("MPL SETUPS", str(mpl_count), change=None, sentiment="neutral")

            render_section_divider("ACTIVE STRATEGIES")

            # Group by instrument
            for instrument in ["MGC", "NQ", "MPL"]:
                inst_df = df[df['instrument'] == instrument]
                if not inst_df.empty:
                    st.markdown(f"### {instrument}")

                    for idx, row in inst_df.iterrows():
                        with st.expander(f"📈 {row['orb_time']} ORB ({row['break_direction']}) - {row['rr_target']}R", expanded=False):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.markdown("**CONFIGURATION**")
                                st.markdown(f"ID: {row['id']}")
                                st.markdown(f"ORB Time: {row['orb_time']}")
                                st.markdown(f"Direction: {row['break_direction']}")
                                st.markdown(f"R:R Target: {row['rr_target']}")
                                st.markdown(f"Stop Mode: {row['stop_loss_mode']}")
                                if row['orb_size_filter']:
                                    st.markdown(f"ORB Filter: {row['orb_size_filter']}")

                            with col2:
                                st.markdown("**PERFORMANCE**")
                                st.metric("Win Rate", f"{row['win_rate']*100:.1f}%")
                                st.metric("Avg R", f"{row['avg_r']:.2f}")
                                st.metric("Total R", f"{row['total_r']:.1f}")

                            with col3:
                                st.markdown("**STATISTICS**")
                                st.metric("Trades", row['n_trades'])
                                st.metric("Max Drawdown", f"{row['max_drawdown_r']:.1f}R")
                                if row['promoted_at_utc']:
                                    st.markdown(f"Promoted: {row['promoted_at_utc']}")
        else:
            st.info("⚡ No production strategies yet. Approve and promote candidates to add them here.", icon="ℹ️")

    except Exception as e:
        logger.error(f"Error loading production strategies: {e}")
        st.error(f"❌ Error loading production data: {str(e)}")


# ============================================================================
# VIEW ROUTER
# ============================================================================

# Session state
if "research_view" not in st.session_state:
    st.session_state.research_view = "DISCOVERY"

# Sidebar navigation
with st.sidebar:
    st.markdown("<h2 style='color: var(--profit-green); font-family: var(--font-display);'>🔬 RESEARCH LAB</h2>", unsafe_allow_html=True)

    view = st.radio(
        "RESEARCH MODE",
        ["DISCOVERY", "PIPELINE", "BACKTESTER", "PRODUCTION"],
        index=["DISCOVERY", "PIPELINE", "BACKTESTER", "PRODUCTION"].index(st.session_state.research_view)
    )

    if view != st.session_state.research_view:
        st.session_state.research_view = view
        st.rerun()

    st.markdown("---")

    st.markdown("""
    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);">
        <div><strong>DISCOVERY</strong> - Find new edges</div>
        <div><strong>PIPELINE</strong> - Manage candidates</div>
        <div><strong>BACKTESTER</strong> - Test strategies</div>
        <div><strong>PRODUCTION</strong> - Live setups</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Database info
    db_path = get_database_path()
    st.markdown(f"""
    <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary);">
        <div><strong>DATABASE</strong></div>
        <div>{db_path}</div>
    </div>
    """, unsafe_allow_html=True)

# Render selected view
if st.session_state.research_view == "DISCOVERY":
    render_discovery_view()
elif st.session_state.research_view == "PIPELINE":
    render_pipeline_view()
elif st.session_state.research_view == "BACKTESTER":
    render_backtester_view()
elif st.session_state.research_view == "PRODUCTION":
    render_production_view()

# Footer
st.markdown("<div style='text-align: center; margin-top: 48px; padding: 24px; font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);'>🔬 RESEARCH LAB // STRATEGY DISCOVERY ENGINE // {}</div>".format(datetime.now().strftime('%H:%M:%S')), unsafe_allow_html=True)
