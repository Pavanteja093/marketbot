from __future__ import annotations

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
    / "track_c_scenario_feature_power.csv"
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


def main():

    print("\n" + "=" * 78)
    print("MARKETBOT TRACK C - SCENARIO CONDITIONED FEATURE POWER")
    print("=" * 78)

    df = pd.read_csv(INPUT)

    required = {
        "trade_date",
        "scenario",
        "scenario_id",
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
            "scenario_id",
            "label",
            "return_5d",
            *FEATURES,
        ]
    ).copy()

    print(f"Observations : {len(df):,}")
    print(f"Scenarios    : {df['scenario'].nunique():,}")

    results = []

    for scenario in sorted(df["scenario"].unique()):

        scenario_df = df[df["scenario"] == scenario]

        print(
            f"\nScenario: {scenario} "
            f"({len(scenario_df):,} observations)"
        )

        for feature in FEATURES:

            grouped = (
                scenario_df
                .groupby("label")[feature]
                .mean()
                .reindex(["DOWN", "FLAT", "UP"])
            )

            if grouped.isna().any():
                continue

            separation = (
                grouped.max() - grouped.min()
            )

            correlation = scenario_df[feature].corr(
                scenario_df["return_5d"]
            )

            results.append(
                {
                    "scenario": scenario,
                    "feature": feature,
                    "observations": len(scenario_df),
                    "down_mean": grouped["DOWN"],
                    "flat_mean": grouped["FLAT"],
                    "up_mean": grouped["UP"],
                    "class_separation": separation,
                    "return_5d_correlation": correlation,
                }
            )

    result = pd.DataFrame(results)

    result = result.sort_values(
        [
            "scenario",
            "class_separation",
        ],
        ascending=[True, False],
    ).reset_index(drop=True)

    print("\nTOP SCENARIO-CONDITIONED RELATIONSHIPS")

    print(
        result.head(30).to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT,
        index=False
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
