import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

# ============================================================
# FIND LATEST AND PREVIOUS SNAPSHOTS
# ============================================================

query = """

WITH snapshot_times AS (

    SELECT
        symbol,
        trade_time,

        ROW_NUMBER() OVER (
            PARTITION BY symbol
            ORDER BY trade_time DESC
        ) AS rn

    FROM (

        SELECT DISTINCT
            symbol,
            trade_time

        FROM option_chain_history

    )

)

SELECT
    symbol,
    MAX(CASE WHEN rn = 1 THEN trade_time END) AS latest_time,
    MAX(CASE WHEN rn = 2 THEN trade_time END) AS previous_time

FROM snapshot_times

GROUP BY symbol

"""

times_df = pd.read_sql(query, conn)

print("\n" + "=" * 60)
print("MAX PAIN SHIFT ANALYSIS")
print("=" * 60)

# ============================================================
# MAX PAIN FUNCTION
# ============================================================

def calculate_max_pain(df):

    strikes = sorted(df["strike"].unique())

    min_loss = float("inf")
    max_pain = None

    for settlement_price in strikes:

        total_loss = 0

        for _, row in df.iterrows():

            strike = row["strike"]

            call_oi = row["call_oi"]
            put_oi = row["put_oi"]

            call_loss = max(
                settlement_price - strike,
                0
            ) * call_oi

            put_loss = max(
                strike - settlement_price,
                0
            ) * put_oi

            total_loss += (
                call_loss +
                put_loss
            )

        if total_loss < min_loss:

            min_loss = total_loss
            max_pain = settlement_price

    return max_pain

# ============================================================
# ANALYSIS
# ============================================================

for _, row in times_df.iterrows():

    symbol = row["symbol"]

    latest_time = row["latest_time"]
    previous_time = row["previous_time"]

    latest_df = pd.read_sql(f"""

        SELECT
            strike,
            call_oi,
            put_oi

        FROM option_chain_history

        WHERE symbol='{symbol}'
        AND trade_time='{latest_time}'

    """, conn)

    previous_df = pd.read_sql(f"""

        SELECT
            strike,
            call_oi,
            put_oi

        FROM option_chain_history

        WHERE symbol='{symbol}'
        AND trade_time='{previous_time}'

    """, conn)

    latest_mp = calculate_max_pain(latest_df)
    previous_mp = calculate_max_pain(previous_df)

    shift = latest_mp - previous_mp

    if shift > 0:

        interpretation = "BULLISH"

    elif shift < 0:

        interpretation = "BEARISH"

    else:

        interpretation = "NEUTRAL"

    print("\n" + "=" * 60)
    print(symbol)
    print("=" * 60)

    print(f"\nPrevious Max Pain : {int(previous_mp)}")
    print(f"Current Max Pain  : {int(latest_mp)}")
    print(f"Shift             : {int(shift)}")

    print()
    print(f"Interpretation    : {interpretation}")

conn.close()