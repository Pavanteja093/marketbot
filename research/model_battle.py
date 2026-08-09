import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


V3_WEIGHTS = {
    "relative_strength": 0.3237,
    "trend_score": 0.2717,
    "momentum_score": 0.1702,
    "volatility_score": 0.1124,
    "liquidity_score": 0.1220,
}

V3_DIRECTIONS = {
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
            p.intelligence_score,
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
            p.intelligence_score IS NOT NULL
            AND p.return_5d IS NOT NULL

        ORDER BY
            p.prediction_date,
            p.index_name
        """,
        conn
    )

    conn.close()

    return df


def rank_normalize(series):

    if series.empty:
        return series

    ranks = series.rank(
        method="first",
        ascending=True
    )

    if len(series) == 1:
        return pd.Series(
            50.0,
            index=series.index
        )

    return (
        (ranks - 1)
        /
        (len(series) - 1)
    ) * 100


def build_v3_score(df):

    df = df.copy()

    score = pd.Series(
        0.0,
        index=df.index
    )

    for factor, weight in V3_WEIGHTS.items():

        normalized = (
            df.groupby("prediction_date")[factor]
            .transform(rank_normalize)
        )

        direction = V3_DIRECTIONS[factor]

        if direction < 0:
            normalized = 100 - normalized

        score += normalized * weight

    df["v3_score"] = score.round(4)

    return df


def calculate_metrics(
    df,
    score_column
):

    if df.empty:
        return None

    working = df[
        [
            "prediction_date",
            "index_name",
            score_column,
            "return_5d"
        ]
    ].dropna()

    if working.empty:
        return None

    correlation = working[
        score_column
    ].corr(
        working["return_5d"]
    )

    top_returns = []
    bottom_returns = []

    for _, group in working.groupby(
        "prediction_date"
    ):

        if len(group) < 5:
            continue

        ranked = group.sort_values(
            score_column,
            ascending=False
        )

        n = max(
            1,
            int(len(ranked) * 0.20)
        )

        top = ranked.head(n)
        bottom = ranked.tail(n)

        top_returns.extend(
            top["return_5d"].tolist()
        )

        bottom_returns.extend(
            bottom["return_5d"].tolist()
        )

    if not top_returns or not bottom_returns:
        return None

    top = pd.Series(top_returns)
    bottom = pd.Series(bottom_returns)

    top_mean = top.mean()
    bottom_mean = bottom.mean()

    return {
        "observations": len(working),

        "dates": working[
            "prediction_date"
        ].nunique(),

        "avg_return": working[
            "return_5d"
        ].mean(),

        "median_return": working[
            "return_5d"
        ].median(),

        "win_rate": (
            working["return_5d"] > 0
        ).mean() * 100,

        "best": working[
            "return_5d"
        ].max(),

        "worst": working[
            "return_5d"
        ].min(),

        "correlation": correlation,

        "top_return": top_mean,

        "bottom_return": bottom_mean,

        "spread": top_mean - bottom_mean,

        "top_win_rate": (
            top > 0
        ).mean() * 100,

        "bottom_win_rate": (
            bottom > 0
        ).mean() * 100
    }


def print_metrics(
    name,
    metrics
):

    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    if metrics is None:

        print("No valid evaluation data.")

        return

    print(
        f"Observations       : "
        f"{metrics['observations']:,}"
    )

    print(
        f"Trading Dates      : "
        f"{metrics['dates']:,}"
    )

    print(
        f"Average 5D Return  : "
        f"{metrics['avg_return']:.4f}%"
    )

    print(
        f"Median 5D Return   : "
        f"{metrics['median_return']:.4f}%"
    )

    print(
        f"Win Rate           : "
        f"{metrics['win_rate']:.2f}%"
    )

    print(
        f"Best Return        : "
        f"{metrics['best']:.4f}%"
    )

    print(
        f"Worst Return       : "
        f"{metrics['worst']:.4f}%"
    )

    print(
        f"Score Correlation  : "
        f"{metrics['correlation']:.6f}"
    )

    print(
        f"Top 20% Return     : "
        f"{metrics['top_return']:.4f}%"
    )

    print(
        f"Bottom 20% Return  : "
        f"{metrics['bottom_return']:.4f}%"
    )

    print(
        f"Top-Bottom Spread  : "
        f"{metrics['spread']:.4f}%"
    )

    print(
        f"Top 20% Win Rate   : "
        f"{metrics['top_win_rate']:.2f}%"
    )

    print(
        f"Bottom 20% Win Rate: "
        f"{metrics['bottom_win_rate']:.2f}%"
    )


def determine_winner(
    production,
    challenger
):

    if production is None or challenger is None:

        return "INSUFFICIENT DATA"

    challenger_score = 0
    production_score = 0

    if challenger["spread"] > production["spread"]:
        challenger_score += 1
    else:
        production_score += 1

    if challenger["avg_return"] > production["avg_return"]:
        challenger_score += 1
    else:
        production_score += 1

    if challenger["win_rate"] > production["win_rate"]:
        challenger_score += 1
    else:
        production_score += 1

    if challenger["correlation"] > production["correlation"]:
        challenger_score += 1
    else:
        production_score += 1

    if challenger_score > production_score:

        return (
            f"V3 CHALLENGER "
            f"({challenger_score}-{production_score})"
        )

    if production_score > challenger_score:

        return (
            f"PRODUCTION V1 "
            f"({production_score}-{challenger_score})"
        )

    return "TIE"


def model_battle():

    print("\n" + "=" * 75)
    print("MARKETBOT MODEL BATTLE")
    print("=" * 75)

    df = load_data()

    if df.empty:

        print("\nNo prediction outcome data available.")

        return

    print(
        f"\nObservations : "
        f"{len(df):,}"
    )

    print(
        f"Trading dates : "
        f"{df['prediction_date'].nunique():,}"
    )

    required = [
        "relative_strength",
        "trend_score",
        "momentum_score",
        "volatility_score",
        "liquidity_score"
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        print(
            "\nMissing V3 factor columns:"
        )

        for column in missing:
            print(f"  - {column}")

        return

    # --------------------------------------------------
    # BUILD V3
    # --------------------------------------------------

    df = build_v3_score(df)

    # --------------------------------------------------
    # PRODUCTION MODEL
    # --------------------------------------------------

    production = calculate_metrics(
        df,
        "intelligence_score"
    )

    # --------------------------------------------------
    # V3 CHALLENGER
    # --------------------------------------------------

    challenger = calculate_metrics(
        df,
        "v3_score"
    )

    # --------------------------------------------------
    # REPORT
    # --------------------------------------------------

    print_metrics(
        "PRODUCTION MODEL",
        production
    )

    print_metrics(
        "V3 CHALLENGER",
        challenger
    )

    # --------------------------------------------------
    # WINNER
    # --------------------------------------------------

    winner = determine_winner(
        production,
        challenger
    )

    print("\n" + "=" * 70)
    print("MODEL BATTLE RESULT")
    print("=" * 70)

    print(
        f"\nWinner : {winner}"
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "V3 remains RESEARCH ONLY."
    )

    print(
        "Production weights have NOT been changed."
    )


if __name__ == "__main__":
    model_battle()