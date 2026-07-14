import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

query = """

SELECT

    symbol,

    ROUND(AVG(pcr), 2) as avg_pcr

FROM option_chain_history

GROUP BY symbol

"""

df = pd.read_sql(query, conn)

conn.close()

print("\n" + "="*60)
print("PCR ANALYSIS")
print("="*60)

for _, row in df.iterrows():

    symbol = row["symbol"]
    pcr = row["avg_pcr"]

    if pcr > 1.2:
        sentiment = "BULLISH"

    elif pcr < 0.8:
        sentiment = "BEARISH"

    else:
        sentiment = "NEUTRAL"

    print(f"\n{symbol}")
    print(f"PCR       : {pcr}")
    print(f"Sentiment : {sentiment}")