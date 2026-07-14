import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def performance_summary():

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        """
        SELECT *
        FROM trade_performance
        """,
        conn
    )

    conn.close()

    if len(df) == 0:

        print("No tracked trades.")
        return

    win_rate = (
        (df["actual_return"] > 0)
        .mean()
        * 100
    )

    avg_return = (
        df["actual_return"]
        .mean()
    )

    print("\nPERFORMANCE SUMMARY\n")

    print(
        f"Trades     : {len(df)}"
    )

    print(
        f"Win Rate   : {win_rate:.2f}%"
    )

    print(
        f"Avg Return : {avg_return:.2f}%"
    )