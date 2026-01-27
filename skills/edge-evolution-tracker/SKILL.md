---
name: edge-evolution-tracker
description: Tracks how trading edges evolve over time, detects degradation, discovers new patterns, and identifies regime changes. Use weekly for edge health monitoring, after significant market changes, or when edge performance deviates from baseline. Extends edge_discovery_live.py with adaptive learning.
allowed-tools: Read, Bash(python:*), Grep, Glob
context: fork
agent: general-purpose
---

# Edge Evolution Tracker Skill

**Institutional-grade adaptive edge monitoring and discovery system.**

This skill extends your edge discovery capabilities with time-series analysis, regime change detection, and adaptive pattern learning. While `edge_discovery_live.py` finds edges in historical data, this skill monitors how those edges perform over time and discovers new patterns as markets evolve.

---

## Why Edges Evolve

**The hard truth about trading edges:**
- Markets adapt (institutional flows change, algorithms evolve, regulations shift)
- Edges degrade over time (profitable patterns get arbitraged away)
- New edges emerge (regime changes create new opportunities)
- Static strategies die (must evolve or become unprofitable)

**Examples from your system:**
- **Degraded edge:** Thursday 0900 ORB stopped working Q4 2025 (institutional flow change)
- **Emerging edge:** Asia high travel + London quiet → NY explosive (discovered 2025-11-03)
- **Regime change:** Trending markets 2024 vs range-bound 2025 (different setups work)

**This skill ensures you:**
1. **Detect degradation early** (30+ days before critical failure)
2. **Discover new patterns** (adaptive learning from recent data)
3. **Adapt to regime changes** (know which setups work in current market)
4. **Maintain edge quality** (continuous validation and improvement)

---

## Core Functions

### Function 1: Edge Health Monitoring

**Purpose:** Track validated_setups performance over rolling time windows

**Metrics tracked:**
- Win rate (current vs historical baseline)
- Expected R (current vs historical)
- Drawdown (max consecutive losses)
- Profit factor (gross win / gross loss)
- Trade frequency (setups per month)

**Detection method:**
- Rolling 30/60/90-day windows
- Statistical significance tests (chi-square for WR, t-test for E[R])
- Degradation threshold: >10% WR drop OR >20% E[R] drop

**Example invocation:**
```bash
/edge-evolution-tracker check-edge-health
```

**Output:**
```
EDGE HEALTH REPORT
==================
Date: 2026-01-25
Lookback windows: 30/60/90 days

🚨 DEGRADED EDGES (Immediate attention required)
-------------------------------------------------

Setup: MGC 0900 ORB (RR=8.0)
Status: DEGRADED (Critical)

Performance:
                Baseline    30-day    60-day    90-day    Change
Win Rate:       62.5%       48.2%     51.3%     54.1%     -14.3%  🔴
Expected R:     +4.40       +2.10     +2.85     +3.20     -27.3%  🔴
Trades:         150 (2yr)   8         14        22        Normal
Max DD:         3 losses    4 losses  4 losses  5 losses  Worse

Statistical Significance:
- Chi-square test: p=0.03 (significant degradation)
- Degradation confidence: 85%

Timeline Analysis:
- Degradation started: ~October 2025 (Q4)
- Acceleration: November-December 2025
- Current status: Stable but below threshold

Pattern Match:
- Matches learned_pattern: "thursday_0900_degraded_q4_2025"
- Hypothesis: Institutional order flow changed
- Supporting evidence: 72% of losses occurred on Thursdays

Cross-Instrument Check:
- NQ 0900 ORB: No degradation (performing normally)
- MPL 0900 ORB: Slight degradation (-8% WR, within noise)
- Conclusion: MGC-specific issue, not market-wide

RECOMMENDATIONS:
1. REDUCE POSITION SIZE: Use 50% size for 0900 ORB until edge stabilizes
2. INVESTIGATE: Run edge discovery with additional filters (day-of-week, session patterns)
3. ALTERNATIVE: Focus on 1100 ORB (stable performance, +64% WR last 90 days)
4. MONITOR: Weekly check for next 4 weeks (flag if WR drops below 45%)

---

✅ HEALTHY EDGES (Performing as expected)
------------------------------------------

Setup: MGC 1100 ORB (RR=8.0)
Status: ACTIVE (Excellent)

Performance:
                Baseline    30-day    60-day    90-day    Change
Win Rate:       61.8%       68.2%     64.1%     64.0%     +2.2%   ✅
Expected R:     +4.14       +5.20     +4.50     +4.45     +7.5%   ✅
Trades:         142 (2yr)   11        19        31        Normal
Max DD:         4 losses    2 losses  3 losses  3 losses  Better

Statistical Significance:
- Chi-square test: p=0.58 (stable, no significant change)
- Performance confidence: 92%

Notable Insights:
- Performance improving (recent 30-day best ever)
- Pattern match: "asia_high_travel_london_quiet" appearing more frequently
- Cross-instrument: Strong correlation with MPL strength (0.76)

RECOMMENDATIONS:
- INCREASE FOCUS: 1100 ORB is current best performer
- MONITOR: Continue tracking for pattern learning

---

⚠️ WATCH LIST (Minor concerns, not critical)
--------------------------------------------

Setup: MGC 2300 ORB (RR=2.5)
Status: STABLE (Watch)

Performance:
                Baseline    30-day    60-day    90-day    Change
Win Rate:       56.2%       50.0%     53.8%     54.9%     -2.3%   ⚠️
Expected R:     +0.85       +0.62     +0.71     +0.78     -8.2%   ⚠️
Trades:         125 (2yr)   6         13        18        Low

Statistical Significance:
- Chi-square test: p=0.42 (not significant)
- Sample size: Small (caution)

Notes:
- Degradation not statistically significant yet
- Small sample size (only 6 trades in 30 days)
- Continue monitoring, no action needed

---

SYSTEM-WIDE METRICS
-------------------

Total Active Edges: 17 (6 MGC, 5 NQ, 6 MPL)
Degraded: 1 (5.9%)
Healthy: 14 (82.4%)
Watch: 2 (11.8%)

Overall System Performance (90 days):
- Combined Win Rate: 58.3% (baseline 59.1%, -0.8%)
- Combined Expected R: +3.85 (baseline +4.02, -4.2%)
- System Status: HEALTHY (minor degradation within acceptable range)

NEXT REVIEW: 2026-02-01 (7 days)
```

### Function 2: Regime Change Detection

**Purpose:** Identify when market behavior shifts fundamentally

**Regime types:**
- **Trending:** Sustained directional moves, breakouts work well
- **Range-bound:** Mean reversion dominates, breakouts fail
- **Volatile:** Large swings, increased risk
- **Quiet:** Compressed ranges, low probability setups

**Detection method:**
- Rolling volatility (ATR, daily range)
- Trend strength (ADX-like metric)
- ORB outcome clustering (break success rate)
- Session flow patterns (Asia→London→NY behavior)

**Example invocation:**
```bash
/edge-evolution-tracker detect-regime-change
```

**Output:**
```
REGIME CHANGE ANALYSIS
======================
Date: 2026-01-25
Analysis window: 90 days (2025-10-27 to 2026-01-25)

🔄 REGIME CHANGE DETECTED (High Confidence)
--------------------------------------------

Previous Regime: TRENDING (2024-Q3 through 2025-Q3)
- Duration: 12 months
- Characteristics:
  - Daily range: 3.5 points average
  - Sustained directional moves
  - Breakout success rate: 68%
  - Best setups: 0900, 1100 ORBs

Current Regime: RANGE-BOUND (Started 2025-Q4)
- Duration: 3 months (ongoing)
- Characteristics:
  - Daily range: 1.8 points average (-49% vs trending)
  - Mean reversion dominant
  - Breakout success rate: 52% (-16% vs trending)
  - Best setups: 2300 ORB (NY volatility compression/release)

Regime Change Timeline:
- Transition period: Late September - Early October 2025
- Confidence: 87% (significant statistical change)
- Detection method: Volatility compression + outcome clustering

Evidence:
1. Average daily range dropped from 3.5 → 1.8 points (p < 0.01)
2. ORB break success rate dropped from 68% → 52% (p = 0.03)
3. Asia session travel decreased 40% (less energy buildup)
4. Mean reversion setups (fade moves) working better

Impact on Validated Edges:
✅ Benefiting from regime:
- 2300 ORB: +8% WR improvement (volatility compression suits this setup)
- 0030 ORB: +5% WR improvement (Asian mean reversion)

❌ Hurt by regime:
- 0900 ORB: -14% WR (breakouts failing in range-bound market)
- 1000 ORB: -9% WR (same issue)

🔮 Regime Forecast (Next 30 days):
- Probability of continuation: 72%
- Probability of return to trending: 18%
- Probability of volatile regime: 10%

Indicators to watch for regime change:
- Daily range expands above 2.8 points (sustained)
- Breakout success rate improves above 60%
- Asia session travel returns to 2.0+ average

ADAPTIVE STRATEGY:
------------------

While RANGE-BOUND regime persists:

INCREASE FOCUS:
- 2300 ORB (RR=2.5) - volatility compression/release
- 0030 ORB (RR=1.0) - mean reversion in Asia
- Position sizing: Standard

REDUCE FOCUS:
- 0900 ORB (breakouts failing)
- 1000 ORB (early-session breakouts weak)
- Position sizing: 50% of normal OR skip

NEW PATTERNS TO TEST:
- Fade extreme Asia moves (mean reversion)
- Trade compression releases (tight ranges → expansion)
- Evening session setups (NY volatility compression)

BACKTEST RECOMMENDATION:
Run edge_discovery_live.py with:
- Filter: date_local >= '2025-10-01' (range-bound regime only)
- Look for: Range-bound specific edges
- Expected: Find new patterns optimized for current regime
```

### Function 3: Adaptive Pattern Discovery

**Purpose:** Discover new edges that work in current market conditions

**How it differs from edge_discovery_live.py:**
- **edge_discovery_live.py:** Scans ALL historical data (5 years)
- **This function:** Focuses on RECENT data (3-12 months) to find patterns that work NOW

**Why this matters:**
- Markets change - edges that worked 3 years ago may not work today
- Recent patterns may not have enough history to pass edge_discovery_live.py thresholds (MIN_TRADES=100)
- But they may be MORE relevant than old edges with large samples

**Discovery methodology:**
1. **Recent Data Focus:** Last 3/6/12 months
2. **Relaxed Thresholds:** MIN_TRADES=30 (vs 100 for long-term edges)
3. **Higher Performance Bar:** MIN_WIN_RATE=15% (vs 12%) to compensate for smaller sample
4. **Cross-Validation:** Test pattern on multiple time windows

**Example invocation:**
```bash
/edge-evolution-tracker discover-recent-patterns --lookback=6months
```

**Output:**
```
ADAPTIVE PATTERN DISCOVERY
==========================
Date: 2026-01-25
Lookback: 6 months (2025-07-25 to 2026-01-25)
Min trades: 30
Min win rate: 15%
Min expected R: +0.20

🆕 NEW PATTERNS DISCOVERED
---------------------------

Pattern 1: "london_quiet_1100_explosive"
----------------------------------------
Description: When London session shows <3 reversals, 1100 ORB has explosive breaks

Performance (6 months):
- Trades: 34
- Win Rate: 70.6% (vs 61.8% baseline, +8.8%)
- Expected R: +5.20 (vs +4.14 baseline, +25.6%)
- Max DD: 3 losses
- Annual R: +28.6R (projected)

Filter Criteria:
- ORB: 1100
- london_reversals < 3
- liquidity_state = 'normal'

Statistical Validation:
- Chi-square: p=0.02 (significant improvement)
- Confidence: 78%
- Cross-validation: Tested on prior 6 months → 68% WR (stable)

Hypothesis:
Quiet London session indicates coiled energy. When Asia builds range (travel > 2.0)
and London consolidates (low reversals), NY session releases explosive move.

RECOMMENDATION: ADD TO VALIDATED SETUPS
- This pattern has statistical significance
- Performance stable across time windows
- Hypothesis makes sense (energy buildup → release)

Suggested Setup:
- Instrument: MGC
- ORB: 1100
- Filter: london_reversals < 3
- RR: 8.0 (use existing 1100 ORB target)
- Expected WR: 70%+ (if pattern holds)
- Expected R: +5.20

Action Items:
1. Run code-review-pipeline on proposed filter change
2. Update edge_discovery_live.py to test this filter
3. If validates, add to validated_setups table
4. Update trading_app/config.py with new filter
5. Monitor performance for next 30 days

---

Pattern 2: "mpl_mgc_correlation_boost"
---------------------------------------
Description: When MPL moves > 3.0 points in Asia session, MGC ORBs have higher WR

Performance (6 months):
- Trades: 28 (MGC ORBs following strong MPL Asia moves)
- Win Rate: 75.0% (vs 61% baseline, +14%)
- Expected R: +5.80 (vs +4.20 baseline, +38%)
- Max DD: 2 losses
- Annual R: +31.2R (projected)

Filter Criteria:
- MPL asia_travel > 3.0
- MGC ORB (any time, but strongest at 1100)
- Within same trading day

Statistical Validation:
- Chi-square: p=0.01 (highly significant)
- Confidence: 82%
- Cross-validation: Tested on prior 6 months → 71% WR (stable)

Hypothesis:
Strong MPL move signals institutional precious metals positioning. MGC follows with lag.
Asia MPL strength → MGC breakouts in NY session have institutional backing.

Cross-Instrument Intelligence:
- This is MULTI-INSTRUMENT pattern discovery
- Requires monitoring MPL in real-time
- Can be integrated into trading_memory session_state

RECOMMENDATION: ADD AS LEARNED PATTERN (not validated setup yet)
- Insert into learned_patterns table
- Monitor for 60 more days
- If performance holds, promote to validated setup with MPL filter

Action Items:
1. Add MPL monitoring to session_state tracking
2. Insert pattern into learned_patterns table
3. Update trading-memory skill to check MPL correlation
4. Test for 60 days before promoting to validated setup

---

⚠️ PATTERNS NOT VALIDATED (Insufficient confidence)
-----------------------------------------------------

Pattern: "thursday_afternoon_fade"
- Trades: 22 (small sample)
- Win Rate: 63.6% (decent)
- Confidence: 42% (too low - likely noise)
- Action: Continue monitoring, need 30+ trades

Pattern: "holiday_week_low_volume_compression"
- Trades: 12 (very small sample)
- Win Rate: 75% (great, but...)
- Confidence: 31% (unreliable)
- Action: Need full year of data (more holiday weeks)

---

SUMMARY
-------

New Patterns Discovered: 2
- Ready to validate: 1 (london_quiet_1100_explosive)
- Needs monitoring: 1 (mpl_mgc_correlation_boost)

Patterns Under Observation: 2
- Need more data for validation

NEXT STEPS:
1. Review "london_quiet_1100_explosive" with code-review-pipeline
2. Add MPL correlation pattern to learned_patterns table
3. Monitor both for 30-60 days
4. Re-run discovery in 30 days (continuous learning)
```

### Function 4: Multi-Timeframe Edge Analysis

**Purpose:** Analyze edge performance across different timeframes to understand stability

**Timeframes analyzed:**
- Last 30 days (current performance)
- Last 90 days (recent trend)
- Last 180 days (medium-term)
- Last 365 days (annual)
- All-time (since edge discovery)

**Example invocation:**
```bash
/edge-evolution-tracker analyze-edge-stability MGC 1100 RR=8.0
```

**Output:**
```
MULTI-TIMEFRAME EDGE ANALYSIS
==============================

Setup: MGC 1100 ORB (RR=8.0)

Performance Across Timeframes:
-------------------------------

| Timeframe | Trades | Win Rate | Exp R  | Max DD | Trend |
|-----------|--------|----------|--------|--------|-------|
| 30 days   | 11     | 68.2%    | +5.20  | 2      | ⬆️ UP  |
| 90 days   | 31     | 64.0%    | +4.45  | 3      | ⬆️ UP  |
| 180 days  | 58     | 62.5%    | +4.25  | 4      | ➡️ FLAT|
| 365 days  | 114    | 61.8%    | +4.14  | 4      | ➡️ FLAT|
| All-time  | 142    | 61.8%    | +4.14  | 4      | ➡️ FLAT|

Visual Trend (Win Rate):
```
70% |           📈 (30d)
65% |       📈 (90d)
60% | ━━━━━━━━━━━━━━━━━━  (baseline: 61.8%)
55% |
50% |
    └──────────────────────────────────
    All-time  365d  180d  90d  30d
```

Stability Analysis:
-------------------

✅ STABLE EDGE (High Confidence)

Edge Stability Score: 94/100 (Excellent)

Characteristics:
- Consistent WR across all timeframes (60-68%)
- Recent performance IMPROVING (not degrading)
- Low variance in expected R (+4.14 to +5.20)
- Drawdowns controlled (2-4 losses max)

Trend Classification: IMPROVING
- 30-day WR > 90-day WR > 365-day WR
- Recent data suggests edge getting STRONGER
- Possible explanation: London session patterns stabilizing

Risk Assessment: LOW
- Degradation probability: 8% (very low)
- Edge likely to continue working
- No regime-specific dependency detected

RECOMMENDATION: INCREASE POSITION SIZE
- Edge is stable AND improving
- High confidence in continuation
- Consider 1100 ORB as PRIMARY setup

Comparison to Other Edges:
---------------------------

MGC 1100 ORB vs MGC 0900 ORB:
- 1100: Stable/improving (✅)
- 0900: Degrading (❌)
- Conclusion: Market regime favors later-session breakouts

MGC 1100 ORB vs NQ 1100 ORB:
- MGC: 61.8% WR, improving
- NQ: 58.2% WR, stable
- Conclusion: MGC has edge, NQ is marginal

Historical Comparison:
----------------------

Best 90-day period: 2025-04-15 to 2025-07-15 (72% WR, +6.10 E[R])
Worst 90-day period: 2024-11-10 to 2025-02-10 (54% WR, +2.80 E[R])
Current 90-day: 64.0% WR, +4.45 E[R] (above median, improving)

Seasonal Patterns:
- Q1: 59.2% WR (below avg)
- Q2: 65.8% WR (best)
- Q3: 60.1% WR (avg)
- Q4: 63.4% WR (above avg)
- Current: Q1 2026, performing ABOVE typical Q1 (68% vs 59% historical)

INSIGHTS:
- Edge performs best in Q2 (spring)
- Currently outperforming typical Q1 pattern
- May indicate regime shift or exceptional conditions
```

### Function 5: Edge Correlation Analysis

**Purpose:** Understand which edges work together and which are redundant

**Why this matters:**
- If 2 edges are highly correlated, taking both doesn't diversify risk
- If 2 edges are anti-correlated, one can hedge the other
- Portfolio construction: Want uncorrelated edges for smoothness

**Example invocation:**
```bash
/edge-evolution-tracker analyze-edge-correlations
```

**Output:**
```
EDGE CORRELATION ANALYSIS
=========================

Correlation Matrix (All MGC Edges):
------------------------------------

           0900  1000  1100  1800  2300  0030
    0900   1.00  0.68  0.42  0.15 -0.08  0.21
    1000   0.68  1.00  0.55  0.22  0.03  0.28
    1100   0.42  0.55  1.00  0.31  0.18  0.35
    1800   0.15  0.22  0.31  1.00  0.52  0.44
    2300  -0.08  0.03  0.18  0.52  1.00  0.61
    0030   0.21  0.28  0.35  0.44  0.61  1.00

Correlation Scale:
  1.0 = Perfect positive correlation (move together)
  0.0 = No correlation (independent)
 -1.0 = Perfect negative correlation (move opposite)

Key Findings:
-------------

🔗 HIGH CORRELATION (Redundant edges):
- 0900 ↔ 1000: r=0.68 (highly correlated)
  → Both are early-session breakouts
  → Taking both on same day provides limited diversification
  → Recommendation: Choose ONE, not both

- 2300 ↔ 0030: r=0.61 (moderately high correlation)
  → Both are evening/overnight setups
  → Somewhat redundant
  → Recommendation: Prefer whichever has better setup quality

⚖️ LOW CORRELATION (Diversifying edges):
- 0900 ↔ 2300: r=-0.08 (near zero, slight negative)
  → Morning vs evening setups
  → Essentially independent
  → Recommendation: Excellent portfolio diversification

- 1100 ↔ 2300: r=0.18 (low positive)
  → Midday vs evening
  → Low correlation = good diversification

Portfolio Optimization:
-----------------------

OPTIMAL EDGE COMBINATION (Maximum Sharpe ratio):
1. 1100 ORB (best performer, improving)
2. 2300 ORB (uncorrelated with 1100, different session)
3. 1800 ORB (moderate correlation, adds exposure)

Expected Portfolio Performance:
- Combined WR: 60.3%
- Combined E[R]: +4.15
- Portfolio std dev: 35% lower than single-edge (diversification benefit)
- Sharpe ratio: 1.8 (excellent)

AVOID COMBINING:
- 0900 + 1000 (r=0.68, redundant)
  → If 0900 fails, 1000 likely fails too
  → Choose one based on current regime

Cross-Instrument Correlations:
-------------------------------

           MGC    NQ     MPL
    MGC    1.00   0.42   0.68
    NQ     0.42   1.00   0.35
    MPL    0.68   0.35   1.00

Key Findings:
- MGC ↔ MPL: r=0.68 (metals correlation, expected)
- MGC ↔ NQ: r=0.42 (moderate, gold vs tech indices)
- NQ ↔ MPL: r=0.35 (low, good diversification)

Portfolio Diversification:
- Trading MGC + NQ provides good diversification
- Trading MGC + MPL is somewhat redundant (both precious metals)
- Optimal: MGC + NQ for maximum uncorrelated exposure
```

---

## Integration with Existing System

### Extends edge_discovery_live.py

This skill COMPLEMENTS (not replaces) edge_discovery_live.py:

| Feature | edge_discovery_live.py | edge-evolution-tracker |
|---------|------------------------|------------------------|
| **Purpose** | Find edges in historical data | Monitor edge evolution over time |
| **Data scope** | All-time (5 years) | Rolling windows (30/60/90d) |
| **Thresholds** | MIN_TRADES=100 | MIN_TRADES=30 (recent patterns) |
| **Focus** | Long-term stable edges | Recent patterns, regime adaptation |
| **Output** | New edges to add to validated_setups | Degradation alerts, adaptive patterns |
| **Frequency** | On-demand (when seeking new edges) | Weekly (continuous monitoring) |

### Writes to learned_patterns

Newly discovered patterns are stored in `learned_patterns` table (from trading-memory skill):

```sql
INSERT INTO learned_patterns (
    pattern_id,
    description,
    hypothesis,
    condition_sql,
    instruments,
    confidence,
    sample_size,
    win_rate,
    avg_rr,
    discovered_date,
    status
) VALUES (
    'london_quiet_1100_explosive',
    'When London session shows <3 reversals, 1100 ORB has explosive breaks',
    'Quiet London = coiled energy, NY releases spring',
    'orb_time = "1100" AND london_reversals < 3',
    'MGC',
    0.78,
    34,
    70.6,
    5.20,
    '2026-01-25',
    'testing'
);
```

### Integrates with trading-memory

Edge degradation events are stored as notable insights:

```sql
INSERT INTO trade_journal (
    date_local,
    orb_time,
    instrument,
    outcome,
    lesson_learned,
    notable
) VALUES (
    '2026-01-25',
    '0900',
    'MGC',
    'DEGRADED_EDGE',
    'Edge health check detected 0900 ORB degradation: -14.3% WR over 90 days. Hypothesis: Institutional flow change on Thursdays.',
    TRUE
);
```

---

## Automation and Scheduling

### Weekly Edge Health Check

```bash
# Add to crontab or Task Scheduler
# Run every Monday at 09:00
0 9 * * 1 /usr/bin/python3 scripts/run_edge_health_check.py
```

### Monthly Regime Detection

```bash
# First day of month at 10:00
0 10 1 * * /usr/bin/python3 scripts/detect_regime_change.py
```

### Quarterly Pattern Discovery

```bash
# First day of quarter at 11:00
0 11 1 1,4,7,10 * /usr/bin/python3 scripts/discover_recent_patterns.py
```

---

## Success Metrics

**This skill is working if:**
- Edge degradation detected 30+ days before critical failure (lead time)
- New patterns discovered 2-4 per quarter (continuous learning)
- Regime changes identified within 30 days of shift (timely adaptation)
- False positives < 20% (not over-alerting on noise)
- Adaptive patterns have >70% validation rate (quality discoveries)

**Red flags:**
- Edge failure not detected until major drawdown (missed degradation)
- No new patterns discovered in 6+ months (system stagnant)
- Regime change missed (trading wrong setups for market)
- High false positive rate (ignoring alerts, alert fatigue)

---

## Example Workflow: Continuous Evolution

**Week 1: Edge Health Check**
```bash
/edge-evolution-tracker check-edge-health
```
Output: 0900 ORB showing early degradation (-8% WR over 60 days)
Action: Add to watch list, monitor weekly

**Week 2-3: Monitoring**
Degradation continues: -10% WR over 60 days
Action: Reduce position size to 50%

**Week 4: Critical Threshold**
Degradation reaches -14% WR over 90 days (CRITICAL)
Action: Stop trading 0900 ORB, run pattern discovery

**Week 5: Adaptive Discovery**
```bash
/edge-evolution-tracker discover-recent-patterns
```
Output: New pattern discovered: "london_quiet_1100_explosive" (70% WR, 34 trades)
Action: Add to learned_patterns, begin testing

**Week 6-10: Validation**
New pattern holds: 72% WR over 5 weeks (consistent)
Action: Promote to validated_setups, update config.py

**Week 11: Regime Check**
```bash
/edge-evolution-tracker detect-regime-change
```
Output: Regime shifted to RANGE-BOUND (87% confidence)
Action: Adjust strategy - focus on mean reversion setups (2300, 0030)

**Week 12: Portfolio Optimization**
```bash
/edge-evolution-tracker analyze-edge-correlations
```
Output: 1100 + 2300 are uncorrelated (optimal portfolio)
Action: Increase focus on these two setups, reduce redundant edges

**Continuous Cycle:**
- Monitor edge health weekly
- Discover new patterns quarterly
- Detect regime changes monthly
- Optimize portfolio continuously

**Result:** System evolves with market, maintains edge quality, avoids degraded strategies

---

## Related Skills

- **trading-memory** - Stores edge performance history, provides data for analysis
- **market-anomaly-detection** - Identifies unusual conditions that may affect edges
- **code-review-pipeline** - Validates new pattern implementations before deployment

---

**This is adaptive intelligence. Markets evolve. Your system evolves faster. While other traders ride edges into the ground, you detect degradation early and discover new patterns. This is how institutional traders maintain alpha over decades.**
