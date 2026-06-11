import sqlite3
import pandas as pd

conn = sqlite3.connect("market_intelligence.db")

df = pd.read_sql("""
SELECT DISTINCT trade_date
FROM stocks_daily
ORDER BY trade_date DESC
""", conn)

conn.close()

print(df)