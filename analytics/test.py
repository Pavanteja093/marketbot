import sqlite3
import pandas as pd

conn = sqlite3.connect(
    r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"
)

df = pd.read_sql(
    "SELECT * FROM signal_performance",
    conn
)

print(df.tail())

conn.close()