import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "trading_app"))

from cloud_mode import get_database_connection

conn = get_database_connection(read_only=True)

# Get table schema
schema = conn.execute("DESCRIBE validated_setups").fetchall()

print("validated_setups schema:")
for col in schema:
    print(f"  {col[0]}: {col[1]}")

conn.close()
