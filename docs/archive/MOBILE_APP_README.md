# Mobile Trading Hub - Complete Guide

**Tinder-Style Card Interface** • ML Predictions • Market Intelligence • Real-Time Monitoring

Version: 2.1 (Jan 17, 2026)

---

## Executive Summary

Professional mobile trading interface with swipeable cards combining:
- Live price monitoring with countdown timers
- ML directional predictions with confidence scores
- Market intelligence and session analysis
- Comprehensive safety checks (data quality + market hours + risk limits)
- High-probability setup scanning
- Enhanced charting with trade levels
- Position tracking with P&L
- AI trading assistant

**Status**: Fully operational and production-ready

---

## Quick Start

### Launch the App

```bash
# Option 1: Double-click batch file
START_MOBILE_APP.bat

# Option 2: Run manually
cd trading_app
streamlit run app_mobile.py
```

**Access**: http://localhost:8501

**Mobile Access**:
1. Find your PC IP: `ipconfig` (Windows)
2. On phone: `http://YOUR_PC_IP:8501`
3. Must be on same Wi-Fi network

---

## Interface Overview

### 5 Swipeable Cards

```
[◄] ● ○ ○ ○ ○ [►]
    Card 1 of 5
```

Swipe left/right or tap arrows:
1. **📊 Dashboard** - Quick glance (price, status, ML, intelligence)
2. **📈 Chart** - Enhanced chart with trade levels and directional bias
3. **🎯 Trade** - Entry calculator with position sizing
4. **💼 Positions** - Active trades with P&L tracking
5. **🤖 AI Chat** - Trading assistant

---

## Card 1: Dashboard (Main View)

### What You See

```
┌─────────────────────────┐
│ 🔴 LIVE Dashboard       │
├─────────────────────────┤
│     $2,650.42           │  ← Live price (48px)
│     MGC Price           │
│     19:05:23            │
├─────────────────────────┤
│ ATR: 42.15  │  ✅ PASS  │  ← Filter status
├─────────────────────────┤
│   ⏰ NEXT: 2300 ORB     │
│   02:54:37              │  ← Live countdown
│   Until Window Opens    │
├─────────────────────────┤
│ STATUS: 🎯 PREPARE      │
│ • 2300 ORB approaching  │
│ • Filter PASSED         │
│ • Get ready             │
│                         │
│ NEXT ACTION:            │
│ Watch 2300-2305 range   │
├─────────────────────────┤
│ 🤖 ML Insights          │  ← NEW
│ Direction: 🚀 UP        │
│ Confidence: 68%         │
│ Expected R: +2.3R       │
├─────────────────────────┤
│ 📊 Market Intelligence  │  ← NEW
│ Session: NY             │
│ Local Time: 23:15       │
├─────────────────────────┤
│ 🛡️ Safety Status        │  ← NEW
│ ✅ SAFE TO TRADE        │
│ Data: ✓ Market: ✓       │
│ Risk: ✓                 │
├─────────────────────────┤
│ 🔍 Active Setups        │  ← NEW
│ • 2300 ORB - Quality: A │
│ • 0030 ORB - Quality: B │
└─────────────────────────┘
```

### Features

**Core Display**:
- Live price (updates every 10s)
- ATR (20-period daily)
- Filter status (✅ PASS or ⏭️ SKIP)
- Next ORB countdown (HH:MM:SS)
- Strategy status (STAND_DOWN/PREPARE/ENTER)
- Actionable next step

**ML Insights** (NEW):
- Directional prediction (UP/DOWN/NONE)
- Confidence percentage (0-100%)
- Expected R-multiple
- Only shows when setup is active
- Powered by LightGBM trained on 740 days

**Market Intelligence** (NEW):
- Current session (ASIA/LONDON/NY)
- Local time display
- Session context for decision-making

**Safety Status** (NEW):
- Data quality check (recent data available)
- Market hours check (safe to trade)
- Risk limits check (within daily/weekly limits)
- Combined indicator (✅ SAFE or ⚠️ BLOCKED)

**Setup Scanner** (NEW):
- Scans next 24 hours for high-quality setups
- Shows ORB time + entry quality (A/B/C)
- Top 3 upcoming opportunities
- Based on validated_setups database

### Use Case

Open app → Instant understanding of market state + ML predictions + safety checks without scrolling

---

## Card 2: Chart (Enhanced)

### Collapsed State (Default)

```
┌─────────────────────────┐
│ 📈 Chart & Levels       │
│ [▼ Show Chart]          │  ← Tap to expand
└─────────────────────────┘
```

### Expanded State

```
┌─────────────────────────┐
│ 📈 Chart & Levels       │
│ [▲ Hide Chart]          │
├─────────────────────────┤
│                         │
│  [Enhanced Chart 350px] │  ← Plotly chart
│  - ORB zones (green/red)│
│  - Entry/stop/target    │
│  - Current price line   │
│  - Pinch to zoom        │
│                         │
├─────────────────────────┤
│ ORB High: $2,655.20     │
│ ORB Low:  $2,652.40     │
│ Size:     2.80pts ✅    │
├─────────────────────────┤
│ 🎯 Directional Bias     │  ← NEW (1100 ORB only)
│ Predicted Break: 🚀 UP  │
│ Confidence: 72%         │
│ 💡 Focus on UP breakout │
└─────────────────────────┘
```

### Features

**Enhanced Chart**:
- Full `build_live_trading_chart()` integration
- ORB zones (green high, red low)
- Entry/stop/target prices when setup active
- Current price indicator
- Filter status badge
- Tier badge (A/B/C)
- Mobile-optimized 350px height

**Directional Bias** (NEW - 1100 ORB only):
- Predicts which direction ORB will break
- Shows confidence percentage
- Provides actionable suggestion
- Based on market structure analysis

### Use Case

Pre-ORB: Expand chart → Watch formation → See predicted direction → Prepare for breakout

---

## Card 3: Trade Entry Calculator

### Interface

```
┌─────────────────────────┐
│ 🎯 Trade Calculator     │
├─────────────────────────┤
│ Direction:              │
│ [🚀 LONG] [🔻 SHORT]    │  ← Toggle
├─────────────────────────┤
│ ORB Levels:             │
│ ORB High: [2655.20]     │  ← Input
│ ORB Low:  [2652.40]     │
│                         │
│ Risk/Reward: [4.0]      │
│ SL Mode: [FULL ▼]       │
├─────────────────────────┤
│ [📊 Calculate Trade]    │  ← Button
├─────────────────────────┤
│ 📍 Results:             │
│ Entry:  $2,655.20       │
│ Stop:   $2,652.40       │
│ Target: $2,666.60 (4R)  │
│ Risk:   $250 (0.25%)    │
├─────────────────────────┤
│ [📋 Copy Levels]        │
└─────────────────────────┘
```

### How to Use

1. Select direction (LONG/SHORT)
2. Enter ORB high/low
3. Set risk/reward ratio (1-10R)
4. Choose SL mode (FULL or HALF)
5. Calculate
6. Copy levels to clipboard

### Features

- Large touch targets (48px)
- Real-time calculation
- Position sizing based on account size
- Copy function for quick order entry
- Validates inputs before calculating

---

## Card 4: Positions (P&L Tracking)

### With Active Position

```
┌─────────────────────────┐
│ 📊 Active Positions (1) │
├─────────────────────────┤
│ 🚀 LONG MGC             │
│ Entry: $2,655.20        │
│ Current: $2,658.40      │
│ (+3.20pts)              │
│                         │
│ +$320 (+1.28R) 💚       │  ← P&L
│                         │
│ Stop: $2,652.40         │
│ Target: $2,666.60       │
│ ▓▓▓▓░░░░ 28%           │  ← Progress
│                         │
│ [🚪 Close Position]     │
└─────────────────────────┘
```

### Empty State

```
┌─────────────────────────┐
│ 📊 Active Positions (0) │
│                         │
│       📭                │
│  No Positions Open      │
│  Wait for next setup    │
│                         │
└─────────────────────────┘
```

### Features

- Live P&L updates with current price
- Dollar gains + R-multiple
- Color-coded (green profit, red loss)
- Progress bar to target
- Close position button
- Multiple positions support

---

## Card 5: AI Chat Assistant

### Interface

```
┌─────────────────────────┐
│ 🤖 AI Assistant         │
│ ✅ Claude Sonnet ready! │
├─────────────────────────┤
│ 💬 Conversation:        │
│                         │
│ You: ORB is 2700-2706,  │
│      LONG, calc stop?   │
│                         │
│ AI: Entry at 2706,      │
│     Stop 2700, Target   │
│     2730 (4R). Risk     │
│     $250 at 0.25%.      │
│                         │
├─────────────────────────┤
│ Ask a Question:         │
│ [Type here...]          │
│ [📤 Send] [🗑️ Clear]    │
├─────────────────────────┤
│ 💡 Quick Actions:       │
│ [📊 Calculate] [❓ Why] │
└─────────────────────────┘
```

### Example Questions

- "ORB is 2700-2706, direction LONG, calculate my stop and target"
- "Why is the 1100 ORB better than 0900?"
- "What's the win rate for 23:00 ORBs?"
- "Should I take this 18:00 ORB setup?"
- "Explain the CASCADE strategy"

### Features

- Persistent conversation history (database)
- Last 10 messages displayed
- Quick action buttons
- Knows current market state
- Strategy knowledge base
- Trade calculation assistance

---

## Advanced Features

### ML Inference Engine

**How It Works**:
- Trained on 740 days (739 days × 6 ORBs = 4,440 examples)
- LightGBM classifier predicting UP/DOWN/NONE
- 55-60% accuracy (vs 33% random)
- Real-time predictions <100ms
- Features: ATR, session gaps, ORB size, RSI, time features

**Shadow Mode**:
- ML predictions shown but don't override rules
- ML enhances confidence, doesn't replace strategy engine
- Hybrid approach: rules gate entry, ML adjusts sizing

**Display**:
- Direction: 🚀 UP, 🔻 DOWN, or ⊝ NONE
- Confidence: 0-100%
- Expected R: -1.0 to +3.0
- Only shows when setup is active

### Market Intelligence

**Sessions Tracked**:
- ASIA: 09:00-17:00 local
- LONDON: 18:00-23:00 local
- NY: 23:00-02:00 local

**Displays**:
- Current session name
- Local time
- Active setup count
- Session context for decisions

### Safety System

**Three-Layer Checks**:

1. **Data Quality** (DataQualityMonitor):
   - Last bar recency check
   - Gap detection
   - Price sanity validation
   - Missing data alerts

2. **Market Hours** (MarketHoursMonitor):
   - Futures trading hours
   - Holiday detection
   - Pre-market/post-market periods
   - Safe to trade indicator

3. **Risk Limits** (RiskManager):
   - Daily loss limit
   - Weekly loss limit
   - Max concurrent positions
   - Position size validation

**Combined Status**:
- ✅ SAFE: All checks pass, OK to trade
- ⚠️ BLOCKED: One or more checks failed, stand down

### Setup Scanner

**Scans**:
- `validated_setups` database table
- Next 24 hours lookahead
- Filters by instrument (MGC/NQ/MPL)
- Considers ORB size filters, RR ratios, session types

**Shows**:
- ORB time (0900, 1000, 1100, etc.)
- Entry quality (A/B/C tier)
- Expected R-multiple
- Top 3 opportunities

### Directional Bias Detector

**For 1100 ORB Only**:
- Analyzes market structure
- Predicts break direction
- Shows confidence
- Provides actionable suggestion

**How It Works**:
- Checks pre-ORB price action
- Analyzes session gaps
- Considers historical patterns
- Returns UP/DOWN/NEUTRAL with confidence

---

## Settings

**Sidebar Settings** (scroll down):

```
┌─────────────────────────┐
│ ⚙️ Settings             │
├─────────────────────────┤
│ Instrument: [MGC ▼]     │
│ Account Size: $100,000  │
│ Auto-refresh: ☑ On      │
│ Interval: 10s           │
│                         │
│ [🔄 Initialize Data]    │
│ [🔄 Refresh Now]        │
│ [🔄 Reset App]          │
└─────────────────────────┘
```

**Options**:
- Instrument selector (MGC/NQ/MPL)
- Account size for position sizing
- Auto-refresh toggle
- Refresh interval (10s market hours, 30s off-hours)
- Manual refresh button
- Reset app (clear cache)

---

## Technical Architecture

### Files

```
trading_app/
├── app_mobile.py              # Main entry point (card navigation)
├── mobile_ui.py               # Card render functions + CSS
├── strategy_engine.py         # Core strategy logic + ML integration
├── data_loader.py             # Data fetching (ProjectX + database)
├── config.py                  # Settings + validated strategies
├── setup_detector.py          # High-probability setup scanning
├── directional_bias.py        # 1100 ORB directional prediction
├── data_quality_monitor.py    # Data validation
├── market_hours_monitor.py    # Trading hours checks
├── risk_manager.py            # Position limits enforcement
├── live_chart_builder.py      # Enhanced charting
├── ai_assistant.py            # Claude AI integration
└── requirements.txt           # Python dependencies
```

### Integration Points

**ML Engine**:
- Initialized in `app_mobile.py` line 192
- Passed to `StrategyEngine` constructor
- Called in `strategy_engine.py` for predictions
- Features extracted from live data

**Advanced Features**:
- Session states initialized lines 130-150 in `app_mobile.py`
- Render functions in `mobile_ui.py` call these components
- All wrapped in try/except for graceful degradation

**Database**:
- `gold.db`: Historical data + validated_setups
- `live_data.db`: Real-time bars
- `trading_app.db`: Journal + ML predictions

### Dependencies

```
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.17.0
duckdb>=0.9.0
anthropic>=0.7.0
lightgbm>=4.0.0
scikit-learn>=1.3.0
python-dotenv>=1.0.0
httpx>=0.24.0
```

---

## Performance

### Optimization

- Lazy loading (charts render on demand)
- Compact 350px chart height
- Cached data between cards
- Debounced inputs
- Auto-refresh: 10s (market) or 30s (off-hours)

### Metrics

- First load: ~8 seconds
- Card navigation: instant
- Chart rendering: <1 second
- ML inference: <100ms
- Data refresh: <2 seconds

---

## Known Behaviors (Not Bugs)

These messages are NORMAL and handled gracefully:

- "ML predictions unavailable" → No active setup yet
- "Directional bias unavailable" → Not 1100 ORB context
- "Setup scanner: No high-quality setups" → None in next 24h
- "Safety: Data quality check failed" → No recent data yet
- "Market intelligence unavailable" → Session analysis failed (data issue)

**These won't crash the app** - all wrapped in try/except with fallback messages.

---

## Troubleshooting

### App Won't Start

```bash
# Check Python
python --version  # Need 3.10+

# Install dependencies
pip install -r trading_app/requirements.txt

# Check database
ls gold.db  # Must exist in project root

# Run manually
cd trading_app
streamlit run app_mobile.py
```

### Can't Access from Phone

1. Check both devices on same Wi-Fi
2. Check PC firewall allows port 8501
3. Find IP: `ipconfig` → IPv4 Address
4. On phone: `http://YOUR_IP:8501`

### ML Not Working

1. Check model files exist: `ml_models/registry/directional_v1/latest/`
2. Check logs: `tail -f trading_app/trading_app.log | grep ML`
3. Verify LightGBM installed: `pip show lightgbm`

### AI Chat Not Working

1. Check `.env` has `ANTHROPIC_API_KEY=sk-ant-...`
2. Verify key valid: https://console.anthropic.com/
3. Check error message in app

### No Data Loading

1. Click "Initialize/Refresh Data" in sidebar
2. Check `gold.db` exists: `python check_db.py`
3. Verify data recent: `python query_features.py`

---

## Workflow Examples

### Morning Preparation

```
08:00 - Open app
08:02 - Check Dashboard → ATR + next ORB + safety status
08:05 - Review ML insights (if preparing)
08:10 - Check Setup Scanner → upcoming opportunities
08:15 - Swipe to Chart → expand → review levels
```

### During Trading (11:00 ORB)

```
10:55 - Dashboard shows "PREPARE" + countdown
11:00 - ORB window opens (watch chart)
11:05 - ORB formed → Swipe to Trade → Calculate levels
11:06 - Check ML insights → 68% confidence UP
11:07 - Check Safety Status → ✅ SAFE
11:08 - Enter trade → Swipe to Positions → Monitor P&L
11:30 - Check progress bar → 40% to target
12:00 - Target hit → Close position
```

### Post-Trade Review

```
- Swipe to AI Chat
- Ask: "Why did that 1100 ORB work?"
- AI explains: Session context + ML reasoning
- Log insights for next time
```

---

## Comparison: Desktop vs Mobile

| Feature | Desktop (`app_trading_hub.py`) | Mobile (`app_mobile.py`) |
|---------|-------------------------------|--------------------------|
| Layout | Wide, multi-column sidebar | Card-based, swipeable |
| Navigation | Scroll + tabs | Swipe gestures + dots |
| Chart | Always visible (600px) | Collapsible (350px) |
| ML Display | Separate expander section | Integrated in Dashboard |
| Touch Targets | 32px | 48px |
| Font Sizes | 14-28px | 16-48px |
| Safety Checks | Separate sections | Combined indicator |
| Use Case | Deep analysis, backtesting | Quick glance, trade entry |

---

## Security & Safety

### Financial Safety

- **No automatic execution**: Decision support only
- **Risk limits enforced**: Daily/weekly loss limits
- **Position sizing validation**: Max contracts check
- **ML shadow mode**: Predictions don't override rules

### Data Security

- **API keys in .env**: Not committed to git
- **Local database**: No cloud exposure
- **HTTPS optional**: For remote access

### Error Handling

- All integrations wrapped in try/except
- Graceful degradation on failures
- Fallback messages for unavailable features
- No crashes from missing data

---

## Maintenance

### Check Logs

```bash
# View recent logs
tail -f trading_app/trading_app.log

# Check for errors
tail -50 trading_app/trading_app.log | grep ERROR

# ML-specific logs
tail -f trading_app/trading_app.log | grep "ML"
```

### Update Data

```bash
# Daily update (run once per morning)
python daily_update.py

# Rebuild features
python build_daily_features_v2.py 2026-01-17
```

### Restart App

```bash
# Kill existing process
pkill -f "streamlit run app_mobile.py"

# Restart
START_MOBILE_APP.bat
```

---

## Documentation

**Mobile App**:
- `MOBILE_APP_README.md` (this file) - Complete guide
- `FINAL_STATUS_REPORT.md` - Integration completion report
- `DEBUGGING_COMPLETE.md` - Bug fixes applied
- `APP_STATUS_VERIFIED.md` - Verification checklist

**ML System**:
- `ML_USER_GUIDE.md` - ML features guide
- `ML_FINAL_SUMMARY.md` - ML completion summary
- `README_ML.md` - ML technical details

**Desktop App**:
- `trading_app/README.md` - Desktop app guide

**Project**:
- `README.md` - Data pipeline + analysis tools
- `CLAUDE.md` - Developer instructions
- `PROJECT_STRUCTURE.md` - File organization

---

## Support

### Get Help

```bash
# Run diagnostics
python check_db.py
python validate_data.py

# Test app sync
python test_app_sync.py

# Check ML models
ls -R ml_models/registry/
```

### Report Issues

Include:
1. Error message from logs
2. Steps to reproduce
3. Screenshot of card showing issue
4. Output of `python check_db.py`

---

## Credits

**Built**: Jan 15-17, 2026
**Architecture**: Tinder-style swipeable cards
**ML Model**: LightGBM trained on 740 days MGC data
**AI Assistant**: Claude Sonnet 3.5
**Framework**: Streamlit + Plotly
**Database**: DuckDB

**Key Features**:
- Mobile-first design
- ML-enhanced predictions
- Comprehensive safety checks
- Real-time market intelligence
- Professional charting
- Position tracking
- AI assistant

---

## What's Next

1. **Start using**: Launch app with `START_MOBILE_APP.bat`
2. **Test features**: Swipe through all 5 cards
3. **Monitor trades**: Use Positions card for P&L
4. **Ask AI**: Use Chat card for strategy questions
5. **Review logs**: Check `trading_app.log` for insights

---

**Status**: 🟢 FULLY OPERATIONAL
**App URL**: http://localhost:8501
**Version**: 2.1 (with ML + Intelligence + Safety)
**Production-Ready**: ✅ Yes

**Disclaimer**: Past performance does not guarantee future results. ML predictions are probabilistic. This is a decision support tool, not financial advice. Trade at your own risk.
