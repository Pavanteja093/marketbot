from pathlib import Path
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(str(DB_PATH))

df = pd.read_sql(
    """
    SELECT DISTINCT trade_date
    FROM stocks_daily
    ORDER BY trade_date
    """,
    conn
)

conn.close()

print(df)
