import sqlite3

import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB = BASE_DIR / "market_intelligence.db"


def score_drift():

    conn = sqlite3.connect(DB)

    df = pd.read_sql(

        """

        SELECT

            trade_date,

            AVG(intelligence_score) avg_score

        FROM factor_history

        GROUP BY trade_date

        ORDER BY trade_date

        """,

        conn

    )

    conn.close()

    print("\nAverage Intelligence Drift")

    print(df.tail(30))


if __name__ == "__main__":

    score_drift()