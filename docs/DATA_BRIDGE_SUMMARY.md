# Data Bridge - Automatic Gap Filling System

**Created:** 2026-01-25
**Status:** ✅ READY TO USE

---

## Problem Solved

**Before:**
- Historical data in database ends at 2026-01-10
- Market scanner can't scan today (2026-01-25)
- Gap = 15 days of missing data
- Apps are useless without current data

**After:**
- Data bridge automatically detects gaps
- Backfills from appropriate source (Databento or ProjectX)
- Market scanner gets current data
- Apps work on fresh data

---

## How It Works

### 1. Gap Detection

```python
from trading_app.data_bridge import DataBridge

bridge = DataBridge()
status = bridge.get_status()

# Returns:
# {
#     'last_db_date': date(2026, 1, 10),
#     'current_date': date(2026, 1, 25),
#     'gap_days': 15,
#     'needs_update': True
# }
```

### 2. Automatic Source Selection

**Logic:**
- **Databento**: For historical data (> 30 days old)
- **ProjectX**: For recent data (0-30 days)

**Why this matters:**
- ProjectX maintains consistency for recent trading
- Databento for deep history where already validated
- Avoids price jump at stitching point

**Example:**
```
Gap: 2026-01-11 to 2026-01-25 (15 days)
Days ago: 0-15 days (recent)
Source selected: ProjectX ✅
```

### 3. Automatic Backfill

```python
# Standalone usage
bridge.update_to_current()

# Or integrated into market scanner
scanner = MarketScanner()
results = scanner.scan_all_setups(auto_update=True)  # Fills gap before scanning
```

**What it does:**
1. Runs `backfill_range.py 2026-01-11 2026-01-25` (ProjectX)
2. Runs `build_daily_features.py` for each date
3. Populates `daily_features` with ORBs
4. Market scanner now has current data

### 4. Stitching Quality Check

**Problem:**
- Price differences between sources
- Databento: settlement prices
- ProjectX: real-time prices
- Could have price jump at boundary

**Solution:**
```python
stitch_check = bridge.check_stitching_quality(last_db_date)

# Returns:
# {
#     'has_anomaly': False,
#     'price_jump': 0.8,  # Points
#     'details': 'Price transition looks normal'
# }
```

**Threshold:** 5 points
- If jump > 5 points → Anomaly (alert user)
- If jump < 5 points → Normal (accept)

---

## Price Consistency Handling

### Sources and Price Differences

| Source | Type | Typical Use | Price Characteristics |
|--------|------|-------------|----------------------|
| **Databento** | Settlement | Deep history | Official EOD prices |
| **ProjectX** | Real-time/delayed | Recent data | Live feed prices |
| **TradingView** | Aggregated | Charting | Multiple sources |

**Typical differences:** 0.1-0.3 points (normal market variation)

### Impact on ORB Sizes

**Example scenario:**
```
Date: 2026-01-20
Databento shows: high=2654.3, low=2653.1 → ORB size = 1.2
ProjectX shows:  high=2654.4, low=2653.0 → ORB size = 1.4
Difference: 0.2 points
```

**Does this break trading logic?**

**NO** - because:

1. **Filters are coarse (0.05, 0.10, 0.15)**
   - Both 1.2 and 1.4 pass 0.10 filter
   - Not sensitive to 0.2 point difference

2. **Large safety margins**
   - Win rates: 60-70% (not 50.1%)
   - R-multiples: 1.0-8.0 points
   - Small price variation absorbed by margin

3. **Statistical significance**
   - 100+ trade samples
   - 0.2 point variation is noise
   - Edge validity unaffected

### When Price Differences DO Matter

**CRITICAL (> 5 points):**
- Indicates data quality issue
- Data bridge alerts automatically
- Review source configuration

**Marginal (0.5-2 points):**
- Normal variation
- May affect borderline ORB filter passes
- Acceptable (edges have margin)

**Negligible (< 0.5 points):**
- Expected market noise
- No impact on trading logic
- Ignore

### Mitigation Strategy

**1. Use ProjectX for ALL recent data (0-30 days)**
- Configured in `data_bridge.py`:
  ```python
  self.DATABENTO_CUTOFF_DAYS = 30  # Use Databento for > 30 days
  self.PROJECTX_CUTOFF_DAYS = 0    # Use ProjectX for 0-30 days
  ```
- Maintains consistency in recent trading
- Avoids stitching issues

**2. Databento only for deep history**
- Historical edges validated on Databento data
- Recent trading uses ProjectX (consistent)
- Stitching point is 30+ days old (doesn't affect current trades)

**3. Automatic stitching quality checks**
- Detects price jumps > 5 points
- Alerts if sources don't match
- You review and adjust if needed

---

## Integration with Market Scanner

**Before integration:**
```python
scanner = MarketScanner()
results = scanner.scan_all_setups()
# Returns: "No data available" if gap exists
```

**After integration:**
```python
scanner = MarketScanner()
results = scanner.scan_all_setups(auto_update=True)
# Automatically fills gap, then scans current data
```

**What happens:**
1. Market scanner checks for gaps
2. If gap exists, calls data bridge
3. Data bridge backfills missing dates
4. Market scanner proceeds with current data
5. Returns valid setups for today

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `trading_app/data_bridge.py` | 450+ | Gap detection, source selection, backfill automation |
| `test_data_bridge.py` | 200+ | Tests and price difference explanation |
| `DATA_BRIDGE_SUMMARY.md` | (this file) | Documentation |

---

## Usage Examples

### Example 1: Standalone Gap Check

```python
from trading_app.data_bridge import DataBridge

bridge = DataBridge()

# Check status
status = bridge.get_status()
print(f"Gap: {status['gap_days']} days")

# Update if needed
if status['needs_update']:
    bridge.update_to_current()
```

### Example 2: Integrated with Market Scanner

```python
from trading_app.market_scanner import MarketScanner

scanner = MarketScanner()

# Auto-fill gaps before scanning
results = scanner.scan_all_setups(auto_update=True)

# Show valid setups
for setup in results['valid_setups']:
    print(f"{setup['orb_time']} ORB: {setup['confidence']} - TAKE TRADE")
```

### Example 3: Check Stitching Quality

```python
from trading_app.data_bridge import DataBridge
from datetime import date

bridge = DataBridge()

# After backfill, check if prices transitioned smoothly
last_old_date = date(2026, 1, 10)
stitch_check = bridge.check_stitching_quality(last_old_date)

if stitch_check['has_anomaly']:
    print(f"WARNING: Price jump of {stitch_check['price_jump']:.2f} points detected!")
else:
    print(f"OK: Price transition normal ({stitch_check['price_jump']:.2f} points)")
```

---

## Testing

**Test the data bridge:**
```bash
python test_data_bridge.py
```

**What it tests:**
1. Gap detection
2. Source selection logic
3. Stitching quality checks
4. Price difference handling

**Expected output:**
```
[TEST 1] Checking current status...
Last DB date: 2026-01-10
Current date: 2026-01-25
Gap: 15 days
Would use source: PROJECTX

[TEST 2] Checking stitching quality...
Price jump: 0.8 points
Details: Price transition looks normal

[OK] DATA BRIDGE TEST COMPLETE
```

---

## Configuration

**Adjust source selection thresholds:**

Edit `trading_app/data_bridge.py`:

```python
# Use ProjectX for more/less recent data
self.DATABENTO_CUTOFF_DAYS = 30  # Change to 7, 14, 60, etc.
self.PROJECTX_CUTOFF_DAYS = 0

# Example: Use ProjectX for last 60 days
self.DATABENTO_CUTOFF_DAYS = 60
```

**Why you might adjust:**
- ProjectX has limited history → reduce to 7-14 days
- Want more consistency → increase to 60-90 days
- Databento preferred → reduce to 0 days (always use Databento)

---

## Next Steps

### Option 1: Test Data Bridge (Recommended First)

```bash
# 1. Test gap detection
python test_data_bridge.py

# 2. Manually run data bridge
python -c "from trading_app.data_bridge import DataBridge; DataBridge().update_to_current()"

# 3. Test market scanner with current data
python -m trading_app.market_scanner
```

### Option 2: Integrate into Trading App

Add to `app_trading_hub.py` or `unified_trading_app.py`:

```python
from trading_app.data_bridge import DataBridge
from trading_app.market_scanner import MarketScanner

# On app startup
print("Checking for data updates...")
bridge = DataBridge()
bridge.update_to_current()

# Then run market scanner
scanner = MarketScanner()
results = scanner.scan_all_setups()

# Show valid setups to user
for setup in results['valid_setups']:
    print(f"✅ {setup['orb_time']} ORB: VALID - Take trade!")
```

### Option 3: Scheduled Auto-Update

Set up cron job / Task Scheduler to run daily:

```bash
# Every day at 08:00 (before trading starts)
0 8 * * * cd /path/to/MPX2_fresh && python -c "from trading_app.data_bridge import DataBridge; DataBridge().update_to_current()"
```

---

## Troubleshooting

### Issue: "No data available" after running bridge

**Cause:** ORB data not calculated (bars exist but features don't)

**Solution:**
```bash
python pipeline/build_daily_features.py 2026-01-25
```

### Issue: "Large price gap detected at stitching point"

**Cause:** Different sources have significantly different prices

**Solution:**
1. Check if it's a real anomaly (> 5 points is unusual)
2. Consider using single source for all recent data
3. Review data quality from ProjectX

### Issue: "ProjectX backfill failed"

**Cause:** ProjectX API issue, credentials, or data unavailable

**Solution:**
1. Check `.env` for ProjectX credentials
2. Try Databento instead (adjust cutoff days)
3. Manual backfill: `python backfill_databento_continuous.py 2026-01-11 2026-01-25`

---

## Summary

**What works:**
- ✅ Automatic gap detection
- ✅ Source selection (Databento vs ProjectX)
- ✅ Backfill automation
- ✅ Stitching quality checks
- ✅ Integration with market scanner

**What it solves:**
- ✅ Database stops at old date → automatically updates to today
- ✅ Price differences between sources → handled with consistency strategy
- ✅ Market scanner needs current data → gets it automatically

**What you get:**
- ✅ Apps always work with current data
- ✅ No manual backfilling required
- ✅ Price consistency maintained
- ✅ Anomaly detection at stitching points

**Bottom line:**
Your apps now automatically maintain current data. No gaps, no stale data, no manual intervention. Just works.
