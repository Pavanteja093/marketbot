import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def prediction_calibration():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql(
        """
        SELECT
            intelligence_score,
            return_5d
        FROM factor_history f
        JOIN forward_returns r
        USING(trade_date,index_name)
        """,
        conn
    )

    conn.close()

    df["bucket"] = pd.qcut(
        df["intelligence_score"],
        5,
        duplicates="drop"
    )

    report = (
        df.groupby("bucket")
        ["return_5d"]
        .mean()
        .round(3)
    )

    print("\nPrediction Calibration")
    print("-"*40)
    print(report)