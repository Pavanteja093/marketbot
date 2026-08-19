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
    / "track_c_feature_predictive_power.csv"
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
    print("MARKETBOT TRACK C - FEATURE PREDICTIVE POWER")
    print("=" * 78)

    df = pd.read_csv(INPUT)

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        errors="coerce"
    )

    for column in FEATURES + ["return_5d"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(
        subset=["trade_date", "label"] + FEATURES + ["return_5d"]
    ).copy()

    print(f"Observations : {len(df):,}")
    print(
        f"Dates        : "
        f"{df['trade_date'].min().date()} -> "
        f"{df['trade_date'].max().date()}"
    )

    results = []

    for feature in FEATURES:

        print(f"\nAnalyzing: {feature}")

        grouped = (
            df.groupby("label")[feature]
            .agg(["count", "mean", "median"])
            .reindex(["DOWN", "FLAT", "UP"])
        )

        down_mean = grouped.loc["DOWN", "mean"]
        flat_mean = grouped.loc["FLAT", "mean"]
        up_mean = grouped.loc["UP", "mean"]

        separation = max(
            down_mean,
            flat_mean,
            up_mean
        ) - min(
            down_mean,
            flat_mean,
            up_mean
        )

        correlation = df[feature].corr(
            df["return_5d"]
        )

        results.append(
            {
                "feature": feature,
                "down_mean": down_mean,
                "flat_mean": flat_mean,
                "up_mean": up_mean,
                "class_separation": separation,
                "return_5d_correlation": correlation,
            }
        )

    result = (
        pd.DataFrame(results)
        .sort_values(
            "class_separation",
            ascending=False
        )
        .reset_index(drop=True)
    )

    print("\nFEATURE RANKING")
    print(result.to_string(index=False))

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
    print("SQLite writes : NONE")
    print("Production changes : NONE")
    print("STATUS : SUCCESS")


if __name__ == "__main__":
    main()
