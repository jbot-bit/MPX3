#!/usr/bin/env python3
"""
MPX3 PROJECT ARBITER — INTELLIGENT GUARDIAN OVERRIDE

This is the DECISION AUTHORITY that determines:
- Whether Code Guardian must trigger
- Whether PASS 1 audit is mandatory
- Whether the task is allowed at all
- What protection level applies

Based on: master1.txt + master.txt

Run: python scripts/check/master_guardian.py "task description"
     python scripts/check/master_guardian.py --interactive

Exit codes:
  0 = SAFE (no guardian needed)
  1 = GUARDED (guardian required)
  2 = BLOCKED (forbidden)
  3 = AMBIGUOUS (need clarification)
"""

import sys
import os
import re
from pathlib import Path
from typing import Tuple, List, Optional

REPO_ROOT = Path(__file__).parent.parent.parent

# =============================================================================
# TASK CLASSIFICATION PATTERNS
# =============================================================================
TASK_PATTERNS = {
    'UI_UX': [
        r'ui\b', r'button', r'display', r'render', r'streamlit', r'layout',
        r'color', r'style', r'component', r'widget', r'dashboard', r'screen',
    ],
    'RESEARCH': [
        r'analyze', r'research', r'investigate', r'explore', r'understand',
        r'read', r'query', r'check', r'audit', r'review', r'examine',
    ],
    'DISCOVERY': [
        r'discover', r'find', r'search', r'experiment', r'test', r'try',
        r'edge_candidates', r'backtest', r'optimize', r'scan',
    ],
    'VALIDATION': [
        r'validate', r'promote', r'approve', r'reject', r'verify',
        r'validated_setups', r'autonomous.*validator',
    ],
    'PRODUCTION': [
        r'live', r'trading', r'execute', r'order', r'position',
        r'cost_model', r'execution_engine', r'entry_rules',
    ],
    'INFRASTRUCTURE': [
        r'guard', r'check', r'hook', r'pipeline', r'schema', r'migration',
        r'ci\b', r'cd\b', r'preflight', r'sync',
    ],
}

# =============================================================================
# RISK CLASSIFICATION
# =============================================================================
RISK_KEYWORDS = {
    'CRITICAL': [
        'cost_model', 'execution_engine', 'live trading', 'entry_rules',
        'position sizing', 'order execution', 'real money',
    ],
    'HIGH': [
        'validated_setups', 'config.py', 'expected_r', 'win_rate',
        'daily_features', 'config sync', 'production',
    ],
    'MEDIUM': [
        'edge_candidates', 'experimental', 'backtest', 'strategy_discovery',
        'edge_utils', 'edge_pipeline',
    ],
    'LOW': [
        'research', 'analysis', 'read-only', 'query', 'artifacts',
        'json', 'export', 'report',
    ],
    'NONE': [
        'docs', 'readme', 'comment', 'explain', 'describe', 'help',
    ],
}

# =============================================================================
# FORBIDDEN PATHS (from GUARDIAN.md / master.txt)
# =============================================================================
FORBIDDEN_PATHS = [
    'strategies/',
    'pipeline/',
    'trading_app/cost_model.py',
    'trading_app/entry_rules.py',
    'trading_app/execution_engine.py',
    'schema/migrations/',
]

# =============================================================================
# CANONICAL TABLES
# =============================================================================
CANONICAL_TABLES = ['daily_features', 'validated_setups', 'validated_setups_archive']


def classify_task(description: str) -> str:
    """Classify task type based on description."""
    desc_lower = description.lower()

    scores = {}
    for task_type, patterns in TASK_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, desc_lower))
        if score > 0:
            scores[task_type] = score

    if not scores:
        return 'AMBIGUOUS'

    # Return highest scoring type
    return max(scores, key=scores.get)


def classify_risk(description: str) -> str:
    """Classify risk level based on description."""
    desc_lower = description.lower()

    # Check from highest to lowest risk
    for risk_level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE']:
        keywords = RISK_KEYWORDS[risk_level]
        if any(kw in desc_lower for kw in keywords):
            return risk_level

    return 'MEDIUM'  # Default to medium if unclear


def check_forbidden_paths(description: str) -> List[str]:
    """Check if description mentions forbidden paths."""
    desc_lower = description.lower()
    touched = []

    for path in FORBIDDEN_PATHS:
        # Check direct mention
        if path.rstrip('/').lower() in desc_lower:
            touched.append(path)
        # Check component names
        if 'cost_model' in desc_lower and 'cost_model' in path:
            touched.append(path)
        if 'execution_engine' in desc_lower and 'execution_engine' in path:
            touched.append(path)
        if 'entry_rules' in desc_lower and 'entry_rules' in path:
            touched.append(path)
        if 'pipeline' in desc_lower and 'pipeline' in path:
            touched.append(path)

    return list(set(touched))


def check_canonical_tables(description: str) -> List[str]:
    """Check if description mentions canonical tables."""
    desc_lower = description.lower()
    touched = []

    for table in CANONICAL_TABLES:
        if table in desc_lower:
            touched.append(table)

    return touched


def determine_verdict(task_type: str, risk_level: str, forbidden_touched: List[str], tables_touched: List[str]) -> Tuple[str, str, List[str]]:
    """
    Determine the verdict based on classification.

    Returns: (verdict, pass_allowed, reasoning)
    """
    reasoning = []

    # BLOCKED: Forbidden paths touched
    if forbidden_touched:
        reasoning.append(f"Forbidden paths potentially touched: {', '.join(forbidden_touched)}")
        reasoning.append("GUARDIAN.md explicitly prohibits editing these paths")
        reasoning.append("Requires explicit authorization (canofix_*.txt)")
        return 'BLOCKED', 'NONE', reasoning

    # CRITICAL risk = BLOCKED or highly restricted
    if risk_level == 'CRITICAL':
        reasoning.append("Task touches CRITICAL risk components (live trading, cost model, execution)")
        reasoning.append("These changes require explicit authorization")
        reasoning.append("Create authorization file with detailed justification")
        return 'BLOCKED', 'NONE', reasoning

    # HIGH risk = GUARDED with PASS 1 + PASS 2
    if risk_level == 'HIGH':
        reasoning.append("Task touches HIGH risk components (validated_setups, config sync)")
        reasoning.append("Guardian PASS 1 audit is MANDATORY")
        reasoning.append("PASS 2 allowed only after PASS 1 approval")
        return 'GUARDED', 'PASS 1 + PASS 2', reasoning

    # Canonical tables touched = GUARDED
    if tables_touched:
        reasoning.append(f"Canonical tables potentially affected: {', '.join(tables_touched)}")
        reasoning.append("Guardian audit required for any canonical table operations")
        return 'GUARDED', 'PASS 1 + PASS 2', reasoning

    # MEDIUM risk = GUARDED with PASS 1 only
    if risk_level == 'MEDIUM':
        reasoning.append("Task involves MEDIUM risk components (discovery, experiments)")
        reasoning.append("Guardian PASS 1 audit recommended")
        return 'GUARDED', 'PASS 1 ONLY', reasoning

    # UI/UX only = SAFE
    if task_type == 'UI_UX':
        reasoning.append("Task is UI/UX only - no trading logic affected")
        reasoning.append("No forbidden paths involved")
        reasoning.append("Proceed without guardian")
        return 'SAFE', 'N/A', reasoning

    # RESEARCH = SAFE (read-only)
    if task_type == 'RESEARCH' and risk_level in ['LOW', 'NONE']:
        reasoning.append("Task is research/read-only")
        reasoning.append("No writes to production systems")
        return 'SAFE', 'N/A', reasoning

    # LOW/NONE risk = SAFE
    if risk_level in ['LOW', 'NONE']:
        reasoning.append("Task is low/no risk")
        reasoning.append("No canonical components affected")
        return 'SAFE', 'N/A', reasoning

    # Ambiguous = ask for clarification
    reasoning.append("Task scope is unclear or mixed")
    reasoning.append("Cannot determine risk level with confidence")
    reasoning.append("Please provide more specific description")
    return 'AMBIGUOUS', 'UNKNOWN', reasoning


def get_next_action(verdict: str, pass_allowed: str) -> str:
    """Determine the next action based on verdict."""
    if verdict == 'SAFE':
        return "Proceed with implementation. Run test_app_sync.py after changes."

    if verdict == 'GUARDED':
        if pass_allowed == 'PASS 1 ONLY':
            return "Run PASS 1 audit first: analyze impact, cite files/lines, do NOT edit code."
        else:
            return "Run PASS 1 audit. After approval, proceed to PASS 2 with smallest possible diffs."

    if verdict == 'BLOCKED':
        return "STOP. Create authorization file (canofix_<description>.txt) with justification, or modify task to avoid forbidden paths."

    return "Clarify task scope before proceeding. Specify exactly what will be read/written."


def print_verdict(task: str, task_type: str, risk_level: str, verdict: str, guardian_required: bool, pass_allowed: str, reasoning: List[str], next_action: str):
    """Print the verdict in the required format."""
    print("=" * 70)
    print("MPX3 PROJECT ARBITER — VERDICT")
    print("=" * 70)
    print()
    print(f"Task: {task[:100]}{'...' if len(task) > 100 else ''}")
    print()
    print(f"Classification:")
    print(f"  Task Type: {task_type}")
    print(f"  Risk Level: {risk_level}")
    print()

    # Verdict with ASCII markers
    markers = {'SAFE': '[OK]', 'GUARDED': '[!!]', 'BLOCKED': '[XX]', 'AMBIGUOUS': '[??]'}
    print(f"Verdict: {markers.get(verdict, '[?]')} {verdict}")
    print()
    print(f"Guardian Required: {'YES' if guardian_required else 'NO'}")
    print(f"Pass Allowed: {pass_allowed}")
    print()
    print("Reasoning:")
    for r in reasoning:
        print(f"  - {r}")
    print()
    print("Next Action:")
    print(f"  {next_action}")
    print()
    print("=" * 70)


def main():
    # Get task description
    if len(sys.argv) > 1 and sys.argv[1] != '--interactive':
        task = ' '.join(sys.argv[1:])
    elif '--interactive' in sys.argv or len(sys.argv) == 1:
        print("MPX3 PROJECT ARBITER")
        print("=" * 40)
        print("Describe your task (what do you want to do?):")
        task = input("> ").strip()
        if not task:
            print("No task provided. Exiting.")
            return 3
    else:
        task = ' '.join(sys.argv[1:])

    # Classify
    task_type = classify_task(task)
    risk_level = classify_risk(task)
    forbidden_touched = check_forbidden_paths(task)
    tables_touched = check_canonical_tables(task)

    # Determine verdict
    verdict, pass_allowed, reasoning = determine_verdict(
        task_type, risk_level, forbidden_touched, tables_touched
    )

    guardian_required = verdict in ['GUARDED', 'BLOCKED']

    # Get next action
    next_action = get_next_action(verdict, pass_allowed)

    # Print
    print_verdict(task, task_type, risk_level, verdict, guardian_required,
                  pass_allowed, reasoning, next_action)

    # Return exit code
    exit_codes = {'SAFE': 0, 'GUARDED': 1, 'BLOCKED': 2, 'AMBIGUOUS': 3}
    return exit_codes.get(verdict, 3)


if __name__ == "__main__":
    sys.exit(main())
