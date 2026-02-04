# Entry Logic - Single Source of Truth

**Last Updated:** 2026-02-04
**Purpose:** Define canonical entry detection rules for ORB strategy

---

## Canonical Entry Rule: "1st Close Outside"

### Definition

Entry is triggered on the **first 1-minute bar that CLOSES outside the ORB range**.

```
IF bar.close > orb_high THEN direction = LONG
IF bar.close < orb_low  THEN direction = SHORT
```

### Key Invariants

1. **CLOSE, not touch** - Price must CLOSE outside, not just touch/wick outside
2. **1-minute bars** - Detection uses 1m closes (bars_1m), not 5m
3. **After ORB window** - Entry can only occur AFTER ORB window ends
4. **No lookahead** - Entry timestamp >= confirmation bar timestamp

### Implementation Locations

| File | Function | Purpose |
|------|----------|---------|
| `strategies/execution_engine.py` | `simulate_orb_trade()` | Backtesting engine (CANONICAL) |
| `trading_app/entry_rules.py` | `compute_1st_close_outside()` | Live entry detection |
| `pipeline/build_daily_features.py` | (implicit) | RR=1.0 outcome calculation |

### Consistency Requirements

All three implementations MUST:
- Use the same close > high / close < low logic
- Respect the same ORB window timing
- Produce identical results for the same input data

### CI Guard

`scripts/check/check_entry_logic_consistency.py` verifies:
- All implementations use CLOSE (not high/low touch)
- All implementations check > / < (not >= / <=)
- No hardcoded edge cases that differ between files

---

## Entry Rule Variants

| Rule | Confirmation | Entry Price |
|------|--------------|-------------|
| `limit_at_orb` | Limit order at ORB edge | ORB edge price |
| `1st_close_outside` | First 1m close outside | Next bar open |
| `5m_close_outside` | First 5m close outside | Next bar open |

---

## Forbidden Modifications

Changes to entry logic require:
1. Authorization file (`canofix_*.txt`)
2. Update ALL three implementation locations
3. Update this document
4. Pass consistency tests
