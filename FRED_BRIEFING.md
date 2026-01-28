# INDEPENDENT REVIEW BRIEFING FOR FRED
**Date: 2026-01-28**
**Purpose: Independent validation of MGC ORB strategy calculations**

---

## Your Mission

You are being asked to INDEPENDENTLY validate trading strategy calculations.

**CRITICAL:** You should NOT see our results until you finish your own calculations.

**Your task:**
1. Read the strategy specifications below
2. Access raw 1-minute bar data (bars_1m table)
3. Implement the logic from scratch
4. Calculate expectancy for each strategy
5. Compare your results to ours (will be provided after)

**DO NOT:**
- Look at validated_trades table (contains our results)
- Look at validated_setups table (contains our expectations)
- Read ADVANCED_BACKTEST_RESULTS.md (contains our findings)
- Trust any existing calculations

**START FRESH. ASSUME EVERYTHING IS WRONG.**

---

## Database Access

**Database:** `data/db/gold.db` (DuckDB)

**Primary table:** `bars_1m`
```sql
CREATE TABLE bars_1m (
    ts_utc TIMESTAMPTZ PRIMARY KEY,
    symbol VARCHAR,           -- 'MGC'
    source_symbol VARCHAR,    -- actual contract (MGCG4, MGCM4, etc.)
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT
);
```

**Date range:** 2024-01-02 to 2026-01-14 (~2 years, 745 trading days)

**Timezone:** All timestamps in UTC. Convert to Australia/Brisbane (UTC+10, no DST) for trading day windows.

---

## Trading Day Definition

**CRITICAL:** Trading day runs 09:00 local → 09:00 local next day

**In UTC:** 23:00 previous day → 23:00 current day

**Example:**
- Trading day "2024-12-09" starts at 2024-12-08 23:00:00 UTC
- Trading day "2024-12-09" ends at 2024-12-09 23:00:00 UTC

**Why:** Gold trades 23 hours/day. This window captures full NY session (opens 23:00 UTC).

---

## Strategy Specifications

### Strategy Family: ORB (Opening Range Breakout)

**Core concept:**
1. Define ORB window (5 minutes at specific time)
2. Calculate ORB high/low
3. Detect break (first 1m CLOSE outside range)
4. Enter at NEXT 1m OPEN after break (B-entry model)
5. Place stop at ORB edge
6. Place target at entry +/- (RR × risk)
7. Exit when target or stop hit

**7 Strategies to Validate:**

| ID | ORB Time | RR | SL Mode |
|----|----------|-----|---------|
| 21 | 1000 | 2.0 | full |
| 22 | 1000 | 2.5 | full |
| 23 | 1000 | 3.0 | full |
| 25 | 0900 | 1.5 | full |
| 28 | 0900 | 2.0 | full |
| 29 | 0900 | 2.5 | full |
| 30 | 0900 | 3.0 | full |

---

## Detailed Logic

### Step 1: Define ORB Window

**ORB times in local time (Australia/Brisbane):**
- 0900 ORB: 09:00-09:05 local
- 1000 ORB: 10:00-10:05 local

**Convert to UTC:**
- 0900 local = 23:00 UTC previous day
- 1000 local = 00:00 UTC current day

**ORB window:** 5 consecutive 1-minute bars starting at ORB time

**Example (0900 ORB on 2024-12-09):**
- Start: 2024-12-08 23:00:00 UTC
- End: 2024-12-08 23:05:00 UTC (exclusive)

### Step 2: Calculate ORB High/Low

```
orb_high = MAX(high) across 5 ORB bars
orb_low = MIN(low) across 5 ORB bars
orb_size = orb_high - orb_low
```

**Handle missing bars:** If < 5 bars in window, skip that day (outcome = NO_TRADE).

### Step 3: Detect Break

**Rule:** First 1m bar AFTER ORB window where CLOSE is outside [orb_low, orb_high]

**Direction:**
- UP break: close > orb_high
- DOWN break: close < orb_low

**Important:**
- Use CLOSE, not high/low touch
- Only first break counts
- If no break by end of day: outcome = NO_TRADE

### Step 4: Entry Price (B-Entry Model)

**CRITICAL:** Entry is NEXT 1m OPEN after break bar

**Example:**
- Break detected at 09:31 (close outside range)
- Entry bar: 09:32
- Entry price: 09:32 OPEN

**Why B-entry:** Avoids look-ahead bias. You can't enter on the same bar that signals the break.

### Step 5: Stop Price

**sl_mode = 'full':** Stop at ORB edge

- UP break (long): stop = orb_low
- DOWN break (short): stop = orb_high

### Step 6: Target Price

```
risk_points = |entry - stop|
target_points = RR × risk_points

If UP break:
    target = entry + target_points

If DOWN break:
    target = entry - target_points
```

### Step 7: Exit Detection

**Scan bars after entry bar** to find when target or stop is hit.

**Rules:**
- UP break (long):
  - Target hit if bar.high >= target
  - Stop hit if bar.low <= stop
- DOWN break (short):
  - Target hit if bar.low <= target
  - Stop hit if bar.high >= stop

**Simultaneous hits:** If both hit in same bar, assume STOP hit (conservative).

**Outcome:**
- Target hit → outcome = 'WIN', exit_price = target
- Stop hit → outcome = 'LOSS', exit_price = stop
- Neither hit by end of day → outcome = 'OPEN' (skip for expectancy calculation)

### Step 8: Calculate Realized RR

**CRITICAL:** Must include transaction costs.

**MGC Specifications:**
- Point value: $10.00 per point
- Total friction: $8.40 RT (round trip)
  - Commission: $2.40
  - Spread (2 crossings): $2.00
  - Slippage: $4.00

**Formula:**
```
If WIN:
    pnl_points = target_points (already calculated)

If LOSS:
    pnl_points = -risk_points

pnl_dollars = pnl_points × 10.0
net_pnl = pnl_dollars - 8.40

risk_dollars = risk_points × 10.0 + 8.40

realized_rr = net_pnl / risk_dollars
```

**Example (WIN):**
```
risk_points = 12.0
target_points = 24.0 (RR=2.0)

pnl_dollars = 24.0 × 10.0 = $240.00
net_pnl = $240.00 - $8.40 = $231.60
risk_dollars = 12.0 × 10.0 + 8.40 = $128.40

realized_rr = $231.60 / $128.40 = +1.804R
```

**Example (LOSS):**
```
risk_points = 12.0

pnl_dollars = -12.0 × 10.0 = -$120.00
net_pnl = -$120.00 - $8.40 = -$128.40
risk_dollars = 12.0 × 10.0 + 8.40 = $128.40

realized_rr = -$128.40 / $128.40 = -1.000R
```

### Step 9: Calculate Expectancy

**For each strategy:**
```
1. Run logic for all 745 trading days
2. Collect realized_rr for all WIN/LOSS trades
3. Calculate: expectancy = MEAN(realized_rr)
4. Calculate: win_rate = wins / (wins + losses)
5. Calculate: sample_size = wins + losses
```

**Skip:**
- NO_TRADE (no ORB break)
- OPEN (never resolved)

---

## Your Deliverables

### 1. Expectancy Results Table

| Strategy | Sample Size | Win Rate | Expectancy | Notes |
|----------|-------------|----------|------------|-------|
| 21 (1000 RR=2.0) | ? | ? | ? | |
| 22 (1000 RR=2.5) | ? | ? | ? | |
| 23 (1000 RR=3.0) | ? | ? | ? | |
| 25 (0900 RR=1.5) | ? | ? | ? | |
| 28 (0900 RR=2.0) | ? | ? | ? | |
| 29 (0900 RR=2.5) | ? | ? | ? | |
| 30 (0900 RR=3.0) | ? | ? | ? | |

### 2. Spot Check: 5 Random Trades

Pick 5 random trades and show full calculation breakdown:
- Date
- ORB high/low
- Break direction
- Entry/stop/target prices
- Exit price
- Realized RR
- Hand calculation verification

### 3. Discrepancy Report

**After calculating your own results:**
- Compare to our results (will be provided)
- Report ANY discrepancies > 0.001R
- Identify root cause of differences

---

## Common Pitfalls to Avoid

### 1. Timezone Errors
❌ Using 0900 UTC (wrong)
✅ Using 0900 local (23:00 UTC previous day)

### 2. Look-Ahead Bias
❌ Entry on break bar close
✅ Entry on NEXT bar open

### 3. Cost Model
❌ Using $4.20 one-way
✅ Using $8.40 round trip

### 4. Exit Detection
❌ Using CLOSE to detect target/stop
✅ Using HIGH/LOW to detect hits

### 5. Bar Boundaries
❌ Including end timestamp in ORB window
✅ Exclusive end (09:00-09:05 means 5 bars, not 6)

---

## Our Results (DO NOT LOOK UNTIL YOU FINISH)

**Results are in:** `validated_trades` table

**Query to compare:**
```sql
SELECT
    setup_id,
    COUNT(*) as n,
    AVG(CASE WHEN outcome IN ('WIN', 'LOSS') THEN realized_rr END) as expectancy,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) /
    SUM(CASE WHEN outcome IN ('WIN', 'LOSS') THEN 1 ELSE 0 END) as win_rate
FROM validated_trades
WHERE setup_id IN (21, 22, 23, 25, 28, 29, 30)
GROUP BY setup_id
ORDER BY setup_id;
```

**Expected results (AFTER you finish):**

| ID | Sample | Win Rate | Expectancy |
|----|--------|----------|------------|
| 21 | 99 | 43.4% | +0.166R |
| 22 | 95 | 38.9% | +0.212R |
| 23 | 95 | 36.8% | +0.308R |
| 25 | 87 | 52.9% | +0.198R |
| 28 | 86 | 43.0% | +0.170R |
| 29 | 86 | 39.5% | +0.257R |
| 30 | 83 | 33.7% | +0.221R |

---

## Questions for You

After you finish your calculations:

1. Do your results match ours within 0.001R tolerance?
2. If not, what's the root cause of the discrepancy?
3. Did you find any logic errors in the strategy specification?
4. Do you agree with the B-entry model (next open after break)?
5. Do you agree with the $8.40 friction assumption?
6. Do these strategies appear to have a statistical edge?
7. What would YOU recommend for next steps?

---

## Independent Review Protocol

**Step 1:** Read this document ONLY
**Step 2:** Write code from scratch (don't look at our code)
**Step 3:** Calculate all 7 strategies
**Step 4:** THEN compare to our results
**Step 5:** Report discrepancies
**Step 6:** Provide your independent assessment

**CRITICAL:** Don't read our code, validated_trades, or ADVANCED_BACKTEST_RESULTS.md until after you finish.

---

**Good luck, Fred. We need your fresh eyes.**

**Question:** Is everything we did WRONG?

---

**Contact:** Report results in a new markdown file: `FRED_VALIDATION_REPORT.md`
