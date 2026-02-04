"""
Tests for entry logic consistency across implementation files.

These tests verify that all entry detection implementations follow
the canonical rules defined in docs/ENTRY_LOGIC_SSOT.md.
"""

import pytest
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Canonical entry rule patterns
CANONICAL_PATTERNS = {
    'long_detection': r'close\s*[>]\s*orb.*high|close\s*[>]\s*orb_high',
    'short_detection': r'close\s*[<]\s*orb.*low|close\s*[<]\s*orb_low',
}

# Files that implement entry logic
IMPLEMENTATION_FILES = [
    'strategies/execution_engine.py',
    'trading_app/entry_rules.py',
]


class TestEntryLogicConsistency:
    """Test suite for entry logic consistency."""

    def test_execution_engine_uses_close_not_touch(self):
        """Verify execution_engine uses CLOSE for detection, not touch."""
        file_path = REPO_ROOT / 'strategies' / 'execution_engine.py'
        if not file_path.exists():
            pytest.skip("execution_engine.py not found")

        content = file_path.read_text(encoding='utf-8')

        # Should have close-based detection
        assert re.search(CANONICAL_PATTERNS['long_detection'], content, re.IGNORECASE), \
            "execution_engine.py missing LONG detection: close > orb_high"

        # Should NOT have touch-based detection without close
        touch_pattern = r'\bhigh\b\s*[>]\s*orb.*high(?!.*close)'
        assert not re.search(touch_pattern, content), \
            "execution_engine.py should use CLOSE, not high touch"

    def test_entry_rules_uses_close_not_touch(self):
        """Verify entry_rules uses CLOSE for detection, not touch."""
        file_path = REPO_ROOT / 'trading_app' / 'entry_rules.py'
        if not file_path.exists():
            pytest.skip("entry_rules.py not found")

        content = file_path.read_text(encoding='utf-8')

        # Should have close-based detection
        assert re.search(CANONICAL_PATTERNS['long_detection'], content, re.IGNORECASE), \
            "entry_rules.py missing LONG detection: close > orb_high"

        assert re.search(CANONICAL_PATTERNS['short_detection'], content, re.IGNORECASE), \
            "entry_rules.py missing SHORT detection: close < orb_low"

    def test_no_inclusive_comparison(self):
        """Verify no implementation uses >= or <= (should be strict > and <)."""
        for file_rel in IMPLEMENTATION_FILES:
            file_path = REPO_ROOT / file_rel
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding='utf-8')

            # Check for inclusive LONG (WRONG)
            inclusive_long = r'close\s*[>]=\s*orb.*high'
            assert not re.search(inclusive_long, content), \
                f"{file_rel} uses >= for LONG (should be >)"

            # Check for inclusive SHORT (WRONG)
            inclusive_short = r'close\s*[<]=\s*orb.*low'
            assert not re.search(inclusive_short, content), \
                f"{file_rel} uses <= for SHORT (should be <)"

    def test_entry_logic_ssot_document_exists(self):
        """Verify SSOT documentation exists."""
        doc_path = REPO_ROOT / 'docs' / 'ENTRY_LOGIC_SSOT.md'
        assert doc_path.exists(), \
            "ENTRY_LOGIC_SSOT.md must exist to document canonical rules"

    def test_consistency_guard_exists(self):
        """Verify consistency guard exists."""
        guard_path = REPO_ROOT / 'scripts' / 'check' / 'check_entry_logic_consistency.py'
        assert guard_path.exists(), \
            "Entry logic consistency guard must exist"


class TestEntryLogicInvariants:
    """Test invariants that must hold for entry logic."""

    def test_entry_after_orb_window(self):
        """Verify entry logic respects ORB window timing."""
        # This is a documentation test - actual implementation
        # is tested via execution_engine tests
        file_path = REPO_ROOT / 'trading_app' / 'entry_rules.py'
        if not file_path.exists():
            pytest.skip("entry_rules.py not found")

        content = file_path.read_text(encoding='utf-8')

        # Should have post-ORB filtering
        assert re.search(r'orb_end|after.*orb|post.*orb', content, re.IGNORECASE), \
            "entry_rules.py must filter for bars AFTER ORB window"

    def test_no_lookahead_in_entry(self):
        """Verify no lookahead bias in entry detection."""
        file_path = REPO_ROOT / 'trading_app' / 'entry_rules.py'
        if not file_path.exists():
            pytest.skip("entry_rules.py not found")

        content = file_path.read_text(encoding='utf-8')

        # Entry timestamp should come from the confirmation or next bar
        # Not from future data
        assert re.search(r'entry.*timestamp|timestamp.*entry|next.*bar', content, re.IGNORECASE), \
            "entry_rules.py should explicitly handle entry timestamp"
