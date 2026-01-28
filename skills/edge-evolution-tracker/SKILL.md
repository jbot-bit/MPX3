---
name: edge-evolution-tracker
description: The backend analysis engine for the Live Edge Discovery & Market Awareness Terminal. It identifies the current market regime and detects the degradation of validated trading edges over time.
allowed-tools: Read, Bash(python:*)
context: fork
agent: general-purpose
---

# Edge Evolution Tracker Skill

## 1. Core Purpose

This skill serves as the primary backend analysis engine for the **Live Edge Discovery & Market Awareness Terminal**. Its purpose is to provide the critical, time-sensitive data that powers the terminal's "Market Awareness" component.

It continuously analyzes market data to answer two key questions:
1.  **What is the market's current personality (regime)?**
2.  **Are our existing strategies still effective in this regime?**

---

## 2. Key Functions for the Terminal

### Function 1: Market Regime Detection

This is the skill's most important function for the terminal. It runs in the background to determine the current market regime, which is then displayed on the Market Awareness Dashboard.

-   **Regime Types:**
    -   **Trending:** Breakout strategies are favored.
    -   **Range-Bound:** Mean-reversion strategies are favored.
    -   **Volatile:** High-risk, caution is advised.
    -   **Quiet:** Low probability, patience is advised.
-   **Methodology:** The skill uses a combination of rolling volatility (ATR), trend-strength indicators (ADX), and the historical success rate of breakout trades to classify the current regime.
-   **Terminal Integration:** The output of this function is a single, clear status (e.g., "RANGE-BOUND") that is displayed prominently in the terminal, allowing the user to instantly grasp the market's current character.

### Function 2: Edge Degradation Monitoring

This function monitors the ongoing performance of all strategies listed in the `validated_setups` table.

-   **Purpose:** To detect when a previously profitable strategy is no longer performing as expected in the current market.
-   **Methodology:** The skill calculates the win rate and expected R-multiple of each strategy over rolling 30, 60, and 90-day windows and compares these metrics to their long-term historical averages.
-   **Terminal Integration:** If a strategy's performance drops below a critical threshold (e.g., a 15% drop in win rate over 90 days), this skill flags the strategy as "Degraded". This status will be clearly visible in the terminal's "Upcoming Strategy Radar", warning the user to be cautious with that particular setup.

---

## 3. Relationship to Other Tools

-   **`Live Edge Discovery & Market Awareness Terminal`**: This skill is the engine that provides the top-level "awareness" data for the terminal's UI.
-   **`edge_discovery_live.py`**: While `edge_discovery_live.py` is used for finding long-term edges, this skill is focused on monitoring their performance in the *current* market.
-   **`trading-memory`**: This skill uses the historical data stored by the `trading-memory` skill to perform its time-series analysis.

By providing a constant, automated assessment of the market regime and strategy health, this skill ensures that the user is always making decisions based on the most relevant and up-to-date information.
