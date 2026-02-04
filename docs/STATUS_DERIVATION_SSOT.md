# Status Derivation - Single Source of Truth

**Last Updated:** 2026-02-04
**Purpose:** Define how strategy status MUST be derived, not stored

---

## The Rule

> **Status MUST be derived from expected_r and sample_size, never stored as source of truth.**

The `status` column in `validated_setups` exists for query convenience, but the **actual status** is always computed from the underlying metrics.

---

## Derivation Logic

```python
def derive_status(expected_r: float, sample_size: int, has_data: bool = True) -> str:
    """
    Derive strategy status from metrics.

    This is the CANONICAL derivation logic.
    """
    if not has_data:
        return 'INVALID_NO_DATA'

    if expected_r is None or sample_size is None:
        return 'INVALID_NO_DATA'

    # Approval thresholds (from CLAUDE.md)
    MIN_EXPECTED_R = 0.15  # Must have positive edge at $8.40 friction
    MIN_SAMPLE_SIZE = 30   # Statistical significance

    if expected_r >= MIN_EXPECTED_R and sample_size >= MIN_SAMPLE_SIZE:
        return 'ACTIVE'
    else:
        return 'REJECTED'
```

---

## Status Values

| Status | Meaning | Derivation |
|--------|---------|------------|
| `ACTIVE` | Production-ready | expected_r >= 0.15 AND sample_size >= 30 |
| `REJECTED` | Does not meet criteria | expected_r < 0.15 OR sample_size < 30 |
| `RETIRED` | Manually archived | Historical, no longer traded |
| `INVALID_NO_DATA` | Cannot compute | Missing expected_r or sample_size |

---

## Consistency Rule

The stored `status` column MUST match what `derive_status()` would compute.

**CI Guard:** `scripts/check/check_status_derivation.py`
- Reads all rows from validated_setups
- Computes derived status from expected_r and sample_size
- Flags any mismatch between stored and derived

---

## Why This Matters

**Bug scenario without derivation:**
1. Strategy added with expected_r = 0.20, status = 'ACTIVE'
2. Costs updated, expected_r recalculated to 0.10
3. Status NOT updated (still 'ACTIVE')
4. App uses bad strategy in production

**With derivation guard:**
- Guard detects mismatch: stored='ACTIVE' but derived='REJECTED'
- Build fails, forcing fix before deployment

---

## Implementation

**Derivation helper:** `trading_app/status_utils.py`
- Single source for `derive_status()` function
- Used by guard and any code that needs to check status

**CI guard:** `scripts/check/check_status_derivation.py`
- Runs in preflight
- Compares stored vs derived for all rows
- Fails if any mismatch found

---

## Transition Plan

1. **Phase 1 (Current):** Add guard that WARNS on mismatch
2. **Phase 2 (Future):** Guard FAILS on mismatch
3. **Phase 3 (Future):** Remove stored status, always derive

Currently in Phase 1 - guard warns but doesn't block.
