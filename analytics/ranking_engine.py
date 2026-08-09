import pandas as pd

from database.db import get_connection


def build_rankings():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            trade_date,
            index_name,
            intelligence_score,
            relative_strength,
            trend_score,
            momentum_score,
            volatility_score,
            liquidity_score
        FROM factor_history
        """,
        conn
    )

    conn.close()

    if df.empty:
        print("No ranking data.")
        return

    # Overall Ranking

    df["overall_rank"] = (
        df["intelligence_score"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )

    # Momentum Ranking

    df["momentum_rank"] = (
        df["momentum_score"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )

    # Trend Ranking

    df["trend_rank"] = (
        df["trend_score"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )

    # Relative Strength Ranking

    df["rs_rank"] = (
        df["relative_strength"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )

    # Liquidity Ranking

    df["liquidity_rank"] = (
        df["liquidity_score"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )

    df = df.sort_values("overall_rank")

    df["signal"] = "HOLD"

    df.loc[
        df["intelligence_score"] >= 70,
        "signal"
    ] = "BUY"

    df.loc[
        df["intelligence_score"] >= 85,
        "signal"
    ] = "STRONG BUY"

    df.loc[
        df["intelligence_score"] < 40,
        "signal"
    ] = "SELL"

    df["strength"] = df[
        [
            "relative_strength",
            "trend_score",
            "momentum_score"
        ]
    ].mean(axis=1)

    df["quality"] = df[
        [
            "volatility_score",
            "liquidity_score"
        ]
    ].mean(axis=1)

    # ------------------------------------------
    # Percentile Rank
    # ------------------------------------------

    df["percentile"] = (
        df["intelligence_score"]
        .rank(pct=True)
        .mul(100)
        .round(1)
    )

    df["score_gap"] = (
        df["intelligence_score"]
        - df["intelligence_score"].shift(-1)
    ).round(2)

    df["score_gap"] = df["score_gap"].fillna(0)

    print("\nRanking Statistics")
    print("-" * 40)
    print(f"Total Stocks : {len(df)}")
    print(f"Average Score: {df['intelligence_score'].mean():.2f}")
    print(f"Highest Score: {df['intelligence_score'].max():.2f}")
    print(f"Lowest Score : {df['intelligence_score'].min():.2f}")

    print("\n==============================")
    print(" MARKETBOT STOCK RANKINGS ")
    print("==============================")
    print(
        df[
            [
                "overall_rank",
                "index_name",
                "signal",
                "intelligence_score",
                "momentum_rank",
                "trend_rank",
                "rs_rank",
                "liquidity_rank"
            ]
        ].head(20)
    )

    print("\nTop Score Gap")

    leader = df.iloc[0]
    runner = df.iloc[1]

    gap = leader["intelligence_score"] - runner["intelligence_score"]

    print(f"{leader['index_name']} leads by {gap:.2f} points")

    print("\nTop 5 Percentile Stocks")
    print("-" * 40)

    print(
        df[
            [
                "overall_rank",
                "index_name",
                "percentile"
            ]
        ].head(5)
    )

    print("\nTop 5 Momentum Leaders")
    print("-" * 40)

    print(
        df.sort_values(
            "momentum_score",
            ascending=False
        )[
            [
                "index_name",
                "momentum_score",
                "overall_rank"
            ]
        ].head(5)
    )

    print("\nTop Momentum Stock")
    print("-" * 30)

    best = df.sort_values(
        "momentum_score",
        ascending=False
    ).iloc[0]

    print(best["index_name"])
    print(best["momentum_score"])

    return df


if __name__ == "__main__":

    build_rankings()