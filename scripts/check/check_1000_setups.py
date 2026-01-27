import duckdb

conn = duckdb.connect('data/db/gold.db', read_only=True)
print('MGC 1000 setups in database:')
for row in conn.execute('SELECT id, orb_time, rr, sl_mode FROM validated_setups WHERE instrument=? AND orb_time=? ORDER BY id', ['MGC', '1000']).fetchall():
    print(f'  ID={row[0]}, ORB={row[1]}, RR={row[2]}, SL={row[3]}')

print('\nAll MGC setups:')
for row in conn.execute('SELECT id, orb_time, rr, sl_mode FROM validated_setups WHERE instrument=? ORDER BY orb_time, id', ['MGC']).fetchall():
    print(f'  ID={row[0]}, ORB={row[1]}, RR={row[2]}, SL={row[3]}')
conn.close()
