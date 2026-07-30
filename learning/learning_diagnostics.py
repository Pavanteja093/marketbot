import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def learning_diagnostics():

    conn = sqlite3.connect(DB_PATH)

    factors = pd.read_sql(
        "SELECT trade_date, symbol FROM factor_history",
        conn
    )

    predictions = pd.read_sql(
        "SELECT trade_date, symbol FROM prediction_history",
        conn
    )

    returns = pd.read_sql(
        "SELECT trade_date, symbol FROM forward_returns",
        conn
    )

    conn.close()

    print("\n" + "=" * 60)
    print("LEARNING DATASET DIAGNOSTICS")
    print("=" * 60)

    print(f"\nFactor History     : {len(factors)}")
    print(f"Prediction History : {len(predictions)}")
    print(f"Forward Returns    : {len(returns)}")

    fp = factors.merge(
        predictions,
        on=["trade_date", "symbol"],
        how="inner"
    )

    print(f"\nFactor ↔ Prediction Matches : {len(fp)}")

    fpr = fp.merge(
        returns,
        on=["trade_date", "symbol"],
        how="inner"
    )

    print(f"Factor ↔ Prediction ↔ Return Matches : {len(fpr)}")

    missing_returns = fp.merge(
        returns,
        on=["trade_date", "symbol"],
        how="left",
        indicator=True
    )

    missing_returns = missing_returns[
        missing_returns["_merge"] == "left_only"
    ]

    print(f"\nRows Missing Returns : {len(missing_returns)}")

    if not missing_returns.empty:
        print("\nSample Missing Rows:")
        print(missing_returns.head(10).to_string(index=False))


if __name__ == "__main__":
    learning_diagnostics()