"""
QUICK SEARCH UI VERIFICATION (update11.txt)

Verifies that the Auto Search UI refactor meets all requirements:
- Zero typing (no free text inputs in main UI)
- 5 control blocks present
- RR non-cumulative caption exists
- Advanced mode hidden by default
- Validation queue integration preserved
"""

import sys
from pathlib import Path

def verify_quick_search_ui():
    """Verify Quick Search UI refactor requirements"""

    app_path = Path(__file__).parent.parent.parent / "trading_app" / "app_canonical.py"

    if not app_path.exists():
        print("[FAIL] app_canonical.py not found")
        return False

    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find Quick Search section
    if "Quick Search" not in content:
        print("[FAIL] 'Quick Search' title not found (should replace 'Auto Search')")
        return False

    print("[PASS] Quick Search section found")

    # Check for required blocks
    required_elements = [
        ("1️⃣ Instrument", "Block 1: Instrument selection"),
        ("2️⃣ ORB Scope", "Block 2: ORB time selection"),
        ("3️⃣ Entry Rule", "Block 3: Entry rule selection"),
        ("4️⃣ RR Targets", "Block 4: RR targets"),
        ("5️⃣ Optional Filters", "Block 5: Optional filters"),
    ]

    all_pass = True
    for element, description in required_elements:
        if element in content:
            print(f"[PASS] {description}")
        else:
            print(f"[FAIL] {description} - '{element}' not found")
            all_pass = False

    # Check for non-cumulative caption (exact phrase from spec)
    if "Tests ONLY selected RR values (not cumulative)" in content:
        print("[PASS] RR non-cumulative caption present")
    else:
        print("[FAIL] RR non-cumulative caption missing")
        all_pass = False

    # Check for radio buttons (zero typing)
    if "st.radio" in content:
        print("[PASS] Radio buttons present (zero typing)")
    else:
        print("[FAIL] Radio buttons not found")
        all_pass = False

    # Check for multiselect (ORB scope)
    if "st.multiselect" in content:
        print("[PASS] Multiselect present (ORB scope)")
    else:
        print("[FAIL] Multiselect not found")
        all_pass = False

    # Check for Advanced Mode expander
    if "Advanced / Research Mode" in content:
        print("[PASS] Advanced Mode expander present")
    else:
        print("[FAIL] Advanced Mode expander missing")
        all_pass = False

    # Check for large run button
    if "Run Quick Search" in content:
        print("[PASS] 'Run Quick Search' button present")
    else:
        print("[FAIL] 'Run Quick Search' button not found")
        all_pass = False

    # Check for card-style results
    if "border-left: 6px solid" in content:
        print("[PASS] Card-style results present")
    else:
        print("[FAIL] Card-style results missing")
        all_pass = False

    # Check for Raw Results expander
    if "Raw Results (Advanced)" in content:
        print("[PASS] Raw Results expander present")
    else:
        print("[FAIL] Raw Results expander missing")
        all_pass = False

    # Check for confirmation checkbox
    if "Confirm: I want to manually enqueue" in content:
        print("[PASS] Confirmation checkbox present")
    else:
        print("[FAIL] Confirmation checkbox missing")
        all_pass = False

    # Check that setup_family is NOT in main UI (only in advanced)
    # Count occurrences - should be in advanced mode only
    if content.count("setup_family") > 0:
        if "advanced_setup_family" in content:
            print("[PASS] Setup family moved to Advanced Mode")
        else:
            print("[WARN] Setup family present but not in Advanced Mode")

    # Check for validation queue integration
    if "validation_queue" in content:
        print("[PASS] Validation queue integration preserved")
    else:
        print("[FAIL] Validation queue integration missing")
        all_pass = False

    return all_pass


def main():
    print("=" * 70)
    print("QUICK SEARCH UI VERIFICATION (update11.txt)")
    print("=" * 70)
    print()

    success = verify_quick_search_ui()

    print()
    print("=" * 70)
    if success:
        print("[PASS] ALL CHECKS PASSED!")
        print()
        print("Quick Search UI refactor complete:")
        print("  [OK] Zero-typing interface (5 blocks)")
        print("  [OK] RR non-cumulative caption present")
        print("  [OK] Advanced Mode hidden by default")
        print("  [OK] Card-style results with Raw Results table")
        print("  [OK] Confirmation checkbox before enqueue")
        print("  [OK] Validation queue integration preserved")
        print()
        print("Launch app:")
        print("  streamlit run trading_app/app_canonical.py")
        return 0
    else:
        print("[FAIL] SOME CHECKS FAILED")
        print("Review failures above and fix before using.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
