import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql("""

SELECT

    symbol,

    COUNT(*) AS rows,

    COUNT(DISTINCT trade_time) AS snapshots,

    MIN(trade_time) AS first_snapshot,

    MAX(trade_time) AS last_snapshot

FROM option_chain_history

GROUP BY symbol

""", conn)

print(df)

conn.close()