import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def walk_forward_validation():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql(
        """
        SELECT
            trade_date,
            intelligence_score,
            return_5d
        FROM factor_history f
        JOIN forward_returns r
        USING(trade_date,index_name)
        """,
        conn
    )

    conn.close()

    if df.empty:
        print("No data.")
        return

    windows = []

    for start in range(0, len(df), 50):

        sample = df.iloc[start:start + 50]

        if len(sample) < 20:
            continue

        corr = sample["intelligence_score"].corr(sample["return_5d"])

        windows.append(corr)

    result = pd.DataFrame({
        "Window": range(1, len(windows)+1),
        "Correlation": windows
    })

    print("\nWalk Forward Validation")
    print("-"*40)
    print(result)