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

        ORDER BY
            p.prediction_date,
            p.index_name
        """,
        conn
    )

    conn.close()

    return df


def daily_ic(group, factor):

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
        return None

    if valid[factor].nunique() < 2:
        return None

    if valid["return_5d"].nunique() < 2:
        return None

    value = valid[factor].corr(
        valid["return_5d"]
    )

    if pd.isna(value):
        return None

    return float(value)


def derive_weights(train):

    ics = {}

    for factor in FACTORS:

        values = []

        for _, group in train.groupby(
            "prediction_date"
        ):

            ic = daily_ic(
                group,
                factor
            )

            if ic is not None:
                values.append(ic)

        if values:

            ics[factor] = (
                sum(values) / len(values)
            )

        else:

            ics[factor] = 0.0

    total = sum(
        abs(value)
        for value in ics.values()
    )

    if total == 0:

        weights = {
            factor: 1 / len(FACTORS)
            for factor in FACTORS
        }

    else:

        weights = {
            factor:
                abs(ics[factor]) / total
            for factor in FACTORS
        }

    directions = {
        factor:
            1 if ics[factor] >= 0 else -1
        for factor in FACTORS
    }

    return weights, directions, ics


def build_score(
    df,
    weights,
    directions
):

    df = df.copy()

    df["score"] = 0.0

    for factor in FACTORS:

        ranks = (
            df.groupby(
                "prediction_date"
            )[factor]
            .rank(
                method="first"
            )
        )

        counts = (
            df.groupby(
                "prediction_date"
            )[factor]
            .transform("count")
        )

        denominator = (
            counts - 1
        ).replace(
            0,
            1
        )

        normalized = (
            (ranks - 1)
            / denominator
        ) * 100

        normalized = normalized.fillna(
            50.0
        )

        if directions[factor] < 0:

            normalized = (
                100 - normalized
            )

        df["score"] += (
            normalized *
            weights[factor]
        )

    return df


def evaluate(test):

    top_returns = []
    bottom_returns = []

    for _, group in test.groupby(
        "prediction_date"
    ):

        group = group.dropna(
            subset=[
                "score",
                "return_5d"
            ]
        )

        if len(group) < 10:
            continue

        group = group.sort_values(
            "score"
        )

        n = max(
            1,
            int(
                len(group) * 0.20
            )
        )

        bottom_returns.extend(
            group.head(n)["return_5d"]
            .tolist()
        )

        top_returns.extend(
            group.tail(n)["return_5d"]
            .tolist()
        )

    top = pd.Series(
        top_returns,
        dtype="float64"
    )

    bottom = pd.Series(
        bottom_returns,
        dtype="float64"
    )

    if top.empty or bottom.empty:

        return {
            "top_return": None,
            "bottom_return": None,
            "normal_spread": None,
            "reversed_spread": None,
            "top_win_rate": None,
            "bottom_win_rate": None,
        }

    top_mean = top.mean()
    bottom_mean = bottom.mean()

    return {
        "top_return": top_mean,
        "bottom_return": bottom_mean,

        "normal_spread":
            top_mean - bottom_mean,

        "reversed_spread":
            bottom_mean - top_mean,

        "top_win_rate":
            (top > 0).mean() * 100,

        "bottom_win_rate":
            (bottom > 0).mean() * 100,
    }


def main():

    print("\n" + "=" * 80)
    print("MARKETBOT SCORE DIRECTION WALK-FORWARD")
    print("=" * 80)

    df = load_data()

    if df.empty:

        print(
            "\nNo matched factor/outcome data."
        )

        return

    print(
        f"\nObservations : {len(df):,}"
    )

    print(
        f"Trading dates : "
        f"{df['prediction_date'].nunique():,}"
    )

    dates = sorted(
        df["prediction_date"].unique()
    )

    train_size = 120
    test_size = 20
    step = 20

    if len(dates) < (
        train_size + test_size
    ):

        print(
            "\nInsufficient dates for "
            "walk-forward validation."
        )

        return

    results = []

    window = 1

    for start in range(
        0,
        len(dates)
        - train_size
        - test_size
        + 1,
        step
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
        ]

        test = df[
            df["prediction_date"].isin(
                test_dates
            )
        ]

        weights, directions, ics = (
            derive_weights(train)
        )

        print("\n" + "-" * 80)
        print(
            f"WINDOW {window}"
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

        print("\nTRAIN IC / WEIGHTS")

        for factor in FACTORS:

            print(
                f"{factor:<22}"
                f"IC={ics[factor]: .5f} "
                f"Weight={weights[factor]:.4f} "
                f"Direction="
                f"{'POSITIVE' if directions[factor] > 0 else 'NEGATIVE'}"
            )

        test = build_score(
            test,
            weights,
            directions
        )

        result = evaluate(test)

        result["window"] = window

        results.append(result)

        if result["normal_spread"] is not None:

            print(
                f"\nNormal spread   : "
                f"{result['normal_spread']:.4f}%"
            )

            print(
                f"Reversed spread : "
                f"{result['reversed_spread']:.4f}%"
            )

        window += 1

    result_df = pd.DataFrame(
        results
    )

    print("\n" + "=" * 80)
    print("DIRECTION SUMMARY")
    print("=" * 80)

    print(
        result_df.round(4).to_string(
            index=False
        )
    )

    valid = result_df.dropna(
        subset=[
            "normal_spread",
            "reversed_spread"
        ]
    )

    if valid.empty:

        print(
            "\nNo valid walk-forward results."
        )

        return

    print("\n" + "=" * 80)
    print("AGGREGATE")
    print("=" * 80)

    normal_positive = (
        valid["normal_spread"] > 0
    ).sum()

    reversed_positive = (
        valid["reversed_spread"] > 0
    ).sum()

    print(
        f"Normal average spread   : "
        f"{valid['normal_spread'].mean():.4f}%"
    )

    print(
        f"Reversed average spread : "
        f"{valid['reversed_spread'].mean():.4f}%"
    )

    print(
        f"Normal positive windows : "
        f"{normal_positive}"
    )

    print(
        f"Reversed positive windows : "
        f"{reversed_positive}"
    )

    print("\nProduction scoring has NOT been changed.")


if __name__ == "__main__":
    main()