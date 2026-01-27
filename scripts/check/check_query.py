import duckdb

conn = duckdb.connect('data/db/gold.db', read_only=True)

# Exact same query as test_app_sync.py
query = """
SELECT instrument, orb_time, rr, sl_mode, orb_size_filter
FROM validated_setups
WHERE instrument = 'MGC'
  AND orb_time NOT IN ('CASCADE', 'SINGLE_LIQ')
ORDER BY orb_time
"""

result = conn.execute(query).fetchall()

print('Query result (what test_app_sync.py sees):')
for i, r in enumerate(result):
    print(f'{i+1}. {r}')

conn.close()
