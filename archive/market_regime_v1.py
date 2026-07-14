import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

# Latest snapshot per symbol
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
print("MARKET REGIME ANALYSIS")
print("=" * 60)

for symbol in sorted(df["symbol"].unique()):

    temp = df[df["symbol"] == symbol]

    max_call_row = temp.loc[temp["call_oi"].idxmax()]
    max_put_row = temp.loc[temp["put_oi"].idxmax()]

    resistance = max_call_row["strike"]
    support = max_put_row["strike"]

    range_width = resistance - support

    total_call_oi = temp["call_oi"].sum()
    total_put_oi = temp["put_oi"].sum()

    pcr = (
        total_put_oi / total_call_oi
        if total_call_oi > 0
        else 0
    )

    # -------- REGIME LOGIC --------

    if range_width <= 1000 and 0.8 <= pcr <= 1.2:
        regime = "RANGEBOUND"

    elif pcr > 1.2:
        regime = "BULLISH"

    elif pcr < 0.8:
        regime = "BEARISH"

    else:
        regime = "NEUTRAL"

    print("\n" + "=" * 60)
    print(symbol)
    print("=" * 60)

    print(f"Spot Price   : {temp['spot_price'].iloc[0]:.2f}")
    print(f"PCR          : {pcr:.2f}")

    print(f"Support      : {int(support)}")
    print(f"Resistance   : {int(resistance)}")

    print(f"Range Width  : {int(range_width)}")

    print()
    print(f"REGIME       : {regime}")