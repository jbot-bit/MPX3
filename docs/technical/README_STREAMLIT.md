# Streamlit Edge Research Dashboard

**Interactive ORB edge research tool with zero-lookahead validation**

<img src="https://img.shields.io/badge/Status-Operational-green" /> <img src="https://img.shields.io/badge/Data-V2%20Zero%20Lookahead-blue" />

---

## Overview

The Streamlit dashboard (`app_edge_research.py`) provides an interactive interface for exploring ORB edges with zero-lookahead guarantees. It uses the V2 dataset (`daily_features_v2`) through the `v_orb_trades` view.

**Key Features:**
- **Strategy Builder** - Test different entry models, retest rules, and stop sizes
- **Session Code Filters** - Filter by Asia/London/Pre-NY types
- **Compare Mode** - A/B test two different setups side-by-side
- **Heatmaps** - Visualize performance across session combinations
- **Equity Curves** - Track cumulative R over time
- **Entry Funnel** - See how many opportunities pass each filter

---

## Installation

### Prerequisites

```bash
pip install streamlit
pip install matplotlib
pip install pandas
pip install numpy
```

All other dependencies (duckdb) should already be installed.

### Verify Installation

```bash
python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"
```

---

## Launch Dashboard

### Basic Launch

```bash
streamlit run app_edge_research.py
```

**Default URL:** http://localhost:8501

### Custom Port

```bash
streamlit run app_edge_research.py --server.port 8502
```

### Remote Access (Caution)

```bash
streamlit run app_edge_research.py --server.address 0.0.0.0
```

**Warning:** Only use this on a trusted network. The dashboard connects to your local database.

---

## User Interface Guide

### Sidebar - Filters & Strategy

#### Search Mode

**Simple Mode:**
- Quick strategy setup with intuitive options
- Entry confirmation (1m, 2m, 3m closes, or 5m close)
- Retest options (touch vs pierce)
- Max stop size limit

**Advanced Mode:**
- Full control over strategy parameters
- Presets for common setups
- Confirmation closes (1-3)
- Retest rules (touch, pierce by ticks)
- Rejection timeframe (1m or 5m)

#### Filters

**Date Range:**
- Filter data by specific date window
- Defaults to full dataset (2024-01-02 to 2026-01-10)

**ORB Time:**
- Select which ORBs to include (0900, 1000, 1100, 1800, 2300, 0030)
- Multi-select

**Direction:**
- ANY, UP, or DOWN

**Outcome:**
- WIN, LOSS, NO_TRADE
- Keep NO_TRADE selected to see all opportunities

**Session Codes (Expandable):**
- Asia Type Code (A0_NORMAL, A1_TIGHT, A2_EXPANDED, etc.)
- London Type Code (L1_SWEEP_HIGH, L2_SWEEP_LOW, L3_EXPANSION, L4_CONSOLIDATION)
- Pre-NY Type Code (N0_NORMAL, N1_SWEEP_HIGH, N2_SWEEP_LOW, N3_CONSOLIDATION, N4_EXPANSION)
- Option to include NULL values (default: ON)

**Volatility Filters (Expandable):**
- ATR 20 range
- Asia range filter

**Advanced (Expandable):**
- Top N days by R (descending)
- Useful for identifying best/worst trading days

#### Compare Mode

**Save as Query A / Query B:**
- Pin current filters and strategy
- Compare two different setups side-by-side
- Shows equity curves for both queries

---

### Main Panel - Results

#### Strategy Summary

Shows:
- Level basis (ORB boundary vs Half ORB)
- Entry model and confirmation closes
- Retest and rejection settings
- Stop rule and cutoff

**Badges:**
- ORB times selected
- Direction filter
- Level type
- Total trades matching filters

#### Headline Stats

**5 Key Metrics:**
- **Trades (WIN/LOSS):** Count of actual trades taken
- **Win Rate:** Percentage of wins
- **Avg R:** Average R-multiple per trade
- **Total R:** Cumulative R across all trades
- **Opportunities:** Total ORB setups (includes NO_TRADE)

**Baseline comparison:**
- Shows baseline trades/opportunities for date window only (no filters)

#### Entry Path Funnel

Visualizes how many opportunities pass each filter stage:
1. **ORBs total** - All ORB setups in date range
2. **Break occurred** - Price broke ORB range
3. **Confirm met** - Required confirmation closes hit
4. **Retest met** - Retest condition satisfied (if required)
5. **Rejection met** - Rejection signal triggered (if required)
6. **Trades taken** - Opportunities that passed all filters
7. **Wins** - Successful trades
8. **Losses** - Unsuccessful trades

#### Charts

**Equity Curve:**
- Cumulative R over time (WIN/LOSS only)
- Chronologically ordered by date and ORB time
- Shows final Total R value

**R-Multiple Distribution:**
- Histogram of R outcomes
- Mean (blue dashed line)
- Median (green dotted line)
- 30 bins

#### Session Heatmap (Asia x London)

**Metrics:**
- Avg R (default)
- Win Rate
- Count

**Color Coding:**
- Green = Positive/High
- Red = Negative/Low

**Usage:**
- Identify which session combinations work best
- Spot patterns (e.g., "TIGHT Asia + EXPANSION London")

#### Drilldown Table

**Default Display (500 rows max):**
- Date, ORB time, direction, outcome
- R-multiple, level price, ORB boundaries
- Confirmation/retest/rejection flags
- Filtered out reason (if not taken)
- Session type codes
- ATR, Asia range

**Download Full CSV:**
- Button below table
- Exports complete filtered dataset
- No row limit

---

## Example Workflows

### 1. Find Best 10:00 UP Setup

1. **Set Filters:**
   - ORB Time: 1000
   - Direction: UP
   - Outcomes: WIN, LOSS (keep NO_TRADE selected too)

2. **Try Different Strategies:**
   - Preset: "Boundary | 1m Break (1 close)"
   - Preset: "Boundary | 1m Break (2 closes)"
   - Preset: "Boundary | Break + Retest + 1m Reject"

3. **Compare Results:**
   - Look at Win Rate, Avg R, Total trades
   - Check equity curve smoothness
   - Examine entry funnel (how many opportunities lost?)

4. **Save Best Setup:**
   - Click "Save as Query A"

### 2. Test PRE_ASIA Filter Effect

1. **Query A (No Filter):**
   - ORB Time: 1100
   - Direction: UP
   - Save as Query A

2. **Query B (With Filter):**
   - ORB Time: 1100
   - Direction: UP
   - Enable "Asia range filter"
   - Set range: 50-1000 (PRE_ASIA > 50 ticks equivalent)
   - Save as Query B

3. **Compare:**
   - See improvement in Win Rate and Avg R
   - Check if sample size is still adequate

### 3. Discover Correlation Edges

**Note:** The dashboard doesn't yet support ORB-to-ORB correlation filters (09:00 WIN → 10:00 UP). For correlation analysis, use:

```bash
python analyze_orb_v2.py
```

Then validate specific dates in the drilldown table.

### 4. Optimize Stop Size

1. **Set Base Strategy:**
   - ORB: 1000
   - Direction: UP
   - Entry: 1m Break (1 close)

2. **Test Max Stop Limits:**
   - No max stop: ___
   - Max 50 ticks: ___
   - Max 75 ticks: ___
   - Max 100 ticks: ___

3. **Compare:**
   - Trades eliminated (funnel)
   - Win rate change
   - Avg R change
   - Total R impact

---

## Data Source

### Tables Used

**`v_orb_trades` (View):**
- Normalized view of all ORB opportunities
- Unpivots `daily_features_v2` columns
- 4,434 rows (6 ORBs × 739 days)

**`daily_features_v2` (Table):**
- Source data with zero-lookahead structure
- 739 days (2024-01-02 to 2026-01-10)
- ORB prices, outcomes, R-multiples
- Session type codes, ATR, ranges

**`orb_trades_1m_exec` (Table):**
- Optional: 1-minute backtest results
- Used to show close confirmations hit
- Currently: 2,924 trades (RR=3.0, 1 close)

### Data Refresh

Dashboard reads from database on each interaction. To update with new data:

1. **Rebuild Features:**
   ```bash
   python build_daily_features_v2.py 2026-01-11 2026-01-11
   ```

2. **Refresh Dashboard:**
   - Streamlit auto-reloads on interaction
   - Or press **R** in browser to force reload

---

## Performance Notes

### Cache System

The dashboard uses `@st.cache_data` decorators for:
- Filter metadata loading
- Headline stats calculation
- Equity curve generation
- Heatmap data
- Drilldown queries

**Cache Invalidation:**
- Caches are keyed by filter/strategy parameters
- Changing filters triggers new queries
- Database changes require Streamlit restart

### Large Datasets

- Drilldown limited to 500 rows (display)
- Full CSV export available (no limit)
- Heatmaps aggregate data efficiently
- Equity curves handle thousands of trades

### Optimization Tips

- Use date range filters to reduce dataset size
- Limit ORB times to specific sessions
- TOP N filter reduces result set

---

## Troubleshooting

### Dashboard Won't Start

**Error:** `ModuleNotFoundError: No module named 'streamlit'`

**Fix:**
```bash
pip install streamlit
```

### Database Connection Failed

**Error:** `duckdb.IOException: IO Error: Database file not found`

**Fix:**
```bash
# Verify database exists
ls gold.db

# Check working directory
pwd

# Run from project root
cd C:\Users\sydne\OneDrive\myprojectx
streamlit run app_edge_research.py
```

### No Data Showing

**Issue:** All queries return 0 trades

**Fix:**
1. Check filters (especially Outcomes - include WIN, LOSS, NO_TRADE)
2. Verify V2 data exists:
   ```bash
   python -c "import duckdb; con = duckdb.connect('gold.db'); print(con.execute('SELECT COUNT(*) FROM daily_features_v2').fetchone())"
   ```
3. Check v_orb_trades view exists:
   ```bash
   python -c "import duckdb; con = duckdb.connect('gold.db'); print(con.execute('SELECT COUNT(*) FROM v_orb_trades').fetchone())"
   ```

### Charts Not Rendering

**Issue:** Matplotlib errors

**Fix:**
```bash
pip install --upgrade matplotlib
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **R** | Rerun app (refresh) |
| **C** | Clear cache |
| **Esc** | Close sidebar (mobile) |

---

## Advanced: Custom Presets

To add your own strategy presets, edit `query_engine.py`:

```python
PRESETS: Dict[str, StrategyConfig] = {
    "Your Custom Strategy": StrategyConfig(
        level_basis="orb_boundary",  # or "orb_half"
        entry_model="1m_close_break",  # see options below
        confirm_closes=1,
        retest_required=False,
        retest_rule="touch",
        pierce_ticks=None,
        rejection_tf="1m",
        stop_rule="ORB_opposite_boundary",
        max_stop_ticks=100,  # or None
        cutoff_minutes=None,  # or integer
        one_trade_per_orb=True,
    ),
}
```

**Entry Models:**
- `1m_close_break` - First 1m close beyond level
- `1m_close_break_confirmed` - N consecutive 1m closes (set confirm_closes)
- `5m_close_break` - First 5m close beyond level
- `break_retest_reject` - Break, retest level, rejection close

---

## Next Steps

### After Finding an Edge

1. **Export Results:**
   - Download CSV from drilldown
   - Document in trading journal

2. **Validate with Backtest:**
   ```bash
   python backtest_orb_exec_1m.py --confirm 1 --rr 2.0
   ```

3. **Check Stability:**
   ```bash
   python analyze_edge_stability.py --orb 1000 --dir UP
   ```

4. **Paper Trade:**
   - Test in live market with alerts
   - Use `python daily_alerts.py` for setup recommendations

---

## Credits

**Built with:**
- Streamlit (UI framework)
- DuckDB (database)
- Matplotlib (charts)
- Pandas/NumPy (data processing)

**Philosophy:**
- Zero-lookahead methodology
- Honesty over accuracy
- 100% reproducible live

---

**Last Updated:** 2026-01-11
**Dashboard Version:** V2 (Zero Lookahead)
**Data Through:** 2026-01-10 (739 days)
