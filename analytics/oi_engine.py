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

print("\n" + "="*60)
print("OI ANALYSIS")
print("="*60)

for symbol in sorted(df["symbol"].unique()):

    temp = df[df["symbol"] == symbol]

    max_call_row = temp.loc[temp["call_oi"].idxmax()]
    max_put_row = temp.loc[temp["put_oi"].idxmax()]

    resistance = max_call_row["strike"]
    support = max_put_row["strike"]

    range_width = resistance - support

    print("\n" + "="*60)
    print(symbol)
    print("="*60)

    print(f"Spot Price        : {max_call_row['spot_price']:.2f}")

    print()
    print("RESISTANCE")

    print(f"Strike            : {int(resistance)}")
    print(f"Call OI           : {max_call_row['call_oi']:,.0f}")

    print()

    print("SUPPORT")
    print(f"Strike            : {int(support)}")
    print(f"Put OI            : {max_put_row['put_oi']:,.0f}")
          
    print()
    print(f"Range_width       : {int(range_width)}")