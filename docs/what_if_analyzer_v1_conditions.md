# What-If Analyzer - V1 Deterministic Conditions

**Date:** 2026-01-28
**Status:** V1 Scope Locked

---

## Overview

The What-If Analyzer V1 supports 4 deterministic condition types for testing against historical data. All conditions are pre-trade evaluable and require no semantic interpretation.

---

## Condition Types

### 1. ORB Size Threshold (Normalized)

**Purpose:** Filter for volatility expansion or compression

**Logic:**
```
orb_size / atr_20 >= min_threshold
orb_size / atr_20 <= max_threshold
```

**Examples:**
- "Only trade if ORB >= 0.5 ATR" (expansion filter)
- "Only trade if ORB <= 0.3 ATR" (compression filter)
- "Only trade if 0.4 <= ORB <= 0.8 ATR" (sweet spot)

**Pre-trade Status:** ✅ Evaluable (ORB forms before entry)

**Data Source:** `daily_features.orb_XXXX_size`, `daily_features.atr_20`

---

### 2. Pre-Session Travel Filter

**Purpose:** Avoid trading after major moves (mean reversion risk)

**Logic:**
```
pre_orb_travel / atr_20 < max_threshold
```

**Examples:**
- "Only trade if Asia travel < 2.5 ATR"
- "Only trade if pre-ORB travel < 1.0 ATR"

**Pre-trade Status:** ✅ Evaluable (travel known before ORB forms)

**Data Source:** `daily_features.pre_orb_travel`, `daily_features.atr_20`

---

### 3. Session Type Filter

**Purpose:** Filter for specific market regimes

**Logic:**
```
asia_type IN allowed_types
london_type IN allowed_types
```

**Session Types:**
- `QUIET`: Low volatility, compressed range
- `CHOPPY`: Bidirectional, no clear trend
- `TRENDING`: Sustained directional move

**Examples:**
- "Only trade if Asia = QUIET" (calm before storm)
- "Only trade if London = TRENDING" (momentum continuation)
- "Only trade if Asia != CHOPPY" (avoid whipsaw)

**Pre-trade Status:** ✅ Evaluable (session type determined before ORB)

**Data Source:** `daily_features.asia_type`, `daily_features.london_type`, `daily_features.ny_type`

---

### 4. Range Percentile Filter

**Purpose:** Filter for compressed ranges (spring-loading effect)

**Logic:**
```
percentile_rank(orb_size, recent_N_days) < threshold
```

**Examples:**
- "Only trade if ORB in bottom 25% of recent 20 days" (compression)
- "Only trade if ORB in top 10% of recent 30 days" (expansion breakout)

**Pre-trade Status:** ✅ Evaluable (compares to historical distribution)

**Data Source:** `daily_features.orb_XXXX_size` (rolling window calculation)

---

## Deterministic Guarantee

All V1 conditions are:
- ✅ **Numerical/categorical** (no semantic interpretation)
- ✅ **Deterministic** (same inputs → same outputs)
- ✅ **Pre-trade evaluable** (no look-ahead bias)
- ✅ **Cacheable** (keyed by condition hash + data version)
- ✅ **Reproducible** (snapshots can be re-run identically)

---

## Deferred to V2+ (NOT in V1)

- ❌ News/event filters (semantic)
- ❌ Pattern recognition (requires NLP)
- ❌ Correlation with other instruments (cross-asset intelligence)
- ❌ Time-of-day gradients (intraday microstructure)
- ❌ Liquidity conditions (order book analysis)

---

## Data Availability

All V1 conditions use existing `daily_features` columns:

| Condition | Required Columns |
|-----------|------------------|
| ORB Size | `orb_XXXX_size`, `atr_20` |
| Pre-Travel | `pre_orb_travel`, `atr_20` |
| Session Type | `asia_type`, `london_type`, `ny_type` |
| Range Percentile | `orb_XXXX_size` (historical) |

**No new data collection required.**

---

## Next Steps

- **Task 1:** Build query engine supporting these 4 condition types
- **Task 2:** Add snapshot persistence for reproducibility
- **Task 3:** Add UI panel for interactive testing
- **Task 4:** Enable promotion to validation pipeline
- **Task 5:** Enforce conditions as live trading gates
