import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def validate_learning_dataset():

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql(
        "SELECT * FROM learning_dataset",
        conn
    )

    conn.close()

    print("\n" + "=" * 60)
    print("LEARNING DATASET VALIDATION")
    print("=" * 60)

    print(f"\nTotal Rows : {len(df)}")
    print(f"Total Columns : {len(df.columns)}")

    print("\n" + "-" * 60)
    print("Missing Values")
    print("-" * 60)

    missing = df.isna().sum()

    for col, count in missing.items():
        pct = (count / len(df)) * 100
        print(f"{col:25} {count:6} ({pct:6.2f}%)")

    print("\n" + "-" * 60)
    print("Unique Values")
    print("-" * 60)

    for col in df.columns:
        print(f"{col:25} {df[col].nunique(dropna=True)}")

    print("\n" + "-" * 60)
    print("Return Availability")
    print("-" * 60)

    for col in [
        "return_1d",
        "return_5d",
        "return_10d",
        "return_20d"
    ]:
        valid = df[col].notna().sum()
        pct = valid / len(df) * 100

        print(f"{col:20} {valid:6} ({pct:6.2f}%)")

    print("\n" + "-" * 60)
    print("Numeric Summary")
    print("-" * 60)

    summary = df.describe(include="all").T

    print(summary)

    summary.to_csv(
        BASE_DIR / "learning" / "learning_dataset_summary.csv"
    )


if __name__ == "__main__":
    validate_learning_dataset()