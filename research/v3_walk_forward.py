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


def cross_sectional_ic(df, factor):

    daily_ic = []

    for _, group in df.groupby("prediction_date"):

        if len(group) < 5:
            continue

        x = pd.to_numeric(
            group[factor],
            errors="coerce"
        )

        y = pd.to_numeric(
            group["return_5d"],
            errors="coerce"
        )

        valid = pd.concat(
            [x, y],
            axis=1
        ).dropna()

        if len(valid) < 5:
            continue

        if valid[factor].nunique() < 2:
            continue

        if valid["return_5d"].nunique() < 2:
            continue

        corr = valid[factor].corr(
            valid["return_5d"]
        )

        if pd.notna(corr):
            daily_ic.append(corr)

    if not daily_ic:
        return 0.0

    return sum(daily_ic) / len(daily_ic)


def derive_weights(
    train
):

    ic_values = {}

    for factor in FACTORS:

        ic_values[factor] = (
            cross_sectional_ic(
                train,
                factor
            )
        )

    absolute_ic = {
        factor: abs(value)
        for factor, value
        in ic_values.items()
    }

    total = sum(
        absolute_ic.values()
    )

    if total == 0:

        weights = {
            factor: 1 / len(FACTORS)
            for factor in FACTORS
        }

    else:

        weights = {
            factor:
            absolute_ic[factor] / total
            for factor in FACTORS
        }

    directions = {
        factor:
        1 if ic_values[factor] >= 0 else -1
        for factor in FACTORS
    }

    return (
        ic_values,
        weights,
        directions
    )


def rank_normalize(series):

    ranks = series.rank(
        method="first"
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


def build_score(
    df,
    weights,
    directions
):

    df = df.copy()

    df["v3_score"] = 0.0

    for factor in FACTORS:

        normalized = (
            df.groupby("prediction_date")[
                factor
            ]
            .transform(rank_normalize)
        )

        if directions[factor] < 0:

            normalized = 100 - normalized

        df["v3_score"] += (
            normalized *
            weights[factor]
        )

    return df


def evaluate(
    df
):

    if df.empty:
        return None

    top_returns = []
    bottom_returns = []

    all_returns = []

    for _, group in df.groupby(
        "prediction_date"
    ):

        if len(group) < 5:
            continue

        ranked = group.sort_values(
            "v3_score",
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

        all_returns.extend(
            group["return_5d"].tolist()
        )

    if not top_returns:
        return None

    top = pd.Series(top_returns)
    bottom = pd.Series(bottom_returns)
    all_data = pd.Series(all_returns)

    return {
        "observations": len(df),

        "dates": df[
            "prediction_date"
        ].nunique(),

        "average_return":
            all_data.mean(),

        "median_return":
            all_data.median(),

        "win_rate":
            (all_data > 0).mean() * 100,

        "top_return":
            top.mean(),

        "bottom_return":
            bottom.mean(),

        "spread":
            top.mean() - bottom.mean(),

        "top_win_rate":
            (top > 0).mean() * 100,

        "bottom_win_rate":
            (bottom > 0).mean() * 100,
    }


def print_result(
    name,
    result
):

    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    if result is None:

        print("No valid evaluation data.")

        return

    print(
        f"Observations       : "
        f"{result['observations']:,}"
    )

    print(
        f"Trading Dates      : "
        f"{result['dates']:,}"
    )

    print(
        f"Average 5D Return  : "
        f"{result['average_return']:.4f}%"
    )

    print(
        f"Median 5D Return   : "
        f"{result['median_return']:.4f}%"
    )

    print(
        f"Win Rate           : "
        f"{result['win_rate']:.2f}%"
    )

    print(
        f"Top 20% Return     : "
        f"{result['top_return']:.4f}%"
    )

    print(
        f"Bottom 20% Return  : "
        f"{result['bottom_return']:.4f}%"
    )

    print(
        f"Top-Bottom Spread  : "
        f"{result['spread']:.4f}%"
    )

    print(
        f"Top 20% Win Rate   : "
        f"{result['top_win_rate']:.2f}%"
    )

    print(
        f"Bottom 20% Win Rate: "
        f"{result['bottom_win_rate']:.2f}%"
    )


def main():

    print("\n" + "=" * 75)
    print("MARKETBOT V3 OUT-OF-SAMPLE WALK-FORWARD")
    print("=" * 75)

    df = load_data()

    if df.empty:

        print("\nNo data available.")

        return

    dates = sorted(
        df["prediction_date"].unique()
    )

    print(
        f"\nTotal observations : "
        f"{len(df):,}"
    )

    print(
        f"Trading dates      : "
        f"{len(dates):,}"
    )

    if len(dates) < 40:

        print(
            "\nInsufficient dates "
            "for walk-forward validation."
        )

        return

    # --------------------------------------------------
    # WALK-FORWARD WINDOWS
    # --------------------------------------------------

    train_size = 120
    test_size = 20
    step_size = 20

    results = []

    window_number = 1

    for start in range(
        0,
        len(dates) - train_size - test_size + 1,
        step_size
    ):

        train_dates = dates[
            start:
            start + train_size
        ]

        test_dates = dates[
            start + train_size:
            start + train_size + test_size
        ]

        train = df[
            df["prediction_date"].isin(
                train_dates
            )
        ].copy()

        test = df[
            df["prediction_date"].isin(
                test_dates
            )
        ].copy()

        if train.empty or test.empty:
            continue

        (
            ic_values,
            weights,
            directions
        ) = derive_weights(train)

        print("\nTRAIN FACTOR IC / WEIGHTS")

        for factor in FACTORS:

            print(
                f"{factor:<22}"
                f" IC={ic_values[factor]:>8.4f}"
                f" Weight={weights[factor]:>7.4f}"
                f" Direction="
                f"{'POSITIVE' if directions[factor] > 0 else 'NEGATIVE'}"
            )

        test_scored = build_score(
            test,
            weights,
            directions
        )

        print("\nTEST FACTOR IC")

        for factor in FACTORS:

            test_ic = cross_sectional_ic(
                test,
                factor
            )

            print(
                f"{factor:<22}"
                f" TestIC={test_ic:>8.4f}"
            )

        result = evaluate(
            test_scored
        )

        if result is None:
            continue

        result["window"] = window_number
        result["train_start"] = train_dates[0]
        result["train_end"] = train_dates[-1]
        result["test_start"] = test_dates[0]
        result["test_end"] = test_dates[-1]

        results.append(result)

        print(
            f"\nWindow {window_number}"
        )

        print(
            f"Train : "
            f"{train_dates[0]} -> "
            f"{train_dates[-1]}"
        )

        print(
            f"Test  : "
            f"{test_dates[0]} -> "
            f"{test_dates[-1]}"
        )

        print(
            f"Spread: "
            f"{result['spread']:.4f}%"
        )

        window_number += 1

    if not results:

        print(
            "\nNo valid walk-forward windows."
        )

        return

    results_df = pd.DataFrame(
        results
    )

    print("\n" + "=" * 75)
    print("WALK-FORWARD SUMMARY")
    print("=" * 75)

    print(
        results_df[
            [
                "window",
                "train_start",
                "train_end",
                "test_start",
                "test_end",
                "average_return",
                "top_return",
                "bottom_return",
                "spread",
                "top_win_rate",
                "bottom_win_rate",
            ]
        ]
        .round(4)
        .to_string(index=False)
    )

    print("\n" + "=" * 75)
    print("OUT-OF-SAMPLE AGGREGATE")
    print("=" * 75)

    print(
        f"Windows             : "
        f"{len(results_df)}"
    )

    print(
        f"Average spread      : "
        f"{results_df['spread'].mean():.4f}%"
    )

    print(
        f"Median spread       : "
        f"{results_df['spread'].median():.4f}%"
    )

    print(
        f"Positive windows    : "
        f"{(results_df['spread'] > 0).sum()}"
    )

    print(
        f"Negative windows    : "
        f"{(results_df['spread'] < 0).sum()}"
    )

    positive_ratio = (
        results_df["spread"] > 0
    ).mean() * 100

    print(
        f"Positive window %   : "
        f"{positive_ratio:.2f}%"
    )

    print("\n" + "=" * 75)
    print("RESEARCH VERDICT")
    print("=" * 75)

    if (
        results_df["spread"].mean() > 0
        and positive_ratio >= 55
    ):

        print(
            "PROMISING:"
        )

        print(
            "V3 shows positive "
            "out-of-sample separation."
        )

    else:

        print(
            "NOT READY:"
        )

        print(
            "V3 does not yet show "
            "sufficiently robust "
            "out-of-sample separation."
        )

    print(
        "\nProduction scoring "
        "has NOT been changed."
    )


if __name__ == "__main__":
    main()