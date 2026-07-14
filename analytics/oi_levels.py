import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

query = """

SELECT *

FROM option_chain_history o

WHERE trade_time =
(
    SELECT MAX(trade_time)
    FROM option_chain_history
    WHERE symbol = o.symbol
)

"""

df = pd.read_sql(query, conn)

conn.close()

print("\n" + "=" * 60)
print("OI LEVEL ANALYSIS")
print("=" * 60)

for symbol in sorted(df["symbol"].unique()):

    temp = df[df["symbol"] == symbol]

    spot_price = temp["spot_price"].iloc[0]

    # Top 2 Put OI levels
    top_puts = temp.nlargest(
        2,
        "put_oi"
    )

    # Top 2 Call OI levels
    top_calls = temp.nlargest(
        2,
        "call_oi"
    )

    print("\n" + "=" * 60)
    print(symbol)
    print("=" * 60)

    print(f"Spot Price : {spot_price:.2f}")

    print("\nSUPPORT LEVELS\n")

    for i, (_, row) in enumerate(
        top_puts.iterrows(),
        start=1
    ):

        print(
            f"S{i} : {int(row['strike'])}"
        )

        print(
            f"OI : {int(row['put_oi']):,}"
        )

        print()

    print("RESISTANCE LEVELS\n")

    for i, (_, row) in enumerate(
        top_calls.iterrows(),
        start=1
    ):

        print(
            f"R{i} : {int(row['strike'])}"
        )

        print(
            f"OI : {int(row['call_oi']):,}"
        )

        print()