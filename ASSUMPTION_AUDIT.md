# ASSUMPTION AUDIT: Treat Everything as FALSE Until Proven
**Date: 2026-01-28**
**Directive: Assume timezone, RR, everything is wrong until verified from scratch**

---

## SUSPECT AREAS (Ordered by Risk)

### 🚨 CRITICAL: Data Alignment & Timing

#### 1. Timezone Handling
**Assumption:** Australia/Brisbane (UTC+10) correctly maps trading day windows
**Risk:** ORB windows could be off by hours, completely invalidating all results
**To Verify:**
- [ ] Check actual bar timestamps match expected ORB windows
- [ ] Verify 0900 ORB is REALLY 0900 local (23:00 UTC previous day)
- [ ] Verify 1000 ORB is REALLY 1000 local (00:00 UTC)
- [ ] Check for DST issues (Brisbane has NO DST, but data source might)
- [ ] Validate session windows (Asia/London/NY) align with actual trading hours

#### 2. Look-Ahead Bias
**Assumption:** Entry is NEXT 1m OPEN after signal bar CLOSE (B-entry model)
**Risk:** Could be accidentally using future data (signal bar close = entry, not next open)
**To Verify:**
- [ ] Trace execution_engine.py logic step-by-step
- [ ] Check if entry_price comes from signal bar or next bar
- [ ] Verify we're NOT using ORB bar close as entry (that's A-entry, not B-entry)
- [ ] Confirm break detection happens BEFORE entry price is set

#### 3. Bar Alignment
**Assumption:** 5m bars aggregate correctly from 1m bars
**Risk:** Bucket boundaries could be wrong, causing misalignment
**To Verify:**
- [ ] Check 5m aggregation logic in build_bars_5m.py
- [ ] Verify floor(epoch/300)*300 correctly buckets bars
- [ ] Confirm no off-by-one errors in bar windows

---

### 🚨 CRITICAL: R-Multiple Calculations

#### 4. Realized RR Formula
**Assumption:** Using cost_model.py formulas correctly
**Risk:** Formula could be wrong, over/under-stating R-multiples
**To Verify:**
- [ ] Hand-calculate 5 random trades manually
- [ ] Check: realized_rr = (exit - entry - friction) / (entry - stop + friction)
- [ ] Verify friction is $8.40 RT (not $4.20 one-way)
- [ ] Confirm point_value = $10 for MGC
- [ ] Check for sign errors (long vs short direction)

#### 5. Win/Loss Classification
**Assumption:** outcome='WIN' when realized_rr > 0, 'LOSS' when < 0
**Risk:** Could be misclassifying breakeven or partial fills
**To Verify:**
- [ ] Check outcome logic in execution_engine.py
- [ ] Verify what happens if exit_price == entry_price (breakeven)
- [ ] Confirm NO_TRADE only for no ORB break
- [ ] Check RISK_TOO_SMALL only for TCA gate failures

#### 6. MAE/MFE Tracking
**Assumption:** MAE/MFE calculated correctly from intrabar excursions
**Risk:** Could be using wrong reference point (entry vs ORB edge)
**To Verify:**
- [ ] Check MAE/MFE logic in execution_engine.py
- [ ] Verify denominator is (entry - stop), NOT ORB size
- [ ] Confirm using 1m bars for intrabar tracking

---

### 🚨 CRITICAL: Entry/Exit Logic

#### 7. ORB Break Detection
**Assumption:** Break detected when 1m CLOSE outside ORB range
**Risk:** Could be using HIGH/LOW touch instead of close (changes results dramatically)
**To Verify:**
- [ ] Check break_detection.py logic
- [ ] Confirm using CLOSE, not high/low
- [ ] Verify confirm_bars=1 means FIRST close outside range
- [ ] Check NO double-counting (only one entry per day)

#### 8. Stop Loss Placement
**Assumption:** sl_mode='full' uses ORB edge, 'half' uses midpoint
**Risk:** Could be placing stops incorrectly
**To Verify:**
- [ ] Check stop_price calculation in execution_engine.py
- [ ] Verify full mode: stop = orb_high (short) or orb_low (long)
- [ ] Verify half mode: stop = (orb_high + orb_low) / 2
- [ ] Confirm NO buffer ticks added (config shows 0.0)

#### 9. Target Placement
**Assumption:** target_price = entry +/- (RR × risk_points)
**Risk:** Could be calculating target wrong (RR applied to wrong base)
**To Verify:**
- [ ] Check target_price formula
- [ ] Verify risk_points = |entry - stop|
- [ ] Confirm target_points = RR × risk_points
- [ ] Check direction (long: entry + target_points, short: entry - target_points)

---

### ⚠️ HIGH RISK: Data Quality

#### 10. Contract Stitching
**Assumption:** Databento continuous front month selection is correct
**Risk:** Could be using wrong contracts, causing bad stitching
**To Verify:**
- [ ] Check backfill_databento_continuous.py logic
- [ ] Verify front month selection (highest volume, no spreads)
- [ ] Check for roll date gaps or overlaps
- [ ] Confirm source_symbol matches expected contracts

#### 11. Missing Bars
**Assumption:** Holidays/weekends handled correctly (NULL ORBs)
**Risk:** Could be forward-filling or creating phantom bars
**To Verify:**
- [ ] Check for weekend bars in bars_1m
- [ ] Verify holiday handling (should have NO bars)
- [ ] Confirm daily_features has NULL for missing ORBs
- [ ] Check validated_trades doesn't create trades on no-data days

#### 12. Duplicate Bars
**Assumption:** No duplicate timestamps in bars_1m
**Risk:** Duplicates could corrupt aggregations
**To Verify:**
- [ ] Query for duplicate (symbol, ts_utc) in bars_1m
- [ ] Check UPSERT logic prevents duplicates
- [ ] Verify bars_5m has no duplicates

---

### ⚠️ HIGH RISK: Cost Modeling

#### 13. Friction Amount
**Assumption:** $8.40 RT is correct for MGC (commission + spread + slippage)
**Risk:** Could be over/under-stating costs
**To Verify:**
- [ ] Check COST_MODEL_MGC_TRADOVATE.txt source
- [ ] Verify $2.40 commission (Tradovate actual rate)
- [ ] Verify $2.00 spread (2 ticks × $1 × 2 crossings)
- [ ] Verify $4.00 slippage (conservative estimate)
- [ ] Compare to actual live trading costs

#### 14. TCA Gate (20% Cap)
**Assumption:** Rejecting trades where friction > 20% of risk is correct
**Risk:** Threshold could be too strict/loose
**To Verify:**
- [ ] Check TCA.txt methodology
- [ ] Verify MIN_RISK_DOLLARS = $50.00 is reasonable
- [ ] Calculate: at $50 risk, $8.40 = 16.8% (PASSES gate)
- [ ] Check if any trades incorrectly filtered/passed

---

### ⚠️ MEDIUM RISK: Statistical Validity

#### 15. Sample Size
**Assumption:** n >= 30 is sufficient for significance
**Risk:** Could have selection bias or regime dependency
**To Verify:**
- [ ] Check if 30 trades span sufficient time periods
- [ ] Verify not concentrated in single regime
- [ ] Check for autocorrelation (clustered wins/losses)
- [ ] Run permutation tests for statistical significance

#### 16. Walk-Forward Robustness
**Assumption:** Edge holds across time periods
**Risk:** Could be overfit to recent data
**To Verify:**
- [ ] Split data into train/test windows
- [ ] Check if expectancy holds in out-of-sample periods
- [ ] Verify no degradation over time
- [ ] Test on different year subsets

#### 17. Monte Carlo Validation
**Assumption:** Win sequence isn't lucky
**Risk:** Could have gotten favorable trade sequence by chance
**To Verify:**
- [ ] Randomize trade sequence 10,000 times
- [ ] Check if actual expectancy falls within 95% confidence interval
- [ ] Verify drawdown distribution is realistic
- [ ] Test for significant p-value

---

### 🔍 LOW RISK: Edge Cases

#### 18. Boundary Conditions
**Assumption:** Edge cases handled correctly
**Risk:** Rare scenarios could corrupt small % of trades
**To Verify:**
- [ ] Check ORB size = 0 (no range)
- [ ] Check entry = stop (zero risk)
- [ ] Check target = entry (zero reward)
- [ ] Check gap opens (entry far from ORB)

#### 19. Rounding Errors
**Assumption:** Price precision is correct
**Risk:** Rounding could accumulate errors
**To Verify:**
- [ ] Check MGC tick size (0.1 points = $1.00)
- [ ] Verify prices rounded to 1 decimal
- [ ] Check for floating point precision issues

---

## VERIFICATION FRAMEWORK

### Phase 1: Ground Truth Validation (MANUAL)
**Goal:** Hand-verify 10 random trades end-to-end
**Method:**
1. Pick 10 random dates from validated_trades
2. For each trade:
   - Load raw 1m bars for that day
   - Manually identify ORB window (5 bars)
   - Manually detect break (first close outside range)
   - Manually calculate entry (next open)
   - Manually calculate stop (ORB edge)
   - Manually calculate target (entry +/- RR × risk)
   - Manually find exit (target/stop hit)
   - Manually calculate realized_rr
   - Compare to database values
3. If ANY discrepancy: STOP and fix

### Phase 2: Systematic Edge Case Testing
**Goal:** Test boundary conditions programmatically
**Tests:**
- [ ] Zero-range ORBs
- [ ] Gap opens (entry >> ORB edge)
- [ ] Immediate stop outs (first bar after entry)
- [ ] Never-resolved trades (target/stop never hit)
- [ ] End-of-day exits (still open at 16:30)

### Phase 3: Look-Ahead Bias Detection
**Goal:** Prove we're NOT using future data
**Method:**
1. Run backtest with only data BEFORE each trade date
2. Compare results to current (should be identical)
3. If different: LOOK-AHEAD BIAS DETECTED

### Phase 4: Walk-Forward Analysis
**Goal:** Prove edge holds out-of-sample
**Method:**
1. Split into 6-month windows
2. Train on window N, test on window N+1
3. Record expectancy per window
4. Check for degradation over time

### Phase 5: Monte Carlo Simulation
**Goal:** Prove win sequence isn't lucky
**Method:**
1. Take actual trade outcomes
2. Randomize sequence 10,000 times
3. Calculate expectancy distribution
4. Verify actual result within 95% CI

### Phase 6: Robustness Tests
**Goal:** Prove edge isn't overfit
**Tests:**
- [ ] Cost sensitivity: Test at +25%, +50%, +100% costs
- [ ] RR sensitivity: Test RR ± 0.5 targets
- [ ] Time sensitivity: Test ORB window ± 5 minutes
- [ ] Threshold sensitivity: Test entry threshold variations

### Phase 7: Fresh Eyes Review (Fred)
**Goal:** Get independent validation
**Method:**
1. Provide Fred with:
   - Raw data (bars_1m)
   - Strategy description
   - NO results or expectations
2. Fred independently:
   - Implements same logic from scratch
   - Calculates expectancy
   - Compares to our results
3. If discrepancy: AUDIT THE DIFFERENCE

---

## NEXT STEPS

1. **Immediate:** Build Phase 1 ground truth validator (hand-check 10 trades)
2. **Then:** Build automated test suite for Phases 2-6
3. **Finally:** Invite Fred to independently validate

**Until ALL phases pass: TREAT ALL RESULTS AS SUSPECT**

---

## FILES TO AUDIT (Priority Order)

### CRITICAL PATH:
1. `pipeline/build_daily_features.py` - ORB calculation
2. `strategies/execution_engine.py` - Entry/exit logic
3. `pipeline/cost_model.py` - R-multiple formulas
4. `pipeline/populate_validated_trades_with_filter.py` - Trade generation
5. `pipeline/backfill_databento_continuous.py` - Data stitching

### SUPPORTING:
6. `strategies/break_detection.py` - Signal logic
7. `pipeline/build_bars_5m.py` - Aggregation
8. `trading_app/config.py` - Parameters
9. `pipeline/schema_validated_trades.sql` - Data model

---

**Status: ASSUMPTION AUDIT COMPLETE**
**Next: BUILD VERIFICATION FRAMEWORK**
