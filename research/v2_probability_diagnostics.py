from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT = (
    BASE_DIR
    / "research"
    / "artifacts"
    / "historical_probability_oos_predictions.csv"
)


def main():
    print("\n" + "=" * 78)
    print("MARKETBOT TRACK C - PROBABILITY FAILURE DIAGNOSTICS")
    print("=" * 78)

    if not INPUT.exists():
        raise FileNotFoundError(f"Missing OOS predictions: {INPUT}")

    df = pd.read_csv(INPUT)

    print(f"Observations : {len(df):,}")
    print(
        f"Date range   : "
        f"{df['trade_date'].min()} -> {df['trade_date'].max()}"
    )

    print("\nACTUAL OUTCOMES")
    print(df["actual"].value_counts().reindex(
        ["DOWN", "FLAT", "UP"], fill_value=0
    ))

    print("\nMODEL PREDICTIONS")
    print(df["predicted"].value_counts().reindex(
        ["DOWN", "FLAT", "UP"], fill_value=0
    ))

    print("\nAVERAGE PROBABILITY BY ACTUAL OUTCOME")

    probability_columns = ["p_down", "p_flat", "p_up"]

    by_actual = (
        df.groupby("actual")[probability_columns]
        .mean()
        .reindex(["DOWN", "FLAT", "UP"])
    )

    print(by_actual.to_string(float_format=lambda x: f"{x:.4f}"))

    print("\nAVERAGE PROBABILITY BY PREDICTED OUTCOME")

    by_predicted = (
        df.groupby("predicted")[probability_columns]
        .mean()
        .reindex(["DOWN", "FLAT", "UP"])
    )

    print(by_predicted.to_string(float_format=lambda x: f"{x:.4f}"))

    print("\nACTUAL VS PREDICTED")

    confusion = pd.crosstab(
        df["actual"],
        df["predicted"],
        normalize="index",
    ).reindex(
        index=["DOWN", "FLAT", "UP"],
        columns=["DOWN", "FLAT", "UP"],
        fill_value=0,
    )

    print(
        confusion.to_string(
            float_format=lambda x: f"{x * 100:.2f}%"
        )
    )

    print("\nPROBABILITY SEPARATION")

    for actual in ["DOWN", "FLAT", "UP"]:
        subset = df[df["actual"] == actual]

        print(
            f"{actual:5} | "
            f"DOWN={subset.p_down.mean():.4f} | "
            f"FLAT={subset.p_flat.mean():.4f} | "
            f"UP={subset.p_up.mean():.4f}"
        )

    print("\nOOS FOLD PERFORMANCE")

    df["trade_date"] = pd.to_datetime(df["trade_date"])

    for fold_end, group in df.groupby("fold_train_end"):
        accuracy = (
            group["actual"] == group["predicted"]
        ).mean()

        print(
            f"{fold_end} | "
            f"rows={len(group):4d} | "
            f"accuracy={accuracy:.4f}"
        )

    print("\nRESEARCH ONLY")
    print("SQLite writes : NONE")
    print("Production changes : NONE")
    print("STATUS : SUCCESS")


if __name__ == "__main__":
    main()
