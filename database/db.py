from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"


def get_connection():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn

def execute(query, params=None):

    conn = get_connection()

    cur = conn.cursor()

    if params:
        cur.execute(query, params)
    else:
        cur.execute(query)

    conn.commit()

    conn.close()


def fetch_dataframe(query):

    import pandas as pd

    conn = get_connection()

    df = pd.read_sql(query, conn)

    conn.close()

    return df