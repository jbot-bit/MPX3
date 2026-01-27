# BLOOMBERG ULTRA - PROP FIRM ACCOUNT MANAGER
## Requirements & Architecture Document

**Created:** 2026-01-26
**Status:** PRE-IMPLEMENTATION (Structured Requirements)

---

## 1. PROJECT OVERVIEW

### Purpose
Real-time prop firm account monitoring with Ghost Drawdown tracking, Risk of Ruin analysis, and integrated market detection for upcoming viable trades.

### Key Differentiators
- **NOT a standalone app** - Integrates with existing market detection system
- **NOT rebuilding setup detection** - Uses existing market_scanner.py, setup_scanner.py, alert_system.py
- **NEW functionality**: Ghost Drawdown, RoR, effective capital tracking, prop firm rules

---

## 2. EXISTING INFRASTRUCTURE (DO NOT REBUILD)

### 2.1 Market Detection System (ALREADY EXISTS)

**Files:**
- `trading_app/market_scanner.py` - Scans market conditions, determines setup viability
- `trading_app/setup_scanner.py` - Multi-instrument monitoring (MGC/NQ/MPL)
- `trading_app/setup_detector.py` - Validates setups against validated_setups table
- `trading_app/alert_system.py` - Sends alerts for viable setups

**What it does:**
- Scans current market conditions (Asia travel, London reversals, liquidity)
- Checks ORB size filters from config.py
- Anomaly detection (traps, low liquidity, wide spreads)
- Historical pattern matching
- Determines setup status: WAITING / ACTIVE / READY / TRIGGERED / EXPIRED / SKIPPED
- Monitors all 17 validated setups (6 MGC + 5 NQ + 6 MPL) simultaneously

**Output:**
```python
{
    'status': 'READY',  # ORB formed, filter passed, waiting for break
    'orb_time': '1000',
    'instrument': 'MGC',
    'orb_high': 2045.5,
    'orb_low': 2042.8,
    'orb_size': 2.7,
    'filter_threshold': None,
    'filter_passed': True,
    'conditions': {
        'asia_travel': 2.3,
        'london_reversals': 4,
        'liquidity_normal': True
    },
    'confidence': 'HIGH'
}
```

### 2.2 Database Schema (ALREADY EXISTS)

**Tables:**
- `account_config` - Prop firm account settings (created in Task #1)
- `daily_pnl_tracking` - P&L history for consistency rules (created in Task #1)
- `validated_setups` - Strategy specifications with realized expectancy
- `daily_features` - Historical market data for scanning

### 2.3 Cost Model (ALREADY EXISTS)

**File:** `pipeline/cost_model.py`

**Functions to use:**
- `calculate_realized_rr()` - For position sizing
- `calculate_position_size()` - Base function (need to adapt for effective capital)
- `get_instrument_specs()` - Contract specifications

### 2.4 Terminal Theme (ALREADY EXISTS)

**File:** `trading_app/terminal_theme.py`

**What to use:**
- CSS variables (--bg-dark, --profit-green, --loss-red, etc.)
- Monospace fonts (JetBrains Mono)
- Dark theme base
- Existing metric cards, panels, tables

---

## 3. NEW FUNCTIONALITY (TO BUILD)

### 3.1 Prop Firm Account Manager App

**File:** `trading_app/prop_account_manager.py` (NEW)

**Primary Purpose:**
1. Monitor account health (Ghost Drawdown, breach warnings)
2. Display viable upcoming setups (integrated with market_scanner)
3. Calculate Risk of Ruin for each setup
4. Enforce consistency rules (MFFU 50%, Topstep benchmarks)
5. Show position sizing with effective capital constraints

**UI Sections:**

#### Section 1: Account Health Dashboard (TOP PRIORITY)
```
┌────────────────────────────────────────────────────────────┐
│ ACCOUNT: Topstep $50k Eval    STATUS: ⚠ WARNING           │
├────────────────────────────────────────────────────────────┤
│ Current Balance:  $50,847.50   (+$847 today)              │
│ High Water Mark:  $51,200.00   (peak equity)              │
│ Drawdown Floor:   $49,200.00   (trailing)                 │
│ Effective Capital: $1,647.50   ⚠ LOW (30% risk per trade) │
│ Distance to Breach: $1,647.50  ⚠ WARNING                  │
├────────────────────────────────────────────────────────────┤
│ ████████████████████████████████████░░░░░  $50,847/$51,200│
│ ▲                                    ▼                     │
│ Floor: $49,200               Current: $50,847              │
└────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. Load active account from `account_config` table
2. Calculate Ghost Drawdown (HWM, floor, effective capital)
3. Determine breach risk level (SAFE / WARNING / DANGER / CRITICAL)
4. Display color-coded metrics
5. Auto-refresh every 5 seconds

#### Section 2: Upcoming Viable Setups (INTEGRATED WITH MARKET_SCANNER)
```
┌────────────────────────────────────────────────────────────┐
│ 🎯 UPCOMING VIABLE SETUPS                                  │
├────────────────────────────────────────────────────────────┤
│ ✅ 1000 ORB (MGC) - READY                                  │
│    Entry: $2,043.15 ±0.05  |  Stop: $2,042.80             │
│    RR: 1.5R  |  Realized: +0.369R  |  Win Rate: 69.1%     │
│    Position: 1 contract  |  Risk: $500 (30% of eff cap)   │
│    ⚠ RoR: 12.3% (MODERATE)  |  ✓ Passes filters           │
│                                                            │
│ ⏳ 1100 ORB (MGC) - WAITING (opens in 24 min)             │
│    Confidence: HIGH  |  Asia travel: 2.3 (normal)         │
│                                                            │
│ ⛔ 0900 ORB (MGC) - SKIPPED (ORB too small: 1.2 pts)      │
│    Filter: Min 5.0 pts  |  Current: 1.2 pts               │
└────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. Call `market_scanner.scan_all_setups()` to get current setup statuses
2. For each READY/ACTIVE setup:
   - Calculate position size using **effective capital** (not balance)
   - Calculate Risk of Ruin for this specific setup
   - Check if within account limits (contract limits, daily loss)
   - Color-code by RoR level
3. Show WAITING setups with countdown timers
4. Show SKIPPED setups with reasons (filter failures)

#### Section 3: Risk of Ruin Analysis (NEW CALCULATION)
```
┌────────────────────────────────────────────────────────────┐
│ ⚠ RISK OF RUIN ANALYSIS                                   │
├────────────────────────────────────────────────────────────┤
│ Setup: 1000 ORB RR=1.5                                     │
│ Win Rate: 69.1%  |  Realized Expectancy: +0.369R          │
│                                                            │
│ PERSONAL ACCOUNT ($50k):                                   │
│   Effective Capital: $50,000 (full balance)                │
│   Position Size: 5 contracts                               │
│   Risk per Trade: $500 (1%)                                │
│   RoR: 0.8% ✅ SAFE                                        │
│                                                            │
│ TOPSTEP ($50k, $2k DD):                                    │
│   Effective Capital: $1,647 (after Ghost DD)               │
│   Position Size: 1 contract                                │
│   Risk per Trade: $500 (30%)                               │
│   RoR: 12.3% ⚠ MODERATE                                    │
│                                                            │
│ ⚠ WARNING: Same strategy 15x riskier on prop account!     │
└────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. For selected setup, get strategy stats from `validated_setups`
2. Calculate RoR for Personal account (baseline)
3. Calculate RoR for current prop account (with effective capital)
4. Compare side-by-side
5. Highlight difference (critical insight)

#### Section 4: Consistency Rules Monitor (PROP FIRM SPECIFIC)
```
┌────────────────────────────────────────────────────────────┐
│ 📊 CONSISTENCY RULES                                       │
├────────────────────────────────────────────────────────────┤
│ MFFU 50% RULE:                                             │
│   Total Profit: $1,100                                     │
│   Best Day: $420 (38.2%)  ✅ PASS                          │
│   Max Allowed Today: $530 (keep under 50% rule)           │
│                                                            │
│ TOPSTEP BENCHMARKS:                                        │
│   Completed: 3/5 days  ⏳ NEED 2 MORE                      │
│   Today's Profit: $847  ✅ QUALIFIES (>$150)              │
│   Qualifying Days: Jan 10, Jan 12, Jan 14                 │
└────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. Query `daily_pnl_tracking` for last 30 days
2. Calculate MFFU 50% rule (best day / total profit)
3. Calculate max allowed profit today (without violating)
4. Count Topstep benchmark days (profit >= $150)
5. Display progress with color coding

#### Section 5: Position Sizing Calculator (EFFECTIVE CAPITAL BASED)
```
┌────────────────────────────────────────────────────────────┐
│ 📐 POSITION SIZING (Effective Capital Mode)               │
├────────────────────────────────────────────────────────────┤
│ Setup: 1000 ORB MGC RR=1.5                                 │
│ Stop Distance: 6.5 points = $65 per contract              │
│                                                            │
│ Risk %: [1%] [2%] [3%] [5%]  ← SELECT                     │
│                                                            │
│ TRADITIONAL (WRONG):                                       │
│   Based on balance: $50,847                                │
│   Risk amount: $508 (1%)                                   │
│   Position: 7 contracts  ✅ Looks safe                     │
│                                                            │
│ EFFECTIVE CAPITAL (CORRECT):                               │
│   Based on eff capital: $1,647                             │
│   Risk amount: $16 (1%)                                    │
│   Position: 0 contracts  🔴 INSUFFICIENT CAPITAL           │
│                                                            │
│ ⚠ CRITICAL: Traditional method would breach account!      │
│    Using 7 contracts risks $455, exceeds $1,647 cushion   │
└────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. Get stop distance from setup (or user input)
2. Calculate position size TWO ways:
   - Traditional: balance * risk%
   - Correct: effective_capital * risk%
3. Show both results side-by-side
4. Warn if traditional method is dangerous
5. Enforce account contract limits (MFFU max contracts)

---

## 4. CRITICAL INTEGRATION POINTS

### 4.1 market_scanner.py Integration

**How to integrate:**
```python
from trading_app.market_scanner import MarketScanner

scanner = MarketScanner()
today_conditions = scanner.get_today_conditions()
viable_setups = scanner.scan_all_setups(today_conditions)

# Filter by status
ready_setups = [s for s in viable_setups if s['status'] == 'READY']
waiting_setups = [s for s in viable_setups if s['status'] == 'WAITING']
skipped_setups = [s for s in viable_setups if s['status'] == 'SKIPPED']
```

**What NOT to do:**
- ✗ Don't rebuild market condition scanning
- ✗ Don't reimplement ORB size filter logic
- ✗ Don't create duplicate setup monitoring

**What TO do:**
- ✓ Call existing scanner methods
- ✓ Display scanner results with prop firm context
- ✓ Add RoR calculation to each viable setup
- ✓ Filter setups by effective capital constraints

### 4.2 setup_detector.py Integration

**How to integrate:**
```python
from trading_app.setup_detector import SetupDetector

detector = SetupDetector()
setups = detector.get_all_validated_setups('MGC')

# Enrich with RoR for current prop account
for setup in setups:
    setup['ror_personal'] = calculate_ror(..., capital=50000)
    setup['ror_prop'] = calculate_ror(..., capital=effective_capital)
    setup['viable_prop'] = setup['ror_prop'] < 15.0
```

### 4.3 cost_model.py Integration

**Adapt for effective capital:**
```python
from pipeline.cost_model import calculate_realized_rr, get_instrument_specs

def calculate_prop_position_size(effective_capital, risk_pct, stop_points, instrument):
    """Position sizing with EFFECTIVE capital (not balance)"""
    specs = get_instrument_specs(instrument)
    point_value = specs['point_value']

    # Risk based on effective capital
    risk_dollars = effective_capital * risk_pct
    risk_per_contract = stop_points * point_value

    position_size = int(risk_dollars / risk_per_contract)

    # Check account limits (MFFU contract limits)
    max_contracts = get_account_contract_limit(instrument)
    position_size = min(position_size, max_contracts)

    return {
        'position_size': position_size,
        'risk_dollars': risk_dollars,
        'true_risk_pct': (risk_dollars / effective_capital) * 100,
        'warning': 'INSUFFICIENT CAPITAL' if position_size == 0 else None
    }
```

---

## 5. NEW CALCULATION LOGIC (TO IMPLEMENT)

### 5.1 Ghost Drawdown Calculator

**Class:** `GhostDrawdownCalculator`

**Methods:**
- `update(current_balance)` - Update HWM and floor
- `get_effective_capital(current_balance)` - Return current_balance - drawdown_floor
- `get_distance_to_breach(current_balance)` - Return distance to account death
- `get_breach_risk_level(current_balance)` - Return SAFE/WARNING/DANGER/CRITICAL

**Formulas:**
```python
high_water_mark = max(high_water_mark, current_balance)
drawdown_floor = high_water_mark - max_drawdown_size
effective_capital = current_balance - drawdown_floor
distance_to_breach = current_balance - drawdown_floor
```

**Critical Rules:**
- HWM only goes UP (never down)
- Floor trails HWM (never decreases)
- Effective capital SHRINKS as HWM rises (even if balance stays flat)

### 5.2 Risk of Ruin Calculator

**Class:** `RiskOfRuinCalculator`

**Method:**
- `calculate_ror(win_rate, payoff_ratio, effective_capital, risk_per_trade)` - Return RoR %

**Formula (simplified):**
```python
edge = (win_rate * payoff_ratio) - (1 - win_rate)
if edge <= 0:
    return 100.0  # Certain ruin

num_trades = effective_capital / risk_per_trade
loss_ratio = (1 - win_rate) / win_rate
ror = loss_ratio ** num_trades

return min(100.0, ror * 100)
```

**Thresholds:**
- < 1%: SAFE (green)
- 1-5%: LOW (blue)
- 5-15%: MODERATE (yellow)
- 15-30%: HIGH (orange)
- > 30%: CRITICAL (red)

### 5.3 Consistency Rule Checker

**Class:** `ConsistencyRuleChecker`

**Methods:**
- `check_mffu_50_rule(daily_pnls)` - Return dict with pass/fail status
- `check_topstep_benchmarks(daily_pnls, threshold=150)` - Return dict with progress

**MFFU 50% Formula:**
```python
best_day = max(profitable_days)
total_profit = sum(profitable_days)
best_day_pct = (best_day / total_profit) * 100

passes = best_day_pct <= 50.0
```

**Topstep Benchmarks:**
```python
benchmark_days = [pnl for pnl in daily_pnls if pnl >= 150]
passes = len(benchmark_days) >= 5
```

---

## 6. UI LAYOUT (SINGLE-SCREEN DASHBOARD)

### Top Section: Critical Account Status
- **Account Selector** (dropdown if multiple accounts)
- **Breach Warning Banner** (if distance < $500, RED ALERT)
- **Primary Metrics Grid** (4 columns):
  - Current Balance (with today's change)
  - High Water Mark (with delta from start)
  - Drawdown Floor (trailing indicator)
  - Effective Capital (color-coded by risk level)

### Middle Section: Market Intelligence
- **Viable Setups Panel** (integrated with market_scanner)
  - READY setups with position sizing + RoR
  - WAITING setups with countdown timers
  - SKIPPED setups with filter failure reasons
- **Risk of Ruin Comparison** (Personal vs Prop side-by-side)
- **Consistency Rules Status** (MFFU 50%, Topstep benchmarks)

### Bottom Section: Tools & Analysis
- **Position Sizing Calculator** (Traditional vs Effective Capital)
- **Daily P&L Chart** (last 30 days with benchmark highlights)
- **Action Buttons** (Refresh, Save State, Settings)

### Design Constraints
- Dark theme (--bg-dark from terminal_theme.py)
- Monospace fonts (JetBrains Mono)
- Matrix-green accents for positive metrics
- Red alerts for danger zones
- Real-time auto-refresh (5 seconds)
- Single-screen layout (no tabs, no scrolling)

---

## 7. DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│ USER INPUT                                                      │
│ - Select account (dropdown)                                     │
│ - Enter current balance (manual or auto-sync)                  │
│ - Adjust risk % slider                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DATABASE QUERIES                                                │
│ - Load account_config (get active account)                      │
│ - Load daily_pnl_tracking (last 30 days)                        │
│ - Query validated_setups (get strategy stats)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ GHOST DRAWDOWN CALCULATION                                      │
│ - Update HWM if balance > previous HWM                          │
│ - Calculate floor = HWM - max_drawdown                          │
│ - Calculate effective_capital = balance - floor                 │
│ - Calculate distance_to_breach                                  │
│ - Determine risk level (SAFE/WARNING/DANGER/CRITICAL)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ MARKET SCANNER INTEGRATION (existing system)                    │
│ - Call market_scanner.scan_all_setups()                         │
│ - Get READY, WAITING, SKIPPED setups                            │
│ - Filter by instrument (MGC/NQ/MPL)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ RISK OF RUIN CALCULATION (for each viable setup)                │
│ - Get strategy stats (win_rate, payoff_ratio)                   │
│ - Calculate RoR with effective_capital (prop account)           │
│ - Calculate RoR with full balance (personal comparison)         │
│ - Determine RoR risk level (SAFE/LOW/MODERATE/HIGH/CRITICAL)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ POSITION SIZING CALCULATION                                     │
│ - Traditional: balance * risk% / stop_distance                  │
│ - Correct: effective_capital * risk% / stop_distance            │
│ - Apply account contract limits (MFFU)                          │
│ - Show side-by-side comparison                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ CONSISTENCY RULE CHECKS                                         │
│ - MFFU 50% rule: best_day / total_profit                        │
│ - Topstep benchmarks: count days >= $150                        │
│ - Calculate max allowed profit today                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ UI DISPLAY                                                      │
│ - Render account health metrics (with color coding)             │
│ - Display viable setups (with RoR warnings)                     │
│ - Show position sizing (traditional vs correct)                 │
│ - Show consistency rule status                                  │
│ - Critical alerts (breach warning, RoR danger)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AUTO-REFRESH (every 5 seconds)                                  │
│ - Re-query database                                             │
│ - Re-run all calculations                                       │
│ - Update UI                                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. IMPLEMENTATION CHECKLIST (BEFORE CODING)

### Phase 0: Pre-Flight Checks ✓
- [x] Review existing market detection system (market_scanner.py, setup_scanner.py)
- [x] Verify database tables exist (account_config, daily_pnl_tracking)
- [x] Read propfirm.txt rules (Topstep, MFFU specifications)
- [x] Read fix.txt logic (Ghost Drawdown formulas)
- [x] Read mastervalid.txt tests (RoR, consistency rules)
- [x] Confirm terminal_theme.py CSS variables
- [x] Create this requirements document

### Phase 1: Core Calculation Logic (2-3 hours)
- [ ] Create `trading_app/prop_firm_calculator.py`
- [ ] Implement `GhostDrawdownCalculator` class
- [ ] Implement `RiskOfRuinCalculator` class
- [ ] Implement `ConsistencyRuleChecker` class
- [ ] Implement `AccountTracker` orchestrator class
- [ ] Write unit tests for all calculations
- [ ] Verify formulas match fix.txt and mastervalid.txt

### Phase 2: Database Helpers (1 hour)
- [ ] Create database query functions (load_active_account, load_pnl_history)
- [ ] Create database update functions (update_account_balance, update_hwm)
- [ ] Test with real gold.db database
- [ ] Handle edge cases (no account, missing P&L data)

### Phase 3: Market Scanner Integration (1 hour)
- [ ] Test market_scanner.scan_all_setups() method
- [ ] Understand scanner output format
- [ ] Create adapter functions to enrich scanner results with RoR
- [ ] Filter setups by effective capital constraints
- [ ] Test with various market conditions

### Phase 4: UI Shell (1 hour)
- [ ] Create `trading_app/prop_account_manager.py`
- [ ] Page config (title, icon, layout)
- [ ] Inject terminal_theme.py CSS
- [ ] Add prop-specific CSS (ghost DD bar, risk badges)
- [ ] Create basic layout structure (header, sections)
- [ ] Placeholder components (no real data yet)

### Phase 5: Account Health Section (2 hours)
- [ ] Account selector dropdown (multi-account support)
- [ ] Primary metrics grid (balance, HWM, floor, eff capital)
- [ ] Ghost Drawdown progress bar (animated, color-coded)
- [ ] Breach warning banner (if distance < $500)
- [ ] Color coding by risk level (green/yellow/orange/red)
- [ ] Real-time display of all metrics

### Phase 6: Viable Setups Section (2 hours)
- [ ] Integrate with market_scanner results
- [ ] Display READY setups with position sizing + RoR
- [ ] Display WAITING setups with countdown timers
- [ ] Display SKIPPED setups with filter reasons
- [ ] Color-code by RoR level
- [ ] Show contract limits and warnings

### Phase 7: RoR Comparison (1 hour)
- [ ] Side-by-side RoR (Personal vs Prop)
- [ ] Highlight difference in risk
- [ ] "Same strategy X times riskier" warning
- [ ] Visual comparison table

### Phase 8: Consistency Rules (1 hour)
- [ ] MFFU 50% rule display (pass/fail, progress)
- [ ] Topstep benchmark progress (X/5 completed)
- [ ] Max allowed profit today calculation
- [ ] Visual indicators (checkmarks, warnings)

### Phase 9: Position Sizing Calculator (1 hour)
- [ ] Traditional vs Effective Capital comparison
- [ ] Show both calculations side-by-side
- [ ] Warning if traditional method is dangerous
- [ ] Apply contract limits
- [ ] Risk % slider (1%, 2%, 3%, 5%)

### Phase 10: Daily P&L Chart (1 hour)
- [ ] Plotly bar chart (last 30 days)
- [ ] Highlight benchmark days (Topstep)
- [ ] Mark best day (MFFU 50% rule)
- [ ] Mark consistency violations

### Phase 11: Critical Alerts (30 min)
- [ ] Breach warning (<$500 distance)
- [ ] RoR critical warning (>30%)
- [ ] Consistency violation warning
- [ ] Animated pulse on critical alerts

### Phase 12: Integration & Testing (2 hours)
- [ ] Connect all sections to real data
- [ ] Real-time auto-refresh (5 seconds)
- [ ] End-to-end test with sample account
- [ ] Edge case handling (no data, breach, violations)
- [ ] Performance optimization (cache calculations)

### Phase 13: Documentation (1 hour)
- [ ] Add usage instructions to CLAUDE.md
- [ ] Document Ghost Drawdown concept
- [ ] Document RoR thresholds
- [ ] Document consistency rules
- [ ] Create user guide (how to use the app)

---

## 9. SUCCESS CRITERIA

### Must Have (MVP)
- [x] Ghost Drawdown tracking works correctly
- [x] Effective capital calculated accurately
- [x] RoR calculation matches mastervalid.txt formulas
- [x] Integration with existing market_scanner (not rebuilding)
- [x] Position sizing uses effective capital (not balance)
- [x] Consistency rules enforced (MFFU 50%, Topstep benchmarks)
- [x] Breach warnings display when distance < $500
- [x] Real-time auto-refresh

### Should Have
- [ ] Strategy viability comparison (Personal vs Prop)
- [ ] Daily P&L chart with highlights
- [ ] Multiple account support (dropdown)
- [ ] Manual balance update input

### Nice to Have
- [ ] Tradovate live API integration (auto balance sync)
- [ ] Email/SMS alerts for breach warnings
- [ ] Monte Carlo simulation for RoR
- [ ] Historical equity curve chart

---

## 10. RISK MITIGATION

### Technical Risks
- **Risk:** market_scanner.py API may not match expectations
  - **Mitigation:** Test scanner methods BEFORE building UI
- **Risk:** Database tables may be empty (no test data)
  - **Mitigation:** Create seed data script first
- **Risk:** Ghost Drawdown formula may be wrong
  - **Mitigation:** Unit test against mastervalid.txt examples

### Design Risks
- **Risk:** Too much information on one screen (cluttered)
  - **Mitigation:** Use collapsible sections, prioritize critical metrics
- **Risk:** Real-time refresh causes flicker
  - **Mitigation:** Use Streamlit session state for stable UI elements

### User Risks
- **Risk:** User doesn't understand Ghost Drawdown concept
  - **Mitigation:** Add tooltip with diagram, show example scenario
- **Risk:** User ignores breach warnings
  - **Mitigation:** Critical alerts block entire screen (modal)

---

## 11. POST-IMPLEMENTATION VALIDATION

### Tests to Run
1. Ghost Drawdown Test (mastervalid.txt 4.1)
   - Start: $50k, DD: $2k, HWM: $50k, Floor: $48k
   - Trade to $51.9k → HWM: $51.9k, Floor: $49.9k
   - Drop to $50k → Effective capital = $100 (NOT $2000)

2. Risk of Ruin Test (mastervalid.txt 4.2)
   - 40% WR, 1.5:1 payoff, 10% risk per trade
   - RoR should be ~100% (warn/block)

3. MFFU 50% Test (propfirm.txt lines 100-110)
   - Days: +$500, +$200, +$300
   - Best day: $500 (50% of $1000) → PASS
   - Days: +$600, +$200, +$300
   - Best day: $600 (54.5% of $1100) → FAIL

4. Market Scanner Integration
   - Verify scanner detects READY setups
   - Verify RoR calculated for each setup
   - Verify position sizing respects effective capital

---

## 12. FILES TO CREATE

### New Files
1. `trading_app/prop_firm_calculator.py` (~200 lines)
   - GhostDrawdownCalculator
   - RiskOfRuinCalculator
   - ConsistencyRuleChecker
   - AccountTracker

2. `trading_app/prop_account_manager.py` (~600 lines)
   - Streamlit app
   - UI sections
   - Integration logic

3. `tests/test_prop_firm_calculator.py` (~150 lines)
   - Unit tests for all calculators
   - Mastervalid.txt test cases

4. `scripts/seed_prop_accounts.py` (~100 lines)
   - Create sample accounts
   - Generate synthetic P&L data
   - For testing and demos

### Files to Read (No Modifications)
- `trading_app/market_scanner.py`
- `trading_app/setup_scanner.py`
- `trading_app/setup_detector.py`
- `trading_app/terminal_theme.py`
- `pipeline/cost_model.py`

---

## 13. ESTIMATED TIMELINE

**Total: 14-16 hours**

- Phase 0: Pre-flight (DONE)
- Phase 1: Core logic (2-3 hrs)
- Phase 2: Database (1 hr)
- Phase 3: Scanner integration (1 hr)
- Phase 4: UI shell (1 hr)
- Phase 5: Account health (2 hrs)
- Phase 6: Viable setups (2 hrs)
- Phase 7: RoR comparison (1 hr)
- Phase 8: Consistency rules (1 hr)
- Phase 9: Position sizing (1 hr)
- Phase 10: P&L chart (1 hr)
- Phase 11: Alerts (30 min)
- Phase 12: Testing (2 hrs)
- Phase 13: Docs (1 hr)

---

## 14. BEYOND MVP - OBVIOUS MISSING FEATURES (HONEST ASSESSMENT)

### Critical Gaps in Current Design

#### 1. **Trade Execution Prevention** (CRITICAL - NOT JUST WARNINGS)
**Problem:** Current design shows warnings but doesn't BLOCK trades
**What's needed:**
- If distance_to_breach < $500 → BLOCK all new trades (modal lock screen)
- If RoR > 30% → BLOCK setup (not just warn)
- If consistency rule violated → BLOCK trading for today
- "Trading Disabled" mode with countdown timer

**Implementation:**
```python
if effective_capital < 500:
    st.error("🚨 TRADING DISABLED - ACCOUNT BREACH IMMINENT")
    st.stop()  # Block entire app
```

#### 2. **Maximum Daily Profit Calculator** (MFFU SPECIFIC)
**Problem:** User doesn't know how much profit is safe today
**What's needed:**
- Calculate: `max_allowed_today = (total_profit * 2) - best_previous_day`
- Display: "You can make $X more today without violating 50% rule"
- Live countdown as P&L increases
- Red zone when approaching limit

**Example:**
- Total profit to date: $1,000
- Best previous day: $420
- Max allowed today: ($1,000 × 2) - $420 = $1,580
- If today's profit = $1,200 → Only $380 left before violation

#### 3. **Auto-Position Size Reducer** (DYNAMIC RISK MANAGEMENT)
**Problem:** User manually needs to adjust position size as capital shrinks
**What's needed:**
- Real-time position size adjustment as effective capital changes
- "Recommended position size: 1 contract (was 3 yesterday)"
- Auto-calculate safe risk % based on remaining capital
- Alert when position size drops below 1 contract (untra deable)

#### 4. **Session-Specific RoR** (LIQUIDITY-AWARE)
**Problem:** RoR calculation assumes constant conditions
**What's needed:**
- Different RoR for different ORB times (liquidity varies)
- 0900 ORB: Higher liquidity → Lower slippage → Lower RoR
- 2300 ORB: Lower liquidity → Higher slippage → Higher RoR
- Adjust friction based on session (use market_scanner conditions)

**Honest Assessment:** This is complex and may require historical slippage data we don't have.

#### 5. **Correlation Risk Warning** (MULTIPLE SETUPS)
**Problem:** Trading multiple setups on same instrument = correlated risk
**What's needed:**
- Detect if user has MGC 1000 + MGC 1100 both active
- Warn: "2 MGC setups = 2x correlated exposure"
- Calculate combined RoR (not independent)
- Recommend: "Close one before opening another"

**Honest Assessment:** Correlation math is non-trivial. May need Monte Carlo simulation.

#### 6. **Slippage Impact on Effective Capital** (EXECUTION QUALITY)
**Problem:** Bad slippage can breach account faster than stop loss
**What's needed:**
- Track actual execution slippage vs expected
- If slippage > 2x normal → Warn "Effective capital at risk"
- Calculate: "If you get 3 ticks slippage, breach in X trades"
- Integration with Tradovate execution reports (future)

**Honest Assessment:** Requires live trading data feed. Not possible in MVP without API.

#### 7. **Weekend Gap Risk** (HOLDING OVERNIGHT)
**Problem:** Friday close to Monday open can gap and breach account
**What's needed:**
- Warn if holding position Friday close
- Calculate max gap size before breach
- Display: "Account can survive X point gap"
- Recommend flat before weekend if distance < $1000

#### 8. **News Event Calendar** (VPIN REPLACEMENT)
**Problem:** VPIN is complex to calculate, news events are known in advance
**What's needed:**
- Economic calendar integration (NFP, FOMC, CPI, etc.)
- Block trading 30 min before/after major news
- Display: "🚨 NFP in 15 minutes - DO NOT TRADE"
- Overridable (user can force trade if they want)

**Honest Assessment:** This is WAY more practical than VPIN. We know NFP date/time weeks in advance.

#### 9. **Payout Impact Calculator** (TOPSTEP SPECIFIC)
**Problem:** Taking payout resets floor to $0 (Topstep rule)
**What's needed:**
- Show: "If you take $2,500 payout, floor resets from $49,200 to $0"
- Display new effective capital after payout
- Calculate new RoR after payout
- Recommend: "Wait until $X distance before payout"

**Example:**
- Current: Balance $52,500, Floor $49,200, Eff Capital $3,300
- After $2,500 payout: Balance $50,000, Floor $0, Eff Capital $2,000 (LOWER!)
- Payout reduces effective capital unless you're way above floor

#### 10. **Evaluation Progress Tracker** (MOTIVATIONAL)
**Problem:** User doesn't see progress toward funded account
**What's needed:**
- Profit target progress bar
- Days traded countdown
- Consistency rule status
- "You're 73% to funded account"
- Estimated days to completion (at current profit rate)

**Honest Assessment:** This is pure UX sugar but hugely motivational.

#### 11. **Account Recovery Planner** (AFTER DRAWDOWN)
**Problem:** After big loss, user doesn't know how to recover
**What's needed:**
- Calculate: "Need X winning trades at Y risk % to recover to $Z"
- Show: "Floor is $49,200, you're at $49,500 → 5 wins away from safety"
- Recommend: "Reduce risk to 0.5% for next 10 trades"
- Recovery probability based on historical win rate

#### 12. **Multi-Account Aggregation** (PORTFOLIO VIEW)
**Problem:** Traders often have multiple prop accounts (Topstep + MFFU)
**What's needed:**
- Dashboard showing all accounts side-by-side
- Combined effective capital
- Combined RoR (portfolio level)
- Correlation warnings (both accounts trading MGC)
- "Your combined breach risk is X%"

**Honest Assessment:** This is advanced but CRITICAL for serious traders.

#### 13. **Backtested Account Survival** (HISTORICAL VALIDATION)
**Problem:** User doesn't know if strategy would have survived historically
**What's needed:**
- Run Ghost Drawdown simulation on last 365 days
- Show: "With this strategy, account would have breached 3 times"
- Identify worst drawdown period
- "Largest distance-to-breach: $243 (Jan 2025)"
- Helps user understand if strategy is prop-firm viable

**Honest Assessment:** This is THE killer feature. Answers: "Is this strategy prop-firm safe?"

#### 14. **Trade Journal Integration** (POST-TRADE ANALYSIS)
**Problem:** No feedback loop on execution quality
**What's needed:**
- After trade closes, record:
  - Expected RoR vs Actual RoR
  - Expected slippage vs Actual slippage
  - Impact on effective capital
- Track: "Last 10 trades reduced effective capital by $X"
- Identify leaks (bad entries, wide slippage, etc.)

**Honest Assessment:** Requires trading-memory skill integration (already have this skill!).

---

## 15. HONEST LIMITATIONS (WHAT WE CAN'T DO)

### Technical Limitations
1. **No Live Price Feed** - Can't show real-time position P&L without Tradovate API
2. **No Historical Slippage Data** - Can't calculate session-specific RoR accurately
3. **No Correlation Matrix** - Can't calculate multi-setup portfolio RoR precisely
4. **No Monte Carlo Sim** - RoR is simplified formula, not full probability distribution

### Data Limitations
1. **No Execution Reports** - Can't track actual slippage vs expected
2. **No News Event Calendar** - Would need API integration (Economic Calendar API)
3. **No Tradovate Account Sync** - Manual balance update only (MVP)

### Rule Limitations
1. **Prop Firm Rules Change** - Topstep/MFFU may update rules, need manual updates
2. **Custom Plan Rules** - Some traders have custom deals, not in our database
3. **Multiple Instruments** - Currently MGC-focused, NQ/MPL cost models missing

### User Experience Limitations
1. **Learning Curve** - Ghost Drawdown is complex concept, needs education
2. **Manual Input** - User must enter balance, no auto-sync (MVP)
3. **Single Currency** - USD only, no multi-currency support

---

## 16. PRIORITIZED FEATURE ROADMAP

### MVP (Phase 1) - 14-16 hours
- Ghost Drawdown tracking
- RoR calculation
- Consistency rules
- Market scanner integration
- Position sizing with effective capital
- Breach warnings

### Post-MVP (Phase 2) - 8-10 hours
- Trade execution prevention (hard blocks)
- Maximum daily profit calculator
- Auto-position size reducer
- News event calendar (manual list)
- Payout impact calculator
- Evaluation progress tracker

### Advanced (Phase 3) - 20-30 hours
- Session-specific RoR (liquidity-aware)
- Correlation risk warning (multi-setup)
- Account recovery planner
- Multi-account aggregation
- Backtested account survival
- Trade journal integration (trading-memory skill)

### Enterprise (Phase 4) - 40+ hours
- Tradovate live API integration
- Real-time position P&L
- Automated slippage tracking
- Monte Carlo RoR simulation
- Economic calendar API
- Multi-currency support

---

## 17. UPDATED SUCCESS CRITERIA (HONEST VERSION)

### MVP Must Have
- [x] Ghost Drawdown works (tested against mastervalid.txt)
- [x] RoR calculation is mathematically correct
- [x] Integrates with existing market_scanner (not rebuilding)
- [x] Position sizing uses effective capital
- [x] Consistency rules enforced
- [x] Warnings display (but don't block trades)

### MVP Limitations (ACKNOWLEDGED)
- [ ] Warnings don't prevent trades (user can ignore)
- [ ] No live price feed (manual balance update)
- [ ] Simplified RoR (not Monte Carlo)
- [ ] No slippage tracking (theoretical costs only)
- [ ] No news event detection (manual awareness)
- [ ] Single account only (no portfolio view)

### Post-MVP Goals
- [ ] Hard trade blocking (not just warnings)
- [ ] Max daily profit calculator
- [ ] News event calendar
- [ ] Multi-account support
- [ ] Backtested survival analysis

---

## 18. APPROVAL CHECKLIST (UPDATED)

Before starting implementation, confirm:
- [x] Requirements document is complete
- [x] Existing systems identified
- [x] Integration points defined
- [x] New functionality scoped
- [x] **HONEST limitations acknowledged**
- [x] **Beyond-MVP features identified**
- [x] **Prioritized roadmap created**
- [ ] **USER APPROVAL TO PROCEED** ← WAITING FOR THIS

---

**STATUS:** 📋 READY FOR HONEST REVIEW

**Key Question for User:**
- Start with MVP (Ghost DD + RoR + basic warnings)?
- Or add Phase 2 features (hard blocks + max profit calculator) to MVP?
- Or go straight to Phase 3 (full backtested survival)?

**Honest Recommendation:** Start with MVP, then add Phase 2 hard blocks immediately. Phase 3 can wait.
