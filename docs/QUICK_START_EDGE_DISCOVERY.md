# Quick Start: Edge Discovery (30 Min Run)

## What This Does

Continuously searches your backtest data (ALL_ORBS_EXTENDED_WINDOWS.csv) for:
- **New edges** not yet in validated_setups
- **Improvements** to existing setups
- **Hidden patterns** in your data

Auto-saves results, auto-restarts if crashed, safe to interrupt anytime.

---

## How to Run (Choose One):

### Option 1: PowerShell (Recommended)
```powershell
# Open PowerShell in project directory
cd C:\Users\sydne\OneDrive\Desktop\MPX2_fresh

# Run edge discovery
python edge_discovery_live.py
```

### Option 2: Batch File
```powershell
# Double-click this file:
RUN_EDGE_DISCOVERY.bat
```

**To stop:** Press `Ctrl+C` anytime

---

## What You'll See

```
======================================================================
LIVE EDGE DISCOVERY ENGINE
======================================================================
Data source: data/exports/ALL_ORBS_EXTENDED_WINDOWS.csv
Results: edge_discovery_results/
Log: edge_discovery_live.log

✓ Loaded 54 backtest results
✓ Loaded 7 validated MGC setups
✓ Ready to discover edges!

Press Ctrl+C to stop.

======================================================================
ITERATION #1
======================================================================

   🎯 NEW EDGE #1!
      0900 ORB | RR=4.0 | SL=FULL
      WR=28.0% | Avg R=+0.312 | Annual≈+21R
      💾 NEW_20260125_115245_0900_RR4.0.txt

   ⭐ IMPROVEMENT #2!
      1000 ORB | RR=8.0→9.0
      E[R]: 0.378→0.395 (+4.5%)
      💾 IMPROVEMENT_20260125_115248_1000.txt

ITERATION COMPLETE
  Edges found: 2
  Total found: 2

  🏆 BEST NEW EDGE:
     0900 ORB | RR=4.0 | Annual≈+21R

  Runtime: 0:00:03

======================================================================

Waiting 5 seconds...
```

---

## Results Location

**All discoveries saved to:**
```
edge_discovery_results/
├── NEW_20260125_115245_0900_RR4.0.txt
├── IMPROVEMENT_20260125_115248_1000.txt
└── ...
```

**Log file:**
```
edge_discovery_live.log
```

---

## What Gets Discovered

### New Edges (Example):
```
======================================================================
NEW EDGE DISCOVERED!
======================================================================

ORB Time: 0900
RR Target: 4.0
SL Mode: FULL

PERFORMANCE:
  Sample Size: 516 trades
  Win Rate: 28.1%
  Wins: 145
  Losses: 371
  Avg R: +0.312
  Total R: +161.0
  Estimated Annual R: +21R/year

Discovered: 2026-01-25 11:52:45
Iteration: 1
Data Source: data/exports/ALL_ORBS_EXTENDED_WINDOWS.csv
```

### Improvements (Example):
```
======================================================================
IMPROVEMENT FOUND!
======================================================================

ORB Time: 1000
Variation: RR+1.0

NEW CONFIGURATION:
  RR Target: 9.0
  SL Mode: FULL
  ORB Filter: None
  Expected R: +0.395
  Win Rate: 14.3%

BASELINE:
  Expected R: +0.378

IMPROVEMENT: +4.5%

Discovered: 2026-01-25 11:52:48
Iteration: 1
```

---

## Edge Criteria

A result must meet ALL of these to be considered an edge:

| Criteria | Minimum |
|----------|---------|
| Sample Size | 100 trades |
| Win Rate | 12% |
| Avg R | +0.10R |
| Annual R | +15R/year |

---

## Iteration Schedule

- **Iteration duration:** ~3 seconds
- **Wait between iterations:** 5 seconds
- **Total cycle:** ~8 seconds
- **30 minutes = ~225 iterations**

Each iteration:
1. Shuffles data (explores different order)
2. Tests all 54 backtest results
3. Compares against validated_setups
4. Saves any discoveries
5. Shows progress

---

## When to Stop

**Stop after 30 minutes if:**
- You found some interesting edges
- No new edges found in last 10 iterations
- You're satisfied with discoveries

**Keep running if:**
- Still finding new edges
- Want comprehensive coverage
- Testing new search strategies

**Safe to interrupt anytime** - all discoveries are already saved!

---

## After Discovery

### 1. Review Results
```powershell
# Check what was found
ls edge_discovery_results/
```

### 2. Analyze Best Edges
Read the `.txt` files for:
- Sample size (need >100 trades)
- Win rate vs RR tradeoff
- Annual R estimate
- How it compares to validated setups

### 3. Test in Execution Engine
```powershell
# Test the new config with execution_engine.py
python strategies/execution_engine.py
```

### 4. Add to Validated Setups (if good)
```powershell
# Update validated_setups database
# Then ALWAYS run:
python test_app_sync.py
```

---

## Troubleshooting

### "No data available"
```powershell
# Check if CSV exists
ls data/exports/ALL_ORBS_EXTENDED_WINDOWS.csv
```

If missing, run backtest first:
```powershell
python research/phase3_backtest_runner.py
```

### "No new edges found"
This is normal! It means:
- Current validated setups are already optimal
- All good configurations already discovered
- Need more backtest data or different RR ranges

### Script crashes
The RUN_EDGE_DISCOVERY.bat file auto-restarts automatically.
Or just run it again manually.

---

## Advanced Usage

### Change Search Criteria

Edit `edge_discovery_live.py`:
```python
# Line 20-23: Adjust thresholds
MIN_TRADES = 50  # Default: 100
MIN_WIN_RATE = 10.0  # Default: 12.0
MIN_AVG_R = 0.05  # Default: 0.10
MIN_ANNUAL_R = 10.0  # Default: 15.0
```

### Add More Instruments

Edit line 16:
```python
INSTRUMENTS = ["MGC", "NQ", "MPL"]  # Add more
```

### Run in Background

```powershell
# PowerShell
Start-Process python -ArgumentList "edge_discovery_live.py" -WindowStyle Hidden
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| **Start** | `python edge_discovery_live.py` |
| **Stop** | `Ctrl+C` |
| **Check results** | `ls edge_discovery_results/` |
| **View log** | `cat edge_discovery_live.log` |
| **Clean results** | `rm -r edge_discovery_results/*` |

---

**Ready to discover edges? Run the command above and let it run for 30 minutes!**

Press Ctrl+C when done, check `edge_discovery_results/` folder, and review your discoveries.

**Good luck! 🎯**
