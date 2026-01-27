import duckdb

databases = ['gold.db', 'data/gold.db', 'data/db/gold.db']

for db_path in databases:
    try:
        conn = duckdb.connect(db_path, read_only=True)
        count = conn.execute('SELECT COUNT(*) FROM validated_setups').fetchone()[0]
        print(f'\n{db_path}:')
        print(f'  Total setups: {count}')

        if count > 0:
            print('  MGC 1000 setups:')
            for row in conn.execute('SELECT id, orb_time, rr, sl_mode FROM validated_setups WHERE instrument=? AND orb_time=?', ['MGC', '1000']).fetchall():
                print(f'    ID={row[0]}, RR={row[2]}, SL={row[3]}')

        conn.close()
    except Exception as e:
        print(f'\n{db_path}: Error - {e}')
