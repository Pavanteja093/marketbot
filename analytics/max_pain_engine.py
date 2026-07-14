from pathlib import Path
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

query = """
SELECT
    symbol,
    strike,
    call_oi,
    put_oi,
    spot_price
FROM option_chain_history
"""

df = pd.read_sql(query, conn)

print("\n" + "="*60)
print("MAX PAIN ANALYSIS")
print("="*60)

for symbol in sorted(df["symbol"].unique()):

    data = df[df["symbol"] == symbol].copy()

    spot = data["spot_price"].iloc[0]

    pain_values = []

    for strike in data["strike"].unique():

        total_pain = 0

        for _, row in data.iterrows():

            call_loss = max(
                0,
                strike - row["strike"]
            ) * row["call_oi"]

            put_loss = max(
                0,
                row["strike"] - strike
            ) * row["put_oi"]

            total_pain += call_loss + put_loss

        pain_values.append(
            (strike, total_pain)
        )

    max_pain = min(
        pain_values,
        key=lambda x: x[1]
    )[0]

    print("\n" + "="*60)
    print(symbol)
    print("="*60)

    print(f"Spot Price : {spot:.2f}")
    print(f"Max Pain   : {int(max_pain)}")

conn.close()