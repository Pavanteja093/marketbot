import sqlite3

import pandas as pd


def confidence_bins():

    conn = sqlite3.connect("market_intelligence.db")

    try:

        df = pd.read_sql(
            """
            SELECT
                confidence,
                future_return_5d
            FROM prediction_history
            WHERE confidence IS NOT NULL
              AND future_return_5d IS NOT NULL
            """,
            conn
        )

    finally:

        conn.close()

    if df.empty:

        print("\nNo validated confidence data.")

        return

    df["confidence_bin"] = pd.cut(

        df["confidence"],

        bins=[0,20,40,60,80,100],

        include_lowest=True

    )

    report = (

        df

        .groupby("confidence_bin")["future_return_5d"]

        .agg(

            Count="count",

            Average_Return="mean"

        )

        .round(2)

    )

    print("\n")

    print("=" * 60)

    print("CONFIDENCE CALIBRATION")

    print("=" * 60)

    print(report)