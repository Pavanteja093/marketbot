import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def rank_stability():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql(
        """
        SELECT
            trade_date,
            index_name,
            intelligence_score
        FROM factor_history
        """,
        conn
    )

    conn.close()

    stability = (
        df.groupby("index_name")
        ["intelligence_score"]
        .std()
        .sort_values()
        .round(2)
    )

    print("\nMost Stable Stocks")
    print("-" * 40)
    print(stability.head(15))


if __name__ == "__main__":
    rank_stability()