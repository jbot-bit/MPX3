# TRADING LOGIC PRINCIPLES
**Source: note.txt with institutional validation**
**Purpose: Guide edge discovery, strategy development, and filter optimization**

---

## 1. RR vs Expectancy (CRITICAL DISTINCTION)

**RR (Reward:Risk Target)** = Trade structure / payoff shape
- Example: RR=2.0 means win +2R, lose -1R
- This is the SETUP, not the OUTCOME

**Expectancy (Avg Net R)** = Edge quality / average outcome
- Example: +0.20R expectancy means avg +0.20R per trade after costs
- This is the RESULT, not the structure

**They are NOT interchangeable.**

A strategy with 2R targets can have:
- -0.10R expectancy (bad)
- +0.05R expectancy (meh)
- +0.25R expectancy (EXCELLENT)

**NEVER confuse these.** "2R expectancy" is a retail myth.

---

## 2. Professional Expectancy Ranges

**After friction, after TCA, after reality:**

| Range | Classification | Status |
|-------|----------------|--------|
| +0.02R to +0.05R | Viable but fragile | Proceed with caution |
| +0.05R to +0.10R | Decent edge | Good |
| +0.10R to +0.20R | Strong edge | Very good |
| +0.20R to +0.30R | Exceptional | Elite |
| > +0.30R | Rare / regime-dependent | Usually overfit |

**Current results: +0.166R to +0.308R = ALLOCATOR-GRADE ALPHA**

**Institutional validation:**
- "Forecast-to-Fill" gold strategy (Sharpe 2.88) had 1.5R structure with 65.8% WR
- Expectancy per active day: ~+2.58 basis points
- Our results align with institutional benchmarks

---

## 3. Why +2R Expectancy is Wrong

If expectancy were +2R:
- You'd double risk every trade
- Win rate could be ~30% and still explode equity
- Funds would arbitrage it away instantly
- Slippage alone would destroy it in live trading

**Reality:**
- +0.1R is already elite
- +0.2R is outstanding
- Anything above that is usually:
  - Overfit
  - Short-lived
  - Or hiding unaccounted risk

---

## 4. The Expectancy Formula

```
Gross Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
Net Expectancy = Gross Expectancy - Friction
```

**Example:**
- RR = 2.0 (structure)
- Win rate = 41%
- Loss rate = 59%
- Gross: (0.41 × 2.0) - (0.59 × 1.0) = +0.23R
- Friction: ~0.17R
- Net expectancy: +0.06R

**That's a real, tradeable edge.**

---

## 5. How Filters Add Edge

**Filters do NOT add edge linearly.** They do THREE things:

1. **Remove high-friction trades** (TCA gate removes mathematically insolvent trades)
2. **Increase conditional win rate** (trade only in favorable regimes)
3. **Reduce variance** (lower drawdowns, smoother equity curve)

**Typical realistic gains:**
- +0.05R to +0.10R → good filter
- +0.10R to +0.15R → excellent filter
- > +0.15R → rare / high risk of overfit

**What TCA filter did:**
- Didn't "optimize"
- Just removed mathematically insolvent trades (Cost > 20% of Risk)
- Result: +0.2R swing in expectancy
- **That's why it felt like a breakthrough**

---

## 6. The Layered Edge Model (LOCK THIS IN)

Think in LAYERS, not absolute thresholds:

```
Layer 1: Raw Structure
  → Often -0.2R to 0.0R (because friction eats profit)

Layer 2: Risk Viability Gate (TCA)
  → Removes "dead" trades where Cost > Edge
  → Can flip expectancy from negative to positive
  → "Safety Valve" for cost constraints

Layer 3: Filters (Time/Vol/Regime)
  → Add +0.05R to +0.15R
  → Align with favorable market conditions
  → "Trading less earns more" (avoid choppy sessions)

Layer 4: Execution Improvements
  → Smaller incremental gains
  → "Free Trade" scaling, active management
```

**CRITICAL INSIGHT:**
> If you demand +0.2R BEFORE filters, you'll kill everything.

Raw structure is often NEGATIVE. That's NORMAL.

TCA gate removes dead trades → flips expectancy positive.

Filters refine further → add final +0.05R to +0.15R.

**This is the correct model. Don't fight it.**

---

## 7. Session-Specific Edges

**"Trading less can mean earning more"** - MQL5 Session Trading

Some sessions have NO edge:
- **Asia session**: Often choppy, low conviction
- **1100 ORB**: Despite 63.9% TCA pass rate, ALL variants REJECTED (no structural edge)
- **1800 ORB**: ALL variants REJECTED (negative expectancy)

**Some sessions have STRONG edges:**
- **0900 ORB**: ALL 4 RR variants APPROVED (+0.170R to +0.257R)
- **1000 ORB**: 3/4 variants APPROVED (+0.166R to +0.308R, RR >= 2.0 only)

**Don't force edges where none exist.** Abandon sessions that fail consistently.

---

## 8. The Honesty Gap

**Theoretical vs Realized R:**

Even if you structure a trade as 2:1 (Reward:Risk):
- Friction DECREASES the numerator (win payout)
- Friction INCREASES the denominator (loss cost)
- Realized R is ALWAYS lower than theoretical

**Formula:**
```
Realized R = (Target - Entry) - Costs
            -------------------------
             (Entry - Stop) + Costs
```

**Example (MGC):**
- Theoretical: 2.0R
- After $8.40 friction: ~1.6R or lower
- Win rate needs to compensate for this gap

---

## 9. When Strategies Fail After TCA

If strategies still FAIL after TCA gate:
- **NOT a cost model issue**
- Professional risk management in action
- The strategy lacks structural edge
- Solutions:
  - Try different filters
  - Try different timing (sessions/regimes)
  - Or abandon the approach entirely

**HONESTY OVER OUTCOME.**

If it doesn't work, it doesn't work. Accept it and move on.

---

## 10. Edge Discovery Guidelines

**When searching for new edges:**

1. **Start with raw structure** - Don't expect positive expectancy yet
2. **Apply TCA gate** - Remove mathematically insolvent trades (Cost > 20% Risk)
3. **Add filters incrementally** - Time, volatility, regime
4. **Measure gains per layer** - Each layer should add +0.05R to +0.15R
5. **Accept reality** - If final expectancy < +0.05R after all filters, ABANDON

**Don't demand:**
- +0.15R before any filters (too strict)
- +0.20R after filters (unrealistic)
- Edge in ALL sessions (some have none)

**Do demand:**
- +0.05R minimum after TCA + filters (viability threshold)
- +0.15R for PRODUCTION deployment (professional threshold)
- Statistical significance (n >= 30 resolved trades)

---

## 11. Current Validation Results

**APPROVED (>= +0.15R):**
- 0900 ORB: 4/4 variants (+0.170R to +0.257R) - ALL approved
- 1000 ORB: 3/4 variants (+0.166R to +0.308R) - RR >= 2.0 only

**REJECTED (< +0.15R):**
- 1000 RR=1.5: +0.098R (marginal, needs filter work)
- 1100 ORB: ALL 4 variants (no structural edge)
- 1800 ORB: ALL 4 variants (no structural edge)

**Insights:**
- **0900 ORB is EXCELLENT** - consistent edge across all RR variants
- **1000 ORB is STRONG** - higher RR variants work best
- **1100/1800 ORBs FAIL** - lack structural edge despite good TCA pass rates
- Solution: Focus on 0900/1000 ORBs, abandon or rework 1100/1800

---

## 12. Key Takeaways

1. RR ≠ Expectancy (structure ≠ outcome)
2. +0.15R to +0.30R is elite professional performance
3. Layered model is correct: Raw → TCA → Filters → Execution
4. Filters add +0.05R to +0.15R, not miracles
5. Some sessions have no edge - accept and move on
6. Honesty over outcome - if it fails, it fails
7. Current results are EXCEPTIONAL by institutional standards

**Use these principles for ALL future edge discovery and strategy development.**

---

**Last Updated: 2026-01-28**
**Validation: 17 MGC strategies tested with TCA gate**
**Sources: note.txt, institutional gold strategy benchmarks, quantitative frameworks**
