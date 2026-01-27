# ORB Trading Terminology - Simple Explanation

## The Basics: UP/DOWN vs WIN/LOSS

### UP/DOWN = **Break Direction** (What Happened)
- **UP** = Price broke **ABOVE** the ORB high (bullish breakout)
- **DOWN** = Price broke **BELOW** the ORB low (bearish breakout)
- This is what you see in real-time when price moves

### WIN/LOSS = **Trade Outcome** (Did You Make Money?)
- **WIN** = Price hit your profit target BEFORE hitting your stop loss
- **LOSS** = Price hit your stop loss BEFORE hitting your profit target
- This is only known AFTER the trade closes

---

## Example: "10:00 UP after 09:00 WIN" (Engine B - Outcome Momentum)

This means:
1. **09:00 ORB** happened first (at 9:00 AM)
   - Price broke UP or DOWN (direction)
   - Trade was placed
   - **Trade CLOSED** (hit target or stop) **BEFORE 10:00**
   - Result: **WIN** (made money) - **KNOWN at 10:00**

2. **10:00 ORB** happens next (at 10:00 AM)
   - Price broke **UP** (above the 10:00 ORB high)
   - **AND** we know 09:00 was a WIN (because it's already closed)
   - Historical data shows: When 09:00 wins, 10:00 UP breakouts win **57.9%** of the time (vs 55.5% normally)

**Why This Matters:** It's a **correlation pattern** - winning momentum tends to continue. If the first trade of the day wins, the second trade in the same direction has better odds.

**⚠️ This is Engine B (Outcome Momentum)** - used for intra-Asia ORBs only, NOT for Asia → London.
- See `ORB_OUTCOME_MOMENTUM.md` for details
- For Asia → London, use Engine A (see `ASIA_LONDON_FRAMEWORK.md`)

### ⚠️ CRITICAL: Zero-Lookahead Requirement

**"10:00 UP after 09:00 WIN" is ONLY valid if:**
- The 09:00 trade is **CLOSED** (WIN or LOSS) before 10:00
- You can **truthfully** know the outcome at decision time

**If 09:00 trade is still OPEN at 10:00:**
- You **CANNOT** use "09:00 WIN" as a condition
- You must track trade state separately:
  - `09_outcome = WIN/LOSS` (only if closed/decided)
  - `09_state = OPEN/FLAT/UNKNOWN`
  - `09_realized = WIN/LOSS/UNKNOWN`

**In practice:** Most ORB trades close quickly (within minutes), so this correlation is usually valid. But you must verify the previous trade is closed before using its outcome.

---

## Understanding "R" (Risk Units)

### What is "1R"?
**1R = One unit of risk** - the dollar amount you could lose on a trade.

**In ORB trading:**
- **1R = Distance from your entry to your stop loss**
- If you enter at $2,500.00 and stop at $2,499.50, your risk is $0.50
- That $0.50 is "1R" for that trade

### Risk/Reward Ratio (RR)
- **RR = How many R's you're targeting for profit**
- RR = 1.0 means you're trying to make 1R profit (risk $0.50 to make $0.50)
- RR = 2.0 means you're trying to make 2R profit (risk $0.50 to make $1.00)
- RR = 3.0 means you're trying to make 3R profit (risk $0.50 to make $1.50)

### Two Definitions of R (Technical Note)
This system uses **two ways to measure R**, depending on what you're analyzing:

1. **Entry-Anchored R** (Real Trading)
   - 1R = Distance from **entry price** to stop
   - Used when you're actually trading (because you enter at market prices)
   - Example: Enter at $2,500.20, stop at $2,499.50 → 1R = $0.70

2. **ORB-Anchored R** (Structural Analysis)
   - 1R = Distance from **ORB edge** to stop
   - Used for analyzing how ORBs behave structurally
   - Example: ORB high at $2,500.00, stop at $2,499.50 → 1R = $0.50

**For beginners:** Focus on entry-anchored R - it's how you'll think about risk when trading. See `R_DEFINITIONS.md` if you want the full technical explanation.

---

## Trading Sessions & ORB Times

### Session Definitions (All times in Australia/Brisbane - UTC+10)

**Three Major Sessions:**
1. **ASIA Session**: 09:00 - 17:00 local
   - Primary trading window for Australian/Asian traders
   - Includes 09:00, 10:00, and 11:00 ORBs
   - Generally highest quality setups

2. **LONDON Session**: 18:00 - 23:00 local
   - European market hours
   - Includes 18:00 ORB
   - Medium volatility

3. **NEW YORK (NY) Session**: 23:00 - 02:00 local (next day)
   - US market hours
   - Includes 23:00 and 00:30 ORBs
   - Late night for Australian traders

### All Six ORB Times

**Primary ORBs (Asia Session):**
- **09:00 ORB** (09:00-09:05) - Asia Open
  - Most reliable edge
  - Best when PRE_ASIA travel > 50 ticks

- **10:00 ORB** (10:00-10:05) - Asia Mid
  - **Strongest standalone edge** (55.5% win rate)
  - Even better after 09:00 WIN (57.9%)

- **11:00 ORB** (11:00-11:05) - Asia Late Morning
  - Best with correlation patterns
  - Works well after 09:00 + 10:00 outcomes

**Secondary ORBs (Evening/Night Sessions):**
- **18:00 ORB** (18:00-18:05) - London Open
  - European session start
  - Lower sample size, less tested

- **23:00 ORB** (23:00-23:05) - NY Open
  - US market open
  - Late night for Australian traders

- **00:30 ORB** (00:30-00:35) - NY Early
  - Mid-NY session
  - Very late for Australian traders

### Trading Day Definition

**Trading day runs: 09:00 local → next 09:00 local**
- All session stats are calculated within this 24-hour window
- Example: Monday's trading day starts Monday 09:00, ends Tuesday 09:00
- This aligns with the Asia Open ORB strategy

### Time Zone Note

**All times are Australia/Brisbane (UTC+10, no DST)**
- This is the local timezone for the primary trader
- Database stores all times as UTC internally
- Session windows are defined in local time, then converted to UTC for queries

### Two Trading Engines (KEEP SEPARATE)

This system uses **TWO DIFFERENT** trading frameworks. Do not mix them.

#### Engine A: Liquidity / Inventory Logic (Session → Session)

**Used for:** Asia → London transitions
**Based on:** Prior-session inventory resolution (NY/London highs/lows from previous day)
**Logic:** If Asia resolved prior HIGH → London LONG (+0.15R edge)

**Example:**
- Prior NY high (yesterday): $2,500.00
- Asia high (today): $2,501.00 ✅ (resolved prior inventory)
- **London decision:** ONLY trade London LONG breaks
- **Not based on:** Asia ORB outcomes (WIN/LOSS)

See `ASIA_LONDON_FRAMEWORK.md` for complete details.

#### Engine B: Outcome Momentum (ORB → ORB Within Session)

**Used for:** Intra-Asia ORB correlations (09:00 → 10:00 → 11:00)
**Based on:** Prior ORB outcomes (WIN/LOSS) if trade is closed
**Logic:** If 09:00 WIN (closed) → 10:00 UP has 57.9% WR vs 55.5% baseline

**Example:**
- 09:00 ORB broke UP at 09:06
- 09:00 trade hit TP at 09:18 ✅ (WIN, closed before 10:00)
- **10:00 decision:** Higher confidence for 10:00 UP (57.9% vs 55.5%)
- **Not based on:** Prior-session inventory

**⚠️ CRITICAL:** Only use if prior ORB trade is CLOSED. If still OPEN, use baseline stats.

See `ORB_OUTCOME_MOMENTUM.md` for complete details.

#### DO NOT MIX ENGINES

**Wrong:** "Asia resolved prior high AND 09:00 was a WIN → London LONG"
- These are different frameworks, don't combine

**Right:**
- Use Engine A for London: "Asia resolved prior high → London LONG"
- Use Engine B for 10:00: "09:00 WIN (closed) → 10:00 UP higher confidence"

---

## How ORB Trading Works

### What is an ORB?
**Opening Range Breakout** - A 5-minute range at market open:
- **ORB High** = Highest price in first 5 minutes
- **ORB Low** = Lowest price in first 5 minutes
- **ORB Range** = High - Low

### The Trade Setup
1. **Wait** for the 5-minute ORB to complete
2. **Watch** for price to break above (UP) or below (DOWN) the ORB
3. **Enter** when price breaks out
4. **Stop Loss** = Opposite side of ORB (if UP break, stop = ORB low)
5. **Profit Target** = RR × Risk (e.g., 1R, 1.5R, 2R, etc.)

**Example:**
- ORB High: $2,500.00
- ORB Low: $2,499.50
- ORB Range: $0.50 (5 ticks)

**UP Breakout Trade:**
- Entry: $2,500.00 (when price breaks above)
- Stop: $2,499.50 (ORB low)
- Risk (1R): $0.50 per contract (entry - stop)
- Target: Depends on RR setting
  - If RR = 1.0: $2,500.50 (entry + 1 × $0.50 = 1R profit)
  - If RR = 2.0: $2,501.00 (entry + 2 × $0.50 = 2R profit)
  - If RR = 3.0: $2,501.50 (entry + 3 × $0.50 = 3R profit)
- **Formula: Target = Entry ± (RR × Risk)**

**Note on R Definitions:**
This example uses **entry-anchored R** (risk = entry - stop), which is how most traders think about risk/reward in real-time. The system also tracks **ORB-anchored R** (risk = ORB edge - stop) for structural analysis. See `R_DEFINITIONS.md` for full technical details.

---

## How This Helps You Trade

### Real-Time Trading Flow

#### **Before 09:00 (Morning Prep)**
Run: `python daily_alerts.py`
- Shows what setups are available today
- Shows historical win rates for current conditions
- Tells you which ORBs to watch

#### **At 09:00 (Asia Open)**
1. **Check PRE_ASIA range** (07:00-09:00)
   - If > 50 ticks → Trade 09:00 ORB
   - If < 30 ticks → Skip 09:00

2. **Wait for ORB to form** (09:00-09:05)
3. **Watch for breakout** (after 09:05)
4. **Enter trade** if breakout happens
5. **Record outcome** (WIN/LOSS) for tomorrow's correlations

#### **At 10:00 (Asia Mid)**
1. **Check 09:00 trade state:**
   - ✅ **If 09:00 trade is CLOSED** → Check outcome (WIN/LOSS)
   - ⚠️ **If 09:00 trade is still OPEN** → Cannot use outcome (state = OPEN/UNKNOWN)
2. **Wait for 10:00 ORB** (10:00-10:05)
3. **Watch for breakout**
4. **If 09:00 was CLOSED and WIN, and 10:00 breaks UP:**
   - Higher confidence (57.9% win rate vs 55.5%)
   - Consider larger position size
5. **If 09:00 was CLOSED and LOSS:**
   - Still trade 10:00 UP (52.7% win rate)
   - But lower confidence
6. **If 09:00 is still OPEN:**
   - Use baseline 10:00 UP stats (55.5% win rate)
   - Cannot use correlation pattern

#### **At 11:00 (Asia Late)**
1. **Check both 09:00 and 10:00 trade states:**
   - ✅ **If both CLOSED** → Use outcomes for correlation
   - ⚠️ **If either still OPEN** → Cannot use that outcome
2. **Best setups (only if both previous trades are CLOSED):**
   - 09:00 WIN + 10:00 WIN → 11:00 UP (57.4% WR)
   - 09:00 LOSS + 10:00 WIN → 11:00 DOWN (57.7% WR)
3. **If trades still open:**
   - Use baseline stats or simpler filters (e.g., PRE_ASIA > 50 ticks)
   - Skip correlation-based patterns

---

## Practical Example: Trading Today

### Scenario: It's 10:00 AM

**What you know:**
- 09:00 ORB happened
- 09:00 broke UP
- **09:00 trade state: CLOSED** ✅
- 09:00 trade: **WIN** (hit target before 10:00)

**What you're watching:**
- 10:00 ORB forming (10:00-10:05)
- Price is near the ORB high

**Your decision:**
- If price breaks UP above 10:00 ORB high → **ENTER**
- Why? Historical data shows: "10:00 UP after 09:00 WIN" = 57.9% win rate
- This is better than the baseline 55.5% win rate
- You have **higher confidence** this will work

**If price breaks DOWN:**
- Skip it (10:00 DOWN after 09:00 WIN = only 49.3% win rate)
- Not worth the risk

### Alternative Scenario: 09:00 Trade Still Open

**What you know:**
- 09:00 ORB happened
- 09:00 broke UP
- **09:00 trade state: OPEN** ⚠️ (still running, hasn't hit target or stop)

**What you're watching:**
- 10:00 ORB forming (10:00-10:05)
- Price is near the ORB high

**Your decision:**
- If price breaks UP above 10:00 ORB high → **ENTER**
- **BUT:** Cannot use "after 09:00 WIN" correlation (09:00 outcome unknown)
- Use baseline 10:00 UP stats: 55.5% win rate
- Still tradeable, but lower confidence than correlation pattern

---

## Key Takeaways

1. **UP/DOWN** = Direction of breakout (real-time)
2. **WIN/LOSS** = Trade result (known **ONLY after trade closes**)
3. **Correlations** = Patterns that improve your odds
   - "10:00 UP after 09:00 WIN" = 57.9% vs 55.5% baseline
   - **BUT:** Only valid if previous trade is CLOSED
   - Use this to size positions and filter trades

4. **Zero Lookahead** = Only use info available NOW
   - Can use: PRE_ASIA range (known at 09:00)
   - Can use: Previous ORB outcomes **IF CLOSED** (known after they close)
   - Cannot use: Previous ORB outcomes if still OPEN
   - Cannot use: Session types (not known until session ends)

5. **Trade State Tracking:**
   - `outcome = WIN/LOSS` (only if closed/decided)
   - `state = OPEN/FLAT/UNKNOWN` (current position status)
   - Always verify trade is closed before using outcome in correlations

6. **Best Edge:** 10:00 UP breakout
   - Works 55.5% of the time standalone
   - Works 57.9% after 09:00 WIN (if 09:00 is closed)
   - This is your bread and butter trade

7. **Risk/Reward (RR):**
   - **1R = Your risk** (distance from entry to stop)
   - **Target = Entry ± (RR × 1R)**
   - System tests multiple RR values (1.0, 1.5, 2.0, 3.0, etc.)
   - Higher RR = larger target, lower win rate, potentially higher profit per trade
   - **Note:** The system uses two R definitions - see `R_DEFINITIONS.md` for details:
     - **Entry-anchored R**: Risk from your actual entry price (used in real trading)
     - **ORB-anchored R**: Risk from ORB edge (used for structural analysis)

---

## Tools to Use

1. **Morning Prep:** `python daily_alerts.py`
   - Shows today's setups

2. **Real-Time Signals:** `python realtime_signals.py --time 1000`
   - Shows what's available right now
   - Shows historical performance

3. **Edge Discovery:** Use the Streamlit app
   - Discover new patterns
   - Test different filters

4. **End of Day:** Record outcomes
   - Track outcomes for all ORBs (09:00, 10:00, 11:00, 18:00, 23:00, 00:30)
   - Primary focus on Asia session (09:00, 10:00, 11:00)
   - Use for tomorrow's correlations

---

## Remember

- **Win rates are 50-58%** (not 70%+)
- **This is honest, tradeable data**
- **Small edges compound over time**
- **Risk management is critical**
- **Only trade when conditions match**

---

## Glossary of Advanced Terms

### Prior Inventory
**Definition:** High/low levels from previous trading day's sessions (NY and London)
**Usage:** "Did Asia resolve prior inventory?"
**Example:** If yesterday's NY high was $2,500, that's prior inventory for today's Asia session

### Resolve / Resolution
**Definition:** When price sweeps through and accepts beyond a prior inventory level
**Types:**
- **Resolved prior HIGH:** Price swept above prior session high
- **Resolved prior LOW:** Price swept below prior session low
**Example:** Asia high = $2,501, prior NY high = $2,500 → Asia resolved prior HIGH

### Continuation
**Definition:** Trading in the SAME direction as the prior session's resolution
**Example:** Asia resolved prior HIGH → London LONG (continuation)
**Edge:** +0.15R vs baseline
**Why it works:** Inventory handoff - accepting price beyond prior levels

### Fade (TOXIC)
**Definition:** Trading AGAINST the direction of prior session's resolution
**Example:** Asia resolved prior HIGH → London SHORT (fade) ❌
**Edge:** -0.37R (worst pattern in system)
**Why avoid:** Fighting accepted price structure

### Compression
**Definition:** When a session fails to resolve prior inventory (stays in range)
**Result:** Range contraction → next session expects expansion
**Example:** Asia doesn't touch prior NY/London highs or lows
**Edge:** ~+0.10R for next session (London)

### Clean Trend
**Definition:** A session that trends without touching any prior inventory
**Behavior:** Looks strong, but often toxic for next session
**Action:** Skip the next session ORB
**Example:** Asia trends up from $2,490 to $2,500, but prior NY high was $2,485 (never touched)

### Break Direction
**Definition:** Whether price broke UP (above ORB high) or DOWN (below ORB low)
**Not the same as:** Trade outcome (WIN/LOSS)
**Usage:** "10:00 broke UP" means price went above the 10:00 ORB high

### Trade Outcome
**Definition:** Whether the trade hit target (WIN) or stop (LOSS)
**Only known:** After trade closes
**Usage:** "10:00 UP was a WIN" means the trade that broke up hit its target

### Session Label / Session Type
**Definition:** Categorization of session behavior (e.g., trend, chop, sweep)
**⚠️ Zero-Lookahead Issue:** Cannot know session type until session ENDS
**Tradeable version:** Use prior session labels for next session (e.g., Asia labels → London decision)

