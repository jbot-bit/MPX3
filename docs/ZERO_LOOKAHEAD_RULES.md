# ZERO LOOKAHEAD RULES

## The Problem We Fixed

**OLD SYSTEM (INVALID):**
"Trade 11:00 UP during Asia EXPANDED sessions" → **You don't know Asia is EXPANDED until 17:00!**

This creates **lookahead bias** - using future information to make past decisions. All backtests using session types were INVALID for real trading.

---

## Session Structure (Correct)

Every major open has **3 components**:

### 1. PRE Block (Positioning)
Available **AT** the open. Use this for trading decisions.

### 2. ORB (Execution)
5-minute opening range breakout.

### 3. SESSION (Outcome)
Known **AFTER** the session closes. Analytics only.

---

## Complete Map

### 🌑 PRE-ASIA
- **Time**: 07:00–09:00 local
- **Available at**: 09:00 (when Asia opens)
- **Use for**: 09:00, 10:00, 11:00 ORB decisions
- **Features**: range, high, low, volume

### 🌏 ASIA SESSION
- **Time**: 09:00–17:00 local
- **ORBs**: 09:00, 10:00, 11:00
- **Available at**: 17:00 (when session closes)
- **Use for**: 18:00 ORB decisions, next day context

### 🌗 PRE-LONDON
- **Time**: 17:00–18:00 local
- **Available at**: 18:00 (when London opens)
- **Use for**: 18:00 ORB decisions
- **Features**: range, high, low, stop runs

### 🇬🇧 LONDON SESSION
- **Time**: 18:00–23:00 local
- **ORB**: 18:00
- **Available at**: 23:00 (when session closes)
- **Use for**: 23:00 ORB decisions

### 🌆 PRE-NY
- **Time**: 23:00–00:30 local
- **Available at**: 00:30 (when NYSE opens)
- **Use for**: 00:30 ORB decisions
- **Features**: NY Futures positioning, range, reversals

### 🇺🇸 NY FUTURES OPEN
- **Time**: 23:00
- **ORB**: 23:00–23:05
- **Available at**: 23:00
- **Use for**: Immediate trading at NY Futures open

### 🇺🇸 NYSE CASH OPEN
- **Time**: 00:30
- **ORB**: 00:30–00:35
- **Available at**: 00:30
- **Use for**: NYSE cash market open trading

---

## What Each ORB Can See (Zero Lookahead)

### 09:00 ORB (Asia Open)
✅ **Available:**
- PRE_ASIA range (07:00-09:00)
- Previous day ASIA, LONDON, NY (completed sessions)
- ATR, overnight gap
- Previous ORB outcomes

❌ **NOT Available:**
- Current Asia range (won't know until 17:00)
- Asia session type (TIGHT/EXPANDED - calculated at 17:00)
- Any 10:00, 11:00 data

### 10:00 ORB (Asia Mid)
✅ **Available:**
- PRE_ASIA range (07:00-09:00)
- ASIA_SO_FAR (09:00-10:00 range)
- 09:00 ORB result
- Previous day data

❌ **NOT Available:**
- Full Asia range (17:00)
- 11:00 ORB data
- London/NY data

### 11:00 ORB (Asia Late)
✅ **Available:**
- PRE_ASIA range (07:00-09:00)
- ASIA_SO_FAR (09:00-11:00 range)
- 09:00, 10:00 ORB results
- Previous day data

❌ **NOT Available:**
- Full Asia range (won't know until 17:00)
- Anything after 11:00

### 18:00 ORB (London Open)
✅ **Available:**
- PRE_LONDON range (17:00-18:00)
- **Completed ASIA session** (09:00-17:00 - NOW we know Asia type!)
- All Asia ORBs (09:00, 10:00, 11:00 results)
- Previous London/NY data

❌ **NOT Available:**
- Current London range
- 23:00, 00:30 data

### 23:00 ORB (NY Futures Open)
✅ **Available:**
- **Completed LONDON session** (18:00-23:00 - NOW we know London type!)
- Completed ASIA session
- 18:00 ORB result
- Previous NY data

❌ **NOT Available:**
- PRE_NY range (happens 23:00-00:30, we're at 23:00)
- 00:30 data

### 00:30 ORB (NYSE Cash Open)
✅ **Available:**
- **PRE_NY range** (23:00-00:30 - NOW we know it!)
- Completed LONDON session
- Completed ASIA session
- 23:00 ORB result (NY Futures)

❌ **NOT Available:**
- Future NY session outcome

---

## Correct Trading Rules (Zero Lookahead)

### Rule 1: 09:00 ORB
**Decision made at 09:00 using:**
- PRE_ASIA range (07:00-09:00) - just completed
- Yesterday's sessions
- ATR

**Example**: "If PRE_ASIA range > 50 ticks, trade 09:00 UP"

### Rule 2: 10:00 ORB
**Decision made at 10:00 using:**
- PRE_ASIA range
- 09:00-10:00 price action
- 09:00 ORB outcome

**Example**: "If 09:00 ORB was WIN and price > PRE_ASIA high, trade 10:00 UP"

### Rule 3: 11:00 ORB
**Decision made at 11:00 using:**
- PRE_ASIA range
- 09:00-11:00 price action
- 09:00, 10:00 ORB outcomes

**Example**: "If both 09:00 and 10:00 ORBs failed, trade 11:00 UP"

### Rule 4: 18:00 ORB
**Decision made at 18:00 using:**
- PRE_LONDON range (17:00-18:00) - just completed
- **Completed ASIA session** (09:00-17:00) - we NOW know if it was EXPANDED!
- All Asia ORB results

**Example**: "If PRE_LONDON range < 20 ticks AND Asia was EXPANDED, trade 18:00 UP"

### Rule 5: 23:00 ORB (NY Futures)
**Decision made at 23:00 using:**
- **Completed LONDON session** (18:00-23:00) - we NOW know the type!
- Completed ASIA
- 18:00 ORB result

**Example**: "If London range > 100 ticks (EXPANSION), trade 23:00 UP"

### Rule 6: 00:30 ORB (NYSE Cash)
**Decision made at 00:30 using:**
- **PRE_NY range** (23:00-00:30) - just completed
- Completed LONDON
- 23:00 ORB result

**Example**: "If PRE_NY range > 30 ticks AND 23:00 was WIN, trade 00:30 continuation"

---

## Feature Categories

### ✅ PRE Features (Tradeable - Zero Lookahead)
- `pre_asia_range` - Use at 09:00, 10:00, 11:00
- `pre_london_range` - Use at 18:00
- `pre_ny_range` - Use at 00:30
- Previous day completed sessions
- ATR, RSI (calculated from past data)

### ⚠️ SESSION Features (Analytics Only - Lookahead!)
- `asia_range` - Don't use until 17:00+
- `asia_type` (TIGHT/EXPANDED) - Don't use until 17:00+
- `london_range` - Don't use until 23:00+
- `london_type` - Don't use until 23:00+
- `ny_range` - Don't use until next day

### ✅ Derived Features (Tradeable if properly lagged)
- `asia_range_PREVIOUS_DAY` - Use anytime (it's historical)
- `london_type_PREVIOUS_DAY` - Use anytime
- `09:00_ORB_outcome` - Use at 10:00+ (it's completed)
- `18:00_ORB_outcome` - Use at 23:00+ (it's completed)

---

## Testing for Lookahead Bias

For any trading rule, ask:

1. **What time is the decision made?**
2. **What time was this data known?**
3. **If data known AFTER decision time = LOOKAHEAD BIAS**

Example:
- Rule: "Trade 11:00 UP if Asia is EXPANDED"
- Decision time: 11:00
- Data known: 17:00 (Asia closes)
- **INVALID** - 6 hours of lookahead!

Correct version:
- Rule: "Trade 11:00 UP if PRE_ASIA range > 50 ticks"
- Decision time: 11:00
- Data known: 09:00 (PRE_ASIA just closed)
- **VALID** - 2 hours of historical data

---

## Migration Path

### Step 1: Rebuild Features
```bash
python build_daily_features_v2.py 2024-01-01 2026-01-10
```

Creates `daily_features_v2` table with:
- PRE blocks (zero lookahead)
- SESSION blocks (flagged as analytics)
- All ORBs

### Step 2: Update Analysis Tools
- Modify backtests to use only PRE features + lagged SESSION features
- Update alerts to use real-time available data
- Flag any SESSION feature usage with lookahead warnings

### Step 3: Validate Backtests
- Re-run all backtests with V2 features
- Compare results (should be different/worse - that's expected and correct!)
- Document real, tradeable edges

---

## Key Insight

**The old 57.9% win rate for "11:00 UP during Asia EXPANDED" is invalid.**

The new, correct analysis will show what we can ACTUALLY achieve using:
- PRE_ASIA range at 09:00
- Completed Asia by 18:00
- Real-time available indicators

This is harder but **honest and tradeable**.

---

**This is the foundation for a real, profitable trading system.**
