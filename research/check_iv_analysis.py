import sqlite3
import pandas as pd

conn = sqlite3.connect(
    r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"
)

df = pd.read_sql("""
SELECT *
FROM iv_analysis
ORDER BY trade_time DESC
""", conn)

conn.close()

print(df)