# Trading App Frontend Design Guide

This document applies the frontend-design skill principles to the trading app UI/UX.

## Design Philosophy: Professional Trading Terminal

**Aesthetic Direction**: Industrial/Utilitarian with Refined Data Visualization
- Professional traders need information density without clutter
- Real-time data must be instantly scannable
- Actions (trade entry/exit) must be one-click accessible
- Visual hierarchy emphasizes P&L, risk, and opportunity

## Design Principles for Trading App

### 1. Typography
- **Display/Headers**: Use a distinctive monospace or technical font (e.g., JetBrains Mono, IBM Plex Mono, Fira Code)
  - Trading terminals have a "terminal" aesthetic - embrace it
  - Monospace ensures numeric alignment
- **Body Text**: Clean, readable sans-serif (avoid Inter/Roboto)
- **Numbers**: Tabular figures for alignment
- **Price Action**: Bold, large font for critical prices

### 2. Color Strategy
**Core Palette:**
- Background: Dark theme (trading happens 24/7, eye strain matters)
- Green: Profitable trades, long positions, bullish signals (#00C853, #76FF03)
- Red: Losing trades, short positions, bearish signals (#FF1744, #F44336)
- Blue: Neutral info, pending orders (#2979FF, #00B0FF)
- Yellow/Orange: Warnings, alerts (#FFD600, #FF6F00)
- White/Gray: Text hierarchy

**Avoid**: Purple gradients, pastel colors, "startup" aesthetics

### 3. Layout & Composition
- **Grid-based with breakouts**: Data in structured grids, but allow key metrics to break grid for emphasis
- **Asymmetric emphasis**: P&L should dominate visual space when significant
- **Density vs Space**: Trading view dense, setup detection spacious
- **Multi-panel**: Dashboard, Chart, Trade Entry, Positions, AI Assistant as separate cards

### 4. Motion & Interactivity
- **Price updates**: Smooth number transitions (not jarring jumps)
- **Trade execution**: Satisfying confirmation animation
- **Alert pop-ups**: Slide in from side with urgency
- **Chart updates**: Real-time without lag perception
- **Hover states**: Show additional data (don't hide critical info)

### 5. Data Visualization
- **Charts**: Use plotly with custom dark theme
  - Candlesticks: Clear wicks, body contrast
  - ORB boxes: Distinct border, semi-transparent fill
  - Support/resistance: Dashed lines
- **Metrics Cards**:
  - Large number with context
  - Trend indicator (up/down arrow)
  - Sparkline for historical context
- **Tables**:
  - Alternating row colors
  - Sort indicators
  - Highlight on hover

### 6. Trading-Specific Components

**Trade Entry Panel:**
- Large BUY/SELL buttons with haptic feel
- Risk calculator visible (position size, R-value)
- One-click entry with confirmation
- Clear stop-loss and target visualization

**Setup Detector:**
- Traffic light system (Green = Trade, Yellow = Monitor, Red = No Trade)
- Setup details in expandable card
- Historical performance mini-chart
- Confidence indicators

**Position Tracker:**
- Real-time P&L with color intensity based on magnitude
- Time in trade
- Distance to target/stop
- Quick exit button

**AI Assistant:**
- Chat interface with trading context
- Prompt suggestions for common queries
- Trade journal integration
- Voice of a professional trader (not a chatbot)

## Implementation Guidelines

### Streamlit-Specific
Since this is a Streamlit app:
- Use `st.markdown()` with custom CSS for styling
- `st.columns()` for layout control
- `st.plotly_chart()` for charts
- `streamlit-autorefresh` for real-time updates
- Custom CSS injection for fonts, colors, animations

### CSS Variables (inject via st.markdown)
```css
:root {
    /* Colors */
    --bg-dark: #0A0E17;
    --bg-panel: #151922;
    --bg-hover: #1E2530;
    --border: #2A303C;

    --green: #00C853;
    --red: #FF1744;
    --blue: #2979FF;
    --yellow: #FFD600;

    --text-primary: #FFFFFF;
    --text-secondary: #8892A6;
    --text-muted: #4A5568;

    /* Typography */
    --font-mono: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

    /* Spacing */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;

    /* Animation */
    --transition-fast: 150ms ease;
    --transition-smooth: 300ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

### Animation Examples
```css
/* Price update flash */
@keyframes price-up {
    0%, 100% { background-color: transparent; }
    50% { background-color: rgba(0, 200, 83, 0.2); }
}

/* Alert slide-in */
@keyframes alert-slide {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

/* Button press */
.trade-button:active {
    transform: scale(0.98);
    transition: transform 0.1s;
}
```

## Mobile Considerations (app_mobile.py)
- Touch targets minimum 48px
- Swipe gestures for navigation
- Simplified layout (stack cards vertically)
- Essential info only (hide secondary metrics)
- Larger fonts for readability

## Accessibility
- High contrast text (WCAG AA minimum)
- Color is not the only indicator (use icons + color)
- Keyboard navigation for critical actions
- Screen reader support for numeric values
- Focus indicators on interactive elements

## Performance
- Minimize re-renders (Streamlit reruns entire script)
- Cache expensive computations
- Lazy load charts/data
- Debounce real-time updates (5 second refresh is fine)

## Design Pattern Library

### Metric Card
```python
st.markdown(f"""
<div class="metric-card">
    <div class="metric-label">Daily P&L</div>
    <div class="metric-value {'positive' if pnl > 0 else 'negative'}">
        {pnl:+.2f}R
    </div>
    <div class="metric-change">
        <span class="arrow">{'↑' if pnl > 0 else '↓'}</span>
        {abs(pnl_change):.1f}%
    </div>
</div>
""", unsafe_allow_html=True)
```

### Status Indicator
```python
status_colors = {
    "TRADE": "green",
    "MONITOR": "yellow",
    "NO_TRADE": "red"
}
st.markdown(f"""
<div class="status-indicator {status_colors[status]}">
    <div class="status-dot"></div>
    <div class="status-text">{status}</div>
</div>
""", unsafe_allow_html=True)
```

## Next Steps for Implementation

When updating the trading app UI:
1. Read this guide + skills/frontend-design/SKILL.md
2. Analyze current component aesthetics
3. Choose BOLD improvements (not incremental tweaks)
4. Implement with full attention to detail
5. Test with real trading scenarios

## Remember
- Traders value FUNCTION over form, but great design enhances function
- Information density is good, clutter is bad
- Every millisecond of latency matters
- Dark theme is non-negotiable for extended use
- Real money is on the line - clarity saves money
