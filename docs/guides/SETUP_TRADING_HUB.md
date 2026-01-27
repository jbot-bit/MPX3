# Trading Hub Setup Guide

**Enhanced dashboard with AI chat, comprehensive parameter controls, and edge discovery**

---

## Prerequisites

### 1. Install Required Packages

```bash
pip install streamlit anthropic matplotlib pandas numpy duckdb
```

### 2. Get Claude API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)

### 3. Set Environment Variable

**Option A: Add to .env file (Recommended)**

```bash
# Add this line to your .env file
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

**Option B: Set in terminal session**

Windows (CMD):
```cmd
set ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

Windows (PowerShell):
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

Linux/Mac:
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

**Option C: Set system environment variable (Permanent)**

Windows:
1. Search for "Environment Variables" in Start Menu
2. Click "Edit the system environment variables"
3. Click "Environment Variables" button
4. Under "User variables", click "New"
5. Variable name: `ANTHROPIC_API_KEY`
6. Variable value: `sk-ant-api03-your-key-here`
7. Click OK

---

## Launch Dashboard

### Basic Launch

```bash
streamlit run app_trading_hub.py
```

**Default URL:** http://localhost:8501

### Custom Port

```bash
streamlit run app_trading_hub.py --server.port 8502
```

### Auto-Open Browser

```bash
streamlit run app_trading_hub.py --server.headless false
```

---

## Features Overview

### 1. 🤖 AI Trading Assistant (Sidebar)

**What it does:**
- Answers questions about your trading data
- Helps interpret edge discovery results
- Validates zero-lookahead compliance
- Suggests strategy optimizations
- Explains statistics and metrics

**How to use:**
1. Type your question in the text area
2. Click "Send" button
3. AI responds with context-aware insights
4. Click "Clear" to start new conversation

**Example questions:**
- "What's the best setup for morning trades?"
- "Why is 10:00 UP the primary edge?"
- "How do I validate zero-lookahead compliance?"
- "What's the difference between PRE blocks and SESSION blocks?"
- "Should I use RR=1.5 or RR=3.0 for 10:00 UP trades?"

### 2. 🔍 Edge Discovery Tab

**What it does:**
- Analyzes 40+ edge configurations
- Tests baseline, PRE block, and correlation edges
- Ranks by quality score (Win Rate × Avg R)
- Allows filtering by criteria
- Exports results to CSV

**How to use:**
1. Click "Run Analysis" button
2. Wait for analysis to complete (~30 seconds)
3. Use sliders to filter results:
   - **Min Win Rate**: Filter edges below threshold
   - **Min Avg R**: Filter negative expectancy edges
   - **Min Trades**: Filter small sample sizes
   - **Edge Type**: Select baseline/pre_block/correlation
4. Review top 10 edges
5. Click "Export All Results" for full CSV

**Edge types explained:**
- **baseline**: No filters (e.g., "1000 UP")
- **pre_block**: PRE_ASIA/LONDON/NY filters (e.g., "1100 UP PRE_ASIA > 50t")
- **correlation**: ORB-to-ORB dependencies (e.g., "1000 UP after 0900 WIN")

### 3. ⚙️ Strategy Builder Tab

**What it does:**
- Build custom ORB strategies
- Configure entry models, confirmations, stops
- Run instant backtests
- View equity curves and entry funnels

**How to use:**
1. **Configure Entry Setup:**
   - Entry Model: 1m_close_break, 5m_close_break, etc.
   - Confirmation Closes: 1, 2, or 3

2. **Set Risk Management:**
   - Max Stop: 0-200 ticks (0 = no limit)
   - RR Target: 1.0-5.0 (recommended 2.0-3.0)

3. **Apply Filters:**
   - ORB Times: Select which ORBs to trade
   - Direction: ANY, UP, or DOWN

4. **Run Backtest:**
   - Click "Run Backtest" button
   - View results: Trades, Win Rate, Avg R, Total R
   - Review equity curve
   - Check entry funnel

### 4. 📊 Backtest Results Tab

**What it does:**
- Shows 1-minute precision backtest results
- Compares RR targets (1.5, 2.0, 2.5, 3.0)
- Charts win rate and avg R by RR

**Prerequisites:**
Must have run RR grid search first:
```bash
python backtest_orb_exec_1m.py --rr-grid "1.5,2.0,2.5,3.0" --confirm 1
```

### 5. 📚 Documentation Tab

**What it does:**
- Quick start guide
- Zero-lookahead principles
- Known edges summary
- Resource links
- Environment setup instructions

---

## Common Use Cases

### Use Case 1: Find Best Morning Setup

**Goal:** Discover the optimal setup for 09:00-11:00 Asia ORBs

**Steps:**
1. Go to **Edge Discovery** tab
2. Click "Run Analysis"
3. Set filters:
   - Min Win Rate: 0.54
   - Min Avg R: 0.10
   - Min Trades: 50
   - Edge Type: All
4. Review results - look for 0900, 1000, 1100 setups
5. Ask AI: "Which morning setup has the best risk-adjusted returns?"

**Expected findings:**
- 10:00 UP (primary edge)
- 10:00 UP after 09:00 WIN (best correlation)
- 11:00 UP PRE_ASIA > 50t (filtered edge)

### Use Case 2: Optimize RR Target

**Goal:** Find the best RR target for your strategy

**Steps:**
1. Go to **Backtest Results** tab
2. Review RR comparison table
3. Look at trade-offs:
   - RR=1.5: Higher win rate (37.7%), lower reward
   - RR=3.0: Lower win rate (19.4%), higher reward
4. Consider your risk tolerance and sample size
5. Ask AI: "Should I use RR=1.5 or RR=3.0 for 10:00 UP trades?"

**Decision factors:**
- Lower RR = more wins, easier psychologically
- Higher RR = fewer wins, bigger payoffs
- All RR targets are net negative WITHOUT filters
- Use edge-based filtering (10:00 UP, correlations) for profitability

### Use Case 3: Validate New Strategy Idea

**Goal:** Test if a new strategy idea has edge

**Steps:**
1. Go to **Strategy Builder** tab
2. Configure your strategy:
   - Entry Model: Select your preferred entry
   - Confirmations: 1, 2, or 3 closes
   - Max Stop: Set limit
   - ORB Times: Select specific ORBs
   - Direction: UP/DOWN/ANY
3. Click "Run Backtest"
4. Check results:
   - **Min threshold:** 52% WR or +0.05 Avg R
   - **Good edge:** 54%+ WR and +0.10+ Avg R
   - **Sample size:** 50+ trades for statistical significance
5. Ask AI: "Is this strategy compliant with zero-lookahead rules?"

### Use Case 4: Get Trading Advice

**Goal:** Ask specific questions about your data

**Example conversations:**

**User:** "What's the best setup for morning trades?"

**AI:** "Based on the data, the primary morning edge is 10:00 UP with a 55.5% win rate and +0.11 avg R across 247 trades. If the 09:00 ORB wins, the 10:00 UP setup improves to 57.9% WR and +0.16 avg R (114 trades). This is the strongest correlation edge in the dataset."

**User:** "Why shouldn't I use session type filters?"

**AI:** "Session type codes (EXPANDED, CONSOLIDATION, etc.) are lookahead bias because they aren't known until AFTER the session closes. For example, at 11:00 you can't know if Asia will be EXPANDED - that's only known at 17:00 (6 hours later). Use PRE blocks instead (PRE_ASIA range is known at 09:00)."

**User:** "Should I trade 09:00 ORBs?"

**AI:** "Overall, 09:00 ORBs have a 48.9% win rate and -0.02 avg R (slight negative expectancy). However, if you filter for PRE_ASIA > 50 ticks, the edge improves to 52.7% WR and +0.05 avg R. Avoid trading 09:00 without filters."

---

## Tips & Best Practices

### Edge Discovery
- Always filter for min 20+ trades (statistical significance)
- Quality score (WR × Avg R) is better than WR alone
- Correlation edges are strongest but have smaller sample sizes
- Re-run analysis after adding new data

### Strategy Building
- Start with simple setups (1 close, no retest)
- Add complexity only if it improves results
- Check entry funnel - how many opportunities lost?
- Lower max stop = fewer trades but better quality

### AI Assistant
- Be specific in your questions
- Reference specific ORB times, directions, or metrics
- Ask for validation of zero-lookahead compliance
- Request comparisons (e.g., "10:00 vs 11:00")
- Follow up for deeper explanations

### Performance
- First analysis run may be slow (~30 sec)
- Subsequent runs use Streamlit cache
- Press 'C' in browser to clear cache if needed
- Press 'R' to rerun app

---

## Troubleshooting

### Issue 1: AI Chat Not Working

**Symptoms:** "AI assistant unavailable" in sidebar

**Fixes:**
1. Check if ANTHROPIC_API_KEY is set:
   ```bash
   # Windows CMD
   echo %ANTHROPIC_API_KEY%

   # Windows PowerShell
   echo $env:ANTHROPIC_API_KEY

   # Linux/Mac
   echo $ANTHROPIC_API_KEY
   ```

2. Verify API key is valid at https://console.anthropic.com/

3. Restart Streamlit after setting environment variable

4. Check .env file syntax (no spaces around =)

### Issue 2: Edge Discovery Takes Too Long

**Symptoms:** Analysis runs for >60 seconds

**Fixes:**
1. Check database size: `python check_db.py`
2. Ensure daily_features_v2 has data
3. Close other database connections
4. Restart Streamlit

### Issue 3: Backtest Results Tab Empty

**Symptoms:** "Could not load backtest results"

**Fix:** Run RR grid search:
```bash
python backtest_orb_exec_1m.py --rr-grid "1.5,2.0,2.5,3.0" --confirm 1
```

### Issue 4: Charts Not Displaying

**Symptoms:** Blank chart areas

**Fixes:**
1. Install matplotlib: `pip install matplotlib`
2. Clear cache (press 'C' in browser)
3. Check console for errors
4. Restart Streamlit

### Issue 5: Slow Performance

**Symptoms:** Dashboard is laggy

**Fixes:**
1. Close unused tabs
2. Clear browser cache
3. Reduce data range filters
4. Restart Streamlit
5. Use `--server.maxUploadSize 200` flag

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **R** | Rerun app (refresh) |
| **C** | Clear cache |
| **Ctrl+R** | Hard reload (browser) |
| **F11** | Fullscreen |

---

## Advanced Configuration

### Customize AI System Prompt

Edit `app_trading_hub.py`, function `get_system_context()`:

```python
def get_system_context(self, data_summary: Dict[str, Any]) -> str:
    return f"""You are a trading research assistant...

    [Add your custom instructions here]
    """
```

### Add Custom Presets

Edit `query_engine.py`, add to `PRESETS` dict:

```python
PRESETS = {
    "My Custom Strategy": StrategyConfig(
        level_basis="orb_boundary",
        entry_model="1m_close_break",
        confirm_closes=2,
        # ... other parameters
    ),
}
```

### Change Port Permanently

Create `.streamlit/config.toml`:

```toml
[server]
port = 8502
headless = false

[theme]
primaryColor = "#007bff"
backgroundColor = "#ffffff"
```

---

## Security Notes

### API Key Safety
- **Never** commit API keys to git
- Add `.env` to `.gitignore`
- Use environment variables, not hardcoded keys
- Rotate keys periodically

### Data Privacy
- Dashboard runs locally (no data sent to cloud)
- AI chat sends only your questions + data summary
- No trading data stored by Anthropic
- Conversation history in session state only

---

## Next Steps

1. **Launch the dashboard**
   ```bash
   streamlit run app_trading_hub.py
   ```

2. **Run edge discovery** to see all 40 edges

3. **Ask AI for insights** on your best setups

4. **Build custom strategies** and backtest

5. **Export results** for further analysis

6. **Read documentation** tab for deeper understanding

---

## Resources

- **Claude API Docs:** https://docs.anthropic.com/
- **Streamlit Docs:** https://docs.streamlit.io/
- **Project Documentation:**
  - WORKFLOW_GUIDE.md - Complete workflow
  - TRADING_PLAYBOOK.md - Trading rules
  - DATABASE_SCHEMA_SOURCE_OF_TRUTH.md - Data structure
  - ZERO_LOOKAHEAD_RULES.md - Temporal rules

---

**Last Updated:** 2026-01-11
**Dashboard Version:** V2.0 (Enhanced with AI)
**Required:** Python 3.8+, Streamlit, Anthropic SDK

**Philosophy:** Honesty over accuracy. AI-assisted, human-validated.
