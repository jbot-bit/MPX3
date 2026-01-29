"""
Experimental Alerts UI Component - Professional Trading Terminal Style

Displays experimental strategy alerts with trading terminal aesthetics:
- Monospace fonts for data alignment
- Dark theme with green/red/blue color coding
- Information density without clutter
- One-click expandable details
"""

import streamlit as st
from typing import List, Dict
from experimental_scanner import ExperimentalScanner


# Professional Trading Terminal CSS
EXPERIMENTAL_ALERTS_CSS = """
<style>
/* Experimental Alerts Container */
.experimental-alerts-container {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #FFD600;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

/* Alert Header */
.experimental-alerts-header {
    color: #FFD600;
    font-size: 18px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.experimental-alerts-header .icon {
    font-size: 24px;
}

/* No Alerts State */
.no-experimental-alerts {
    color: #888;
    font-size: 14px;
    padding: 16px;
    text-align: center;
    font-style: italic;
    border: 1px dashed #444;
    border-radius: 4px;
}

/* Alert Card */
.experimental-alert-card {
    background: rgba(255, 214, 0, 0.05);
    border-left: 4px solid #FFD600;
    padding: 16px;
    margin-bottom: 12px;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.experimental-alert-card:hover {
    background: rgba(255, 214, 0, 0.1);
    transform: translateX(4px);
}

/* Alert Title */
.alert-title {
    color: #FFD600;
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 8px;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}

/* Alert Metrics Row */
.alert-metrics {
    display: flex;
    gap: 20px;
    margin-bottom: 8px;
    flex-wrap: wrap;
}

.alert-metric {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.alert-metric-label {
    color: #888;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.alert-metric-value {
    color: #fff;
    font-size: 14px;
    font-weight: bold;
}

.alert-metric-value.positive {
    color: #00C853;
}

.alert-metric-value.neutral {
    color: #2979FF;
}

/* Alert Condition */
.alert-condition {
    color: #aaa;
    font-size: 12px;
    margin-bottom: 8px;
    padding: 8px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 4px;
    font-style: italic;
}

/* Alert Match Reason */
.alert-match-reason {
    color: #FFD600;
    font-size: 12px;
    font-weight: bold;
    margin-top: 8px;
    padding: 6px 10px;
    background: rgba(255, 214, 0, 0.1);
    border-radius: 4px;
    display: inline-block;
}

/* Summary Stats */
.experimental-summary {
    display: flex;
    gap: 30px;
    padding: 16px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 4px;
    margin-top: 16px;
    justify-content: center;
}

.summary-stat {
    text-align: center;
}

.summary-stat-value {
    color: #00C853;
    font-size: 24px;
    font-weight: bold;
}

.summary-stat-label {
    color: #888;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}

/* Filter Type Badge */
.filter-type-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-right: 8px;
}

.filter-type-badge.day-of-week {
    background: #2979FF;
    color: #fff;
}

.filter-type-badge.combined {
    background: #FF6F00;
    color: #fff;
}

.filter-type-badge.session-context {
    background: #9C27B0;
    color: #fff;
}

.filter-type-badge.volatility-regime {
    background: #00BCD4;
    color: #fff;
}

.filter-type-badge.multi-day {
    background: #4CAF50;
    color: #fff;
}
</style>
"""


def render_experimental_alerts(
    scanner: ExperimentalScanner,
    instrument: str = 'MGC'
):
    """
    Render experimental strategy alerts in professional trading terminal style

    Args:
        scanner: ExperimentalScanner instance
        instrument: Trading instrument
    """
    # Inject custom CSS
    st.markdown(EXPERIMENTAL_ALERTS_CSS, unsafe_allow_html=True)

    # Validate strategies data integrity (MANDATORY per CLAUDE.md)
    is_valid, validation_issues = scanner.validate_strategies(instrument=instrument)

    if not is_valid:
        # Show validation errors
        error_count = sum(1 for issue in validation_issues if 'ERROR' in issue)
        warning_count = sum(1 for issue in validation_issues if 'WARNING' in issue)

        st.error(
            f"⚠️ Experimental Strategies Validation FAILED: "
            f"{error_count} errors, {warning_count} warnings"
        )
        with st.expander("🔍 View Validation Issues", expanded=True):
            for issue in validation_issues:
                if 'ERROR' in issue:
                    st.error(issue)
                elif 'WARNING' in issue:
                    st.warning(issue)
                else:
                    st.info(issue)

        st.info(
            "Fix validation issues before using experimental strategies. "
            "Run: `python scripts/check/check_experimental_strategies.py`"
        )
        return  # Don't render alerts if validation fails

    # Show validation badge (PASS)
    st.success("✅ Experimental strategies validated")

    # Scan for matches
    matches = scanner.scan_for_matches(instrument=instrument)
    summary = scanner.get_experimental_summary(instrument=instrument)

    # Build HTML
    html_parts = []

    # Container start
    html_parts.append('<div class="experimental-alerts-container">')

    # Header
    html_parts.append('''
        <div class="experimental-alerts-header">
            <span class="icon">🎁</span>
            <span>EXPERIMENTAL EDGES - BONUS OPPORTUNITIES</span>
        </div>
    ''')

    # Show matches or no-matches message
    if matches:
        html_parts.append(f'<div style="color: #FFD600; margin-bottom: 12px; font-size: 14px;">')
        html_parts.append(f'✓ Found {len(matches)} matching experimental strategies today')
        html_parts.append('</div>')

        for match in matches:
            html_parts.append(render_alert_card(match))
    else:
        html_parts.append('''
            <div class="no-experimental-alerts">
                No experimental strategies match today's conditions.
                <br>Your 9 ACTIVE strategies are always available!
            </div>
        ''')

    # Summary stats
    html_parts.append(f'''
        <div class="experimental-summary">
            <div class="summary-stat">
                <div class="summary-stat-value">{summary['total_count']}</div>
                <div class="summary-stat-label">Total Experimental</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value">+{summary['total_expected_r']}R</div>
                <div class="summary-stat-label">Annual Bonus</div>
            </div>
            <div class="summary-stat">
                <div class="summary-stat-value">{summary['total_annual_frequency']:.0f}</div>
                <div class="summary-stat-label">Trades/Year</div>
            </div>
        </div>
    ''')

    # Container end
    html_parts.append('</div>')

    # Render
    st.markdown(''.join(html_parts), unsafe_allow_html=True)


def render_alert_card(match: Dict) -> str:
    """
    Render single alert card

    Args:
        match: Matching strategy dict from scanner

    Returns:
        HTML string for alert card
    """
    filter_type = match['filter_type']
    filter_type_lower = filter_type.lower().replace('_', '-')

    # Build HTML
    html = f'''
        <div class="experimental-alert-card">
            <div class="alert-title">
                <span class="filter-type-badge {filter_type_lower}">{filter_type}</span>
                {match['description']}
            </div>

            <div class="alert-metrics">
                <div class="alert-metric">
                    <div class="alert-metric-label">Expected R</div>
                    <div class="alert-metric-value positive">+{match['expected_r']:.3f}R</div>
                </div>
                <div class="alert-metric">
                    <div class="alert-metric-label">Win Rate</div>
                    <div class="alert-metric-value neutral">{match['win_rate']*100:.1f}%</div>
                </div>
                <div class="alert-metric">
                    <div class="alert-metric-label">Sample Size</div>
                    <div class="alert-metric-value neutral">{match['sample_size']} trades</div>
                </div>
                <div class="alert-metric">
                    <div class="alert-metric-label">Frequency</div>
                    <div class="alert-metric-value neutral">~{match['annual_frequency']:.0f}/year</div>
                </div>
            </div>

            <div class="alert-condition">
                📋 Condition: {match['filter_condition']}
            </div>

            <div class="alert-match-reason">
                ✓ {match['match_reason']}
            </div>
        </div>
    '''

    return html


def render_experimental_alerts_compact(
    scanner: ExperimentalScanner,
    instrument: str = 'MGC'
) -> int:
    """
    Render compact version - just count badge

    Returns:
        Number of matches
    """
    matches = scanner.scan_for_matches(instrument=instrument)
    count = len(matches)

    if count > 0:
        st.markdown(f'''
            <div style="
                background: linear-gradient(135deg, #FFD600 0%, #FF6F00 100%);
                color: #000;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
                display: inline-block;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                box-shadow: 0 2px 8px rgba(255, 214, 0, 0.4);
            ">
                🎁 {count} BONUS EDGE{"S" if count != 1 else ""} ACTIVE
            </div>
        ''', unsafe_allow_html=True)

    return count


# Demo function
def demo():
    """Demo the experimental alerts UI"""
    import duckdb
    from pathlib import Path

    st.set_page_config(page_title="Experimental Alerts Demo", layout="wide")

    # Dark theme
    st.markdown("""
        <style>
        .stApp {
            background-color: #0e1117;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🎁 Experimental Strategy Alerts - Demo")

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "db" / "gold.db"
    con = duckdb.connect(str(db_path))
    scanner = ExperimentalScanner(con)

    # Render alerts
    st.markdown("---")
    render_experimental_alerts(scanner, instrument='MGC')

    st.markdown("---")
    st.markdown("### Compact Version")
    count = render_experimental_alerts_compact(scanner, instrument='MGC')
    if count == 0:
        st.info("No matches today - check back on Tuesday/Monday/Wednesday!")

    con.close()


if __name__ == "__main__":
    demo()
