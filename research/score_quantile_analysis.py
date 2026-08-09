import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def load_data():

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        """
        SELECT
            prediction_date,
            index_name,
            rank,
            intelligence_score,
            return_5d

        FROM prediction_outcomes

        WHERE
            intelligence_score IS NOT NULL
            AND return_5d IS NOT NULL

        ORDER BY
            prediction_date,
            intelligence_score DESC
        """,
        conn
    )

    conn.close()

    return df


def analyze():

    print("\n" + "=" * 75)
    print("MARKETBOT SCORE QUANTILE ANALYSIS")
    print("=" * 75)

    df = load_data()

    if df.empty:

        print("\nNo prediction outcome data.")
        return

    print(
        f"\nObservations : {len(df):,}"
    )

    print(
        f"Trading dates : "
        f"{df['prediction_date'].nunique():,}"
    )

    # --------------------------------------------------
    # QUINTILES
    # --------------------------------------------------

    df["quintile"] = (
        df.groupby("prediction_date")[
            "intelligence_score"
        ]
        .transform(
            lambda x:
            pd.qcut(
                x.rank(
                    method="first"
                ),
                5,
                labels=[
                    "Q1_LOW",
                    "Q2",
                    "Q3",
                    "Q4",
                    "Q5_HIGH"
                ]
            )
        )
    )

    print("\n" + "=" * 75)
    print("5D RETURN BY SCORE QUINTILE")
    print("=" * 75)

    summary = (
        df.groupby("quintile", observed=True)
        .agg(
            observations=(
                "return_5d",
                "count"
            ),

            avg_return=(
                "return_5d",
                "mean"
            ),

            median_return=(
                "return_5d",
                "median"
            ),

            win_rate=(
                "return_5d",
                lambda x:
                (x > 0).mean() * 100
            ),

            best=(
                "return_5d",
                "max"
            ),

            worst=(
                "return_5d",
                "min"
            )
        )
    )

    print(
        summary.round(3).to_string()
    )

    # --------------------------------------------------
    # TOP VS BOTTOM
    # --------------------------------------------------

    top = df[
        df["quintile"] == "Q5_HIGH"
    ]["return_5d"]

    bottom = df[
        df["quintile"] == "Q1_LOW"
    ]["return_5d"]

    spread = (
        top.mean()
        -
        bottom.mean()
    )

    print("\n" + "=" * 75)
    print("TOP vs BOTTOM")
    print("=" * 75)

    print(
        f"Top 20% average return    : "
        f"{top.mean():.4f}%"
    )

    print(
        f"Bottom 20% average return : "
        f"{bottom.mean():.4f}%"
    )

    print(
        f"Top-Bottom spread         : "
        f"{spread:.4f}%"
    )

    print(
        f"Top 20% win rate          : "
        f"{(top > 0).mean() * 100:.2f}%"
    )

    print(
        f"Bottom 20% win rate       : "
        f"{(bottom > 0).mean() * 100:.2f}%"
    )

    # --------------------------------------------------
    # MONOTONICITY
    # --------------------------------------------------

    # Explicitly enforce the intended score order.
    # This prevents pandas/groupby ordering from affecting
    # the monotonicity test.

    quintile_order = [
        "Q1_LOW",
        "Q2",
        "Q3",
        "Q4",
        "Q5_HIGH"
    ]

    means = (
        summary
        .reindex(quintile_order)["avg_return"]
        .apply(pd.to_numeric, errors="coerce")
        .dropna()
        .astype(float)
        .tolist()
    )

    monotonic = all(
        means[i] <= means[i + 1]
        for i in range(len(means) - 1)
    )

    print("\n" + "=" * 75)
    print("SCORE MONOTONICITY")
    print("=" * 75)

    if monotonic:

        print(
            "PASS: Higher scores "
            "produce progressively higher returns."
        )

    else:

        print(
            "FAIL: Score ordering is "
            "not monotonic."
        )

    # --------------------------------------------------
    # VERDICT
    # --------------------------------------------------

    print("\n" + "=" * 75)
    print("RESEARCH VERDICT")
    print("=" * 75)

    if spread > 0:

        print(
            "The current score shows "
            "positive top-bottom separation."
        )

    elif spread < 0:

        print(
            "The current score shows "
            "NEGATIVE top-bottom separation."
        )

    else:

        print(
            "The current score shows "
            "no top-bottom separation."
        )


if __name__ == "__main__":

    analyze()