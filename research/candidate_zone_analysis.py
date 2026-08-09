import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


WEIGHTS = {
    "relative_strength": 0.3237,
    "trend_score": 0.2717,
    "momentum_score": 0.1702,
    "volatility_score": 0.1124,
    "liquidity_score": 0.1220,
}


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
            p.prediction_date,
            p.index_name,
            p.return_5d,

            f.relative_strength,
            f.trend_score,
            f.momentum_score,
            f.volatility_score,
            f.liquidity_score

        FROM prediction_outcomes p

        INNER JOIN factor_history f
            ON p.prediction_date = f.trade_date
            AND p.index_name = f.index_name

        WHERE
            p.return_5d IS NOT NULL
            AND f.relative_strength IS NOT NULL
            AND f.trend_score IS NOT NULL
            AND f.momentum_score IS NOT NULL
            AND f.volatility_score IS NOT NULL
            AND f.liquidity_score IS NOT NULL

        ORDER BY
            p.prediction_date,
            p.index_name
        """,
        conn
    )

    conn.close()

    return df


def rank_normalize(series):

    ranks = series.rank(
        method="first",
        ascending=True
    )

    if len(series) <= 1:
        return pd.Series(
            50.0,
            index=series.index
        )

    return (
        (ranks - 1)
        /
        (len(series) - 1)
    ) * 100


def build_score(df):

    df = df.copy()

    df["candidate_score"] = 0.0

    for factor, weight in WEIGHTS.items():

        normalized = (
            df.groupby("prediction_date")[factor]
            .transform(rank_normalize)
        )

        if DIRECTIONS[factor] < 0:

            normalized = 100 - normalized

        df["candidate_score"] += (
            normalized * weight
        )

    return df


def assign_quintiles(df):

    df = df.copy()

    df["quintile"] = (
        df.groupby("prediction_date")[
            "candidate_score"
        ]
        .transform(
            lambda x:
            pd.qcut(
                x.rank(method="first"),
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

    return df


def analyze():

    print("\n" + "=" * 75)
    print("MARKETBOT CANDIDATE ZONE ANALYSIS")
    print("=" * 75)

    df = load_data()

    if df.empty:

        print("\nNo data available.")

        return

    print(
        f"\nObservations : {len(df):,}"
    )

    print(
        f"Trading dates : "
        f"{df['prediction_date'].nunique():,}"
    )

    df = build_score(df)

    df = assign_quintiles(df)

    print("\n" + "=" * 75)
    print("QUINTILE PERFORMANCE")
    print("=" * 75)

    summary = (
        df.groupby(
            "quintile",
            observed=True
        )
        .agg(
            observations=("return_5d", "count"),

            avg_return=("return_5d", "mean"),

            median_return=("return_5d", "median"),

            win_rate=(
                "return_5d",
                lambda x:
                (x > 0).mean() * 100
            ),

            best=("return_5d", "max"),

            worst=("return_5d", "min")
        )
    )

    print(
        summary.round(4).to_string()
    )

    q34 = df[
        df["quintile"].isin(
            ["Q3", "Q4"]
        )
    ]["return_5d"]

    q5 = df[
        df["quintile"] == "Q5_HIGH"
    ]["return_5d"]

    q12 = df[
        df["quintile"].isin(
            ["Q1_LOW", "Q2"]
        )
    ]["return_5d"]

    print("\n" + "=" * 75)
    print("ZONE COMPARISON")
    print("=" * 75)

    print(
        f"\nQ3 + Q4 average return : "
        f"{q34.mean():.4f}%"
    )

    print(
        f"Q5 average return      : "
        f"{q5.mean():.4f}%"
    )

    print(
        f"Q1 + Q2 average return : "
        f"{q12.mean():.4f}%"
    )

    print(
        f"\nQ3 + Q4 win rate       : "
        f"{(q34 > 0).mean() * 100:.2f}%"
    )

    print(
        f"Q5 win rate             : "
        f"{(q5 > 0).mean() * 100:.2f}%"
    )

    print(
        f"Q1 + Q2 win rate        : "
        f"{(q12 > 0).mean() * 100:.2f}%"
    )

    print("\n" + "=" * 75)
    print("ZONE VERDICT")
    print("=" * 75)

    if q34.mean() > q5.mean():

        print(
            "Q3 + Q4 currently outperform Q5."
        )

    elif q5.mean() > q34.mean():

        print(
            "Q5 currently outperforms Q3 + Q4."
        )

    else:

        print(
            "Q3 + Q4 and Q5 are currently equal."
        )

    print(
        "\nThis is RESEARCH ONLY."
    )

    print(
        "No production selection rule has been changed."
    )


if __name__ == "__main__":
    analyze()