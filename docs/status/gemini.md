# Gemini Project Context: MGC Trading System

This document provides a comprehensive overview of the MGC Trading System project to give you the necessary context for development, analysis, and strategic improvement.

## 1. Project Overview

This project is a sophisticated algorithmic trading system focused on Micro Gold futures (MGC). The core purpose is to discover, validate, and deploy trading strategies based on Opening Range Breakouts (ORBs). It includes a full data pipeline, backtesting engine, analysis tools, and trading applications.

**Primary Goal:** To build a profitable, automated trading system with a strong emphasis on data integrity, rigorous validation, and honest performance metrics.

**Key Technologies:**
- **Language:** Python
- **Database:** DuckDB (`gold.db`)
- **Data Source:** Databento
- **Core Logic:** ORB-based strategies, session statistics, and technical indicators (RSI).

## 2. Core Concepts & Business Logic

### Strategy Family Isolation
This is a critical rule. All analysis, validation, and conclusions apply *only* to the active `STRATEGY_FAMILY`. Cross-family inference is forbidden. This prevents contamination of findings and ensures a focused, methodical approach to research.

- **ORB_L4:** 0900, 1000 ORBs with L4_CONSOLIDATION filter.
- **ORB_BOTH_LOST:** 1100 ORB with sequential failure pattern.
- **ORB_RSI:** 1800 ORB with momentum exhaustion.
- **ORB_NIGHT:** 2300, 0030 ORBs (Research Only).

### Canonical Realized RR (Reward/Risk)
The system uses **realized RR**, which embeds transaction costs directly into the calculation. This provides a more honest and accurate measure of a strategy's profitability compared to theoretical RR.

- **Source of Truth:** `pipeline/cost_model.py` defines all costs and formulas.
- **Friction Model:** Includes commission, spread, and slippage for realistic backtesting.
- **MGC Cost:** $8.40 per round turn is the mandatory baseline for validation.

### Database & Config Synchronization
A critical safety protocol. The `validated_setups` table in `gold.db` and the `config.py` file must ALWAYS be synchronized. Failure to do so can lead to real financial losses.

- **Verification Command:** `python test_app_sync.py` **MUST** be run after any changes to strategies, database, or configuration files.

## 3. Project Structure

The project is organized into several key directories:

- `trading_app/`: Contains the main trading applications, UI, and business logic.
- `pipeline/`: Data ingestion, normalization, and feature engineering scripts.
- `analysis/`: Scripts for querying, analyzing, and visualizing data.
- `strategies/`: Core execution engine and strategy definitions.
- `docs/`: Extensive documentation, research findings, and system architecture.
- `skills/`: Specialized agent skills to automate and guide development.
- `tests/`: Pytest unit and integration tests.
- `data/db/`: Location of the `gold.db` DuckDB database.

**Key Files:**
- `claude.md`: The original context file for the Claude model.
- `gemini.md`: This file, the primary context for the Gemini model.
- `CANONICAL_LOGIC.txt`: The mathematical source of truth for all trading calculations.
- `schema.sql`: The database schema definition.
- `requirements.txt`: Python package dependencies.

## 4. Key Commands

- **Backfill Data:**
  `python pipeline/backfill_databento_continuous.py YYYY-MM-DD YYYY-MM-DD`
- **Initialize Database:**
  `python pipeline/init_db.py`
- **Run Sync Test (CRITICAL):**
  `python test_app_sync.py`
- **Run Strategy Validator:**
  `python scripts/audit/autonomous_strategy_validator.py`

## 5. Available Skills

This project is enhanced with a suite of "skills" to automate complex tasks and enforce best practices. These should be used proactively.

- **`code-guardian`**: Protects critical files from unintended changes.
- **`quick-nav`**: Provides fast, context-aware navigation of the codebase.
- **`project-organizer`**: Helps clean up and organize the project directory.
- **`focus-mode`**: A task management system to maintain focus.
- **`strategy-validator`**: An autonomous 6-phase framework for validating trading strategies.
- **`frontend-design`**: Guides the creation of professional trading UIs.
- **`database-design`**: Assists with schema design, migrations, and optimization.
- **`trading-memory`**: A system for learning from historical trade outcomes.
- **`market-anomaly-detection`**: Detects unusual market conditions and execution issues.
- **`edge-evolution-tracker`**: Monitors strategy performance over time to detect degradation.
- **`brainstorming`**: A structured process for planning new features.
- **`reflect`**: A session-end learning and continuous improvement mechanism.

This document serves as your starting point for understanding the project. Refer to the `docs/` and `skills/` directories for more in-depth information on specific topics.
