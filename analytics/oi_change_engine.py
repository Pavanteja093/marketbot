import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\pavan\Documents\Python\Marketbot\market_intelligence.db"

conn = sqlite3.connect(DB_PATH)

# ============================================================
# GET LATEST & PREVIOUS SNAPSHOTS
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
print("OI CHANGE ANALYSIS")
print("=" * 60)

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

    merged = latest_df.merge(
        previous_df,
        on="strike",
        suffixes=("_latest", "_prev")
    )

    merged["call_change"] = (
        merged["call_oi_latest"]
        - merged["call_oi_prev"]
    )

    merged["put_change"] = (
        merged["put_oi_latest"]
        - merged["put_oi_prev"]
    )

    biggest_put = merged.loc[
        merged["put_change"].idxmax()
    ]

    biggest_call = merged.loc[
        merged["call_change"].idxmax()
    ]

    print("\n" + "=" * 60)
    print(symbol)
    print("=" * 60)

    print("\nSUPPORT BUILDUP")
    print(
        f"Strike      : {int(biggest_put['strike'])}"
    )
    print(
        f"Put OI Chg  : {int(biggest_put['put_change']):,}"
    )

    print("\nRESISTANCE BUILDUP")
    print(
        f"Strike      : {int(biggest_call['strike'])}"
    )
    print(
        f"Call OI Chg : {int(biggest_call['call_change']):,}"
    )

    print("\nINTERPRETATION")

    if (
        biggest_put["put_change"] > 0
        and biggest_call["call_change"] > 0
    ):
        print("Range Building")

    elif biggest_put["put_change"] > biggest_call["call_change"]:
        print("Bullish OI Build-up")

    elif biggest_call["call_change"] > biggest_put["put_change"]:
        print("Bearish OI Build-up")

    else:
        print("Neutral")

conn.close()