# Filter Optimizer - Usage Guide

**A reusable, built-in system for optimizing trading filters**

---

## 🎯 What It Does

The filter optimizer:
- **Tests hundreds of filter combinations** automatically
- **Prevents overfitting** with train/test split (60% train, 40% test)
- **Ranks filters** by improvement (win rate, expected R, annual R)
- **Validates filters** (rejects filters that work on train but not test)
- **Exports results** to CSV for analysis

---

## 🚀 Quick Start

### Optimize a Single Edge

```bash
# Test filters for 0900 ORB:
python filter_optimizer.py --orb 0900 --rr 1.5 --sl-mode half

# Output:
# Testing 150+ filter combinations...
# TOP FILTERS:
# 1. ORB size >= 0.10 AND Asia travel > 1.5
#    Train: 68% WR, +0.40R avg, 65 trades
#    Test:  66% WR, +0.38R avg, 28 trades
#    ✅ VALIDATED
```

### Optimize All ORBs

```bash
# Test all 6 ORBs at once:
python filter_optimizer.py --optimize-all --rr 1.5
```

### Export Results

```bash
# Save results to CSV:
python filter_optimizer.py --orb 0900 --export results_0900.csv
```

---

## 📊 Example Output

```
===========================================================================
OPTIMIZING FILTERS: 0900 ORB (RR=1.5, SL=HALF)
===========================================================================

Total data points: 520
Train set: 312 trades (60%)
Test set: 208 trades (40%)

BASELINE PERFORMANCE:
  Train: 58.0% WR, +0.25R avg, 312 trades, +30R/year
  Test:  57.0% WR, +0.23R avg, 208 trades, +28R/year

Testing 150 filter combinations...
Valid filters: 87 (with sufficient sample size)

===========================================================================
FILTER OPTIMIZATION RESULTS
===========================================================================

Edge: 0900 ORB (RR=1.5, SL=HALF)
Baseline: 58.0% WR, +0.25R avg, 312 train trades, +30R/year

TOP FILTERS (Ranked by Test Set Improvement):

1. ORB size >= 0.10 AND Asia travel > 1.5
   Train: 68.0% WR, +0.40R avg, 65 trades, +50R/year (+10.0% WR, +0.15R)
   Test:  66.0% WR, +0.38R avg, 28 trades, +48R/year (+9.0% WR, +0.15R)
   ✅ VALIDATED (test performance within 10% of train)
   Confidence: HIGH

2. ORB size >= 0.10
   Train: 62.0% WR, +0.30R avg, 95 trades, +40R/year (+4.0% WR, +0.05R)
   Test:  60.0% WR, +0.28R avg, 40 trades, +38R/year (+3.0% WR, +0.05R)
   ✅ VALIDATED
   Confidence: HIGH

3. Asia travel > 2.0
   Train: 70.0% WR, +0.45R avg, 50 trades, +55R/year (+12.0% WR, +0.20R)
   Test:  58.0% WR, +0.22R avg, 22 trades, +28R/year (+1.0% WR, -0.01R)
   ❌ OVERFIT (train +12.0% WR, test +1.0% WR, diff=11.0%)
   Confidence: LOW
```

---

## 🔧 How to Customize

### 1. Add New Filter Types

Edit `filter_optimizer.py` → `generate_all_filters()`:

```python
def generate_all_filters(self):
    filters = []

    # YOUR CUSTOM FILTERS HERE:

    # Add momentum filter:
    filters.append((
        "Strong momentum",
        "asia_travel > 2.5 and london_range > 2.0"
    ))

    # Add time-based filter:
    filters.append((
        "Mid-week only",
        "day_of_week in ['Wednesday', 'Thursday']"
    ))

    # Add regime filter:
    filters.append((
        "Trending regime",
        "asia_travel > 2.0 and pre_ny_travel > 1.5"
    ))

    return filters
```

### 2. Adjust Thresholds

Edit `__init__` method:

```python
def __init__(self, db_path: str = DB_PATH):
    # ... existing code ...

    # CUSTOMIZE THESE:
    self.orb_size_thresholds = [0.05, 0.10, 0.15, 0.20, 0.25]  # Add more values
    self.asia_travel_thresholds = [1.0, 1.5, 2.0, 2.5, 3.0]    # Adjust ranges
    self.MIN_TRAIN_TRADES = 30  # Increase for more conservative validation
    self.OVERFIT_THRESHOLD = 0.10  # Lower for stricter overfit detection
```

### 3. Change Validation Rules

Edit `test_filter()` method:

```python
# BEFORE (default):
is_validated = overfit_score <= (self.OVERFIT_THRESHOLD * 100)

# AFTER (stricter - require test improvement > 5%):
is_validated = (
    overfit_score <= (self.OVERFIT_THRESHOLD * 100) and
    test_wr_improvement >= 5.0
)
```

### 4. Change Ranking Criteria

Edit `optimize_edge()` method:

```python
# BEFORE (ranks by test WR improvement):
results.sort(key=lambda x: (x.test_wr_improvement, x.test_r_improvement), reverse=True)

# AFTER (rank by annual R improvement):
results.sort(key=lambda x: (x.test_annual_r, x.is_validated), reverse=True)

# Or rank validated filters only:
validated = [r for r in results if r.is_validated]
validated.sort(key=lambda x: x.test_wr_improvement, reverse=True)
```

---

## 🔁 When to Re-Run

### 1. After Finding New Edges
```bash
# Discovered 35 new edges? Optimize them all:
python filter_optimizer.py --optimize-all --rr 1.5
```

### 2. Quarterly Re-Optimization
```bash
# Market conditions change - re-optimize quarterly:
python filter_optimizer.py --optimize-all --export Q1_2026.csv
python filter_optimizer.py --optimize-all --export Q2_2026.csv

# Compare results:
diff Q1_2026.csv Q2_2026.csv
```

### 3. After Backfilling New Data
```bash
# Added 6 months of new data? Re-run optimizer:
python filter_optimizer.py --orb 0900 --rr 2.0
```

### 4. Testing New Filter Ideas
```python
# 1. Edit filter_optimizer.py → add your custom filter
# 2. Run:
python filter_optimizer.py --orb 0900
# 3. Review results
# 4. If validated, add to validated_setups
```

---

## 📈 Integration with Your System

### Step 1: Run Filter Optimizer

```bash
python filter_optimizer.py --optimize-all --export optimized_filters.csv
```

### Step 2: Review Results

Open `optimized_filters.csv`:
- Look for `is_validated = True` (not overfit)
- Look for `confidence = HIGH` (sufficient sample size)
- Look for `test_wr_improvement >= 5%` (meaningful improvement)

### Step 3: Add Best Filters to validated_setups

```sql
-- Add filtered edge to database:
INSERT INTO validated_setups (
    orb_time, rr, sl_mode, win_rate, expected_r, sample_size, orb_size_filter
) VALUES (
    '0900', 1.5, 'HALF', 66.0, 0.38, 28, 0.10
);
```

### Step 4: Update market_scanner.py

Add custom filter logic:

```python
def validate_orb_setup(self, orb_time, orb_size, date_local):
    # ... existing code ...

    # Add Asia travel filter for 0900 ORB:
    if orb_time == '0900':
        asia_travel = self.get_asia_travel(date_local)
        if asia_travel <= 1.5:
            return {
                'passes_filter': False,
                'reason': 'Asia travel too low (< 1.5)'
            }

    # ... rest of code ...
```

### Step 5: Update filter_library.py

Save commonly-used filters:

```python
FILTER_QUERIES = {
    # Add your validated filter:
    'quality_0900_setup': 'orb_size >= 0.10 and asia_travel > 1.5',
}

FILTER_METADATA = {
    'quality_0900_setup': {
        'description': 'ORB >= 0.10 AND Asia travel > 1.5',
        'tested_on': ['0900'],
        'performance': {
            '0900': {
                'train_wr': 68,
                'test_wr': 66,
                'validated': True,
                'confidence': 'HIGH'
            }
        },
        'notes': 'Improves WR by 9% on 0900 ORB'
    }
}
```

---

## 🎯 Typical Workflow

### Month 1: Initial Optimization

```bash
# 1. Discover edges:
python edge_discovery_live.py
# Found: 35 new edges

# 2. Optimize all edges:
python filter_optimizer.py --optimize-all --export month1_filters.csv

# 3. Review and select top 5 validated filters

# 4. Add to validated_setups database

# 5. Update market_scanner.py with filter logic

# 6. Start trading with filtered edges
```

### Month 2-3: Monitor Performance

```bash
# Track real trading results in trading memory
# Use edge_tracker to monitor degradation
```

### Month 4: Re-Optimization

```bash
# 1. Re-run filter optimizer:
python filter_optimizer.py --optimize-all --export month4_filters.csv

# 2. Compare with Month 1:
diff month1_filters.csv month4_filters.csv

# 3. Update filters if needed (market conditions changed)
```

---

## 🔬 Understanding the Output

### Filter Result Fields

- **filter_name**: Human-readable name
- **filter_condition**: Pandas query string
- **train_trades**: Number of trades in training set
- **train_win_rate**: Win rate on training data (%)
- **train_avg_r**: Average R-multiple on training data
- **test_trades**: Number of trades in test set
- **test_win_rate**: Win rate on test data (%)
- **test_avg_r**: Average R-multiple on test data
- **train_wr_improvement**: WR improvement vs baseline (train)
- **test_wr_improvement**: WR improvement vs baseline (test)
- **is_validated**: True if not overfit (test matches train)
- **confidence**: HIGH/MEDIUM/LOW based on sample size
- **overfit_score**: Difference between train and test improvement

### What to Look For

**✅ GOOD FILTER:**
- `is_validated = True` (not overfit)
- `confidence = HIGH` (sufficient data)
- `test_wr_improvement >= 5%` (meaningful improvement)
- `test_trades >= 25` (reliable sample)

**❌ BAD FILTER:**
- `is_validated = False` (overfit)
- `confidence = LOW` (insufficient data)
- `test_wr_improvement < 0%` (worse than baseline)
- `overfit_score > 10%` (train/test mismatch)

---

## 🚨 Common Pitfalls

### 1. Overfitting
**Problem:** Filter works on train but fails on test
**Solution:** Only use filters with `is_validated = True`

### 2. Insufficient Sample Size
**Problem:** Filter looks good but only 10 trades in test
**Solution:** Require `confidence = HIGH` (50+ train, 25+ test)

### 3. Curve Fitting
**Problem:** Testing too many filters increases false positives
**Solution:** Use conservative overfit threshold (5-10%)

### 4. Data Snooping
**Problem:** Re-running optimizer multiple times on same data
**Solution:** Re-optimize quarterly with fresh data only

---

## 💡 Pro Tips

### 1. Start Conservative
```python
# Use strict validation first:
self.MIN_TRAIN_TRADES = 50
self.OVERFIT_THRESHOLD = 0.05  # 5% max difference
```

### 2. Validate on Out-of-Sample Data
```bash
# Test on recent data only:
# In filter_optimizer.py, add date filters:
df = self.get_edge_data(orb_time, min_date=date(2025, 1, 1))
```

### 3. Combine Filters Carefully
```python
# Don't combine too many filters (overfitting risk):
# GOOD: "ORB >= 0.10 AND Asia > 1.5" (2 filters)
# BAD: "ORB >= 0.10 AND Asia > 1.5 AND RSI < 40 AND Monday" (4 filters)
```

### 4. Monitor Filter Performance
```bash
# Re-run quarterly to check if filters still work:
python filter_optimizer.py --optimize-all --export Q1.csv
python filter_optimizer.py --optimize-all --export Q2.csv
diff Q1.csv Q2.csv
```

---

## 📚 Related Files

- **filter_optimizer.py** - Main optimizer script
- **filter_library.py** - Reusable filter definitions
- **market_scanner.py** - Real-time filter validation
- **edge_tracker.py** - Monitor filter performance
- **validated_setups** - Database of filtered edges

---

## 🎯 Next Steps

1. **Run filter optimizer on your 35 new edges:**
   ```bash
   python filter_optimizer.py --optimize-all --export my_edges.csv
   ```

2. **Review results and select top validated filters**

3. **Add filters to validated_setups database**

4. **Update market_scanner.py with filter logic**

5. **Re-run quarterly to adapt to market changes**

---

**The filter optimizer is a PERMANENT PART of your trading system.**

You can:
- ✅ Run it anytime on any edge
- ✅ Adjust parameters (thresholds, validation rules)
- ✅ Add new filter types easily
- ✅ Export results to CSV
- ✅ Integrate with market_scanner
- ✅ Re-optimize as markets evolve

**It's a built-in system you'll use repeatedly, not a one-time tool!**
