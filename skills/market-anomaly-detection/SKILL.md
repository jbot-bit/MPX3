---
name: market-anomaly-detection
description: Detects unusual market conditions, execution issues, and data quality problems specific to trading. Use before taking trades (market condition checks), after trades (execution quality validation), or for data integrity monitoring. Identifies ORB traps, liquidity issues, slippage anomalies, and data feed errors.
allowed-tools: Read, Bash(python:*, duckdb:*), Grep
---

# Market Anomaly Detection Skill

**Institutional-grade anomaly detection for trading system safety and performance.**

This skill detects unusual market conditions and system issues that could cause financial losses or indicate problems requiring immediate attention. Unlike generic anomaly detection (which just flags "unusual" data), this is trading-specific with domain knowledge about what anomalies matter and why.

---

## What Makes This Institutional-Grade

**Standard anomaly detection:**
- "This data point is 3 standard deviations from mean" (so what?)
- No context on whether anomaly is good or bad
- No domain knowledge

**This system:**
- "ORB size is 10x normal AND spread is 3x wider → manipulation/trap (DON'T TRADE)"
- "Slippage is 5x your average → system issue or connection problem (INVESTIGATE)"
- "10R winner detected → anomaly but GOOD (document what made it work)"
- Context-aware: Different thresholds for different instruments, sessions, market conditions

---

## Anomaly Categories

### 1. Market Anomalies (Pre-Trade Risk Assessment)

Detect unusual market conditions that affect trade quality.

#### ORB Size Anomalies
**Detection:** ORB size > 3 std deviations from historical mean for that time/instrument

**Why it matters:**
- Extremely large ORB = potential trap/manipulation
- Extremely small ORB = low probability of meaningful break
- Both reduce edge quality

**Thresholds (MGC):**
```python
# Historical mean ± std dev (from daily_features_v2)
NORMAL_ORB_SIZES = {
    '0900': {'mean': 0.08, 'std': 0.03},  # 0.05-0.11 normal range
    '1000': {'mean': 0.09, 'std': 0.04},
    '1100': {'mean': 0.10, 'std': 0.04},
    '1800': {'mean': 0.12, 'std': 0.05},
    '2300': {'mean': 0.15, 'std': 0.06},
    '0030': {'mean': 0.11, 'std': 0.04},
}

# Anomaly if:
# - ORB size > mean + 3*std  (trap risk)
# - ORB size < mean - 2*std  (low probability)
```

**Example:**
```
MARKET ANOMALY DETECTED: ORB Size Trap

ORB: 0900
Size: 0.25 (250% above normal)
Z-score: 4.2 (extreme outlier)

Historical context:
- Normal 0900 ORB: 0.05-0.11
- This size seen only 3 times in 5 years
- All 3 prior cases: LOSS (trap/false breakout)

RISK LEVEL: HIGH
RECOMMENDATION: SKIP this ORB
Reason: Abnormally large ORB size indicates potential manipulation or trap
```

#### Liquidity Anomalies
**Detection:** Volume < 50% of historical average for that session

**Why it matters:**
- Low liquidity = wider spreads, worse fills, higher slippage
- Increases execution risk
- Reduces edge quality

**Thresholds:**
```python
# Compare current volume to historical session averages
VOLUME_THRESHOLD = 0.50  # Alert if <50% of normal

# Query daily_features_v2 for session volume stats
SELECT
    AVG(asia_volume) as avg_asia_vol,
    AVG(london_volume) as avg_london_vol,
    AVG(ny_volume) as avg_ny_vol
FROM daily_features_v2
WHERE date_local >= DATE('now', '-90 days')
```

**Example:**
```
MARKET ANOMALY DETECTED: Low Liquidity

Session: Asia
Current volume: 1,240 contracts
Normal volume: 3,500 contracts (90-day avg)
Deviation: -64% (CRITICAL)

Context:
- Date: 2026-01-01 (New Year's Day)
- Holiday trading (reduced participation)

RISK LEVEL: HIGH
RECOMMENDATION: SKIP all ORBs today
Reason: Extremely low liquidity increases execution risk and reduces edge reliability

Expected impact:
- Slippage: 3-5x normal
- Spread: 2-3x wider
- Fill quality: Poor
```

#### Spread Anomalies
**Detection:** Bid-ask spread > 2x normal for that instrument

**Why it matters:**
- Wide spread = poor fills on both entry and exit
- Eats into edge (0.5 point spread on MGC = 50% of 1.0 ORB)
- Indicates liquidity stress or market uncertainty

**Thresholds (MGC):**
```python
NORMAL_SPREAD = 0.1  # 1 tick
ALERT_THRESHOLD = 0.3  # 3 ticks (3x normal)
CRITICAL_THRESHOLD = 0.5  # 5 ticks (5x normal)
```

**Example:**
```
MARKET ANOMALY DETECTED: Wide Spread

Instrument: MGC
Current spread: 0.6 points
Normal spread: 0.1 points
Deviation: 6x normal (CRITICAL)

Possible causes:
- Contract rollover (check contract_days_to_roll)
- News event (high uncertainty)
- Low liquidity

RISK LEVEL: CRITICAL
RECOMMENDATION: DO NOT TRADE until spread normalizes
Reason: 0.6 spread would consume 60% of typical 1.0R target (edge destroyed)

Wait for:
- Spread < 0.3 points (acceptable)
- Liquidity to return to normal
```

#### Volume Spike Anomalies
**Detection:** Volume > 5x average in short period (5 minutes)

**Why it matters:**
- Sudden volume spike = news event or institutional activity
- May invalidate technical setup
- Requires fundamental check before trading

**Example:**
```
MARKET ANOMALY DETECTED: Volume Spike

Time: 08:55 (5 minutes before 0900 ORB)
Current 5min volume: 12,500 contracts
Normal 5min volume: 2,000 contracts
Spike: 6.2x normal (EXTREME)

Possible causes:
- Economic data release (check calendar)
- Breaking news (geopolitical, Fed, etc.)
- Large institutional order

RISK LEVEL: HIGH
RECOMMENDATION: PAUSE trading, check news sources
Reason: Technical setup may be invalidated by fundamental driver

Action items:
1. Check economic calendar (Fed announcement? NFP?)
2. Scan news (gold-specific or macro events)
3. Wait for volatility to settle before taking technical setup
```

### 2. Execution Anomalies (Post-Trade Quality Check)

Detect poor execution quality that may indicate system issues.

#### Slippage Anomalies
**Detection:** Slippage > 2 std deviations from your historical average

**Why it matters:**
- Excessive slippage destroys edge profitability
- May indicate connection issues, platform problems, or market stress
- Requires investigation and potential system fixes

**Thresholds:**
```python
# Your historical execution metrics (from trade_journal/execution_metrics)
YOUR_SLIPPAGE_STATS = {
    'normal_market': {'mean': 0.1, 'std': 0.05},  # 0.05-0.15 typical
    'fast_market': {'mean': 0.3, 'std': 0.10},     # 0.20-0.40 typical
    'thin_liquidity': {'mean': 0.5, 'std': 0.15},  # 0.35-0.65 typical
}

# Anomaly if: actual_slippage > mean + 2*std
```

**Example:**
```
EXECUTION ANOMALY DETECTED: Excessive Slippage

Trade: 0900 ORB entry
Theoretical entry: 2654.4
Actual entry: 2655.9
Slippage: 1.5 points (15x your average!)
Z-score: 5.8 (extreme outlier)

Your historical slippage:
- Normal market: 0.05-0.15 points
- Fast market: 0.20-0.40 points
- This trade: 1.5 points (CRITICAL)

RISK LEVEL: CRITICAL
IMPACT: 1.5 point slippage on 1.0R target = -150% of expected profit (trade became instant loser)

Possible causes:
1. Connection issues (latency spike, packet loss)
2. Platform/broker issue (order routing failure)
3. Extreme market volatility (flash crash, news event)
4. Wrong order type used (market order in thin liquidity)

ACTION REQUIRED: INVESTIGATE IMMEDIATELY
- Check connection logs (ping, latency)
- Review platform order flow
- Contact broker if pattern repeats
- Consider limit orders instead of market orders
```

#### Fill Time Anomalies
**Detection:** Fill time > 2 seconds (when usually < 500ms)

**Why it matters:**
- Slow fills = prices move against you
- May indicate connection or platform issues
- In fast-moving ORB breaks, seconds matter

**Thresholds:**
```python
NORMAL_FILL_TIME_MS = 300  # 300ms average
ALERT_THRESHOLD_MS = 1000  # 1 second (slow)
CRITICAL_THRESHOLD_MS = 2000  # 2 seconds (very slow)
```

**Example:**
```
EXECUTION ANOMALY DETECTED: Slow Fill

Trade: 1100 ORB entry
Order submitted: 11:05:12.340
Fill confirmed: 11:05:15.890
Fill time: 3,550ms (3.55 seconds)

Your historical fill times:
- Average: 280ms
- 95th percentile: 500ms
- This trade: 3,550ms (12x slower than normal)

Price impact:
- Price at order: 2654.4
- Price at fill: 2655.1
- Slippage due to delay: 0.7 points

RISK LEVEL: HIGH
ACTION REQUIRED: Diagnose connection/platform issue

Diagnostic checklist:
1. Check internet connection (speed test, ping)
2. Review platform logs (order routing, exchange connectivity)
3. Test on paper trading account (isolate broker issue)
4. Consider switching to backup connection (mobile hotspot, VPN)
```

#### Entry Price Anomalies
**Detection:** Entry price > 0.5 points from theoretical ORB boundary

**Why it matters:**
- Incorrect entry = edge calculation wrong
- May indicate logic bug in strategy code
- Could be catastrophic if systematic

**Example:**
```
EXECUTION ANOMALY DETECTED: Wrong Entry Price

Trade: 0900 ORB (UP break)
ORB high: 2654.3
Expected entry: ~2654.4 (first close above high)
Actual entry: 2656.8
Deviation: 2.5 points (MASSIVE ERROR)

RISK LEVEL: CRITICAL
This is NOT normal slippage - this is a logic error!

Possible causes:
1. BUG: Entry logic calculated wrong ORB boundary
2. BUG: Using wrong bar data (5min instead of 1min close)
3. MANUAL ERROR: User entered trade manually at wrong price
4. DATA ERROR: ORB high stored incorrectly in database

ACTION REQUIRED: IMMEDIATE CODE REVIEW
Run: /code-review-pipeline on setup_detector.py and execution_engine.py

DO NOT TRADE until root cause identified and fixed!
Risk: If this is a systematic bug, ALL trades may have wrong entries
```

### 3. Data Quality Anomalies (System Health Monitoring)

Detect data feed or database issues.

#### Missing Bars
**Detection:** Gaps in 1-minute bar timestamps

**Why it matters:**
- Missing bars = incomplete session data
- ORB calculations may be wrong
- Feature building may fail or use incorrect data

**Example:**
```
DATA QUALITY ANOMALY: Missing Bars

Date: 2026-01-25
Expected bars: 1440 (full 24-hour session)
Actual bars: 1387
Missing: 53 bars (3.7% data loss)

Gap details:
- 09:15-09:42: 27 bars missing (during Asia session)
- 14:20-14:45: 26 bars missing (during NY session)

RISK LEVEL: HIGH
IMPACT:
- 0900 ORB may be calculated incorrectly (gap during formation)
- Daily features may be incomplete
- Backtest results unreliable for this date

ACTION REQUIRED:
1. Check data feed logs (Databento connection issues?)
2. Rerun backfill for this date
3. Verify daily_features_v2 for 2026-01-25
4. Flag this date in quality control log
```

#### Duplicate Timestamps
**Detection:** Same timestamp appears multiple times in bars_1m

**Why it matters:**
- Indicates data corruption or feed bug
- Aggregations will be wrong
- Database integrity compromised

**Example:**
```
DATA QUALITY ANOMALY: Duplicate Timestamps

Date: 2026-01-25
Timestamp: 2026-01-25 09:05:00 UTC
Occurrences: 3 (should be 1)

Bars with duplicate timestamp:
1. open=2654.1, high=2654.5, low=2653.9, close=2654.3
2. open=2654.3, high=2654.7, low=2654.1, close=2654.5
3. open=2654.5, high=2654.9, low=2654.3, close=2654.7

RISK LEVEL: CRITICAL
IMPACT: Database integrity compromised

Which bar is correct? Unknown - manual inspection required

ACTION REQUIRED:
1. Check source data (DBN file or ProjectX API response)
2. Delete duplicate rows from bars_1m
3. Rerun backfill for this timestamp/date range
4. Investigate root cause (feed bug, database constraint failure)
5. Add database constraint to prevent duplicates (UNIQUE on ts_utc)
```

#### Price Spike Anomalies
**Detection:** Price move > 10 points in 1 minute (likely data error, not real)

**Why it matters:**
- Data feed error (bad tick) vs real market event
- Can corrupt ORB calculations, trigger false trades
- Must filter out data errors

**Example:**
```
DATA QUALITY ANOMALY: Price Spike (Likely Data Error)

Date: 2026-01-25
Time: 09:22:00 UTC
Price change: -15.3 points in 1 minute (0.6% move)

Bar details:
- Previous close: 2654.3
- This bar: open=2654.3, high=2654.5, low=2639.0, close=2639.5
- Next bar: open=2654.4, high=2654.8, low=2654.2, close=2654.6

RISK LEVEL: HIGH
DIAGNOSIS: Data error (not real market move)

Evidence:
- 15 point drop, then immediate recovery (V-shaped)
- No corresponding volume spike
- No news event at this timestamp
- Next bar returns to normal range

ACTION REQUIRED:
1. Flag this bar as invalid (data_quality_issues table)
2. Exclude from ORB calculations
3. Report to data provider (Databento ticket)
4. Implement sanity check filter in backfill scripts:
   - If abs(close - prev_close) > 10 points AND next bar reverts, flag as error
```

---

## Detection Methodology

### Statistical Thresholds

All anomalies use **data-driven thresholds** from your historical data (not generic defaults):

```python
# Calculate from daily_features_v2, trade_journal, execution_metrics
def calculate_thresholds(instrument, metric, lookback_days=90):
    """
    Calculate mean, std, and anomaly thresholds from historical data.

    Returns:
        mean: Historical average
        std: Standard deviation
        z_score_threshold: Anomaly trigger (typically 2-3 std devs)
    """
    query = f"""
        SELECT {metric}
        FROM daily_features_v2
        WHERE instrument = '{instrument}'
          AND date_local >= DATE('now', '-{lookback_days} days')
          AND {metric} IS NOT NULL
    """
    data = execute_query(query)

    mean = np.mean(data)
    std = np.std(data)

    # Conservative threshold (2 std for warnings, 3 std for critical)
    return {
        'mean': mean,
        'std': std,
        'warning_threshold': mean + 2 * std,
        'critical_threshold': mean + 3 * std
    }
```

### Context-Aware Detection

Thresholds adapt to context:

- **Market conditions:** Fast markets allow higher slippage (don't false-alarm)
- **Instrument:** MGC vs NQ have different normal ranges
- **Session:** Asia vs NY sessions have different volatility/liquidity
- **Your execution:** Thresholds based on YOUR historical performance, not generic trader

**Example:**
```python
# Slippage anomaly detection (context-aware)
if market_condition == 'fast':
    threshold = YOUR_FAST_MARKET_SLIPPAGE + 2 * std
elif market_condition == 'thin':
    threshold = YOUR_THIN_LIQUIDITY_SLIPPAGE + 2 * std
else:
    threshold = YOUR_NORMAL_SLIPPAGE + 2 * std

if actual_slippage > threshold:
    alert("ANOMALY: Excessive slippage for these market conditions")
```

---

## Integration with Trading System

### Pre-Trade Checks (Before Entry)

```python
# Example workflow
def pre_trade_check(orb_time, instrument):
    """
    Run market anomaly detection before taking trade.
    Returns: (safe_to_trade: bool, warnings: list)
    """
    warnings = []

    # Check ORB size
    orb_size = get_current_orb_size(orb_time, instrument)
    if is_orb_size_anomaly(orb_size, orb_time, instrument):
        warnings.append("ORB size anomaly (trap risk)")

    # Check liquidity
    if is_liquidity_anomaly(instrument):
        warnings.append("Low liquidity (execution risk)")

    # Check spread
    if is_spread_anomaly(instrument):
        warnings.append("Wide spread (edge degradation)")

    # Check volume
    if is_volume_spike():
        warnings.append("Volume spike (news event?)")

    safe_to_trade = len(warnings) == 0
    return safe_to_trade, warnings
```

### Post-Trade Checks (After Execution)

```python
# Example workflow
def post_trade_check(trade_data):
    """
    Run execution anomaly detection after trade completes.
    Returns: (execution_quality: str, issues: list)
    """
    issues = []

    # Check slippage
    if is_slippage_anomaly(trade_data):
        issues.append(f"Excessive slippage: {trade_data['slippage']} points")

    # Check fill time
    if is_fill_time_anomaly(trade_data):
        issues.append(f"Slow fill: {trade_data['fill_time_ms']}ms")

    # Check entry price
    if is_entry_price_anomaly(trade_data):
        issues.append(f"Entry price wrong by {trade_data['entry_deviation']} points")

    if len(issues) == 0:
        execution_quality = "EXCELLENT"
    elif len(issues) == 1:
        execution_quality = "ACCEPTABLE"
    else:
        execution_quality = "POOR"

    return execution_quality, issues
```

### Data Quality Monitoring (Continuous)

```bash
# Run daily after backfill
/market-anomaly-detection check-data-quality 2026-01-25
```

Checks for:
- Missing bars
- Duplicate timestamps
- Price spike errors
- Volume anomalies

Generates quality report and flags issues for manual review.

---

## Anomaly Response Protocols

### CRITICAL Anomalies (Immediate Action)

**DO NOT TRADE:**
- ORB size > 3 std devs (trap risk)
- Spread > 5x normal (execution impossible)
- Entry price > 0.5 points wrong (logic bug)
- Slippage > 5x your average (system failure)

**ACTION:**
1. STOP all trading immediately
2. Investigate root cause
3. Run diagnostics (connection, platform, code review)
4. DO NOT RESUME until issue resolved

### HIGH Anomalies (Trade with Caution)

**REDUCE POSITION SIZE OR SKIP:**
- Liquidity < 50% normal
- Spread 2-3x normal
- Recent execution quality degraded

**ACTION:**
1. Assess if edge still positive given conditions
2. Reduce position size 50% if proceeding
3. Monitor execution closely
4. Document outcome for learning

### MEDIUM Anomalies (Awareness Only)

**PROCEED WITH AWARENESS:**
- ORB size slightly large/small
- Volume spike (but spread normal)
- Slippage at upper end of normal range

**ACTION:**
1. Note anomaly in trade log
2. Adjust expectations (may exit earlier, wider stop)
3. No change to position size

---

## Success Metrics

**This skill is working if:**
- CRITICAL anomalies detected before losses (100% catch rate)
- False positive rate < 10% (not over-alerting)
- Data quality issues caught within 24 hours
- Execution quality improves (anomaly feedback → system fixes)
- Zero trades taken during critical anomalies

**Red flags:**
- Anomaly detected AFTER loss (too late)
- High false positive rate (ignoring alerts)
- Data quality issues undetected for days
- Same anomaly repeating (not addressing root cause)

---

## Related Skills

- **trading-memory** - Stores anomaly occurrences for pattern learning
- **edge-evolution-tracker** - Monitors if edges degrade during anomalous conditions
- **code-review-pipeline** - Detects bugs that could cause execution anomalies

---

**This is your safety net. It prevents bad trades, catches system issues, and maintains data integrity. Bloomberg traders lose millions to execution problems. You won't.**
