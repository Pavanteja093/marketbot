import sqlite3
import pandas as pd

conn = sqlite3.connect("market_intelligence.db")

df = pd.read_sql("""

SELECT
    trade_date,
    rank,
    symbol,
    sector,
    score

FROM signal_history

ORDER BY trade_date DESC, rank

""", conn)

conn.close()

print(df)