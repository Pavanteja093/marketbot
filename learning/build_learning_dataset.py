import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def build_learning_dataset():

    conn = sqlite3.connect(DB_PATH)

    print("\nLoading tables...")

    factors = pd.read_sql(
        "SELECT * FROM factor_history",
        conn
    )

    predictions = pd.read_sql(
        "SELECT * FROM prediction_history",
        conn
    )

    returns = pd.read_sql(
        "SELECT * FROM forward_returns",
        conn
    )

    print("Joining datasets...")

    df = factors.merge(
        predictions[
            [
                "trade_date",
                "symbol",
                "rank",
                "grade",
                "intelligence_score"
            ]
        ],
        on=["trade_date", "symbol"],
        how="left",
        suffixes=("", "_prediction")
    )

    df = df.merge(
        returns,
        on=["trade_date", "symbol"],
        how="left"
    )

    valid_returns = df["return_20d"].notna().sum()

    print(f"\nRows with valid 20-day returns: {valid_returns}")

    if valid_returns == 0:
        print("\nWARNING:")
        print("No valid forward returns were found.")
        print("Learning modules cannot be trained yet.")

    # --------------------------------------------------
    # Remove duplicate intelligence_score if present
    # --------------------------------------------------

    if "intelligence_score_prediction" in df.columns:

        df.drop(
            columns=["intelligence_score_prediction"],
            inplace=True
        )

    # --------------------------------------------------
    # Success Labels
    # --------------------------------------------------

    df["success_1d"] = df["return_1d"] > 0
    df["success_5d"] = df["return_5d"] > 0
    df["success_10d"] = df["return_10d"] > 0
    df["success_20d"] = df["return_20d"] > 0

    # --------------------------------------------------
    # Magnitude Labels
    # --------------------------------------------------

    df["strong_win"] = df["return_20d"] >= 5
    df["strong_loss"] = df["return_20d"] <= -5

    # --------------------------------------------------
    # Ranking Percentile
    # --------------------------------------------------

    df["top10_pick"] = df["rank"] <= 10
    df["top20_pick"] = df["rank"] <= 20

    # --------------------------------------------------
    # Future Direction
    # --------------------------------------------------

    df["future_direction"] = (
        df["return_20d"]
        .fillna(0)
        .apply(
            lambda x:
            "BULLISH" if x > 0
            else "BEARISH"
        )
    )

    # --------------------------------------------------
    # Store
    # --------------------------------------------------

    conn.execute("""
    DROP TABLE IF EXISTS learning_dataset
    """)

    df.to_sql(
        "learning_dataset",
        conn,
        index=False
    )

    conn.commit()
    conn.close()

    print("\n===================================")
    print("LEARNING DATASET CREATED")
    print("===================================")
    print(f"Rows    : {len(df)}")
    print(f"Columns : {len(df.columns)}")


if __name__ == "__main__":
    build_learning_dataset()