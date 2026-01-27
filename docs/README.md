# MGC (Micro Gold) Trading System

**Complete ORB-based trading system with AI query interface, backtesting, journaling, and analysis tools.**

740 days of historical data (2024-2026) | 716,540+ bars analyzed | Production-ready

---

## 🤖 AI Handover Context (Updated: 2026-01-19)

**System Status:** ✅ Fully audited, synchronized, and production-ready

### Recent Session Changes (Jan 19, 2026)

**1. Mobile UI Fixes**
- Fixed `datetime` scoping issue in `trading_app/mobile_ui.py`
- Fixed HTML rendering in strategy recommendations (separated into multiple st.markdown() calls)
- Added clear action status for all ORBs: ⏰ UPCOMING, ⏳ FORMING NOW, ⏳ WAIT FOR BREAKOUT, 🚀 READY TO TRADE LONG, 🔻 READY TO TRADE SHORT, ✅ TRADE IN PROGRESS
- All ORBs now show complete trade details: Entry, Stop (with logic), Target (with RR), Risk/Reward in points

**2. Gap Research Completed & Archived**
- Analyzed 526 gaps (2024-2026) for continuation vs fill behavior
- **KEY FINDING:** 94.6% of gaps eventually fill (return to prev_close), but many run away FIRST before filling
- **Gap Fade Strategy:** Trade ONLY gaps <1.0 ticks immediately → 74% win rate (228/308 trades)
- **Gap Continuation Strategy:** Also viable → +0.52R expectancy, 25.3% win rate with 5R targets
- **CRITICAL:** "Eventual fill" ≠ "immediate fill" - gaps can run 20-400+ ticks away before filling
- All research consolidated to `GAP_RESEARCH_COMPLETE.md`, experiments archived to `_archive/gap_research_jan2026/`

**3. Files Added/Modified**
- **Modified:** `trading_app/mobile_ui.py` (HTML rendering fix + action status clarity)
- **Added:** `GAP_RESEARCH_COMPLETE.md` (consolidated gap research guide)
- **Archived:** 22 gap research files → `_archive/gap_research_jan2026/`

### Critical Files & Their Purpose

**Data Pipeline:**
- `gold.db` - Main DuckDB database (bars_1m, bars_5m, daily_features, validated_setups)
- `backfill_databento_continuous.py` - Primary data source (Databento GLBX.MDP3)
- `build_daily_features_v2.py` - Zero-lookahead feature builder (PRODUCTION)

**Trading Apps:**
- `trading_app/app_mobile.py` - Mobile Streamlit app (Streamlit Cloud deployment)
- `streamlit_app.py` - Entry point for Streamlit Cloud
- `trading_app/config.py` - MUST stay synchronized with validated_setups table

**Validation:**
- `test_app_sync.py` - **RUN AFTER ANY validated_setups OR config.py CHANGES**
- `audit_master.py` - 38-test audit system (100% pass rate as of Jan 17)

**Strategy Source of Truth:**
- `validated_setups` table in gold.db (19 setups: 8 MGC, 5 NQ, 6 MPL)
- `trading_app/config.py` - Python representation (must match database)
- `populate_validated_setups.py` - Rebuild validated_setups from scratch

### Synchronization Status

✅ **Database ↔ Config:** Synchronized (test_app_sync.py passes)
✅ **Audit System:** 38/38 tests passing
✅ **ORB Windows:** All extended to 09:00 next day (scan window bug fixed Jan 16)
✅ **Mobile App:** Deployed to Streamlit Cloud, clear action statuses working

### Known Issues & Warnings

⚠️ **Gap Analysis Caveat:** 94.6% fill rate measures "eventual fill within 24 hours", NOT "immediate fill before stop-out". For trading, only <1.0 tick gaps have 74% immediate fill rate.

⚠️ **Never Update validated_setups Without Updating config.py:** This will cause apps to use wrong RR/filters. ALWAYS run `test_app_sync.py` after changes.

⚠️ **Session Tracking:** System tracks Asia/London/NY sessions with deterministic type codes (sweep/expansion/consolidation) in daily_features_v2. No advanced session tracking beyond this currently exists.

### Project Structure Compliance

- Root directory: Production code only (29 Python files, clean)
- `_archive/`: All experiments, old versions, research
- Gap research: Properly archived (Jan 19)
- No duplicates, one canonical source per file

### Next Session Priorities

1. Check Streamlit Cloud deployment status (datetime fix + HTML rendering fix)
2. Review GAP_RESEARCH_COMPLETE.md if gap trading interests you
3. Run `python test_app_sync.py` to verify sync still passes
4. If adding new strategies, update validated_setups + config.py + run test

---

## Quick Start

### 1. Daily Morning Routine

```bash
# Update data and get today's setup alerts (one command does everything)
python daily_update.py
```

That's it! This automatically:
- Fetches latest MGC data from Databento
- Rebuilds features and ORBs
- Shows you high-probability setups for today

### 2. Ask Questions (AI Query Interface)

```bash
# Natural language queries
python ai_query.py "What was the win rate for 1100 UP?"
python ai_query.py "Show me the best performing ORBs"
python ai_query.py "Compare 1100 vs 0900"

# Interactive mode
python ai_query.py -i
```

### 3. Log Your Trades

```bash
python journal.py add          # Log a new trade (interactive)
python journal.py stats         # View your performance
python journal.py compare       # Compare vs historical
```

### Run Dashboard A (Edge Research)

```bash
# Install dashboard dependencies
pip install -r requirements.txt

# Launch Streamlit dashboard (reads gold.db and v_orb_trades)
streamlit run app_edge_research.py

# Quick DB connectivity test (PowerShell/cmd safe)
python -c "import duckdb; con=duckdb.connect('gold.db'); print(con.execute('SELECT COUNT(*) FROM v_orb_trades').fetchone())"
```

Use the left sidebar to filter by date, ORB time, break direction, outcomes (WIN/LOSS/NO_TRADE), session type codes, and optional ATR/Asia range bounds. Charts and tables update instantly; download the drilldown table for CSV analysis.

---

## System Overview

### What This System Does

1. **Data Pipeline**: Fetches and stores continuous Micro Gold futures data
2. **Feature Engineering**: Calculates ORBs, session stats, indicators
3. **Analysis Tools**: Backtesting, filtering, performance analytics
4. **AI Interface**: Ask questions in natural language
5. **Trading Journal**: Track real trades, compare to historical
6. **Visualizations**: Charts, equity curves, heatmaps
7. **Alerts**: Daily high-probability setup recommendations

### Zero-Lookahead (Current Objective)
- **V2 is the trusted dataset**: `build_daily_features_v2.py` builds zero-lookahead features; `analyze_orb_v2.py` and `realtime_signals.py` consume them.
- **Automation**: `daily_update.py` → `backfill_databento_continuous.py` now builds **both** `daily_features` (legacy) and `daily_features_v2` (preferred). Always favor V2 outputs for decisions.
- **Legacy data caution**: V1 (`daily_features`, session types) is retained for comparison only and contains lookahead bias. Do not base live rules on V1 session labels.
- **Execution backtest**: `backtest_orb_exec_1m.py` uses `daily_features_v2` levels and 1m closes for realistic entries/exits.
- **Deterministic session codes**: `daily_features_v2` stores `asia_type_code`, `london_type_code`, and `pre_ny_type_code` (sweep/expansion/consolidation) computed strictly from each session’s own highs/lows and ATR — no subjective trend or lookahead.

### Data Coverage

- **Date Range**: 2024-01-02 to 2026-01-10
- **Bars**: 716,540 (1-minute) + 143,648 (5-minute)
- **ORBs Tracked**: 09:00, 10:00, 11:00, 18:00, 23:00, 00:30
- **Sessions**: Asia, London, NY with type classification
- **Storage**: Local DuckDB (no cloud dependencies)

---

## Complete Tool Reference

### Data Management

```bash
# Daily update (run every morning)
python daily_update.py
python daily_update.py --dry-run         # Preview without changes
python daily_update.py --days 7          # Catch up last 7 days

# Manual backfill (if needed)
python backfill_databento_continuous.py 2024-01-01 2026-01-10

# Rebuild features for specific date
python build_daily_features.py 2026-01-10

# Wipe all MGC data (fresh start)
python wipe_mgc.py

# Database health check
python check_db.py
python validate_data.py                 # Comprehensive validation
python validate_data.py --report         # Save JSON report

# System audit (run after major changes)
python audit_master.py                  # Complete 38-test audit (100% pass rate)
python audit_master.py --quick          # Quick validation check
python test_app_sync.py                 # Verify app synchronization
```

### Analysis & Research

```bash
# AI query interface (natural language)
python ai_query.py "What was the win rate for 1100 UP?"
python ai_query.py "Show me the best ORBs"
python ai_query.py -i                    # Interactive mode

# Performance analysis
python analyze_orb_performance.py        # Full analysis report

# Filter setups
python filter_orb_setups.py --orb 1100 --direction UP
python filter_orb_setups.py --orb 1800 --london_type CONSOLIDATION --outcome WIN
python filter_orb_setups.py --orb 0030 --ny_type EXPANSION --last_days 30

# Query recent data
python query_features.py                 # Last 20 days
```

### Backtesting

```bash
# Test strategies
python backtest.py --orb 1100 --direction UP
python backtest.py --orb 1800 --london_type CONSOLIDATION
python backtest.py --orb 2300 --ny_type EXPANSION

# Compare strategies
python backtest.py --orb 1100 --direction UP --compare 1800 UP 0900 UP

# Export results
python backtest.py --orb 1100 --direction UP --export results_1100_up.csv

# Date range backtest
python backtest.py --orb 1100 --start 2024-01-01 --end 2025-12-31
```

### Trading Journal

```bash
# Add trades
python journal.py add                    # Interactive entry

# View journal
python journal.py list                   # All trades
python journal.py list --last 30         # Last 30 days

# Performance stats
python journal.py stats                  # Your statistics
python journal.py compare                # Compare vs historical

# Export
python journal.py export                 # Export to CSV
```

### Daily Alerts

```bash
# Today's setup recommendations
python daily_alerts.py                   # Today
python daily_alerts.py 2026-01-09       # Specific date
```

### Export & Visualization

```bash
# Export to CSV
python export_csv.py daily_features              # All features
python export_csv.py daily_features --days 30    # Last 30 days
python export_csv.py orb_performance             # Setup performance
python export_csv.py session_stats               # Session analysis
python export_csv.py bars_1m 2026-01-09         # 1-min bars for date
python export_csv.py bars_5m 2026-01-09         # 5-min bars for date

# Visualizations (requires matplotlib)
python visualize.py --all                # All charts
python visualize.py --equity             # Equity curves
python visualize.py --win_rates          # Win rate bar chart
python visualize.py --text               # Text-based (no matplotlib)
```

---

## Key Findings (740 Days Analyzed)

### Best Setups (TRADE THESE)

1. **11:00 UP** - 57.9% WR, +0.16 R avg (247 trades)
   - Best during EXPANDED Asia sessions
   - Primary trading opportunity

2. **18:00 UP** - 56.9% WR, +0.14 R avg (262 trades)
   - Strong across all London sessions
   - After CONSOLIDATION: 58.8% WR with DOWN breakouts

3. **23:00 during NY EXPANSION** - 52.0% WR, +0.04 R avg

### Worst Setups (AVOID)

1. **09:00 ORBs** - 45.2% WR, -0.10 R avg
2. **00:30 ORBs** - 46.8% WR, -0.06 R avg (except NY EXPANSION)
3. **ANY ORB during NY CONSOLIDATION** - 31-37% WR ❌

### Session Insights

- **Asia EXPANDED** (most common): 11:00 UP works best
- **London CONSOLIDATION**: 18:00 DOWN has strong edge
- **London SWEEP_HIGH**: AVOID 23:00 ORB (42.5% WR)
- **NY EXPANSION**: Best time for late NY ORBs

---

## System Audit & Validation

### Complete Audit Framework (38 Tests)

Comprehensive audit system validates all aspects of the trading system:

```bash
# Run complete audit (all 38 tests)
python audit_master.py

# Quick validation check
python audit_master.py --quick

# Run specific step
python audit_master.py --step 1     # Data integrity
python audit_master.py --step 2     # Feature verification
python audit_master.py --step 3     # Strategy validation

# Verify app synchronization (CRITICAL)
python test_app_sync.py
```

**Audit Coverage:**
- **Step 1: Data Integrity** (12 tests) - Validates raw data, ORBs, sessions
- **Step 1.5: Gap & Transition** (5 tests) - Weekend/holiday behavior
- **Step 2: Feature Verification** (11 tests) - Deterministic calculations
- **Step 2.4: Time-Safety** (5 tests) - Zero-lookahead enforcement
- **Step 3: Strategy Validation** (5 tests) - Strategy correctness

**Current Status**: 38/38 tests passed (100%)

All reports saved to `audit_reports/` directory. See `MASTER_AUDIT_PLAN.md` for details.

---

## File Structure

```
myprojectx/
├── gold.db                          # Main database (DuckDB)
├── trades.db                        # Trading journal (SQLite)
├── CLAUDE.md                        # Project instructions
├── TRADING_PLAYBOOK.md              # Trading strategy guide
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
│
├── Data Pipeline
│   ├── backfill_databento_continuous.py  # Main backfill script
│   ├── build_daily_features.py           # Feature engineering
│   ├── build_5m.py                       # 5-min aggregation
│   ├── daily_update.py                   # One-command daily update
│   └── init_db.py                        # Initialize database
│
├── Analysis Tools
│   ├── ai_query.py                       # AI query interface ⭐
│   ├── analyze_orb_performance.py        # Full performance report
│   ├── filter_orb_setups.py              # Find specific setups
│   ├── query_features.py                 # Quick data check
│   ├── daily_alerts.py                   # Daily setup alerts ⭐
│   └── validate_data.py                  # Data quality checks
│
├── Trading Tools
│   ├── backtest.py                       # Backtest strategies ⭐
│   ├── journal.py                        # Trading journal ⭐
│   ├── export_csv.py                     # Export to CSV
│   └── visualize.py                      # Charts & graphs
│
├── Database Utilities
│   ├── check_db.py                       # Quick DB check
│   ├── wipe_mgc.py                       # Wipe all data
│   └── dump_contracts.py                 # List contracts
│
├── Audit System
│   ├── audit_master.py                   # Main audit runner ⭐
│   ├── audits/step1_data_integrity.py    # Data integrity tests
│   ├── audits/step1a_gaps_transitions.py # Gap/transition tests
│   ├── audits/step2_feature_verification.py # Feature tests
│   ├── audits/step2a_time_assertions.py  # Time-safety tests
│   ├── audits/step3_strategy_validation.py # Strategy tests
│   ├── audits/attack_harness.py          # Attack testing framework
│   ├── test_app_sync.py                  # App sync verification ⭐
│   ├── MASTER_AUDIT_PLAN.md              # Audit specification
│   ├── AUDIT_STATUS_JAN17.md             # Latest status report
│   └── audit_reports/                    # JSON/CSV reports
│
└── charts/                          # Generated visualizations
    ├── win_rates.png
    ├── equity_curve.png
    └── ...
```

---

## Installation

### Requirements

- Python 3.10+
- Windows / macOS / Linux
- Databento API key (for data updates)

### Setup

1. **Clone or download this project**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file** (copy from example or create new):
   ```bash
   DATABENTO_API_KEY=your_key_here
   DATABENTO_DATASET=GLBX.MDP3
   DATABENTO_SCHEMA=ohlcv-1m
   DATABENTO_SYMBOLS=MGC.FUT
   DUCKDB_PATH=gold.db
   SYMBOL=MGC
   TZ_LOCAL=Australia/Brisbane
   ```

4. **Initialize database** (if starting fresh):
   ```bash
   python init_db.py
   ```

5. **Backfill data**:
   ```bash
   python backfill_databento_continuous.py 2024-01-01 2026-01-10
   ```

6. **Verify setup**:
   ```bash
   python check_db.py
   python validate_data.py
   ```

---

## Advanced Usage

### AI Query Examples

The AI interface understands natural language:

```bash
# Win rates
python ai_query.py "What's the win rate for 1100 UP?"
python ai_query.py "How does 1800 perform?"

# Comparisons
python ai_query.py "Compare 1100 vs 0900"
python ai_query.py "Which is better: 1800 UP or 2300 UP?"

# Recent performance
python ai_query.py "How did I do in the last 30 days?"
python ai_query.py "Show recent performance"

# Specific dates
python ai_query.py "What happened on 2026-01-09?"

# Session queries
python ai_query.py "How many EXPANDED Asia days?"
python ai_query.py "Best ORBs during London CONSOLIDATION?"

# Journal
python ai_query.py "Show my trading stats"
python ai_query.py "How am I performing?"
```

### Advanced Backtesting

```bash
# Multi-filter backtest
python backtest.py --orb 1800 \
  --direction DOWN \
  --london_type CONSOLIDATION \
  --min_asia_range 300

# Strategy comparison
python backtest.py --orb 1100 --direction UP \
  --compare 1800 UP 1100 DOWN

# Export for Excel analysis
python backtest.py --orb 1100 --direction UP \
  --export my_strategy.csv
```

### Complex Filtering

```bash
# Find tight ORBs that won
python filter_orb_setups.py \
  --orb 1000 \
  --outcome WIN \
  --max_orb_size 50

# Find large Asia days
python filter_orb_setups.py \
  --min_asia_range 500 \
  --orb 1100 \
  --direction UP

# Recent winners only
python filter_orb_setups.py \
  --orb 1800 \
  --outcome WIN \
  --last_days 60
```

---

## Workflow Examples

### Morning Preparation (08:00-08:30 Brisbane)

```bash
# 1. Update everything
python daily_update.py

# 2. Review alerts (auto-runs in daily_update)
# Alerts show high-probability setups for today

# 3. Check recent performance (optional)
python ai_query.py "Show recent performance"
```

### During Trading Day

1. **11:00 ORB** - Primary opportunity (wait for this)
2. **18:00 ORB** - Secondary opportunity
3. **23:00/00:30** - Only if session conditions align

### End of Day

```bash
# 1. Log your trades
python journal.py add

# 2. Review performance
python journal.py stats

# 3. Compare to historical
python journal.py compare
```

### Weekly Review

```bash
# Performance analysis
python analyze_orb_performance.py

# Export for deeper analysis
python export_csv.py daily_features --days 7

# Check journal stats
python journal.py stats
```

---

## FAQ

**Q: How often should I run daily_update.py?**
A: Once per morning (08:00-08:30 Brisbane time) before Asia session.

**Q: Do I need matplotlib?**
A: No. Visualization tools have text-based fallbacks. Install matplotlib for charts.

**Q: Can I backtest custom strategies?**
A: Yes! Use `backtest.py` with filters or write custom queries in `ai_query.py`.

**Q: How do I add my real trades?**
A: Use `python journal.py add` for interactive entry. It auto-fetches session context.

**Q: What if I miss a day of updates?**
A: Run `python daily_update.py --days 7` to catch up.

**Q: Can I export to Excel?**
A: Yes! Use `export_csv.py` for any table or analysis result.

**Q: How do I query specific conditions?**
A: Use `ai_query.py` for natural language or `filter_orb_setups.py` for precise filtering.

**Q: Is the database safe to backup?**
A: Yes. Just copy `gold.db` and `trades.db`. They're portable SQLite/DuckDB files.

**Q: Can I run this on a schedule?**
A: Yes. Use Windows Task Scheduler or cron to run `daily_update.py` daily.

---

## Support & Troubleshooting

**Data validation issues:**
```bash
python validate_data.py --report
```

**Database corruption:**
```bash
python wipe_mgc.py
python backfill_databento_continuous.py 2024-01-01 2026-01-10
```

**Missing data gaps:**
```bash
python daily_update.py --days 30
```

**Check system health:**
```bash
python check_db.py
python validate_data.py
```

---

## Performance Notes

- **Database size**: ~100-200 MB for 2 years of data
- **Query speed**: Sub-second for most queries
- **Backfill speed**: ~5-10 seconds per day
- **Update time**: ~30 seconds for daily update

---

## What's Next?

1. **Start trading**: Use TRADING_PLAYBOOK.md for strategies
2. **Build your journal**: Log trades with `journal.py`
3. **Experiment**: Try different filters and setups
4. **Automate**: Schedule `daily_update.py` to run automatically
5. **Visualize**: Install matplotlib for charts

---

## Credits

**Built for**: Discretionary MGC ORB trading
**Data Source**: Databento (GLBX.MDP3)
**Database**: DuckDB + SQLite
**AI Interface**: Pattern-based natural language processing
**Last Updated**: 2026-01-11

---

**Disclaimer**: Past performance does not guarantee future results. This is a research and analysis tool. Use at your own risk.
