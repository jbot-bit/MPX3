# Database Schema - Source of Truth

**Last Updated:** 2026-01-18 (merged multi-instrument guide)

## VERIFIED TABLES (Source of Truth)

These tables contain VERIFIED backtest results that match config.py:

### 1. `daily_features_v2_half` (MGC HALF SL mode)
- **Purpose:** Daily ORB features with HALF stop loss mode
- **Used by:** `v_orb_trades_half` view
- **Verified:** YES - matches config.py performance numbers
- **Slippage:** NO (perfect fills)
- **Columns:** date_local, orb_XXXX_high/low/size/break_dir/outcome/r_multiple/mae/mfe/stop_price/risk_ticks
- **ORB Times:** 0900, 1000, 1100, 1800, 2300, 0030

### 2. `v_orb_trades_half` (VIEW)
- **Purpose:** Clean view of all ORB trades from daily_features_v2_half
- **Source:** Reads from daily_features_v2_half
- **Usage:** Query this for MGC backtest results
- **Example:**
  ```sql
  SELECT orb_time, COUNT(*) as trades,
         AVG(CASE WHEN outcome='WIN' THEN 1.0 ELSE 0.0 END) as win_rate,
         AVG(r_multiple) as avg_r
  FROM v_orb_trades_half
  WHERE instrument='MGC' AND outcome IN ('WIN','LOSS')
  GROUP BY orb_time;
  ```

### 3. `daily_features_v2_nq` (NQ instrument)
- **Purpose:** Daily ORB features for NQ (Micro Nasdaq)
- **Verified:** YES
- **Same structure as daily_features_v2_half**

### 4. `daily_features_v2_mpl` (MPL instrument)
- **Purpose:** Daily ORB features for MPL (Micro Platinum)
- **Verified:** YES (2026-01-15)
- **Same structure as daily_features_v2_half**

## ARCHIVED TABLES (Do Not Use)

These tables were from experimental parameter testing and have been archived:

- `_archive_orb_trades_1m_exec` - 1-minute execution tests (outdated)
- `_archive_orb_trades_1m_exec_nofilters` - 1-minute without filters
- `_archive_orb_trades_5m_exec` - 5-minute execution tests (WRONG NUMBERS)
- `_archive_orb_trades_5m_exec_nofilters` - 5-minute without filters
- `_archive_orb_trades_5m_exec_nomax` - 5-minute without max filters
- `_archive_orb_trades_5m_exec_orbr` - 5-minute ORB range tests

**DO NOT QUERY THESE TABLES** - they contain outdated methodology and incorrect parameters.

## RAW DATA TABLES (Do Not Modify)

### Bars (1-minute and 5-minute)
- `bars_1m` - MGC 1-minute bars
- `bars_1m_nq` - NQ 1-minute bars
- `bars_1m_mpl` - MPL 1-minute bars
- `bars_5m` - MGC 5-minute bars (aggregated from bars_1m)
- `bars_5m_nq` - NQ 5-minute bars
- `bars_5m_mpl` - MPL 5-minute bars

## Config.py Performance Numbers

The numbers in `config.py` come from `daily_features_v2_half`:

```python
MGC_ORB_CONFIGS = {
    "0900": {"rr": 1.0, "sl_mode": "FULL", "tier": "DAY"},  # +0.431R
    "1000": {"rr": 3.0, "sl_mode": "FULL", "tier": "DAY"},  # +0.342R
    "1100": {"rr": 1.0, "sl_mode": "FULL", "tier": "DAY"},  # +0.449R
    "1800": {"rr": 1.0, "sl_mode": "HALF", "tier": "DAY"},  # +0.425R
    "2300": {"rr": 1.0, "sl_mode": "HALF", "tier": "NIGHT"}, # +0.387R ✓ VERIFIED
    "0030": {"rr": 1.0, "sl_mode": "HALF", "tier": "NIGHT"}, # +0.231R
}
```

**VERIFIED EXAMPLE (MGC 2300 ORB):**
- Source: `v_orb_trades_half`
- Win Rate: 69.3%
- Avg R: +0.387R (NO slippage)
- With 1 tick slippage: +0.261R
- With 2 tick slippage: +0.134R

## Important Notes

1. **No Slippage in Backtest:** The daily_features tables assume PERFECT fills (no slippage)
2. **Real Trading:** Expect 1-2 tick slippage on entry and stop
3. **Always Query v_orb_trades_half:** Don't query daily_features tables directly
4. **RR Values:** Some configs use RR > 1.0 (e.g., 1000 ORB uses RR=3.0)
5. **SL Modes:** HALF = stop at ORB midpoint, FULL = stop at opposite ORB edge

## How to Add Real-World Slippage

```sql
-- Example: MGC 2300 with 1 tick slippage
SELECT
    AVG(CASE
        WHEN outcome='WIN' THEN 1.0 - (0.2 / 0.1) / risk_ticks
        WHEN outcome='LOSS' THEN -1.0 - (0.2 / 0.1) / risk_ticks
    END) as avg_r_with_slippage
FROM v_orb_trades_half
WHERE orb_time='2300'
  AND instrument='MGC'
  AND outcome IN ('WIN','LOSS')
  AND risk_ticks > 0;
```

Where:
- 0.2 = 0.1 entry slip + 0.1 stop slip (1 tick each)
- 0.1 = MGC tick size
- risk_ticks = stop distance in ticks

---

**CRITICAL:** Only use `v_orb_trades_half` and related daily_features_v2 tables. All orb_trades_*_exec tables are ARCHIVED and outdated.

---

## Table Naming Convention

**Pattern:**
```
{table_name}         <- MGC (default, no suffix)
{table_name}_mpl     <- MPL
{table_name}_nq      <- NQ
{table_name}_es      <- ES (future)
{table_name}_rty     <- RTY (future)
```

**Examples:**
- `bars_1m` = MGC 1-minute bars
- `bars_1m_mpl` = MPL 1-minute bars
- `bars_1m_nq` = NQ 1-minute bars
- `daily_features_v2` = MGC daily features
- `daily_features_v2_mpl` = MPL daily features
- `daily_features_v2_nq` = NQ daily features

---

## Full Table Schemas

### bars_1m (and bars_1m_mpl, bars_1m_nq)
```sql
CREATE TABLE bars_1m (
    ts_utc TIMESTAMPTZ PRIMARY KEY,
    symbol VARCHAR,              -- e.g., 'MGC', 'MGCG6', etc.
    source_symbol VARCHAR,       -- actual contract (e.g., 'MGCG6')
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT
);
```

### bars_5m (and bars_5m_mpl, bars_5m_nq)
```sql
CREATE TABLE bars_5m (
    ts_utc TIMESTAMPTZ PRIMARY KEY,
    symbol VARCHAR,
    source_symbol VARCHAR,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT
);
```
**Note:** 5-minute bars are aggregated from 1-minute bars. Never manually edit.

### daily_features_v2 (and daily_features_v2_mpl, daily_features_v2_nq)
```sql
CREATE TABLE daily_features_v2 (
    date_local DATE PRIMARY KEY,
    instrument VARCHAR,          -- 'MGC', 'MPL', 'NQ'

    -- Session data
    asia_high DOUBLE,
    asia_low DOUBLE,
    london_high DOUBLE,
    london_low DOUBLE,
    ny_high DOUBLE,
    ny_low DOUBLE,

    -- ORBs (6 total: 0900, 1000, 1100, 1800, 2300, 0030)
    orb_0900_high DOUBLE,
    orb_0900_low DOUBLE,
    orb_0900_size DOUBLE,
    orb_0900_break_dir VARCHAR,
    orb_0900_outcome VARCHAR,
    orb_0900_r_multiple DOUBLE,
    -- ... (repeated for each ORB time: 1000, 1100, 1800, 2300, 0030)

    -- Indicators
    atr_20 DOUBLE,
    rsi_14 DOUBLE,

    -- Pre-move metrics
    pre_ny_travel DOUBLE,
    pre_orb_travel DOUBLE
);
```

### validated_setups (shared across all instruments)
```sql
CREATE TABLE validated_setups (
    setup_id INTEGER PRIMARY KEY,
    instrument VARCHAR,           -- 'MGC', 'MPL', 'NQ'
    strategy_name VARCHAR,
    orb_time VARCHAR,
    rr_target DOUBLE,
    sl_mode VARCHAR,
    tier VARCHAR,
    win_rate DOUBLE,
    avg_r DOUBLE,
    trade_count INTEGER,
    orb_size_filter DOUBLE        -- NULL or threshold
);
```

---

## Query Patterns

### Get MGC bars
```sql
SELECT * FROM bars_1m WHERE ts_utc >= '2026-01-01';
```

### Get MPL bars
```sql
SELECT * FROM bars_1m_mpl WHERE ts_utc >= '2026-01-01';
```

### Get NQ bars
```sql
SELECT * FROM bars_1m_nq WHERE ts_utc >= '2026-01-01';
```

### Get all validated setups for MGC
```sql
SELECT * FROM validated_setups WHERE instrument = 'MGC';
```

### Get daily features for MPL
```sql
SELECT * FROM daily_features_v2_mpl
WHERE instrument = 'MPL'
ORDER BY date_local DESC
LIMIT 30;
```

---

## Application Integration

### Python Helper Functions

```python
def get_bars_table(instrument: str) -> str:
    """Get 1-minute bars table name for instrument"""
    if instrument == 'MGC':
        return 'bars_1m'
    elif instrument == 'MPL':
        return 'bars_1m_mpl'
    elif instrument == 'NQ':
        return 'bars_1m_nq'
    else:
        raise ValueError(f"Unknown instrument: {instrument}")

def get_feature_table(instrument: str) -> str:
    """Get daily features table for instrument"""
    if instrument == 'MGC':
        return 'daily_features_v2'
    else:
        return f'daily_features_v2_{instrument.lower()}'

# Usage example
instrument = 'MPL'
bars_table = get_bars_table(instrument)
features_table = get_feature_table(instrument)

bars = conn.execute(
    f"SELECT * FROM {bars_table} WHERE ts_utc >= ?",
    [start_date]
).fetchall()
```

---

## Data Pipeline

### Backfill Process

Each instrument has its own backfill workflow:

**MGC:**
```bash
python backfill_databento_continuous.py 2024-01-01 2026-01-10
python build_daily_features.py 2026-01-10
```

**MPL:**
```bash
python backfill_databento_continuous.py 2024-01-01 2026-01-10 --instrument MPL
python build_daily_features.py 2026-01-10 --instrument MPL
```

**NQ:**
```bash
python backfill_databento_continuous.py 2024-01-01 2026-01-10 --instrument NQ
python build_daily_features.py 2026-01-10 --instrument NQ
```

---

## Adding New Instruments

To add a new instrument (e.g., ES - E-mini S&P 500):

1. **Create tables:**
   - `bars_1m_es`
   - `bars_5m_es`
   - `daily_features_v2_es`

2. **Backfill data:**
   ```bash
   python backfill_databento_continuous.py 2024-01-01 2026-01-10 --instrument ES
   python build_daily_features.py 2026-01-10 --instrument ES
   ```

3. **Add strategies to validated_setups:**
   ```sql
   INSERT INTO validated_setups (instrument, strategy_name, orb_time, ...)
   VALUES ('ES', 'DAY_ORB', '0900', ...);
   ```

4. **Update apps:**
   - Add 'ES' to instrument selector
   - Update helper functions (get_bars_table, get_feature_table)

---

## Architecture Decision: Separate Tables

**Why separate tables per instrument instead of unified tables?**

**Benefits:**
- **Simple**: No complex consolidation logic
- **Fast**: Smaller tables = faster queries
- **Safe**: No schema confusion or type mismatches
- **Debuggable**: Each instrument is isolated
- **Scalable**: Easy to add new instruments

**Avoided Problems:**
- Schema corruption during consolidation
- VARCHAR vs DOUBLE type issues
- Complex multi-instrument queries
- Migration complexity

**Current Status:**
- MGC: 720,227 1-min bars, 740 daily features
- MPL: 327,127 1-min bars, 730 daily features
- NQ: 350,499 1-min bars, 310 daily features
