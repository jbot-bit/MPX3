# 🔬 RESEARCH LAB - Complete Guide

## What Is This?

The RESEARCH LAB is your **primary tool** for:
- **Discovering** profitable trading strategies automatically
- **Backtesting** any strategy configuration on historical data
- **Managing** candidates through the validation workflow
- **Promoting** proven winners to production

This is where the real edge discovery happens. Not just signal generation - actual systematic strategy research.

---

## 🚀 Quick Start

### Open the Research Lab

**Option 1: Auto-redirect (Easiest)**
```
Double-click: OPEN_RESEARCH.html
```

**Option 2: Batch file**
```bash
start_research.bat
```

**Option 3: Direct URL**
```
http://localhost:8503
```

---

## 🎯 Four Research Modes

### 1. DISCOVERY Mode

**Purpose:** Automatically scan for profitable strategy configurations

**What it does:**
- Tests hundreds of ORB strategy variations systematically
- Tries different instruments (MGC, NQ, MPL)
- Tests all ORB times (0900, 1000, 1100, 1800, 2300, 0030)
- Optimizes filter combinations (ORB size, ATR, RSI, session travel)
- Tests different R:R ratios (1:1 through 1:20)
- Ranks results by profitability

**How to use:**
1. Select instrument (or scan all)
2. Choose ORB times to test
3. Set minimum criteria (win rate, avg R, max drawdown)
4. Enable filter tests (ORB size, ATR, session travel, etc.)
5. Click "START DISCOVERY SCAN"
6. Wait for results (may take several minutes)
7. Review top performers
8. Add selected strategies to pipeline

**Output:**
- Sorted list of all profitable configurations
- Metrics: Win Rate, Avg R, Total R, Trades, Drawdown, Sharpe
- Auto-creates candidates for selected strategies

---

### 2. PIPELINE Mode

**Purpose:** Manage candidates through the validation workflow

**Workflow:**
```
DRAFT → TESTED → PENDING → APPROVED → PROMOTED
```

**Status Definitions:**
- **DRAFT**: New candidate, needs backtest
- **TESTED**: Backtest complete, awaiting review
- **PENDING**: Under human review
- **APPROVED**: Validated, ready for production
- **REJECTED**: Failed validation
- **PROMOTED**: Live in validated_setups table

**How to use:**
1. View candidates by status/instrument
2. Run backtests on DRAFT candidates
3. Review TESTED candidates' metrics
4. Approve or reject PENDING candidates
5. Promote APPROVED candidates to production

**Actions per status:**
- DRAFT → Click "RUN BACKTEST"
- TESTED → Click "REVIEW" to move to PENDING
- PENDING → Click "APPROVE" or "REJECT"
- APPROVED → Click "PROMOTE TO PRODUCTION"

---

### 3. BACKTESTER Mode

**Purpose:** Run custom backtests with full control

**What it does:**
- Test any strategy configuration on historical data
- Full control over all parameters
- Comprehensive metrics output
- Instant results

**Configuration:**
- **Instrument**: MGC, NQ, or MPL
- **ORB Time**: 0900-0030
- **R:R Target**: 1.0 to 20.0
- **Entry Filters**:
  - Min/Max ORB Size
  - Min/Max ATR
- **Advanced Options**:
  - Half Stop Loss (50% of ORB)
  - Extended Profit Window (24h)
- **Test Window**: Any date range

**Results:**
- Win Rate
- Average R per trade
- Total R (cumulative profit)
- Number of trades
- Maximum Drawdown
- Sharpe Ratio
- Profit Factor
- MAE/MFE (Max Adverse/Favorable Excursion)

**Verdict:**
- ✅ PROFITABLE EDGE DETECTED (if Total R > 0)
- ❌ NO EDGE DETECTED (if Total R ≤ 0)

---

### 4. PRODUCTION Mode

**Purpose:** View all strategies live in production

**What it shows:**
- All entries in `validated_setups` table
- Grouped by instrument (MGC, NQ, MPL)
- Full configuration for each setup
- Performance metrics
- Promotion timestamps

**Information per setup:**
- ID (used by trading apps)
- ORB Time
- Break Direction (UP/DOWN/BOTH)
- R:R Target
- Stop Loss Mode
- ORB Size Filter (if any)
- Win Rate
- Avg R
- Total R
- Number of trades
- Max Drawdown
- Promotion date

---

## 📊 Understanding the Metrics

### Win Rate
- Percentage of profitable trades
- **Good**: > 50%
- **Excellent**: > 60%

### Average R
- Average profit per trade in R multiples
- **Good**: > 1.0R
- **Excellent**: > 1.5R

### Total R
- Cumulative profit across all trades
- **Profitable**: > 0R
- **Strong Edge**: > 20R

### Max Drawdown
- Largest losing streak in R
- **Acceptable**: < 5R
- **Concerning**: > 10R

### Sharpe Ratio
- Risk-adjusted returns
- **Good**: > 0.5
- **Excellent**: > 1.0

### Profit Factor
- Ratio of gross profit to gross loss
- **Profitable**: > 1.0
- **Strong**: > 1.5

### MAE (Max Adverse Excursion)
- Average worst drawdown during trades
- Lower is better

### MFE (Max Favorable Excursion)
- Average best profit during trades
- Higher is better

---

## 🔬 Discovery Scan Tips

### Start Broad, Then Narrow
1. **First scan**: Test all ORB times, basic filters only
2. **Review results**: Identify which times/instruments work
3. **Second scan**: Focus on winners, add more filters
4. **Optimize**: Fine-tune successful configurations

### Filter Combinations to Test

**Essential:**
- ORB Size Filters (eliminates too-small/too-large setups)
- Session Travel (prior movement filter)
- R:R Ratios (find optimal targets)

**Advanced:**
- ATR Filters (volatility-based entry)
- RSI Filters (momentum confirmation)
- Extended Windows (longer profit targets)

### Criteria Guidelines

**Conservative (fewer candidates, higher quality):**
- Min Win Rate: 55%
- Min Avg R: 1.2
- Max Drawdown: 3R
- Min Sharpe: 1.0

**Aggressive (more candidates, cast wide net):**
- Min Win Rate: 45%
- Min Avg R: 0.8
- Max Drawdown: 7R
- Min Sharpe: 0.3

---

## 🎯 Backtest Best Practices

### Test Window Selection

**Short-term validation (3-6 months):**
- Quick feedback
- Recent market conditions
- Good for initial screening

**Medium-term validation (1-2 years):**
- More robust
- Multiple market regimes
- Recommended for approval

**Long-term validation (3+ years):**
- Maximum confidence
- All market conditions
- Required for high-stakes strategies

### What Makes a Good Strategy?

**Minimum viable:**
- Win Rate > 50%
- Avg R > 1.0
- Total R > 10
- Trades > 30
- Max DD < 5R

**Production-ready:**
- Win Rate > 55%
- Avg R > 1.2
- Total R > 20
- Trades > 50
- Max DD < 3R
- Sharpe > 0.5

---

## 📈 Pipeline Workflow

### Stage 1: Discovery
Run discovery scan → System creates DRAFT candidates

### Stage 2: Testing
Review DRAFT candidates → Click "RUN BACKTEST"
- Runs comprehensive backtest
- Computes all metrics
- Updates status to TESTED

### Stage 3: Review
Review TESTED results → Move to PENDING
- Check metrics meet criteria
- Verify trade count sufficient
- Assess drawdown acceptable

### Stage 4: Approval
Review PENDING candidates → APPROVE or REJECT
- Human validation
- Final quality check
- Approved = ready for production

### Stage 5: Promotion
APPROVE candidates → PROMOTE TO PRODUCTION
- Adds to validated_setups table
- Becomes available in trading apps
- Links back to candidate_id

---

## 🔧 Technical Details

### Database Tables Used

**edge_candidates**
- All strategy candidates in the pipeline
- Stores configurations, metrics, status
- Links to validated_setups when promoted

**validated_setups**
- Production strategies
- Used by trading apps
- Immutable once promoted

**daily_features_v2**
- Historical ORB data
- Session statistics
- Used for backtesting

**bars_1m / bars_5m**
- Price data for entry/exit analysis
- Required for precise trade simulation

### Backtest Engine

**Location:** `research/candidate_backtest_engine.py`

**What it does:**
1. Loads historical ORB data from daily_features_v2
2. Applies entry filters (ORB size, ATR, etc.)
3. Simulates trades with exact entry/stop/target
4. Tracks P&L in R multiples
5. Computes comprehensive metrics
6. Stores results in metrics_json field

**Validation:**
- No lookahead bias (uses only data available at trade time)
- Precise 1-minute bar entry simulation
- Realistic stop/target execution
- Conservative assumptions (slippage, etc.)

---

## 🚀 Advanced Features

### Robustness Checks
- Walk-forward validation
- Regime split testing
- Out-of-sample performance
- Stability analysis

### Bulk Operations
- Test multiple candidates at once
- Approve/reject in batches
- Export results to CSV

### Integration
- Promoted strategies automatically appear in trading apps
- Seamless pipeline from discovery → production
- Full audit trail (who approved, when promoted)

---

## 📝 Example Workflows

### Workflow 1: Find New MGC Edge

1. Open DISCOVERY mode
2. Select "MGC" instrument
3. Select all ORB times (0900-0030)
4. Set Min Win Rate: 52%, Min Avg R: 1.0
5. Enable: ORB Size, Session Travel, R:R Ratios
6. Click "START DISCOVERY SCAN"
7. Wait for results (5-10 minutes)
8. Sort by Total R
9. Select top 5 performers
10. Click "ADD SELECTED TO PIPELINE"
11. Switch to PIPELINE mode
12. Review each candidate
13. Approve best ones
14. Promote to production

### Workflow 2: Validate Custom Strategy

1. Open BACKTESTER mode
2. Configure:
   - Instrument: NQ
   - ORB Time: 2300
   - R:R Target: 5.0
   - Min ORB Size: 0.10
   - Test Window: 2021-01-01 to 2024-12-31
3. Click "RUN BACKTEST"
4. Review results
5. If good: Note configuration
6. Go to PIPELINE, find auto-created candidate
7. Move through workflow: TESTED → PENDING → APPROVED → PROMOTED

### Workflow 3: Audit Production Strategies

1. Open PRODUCTION mode
2. Review all live strategies
3. Check performance metrics
4. Identify underperformers
5. Note configurations for improvement
6. Run new discovery scans with learned parameters

---

## ⚠️ Important Notes

### Overfitting Risk
- Don't over-optimize on small samples
- Require minimum 30 trades for validation
- Test on multiple time periods
- Prefer simpler strategies

### Data Quality
- Ensure complete historical data
- Check for gaps in bars tables
- Validate ORB calculations
- Run data quality checks first

### Realistic Expectations
- Not all scans will find edges
- Market conditions change
- Past performance ≠ future results
- Diversify across strategies

### Production Discipline
- Only promote strategies you understand
- Document reasoning for approvals
- Monitor production performance
- Be prepared to retire underperformers

---

## 🎓 Learning Resources

### Understanding ORB Strategies
See: `docs/TRADING_PLAYBOOK.md`

### Database Schema
See: `docs/DATABASE_SCHEMA_SOURCE_OF_TRUTH.md`

### Edge Pipeline Architecture
See: `docs/EDGE_SYSTEM_UNIFICATION.md`

### Zero Lookahead Rules
See: `docs/ZERO_LOOKAHEAD_RULES.md`

---

## 🆘 Troubleshooting

### "No candidates found"
- Run discovery scan first
- Or manually create candidates

### "Backtest failed"
- Check database has data for date range
- Verify daily_features_v2 populated
- Check error logs

### "Can't promote candidate"
- Ensure status is APPROVED
- Check not already promoted
- Verify validated_setups table accessible

### "Discovery scan too slow"
- Reduce number of ORB times tested
- Disable some filter tests
- Shorten test window

---

## ✅ You're Ready!

The Research Lab is your systematic edge discovery engine. Use it to:
- Find profitable strategies automatically
- Validate them rigorously
- Promote winners to production
- Build a robust strategy portfolio

**Start exploring. The edges are out there. Go find them.** 🔬

---

**Research Lab Version:** 1.0
**Last Updated:** 2026-01-25
**Database:** Local (gold.db)
**Port:** 8503
