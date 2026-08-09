import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

FACTORS = [
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]

# Research directions obtained from the
# cross-sectional IC analysis.
DIRECTIONS = {
    "relative_strength": -1,
    "trend_score": 1,
    "momentum_score": -1,
    "volatility_score": -1,
    "liquidity_score": -1,
}


def load_data():

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        """
        SELECT
            DATE(f.trade_date) AS trade_date,
            f.index_name,

            f.relative_strength,
            f.trend_score,
            f.momentum_score,
            f.volatility_score,
            f.liquidity_score,

            o.return_5d

        FROM factor_history f

        INNER JOIN prediction_outcomes o
            ON DATE(f.trade_date)
             = DATE(o.prediction_date)
            AND f.index_name
             = o.index_name

        WHERE
            o.return_5d IS NOT NULL

        ORDER BY
            DATE(f.trade_date),
            f.index_name
        """,
        conn,
    )

    conn.close()

    return df


def rank_normalize(group):

    group = group.copy()

    for factor in FACTORS:

        values = pd.to_numeric(
            group[factor],
            errors="coerce"
        )

        ranks = values.rank(
            method="average",
            pct=True
        )

        group[f"{factor}_rank"] = (
            ranks * 100
        )

    return group


def build_candidate(df):

    df = df.copy()

    # --------------------------------------------------
    # CROSS-SECTIONAL RANK NORMALIZATION
    # --------------------------------------------------

    for factor in FACTORS:

        values = pd.to_numeric(
            df[factor],
            errors="coerce"
        )

        df[f"{factor}_rank"] = (
            values
            .groupby(df["trade_date"])
            .rank(
                method="average",
                pct=True
            )
            * 100
        )

    # --------------------------------------------------
    # DIRECTION ADJUSTMENT
    # --------------------------------------------------

    for factor in FACTORS:

        rank_column = f"{factor}_rank"
        adjusted_column = f"{factor}_adjusted"

        if DIRECTIONS[factor] == -1:

            df[adjusted_column] = (
                100
                - df[rank_column]
            )

        else:

            df[adjusted_column] = (
                df[rank_column]
            )

    # --------------------------------------------------
    # COMPOSITE CANDIDATE SCORE
    # --------------------------------------------------

    adjusted_columns = [
        f"{factor}_adjusted"
        for factor in FACTORS
    ]

    df["candidate_score"] = (
        df[adjusted_columns]
        .mean(axis=1)
    )

    return df


def quintile_analysis(df):

    df["quintile"] = (
        df.groupby("trade_date")[
            "candidate_score"
        ]
        .transform(
            lambda x: pd.qcut(
                x.rank(
                    method="first"
                ),
                5,
                labels=[
                    "Q1_LOW",
                    "Q2",
                    "Q3",
                    "Q4",
                    "Q5_HIGH",
                ],
            )
        )
    )

    summary = (
        df.groupby(
            "quintile",
            observed=True
        )
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
            ),
        )
    )

    return summary


def analyze():

    print("\n" + "=" * 75)
    print("MARKETBOT CANDIDATE SCORE V2")
    print("=" * 75)

    df = load_data()

    if df.empty:

        print("\nNo prediction outcome data.")
        return

    print(
        f"\nObservations : {len(df):,}"
    )

    print(
        "Trading dates : "
        f"{df['trade_date'].nunique():,}"
    )

    df = build_candidate(df)

    summary = quintile_analysis(df)

    print(
        "\n===== RANK-NORMALIZED SCORE ====="
    )

    print(
        summary.round(4).to_string()
    )

    top = df[
        df["quintile"] == "Q5_HIGH"
    ]["return_5d"]

    bottom = df[
        df["quintile"] == "Q1_LOW"
    ]["return_5d"]

    spread = (
        top.mean()
        - bottom.mean()
    )

    print("\n===== TOP vs BOTTOM =====")

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

    means = (
        summary["avg_return"]
        .astype(float)
        .tolist()
    )

    monotonic = all(
        means[i] <= means[i + 1]
        for i in range(len(means) - 1)
    )

    print(
        "\n===== MONOTONICITY ====="
    )

    if monotonic:

        print(
            "PASS: Higher candidate scores "
            "produce progressively higher "
            "average returns."
        )

    else:

        print(
            "FAIL: Candidate score is "
            "not monotonic."
        )

    print(
        "\n===== FACTOR DIRECTIONS ====="
    )

    for factor in FACTORS:

        direction = (
            "POSITIVE"
            if DIRECTIONS[factor] == 1
            else "NEGATIVE"
        )

        print(
            f"{factor:<25} {direction}"
        )

    print(
        "\nNOTE: Candidate V2 is research only."
    )

    print(
        "It has NOT modified production weights."
    )


if __name__ == "__main__":
    analyze()