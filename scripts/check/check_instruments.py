"""Quick check of instruments in validated_setups"""
import duckdb
from pipeline.paths import GOLD_DB_PATH

conn = duckdb.connect(GOLD_DB_PATH)

result = conn.execute('SELECT instrument, COUNT(*) as count FROM validated_setups GROUP BY instrument ORDER BY instrument').fetchall()

print('Current validated_setups by instrument:')
for row in result:
    print(f'  {row[0]}: {row[1]} setups')

total = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]
print(f'\nTotal: {total} setups')

conn.close()
