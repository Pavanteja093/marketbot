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
    "intelligence_score",
]


def load_data():

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        """
        SELECT
            f.trade_date,
            f.index_name,

            f.relative_strength,
            f.trend_score,
            f.momentum_score,
            f.volatility_score,
            f.liquidity_score,
            f.intelligence_score,

            r.return_5d

        FROM factor_history f

        INNER JOIN forward_returns r
            ON f.trade_date = substr(r.trade_date, 1, 10)
            AND f.index_name = r.index_name

        WHERE
            r.return_5d IS NOT NULL

        ORDER BY
            f.trade_date,
            f.index_name
        """,
        conn,
    )

    conn.close()

    return df


def factor_quintile_analysis(df, factor):

    data = df[
        [
            factor,
            "return_5d"
        ]
    ].dropna()

    if len(data) < 100:

        return None

    data = data.copy()

    data["quintile"] = pd.qcut(
        data[factor].rank(method="first"),
        5,
        labels=[
            "Q1_LOW",
            "Q2",
            "Q3",
            "Q4",
            "Q5_HIGH"
        ]
    )

    grouped = (
        data.groupby(
            "quintile",
            observed=True
        )["return_5d"]
        .agg(
            observations="count",
            avg_return="mean",
            median_return="median"
        )
    )

    grouped = grouped.reindex(
        [
            "Q1_LOW",
            "Q2",
            "Q3",
            "Q4",
            "Q5_HIGH"
        ]
    )

    top = grouped.loc["Q5_HIGH", "avg_return"]
    bottom = grouped.loc["Q1_LOW", "avg_return"]

    spread = top - bottom

    correlation = data[factor].corr(
        data["return_5d"]
    )

    return {
        "factor": factor,
        "observations": len(data),
        "correlation": correlation,
        "q1_return": bottom,
        "q5_return": top,
        "spread": spread,
        "monotonic": all(
            grouped["avg_return"].iloc[i]
            <= grouped["avg_return"].iloc[i + 1]
            for i in range(len(grouped) - 1)
        ),
    }


def analyze():

    print("\n" + "=" * 75)
    print("MARKETBOT FACTOR DIAGNOSTIC")
    print("=" * 75)

    df = load_data()

    if df.empty:

        print("\nNo factor/return observations found.")
        return

    print(
        f"\nObservations : {len(df):,}"
    )

    print(
        f"Trading dates : "
        f"{df['trade_date'].nunique():,}"
    )

    results = []

    for factor in FACTORS:

        result = factor_quintile_analysis(
            df,
            factor
        )

        if result is not None:

            results.append(result)

    result_df = pd.DataFrame(results)

    if result_df.empty:

        print("\nNo diagnostic results available.")
        return

    result_df = result_df.sort_values(
        "spread",
        ascending=False
    )

    print("\n" + "=" * 75)
    print("FACTOR PERFORMANCE")
    print("=" * 75)

    display_df = result_df.copy()

    display_df["correlation"] = (
        display_df["correlation"].round(4)
    )

    display_df["q1_return"] = (
        display_df["q1_return"].round(4)
    )

    display_df["q5_return"] = (
        display_df["q5_return"].round(4)
    )

    display_df["spread"] = (
        display_df["spread"].round(4)
    )

    print(
        display_df.to_string(
            index=False
        )
    )

    print("\n" + "=" * 75)
    print("FACTOR INTERPRETATION")
    print("=" * 75)

    for _, row in result_df.iterrows():

        direction = (
            "POSITIVE"
            if row["spread"] > 0
            else "NEGATIVE"
            if row["spread"] < 0
            else "NEUTRAL"
        )

        print(
            f"{row['factor']:<25}"
            f"{direction:<10}"
            f"Spread={row['spread']:.4f}%"
            f"  Corr={row['correlation']:.4f}"
        )


if __name__ == "__main__":

    analyze()