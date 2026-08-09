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


def derive_weights(train):

    ic_values = {}

    for factor in FACTORS:

        ic_values[factor] = cross_sectional_ic(
            train,
            factor
        )

    abs_ic = {
        factor: abs(value)
        for factor, value in ic_values.items()
    }

    total = sum(abs_ic.values())

    if total == 0:

        weights = {
            factor: 1 / len(FACTORS)
            for factor in FACTORS
        }

    else:

        weights = {
            factor: abs_ic[factor] / total
            for factor in FACTORS
        }

    directions = {
        factor:
        1 if ic_values[factor] >= 0 else -1
        for factor in FACTORS
    }

    return weights, directions


def rank_score(df, weights, directions):

    df = df.copy()

    df["score"] = 0.0

    for factor in FACTORS:

        ranked = (
            df.groupby("prediction_date")[factor]
            .transform(
                lambda x: x.rank(
                    method="first"
                )
            )
        )

        max_rank = (
            df.groupby("prediction_date")[factor]
            .transform("count")
        )

        normalized = (
            (ranked - 1)
            /
            (max_rank - 1).replace(
                0,
                1
            )
        ) * 100

        if directions[factor] < 0:
            normalized = 100 - normalized

        df["score"] += (
            normalized *
            weights[factor]
        )

    return df


def evaluate_zones(df):

    rows = []

    for date, group in df.groupby(
        "prediction_date"
    ):

        if len(group) < 10:
            continue

        group = group.sort_values(
            "score"
        ).copy()

        n = len(group)

        group["zone"] = pd.cut(
            range(n),
            bins=[
                -1,
                n * 0.20,
                n * 0.40,
                n * 0.60,
                n * 0.80,
                n
            ],
            labels=[
                "Q1",
                "Q2",
                "Q3",
                "Q4",
                "Q5"
            ]
        )

        for zone, z in group.groupby(
            "zone",
            observed=True
        ):

            if z.empty:
                continue

            rows.append(
                {
                    "prediction_date": date,
                    "zone": zone,
                    "return_5d":
                        z["return_5d"].mean(),
                    "win_rate":
                        (z["return_5d"] > 0).mean()
                        * 100
                }
            )

    result = pd.DataFrame(rows)

    if result.empty:
        return None

    return (
        result.groupby("zone")
        .agg(
            observations=("return_5d", "count"),
            avg_return=("return_5d", "mean"),
            median_return=("return_5d", "median"),
            win_rate=("win_rate", "mean")
        )
    )


def main():

    print("\n" + "=" * 75)
    print("MARKETBOT SCORE-ZONE WALK-FORWARD")
    print("=" * 75)

    df = load_data()

    dates = sorted(
        df["prediction_date"].unique()
    )

    print(
        f"\nObservations : {len(df):,}"
    )

    print(
        f"Trading dates : {len(dates):,}"
    )

    train_size = 120
    test_size = 20
    step_size = 20

    all_windows = []

    window = 1

    for start in range(
        0,
        len(dates) - train_size - test_size + 1,
        step_size
    ):

        train_dates = dates[
            start:start + train_size
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

        weights, directions = derive_weights(
            train
        )

        test = rank_score(
            test,
            weights,
            directions
        )

        zones = evaluate_zones(test)

        if zones is None:
            continue

        zones["window"] = window

        print(
            f"\nWindow {window}"
        )

        print(
            f"Train : {train_dates[0]}"
            f" -> {train_dates[-1]}"
        )

        print(
            f"Test  : {test_dates[0]}"
            f" -> {test_dates[-1]}"
        )

        print(
            zones.round(4).to_string()
        )

        all_windows.append(zones)

        window += 1

    if not all_windows:
        print("\nNo valid windows.")
        return

    combined = pd.concat(
        all_windows
    )

    print("\n" + "=" * 75)
    print("AGGREGATE OUT-OF-SAMPLE ZONE RESULTS")
    print("=" * 75)

    print(
        combined
        .groupby("zone")
        .agg(
            observations=("observations", "sum"),
            avg_return=("avg_return", "mean"),
            median_return=("median_return", "mean"),
            avg_win_rate=("win_rate", "mean")
        )
        .round(4)
        .to_string()
    )

    print("\nProduction scoring has NOT been changed.")


if __name__ == "__main__":
    main()