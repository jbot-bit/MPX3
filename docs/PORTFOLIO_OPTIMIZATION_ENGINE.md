# Proposal: Multi-Instrument Portfolio Optimization Engine

This document details the plan for building a portfolio-level optimization engine. This system will elevate the project from managing a collection of individual strategies to optimizing a cohesive, cross-instrument portfolio to maximize risk-adjusted returns and minimize drawdowns.

## 1. Vision

Currently, strategies are evaluated on their individual merits. However, in professional quantitative trading, the ultimate measure of success is the performance of the *portfolio as a whole*. A seemingly mediocre strategy might be incredibly valuable if its returns are uncorrelated with the rest of the portfolio, as it can smooth out the equity curve and reduce overall risk.

The vision is to build an engine that thinks like a hedge fund portfolio manager. It will analyze the entire suite of validated strategies (across MGC, NQ, MPL, etc.) and construct the "optimal" combination of them to achieve the best possible risk-adjusted return.

## 2. Key Features & Capabilities

### 2.1. Correlation Matrix Analysis
-   The engine's first task is to compute a **correlation matrix** of the historical returns of all validated strategies.
-   This matrix is the cornerstone of portfolio optimization. It will answer critical questions like:
    -   Do the MGC and NQ ORB strategies tend to win or lose at the same time?
    -   Does the 18:00 ORB strategy provide good diversification from the 10:00 ORB strategy?
    -   Are there any strategies that are highly correlated, suggesting we are taking on redundant risk?

### 2.2. Mean-Variance Optimization (MVO) & The Efficient Frontier
-   Using the strategy returns and their correlations, the engine will perform Mean-Variance Optimization (MVO), the Nobel Prize-winning technique developed by Harry Markowitz.
-   The output of MVO is the **Efficient Frontier**: a curve that shows the best possible expected return for any given level of risk (standard deviation).
-   The engine will generate a visual plot of the Efficient Frontier, with each point on the curve representing a different portfolio allocation (e.g., 50% MGC 1000 ORB, 30% NQ 1100 ORB, 20% MPL 1800 ORB).

### 2.3. Optimal Portfolio Construction
-   The engine will identify several key portfolios on the Efficient Frontier:
    -   **The Maximum Sharpe Ratio Portfolio:** The single portfolio that offers the best risk-adjusted return. This is often considered the "optimal" portfolio.
    -   **The Minimum Variance Portfolio:** The portfolio with the absolute lowest risk, for the most conservative risk profile.
    -   **Custom Risk Target Portfolios:** The ability for the user to select a desired level of risk and have the engine provide the portfolio that offers the highest return for that risk level.

### 2.4. Automated Rebalancing Recommendations
-   Portfolio characteristics change over time. The engine will run on a periodic basis (e.g., weekly or monthly) and provide **rebalancing recommendations**.
-   For example, it might suggest: *"The correlation between MGC and NQ has increased. To maintain optimal diversification, recommend reducing NQ allocation from 30% to 25% and increasing MPL allocation from 20% to 25%."*

## 3. Implementation Plan

**Phase 1: Standardized Returns Data**
-   Ensure that the historical returns for every validated strategy are stored in a standardized format in the database (e.g., in the `trade_journal` table from the `trading-memory` skill).

**Phase 2: The Correlation Engine**
-   Build a script that can query the historical returns for all strategies and compute the correlation matrix. This will likely involve heavy use of `pandas`.

**Phase 3: The MVO Engine**
-   Implement the Mean-Variance Optimization algorithm. This can be done using libraries like `PyPortfolioOpt`, `cvxpy`, or even from scratch with `numpy` for maximum control.

**Phase 4: The Visualizer**
-   Create a new Streamlit app (`portfolio_optimizer_app.py`) that:
    -   Displays the correlation matrix as a heatmap.
    -   Plots the Efficient Frontier.
    -   Allows the user to interactively explore different points on the frontier and see the corresponding portfolio allocations.
    -   Presents the rebalancing recommendations in a clear, actionable format.

## 4. Integration with Existing Skills & Systems

-   **`validated_setups` table:** This table will be the primary input for the optimization engine, providing the list of available "assets" (strategies) to include in the portfolio.
-   **`trading-memory` skill:** The historical trade data stored by this skill is the raw material for the correlation and MVO calculations.
-   **`AI-Powered Prop Firm Manager`**: The output of the portfolio optimizer will be a key input for the AI Manager. The AI Manager's capital allocation decisions will be guided by the optimal portfolio weights recommended by this engine. For example, instead of just allocating capital based on individual strategy performance, it will allocate capital to achieve the target portfolio weights.
-   **`edge-evolution-tracker`**: This skill tracks when individual strategies begin to degrade. This is a critical input. If a strategy is degrading, the portfolio optimizer should be automatically re-run to find the new optimal portfolio *without* that failing strategy.
