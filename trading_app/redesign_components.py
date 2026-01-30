"""
REDESIGN COMPONENTS - Infrastructure for Conveyor Belt UI
==========================================================

Core components for the app redesign:
1. Write safety wrapper (mandatory pre-flight checks)
2. Next-step rail (guided navigation)
3. Status derivation (PASS/WEAK/FAIL computed on-the-fly)

CRITICAL RULES:
- All write actions MUST use attempt_write_action()
- Status NEVER stored, always derived
- No new write paths, use existing flows only
"""

import streamlit as st
import subprocess
import logging
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)


# =============================================================================
# WRITE SAFETY WRAPPER (MANDATORY - FAIL-CLOSED)
# =============================================================================

def attempt_write_action(
    action_name: str,
    callback: Callable,
    *args,
    **kwargs
) -> bool:
    """
    Wrapper for ALL write operations.

    MANDATORY PRE-FLIGHT CHECKS:
    1. python scripts/check/app_preflight.py
    2. python test_app_sync.py

    FAIL-CLOSED: If either fails, BLOCK action and show red banner.

    Args:
        action_name: Human-readable action name (e.g., "Approve Candidate")
        callback: Existing function to call if checks pass
        *args, **kwargs: Arguments for callback

    Returns:
        True if success, False if blocked

    Example:
        if st.button("Approve"):
            attempt_write_action(
                "Approve Candidate",
                edge_pipeline.promote_candidate_to_validated_setups,
                candidate_id=123,
                actor="user"
            )
    """
    st.info(f"🔒 Running mandatory safety checks for: **{action_name}**")

    checks_passed = True
    error_messages = []

    # =============================================================================
    # CHECK 1: app_preflight.py (MANDATORY)
    # =============================================================================
    try:
        st.caption("⏳ Running app_preflight.py...")
        result = subprocess.run(
            ["python", "scripts/check/app_preflight.py"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="."
        )

        if result.returncode != 0:
            checks_passed = False
            error_messages.append(f"**app_preflight.py FAILED**\n```\n{result.stderr}\n```")
            logger.error(f"app_preflight.py failed for {action_name}: {result.stderr}")
        else:
            st.success("✅ app_preflight.py PASSED")

    except subprocess.TimeoutExpired:
        checks_passed = False
        error_messages.append("**app_preflight.py TIMEOUT** (>30s)")
        logger.error(f"app_preflight.py timeout for {action_name}")

    except Exception as e:
        checks_passed = False
        error_messages.append(f"**app_preflight.py ERROR**: {e}")
        logger.error(f"app_preflight.py error for {action_name}: {e}", exc_info=True)

    # =============================================================================
    # CHECK 2: test_app_sync.py (MANDATORY)
    # =============================================================================
    try:
        st.caption("⏳ Running test_app_sync.py...")
        result = subprocess.run(
            ["python", "test_app_sync.py"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="."
        )

        if result.returncode != 0:
            checks_passed = False
            error_messages.append(f"**test_app_sync.py FAILED**\n```\n{result.stderr}\n```")
            logger.error(f"test_app_sync.py failed for {action_name}: {result.stderr}")
        else:
            st.success("✅ test_app_sync.py PASSED")

    except subprocess.TimeoutExpired:
        checks_passed = False
        error_messages.append("**test_app_sync.py TIMEOUT** (>30s)")
        logger.error(f"test_app_sync.py timeout for {action_name}")

    except Exception as e:
        checks_passed = False
        error_messages.append(f"**test_app_sync.py ERROR**: {e}")
        logger.error(f"test_app_sync.py error for {action_name}: {e}", exc_info=True)

    # =============================================================================
    # FAIL-CLOSED ENFORCEMENT
    # =============================================================================
    if not checks_passed:
        # BLOCK ACTION - Show red banner
        st.markdown("""
        <div style="
            background: #f8d7da;
            border-left: 8px solid #dc3545;
            border-radius: 8px;
            padding: 20px;
            margin: 16px 0;
        ">
            <div style="font-size: 18px; font-weight: bold; color: #721c24; margin-bottom: 8px;">
                🚫 ACTION BLOCKED
            </div>
            <div style="color: #721c24;">
                Safety checks FAILED. Action will NOT proceed.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Show errors
        for error in error_messages:
            st.error(error)

        st.warning("⚠️ **Fix the issues above and try again**")

        logger.warning(f"Action blocked: {action_name}")
        return False

    # =============================================================================
    # EXECUTE ACTION (Checks passed)
    # =============================================================================
    st.success("✅ **All safety checks PASSED** - Proceeding with action")

    try:
        # Call existing function
        callback(*args, **kwargs)

        st.success(f"✅ **{action_name} completed successfully**")
        logger.info(f"Action succeeded: {action_name}")
        return True

    except Exception as e:
        st.error(f"❌ **{action_name} FAILED**: {e}")
        logger.error(f"Action failed: {action_name}: {e}", exc_info=True)
        return False


# =============================================================================
# NEXT-STEP RAIL (GUIDED NAVIGATION)
# =============================================================================

def render_next_step_rail(current_zone: str):
    """
    Render next-step rail at top of tab.

    Shows user the single valid next action in the pipeline.

    Args:
        current_zone: "RESEARCH", "VALIDATION", "PRODUCTION", or "LIVE"

    Pipeline flow:
        RESEARCH → VALIDATION → PRODUCTION → LIVE
    """
    rails = {
        "RESEARCH": {
            "text": "Found promising candidates?",
            "action": "Send to Validation",
            "icon": "→",
            "color": "#ffc107"
        },
        "VALIDATION": {
            "text": "Approved strategies ready?",
            "action": "View Production",
            "icon": "→",
            "color": "#ffc107"
        },
        "PRODUCTION": {
            "text": "Ready to trade live?",
            "action": "Go to Live Trading",
            "icon": "→",
            "color": "#ffc107"
        },
        "LIVE": None  # End of pipeline
    }

    rail = rails.get(current_zone)

    if rail:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fff3cd 0%, #fff3cddd 100%);
            border-left: 6px solid {rail['color']};
            border-radius: 10px;
            padding: 18px 24px;
            margin-bottom: 24px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 16px; font-weight: 600; color: #856404;">
                    {rail['icon']} <span style="font-weight: 700;">Next Step:</span> {rail['text']}
                </div>
                <div style="
                    background: {rail['color']};
                    color: #000;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 700;
                    font-size: 14px;
                    cursor: pointer;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                ">
                    {rail['action']} {rail['icon']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# STATUS DERIVATION (NEVER STORED - ALWAYS COMPUTED)
# =============================================================================

def derive_candidate_status(candidate: Dict[str, Any]) -> str:
    """
    Derive candidate status from existing metrics.

    CRITICAL: Status is NEVER stored in database, always computed on-the-fly.

    Status Logic:
    - PASS: ExpR >= 0.15R AND stress_50_pass == True
    - WEAK: ExpR >= 0.15R AND stress_25_pass == True (but NOT stress_50)
    - FAIL: ExpR < 0.15R OR both stress tests fail

    Args:
        candidate: Dict with 'metrics_json' and 'robustness_json' fields

    Returns:
        "PASS", "WEAK", or "FAIL"

    Example:
        status = derive_candidate_status(candidate_row)
        if status == "PASS":
            st.success("✅ PASS")
    """
    try:
        # Parse metrics
        metrics = candidate.get('metrics_json', {})
        if isinstance(metrics, str):
            import json
            metrics = json.loads(metrics)

        exp_r = float(metrics.get('avg_r', 0))

        # Parse robustness
        robustness = candidate.get('robustness_json', {})
        if isinstance(robustness, str):
            import json
            robustness = json.loads(robustness)

        stress_25_pass = robustness.get('stress_25_pass', False)
        stress_50_pass = robustness.get('stress_50_pass', False)

        # Derive status (NEVER store this)
        if exp_r >= 0.15 and stress_50_pass:
            return "PASS"
        elif exp_r >= 0.15 and stress_25_pass:
            return "WEAK"
        else:
            return "FAIL"

    except Exception as e:
        logger.error(f"Error deriving status: {e}", exc_info=True)
        return "FAIL"  # Fail-closed


def render_status_chip(status: str):
    """
    Render status chip with appropriate styling.

    Args:
        status: "PASS", "WEAK", or "FAIL"
    """
    colors = {
        "PASS": {"bg": "#d1e7dd", "text": "#0f5132", "border": "#198754"},
        "WEAK": {"bg": "#fff3cd", "text": "#856404", "border": "#ffc107"},
        "FAIL": {"bg": "#f8d7da", "text": "#721c24", "border": "#dc3545"}
    }

    icons = {
        "PASS": "✅",
        "WEAK": "⚠️",
        "FAIL": "❌"
    }

    color = colors.get(status, colors["FAIL"])
    icon = icons.get(status, "❓")

    st.markdown(f"""
    <div style="
        background: {color['bg']};
        border: 2px solid {color['border']};
        border-radius: 6px;
        padding: 6px 12px;
        display: inline-block;
        font-weight: 700;
        color: {color['text']};
        font-size: 13px;
    ">
        {icon} {status}
    </div>
    """, unsafe_allow_html=True)


def derive_strategy_health(strategy: Dict[str, Any], recent_trades: Optional[list] = None) -> str:
    """
    Derive strategy health indicator from performance data.

    CRITICAL: Health is NEVER stored, always computed on-the-fly.

    Health Logic:
    - HEALTHY: Recent ExpR within 10% of baseline
    - WATCH: Recent ExpR degraded 10-25%
    - FAILING: Recent ExpR degraded >25%

    Args:
        strategy: Dict with 'expected_r' (baseline)
        recent_trades: Optional list of recent trades for comparison

    Returns:
        "HEALTHY", "WATCH", or "FAILING"
    """
    try:
        baseline_exp_r = float(strategy.get('avg_r', 0) or strategy.get('expected_r', 0))

        if recent_trades is None or len(recent_trades) == 0:
            # No recent data - assume healthy (fail-open for monitoring)
            return "HEALTHY"

        # Calculate recent ExpR
        recent_r_values = [t.get('r_multiple', 0) for t in recent_trades]
        recent_exp_r = sum(recent_r_values) / len(recent_r_values) if recent_r_values else 0

        # Calculate degradation %
        if baseline_exp_r == 0:
            return "HEALTHY"  # Can't compare if baseline is 0

        degradation = (baseline_exp_r - recent_exp_r) / abs(baseline_exp_r)

        if degradation < 0.10:
            return "HEALTHY"
        elif degradation < 0.25:
            return "WATCH"
        else:
            return "FAILING"

    except Exception as e:
        logger.error(f"Error deriving health: {e}", exc_info=True)
        return "WATCH"  # Fail-safe


def render_health_indicator(health: str):
    """
    Render health indicator with appropriate styling.

    Args:
        health: "HEALTHY", "WATCH", or "FAILING"
    """
    colors = {
        "HEALTHY": {"bg": "#d1e7dd", "text": "#0f5132", "icon": "🟢"},
        "WATCH": {"bg": "#fff3cd", "text": "#856404", "icon": "🟡"},
        "FAILING": {"bg": "#f8d7da", "text": "#721c24", "icon": "🔴"}
    }

    color = colors.get(health, colors["WATCH"])

    st.markdown(f"""
    <div style="
        background: {color['bg']};
        border-radius: 6px;
        padding: 6px 12px;
        display: inline-block;
        font-weight: 600;
        color: {color['text']};
        font-size: 13px;
    ">
        {color['icon']} {health}
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# VALIDATION STATUS SUMMARY
# =============================================================================

def get_validation_summary(candidates: list) -> Dict[str, int]:
    """
    Get summary counts of candidate statuses.

    Returns:
        Dict with counts: {"PASS": N, "WEAK": N, "FAIL": N, "PENDING": N}
    """
    summary = {"PASS": 0, "WEAK": 0, "FAIL": 0, "PENDING": 0}

    for candidate in candidates:
        # Check if candidate has been validated
        robustness = candidate.get('robustness_json')
        if robustness is None or (isinstance(robustness, str) and not robustness):
            summary["PENDING"] += 1
        else:
            status = derive_candidate_status(candidate)
            summary[status] = summary.get(status, 0) + 1

    return summary
