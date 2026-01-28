# Proposal: Generative AI for Novel Strategy Discovery

This document details the vision, architecture, and implementation plan for creating a generative AI system capable of discovering novel trading strategies from market data.

## 1. Vision

The current system is highly effective at validating pre-defined trading strategies (e.g., `edge_discovery_live.py`). This proposal aims to transcend that by building a system that can *invent* entirely new strategies. We will use a generative model to analyze market data and propose novel patterns, filters, and logic that a human analyst might never conceive of.

The goal is to create a "Strategy Gene Lab" where new trading ideas are born, evolved, and tested in a continuous, automated loop.

## 2. Proposed Architecture

The system will be an "Evolutionary Algorithm" driven by a Large Language Model (LLM).

1.  **Population Generation:** The LLM will be prompted to create an initial "population" of trading strategies. Each strategy will be a self-contained Python function.
    - **Prompt:** *"You are an expert quantitative trading strategist. Your task is to invent a new trading strategy for Micro Gold (MGC) futures. The strategy should be a Python function that takes a pandas DataFrame of market data and returns a trading signal (1 for long, -1 for short, 0 for flat). Be creative. Use any combination of technical indicators, price patterns, or statistical measures you think will be profitable."*

2.  **Fitness Evaluation:** Each strategy function in the population will be passed to our existing backtesting engine (`strategies/execution_engine.py`). The backtester will evaluate the strategy's performance and assign a "fitness score" (e.g., Sharpe ratio, Calmar ratio, or a custom metric based on realized expectancy).

3.  **Selection & Evolution:** The best-performing strategies (the "fittest") are selected. The LLM is then used to "breed" and "mutate" these strategies:
    - **Breeding (Crossover):** The LLM will be prompted to combine the logic of two high-performing parent strategies. *"Here are two profitable trading strategies. Create a new child strategy that combines the best elements of both."*
    - **Mutation:** The LLM will be prompted to make random, creative changes to a high-performing strategy. *"Here is a profitable trading strategy. Introduce a random mutation to it. This could be changing a parameter, adding a new filter, or using a different indicator."*

4.  **Iteration:** The newly generated "offspring" strategies form the next generation. The process repeats, with each generation theoretically becoming more profitable than the last.

5.  **Candidate Promotion:** When a strategy consistently performs well for several generations, it is "promoted" to become a formal "edge candidate". It is then fed into the existing `strategy-validator` skill for rigorous, out-of-sample testing before being considered for live deployment.

## 3. Implementation Plan

**Phase 1: The "Strategy Gene" Format**
- Define a standardized, self-contained format for a single trading strategy. This will likely be a Python function with a specific signature, e.g., `def my_strategy(df: pd.DataFrame) -> pd.Series:`.

**Phase 2: The Backtesting Harness**
- Create a script that can take a dynamically generated Python strategy function, execute it against historical data, and return a fitness score. This will be the core of the evaluation step.

**Phase 3: The LLM "Breeder" and "Mutator"**
- Develop the prompts and the orchestration logic for using the LLM to perform the crossover and mutation operations.

**Phase 4: The Evolutionary Loop**
- Tie everything together into a master script that runs the full evolutionary loop: generate, evaluate, select, breed, mutate, repeat.

**Phase 5: Integration with Existing Systems**
- Build the pipeline to automatically promote high-performing generated strategies into the `edge_candidates_ui` and `strategy-validator` workflow.

## 4. Integration with Existing Skills

- **`strategy-validator`**: This skill is the final gatekeeper. No matter how profitable a generated strategy appears to be "in-sample", it must pass the rigorous, out-of-sample validation of this skill before it can be trusted.
- **`trading-memory`**: As generated strategies are tested, the `trading-memory` skill will record their performance, helping to identify which *types* of generated strategies tend to work best.
- **`edge-evolution-tracker`**: This skill will be crucial for monitoring the performance of generated strategies *after* they have been deployed, to see if their performance decays over time.
