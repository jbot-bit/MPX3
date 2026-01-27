"""
TERMINAL THEME - Professional Trading Terminal Design System

Aesthetic Direction: Industrial/Utilitarian with Retro-Futuristic Elements
- Bloomberg Terminal meets refined Cyberpunk
- Matrix-inspired green accents on deep space black
- Monospace typography with military precision
- Scan lines, subtle glows, terminal authenticity
- Information density without chaos
"""

TERMINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Share+Tech+Mono&family=Rajdhani:wght@400;500;600;700&display=swap');

:root {
    /* COLORS - Deep Space Trading Terminal */
    --bg-void: #0a0e15;
    --bg-terminal: #0d1117;
    --bg-panel: #161b22;
    --bg-panel-hover: #1c2128;
    --bg-input: #0d1117;
    --border-dim: #21262d;
    --border-bright: #30363d;
    --border-active: #58a6ff;

    /* MATRIX GREEN - Primary Accent */
    --green-dark: #00ff41;
    --green-bright: #0aff6c;
    --green-glow: rgba(0, 255, 65, 0.3);
    --green-dim: #00a82d;

    /* TRADING COLORS */
    --profit-green: #00ff41;
    --loss-red: #ff0844;
    --neutral-blue: #58a6ff;
    --warning-amber: #ffb627;
    --alert-orange: #ff6e42;

    /* TEXT HIERARCHY */
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-tertiary: #6e7681;
    --text-inverse: #0d1117;

    /* TYPOGRAPHY */
    --font-terminal: 'JetBrains Mono', 'Share Tech Mono', 'Courier New', monospace;
    --font-display: 'Rajdhani', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'Share Tech Mono', 'Courier New', monospace;

    /* SPACING */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-2xl: 48px;

    /* ANIMATION */
    --transition-fast: 0.1s cubic-bezier(0.4, 0, 0.2, 1);
    --transition-smooth: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    --transition-slow: 0.5s cubic-bezier(0.4, 0, 0.2, 1);

    /* EFFECTS */
    --glow-green: 0 0 10px var(--green-glow);
    --glow-profit: 0 0 15px rgba(0, 255, 65, 0.4);
    --glow-loss: 0 0 15px rgba(255, 8, 68, 0.4);
    --scan-line: repeating-linear-gradient(
        0deg,
        rgba(0, 255, 65, 0.03) 0px,
        rgba(0, 255, 65, 0.03) 1px,
        transparent 1px,
        transparent 2px
    );
}

/* GLOBAL RESETS */
* {
    font-variant-numeric: tabular-nums;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* STREAMLIT OVERRIDES */
.stApp {
    background: var(--bg-void);
    font-family: var(--font-terminal);
}

/* Remove Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* SCAN LINE EFFECT - Subtle CRT aesthetic */
.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--scan-line);
    pointer-events: none;
    opacity: 0.4;
    z-index: 1;
    animation: scanline 8s linear infinite;
}

@keyframes scanline {
    0% { transform: translateY(0); }
    100% { transform: translateY(4px); }
}

/* TERMINAL HEADER */
.terminal-header {
    background: var(--bg-terminal);
    border-bottom: 2px solid var(--border-bright);
    padding: var(--space-lg) var(--space-xl);
    margin: 0 0 var(--space-xl) 0;
    position: relative;
    overflow: hidden;
}

.terminal-header::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg,
        transparent,
        var(--green-bright),
        transparent
    );
    animation: header-pulse 3s ease-in-out infinite;
}

@keyframes header-pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
}

.terminal-title {
    font-family: var(--font-display);
    font-size: 48px;
    font-weight: 700;
    letter-spacing: -1px;
    color: var(--green-bright);
    text-transform: uppercase;
    margin: 0;
    text-shadow: 0 0 20px var(--green-glow);
}

.terminal-subtitle {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--text-secondary);
    letter-spacing: 2px;
    margin: var(--space-sm) 0 0 0;
}

/* METRIC CARDS - Trading Terminal Style */
.metric-card {
    background: var(--bg-panel);
    border: 1px solid var(--border-bright);
    border-radius: 0;
    padding: var(--space-lg);
    position: relative;
    transition: all var(--transition-smooth);
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: var(--green-dark);
    opacity: 0;
    transition: opacity var(--transition-fast);
}

.metric-card:hover {
    border-color: var(--green-dark);
    box-shadow: var(--glow-green);
}

.metric-card:hover::before {
    opacity: 1;
}

.metric-label {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: var(--space-sm);
}

.metric-value {
    font-family: var(--font-terminal);
    font-size: 36px;
    font-weight: 700;
    line-height: 1;
    margin-bottom: var(--space-xs);
}

.metric-value.positive {
    color: var(--profit-green);
    text-shadow: var(--glow-profit);
    animation: pulse-profit 2s ease-in-out infinite;
}

.metric-value.negative {
    color: var(--loss-red);
    text-shadow: var(--glow-loss);
}

.metric-value.neutral {
    color: var(--text-primary);
}

@keyframes pulse-profit {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.85; }
}

.metric-change {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: var(--space-xs);
}

/* STATUS INDICATORS */
.status-indicator {
    display: inline-flex;
    align-items: center;
    gap: var(--space-sm);
    padding: var(--space-sm) var(--space-md);
    background: var(--bg-panel);
    border: 1px solid var(--border-bright);
    border-radius: 0;
    font-family: var(--font-mono);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    position: relative;
}

.status-dot::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100%;
    height: 100%;
    border-radius: 50%;
    animation: status-pulse 2s ease-in-out infinite;
}

.status-indicator.green .status-dot {
    background: var(--profit-green);
    box-shadow: 0 0 10px var(--profit-green);
}

.status-indicator.green .status-dot::before {
    background: var(--profit-green);
}

.status-indicator.red .status-dot {
    background: var(--loss-red);
    box-shadow: 0 0 10px var(--loss-red);
}

.status-indicator.yellow .status-dot {
    background: var(--warning-amber);
    box-shadow: 0 0 10px var(--warning-amber);
}

@keyframes status-pulse {
    0%, 100% {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1);
    }
    50% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(2);
    }
}

/* PRICE DISPLAY - Large, Terminal-Style */
.price-display {
    font-family: var(--font-terminal);
    font-size: 64px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -2px;
    color: var(--green-bright);
    text-shadow: 0 0 30px var(--green-glow);
    animation: price-flicker 0.1s;
}

@keyframes price-flicker {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.95; }
}

.price-display.up {
    color: var(--profit-green);
    animation: price-up 0.5s ease-out;
}

.price-display.down {
    color: var(--loss-red);
    animation: price-down 0.5s ease-out;
}

@keyframes price-up {
    0% {
        transform: translateY(2px);
        color: var(--profit-green);
        text-shadow: 0 0 40px var(--profit-green);
    }
    100% {
        transform: translateY(0);
    }
}

@keyframes price-down {
    0% {
        transform: translateY(-2px);
        color: var(--loss-red);
        text-shadow: 0 0 40px var(--loss-red);
    }
    100% {
        transform: translateY(0);
    }
}

/* BUTTON SYSTEM - Terminal Actions */
.stButton button {
    background: var(--bg-panel);
    color: var(--text-primary);
    border: 1px solid var(--border-bright);
    border-radius: 0;
    padding: var(--space-md) var(--space-xl);
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all var(--transition-fast);
}

.stButton button:hover {
    background: var(--bg-panel-hover);
    border-color: var(--green-dark);
    box-shadow: var(--glow-green);
    transform: translateY(-1px);
}

.stButton button:active {
    transform: translateY(0);
}

/* PRIMARY BUTTON - Trade Actions */
.stButton.primary button {
    background: var(--green-dark);
    color: var(--text-inverse);
    border-color: var(--green-bright);
    box-shadow: var(--glow-green);
}

.stButton.primary button:hover {
    background: var(--green-bright);
    box-shadow: 0 0 20px var(--green-glow);
}

/* DANGER BUTTON - Exit/Stop */
.stButton.danger button {
    background: var(--loss-red);
    color: var(--text-primary);
    border-color: var(--loss-red);
}

/* TERMINAL PANEL */
.terminal-panel {
    background: var(--bg-panel);
    border: 1px solid var(--border-bright);
    border-radius: 0;
    padding: var(--space-lg);
    margin-bottom: var(--space-lg);
    position: relative;
}

.terminal-panel::before {
    content: attr(data-title);
    position: absolute;
    top: -10px;
    left: var(--space-md);
    background: var(--bg-void);
    padding: 0 var(--space-sm);
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--green-dark);
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* DATA TABLE - Terminal Grid */
.dataframe {
    background: var(--bg-terminal) !important;
    border: 1px solid var(--border-bright) !important;
    font-family: var(--font-terminal) !important;
    font-size: 13px !important;
}

.dataframe thead tr th {
    background: var(--bg-panel) !important;
    color: var(--green-dark) !important;
    border-bottom: 2px solid var(--border-bright) !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}

.dataframe tbody tr {
    border-bottom: 1px solid var(--border-dim) !important;
}

.dataframe tbody tr:hover {
    background: var(--bg-panel-hover) !important;
}

/* CHART CUSTOMIZATION */
.js-plotly-plot {
    background: var(--bg-terminal) !important;
    border: 1px solid var(--border-bright) !important;
}

/* INPUT FIELDS */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-bright) !important;
    border-radius: 0 !important;
    color: var(--text-primary) !important;
    font-family: var(--font-terminal) !important;
    padding: var(--space-md) !important;
}

.stTextInput input:focus, .stNumberInput input:focus {
    border-color: var(--green-dark) !important;
    box-shadow: var(--glow-green) !important;
}

/* COUNTDOWN TIMER */
.countdown-timer {
    font-family: var(--font-terminal);
    font-size: 28px;
    font-weight: 700;
    color: var(--warning-amber);
    text-align: center;
    padding: var(--space-md);
    background: var(--bg-panel);
    border: 1px solid var(--border-bright);
    letter-spacing: 2px;
}

.countdown-timer.urgent {
    color: var(--loss-red);
    animation: countdown-pulse 1s ease-in-out infinite;
}

@keyframes countdown-pulse {
    0%, 100% {
        transform: scale(1);
        box-shadow: none;
    }
    50% {
        transform: scale(1.05);
        box-shadow: 0 0 20px var(--loss-red);
    }
}

/* ALERT SYSTEM */
.alert-slide {
    animation: alert-slide-in 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes alert-slide-in {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* GLITCH EFFECT - Subtle, for emphasis */
.glitch {
    position: relative;
}

.glitch::before,
.glitch::after {
    content: attr(data-text);
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0.8;
}

.glitch::before {
    animation: glitch-1 2s infinite;
    color: var(--green-bright);
    z-index: -1;
}

.glitch::after {
    animation: glitch-2 2s infinite;
    color: var(--loss-red);
    z-index: -2;
}

@keyframes glitch-1 {
    0%, 100% {
        transform: translate(0);
        opacity: 0;
    }
    33% {
        transform: translate(-2px, 2px);
        opacity: 0.8;
    }
    66% {
        transform: translate(2px, -2px);
        opacity: 0.8;
    }
}

@keyframes glitch-2 {
    0%, 100% {
        transform: translate(0);
        opacity: 0;
    }
    33% {
        transform: translate(2px, -2px);
        opacity: 0.6;
    }
    66% {
        transform: translate(-2px, 2px);
        opacity: 0.6;
    }
}

/* MOBILE RESPONSIVE */
@media (max-width: 768px) {
    .terminal-title {
        font-size: 32px;
    }

    .price-display {
        font-size: 42px;
    }

    .metric-value {
        font-size: 24px;
    }

    .terminal-panel {
        padding: var(--space-md);
    }
}

/* LOADING ANIMATIONS */
.loading-spinner {
    border: 3px solid var(--border-dim);
    border-top: 3px solid var(--green-dark);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: var(--space-lg) auto;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* SYSTEM FONT STACK - Fallbacks */
body {
    font-feature-settings: "tnum" 1, "ss01" 1;
}

/* ACCESSIBILITY - High Contrast Mode Support */
@media (prefers-contrast: high) {
    :root {
        --border-bright: #ffffff;
        --text-primary: #ffffff;
        --green-dark: #00ff00;
    }
}
</style>
"""

def inject_terminal_theme():
    """Inject the professional trading terminal theme"""
    import streamlit as st
    st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
