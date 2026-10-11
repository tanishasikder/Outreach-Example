from fastapi import Request

tables = ["deals", "events", "accounts"]

def initialize(request: Request):
    for name in tables:
        request.app.state.db.execute("""
            CREATE TABLE IF NOT EXISTS {name} AS
            SELECT * FROM read_csv_auto('data/{name}.csv')
        """)

def get_db(request: Request):
    cur = request.app.state.db.cursor()
    try:
        yield cur
    finally:
        cur.close()