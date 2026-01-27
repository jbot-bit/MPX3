"""
Test AI Source Lock enforcement.

Uses AST scanning to ensure NO files call the Anthropic API directly.
All AI calls MUST route through trading_app/ai_guard.py.

Also tests runtime behavior: evidence pack validation, fail-closed gates, etc.

Run:
    pytest tests/test_ai_source_lock.py -v
"""

import pytest
import ast
from pathlib import Path
from typing import List, Tuple
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "trading_app"))

# Import AI guard components
from ai_guard import (
    guarded_chat_answer,
    validate_evidence_pack,
    EvidencePack,
    SetupInfo,
    EngineEvaluation,
    assert_ai_lock_enabled
)


class AnthropicClientFinder(ast.NodeVisitor):
    """AST visitor to find direct Anthropic API calls."""

    def __init__(self):
        self.violations = []
        self.has_anthropic_import = False

    def visit_Import(self, node):
        """Check for 'import anthropic'."""
        for alias in node.names:
            if alias.name == "anthropic" or alias.name.startswith("anthropic."):
                self.has_anthropic_import = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Check for 'from anthropic import ...'."""
        if node.module and (node.module == "anthropic" or node.module.startswith("anthropic.")):
            # Check if importing Anthropic class
            for alias in node.names:
                if alias.name == "Anthropic":
                    self.has_anthropic_import = True
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check for Anthropic() instantiation or .messages.create() calls."""

        # Check for Anthropic() instantiation
        if isinstance(node.func, ast.Name):
            if node.func.id == "Anthropic":
                self.violations.append({
                    "lineno": node.lineno,
                    "col_offset": node.col_offset,
                    "type": "Anthropic() client instantiation"
                })

        # Check for client.messages.create() calls
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "create":
                # Check if it's .messages.create()
                if isinstance(node.func.value, ast.Attribute):
                    if node.func.value.attr == "messages":
                        self.violations.append({
                            "lineno": node.lineno,
                            "col_offset": node.col_offset,
                            "type": "client.messages.create() direct API call"
                        })

        self.generic_visit(node)


def is_allowed_exception(file_path: Path, repo_root: Path) -> Tuple[bool, str]:
    """
    Check if file is an allowed exception for direct Anthropic API calls.

    Returns:
        (is_allowed, reason)
    """
    rel_path = file_path.relative_to(repo_root)
    rel_path_str = str(rel_path).replace("\\", "/")

    # Exception 1: ai_guard.py itself (THE ONLY CHOKE POINT)
    if rel_path_str == "trading_app/ai_guard.py":
        return True, "AI Guard module (the single choke point)"

    # Exception 2: chart_analyzer.py (uses vision API for chart analysis, not trading advice)
    if rel_path_str == "trading_app/chart_analyzer.py":
        return True, "Chart vision analyzer (image analysis, not text chat with database)"

    # Exception 3: csv_chart_analyzer.py (similar to chart_analyzer)
    if rel_path_str == "trading_app/csv_chart_analyzer.py":
        return True, "CSV chart analyzer (image analysis, not text chat with database)"

    # Exception 4: Archived code
    if rel_path_str.startswith("_archive/") or rel_path_str.startswith("_INVALID_SCRIPTS_ARCHIVE/"):
        return True, "Archived code"

    # Exception 5: Test files (this file tests the guard)
    if rel_path_str.startswith("tests/") and "test_" in file_path.name:
        return True, "Test file"

    # Exception 6: Standalone experiments/research (not part of production)
    if rel_path_str.startswith("research/") or rel_path_str.startswith("experiments/"):
        return True, "Research/experiment code (not production)"

    return False, ""


def scan_file_for_anthropic_calls(file_path: Path, repo_root: Path) -> List[dict]:
    """
    Scan a Python file for direct Anthropic API calls.

    Returns:
        List of violations with file path, line number, and details
    """
    # Check if allowed exception
    is_allowed, reason = is_allowed_exception(file_path, repo_root)
    if is_allowed:
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        finder = AnthropicClientFinder()
        finder.visit(tree)

        # Only report if file has anthropic import AND violations
        if finder.has_anthropic_import and finder.violations:
            rel_path = file_path.relative_to(repo_root)
            return [
                {
                    "file": str(rel_path).replace("\\", "/"),
                    "line": v["lineno"],
                    "type": v["type"]
                }
                for v in finder.violations
            ]

    except (SyntaxError, UnicodeDecodeError):
        # Skip files with syntax errors or encoding issues
        pass

    return []


# ================================================================================
# AST SCAN TESTS (PREVENT BYPASS)
# ================================================================================

def test_no_direct_anthropic_calls_in_trading_app():
    """Test that trading_app/ has no direct Anthropic API calls (except ai_guard.py)."""
    repo_root = Path(__file__).parent.parent
    trading_app_dir = repo_root / "trading_app"

    if not trading_app_dir.exists():
        pytest.skip("trading_app/ directory not found")

    violations = []

    # Scan all Python files in trading_app/
    for py_file in trading_app_dir.rglob("*.py"):
        file_violations = scan_file_for_anthropic_calls(py_file, repo_root)
        violations.extend(file_violations)

    if violations:
        violation_report = "\n".join(
            f"  - {v['file']}:{v['line']} - {v['type']}"
            for v in violations
        )
        pytest.fail(
            f"AI SOURCE LOCK VIOLATION: Found {len(violations)} direct Anthropic API call(s) in trading_app/:\n"
            f"{violation_report}\n\n"
            f"ALL AI CALLS MUST ROUTE THROUGH:\n"
            f"  from trading_app.ai_guard import guarded_chat_answer\n"
            f"  response = guarded_chat_answer(question, evidence_pack, conversation_history)\n\n"
            f"NO OTHER FILE MAY CALL ANTHROPIC API DIRECTLY."
        )


def test_no_direct_anthropic_calls_in_root():
    """Test that root-level Python files have no direct Anthropic API calls."""
    repo_root = Path(__file__).parent.parent

    violations = []

    # Scan Python files in root directory
    for py_file in repo_root.glob("*.py"):
        file_violations = scan_file_for_anthropic_calls(py_file, repo_root)
        violations.extend(file_violations)

    if violations:
        violation_report = "\n".join(
            f"  - {v['file']}:{v['line']} - {v['type']}"
            for v in violations
        )
        pytest.fail(
            f"AI SOURCE LOCK VIOLATION: Found {len(violations)} direct Anthropic API call(s) in root:\n"
            f"{violation_report}\n\n"
            f"Use AI guard module:\n"
            f"  from trading_app.ai_guard import guarded_chat_answer"
        )


def test_ai_guard_is_sole_choke_point():
    """Test that ai_guard.py exists and has required functions."""
    repo_root = Path(__file__).parent.parent
    ai_guard_file = repo_root / "trading_app" / "ai_guard.py"

    assert ai_guard_file.exists(), "AI guard module (ai_guard.py) not found"

    # Check that it has the required functions
    with open(ai_guard_file, 'r') as f:
        content = f.read()

    required_functions = [
        "guarded_chat_answer",
        "validate_evidence_pack",
        "assert_ai_lock_enabled"
    ]

    missing_functions = []
    for func in required_functions:
        if f"def {func}" not in content:
            missing_functions.append(func)

    assert len(missing_functions) == 0, (
        f"ai_guard.py missing required functions: {', '.join(missing_functions)}"
    )


def test_locked_prompt_exists():
    """Test that LOCKED_SYSTEM_PROMPT.txt exists and is not empty."""
    repo_root = Path(__file__).parent.parent
    prompt_file = repo_root / "trading_app" / "prompts" / "LOCKED_SYSTEM_PROMPT.txt"

    assert prompt_file.exists(), "LOCKED_SYSTEM_PROMPT.txt not found"

    content = prompt_file.read_text(encoding='utf-8')
    assert len(content.strip()) > 100, "LOCKED_SYSTEM_PROMPT.txt is too short or empty"

    # Check for key enforcement phrases
    required_phrases = [
        "Evidence Pack",
        "ONLY use",
        "refuse",
        "NOT AVAILABLE"
    ]

    for phrase in required_phrases:
        assert phrase in content, f"LOCKED_SYSTEM_PROMPT.txt missing required phrase: '{phrase}'"


# ================================================================================
# RUNTIME BEHAVIOR TESTS (FAIL-CLOSED GATES)
# ================================================================================

def test_no_evidence_pack_is_rejected():
    """Test that calling with None evidence pack returns refusal (without calling model)."""

    # This should return a refusal message immediately (no API call)
    result = guarded_chat_answer(
        question="Should I take this trade?",
        evidence_pack=None,
        conversation_history=[]
    )

    # Check that it's a refusal
    assert "NOT AVAILABLE" in result
    assert "No Evidence Pack" in result
    assert "evidence_pack" in result


def test_missing_fields_rejected():
    """Test that evidence pack with missing required fields is rejected."""

    # Create incomplete evidence pack (missing engine_eval)
    incomplete_pack = EvidencePack(
        instrument="MGC",
        timeframe="1m",
        candle_tables_used=["bars_1m"],
        ts_utc_start=datetime(2026, 1, 1),
        ts_utc_end=datetime(2026, 1, 19),
        setup_rows_used=[],
        engine_eval=None,  # MISSING
        facts=["Test fact"],
        queries=[],
        db_mode="local",
        no_lookahead_check="PASS",
        strategy_ids=[]
    )

    result = guarded_chat_answer(
        question="What's the current status?",
        evidence_pack=incomplete_pack,
        conversation_history=[]
    )

    assert "NOT AVAILABLE" in result
    assert "MISSING" in result or "incomplete" in result.lower()


def test_wait_signal_rejects_trade_recommendation():
    """Test that WAIT signal rejects trade recommendation requests."""

    # Create evidence pack with WAIT status
    engine_eval = EngineEvaluation(
        status="WAIT",
        strategy_name="2300 ORB HALF",
        reasons=["ORB not formed yet", "Waiting for setup confirmation"]
    )

    evidence_pack = EvidencePack(
        instrument="MGC",
        timeframe="1m",
        candle_tables_used=["bars_1m", "validated_setups"],
        ts_utc_start=datetime(2026, 1, 19, 0, 0),
        ts_utc_end=datetime(2026, 1, 19, 10, 0),
        setup_rows_used=[
            SetupInfo(
                setup_id=1,
                strategy_name="2300 ORB HALF",
                orb_time="2300",
                rr_target=1.5,
                sl_mode="HALF",
                tier="A",
                win_rate=56.1,
                avg_r=0.403,
                trade_count=260,
                annual_trades=260
            )
        ],
        engine_eval=engine_eval,
        facts=["Instrument: MGC", "Strategy: 2300 ORB HALF", "Status: WAIT"],
        queries=["SELECT FROM validated_setups WHERE instrument='MGC'"],
        db_mode="local",
        no_lookahead_check="PASS",
        strategy_ids=[1]
    )

    result = guarded_chat_answer(
        question="Should I take this trade?",
        evidence_pack=evidence_pack,
        conversation_history=[]
    )

    # Should refuse trade with NO TRADE message
    assert "NO TRADE" in result or "WAIT" in result
    assert "NOT AVAILABLE" in result or "WAIT" in result


def test_no_candles_rejected():
    """Test that empty candle tables cause rejection."""

    # Create evidence pack with empty candle tables list
    engine_eval = EngineEvaluation(
        status="WAIT",
        strategy_name="None"
    )

    evidence_pack = EvidencePack(
        instrument="MGC",
        timeframe="1m",
        candle_tables_used=[],  # EMPTY
        ts_utc_start=datetime(2026, 1, 19),
        ts_utc_end=datetime(2026, 1, 19),
        setup_rows_used=[],
        engine_eval=engine_eval,
        facts=[],
        queries=[],
        db_mode="local",
        no_lookahead_check="PASS",
        strategy_ids=[]
    )

    result = guarded_chat_answer(
        question="What's the market doing?",
        evidence_pack=evidence_pack,
        conversation_history=[]
    )

    assert "NOT AVAILABLE" in result
    assert "candle_tables_used" in result


def test_enter_signal_with_prices_allows_response():
    """
    Test that ENTER signal with complete trade info allows AI response.

    NOTE: This test requires ANTHROPIC_API_KEY in environment to actually call the model.
    If key is missing, it should return an error message (not a refusal).
    """

    # Create complete evidence pack with ENTER signal
    setup = SetupInfo(
        setup_id=5,
        strategy_name="2300 ORB HALF",
        orb_time="2300",
        rr_target=1.5,
        sl_mode="HALF",
        tier="A",
        win_rate=56.1,
        avg_r=0.403,
        trade_count=260,
        annual_trades=260
    )

    engine_eval = EngineEvaluation(
        status="ENTER",
        strategy_name="2300 ORB HALF",
        direction="LONG",
        entry_price=2706.0,
        stop_price=2703.0,
        target_price=2710.5,
        orb_high=2706.0,
        orb_low=2700.0,
        setup_tier="A",
        rr=1.5,
        win_rate=56.1,
        avg_r=0.403,
        reasons=["ORB formed", "Breakout confirmed", "Filters passed"]
    )

    evidence_pack = EvidencePack(
        instrument="MGC",
        timeframe="1m",
        candle_tables_used=["bars_1m", "validated_setups"],
        ts_utc_start=datetime(2026, 1, 19, 0, 0),
        ts_utc_end=datetime(2026, 1, 19, 10, 0),
        setup_rows_used=[setup],
        engine_eval=engine_eval,
        facts=[
            "Instrument: MGC",
            "Current price: $2706.00",
            "Strategy: 2300 ORB HALF",
            "ORB: $2700.00 - $2706.00 (size: 6.00)"
        ],
        queries=["SELECT FROM validated_setups WHERE instrument='MGC'"],
        db_mode="local",
        no_lookahead_check="PASS",
        strategy_ids=[5],
        current_price=2706.0,
        orb_data={"2300 ORB": {"low": 2700.0, "high": 2706.0, "size": 6.0}}
    )

    result = guarded_chat_answer(
        question="Should I take this trade?",
        evidence_pack=evidence_pack,
        conversation_history=[]
    )

    # Should NOT be a refusal (either AI response or "API key not set" error)
    assert "NOT AVAILABLE" not in result
    # Should either have API response or API key error (both acceptable)
    assert len(result) > 50  # Got some meaningful response


def test_runtime_self_check():
    """Test that assert_ai_lock_enabled() verifies configuration."""

    # This should pass (or raise AssertionError if misconfigured)
    try:
        result = assert_ai_lock_enabled()
        assert result is True
    except AssertionError as e:
        pytest.fail(f"AI lock misconfigured: {e}")


# ================================================================================
# INTEGRATION TEST
# ================================================================================

def test_ai_assistant_uses_guarded_path():
    """Test that TradingAIAssistant uses guarded path (integration check)."""

    # Import TradingAIAssistant
    from ai_assistant import TradingAIAssistant

    # Check that it imports from ai_guard
    import ai_assistant
    import inspect

    source = inspect.getsource(ai_assistant)

    # Should import from ai_guard
    assert "from ai_guard import" in source or "import ai_guard" in source, \
        "TradingAIAssistant does not import from ai_guard"

    # Should call guarded_chat_answer
    assert "guarded_chat_answer" in source, \
        "TradingAIAssistant does not call guarded_chat_answer"

    # Should NOT call Anthropic client directly
    assert "self.client.messages.create" not in source, \
        "TradingAIAssistant still calls Anthropic client directly (bypass detected)"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
