# 🔬 START HERE

## Your Primary Tool: RESEARCH LAB

The **RESEARCH LAB** is your main workspace. This is where you:
- Discover profitable trading strategies automatically
- Run comprehensive backtests on historical data
- Validate strategies with robustness checks
- Manage candidates through the approval workflow
- Promote proven winners to production

**This is THE tool for systematic edge discovery.**

---

## 🚀 Quick Launch

### Open Research Lab (Primary)
```
Double-click: START_HERE.bat
```
Or:
```
http://localhost:8503
```

---

## 📱 Both Apps

### 1. Research Lab (PRIMARY) - Port 8503
**Purpose:** Strategy discovery, backtesting, research

**Launch:**
- `START_HERE.bat` (recommended)
- `start_research.bat`
- `OPEN_RESEARCH.html`
- http://localhost:8503

**Use this for:**
- Finding new profitable setups
- Running backtests
- Validating strategies
- Managing research pipeline
- Promoting to production

### 2. Trading Terminal (SECONDARY) - Port 8502
**Purpose:** Live signal monitoring, position tracking

**Launch:**
- `start_terminal.bat`
- `OPEN_TERMINAL.html`
- http://localhost:8502

**Use this for:**
- Monitoring live signals (optional)
- Tracking active positions (optional)
- Viewing charts (optional)
- AI assistant (optional)

---

## 🎯 Recommended Workflow

### Step 1: Research (Primary Tool)
Use **Research Lab** to:
1. Run discovery scans
2. Test strategy configurations
3. Review backtest results
4. Approve profitable setups
5. Promote to production

### Step 2: Monitor (Secondary Tool - Optional)
Use **Trading Terminal** to:
1. Watch for live signals from approved strategies
2. Track active positions
3. Monitor P&L
4. Get AI insights

**But the real work happens in the Research Lab.**

---

## 📊 Tool Comparison

| Feature | Research Lab (Primary) | Terminal (Secondary) |
|---------|------------------------|----------------------|
| **Strategy Discovery** | ✅ Main Feature | ❌ |
| **Backtesting** | ✅ Full Engine | ❌ |
| **Pipeline Management** | ✅ Complete Workflow | ❌ |
| **Production Promotion** | ✅ Yes | ❌ |
| **Live Signals** | ❌ | ✅ (from promoted setups) |
| **Position Tracking** | ❌ | ✅ Optional |
| **Charts** | ✅ Analysis Mode | ✅ Live Mode |
| **AI Assistant** | ❌ | ✅ Optional |

**Summary:** Research Lab does the heavy lifting. Terminal is just for monitoring.

---

## 🔬 Research Lab Features

### DISCOVERY Mode
- Automatic strategy scanning
- Tests hundreds of configurations
- Ranks by profitability
- Creates candidates automatically

### PIPELINE Mode
- Manage candidates: Draft → Tested → Approved → Promoted
- Run backtests
- Review metrics
- Approve/reject strategies

### BACKTESTER Mode
- Custom backtest runner
- Full parameter control
- Instant results
- Comprehensive metrics

### PRODUCTION Mode
- View all live strategies
- Performance tracking
- Configuration details

---

## 📖 Full Documentation

### Research Lab Guide (Read This First!)
**File:** `RESEARCH_LAB_GUIDE.md`

Everything you need to know:
- How to run discovery scans
- Understanding metrics
- Pipeline workflow
- Backtest best practices
- Production promotion

### Trading Terminal Guide (Optional)
**File:** `TERMINAL_COMPLETE.md`

If you want to use the monitoring terminal:
- 4 view modes
- Status indicators
- Position tracking
- AI integration

### Database Schema
**File:** `docs/DATABASE_SCHEMA_SOURCE_OF_TRUTH.md`

Technical details:
- Table structures
- Data flow
- ORB calculations

### Trading Rules
**File:** `docs/TRADING_PLAYBOOK.md`

Strategy fundamentals:
- ORB concepts
- Entry/exit rules
- Risk management

---

## ⚡ First Time Setup

### 1. Ensure Database is Ready
```bash
# Check database exists
python pipeline/check_db.py
```

If empty, backfill data:
```bash
python pipeline/backfill_databento_continuous.py 2021-01-01 2024-12-31
```

### 2. Launch Research Lab
```
START_HERE.bat
```

### 3. Start Discovering Edges
1. Go to DISCOVERY mode
2. Select instrument (MGC recommended for first run)
3. Select ORB times (try 0900, 1000, 1100)
4. Set minimum criteria (50% WR, 1.0 Avg R)
5. Click "START DISCOVERY SCAN"
6. Review results
7. Add top performers to pipeline

### 4. Validate & Promote
1. Go to PIPELINE mode
2. Run backtests on DRAFT candidates
3. Review TESTED results
4. Approve profitable ones
5. Promote to PRODUCTION

### 5. (Optional) Monitor Live
1. Launch Trading Terminal: `start_terminal.bat`
2. Initialize data connection
3. Watch for signals from promoted strategies

---

## 🎓 Learning Path

### Week 1: Discovery Basics
- Run your first discovery scan
- Understand the metrics (Win Rate, Avg R, Total R)
- Add candidates to pipeline
- Run backtests

### Week 2: Pipeline Management
- Review tested candidates
- Approve promising strategies
- Promote to production
- Understand the workflow

### Week 3: Advanced Discovery
- Test complex filter combinations
- Optimize R:R ratios
- Run regime split analysis
- Build strategy portfolio

### Week 4: Production Management
- Monitor live strategies
- Retire underperformers
- Discover replacement edges
- Maintain strategy pipeline

---

## 🆘 Troubleshooting

### Research Lab won't start
```bash
# Try manual start
streamlit run trading_app\app_research_lab.py --server.port=8503
```

### No data in database
```bash
# Backfill historical data
python pipeline/backfill_databento_continuous.py 2021-01-01 2024-12-31
```

### Discovery scan finds nothing
- Relax criteria (lower min WR, lower min Avg R)
- Try different instruments
- Check database has sufficient data

### Can't promote to production
- Ensure status is APPROVED
- Check candidate not already promoted
- Verify validated_setups table exists

---

## ✅ You're Ready!

**Your primary tool:** Research Lab (Port 8503)
**Your secondary tool:** Trading Terminal (Port 8502) - optional

**Focus on the Research Lab.** That's where you discover edges, validate strategies, and build your trading system.

The terminal is just for monitoring if you want it.

---

## 🔗 Quick Links

**Launch Research Lab:**
- START_HERE.bat
- http://localhost:8503

**Documentation:**
- RESEARCH_LAB_GUIDE.md (Read this!)
- TERMINAL_COMPLETE.md (Optional)
- docs/TRADING_PLAYBOOK.md

**Database Tools:**
- pipeline/check_db.py
- pipeline/backfill_databento_continuous.py
- pipeline/build_daily_features.py

---

**Ready to discover profitable edges? Launch the Research Lab and start scanning.** 🔬
