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
    / "track_c_scenario_factor_interactions.csv"
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

MIN_OBSERVATIONS = 100


def main():

    print("\n" + "=" * 78)
    print("MARKETBOT TRACK C - SCENARIO × FACTOR INTERACTION DISCOVERY")
    print("=" * 78)

    df = pd.read_csv(INPUT)

    required = {
        "scenario",
        "label",
        "return_5d",
        *FEATURES,
    }

    missing = sorted(required - set(df.columns))

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    for column in FEATURES + ["return_5d"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(
        subset=[
            "scenario",
            "label",
            "return_5d",
            *FEATURES,
        ]
    ).copy()

    print(f"Observations : {len(df):,}")
    print(f"Scenarios    : {df['scenario'].nunique():,}")

    results = []

    for scenario in sorted(df["scenario"].unique()):

        scenario_df = df[df["scenario"] == scenario].copy()

        if len(scenario_df) < MIN_OBSERVATIONS:
            continue

        print(
            f"\nAnalyzing {scenario}: "
            f"{len(scenario_df):,} observations"
        )

        # Create within-scenario HIGH / LOW states
        # using the median. This avoids arbitrary thresholds.
        states = pd.DataFrame(index=scenario_df.index)

        for feature in FEATURES:
            median = scenario_df[feature].median()

            states[feature + "_state"] = (
                scenario_df[feature] >= median
            ).map({
                True: "HIGH",
                False: "LOW",
            })

        for feature_a, feature_b in combinations(FEATURES, 2):

            state_a = feature_a + "_state"
            state_b = feature_b + "_state"

            work = scenario_df[
                ["label", "return_5d"]
            ].copy()

            work["state_a"] = states[state_a]
            work["state_b"] = states[state_b]

            for state_a_value in ["LOW", "HIGH"]:
                for state_b_value in ["LOW", "HIGH"]:

                    subset = work[
                        (work["state_a"] == state_a_value)
                        & (work["state_b"] == state_b_value)
                    ]

                    if len(subset) < MIN_OBSERVATIONS:
                        continue

                    rates = (
                        subset["label"]
                        .value_counts(normalize=True)
                        .reindex(
                            ["DOWN", "FLAT", "UP"],
                            fill_value=0.0,
                        )
                    )

                    results.append(
                        {
                            "scenario": scenario,
                            "factor_a": feature_a,
                            "factor_b": feature_b,
                            "state_a": state_a_value,
                            "state_b": state_b_value,
                            "observations": len(subset),
                            "down_pct": rates["DOWN"] * 100,
                            "flat_pct": rates["FLAT"] * 100,
                            "up_pct": rates["UP"] * 100,
                            "outcome_separation": (
                                rates.max() - rates.min()
                            ) * 100,
                            "mean_return_5d": (
                                subset["return_5d"].mean()
                            ),
                            "median_return_5d": (
                                subset["return_5d"].median()
                            ),
                        }
                    )

    result = pd.DataFrame(results)

    if result.empty:
        raise RuntimeError(
            "No interaction groups met the minimum observation requirement."
        )

    result = result.sort_values(
        [
            "outcome_separation",
            "observations",
        ],
        ascending=[False, False],
    ).reset_index(drop=True)

    print("\nTOP FACTOR INTERACTIONS")

    print(
        result.head(40).to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT,
        index=False,
    )

    print(f"\nSaved: {OUTPUT}")

    print("\nRESEARCH ONLY")
    print("SQLite writes      : NONE")
    print("Production changes : NONE")
    print("Weight changes     : NONE")
    print("Weapon promotion   : NONE")
    print("STATUS             : SUCCESS")


if __name__ == "__main__":
    main()
