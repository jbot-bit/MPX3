import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "trading_app"))

from cloud_mode import get_database_connection
from config import MGC_ORB_CONFIGS

# Get database connection (same as test)
conn = get_database_connection(read_only=True)

# Read MGC setups from database (same query as test)
query = """
SELECT instrument, orb_time, rr, sl_mode, orb_size_filter
FROM validated_setups
WHERE instrument = 'MGC'
  AND orb_time NOT IN ('CASCADE', 'SINGLE_LIQ')
ORDER BY orb_time
"""

db_setups = conn.execute(query).fetchall()
conn.close()

print("Database MGC setups:")
for setup in db_setups:
    instrument, orb_time, rr, sl_mode, orb_filter = setup
    print(f'  {orb_time}: RR={rr}, SL={sl_mode}, Filter={orb_filter}')

print("\nConfig MGC 1000 setups:")
if '1000' in MGC_ORB_CONFIGS:
    config_1000 = MGC_ORB_CONFIGS['1000']
    print(f'  Type: {type(config_1000)}')
    print(f'  Value: {config_1000}')
else:
    print('  NOT FOUND in config')

print("\nAll config ORB times:")
for orb_time in sorted(MGC_ORB_CONFIGS.keys()):
    print(f'  {orb_time}: {MGC_ORB_CONFIGS[orb_time]}')
