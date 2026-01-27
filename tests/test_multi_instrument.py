"""Test multi-instrument support"""
import sys
import os

# Add trading_app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trading_app'))

from data_loader import LiveDataLoader

print("\n" + "="*60)
print("MULTI-INSTRUMENT SUPPORT TEST")
print("="*60 + "\n")

instruments = [
    ("MGC", "Micro Gold"),
    ("MNQ", "Micro Nasdaq"),
    ("MPL", "Micro Platinum")
]

results = {}

for symbol, name in instruments:
    print(f"Testing {symbol} ({name})...")
    try:
        loader = LiveDataLoader(symbol=symbol)

        # Test ATR loading
        atr = loader.get_today_atr()

        # Test latest bar (from cache, will be None but shouldn't crash)
        latest_bar = loader.get_latest_bar()

        print(f"  [OK] {symbol}: ATR={atr if atr else 'N/A'}, Latest bar={'Found' if latest_bar else 'N/A'}")
        results[symbol] = "PASS"
    except Exception as e:
        print(f"  [FAIL] {symbol}: {e}")
        results[symbol] = f"FAIL: {e}"
    print()

print("="*60)
print("RESULTS")
print("="*60 + "\n")

all_pass = all(r == "PASS" for r in results.values())

for symbol, result in results.items():
    status = "[OK]" if result == "PASS" else "[FAIL]"
    print(f"{status} {symbol}: {result}")

print()
if all_pass:
    print("SUCCESS: All instruments load correctly!")
else:
    print("FAILURE: Some instruments failed to load")
print("="*60)
