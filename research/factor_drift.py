import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def factor_drift():

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

    if df.empty:
        return

    monthly = (
        df.groupby("trade_date")
        ["intelligence_score"]
        .mean()
        .round(2)
    )

    print("\nFactor Drift")
    print("-" * 40)
    print(monthly)


if __name__ == "__main__":
    factor_drift()