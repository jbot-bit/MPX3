---
name: strategy-validator
description: The backend validation engine for the Live Edge Discovery & Market Awareness Terminal. It runs a rigorous, multi-phase validation checklist on candidate edges to approve them for promotion.
allowed-tools: Read, Bash(python:*)
context: fork
agent: general-purpose
---

# Strategy Validator Skill

## 1. Core Purpose

This skill serves as the backend validation engine for the **Live Edge Discovery & Market Awareness Terminal**. Its sole purpose is to be invoked by the terminal to run a rigorous, automated, multi-phase validation checklist on a newly discovered "candidate edge".

It does not act on its own, but rather as a service that the terminal calls upon during the **In-App Promotion Workflow**. It provides the pass/fail results that determine whether a candidate edge is worthy of being promoted to a `validated_setup`.

---

## 2. The Validation Workflow for the Terminal

When a user in the **Edge Discovery Terminal** decides to validate a candidate edge, the terminal's backend will invoke this skill. The skill will then execute the following automated checklist, returning the results of each phase to the terminal UI.

### Phase 1: Data Integrity Check
-   **Action:** Verifies that the data underlying the candidate edge is clean and complete.
-   **Checks:** No NULL values, correct data types, sufficient sample size (>= 30 trades).
-   **Terminal UI:** Displays `[PASS]` or `[FAIL]` next to the "Data Integrity" checklist item.

### Phase 2: Statistical Significance Test
-   **Action:** Calculates the core performance metrics of the candidate edge.
-   **Checks:**
    -   Is the Win Rate statistically significant?
    -   Is the **Realized Expectancy at production costs ($8.40 RT)** greater than the minimum threshold (e.g., +0.15R)?
-   **Terminal UI:** Displays the calculated Win Rate and Expectancy, and a `[PASS]` or `[FAIL]` status. A `[FAIL]` here is critical.

### Phase 3: Cost & Slippage Stress Test
-   **Action:** Re-calculates the expectancy under harsher cost assumptions to test the edge's robustness.
-   **Checks:**
    -   Does the expectancy remain positive at +25% costs?
    -   Does the expectancy remain positive at +50% costs?
-   **Terminal UI:** Shows the expectancy at each stress level and a `[PASS]` or `[FAIL]` status.

### Phase 4: Regime-Sensitivity Analysis
-   **Action:** Checks how the candidate edge performs across different market regimes.
-   **Checks:**
    -   Does the edge perform well only in "Trending" markets?
    -   Does it fail completely in "Range-Bound" markets?
-   **Terminal UI:** Displays a summary of performance by regime, helping the user understand the conditions in which the edge is most effective.

---

## 3. Integration with the Terminal

-   **Invocation:** The `Live Edge Discovery & Market Awareness Terminal` is the **only** intended caller of this skill. A user will click a "Run Validation" button in the UI, which triggers a backend call to this skill.
-   **Input:** The skill receives the filter parameters for the candidate edge from the terminal.
-   **Output:** The skill returns a structured JSON or dictionary containing the pass/fail status and detailed results for each of the four validation phases. The terminal is then responsible for rendering this information in the "Validation Checklist" UI.
-   **Promotion Gatekeeper:** An edge cannot be promoted to `validated_setups` within the app unless this skill returns a "PASS" on all critical phases of the validation checklist.

This skill acts as the impartial, automated quality assurance step in the journey of an idea from discovery to a live, validated trading strategy.
