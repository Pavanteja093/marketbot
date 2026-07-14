import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

# --------------------------------------------------
# LOAD LATEST OPTION CHAIN DATA
# --------------------------------------------------

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
print("MARKET INTELLIGENCE")
print("=" * 60)

for symbol in sorted(df["symbol"].unique()):

    temp = df[df["symbol"] == symbol]

    spot = temp["spot_price"].iloc[0]

    # -----------------------------
    # PCR
    # -----------------------------

    total_call_oi = temp["call_oi"].sum()
    total_put_oi = temp["put_oi"].sum()

    pcr = (
        total_put_oi / total_call_oi
        if total_call_oi
        else 0
    )

    if pcr > 1.2:
        bias = "BULLISH"

    elif pcr < 0.8:
        bias = "BEARISH"

    else:
        bias = "NEUTRAL"

    # -----------------------------
    # OI Levels
    # -----------------------------

    support = temp.loc[
        temp["put_oi"].idxmax(),
        "strike"
    ]

    resistance = temp.loc[
        temp["call_oi"].idxmax(),
        "strike"
    ]

    range_width = int(
        resistance - support
    )

    # -----------------------------
    # Max Pain
    # -----------------------------

    pain_values = []

    for strike in temp["strike"].unique():

        total_pain = 0

        for _, row in temp.iterrows():

            call_loss = max(
                0,
                strike - row["strike"]
            ) * row["call_oi"]

            put_loss = max(
                0,
                row["strike"] - strike
            ) * row["put_oi"]

            total_pain += (
                call_loss + put_loss
            )

        pain_values.append(
            (strike, total_pain)
        )

    max_pain = min(
        pain_values,
        key=lambda x: x[1]
    )[0]

    # -----------------------------
    # INTERPRETATION
    # -----------------------------

    if range_width <= 500:
        regime = "RANGEBOUND"

    elif range_width <= 2000:
        regime = "NEUTRAL"

    else:
        regime = "VOLATILE"

    print("\n" + "=" * 60)
    print(symbol)
    print("=" * 60)

    print(f"Spot Price     : {spot:.2f}")

    print(f"\nPCR            : {pcr:.2f}")
    print(f"Bias           : {bias}")

    print(f"\nSupport        : {int(support)}")
    print(f"Resistance     : {int(resistance)}")

    print(f"Range Width    : {range_width}")

    print(f"\nMax Pain       : {int(max_pain)}")

    print(f"\nRegime         : {regime}")