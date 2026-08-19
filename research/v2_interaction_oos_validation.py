from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "historical_probability_dataset.csv"
)

OUTPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "track_c_interaction_oos_validation.csv"
)

FEATURES = [
    "change_pct",
    "intelligence_score",
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]

CLASSES = ["DOWN", "FLAT", "UP"]

MIN_TRAIN_DATES = 60
TEST_DATES = 20
STEP_DATES = 20

MIN_OOS_OBSERVATIONS = 20


def assign_states(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_a: str,
    feature_b: str,
):
    """
    Learn HIGH/LOW thresholds strictly from training data,
    then apply those thresholds to both train and future test data.
    """

    threshold_a = train[feature_a].median()
    threshold_b = train[feature_b].median()

    train = train.copy()
    test = test.copy()

    train["state_a"] = (
        train[feature_a] >= threshold_a
    ).map({
        True: "HIGH",
        False: "LOW",
    })

    train["state_b"] = (
        train[feature_b] >= threshold_b
    ).map({
        True: "HIGH",
        False: "LOW",
    })

    test["state_a"] = (
        test[feature_a] >= threshold_a
    ).map({
        True: "HIGH",
        False: "LOW",
    })

    test["state_b"] = (
        test[feature_b] >= threshold_b
    ).map({
        True: "HIGH",
        False: "LOW",
    })

    return train, test, threshold_a, threshold_b


def main():

    print("\n" + "=" * 78)
    print("MARKETBOT TRACK C - INTERACTION OOS VALIDATION")
    print("=" * 78)

    df = pd.read_csv(INPUT)

    required = {
        "trade_date",
        "scenario",
        "label",
        "return_5d",
        *FEATURES,
    }

    missing = sorted(
        required - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        errors="coerce",
    )

    for column in FEATURES + ["return_5d"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["label"] = df["label"].astype(str)

    df = (
        df.dropna(
            subset=[
                "trade_date",
                "scenario",
                "label",
                "return_5d",
                *FEATURES,
            ]
        )
        .sort_values(
            ["trade_date", "index_name"]
            if "index_name" in df.columns
            else ["trade_date"]
        )
        .reset_index(drop=True)
    )

    dates = sorted(
        df["trade_date"]
        .dt.normalize()
        .unique()
    )

    print(
        f"Observations : {len(df):,}"
    )

    print(
        f"Trading dates: {len(dates):,}"
    )

    print(
        f"Scenarios    : "
        f"{df['scenario'].nunique():,}"
    )

    folds = []

    start = MIN_TRAIN_DATES

    while start < len(dates):

        test_end = min(
            start + TEST_DATES,
            len(dates),
        )

        train_dates = dates[:start]

        test_dates = dates[start:test_end]

        train = df[
            df["trade_date"]
            .dt.normalize()
            .isin(train_dates)
        ].copy()

        test = df[
            df["trade_date"]
            .dt.normalize()
            .isin(test_dates)
        ].copy()

        if test.empty:
            break

        print(
            f"\nOOS fold: "
            f"{train_dates[0].date()} -> "
            f"{train_dates[-1].date()} | "
            f"test "
            f"{test_dates[0].date()} -> "
            f"{test_dates[-1].date()}"
        )

        for feature_a, feature_b in combinations(
            FEATURES,
            2,
        ):

            train_states, test_states, threshold_a, threshold_b = (
                assign_states(
                    train,
                    test,
                    feature_a,
                    feature_b,
                )
            )

            for scenario in sorted(
                test_states["scenario"].unique()
            ):

                scenario_test = test_states[
                    test_states["scenario"] == scenario
                ]

                for state_a in ["LOW", "HIGH"]:

                    for state_b in ["LOW", "HIGH"]:

                        subset = scenario_test[
                            (scenario_test["state_a"] == state_a)
                            &
                            (scenario_test["state_b"] == state_b)
                        ]

                        if len(subset) < MIN_OOS_OBSERVATIONS:
                            continue

                        counts = (
                            subset["label"]
                            .value_counts()
                            .reindex(
                                CLASSES,
                                fill_value=0,
                            )
                        )

                        results = {
                            "scenario": scenario,
                            "factor_a": feature_a,
                            "factor_b": feature_b,
                            "state_a": state_a,
                            "state_b": state_b,
                            "train_start": train_dates[0].date().isoformat(),
                            "train_end": train_dates[-1].date().isoformat(),
                            "test_start": test_dates[0].date().isoformat(),
                            "test_end": test_dates[-1].date().isoformat(),
                            "observations": int(len(subset)),
                            "down_count": int(counts["DOWN"]),
                            "flat_count": int(counts["FLAT"]),
                            "up_count": int(counts["UP"]),
                            "down_pct": float(
                                counts["DOWN"]
                                / len(subset)
                                * 100
                            ),
                            "flat_pct": float(
                                counts["FLAT"]
                                / len(subset)
                                * 100
                            ),
                            "up_pct": float(
                                counts["UP"]
                                / len(subset)
                                * 100
                            ),
                            "mean_return_5d": float(
                                subset["return_5d"].mean()
                            ),
                            "median_return_5d": float(
                                subset["return_5d"].median()
                            ),
                            "threshold_a": float(threshold_a),
                            "threshold_b": float(threshold_b),
                        }

                        folds.append(results)

        start += STEP_DATES

    if not folds:
        raise RuntimeError(
            "No interaction produced sufficient OOS observations."
        )

    fold_df = pd.DataFrame(folds)

    group_columns = [
        "scenario",
        "factor_a",
        "factor_b",
        "state_a",
        "state_b",
    ]

    # IMPORTANT:
    # Aggregate counts, not percentages.
    aggregate = (
        fold_df
        .groupby(
            group_columns,
            as_index=False,
        )
        .agg(
            observations=("observations", "sum"),
            down_count=("down_count", "sum"),
            flat_count=("flat_count", "sum"),
            up_count=("up_count", "sum"),
            mean_return_5d=("mean_return_5d", "mean"),
            median_return_5d=("median_return_5d", "mean"),
            oos_folds=("test_start", "count"),
        )
    )

    aggregate["down_pct"] = (
        aggregate["down_count"]
        / aggregate["observations"]
        * 100
    )

    aggregate["flat_pct"] = (
        aggregate["flat_count"]
        / aggregate["observations"]
        * 100
    )

    aggregate["up_pct"] = (
        aggregate["up_count"]
        / aggregate["observations"]
        * 100
    )

    aggregate["dominant_outcome"] = (
        aggregate[
            [
                "down_pct",
                "flat_pct",
                "up_pct",
            ]
        ]
        .idxmax(axis=1)
        .str.replace(
            "_pct",
            "",
            regex=False,
        )
        .str.upper()
    )

    aggregate["dominant_probability_pct"] = (
        aggregate[
            [
                "down_pct",
                "flat_pct",
                "up_pct",
            ]
        ].max(axis=1)
    )

    # OOS stability:
    # A relationship appearing in only one fold is weaker
    # than one repeating across several independent folds.
    aggregate["oos_stability"] = aggregate[
        "oos_folds"
    ].map(
        lambda x:
            "REPEATED"
            if x >= 3
            else "EARLY"
            if x >= 2
            else "SINGLE_FOLD"
    )

    aggregate = aggregate.sort_values(
        [
            "dominant_probability_pct",
            "oos_folds",
            "observations",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    ).reset_index(drop=True)

    print("\n" + "-" * 78)
    print("TOP OOS INTERACTIONS")
    print("-" * 78)

    print(
        aggregate.head(40).to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    aggregate.to_csv(
        OUTPUT,
        index=False,
    )

    print(
        f"\nSaved: {OUTPUT}"
    )

    print("\nRESEARCH ONLY")
    print("SQLite writes      : NONE")
    print("Production changes : NONE")
    print("Weight changes     : NONE")
    print("Weapon promotion   : NONE")
    print("STATUS             : SUCCESS")


if __name__ == "__main__":
    main()
