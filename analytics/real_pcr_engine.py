import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

query = """

SELECT
    symbol,

    SUM(call_oi) AS total_call_oi,
    SUM(put_oi)  AS total_put_oi,

    MAX(spot_price) AS spot_price

FROM option_chain_history

GROUP BY symbol

"""

df = pd.read_sql(query, conn)

conn.close()

print("\n" + "=" * 60)
print("REAL PCR ANALYSIS")
print("=" * 60)

for _, row in df.iterrows():

    symbol = row["symbol"]

    call_oi = row["total_call_oi"]
    put_oi = row["total_put_oi"]

    pcr = put_oi / call_oi if call_oi else 0

    if pcr > 1.2:
        bias = "BULLISH"

    elif pcr < 0.8:
        bias = "BEARISH"

    else:
        bias = "NEUTRAL"

    print(f"\n{symbol}")
    print("-" * 40)

    print(f"Spot Price   : {row['spot_price']:.2f}")
    print(f"Call OI      : {call_oi:,.0f}")
    print(f"Put OI       : {put_oi:,.0f}")
    print(f"PCR          : {pcr:.2f}")
    print(f"Market Bias  : {bias}")