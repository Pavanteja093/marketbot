import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def rolling_performance():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql(
        """
        SELECT
            trade_date,
            intelligence_score
        FROM factor_history
        ORDER BY trade_date
        """,
        conn
    )

    conn.close()

    df["rolling_mean"] = (
        df["intelligence_score"]
        .rolling(20)
        .mean()
    )

    print("\nRolling Performance")
    print("-"*40)
    print(df.tail(30))