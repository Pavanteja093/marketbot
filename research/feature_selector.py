import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def feature_selector():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql(
        """
        SELECT *
        FROM factor_history
        """,
        conn
    )

    conn.close()

    ignore = [
        "id",
        "trade_date",
        "index_name",
        "sector",
        "created_at"
    ]

    numeric = [
        c for c in df.columns
        if c not in ignore
        and pd.api.types.is_numeric_dtype(df[c])
    ]

    variance = (
        df[numeric]
        .var()
        .sort_values(ascending=False)
        .round(3)
    )

    print("\nFeature Variance")
    print("-"*40)
    print(variance)