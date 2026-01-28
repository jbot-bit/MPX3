# Live Edge Discovery & Market Awareness Terminal
## Design & Architecture Document

**Version:** 3.0
**Status:** Personalized Implementation Plan

---

## 1. Guiding Principles ("Honesty Over Outcome")

This document outlines the design for the **Live Edge Discovery & Market Awareness Terminal**. The development and use of this application are strictly governed by the following principles:

1.  **Honesty First:** The system will always present data in the most intellectually honest way possible. Costs and slippage are applied by default, and vanity metrics are avoided.
2.  **Perfect Backtesting:** Backtest results must be rigorous, statistically sound, and designed to minimize curve-fitting. Out-of-sample validation is not optional.
3.  **Data Integrity is Paramount:** Data verification must be a constant, automated process that is clearly visible.
4.  **Avoid Performance Drift:** The system must proactively detect and flag any degradation in strategy performance.
5.  **Accelerate Discovery:** The primary goal is to create an intuitive environment for discovering new, robust trading edges.
6.  **Enhance User Performance:** The system should actively assist the user, leveraging personalized data to improve their focus, discipline, and decision-making.

---

## 2. Application Layout & Components

The application is a single-page dashboard designed for focus and clarity.

### Component 1: Market & Personal Awareness Dashboard

**Purpose:** To provide a real-time, honest snapshot of the current market state and your personal performance patterns within it.

**Data Sources:**
-   `skills/edge-evolution-tracker`
-   `skills/market-anomaly-detection`
-   `trading_app/market_scanner.py`
-   `skills/trading-memory`

**UI Elements:**
-   **Data Integrity Status:** `[HEALTHY]` or `[WARNING]` widget.
-   **Regime Status:** Clear indicator of the current market regime (e.g., "Trending", "Range-Bound").
-   **Key Market Metrics:** Table of real-time stats (Asia Travel, London Reversals, etc.).
-   **Anomaly Alerts:** Displays active market anomalies (e.g., "WARNING: Spreads are 2x Normal").
-   **[NEW V3] Your Personal Insights Panel:**
    -   This panel is powered by the `trading-memory` skill and provides personalized, actionable advice based on *your* historical execution data.
    -   **Example Insights:**
        -   `"You are on a 2-trade losing streak. Your `trading-memory` shows you tend to force trades here. Wait for A+ setups only."`
        -   `"Market is quiet. Your highest win rate occurs in these conditions. Stay patient and focused."`
        -   `"Your slippage on NQ has been 0.75 points higher than your average today. Consider using limit orders."`

### Component 2: Upcoming Strategy Radar

**Purpose:** To provide a clear, honest view of validated strategies, with a focus on avoiding performance drift.

**Data Sources:**
-   `trading_app/setup_scanner.py`
-   `skills/edge-evolution-tracker`
-   `gold.db` -> `validated_setups` table

**UI Elements:**
-   **Strategy List:** Dynamic list of all validated strategies.
-   **Status Indicator:** `ACTIVE`, `WAITING`, `SKIPPED`.
-   **Performance Drift Indicator:** `⬆️` (Improving), `➡️` (Stable), `⬇️` (Degrading) icon next to each strategy, with a pop-up chart showing the rolling 90-day win rate.

### Component 3: Interactive Edge Discovery Lab

**Purpose:** To provide an intuitive interface for discovering and validating new edges, with a ruthless focus on "Honesty-First Backtesting" and user focus.

**Data Sources:**
-   `analysis/query_engine.py`
-   `skills/strategy-validator`
-   `gold.db`

**UI Elements & Workflow:**
-   **[NEW V3] "Begin Research Session" Button:**
    -   Clicking this button initiates a **Focus Mode** session, powered by your `focus-mode` skill.
    -   A 25-minute timer starts within the app. The UI is simplified to remove non-essential elements, helping you concentrate solely on the task of discovery.
-   **"Honesty-First" Backtesting Framework:**
    -   Mandatory in-sample vs. out-of-sample testing.
    -   All results are calculated *after* the `$8.40` realistic cost model.
-   **The "Honesty Panel" Results Display:**
    -   Includes Core Metrics (Win Rate, Trades) and advanced Risk Metrics (Sharpe Ratio, Calmar Ratio, Max Drawdown).

---

## 3. The In-App Promotion Workflow (V3)

This workflow remains the gatekeeper for promoting strategies, now with even more rigor.

-   **Step 1: Discover a Robust Edge:** Find a profitable edge using the in-sample/out-of-sample framework.
-   **Step 2: Automated "Perfection & Honesty" Validation:** The app runs the candidate through the `strategy-validator` checklist, including Cost Stress Tests, Slippage Stress Tests, Monte Carlo Simulation, and Regime Sensitivity Analysis.
-   **Step 3: Promote to Validated:** Only if all critical phases pass, the **"Promote to Validated"** button becomes active, which writes to the database and runs the mandatory `test_app_sync.py` verification.

---

## 4. [NEW V3] Development & Maintenance Protocol

To ensure the terminal itself remains robust, bug-free, and aligned with project standards, the following protocol is formalized:

-   **`code-guardian` Enforcement:** All source code files for the `Live Edge Discovery & Market Awareness Terminal` will be added to the `code-guardian`'s list of protected files. No direct modifications are allowed without triggering the guardian's verification steps.
-   **`code-review-pipeline` Mandate:** Any proposed changes, new features, or bug fixes for the terminal application *must* be processed through the multi-agent `code-review-pipeline` skill before they can be merged. This ensures that all changes are vetted for security, architectural soundness, and correctness.
-   **`project-organizer` Alignment:** The file structure for the terminal application and its related components will adhere to the conventions established by the `project-organizer` skill to ensure long-term maintainability.

By integrating these skills into the development process of the tool itself, we protect the core asset and ensure it remains a reliable foundation for your trading and research.
