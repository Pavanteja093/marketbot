import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"


    
def calculate_pcr(df):
    """
    Calculate aggregate Put/Call OI ratio for one option-chain snapshot.

    Contract
    --------
    Returns:
        float
            Total put OI / total call OI.

    Raises:
        ValueError
            If required OI columns are missing or call OI is zero.
    """

    required = {"call_oi", "put_oi"}

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"PCR calculation missing required columns: {sorted(missing)}"
        )

    call_oi = df["call_oi"].fillna(0).sum()
    put_oi = df["put_oi"].fillna(0).sum()

    if call_oi <= 0:
        raise ValueError("PCR calculation requires positive total call OI")

    return float(put_oi / call_oi)


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