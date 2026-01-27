# Quick Start - Trading Hub

**Get up and running in 5 minutes**

---

## 1. Install (One-Time Setup)

```bash
# Install required packages
pip install streamlit anthropic matplotlib

# Get API key from https://console.anthropic.com/
# Add to .env file:
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

---

## 2. Launch Dashboard

```bash
streamlit run app_trading_hub.py
```

**Opens at:** http://localhost:8501

---

## 3. Quick Tour

### Tab 1: Edge Discovery
1. Click **"Run Analysis"**
2. Wait 30 seconds
3. View top edges ranked by quality
4. Filter by win rate / avg R / trades
5. Export to CSV

### Tab 2: Strategy Builder
1. Pick entry model (e.g., "1m_close_break")
2. Set RR target (2.0 recommended)
3. Select ORB times (e.g., 1000)
4. Click **"Run Backtest"**
5. View equity curve & stats

### Tab 3: Backtest Results
- Compare RR targets (1.5 vs 2.0 vs 2.5 vs 3.0)
- View win rate and avg R charts

### Tab 4: Documentation
- Quick guides
- Zero-lookahead rules
- Known edges
- Resources

### Sidebar: AI Chat
1. Type question (e.g., "What's the best morning setup?")
2. Click **"Send"**
3. Get AI-powered insights
4. Click **"Clear"** to reset

---

## 4. Example Workflow

**Find best 10:00 setup:**

1. **Edge Discovery**
   - Run Analysis
   - Filter: Min WR = 0.54, Min Trades = 50
   - Find: "1000 UP" (55.5% WR, +0.11 R)

2. **Ask AI**
   - "Should I trade 10:00 UP every day or filter by PRE_ASIA?"
   - AI explains PRE_ASIA filtering improves edge

3. **Test Strategy**
   - Strategy Builder > Set: 1000 UP, RR=2.0
   - Run Backtest > Check results
   - Compare with/without filters

4. **Optimize RR**
   - Backtest Results > See RR comparison
   - Choose based on win rate preference

---

## 5. Top Edges (Pre-Discovered)

| Setup | Win Rate | Avg R | Trades | Type |
|-------|----------|-------|--------|------|
| 1000 UP after 0900 WIN | 57.9% | +0.16 | 114 | correlation |
| 1000 UP | 55.5% | +0.11 | 247 | baseline |
| 1100 UP PRE_ASIA > 50t | 55.1% | +0.10 | 107 | pre_block |
| 1100 DOWN after 0900 LOSS + 1000 WIN | 57.7% | +0.15 | 71 | correlation |

---

## 6. AI Chat Examples

**Q:** "What's the best setup for morning trades?"
**A:** The primary morning edge is 10:00 UP (55.5% WR, +0.11 R). If 09:00 wins first, 10:00 UP improves to 57.9% WR.

**Q:** "Why can't I use session type filters?"
**A:** Session types (EXPANDED, CONSOLIDATION) aren't known until AFTER the session closes. That's lookahead bias. Use PRE blocks instead.

**Q:** "Should I use RR=1.5 or RR=3.0?"
**A:** RR=1.5 has higher win rate (37.7%) but lower reward. RR=3.0 has lower win rate (19.4%) but bigger wins. Both are net negative without filters - use edge-based strategies (10:00 UP, correlations).

---

## 7. Keyboard Shortcuts

- **R** - Refresh dashboard
- **C** - Clear cache
- **F11** - Fullscreen

---

## 8. Troubleshooting

**AI not working?**
- Check ANTHROPIC_API_KEY in .env
- Restart dashboard after adding key

**Analysis slow?**
- First run takes 30 seconds (normal)
- Subsequent runs use cache

**No backtest data?**
```bash
python backtest_orb_exec_1m.py --rr-grid "1.5,2.0,2.5,3.0" --confirm 1
```

---

## 9. Resources

- **Full Setup:** SETUP_TRADING_HUB.md
- **Workflow:** WORKFLOW_GUIDE.md
- **Trading Rules:** TRADING_PLAYBOOK.md
- **Data Schema:** DATABASE_SCHEMA_SOURCE_OF_TRUTH.md

---

## 10. Philosophy

**Zero-Lookahead:** Only use information available AT decision time

**Honesty Over Accuracy:** 50-58% real win rates > 57%+ inflated backtests

**AI-Assisted, Human-Validated:** Use AI for insights, validate with data

---

**Ready to trade smarter? Launch the dashboard now!**

```bash
streamlit run app_trading_hub.py
```
