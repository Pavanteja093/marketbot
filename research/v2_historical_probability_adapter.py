from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from research.v2_probability_forecaster import (
    CLASSES,
    ForecastConfig,
    evaluate_probabilities,
    walk_forward,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = (
    BASE_DIR / "research" / "artifacts"
    / "historical_probability_dataset.csv"
)
DEFAULT_OUTPUT = (
    BASE_DIR / "research" / "artifacts"
    / "historical_probability_oos_predictions.csv"
)

REQUIRED_COLUMNS = {
    "trade_date",
    "index_name",
    "change_pct",
    "intelligence_score",
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
    "return_5d",
    "label",
}

FEATURE_COLUMNS = [
    "change_pct",
    "intelligence_score",
    "relative_strength",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "liquidity_score",
]

TARGET_COLUMNS = {
    "return_5d",
    "label",
}


def load_historical_dataset(
    dataset_path: Path = DEFAULT_DATASET,
) -> tuple[pd.DataFrame, list[str]]:
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Historical probability dataset not found: {dataset_path}"
        )

    df = pd.read_csv(dataset_path)

    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(
            "Historical probability dataset is missing required columns: "
            + ", ".join(missing)
        )

    forbidden_features = sorted(
        TARGET_COLUMNS.intersection(FEATURE_COLUMNS)
    )
    if forbidden_features:
        raise RuntimeError(
            "Target leakage detected in feature configuration: "
            + ", ".join(forbidden_features)
        )

    df["trade_date"] = pd.to_datetime(
        df["trade_date"],
        errors="coerce",
    )

    for column in FEATURE_COLUMNS + ["return_5d"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["label"] = df["label"].astype(str)

    # Compatibility alias for the existing V2 walk-forward engine.
    df["future_return"] = df["return_5d"]

    invalid_labels = sorted(
        set(df["label"].dropna()) - set(CLASSES)
    )
    if invalid_labels:
        raise ValueError(
            "Unexpected labels found: "
            + ", ".join(invalid_labels)
        )

    before = len(df)

    df = df.dropna(
        subset=[
            "trade_date",
            "index_name",
            *FEATURE_COLUMNS,
            "return_5d",
            "label",
        ]
    ).copy()

    if len(df) < before:
        print(
            f"Rows excluded after validation : {before - len(df):,}"
        )

    if df.empty:
        raise ValueError(
            "Historical probability dataset contains no usable rows."
        )

    # Explicit chronological ordering.
    df = (
        df.sort_values(
            ["trade_date", "index_name"]
        )
        .reset_index(drop=True)
    )

    return df, FEATURE_COLUMNS.copy()


def run_research(
    dataset_path: Path = DEFAULT_DATASET,
    output_path: Path | None = DEFAULT_OUTPUT,
    config: ForecastConfig | None = None,
) -> dict:
    config = config or ForecastConfig()

    print("\n" + "=" * 78)
    print("MARKETBOT TRACK C - HISTORICAL PROBABILITY FORECASTER")
    print("=" * 78)
    print("RESEARCH ONLY")
    print(f"Dataset                    : {dataset_path}")

    df, feature_columns = load_historical_dataset(dataset_path)

    print(f"Observations               : {len(df):,}")
    print(
        f"Trading dates              : "
        f"{df['trade_date'].dt.normalize().nunique():,}"
    )
    print(
        f"Symbols                    : "
        f"{df['index_name'].nunique():,}"
    )
    print(
        f"Date range                 : "
        f"{df['trade_date'].min().date()} -> "
        f"{df['trade_date'].max().date()}"
    )
    print(
        f"Features                   : "
        f"{', '.join(feature_columns)}"
    )
    print(f"Target                     : label")
    print(f"Underlying target          : return_5d")
    print(
        f"FLAT threshold             : "
        f"±{config.flat_threshold_pct:.2f}%"
    )

    print("\nClass distribution:")
    print(df["label"].value_counts().reindex(CLASSES, fill_value=0))

    predictions, folds = walk_forward(
        df,
        feature_columns,
        config,
    )

    metrics = evaluate_probabilities(predictions)

    print("\n" + "-" * 78)
    print("WALK-FORWARD RESULTS")
    print("-" * 78)

    for fold in folds:
        print(
            f"{fold['train_start']} -> {fold['train_end']} | "
            f"test {fold['test_start']} -> {fold['test_end']} | "
            f"{fold['status']}"
        )

    print("\n" + "-" * 78)
    print("OOS PROBABILITY METRICS")
    print("-" * 78)

    for key, value in metrics.items():
        if value is None:
            print(f"{key:<24}: N/A")
        elif isinstance(value, float):
            print(f"{key:<24}: {value:.6f}")
        else:
            print(f"{key:<24}: {value}")

    if output_path is not None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        predictions.to_csv(
            output_path,
            index=False,
        )
        print(
            f"\nOOS predictions written: {output_path}"
        )

    print("\nPRODUCTION IMPACT       : NONE")
    print("SQLITE WRITES           : NONE")
    print("TARGET LEAKAGE          : BLOCKED")
    print("STATUS                  : SUCCESS")

    return {
        "dataset": df,
        "feature_columns": feature_columns,
        "predictions": predictions,
        "folds": folds,
        "metrics": metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "MarketBot Track-C historical probability "
            "research adapter."
        )
    )

    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )
    parser.add_argument(
        "--min-train-dates",
        type=int,
        default=60,
    )
    parser.add_argument(
        "--test-dates",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--step-dates",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--min-class-count",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--flat-threshold",
        type=float,
        default=0.5,
    )

    args = parser.parse_args()

    config = ForecastConfig(
        flat_threshold_pct=args.flat_threshold,
        horizon="return_5d",
        min_train_dates=args.min_train_dates,
        test_dates=args.test_dates,
        step_dates=args.step_dates,
        min_class_count=args.min_class_count,
    )

    run_research(
        dataset_path=Path(args.dataset),
        output_path=Path(args.output),
        config=config,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())




