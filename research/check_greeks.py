import sqlite3
import pandas as pd

conn = sqlite3.connect(
    r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"
)

df = pd.read_sql("""

SELECT

symbol,
strike,

call_iv,
put_iv,

call_delta,
put_delta,

call_gamma,
put_gamma,

call_theta,
put_theta,

call_vega,
put_vega

FROM option_chain_history

ORDER BY id DESC

LIMIT 10

""", conn)

print(df)

conn.close()