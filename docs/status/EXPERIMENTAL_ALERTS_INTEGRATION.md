# EXPERIMENTAL ALERTS - APP INTEGRATION GUIDE

**Status:** ✅ Scanner built, UI component ready
**Next Step:** Add to your trading app

---

## 🎯 What This Does

Your app will now **automatically scan** for experimental strategy conditions and display **🎁 BONUS EDGE alerts** when:

- **Day of week matches** (Tuesday/Monday/Wednesday)
- **Previous Asia was big** (> 1.0 or 1.5 ATR)
- **Current ATR is high** (> 75th percentile)
- **Previous ORB failed** (mean reversion setup)
- **Combined conditions** (Big Asia + Tiny ORB)

**NO MANUAL TRACKING NEEDED** - the app checks everything automatically!

---

## 📁 Files Created

### 1. **`trading_app/experimental_scanner.py`**
   - Core scanning logic
   - Evaluates all 5 filter types
   - Queries experimental_strategies table
   - Returns matching strategies

### 2. **`trading_app/experimental_alerts_ui.py`**
   - Professional trading terminal UI
   - Dark theme with monospace fonts
   - Yellow/gold alert styling (bonus opportunity theme)
   - One-click expandable details

---

## 🔧 How to Integrate

### **Option A: Add to Production Tab (Recommended)**

Add this to your `app_canonical.py` in the PRODUCTION zone:

```python
# At the top, add import:
from experimental_scanner import ExperimentalScanner
from experimental_alerts_ui import render_experimental_alerts

# In the PRODUCTION tab rendering section, add:
st.header("🎁 Experimental Strategy Scanner")

# Create scanner
exp_scanner = ExperimentalScanner(con)

# Render alerts
render_experimental_alerts(exp_scanner, instrument='MGC')
```

### **Option B: Add to Live Scanner Tab**

If you have a live scanner tab, add it there alongside your ACTIVE strategy detector.

### **Option C: Standalone Demo Page**

Test it first with the demo:

```bash
streamlit run trading_app/experimental_alerts_ui.py
```

---

## 🎨 UI Preview

**When matches found (e.g., Tuesday):**

```
┌─────────────────────────────────────────────────────────────────┐
│ 🎁 EXPERIMENTAL EDGES - BONUS OPPORTUNITIES                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ✓ Found 3 matching experimental strategies today               │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ [DAY_OF_WEEK] 1000 RR=3.0 DAY_OF_WEEK (+0.885R)            ││
│ │                                                             ││
│ │ Expected R   Win Rate    Sample Size    Frequency          ││
│ │ +0.885R      53.3%       15 trades      ~7/year            ││
│ │                                                             ││
│ │ 📋 Condition: Tuesday only - 15 historical, ~7/yr          ││
│ │ ✓ Tuesday match                                            ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ [Similar cards for 1000 RR=2.5 and 1000 RR=2.0]               │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │   19          +8.43R         269                            ││
│ │   Total       Annual Bonus   Trades/Year                    ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**When no matches (e.g., Thursday):**

```
┌─────────────────────────────────────────────────────────────────┐
│ 🎁 EXPERIMENTAL EDGES - BONUS OPPORTUNITIES                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   No experimental strategies match today's conditions.          │
│   Your 9 ACTIVE strategies are always available!                │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │   19          +8.43R         269                            ││
│ │   Total       Annual Bonus   Trades/Year                    ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing

### Test the scanner alone:
```bash
python trading_app/experimental_scanner.py
```

**Output:**
- Summary of all 19 experimental strategies
- Today's matches (if any)
- Reasons why conditions match/don't match

### Test the UI component:
```bash
streamlit run trading_app/experimental_alerts_ui.py
```

**Opens demo page** showing:
- Full alerts panel
- Compact badge version

---

## 🔄 How It Works (Technical)

### **Morning workflow:**

1. **You open app** → Scanner initializes
2. **Scanner queries database:**
   - Gets all 19 experimental_strategies (status='ACTIVE')
   - Gets yesterday's Asia range, ATR, 0900 outcome
   - Gets today's ATR, ORB sizes (when available)
   - Calculates ATR 75th percentile
3. **Scanner evaluates each strategy:**
   - DAY_OF_WEEK: Checks if today matches
   - SESSION_CONTEXT: Checks prev_asia_range / prev_atr ratio
   - VOLATILITY_REGIME: Checks current_atr vs 75th percentile
   - COMBINED: Checks BOTH prev Asia AND current ORB size
   - MULTI_DAY: Checks prev_0900_outcome
4. **UI renders results:**
   - Shows matching strategies with green/yellow styling
   - Shows "No matches" if conditions don't align
   - Always shows summary stats

### **During trading day:**

As ORBs form (0900, 1000, 1100), the scanner re-evaluates:
- **COMBINED filters** (need current ORB size)
- Displays alerts for newly available setups

---

## 📊 Current Experimental Strategies (19 total)

| Filter Type | Count | Annual R | Trades/Yr |
|-------------|-------|----------|-----------|
| DAY_OF_WEEK | 7 | +3.32R | ~62 |
| COMBINED | 4 | +2.28R | ~46 |
| SESSION_CONTEXT | 5 | +2.15R | ~76 |
| VOLATILITY_REGIME | 2 | +0.46R | ~68 |
| MULTI_DAY | 1 | +0.22R | ~16 |
| **TOTAL** | **19** | **+8.43R** | **~269** |

**Combined with ACTIVE strategies:**
- 9 ACTIVE + 19 EXPERIMENTAL = 28 total edges
- +76.7R (active) + 8.43R (experimental) = **+85.1R/year**

---

## ⚠️ Important Notes

1. **Experimental strategies need verification:**
   - Small samples (15-70 trades)
   - Paper trade first before live deployment
   - Track actual vs expected results

2. **Database column requirement:**
   - Scanner reads `daily_features_v2` table
   - Needs: `asia_range`, `atr_20`, `orb_*_outcome`, `orb_*_size`
   - All columns exist ✅

3. **Real-time updates:**
   - Use `streamlit-autorefresh` or manual refresh
   - Scanner runs each time app loads
   - No caching (always fresh conditions)

---

## 🎯 Next Steps

1. **Test the scanner:**
   ```bash
   python trading_app/experimental_scanner.py
   ```

2. **Test the UI:**
   ```bash
   streamlit run trading_app/experimental_alerts_ui.py
   ```

3. **Integrate into your app:**
   - Add imports to `app_canonical.py`
   - Add `render_experimental_alerts()` to PRODUCTION tab
   - Test with app running

4. **Paper trade experimentals:**
   - When alerts show, take paper trades
   - Track results for 20-50 occurrences
   - Promote successful ones to ACTIVE

5. **Monday/Tuesday/Wednesday - verify edges:**
   - These are the key days with experimental matches
   - Check if conditions actually work live

---

## 🚀 Benefits

**Before this feature:**
- 9 ACTIVE strategies only
- No way to know when rare conditions match
- Missing 19 bonus opportunities

**After this feature:**
- Auto-scans 19 experimental strategies every day
- Alerts you when conditions match (no manual checking)
- Professional UI shows exactly what's available
- Complete automation of complex filter logic

**You just open the app and trade what it shows!** 🎯

---

**Generated:** 2026-01-29
**Files:** `experimental_scanner.py`, `experimental_alerts_ui.py`
**Status:** Ready for integration
