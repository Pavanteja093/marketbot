import sqlite3
import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def optimize_weights():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql(
        """
        SELECT *
        FROM factor_history f
        JOIN forward_returns r
        USING(trade_date,index_name)
        """,
        conn
    )

    conn.close()

    factors = [
        "relative_strength",
        "trend_score",
        "momentum_score",
        "volatility_score",
        "liquidity_score"
    ]

    weights = {}

    for factor in factors:

        corr = df[factor].corr(df["return_5d"])

        if pd.isna(corr):
            corr = 0.0

        weights[factor] = float(abs(corr))

    weights = pd.Series(weights, dtype=float)

    weights = weights / weights.sum()

    print("\nRecommended Weights")
    print("-"*40)
    print(weights.round(3))

    import json

    weight_file = BASE_DIR / "weights.json"

    with open(weight_file, "w") as f:

        json.dump(
            weights.round(3).to_dict(),
            f,
            indent=4
        )

    print("\nweights.json updated.")
