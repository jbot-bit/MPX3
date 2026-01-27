"""
Professional UI Components & Styling
Modern dark-themed trading dashboard
"""

import streamlit as st

# ============================================================================
# PROFESSIONAL CSS THEME
# ============================================================================

PROFESSIONAL_CSS = """
<style>
    /* Import Professional Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global Styling */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Custom Cards */
    .pro-card {
        background: linear-gradient(145deg, #1a1d26 0%, #252933 100%);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 24px;
        margin: 12px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: all 0.3s ease;
    }

    .pro-card:hover {
        border-color: rgba(255, 255, 255, 0.12);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
        transform: translateY(-2px);
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #2d3139 0%, #1e2128 100%);
        border: 1px solid rgba(99, 102, 241, 0.1);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        transition: all 0.2s ease;
    }

    .metric-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
        transform: scale(1.02);
    }

    .metric-label {
        font-size: 12px;
        font-weight: 500;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #f3f4f6;
        line-height: 1.2;
    }

    .metric-change {
        font-size: 13px;
        font-weight: 500;
        margin-top: 4px;
    }

    .metric-positive {
        color: #10b981;
    }

    .metric-negative {
        color: #ef4444;
    }

    .metric-neutral {
        color: #6b7280;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.3px;
        margin: 4px;
    }

    .badge-active {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .badge-forming {
        background: rgba(59, 130, 246, 0.15);
        color: #3b82f6;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    .badge-upcoming {
        background: rgba(251, 191, 36, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.3);
    }

    .badge-inactive {
        background: rgba(107, 114, 128, 0.15);
        color: #9ca3af;
        border: 1px solid rgba(107, 114, 128, 0.3);
    }

    /* Intelligence Panel */
    .intelligence-panel {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 50%, #3b82f6 100%);
        border: 2px solid rgba(59, 130, 246, 0.4);
        border-radius: 16px;
        padding: 32px;
        margin: 20px 0;
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.2);
    }

    .intelligence-critical {
        background: linear-gradient(135deg, #991b1b 0%, #dc2626 50%, #ef4444 100%);
        border-color: rgba(239, 68, 68, 0.4);
        animation: pulse 2s ease-in-out infinite;
    }

    .intelligence-high {
        background: linear-gradient(135deg, #ea580c 0%, #f97316 50%, #fb923c 100%);
        border-color: rgba(249, 115, 22, 0.4);
    }

    .intelligence-success {
        background: linear-gradient(135deg, #047857 0%, #059669 50%, #10b981 100%);
        border-color: rgba(16, 185, 129, 0.4);
    }

    @keyframes pulse {
        0%, 100% { box-shadow: 0 8px 32px rgba(239, 68, 68, 0.2); }
        50% { box-shadow: 0 8px 48px rgba(239, 68, 68, 0.4); }
    }

    .intelligence-action {
        font-size: 48px;
        font-weight: 800;
        color: white;
        text-align: center;
        margin: 16px 0;
        text-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
        letter-spacing: -1px;
    }

    .intelligence-subtitle {
        font-size: 20px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
        text-align: center;
        margin-bottom: 24px;
    }

    /* Tables */
    .dataframe {
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    .dataframe thead tr th {
        background: #1e2128 !important;
        color: #9ca3af !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        border: none !important;
        padding: 12px !important;
    }

    .dataframe tbody tr {
        border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
        transition: background 0.2s ease;
    }

    .dataframe tbody tr:hover {
        background: rgba(99, 102, 241, 0.05) !important;
    }

    .dataframe tbody tr td {
        color: #e5e7eb !important;
        padding: 14px 12px !important;
        border: none !important;
        font-size: 14px !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.3);
        transform: translateY(-2px);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px 10px 0 0;
        padding: 14px 24px;
        font-weight: 600;
        font-size: 15px;
        color: #9ca3af;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.06);
        color: #e5e7eb;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border-color: #6366f1;
    }

    /* Sidebar */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1d26 0%, #0f1117 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    .sidebar .sidebar-content {
        padding: 20px;
    }

    /* Headers */
    h1 {
        font-weight: 800;
        font-size: 36px;
        color: #f9fafb;
        letter-spacing: -0.5px;
        margin-bottom: 8px;
    }

    h2 {
        font-weight: 700;
        font-size: 28px;
        color: #f3f4f6;
        letter-spacing: -0.3px;
        margin-top: 24px;
        margin-bottom: 16px;
    }

    h3 {
        font-weight: 600;
        font-size: 20px;
        color: #e5e7eb;
        margin-top: 20px;
        margin-bottom: 12px;
    }

    /* Dividers */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.1) 50%, transparent 100%);
        margin: 28px 0;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
        padding: 12px 16px;
        font-weight: 600;
        color: #e5e7eb;
        transition: all 0.2s ease;
    }

    .streamlit-expanderHeader:hover {
        background: rgba(255, 255, 255, 0.04);
        border-color: rgba(99, 102, 241, 0.3);
    }

    /* Input fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #f3f4f6;
        padding: 10px 14px;
        font-size: 14px;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }

    /* Success/Warning/Error boxes */
    .stSuccess, .stWarning, .stError, .stInfo {
        border-radius: 10px;
        padding: 16px;
        border-left: 4px solid;
    }

    .stSuccess {
        background: rgba(16, 185, 129, 0.1);
        border-left-color: #10b981;
    }

    .stWarning {
        background: rgba(251, 191, 36, 0.1);
        border-left-color: #fbbf24;
    }

    .stError {
        background: rgba(239, 68, 68, 0.1);
        border-left-color: #ef4444;
    }

    .stInfo {
        background: rgba(59, 130, 246, 0.1);
        border-left-color: #3b82f6;
    }

    /* Progress bars */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
    }

    /* Countdown timer */
    .countdown-timer {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 16px 0;
    }

    .countdown-value {
        font-size: 48px;
        font-weight: 800;
        color: #6366f1;
        font-variant-numeric: tabular-nums;
        letter-spacing: -2px;
    }

    .countdown-label {
        font-size: 14px;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 8px;
    }

    /* Price Display */
    .price-display {
        font-size: 42px;
        font-weight: 800;
        font-variant-numeric: tabular-nums;
        color: #f9fafb;
        letter-spacing: -1px;
        line-height: 1;
    }

    .price-change-up {
        color: #10b981;
    }

    .price-change-down {
        color: #ef4444;
    }

    /* Chart container */
    .chart-container {
        background: #1a1d26;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 16px;
        margin: 16px 0;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.02);
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(99, 102, 241, 0.3);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(99, 102, 241, 0.5);
    }
</style>
"""


def inject_professional_css():
    """Inject professional CSS into the Streamlit app"""
    st.markdown(PROFESSIONAL_CSS, unsafe_allow_html=True)


def render_pro_metric(label: str, value: str, change: str = None, change_positive: bool = True):
    """Render a professional metric card"""
    change_class = "metric-positive" if change_positive else "metric-negative"
    change_html = f'<div class="metric-change {change_class}">{change}</div>' if change else ''

    html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {change_html}
    </div>
    """
    return html


def render_status_badge(text: str, status: str = "active"):
    """Render a status badge

    Args:
        text: Badge text
        status: One of "active", "forming", "upcoming", "inactive"
    """
    return f'<span class="status-badge badge-{status}">{text}</span>'


def render_intelligence_card(action: str, subtitle: str, priority: str = "medium"):
    """Render intelligence recommendation card

    Args:
        action: Main action text (e.g., "GO LONG", "WAIT")
        subtitle: Subtitle text
        priority: One of "critical", "high", "medium", "low"
    """
    priority_class = f"intelligence-{priority}"

    html = f"""
    <div class="intelligence-panel {priority_class}">
        <div class="intelligence-action">{action}</div>
        <div class="intelligence-subtitle">{subtitle}</div>
    </div>
    """
    return html


def render_countdown_timer(value: str, label: str):
    """Render countdown timer"""
    html = f"""
    <div class="countdown-timer">
        <div class="countdown-value">{value}</div>
        <div class="countdown-label">{label}</div>
    </div>
    """
    return html


def render_price_display(price: float, change: float = None):
    """Render large price display"""
    price_str = f"${price:,.2f}"

    if change is not None:
        change_class = "price-change-up" if change >= 0 else "price-change-down"
        change_symbol = "▲" if change >= 0 else "▼"
        change_html = f'<span class="{change_class}" style="font-size: 24px; margin-left: 12px;">{change_symbol} {abs(change):.2f}</span>'
    else:
        change_html = ''

    html = f"""
    <div style="text-align: center; padding: 24px 0;">
        <div class="price-display">{price_str}{change_html}</div>
    </div>
    """
    return html
