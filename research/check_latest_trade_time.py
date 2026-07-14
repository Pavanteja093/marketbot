import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql("""
SELECT
    trade_time,
    symbol
FROM option_chain_history
WHERE DATE(trade_time) = DATE('now')
ORDER BY ROWID DESC
LIMIT 50
""", conn)

conn.close()

print(df)