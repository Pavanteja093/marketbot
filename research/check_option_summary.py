import sqlite3
import pandas as pd

conn = sqlite3.connect("market_intelligence.db")

df = pd.read_sql("""

SELECT

    symbol,

    COUNT(*) as rows_count,

    MAX(trade_time) as latest_time,

    ROUND(MAX(spot_price),2) as spot

FROM option_chain_history

GROUP BY symbol

ORDER BY symbol

""", conn)

print(df)

conn.close()