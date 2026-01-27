import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "trading_app"))

from cloud_mode import get_database_connection
import duckdb

# Test 1: Direct connection
print("TEST 1: Direct connection to data/db/gold.db")
conn1 = duckdb.connect('data/db/gold.db', read_only=True)
result1 = conn1.execute("SELECT orb_time, rr, sl_mode FROM validated_setups WHERE instrument='MGC' AND orb_time='1000' ORDER BY rr").fetchall()
print("  Results:", result1)
conn1.close()

# Test 2: cloud_mode connection
print("\nTEST 2: Using get_database_connection()")
conn2 = get_database_connection(read_only=True)
result2 = conn2.execute("SELECT orb_time, rr, sl_mode FROM validated_setups WHERE instrument='MGC' AND orb_time='1000' ORDER BY rr").fetchall()
print("  Results:", result2)
conn2.close()

print("\nMATCH:", result1 == result2)
