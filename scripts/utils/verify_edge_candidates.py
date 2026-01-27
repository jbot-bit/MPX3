from trading_app.cloud_mode import get_database_connection

con = get_database_connection(read_only=True)
row = con.execute("SELECT candidate_id, code_version, data_version, test_config_json, status FROM edge_candidates WHERE candidate_id=1").fetchone()
print(row)
con.close()
