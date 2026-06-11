from pathlib import Path
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

print("Database being opened:")
print(DB_PATH)

conn = sqlite3.connect(str(DB_PATH))

df = pd.read_sql(
    """
    SELECT
        trade_date,
        COUNT(*) AS signals
    FROM signal_history
    GROUP BY trade_date
    ORDER BY trade_date
    """,
    conn
)

conn.close()

print("\nSignal History:")
print(df)