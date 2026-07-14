import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql("""
SELECT trade_time
FROM option_chain_history
""", conn)

conn.close()

df["trade_time"] = pd.to_datetime(df["trade_time"], format="mixed")

df["hour"] = df["trade_time"].dt.hour

print(df["hour"].value_counts().sort_index())\