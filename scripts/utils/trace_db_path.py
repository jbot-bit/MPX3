import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "trading_app"))

# Show current directory and environment
print("Current directory:", os.getcwd())
print("Script location:", Path(__file__).resolve())

# Import cloud_mode and check what path it computes
import cloud_mode

# Manually compute the path like cloud_mode does
app_dir = Path(cloud_mode.__file__).parent
db_path = app_dir.parent / "data" / "db" / "gold.db"

print("\ncloud_mode.__file__:", Path(cloud_mode.__file__).resolve())
print("app_dir:", app_dir.resolve())
print("Computed db_path:", db_path.resolve())
print("DB exists?", db_path.exists())
print("DB size:", db_path.stat().st_size if db_path.exists() else "N/A")

# Now get connection and check it
conn = cloud_mode.get_database_connection(read_only=True)
print("\nConnection obtained")

# Try to get the connection path (if possible)
try:
    # DuckDB doesn't have a direct way to get the file path, but we can check the data
    result = conn.execute("SELECT COUNT(*) FROM validated_setups WHERE instrument='MGC' AND orb_time='1000'").fetchone()
    print(f"Number of MGC 1000 setups in connected DB: {result[0]}")

    result = conn.execute("SELECT rr, sl_mode FROM validated_setups WHERE instrument='MGC' AND orb_time='1000' ORDER BY rr").fetchall()
    print(f"MGC 1000 setups: {result}")
except Exception as e:
    print(f"Error querying: {e}")

conn.close()
