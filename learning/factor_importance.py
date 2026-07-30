import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def calculate_factor_importance():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql(
        "SELECT * FROM learning_dataset",
        conn
    )

    conn.close()

    factors = [
        "change_pct",
        "sector_strength",
        "position_pct",
        "total_score",
        "intelligence_score"
    ]

    target = "return_20d"

    results = []

    for factor in factors:

        corr = df[factor].corr(df[target])

        strength = abs(corr)

        if strength >= 0.70:
            rating = "VERY STRONG"
        elif strength >= 0.50:
            rating = "STRONG"
        elif strength >= 0.30:
            rating = "MODERATE"
        elif strength >= 0.10:
            rating = "WEAK"
        else:
            rating = "VERY WEAK"

        results.append({
            "factor": factor,
            "correlation": round(corr, 4),
            "rating": rating
        })

    results = (
        pd.DataFrame(results)
        .sort_values(
            "correlation",
            ascending=False
        )
    )

    print("\n")
    print("=" * 50)
    print("FACTOR IMPORTANCE")
    print("=" * 50)

    print(results.to_string(index=False))

    results.to_sql(
        "factor_importance",
        sqlite3.connect(DB_PATH),
        if_exists="replace",
        index=False
    )

    return results


if __name__ == "__main__":

    calculate_factor_importance()