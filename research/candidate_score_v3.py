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


# --------------------------------------------------
# RESEARCH DIRECTIONS
# --------------------------------------------------

DIRECTIONS = {
    "relative_strength": -1,
    "trend_score": 1,
    "momentum_score": -1,
    "volatility_score": -1,
    "liquidity_score": -1,
}


# --------------------------------------------------
# IC-DERIVED RESEARCH WEIGHTS
#
# Source:
# research/weight_optimizer.py
#
# These are research values only.
# They are NOT production weights.
# --------------------------------------------------

WEIGHTS = {
    "relative_strength": 0.3237,
    "trend_score": 0.2717,
    "momentum_score": 0.1702,
    "volatility_score": 0.1124,
    "liquidity_score": 0.1220,
}


def load_data():

    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql(
        """
        SELECT
            DATE(f.trade_date) AS trade_date,
            f.index_name AS index_name,

            f.relative_strength,
            f.trend_score,
            f.momentum_score,
            f.volatility_score,
            f.liquidity_score,

            o.return_5d

        FROM factor_history AS f

        INNER JOIN prediction_outcomes AS o

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
    # IC-WEIGHTED COMPOSITE
    # --------------------------------------------------

    weighted_components = []

    for factor in FACTORS:

        adjusted_column = (
            f"{factor}_adjusted"
        )

        weighted_column = (
            f"{factor}_weighted"
        )

        df[weighted_column] = (
            df[adjusted_column]
            * WEIGHTS[factor]
        )

        weighted_components.append(
            weighted_column
        )

    df["candidate_score"] = (
        df[weighted_components]
        .sum(axis=1)
    )

    return df


def quintile_analysis(df):

    df = df.copy()

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

    return df, summary


def calculate_ic(df):

    rows = []

    for factor in FACTORS:

        daily_ic = (
            df.groupby("trade_date")
            .apply(
                lambda x:
                x[f"{factor}_adjusted"]
                .corr(x["return_5d"]),
                include_groups=False
            )
            .dropna()
        )

        if daily_ic.empty:

            mean_ic = 0.0
            icir = 0.0

        else:

            mean_ic = daily_ic.mean()

            std_ic = daily_ic.std()

            icir = (
                mean_ic / std_ic
                if std_ic and std_ic > 0
                else 0.0
            )

        rows.append(
            {
                "factor": factor,
                "mean_ic": mean_ic,
                "icir": icir,
                "positive_days": int(
                    (daily_ic > 0).sum()
                ),
                "days": len(daily_ic),
            }
        )

    return pd.DataFrame(rows)


def analyze():

    print("\n" + "=" * 75)
    print("MARKETBOT CANDIDATE SCORE V3")
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

    # --------------------------------------------------
    # QUINTILE ANALYSIS
    # --------------------------------------------------

    df, summary = quintile_analysis(df)

    print(
        "\n===== IC-WEIGHTED RANK SCORE ====="
    )

    print(
        summary.round(4).to_string()
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
        - bottom.mean()
    )

    print(
        "\n===== TOP vs BOTTOM ====="
    )

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

    # --------------------------------------------------
    # FACTOR WEIGHTS
    # --------------------------------------------------

    print(
        "\n===== IC-DERIVED WEIGHTS ====="
    )

    for factor in FACTORS:

        direction = (
            "POSITIVE"
            if DIRECTIONS[factor] == 1
            else "NEGATIVE"
        )

        print(
            f"{factor:<25} "
            f"weight={WEIGHTS[factor]:.4f} "
            f"direction={direction}"
        )

    # --------------------------------------------------
    # FACTOR IC CHECK
    # --------------------------------------------------

    ic = calculate_ic(df)

    print(
        "\n===== CANDIDATE FACTOR IC ====="
    )

    print(
        ic.round(4).to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # VERDICT
    # --------------------------------------------------

    print(
        "\n===== RESEARCH VERDICT ====="
    )

    if spread > 0 and monotonic:

        print(
            "PASS: Candidate V3 has "
            "positive separation and "
            "monotonic quintile returns."
        )

    elif spread > 0:

        print(
            "PROMISING: Candidate V3 has "
            "positive top-bottom separation "
            "but is not monotonic."
        )

    else:

        print(
            "FAIL: Candidate V3 does not "
            "produce positive separation."
        )

    print(
        "\nCandidate V3 remains RESEARCH ONLY."
    )

    print(
        "Production scoring has NOT been changed."
    )


if __name__ == "__main__":
    analyze()