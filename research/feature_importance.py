import pandas as pd

from research.ml_dataset import build_ml_dataset


def feature_importance():

    df = build_ml_dataset()

    if df is None or df.empty:
        return

    correlation = (

        df.corr(numeric_only=True)["return_5d"]

        .sort_values(ascending=False)

        .round(3)

    )

    print()
    print("=" * 60)
    print("FEATURE IMPORTANCE")
    print("=" * 60)

    print(correlation)

    return correlation


if __name__ == "__main__":
    feature_importance()