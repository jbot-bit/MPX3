# Daily Features Schema Reference (SSOT)

**Last Updated:** 2026-02-04
**Purpose:** Single Source of Truth for daily_features column classification

---

## Column Classification System

| Type | Description | Usage Rules |
|------|-------------|-------------|
| **FACT** | Raw measurements from market data | Safe to use anywhere |
| **DERIVED_RR1** | Computed outcomes at RR=1.0 only | Only valid for RR=1.0 analysis |
| **LEGACY** | Deprecated columns for backwards compatibility | DO NOT USE in new code |

---

## ORB Columns (per ORB time: 0900, 1000, 1100, 1800, 2300, 0030)

### FACT Columns (Safe)

| Column | Type | Description |
|--------|------|-------------|
| `orb_XXXX_high` | DOUBLE | ORB high price (raw measurement) |
| `orb_XXXX_low` | DOUBLE | ORB low price (raw measurement) |
| `orb_XXXX_size` | DOUBLE | ORB range in points (high - low) |
| `orb_XXXX_break_dir` | VARCHAR | Break direction: UP, DOWN, NONE |
| `orb_XXXX_mae` | DOUBLE | Max Adverse Excursion (raw measurement) |
| `orb_XXXX_mfe` | DOUBLE | Max Favorable Excursion (raw measurement) |
| `orb_XXXX_stop_price` | DOUBLE | Stop price level |
| `orb_XXXX_risk_ticks` | INTEGER | Risk in ticks |

### DERIVED_RR1 Columns (RR=1.0 Specific)

| Column | Type | Description |
|--------|------|-------------|
| `orb_XXXX_outcome_rr1` | VARCHAR | Outcome at RR=1.0: WIN, LOSS, NO_TRADE |
| `orb_XXXX_r_multiple_rr1` | DOUBLE | R-multiple at RR=1.0 (~+1.0 or ~-1.0) |

### LEGACY Columns (DEPRECATED)

| Column | Type | Status |
|--------|------|--------|
| `orb_XXXX_outcome` | VARCHAR | DEPRECATED - Use `*_rr1` or StrategyDiscovery |
| `orb_XXXX_r_multiple` | DOUBLE | DEPRECATED - Use `*_rr1` or StrategyDiscovery |

---

## Critical Rules

### 1. For RR=1.0 Analysis
Use `orb_XXXX_outcome_rr1` and `orb_XXXX_r_multiple_rr1` columns directly.

### 2. For RR > 1.0 Analysis (RR=2.0, 3.0, 4.0, etc.)
**DO NOT use daily_features outcome columns.**

Use StrategyDiscovery (canonical):
```python
from trading_app.strategy_discovery import StrategyDiscovery, DiscoveryConfig

discovery = StrategyDiscovery()
config = DiscoveryConfig(
    instrument='MGC',
    orb_time='0900',
    rr=4.0,  # Your target RR
    sl_mode='HALF',
    orb_size_filter=None
)
result = discovery.backtest_configuration(config)
# result.avg_r is the correct ExpR at RR=4.0
```

### 3. Legacy Columns
- Exist ONLY for backwards compatibility with `trading_app/` code
- Accessed via `daily_features_compat` VIEW
- **New code MUST NOT reference these columns directly**
- CI guard will FAIL builds that use legacy columns

---

## Compatibility View

A read-only view `daily_features_compat` maps legacy names to RR1 columns:

```sql
CREATE VIEW daily_features_compat AS
SELECT
    *,
    orb_0900_outcome_rr1 AS orb_0900_outcome,
    orb_0900_r_multiple_rr1 AS orb_0900_r_multiple,
    -- ... (all ORB times)
FROM daily_features;
```

This allows `trading_app/` to continue working without code changes.

---

## Why This Matters

**Bug found 2026-02-04:** Validation scripts read WIN/LOSS outcomes from daily_features
(calculated at RR=1.0) and incorrectly applied RR=4.0 multipliers, inflating ExpR
from +0.08R to +0.55R (7x inflation).

**The fix:** Make RR explicit in column names. No more ambiguity.

---

## Enforcement

CI guard: `scripts/check/check_rr1_column_misuse.py`
- FAILS if legacy column names used in new code
- Allowlist: `trading_app/*` (uses compat view)
