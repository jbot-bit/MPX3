# MGC (Micro Gold) ORB Trading Strategy - Complete Guide

## 🎯 Purpose
This document contains everything needed to advise on MGC (Micro Gold futures) Opening Range Breakout (ORB) trades for the **2300 ORB** and **0030 ORB** sessions.

---

## 📊 VALIDATED SETUPS (Current as of Jan 16, 2026)

### **2300 ORB (11:00 PM - Sydney/Brisbane Time)**
- **Tier:** S+ (BEST OVERALL SETUP!)
- **Risk/Reward:** 1.5R
- **Stop Loss Mode:** HALF (midpoint of ORB)
- **ORB Size Filter:** < 15.5% of ATR (~6.2pts when ATR=40)
- **Position Risk:** 0.50% (night setup)
- **Performance:** ~+105R/year (best performer)
- **Win Rate:** 59%
- **Frequency:** 63% of nights
- **Scan Window:** 2300-0900 next day (10 hours - captures full overnight moves)

### **0030 ORB (12:30 AM - Sydney/Brisbane Time)**
- **Tier:** S
- **Risk/Reward:** 3.0R
- **Stop Loss Mode:** HALF (midpoint of ORB)
- **ORB Size Filter:** < 11.2% of ATR (~4.5pts when ATR=40)
- **Position Risk:** 0.50% (night setup)
- **Performance:** ~+66R/year
- **Win Rate:** 54%
- **Frequency:** 47% of nights
- **Scan Window:** 0030-0900 next day (8.5 hours - captures full overnight moves)

---

## 🕐 TIME ZONES & SCHEDULE

**Local Time:** Australia/Brisbane (UTC+10, no DST)

**Tonight's Sessions:**
- **2300 ORB:** 23:00-23:05 (5-minute window)
- **0030 ORB:** 00:30-00:35 (5-minute window, next day)

**What Happens:**
1. **23:00-23:05**: Watch price form a 5-minute range (ORB high/low)
2. **23:05+**: Wait for breakout (5-min close OUTSIDE the range)
3. **Enter:** When 5-min candle closes above high (LONG) or below low (SHORT)
4. **00:30-00:35**: Second ORB window forms
5. **00:35+**: Wait for breakout again

---

## 📏 ENTRY RULES

### **Step 1: Form the ORB (5-minute window)**
- Note the **high** and **low** during the 5-minute window
- Calculate **ORB size** = high - low

### **Step 2: Check the Filter**
- Get current **ATR (20-period)**
- **2300 Filter:** ORB size must be < 0.155 × ATR
  - Example: ATR=40 → Filter=6.2pts → ORB must be < 6.2pts
- **0030 Filter:** ORB size must be < 0.112 × ATR
  - Example: ATR=40 → Filter=4.5pts → ORB must be < 4.5pts
- **If filter fails:** SKIP the setup (no trade)

### **Step 3: Wait for Breakout**
- Watch for 5-minute candle **close** outside the ORB
- **LONG:** Close > ORB high
- **SHORT:** Close < ORB low

### **Step 4: Calculate Levels**

**For 2300 ORB (1.5R, HALF SL):**
```
ORB Midpoint = (High + Low) / 2

IF LONG:
  Entry = ORB High
  Stop = ORB Midpoint
  Risk = Entry - Stop
  Target = Entry + (Risk × 1.5)

IF SHORT:
  Entry = ORB Low
  Stop = ORB Midpoint
  Risk = Stop - Entry
  Target = Entry - (Risk × 1.5)
```

**For 0030 ORB (3.0R, HALF SL):**
```
ORB Midpoint = (High + Low) / 2

IF LONG:
  Entry = ORB High
  Stop = ORB Midpoint
  Risk = Entry - Stop
  Target = Entry + (Risk × 3.0)

IF SHORT:
  Entry = ORB Low
  Stop = ORB Midpoint
  Risk = Stop - Entry
  Target = Entry - (Risk × 3.0)
```

### **Step 5: Position Sizing**
- **Risk per trade:** 0.50% of account
- **Example (100k account):**
  - Risk dollars = $500
  - If risk = 2.5pts → Position size = $500 / ($10 × 2.5) = 20 micro contracts
  - MGC = $10/point × micro multiplier

---

## 🎯 ENTRY CHECKLIST

### **Before Entering:**
- [ ] ORB window completed (5 minutes)
- [ ] ORB high and low noted
- [ ] ORB size calculated
- [ ] ATR confirmed (current 20-period ATR)
- [ ] Filter checked (ORB < X% of ATR)
- [ ] Filter PASSED
- [ ] 5-min candle closed OUTSIDE range
- [ ] Entry price = ORB high (LONG) or ORB low (SHORT)
- [ ] Stop calculated (midpoint for both setups)
- [ ] Target calculated (1.5R for 2300, 3.0R for 0030)
- [ ] Position size calculated (0.50% risk)

---

## 🚫 DO NOT TRADE IF:

### **Filter Fails:**
- ORB size TOO LARGE (> filter threshold)
- This means range is too wide, breakout less reliable

### **No Clear Breakout:**
- Price touches but doesn't CLOSE outside range
- Multiple false breakouts (whipsaw)

### **Risk Too High:**
- Account already down for the day/week
- Position size would exceed limits

### **Data Issues:**
- Missing bars (data gaps)
- Unusual price spikes (bad data)

---

## 📐 EXAMPLE TRADE CALCULATION

### **2300 ORB Example:**

**Scenario:**
- ATR = 42.15pts
- ORB forms: High = 2655.20, Low = 2652.40
- ORB size = 2.80pts

**Check Filter:**
- Filter threshold = 42.15 × 0.155 = 6.53pts
- ORB size (2.80pts) < 6.53pts ✅ PASS

**Breakout:**
- 23:10 candle closes at 2656.50 (above 2655.20)
- Direction: LONG

**Calculate Levels:**
```
Entry = 2655.20
Midpoint = (2655.20 + 2652.40) / 2 = 2653.80
Stop = 2653.80
Risk = 2655.20 - 2653.80 = 1.40pts
Target = 2655.20 + (1.40 × 1.5) = 2657.30

Trade:
  LONG @ 2655.20
  Stop @ 2653.80 (-1.40pts)
  Target @ 2657.30 (+2.10pts)
  R:R = 1:1.5
```

**Position Sizing (100k account, 0.50% risk):**
```
Risk $ = $500
Risk pts = 1.40pts
MGC = $10/point
Contracts = $500 / ($10 × 1.40) = 35.7 → 35 micro contracts
```

---

## 🧠 STRATEGY INTELLIGENCE

### **Why These Setups Work:**

**2300 ORB (S+ Tier):**
- Catches overnight moves in gold
- NY session closing, Asian session opening
- Institutional flows create strong directional moves
- HALF stop reduces risk on tight ORBs
- Small filter (15.5%) ensures high-quality setups
- 63% frequency = trades often

**0030 ORB (S Tier):**
- Pure Asian session momentum
- Less noise than NY hours
- 3.0R target catches bigger moves
- Tighter filter (11.2%) = only best setups
- 47% frequency = selective but profitable

### **Why HALF Stop?**
- Both setups use midpoint as stop
- Reduces risk by 50% vs FULL stop
- Still profitable due to extended scan windows (10hrs for 2300, 8.5hrs for 0030)
- Allows larger position size for same dollar risk

### **Why These Filters?**
- **2300: 15.5% ATR** - Allows slightly larger ORBs, trades more often
- **0030: 11.2% ATR** - Tighter filter, more selective, higher quality
- Filters eliminate wide choppy ranges (low win rate)
- Only trade compressed ranges = explosive breakouts

---

## 📈 PERFORMANCE DATA (2024-01-01 to 2026-01-10)

### **2300 ORB:**
- Total R: +105R/year (BEST)
- Win Rate: 59%
- Avg R: +0.51R per trade
- Max Drawdown: -8.2R
- Consecutive Wins: 7
- Consecutive Losses: 4
- Best Trade: +3.8R
- Worst Trade: -1.0R (half stop)

### **0030 ORB:**
- Total R: +66R/year
- Win Rate: 54%
- Avg R: +0.38R per trade
- Max Drawdown: -11.5R
- Consecutive Wins: 6
- Consecutive Losses: 5
- Best Trade: +5.2R (3.0R target allows big wins)
- Worst Trade: -1.0R (half stop)

---

## 🎯 TONIGHT'S TRADING PLAN

### **What to Ask ChatGPT:**

"Based on current MGC price and ATR:
1. What is the current ATR (20-period)?
2. What are the filter thresholds for 2300 and 0030 ORBs?
3. If 2300 ORB forms at [high] to [low], does it pass the filter?
4. What are my entry/stop/target levels for LONG and SHORT?
5. What position size should I use (account = $X)?
6. Should I take both setups or just one?"

### **Decision Tree:**

```
2300 ORB (23:00-23:05):
├─ ORB forms
├─ Calculate size
├─ Check filter (< 15.5% ATR)
│  ├─ PASS → Wait for breakout
│  │  ├─ Breakout LONG → Enter (1.5R, HALF SL, 0.50% risk)
│  │  └─ Breakout SHORT → Enter (1.5R, HALF SL, 0.50% risk)
│  └─ FAIL → SKIP (wait for 0030)
│
0030 ORB (00:30-00:35):
├─ ORB forms
├─ Calculate size
├─ Check filter (< 11.2% ATR)
│  ├─ PASS → Wait for breakout
│  │  ├─ Breakout LONG → Enter (3.0R, HALF SL, 0.50% risk)
│  │  └─ Breakout SHORT → Enter (3.0R, HALF SL, 0.50% risk)
│  └─ FAIL → SKIP (no more night setups)
```

---

## 🚨 CRITICAL REMINDERS

### **Scan Window Bug (FIXED Jan 16, 2026):**
- **OLD BUG:** Scans stopped after 85 minutes (missed big moves!)
- **NEW FIX:** Scans until 09:00 next day (captures full overnight runs)
- **RESULT:** System improved from +400R/year to +600R/year (+50%!)
- All performance data above is CORRECTED with extended scan windows

### **DO NOT:**
- Enter before 5-min close confirms breakout
- Trade if filter fails (too risky)
- Use FULL stop (these setups validated with HALF)
- Adjust RR targets (1.5R for 2300, 3.0R for 0030 are optimal)
- Skip the filter check (critical for edge)

### **DO:**
- Wait patiently for filter to pass
- Enter EXACTLY at ORB high/low (not chase)
- Use HALF stop (midpoint)
- Risk exactly 0.50% per trade
- Track all trades in journal
- Follow scan windows (don't exit early!)

---

## 💾 QUICK REFERENCE CARD

```
═══════════════════════════════════════════════
        MGC NIGHT ORB QUICK REFERENCE
═══════════════════════════════════════════════

2300 ORB (23:00-23:05 Brisbane Time)
────────────────────────────────────────────
  Tier: S+ (BEST SETUP!)
  RR: 1.5R
  Stop: HALF (midpoint)
  Filter: < 15.5% ATR (~6.2pts @ ATR=40)
  Risk: 0.50% of account
  Performance: +105R/year, 59% WR

0030 ORB (00:30-00:35 Brisbane Time)
────────────────────────────────────────────
  Tier: S
  RR: 3.0R
  Stop: HALF (midpoint)
  Filter: < 11.2% ATR (~4.5pts @ ATR=40)
  Risk: 0.50% of account
  Performance: +66R/year, 54% WR

ENTRY FORMULA:
────────────────────────────────────────────
1. ORB forms → Note high/low
2. Check: Size < (ATR × Filter%)
3. Breakout: 5-min close outside range
4. Entry: ORB high (LONG) or low (SHORT)
5. Stop: (High + Low) / 2
6. Target: Entry ± (Risk × RR)
7. Size: (Risk$ / Risk pts) / $10

═══════════════════════════════════════════════
```

---

## 📞 PROMPT FOR CHATGPT

**Copy/paste this to ChatGPT tonight:**

```
I'm trading MGC (Micro Gold) tonight using ORB breakout strategy.

CURRENT DATA:
- MGC Price: $____
- ATR (20): ____pts

SETUPS AVAILABLE:
1. 2300 ORB (23:00-23:05): RR=1.5R, HALF SL, Filter<15.5% ATR, Risk=0.50%
2. 0030 ORB (00:30-00:35): RR=3.0R, HALF SL, Filter<11.2% ATR, Risk=0.50%

QUESTIONS:
1. What are the filter thresholds (in points)?
2. If 2300 ORB forms at High=$____ Low=$____, does it pass the filter?
3. What direction breakout (LONG/SHORT)?
4. What are my Entry/Stop/Target levels?
5. What position size (account=$100,000, risk=0.50%)?
6. Should I take this trade?
7. Any concerns or recommendations?

Please calculate all levels and advise whether to take the trade.
```

---

## ✅ FINAL CHECKLIST

Before asking ChatGPT tonight:
- [ ] Get current MGC price
- [ ] Get current ATR (20-period)
- [ ] Have your account size ready
- [ ] Know your risk tolerance (0.50% standard)
- [ ] Ready to enter trades manually
- [ ] Alerts set for 23:00 and 00:30

**This document contains EVERYTHING ChatGPT needs to advise you on tonight's MGC trades!**

---

**Last Updated:** January 16, 2026
**Data Source:** gold.db → validated_setups table (post scan-window bug fix)
**Performance:** Verified 2024-01-01 to 2026-01-10 (2 years)
