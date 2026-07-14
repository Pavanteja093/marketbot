import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

query = """

SELECT
    symbol,
    SUM(put_oi)  AS total_put_oi,
    SUM(call_oi) AS total_call_oi

FROM option_chain_history

WHERE trade_time = (

    SELECT MAX(trade_time)

    FROM option_chain_history o2

    WHERE o2.symbol = option_chain_history.symbol

)

GROUP BY symbol

"""

df = pd.read_sql(query, conn)

print("\nREAL PCR ANALYSIS")
print("=" * 60)

for _, row in df.iterrows():

    symbol = row["symbol"]

    total_put_oi = row["total_put_oi"]
    total_call_oi = row["total_call_oi"]

    real_pcr = round(total_put_oi / total_call_oi, 2)

    print(f"\n{symbol}")
    print(f"Put OI  : {total_put_oi:,.0f}")
    print(f"Call OI : {total_call_oi:,.0f}")
    print(f"Real PCR: {real_pcr}")

conn.close()