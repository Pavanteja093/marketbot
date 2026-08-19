import sqlite3
import pandas as pd
from pathlib import Path
from analytics.pcr_engine import calculate_pcr
from analytics.oi_engine import calculate_oi_levels

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
print("SIGNAL ENGINE")
print("=" * 60)

for symbol in sorted(df["symbol"].unique()):

    temp = df[df["symbol"] == symbol]

    spot = temp["spot_price"].iloc[0]

    pcr = calculate_pcr(temp)

    oi_levels = calculate_oi_levels(temp)

    support = oi_levels["support"]

    resistance = oi_levels["resistance"]

    range_width = oi_levels["range_width"]

    # --------------------------------------------------
    # Max Pain
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Regime
    # --------------------------------------------------

    if range_width <= 500:
        regime = "RANGEBOUND"

    elif range_width <= 2000:
        regime = "NEUTRAL"

    else:
        regime = "VOLATILE"

    # --------------------------------------------------
    # Strategy Logic
    # --------------------------------------------------

    confidence = "MEDIUM"

    strategy = "WAIT"

    if (
        regime == "RANGEBOUND"
        and 0.9 <= pcr <= 1.2
    ):

        strategy = "IRON CONDOR"
        confidence = "HIGH"

    elif (
        pcr > 1.2
        and spot > max_pain
    ):

        strategy = "BULL PUT SPREAD"
        confidence = "HIGH"

    elif (
        pcr < 0.8
        and spot < max_pain
    ):

        strategy = "BEAR CALL SPREAD"
        confidence = "HIGH"

    elif regime == "VOLATILE":

        strategy = "SHORT STRANGLE"
        confidence = "LOW"

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print(symbol)
    print("=" * 60)

    print(f"Spot Price      : {spot:.2f}")
    print(f"PCR             : {pcr:.2f}")

    print(f"Support         : {int(support)}")
    print(f"Resistance      : {int(resistance)}")

    print(f"Max Pain        : {int(max_pain)}")

    print(f"Regime          : {regime}")

    print("\nMARKET VIEW")

    print(
        f"Expected Range  : "
        f"{int(support)} - {int(resistance)}"
    )

    print(
        f"Confidence      : {confidence}"
    )

    print(
        f"Strategy        : {strategy}"
    )