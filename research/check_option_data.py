import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

print("DATABASE FILE:")
print(DB_PATH)

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
""")

print("\nTABLES FOUND:")
print(cursor.fetchall())


df = pd.read_sql(
    "SELECT * FROM option_chain_history LIMIT 10",
    conn
)

print(df)

conn.close()