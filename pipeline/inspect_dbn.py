# inspect_dbn.py
import databento as db
from pathlib import Path

p = Path("dbn/glbx-mdp3-20251201-20251219.ohlcv-1m.dbn.zst")  # change if needed

store = db.DBNStore.from_file(p)

print("FILE:", p.name)
print("SCHEMA:", store.schema)          # e.g., ohlcv-1m
print("DATASET:", store.dataset)        # e.g., GLBX.MDP3
# print("RECORD_COUNT:", store.count)  # count not available in this version

# Show first few symbols present
symbols = set()
i = 0
for rec in store:
    symbols.add(getattr(rec, "symbol", None))
    i += 1
    if i >= 2000:
        break
print("SYMBOLS(sample):", sorted([s for s in symbols if s])[:30])

# Show first record fields + timestamps
store2 = db.DBNStore.from_file(p)  # re-open iterator
first = next(iter(store2))
print("FIRST_RECORD_TYPE:", type(first))
print("FIRST_SYMBOL:", getattr(first, "symbol", None))
print("TS_EVENT:", getattr(first, "ts_event", None))
print("OPEN/HIGH/LOW/CLOSE/VOL:", first.open, first.high, first.low, first.close, getattr(first, "volume", None))
