# AUDIT - LOCKED ASSUMPTIONS (2026-01-25)

## Purpose
These assumptions are LOCKED and must be followed for all optimization, backtesting, and live trading. Any deviation requires re-audit.

---

## BATCH 1: Definitions & Invariants

### Risk Definition
- **Canonical R**: ORB edge → stop distance
  - For FULL mode UP break: risk = ORB_high - ORB_low (ORB size)
  - Used for consistent measurement across setups
  - Stored in daily_features.orb_XXXX_r_multiple

- **Real R**: Entry fill → stop distance
  - Includes slippage impact on entry price
  - Used for actual P&L calculations
  - Must implement via execution_metrics.py

- **BOTH must be tracked** in database and shown in apps

### Entry Trigger (Canonical)
- **First 1-min CLOSE outside ORB**
- Wait for candle to close beyond boundary
- Entry price = close price + slippage
- Matches build_daily_features.py lines 174-186
- Order type (market/limit) is execution model detail

### Trading Day Definition
- **09:00 local → next 09:00 local** (Australia/Brisbane, UTC+10)
- date_local in daily_features = Asia trading day start
- All ORBs from 09:00 to 00:30 belong to same trading day
- Example: date_local=2026-01-09 includes:
  - 0900 ORB: 2026-01-09 09:00-09:05
  - 1000 ORB: 2026-01-09 10:00-10:05
  - 2300 ORB: 2026-01-09 23:00-23:05
  - 0030 ORB: 2026-01-10 00:30-00:35 (next calendar day)

### No Outcome Trades
- **Count as LOSS (-1.0R)**
- If neither TP nor SL hit in scan window, assume position closed at loss
- Conservative assumption prevents false inflation of win rates

---

## BATCH 2: Data & Session Timing

### 0030 ORB Window
- **(D+1) 00:30:00 to 00:35:00 local time**
- For date_local=2026-01-09: 2026-01-10 00:30-00:35
- **DATABASE CURRENTLY HAS WRONG VALUES - MUST REBUILD**

### Scan Window (All ORBs)
- **ORB end → (D+1) 09:00 local**
- Example for 0030 ORB: (D+1) 00:35 to (D+1) 09:00 (8h 25m)
- Example for 1000 ORB: D 10:05 to (D+1) 09:00 (~23h)
- Consistent across all 6 ORBs
- Matches build_daily_features.py

### Data Quality Protocol
- **STOP if ORB values don't match bars_1m**
- Rebuild database before proceeding (Task #1)
- Current 2300/0030 results (84% WR) are INVALID
- Must verify all ORB calculations after rebuild

---

## BATCH 3: Execution & Fills

### Fill Price Simulation
- **Entry fill = close price + slippage**
- UP break: entry = close + 0.5 points
- DOWN break: entry = close - 0.5 points
- Assumes market order execution

### MGC Trading Costs (CORRECTED)
- Tick size: 0.1 points
- Tick value: $1.00
- **Point value: $10.00** (1 point = 10 ticks)
- Commission (round turn): $2.40-$3.00
- **Total cost per trade: $3.00** (use for conservative estimates)
- **NOT $6 as previously assumed!**

### Cost Accounting
- Methods are mathematically equivalent:
  - Cost_R = total_cost / (risk_points × point_value)
  - Example: $3 / (2.0 points × $10) = 0.15R
- Subtract from R-multiple: Outcome_R = raw_R - cost_R
- Verify execution_metrics.py implementation

### Same-Bar Resolution
- **Always LOSS (Conservative)**
- If TP and SL both hit in same bar, count as LOSS
- Matches build_daily_features.py line 252
- Most conservative assumption for backtesting

---

## BATCH 4: Outputs & Acceptance Tests

### Realistic Win Rate Ranges (Sanity Check)
| RR Value | Realistic WR Range | Breakeven WR |
|----------|-------------------|--------------|
| 1.5 | 50-65% | 40.0% |
| 2.0 | 45-60% | 33.3% |
| 3.0 | 30-45% | 25.0% |
| 4.0 | 23-35% | 20.0% |
| 6.0 | 15-25% | 14.3% |
| 8.0 | 10-15% | 11.1% |

**REJECT results exceeding these ranges**

### Verification Protocol (Execute in Order)
1. **Manual verification**: Pick 3-5 random trades, verify by hand
2. **Database comparison**: RR=1.0, FULL mode must match daily_features exactly
3. **Impossible statistics check**: Flag WR >80% for RR>4.0, avg R > RR/2, etc.
4. **Scan window check**: Ensure enough bars for high RR targets

### Red Flags (Automatic Rejection)
1. ❌ **Win rate impossibly high** (>70% for RR>4.0)
2. ❌ **ORB values don't match bars_1m**
3. ❌ **Too many NO_OUTCOME** (>30% of trades)
4. ❌ **Results unstable** (drastic changes with small parameter tweaks)

### Acceptance Criteria (ALL must pass for "ready to trade")
1. ✅ **Avg R > 0.15** after costs
2. ✅ **Win rate within realistic range** (see table above)
3. ✅ **Sample size > 100 trades**
4. ✅ **Execution verified**: Real R within 0.10R of canonical R

---

## Critical Issues Identified

### Issue 1: Database Corruption ❌
- **Problem**: 0030 ORB values in database don't match actual bars
  - Database: high=4442.0, low=4430.3
  - Actual: high=4504.2, low=4491.6 (from bars_1m)
- **Impact**: All 2300/0030 optimization results are INVALID
- **Fix**: Task #1 - Rebuild database
- **Blocker**: Cannot proceed with analysis until fixed

### Issue 2: Wrong Cost Assumptions ❌
- **Problem**: Optimization scripts used $6 total costs
- **Correct**: MGC costs are $3 per trade (round turn)
- **Impact**: All current results underestimate profitability by ~0.10R per trade
- **Fix**: Update scripts and re-run after database rebuild
- **Test**: Verify with execution_metrics.py

### Issue 3: Missing Primary Key ❌
- **Problem**: daily_features table has no primary key
- **Impact**: build_daily_features.py upsert fails
- **Fix**: Task #1 - Run pipeline/init_db.py to fix schema
- **Test**: Verify with `PRAGMA table_info(daily_features)`

### Issue 4: No Outcome Handling ⚠️
- **Problem**: Unclear how NO_OUTCOME trades were counted in current results
- **Correct**: Must count as LOSS (-1.0R)
- **Impact**: May have inflated win rates if counted as 0.0R or excluded
- **Fix**: Verify script logic, re-run if needed
- **Test**: Check NO_OUTCOME rate in results (should be <30%)

---

## Proposed Tests to Resolve Issues

### Test 1: Database Rebuild Verification
```bash
# Backup current
cp gold.db gold.db.backup_2026-01-25

# Rebuild
python pipeline/init_db.py
python backfill_databento_continuous.py 2024-01-01 2026-01-26

# Verify 0030 ORB for 2026-01-09
python -c "
import duckdb
conn = duckdb.connect('gold.db')
row = conn.execute('''
    SELECT orb_0030_high, orb_0030_low
    FROM daily_features
    WHERE instrument='MGC' AND date_local='2026-01-09'
''').fetchone()
print(f'0030 ORB: high={row[0]}, low={row[1]}')
# Expected: high=4504.2, low=4491.6
"
```

### Test 2: Manual Trade Verification
```python
# Pick random trade, verify all calculations by hand
# Compare to script results
# Document in verify_sample_trade.py
```

### Test 3: Cost Impact Analysis
```bash
# Re-run 1100 ORB with $3 costs (was $6)
# Compare results to current
# Expected: ~+0.10R improvement in avg R
```

### Test 4: NO_OUTCOME Rate Check
```bash
# For each ORB optimization, count:
# - WIN trades
# - LOSS trades
# - NO_OUTCOME trades (before counting as LOSS)
# Verify NO_OUTCOME < 30%
```

---

## Implementation Checklist

### Phase 1: Fix Database (CRITICAL - DO FIRST)
- [ ] Backup current database
- [ ] Run pipeline/init_db.py to fix schema
- [ ] Run backfill_databento_continuous.py 2024-01-01 2026-01-26
- [ ] Verify 0030 ORB values match bars_1m (Test 1)
- [ ] Verify primary key exists on daily_features

### Phase 2: Update Optimization Scripts
- [ ] Change cost from $6 to $3 in optimize_orb_canonical.py
- [ ] Verify NO_OUTCOME counted as LOSS (-1.0R)
- [ ] Add verification output (NO_OUTCOME count, cost_R breakdown)

### Phase 3: Re-run Optimizations
- [ ] Run all 6 ORBs with corrected costs and fixed database
- [ ] Execute verification protocol (Batch 4, step 2)
- [ ] Check all red flags (Batch 4, step 3)
- [ ] Manually verify 3-5 sample trades (Test 2)

### Phase 4: Integrate Execution Metrics
- [ ] Add execution_metrics.py to build_daily_features.py
- [ ] Update daily_features schema with real_risk, real_r_multiple columns
- [ ] Verify real R within 0.10R of canonical R
- [ ] Surface both metrics in trading apps

### Phase 5: Update validated_setups
- [ ] Only add setups passing ALL acceptance criteria
- [ ] Update trading_app/config.py
- [ ] Run python test_app_sync.py
- [ ] DO NOT PROCEED if sync test fails

---

## Sign-Off

These assumptions are LOCKED as of 2026-01-25 23:50 UTC+10.

Any changes require:
1. User approval
2. Re-audit of affected components
3. Re-verification of results
4. Update to this document

**DO NOT trade any setup until database is rebuilt and results re-verified!**
