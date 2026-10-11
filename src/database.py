import duckdb
from fastapi import Request
from src.core.config import BASE_DIR

tables = ["deals", "events", "accounts"]

def initialize(con: duckdb.DuckDBPyConnection):
    # Only loads a table from its CSV if it isn't there yet
    # (src/clean_data.py replaces them with cleaned versions)
    for name in tables:
        csv_path = (BASE_DIR / 'data' / f'{name}.csv').as_posix()
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {name} AS
            SELECT * FROM read_csv_auto('{csv_path}')
        """)

def get_db(request: Request):
    cur = request.app.state.db.cursor()
    try:
        yield cur
    finally:
        cur.close()
