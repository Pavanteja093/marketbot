import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def performance_report():

    conn = sqlite3.connect(str(DB_PATH))

    query = """
    SELECT

        p.trade_date,
        p.symbol,
        p.sector,
        p.rank,
        p.grade,
        p.intelligence_score,

        f.return_5d,
        f.return_10d,
        f.return_20d

    FROM prediction_history p

    JOIN forward_returns f

        ON date(p.trade_date) = date(f.trade_date)
        AND p.symbol = f.symbol

    WHERE
        f.return_5d IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    df["intelligence_score"] = pd.to_numeric(
        df["intelligence_score"],
        errors="coerce"
    )

    df["return_5d"] = pd.to_numeric(
        df["return_5d"],
        errors="coerce"
    )

    df["return_10d"] = pd.to_numeric(
        df["return_10d"],
        errors="coerce"
    )

    df["return_20d"] = pd.to_numeric(
        df["return_20d"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "intelligence_score",
            "return_5d"
        ]
    )

    print("\nDEBUG")
    print(df.head())

    print("\nDTYPES")
    print(df.dtypes)

    print("\nNULL COUNTS")
    print(df.isnull().sum())

    df["return_5d"] = pd.to_numeric(
        df["return_5d"],
        errors="coerce"
    )

    df["return_10d"] = pd.to_numeric(
        df["return_10d"],
        errors="coerce"
    )

    df["return_20d"] = pd.to_numeric(
        df["return_20d"],
        errors="coerce"
    )

    df["intelligence_score"] = pd.to_numeric(
        df["intelligence_score"],
        errors="coerce"
    )
    conn.close()

    print("\n" + "=" * 70)
    print("MARKETBOT PERFORMANCE REPORT")
    print("=" * 70)

    print("\nDATASET")

    print(f"Predictions : {len(df):,}")

    print(
        f"Avg 5D Return  : {df['return_5d'].mean():.2f}%"
    )

    print(
        f"Avg 10D Return : {df['return_10d'].mean():.2f}%"
    )

    print(
        f"Avg 20D Return : {df['return_20d'].mean():.2f}%"
    )

    # --------------------------------
    # Top Rank Analysis
    # --------------------------------

    print("\n" + "-" * 70)
    print("TOP RANK ANALYSIS")
    print("-" * 70)

    top1 = df[df["rank"] == 1]

    if len(top1):

        print(
            f"Rank #1 Avg 5D Return : "
            f"{top1['return_5d'].mean():.2f}%"
        )

    top5 = df[df["rank"] <= 5]

    print(
        f"Top 5 Avg 5D Return   : "
        f"{top5['return_5d'].mean():.2f}%"
    )

    top10 = df[df["rank"] <= 10]

    print(
        f"Top10 Avg 5D Return   : "
        f"{top10['return_5d'].mean():.2f}%"
    )

    # --------------------------------
    # Grade Analysis
    # --------------------------------

    print("\n" + "-" * 70)
    print("GRADE ANALYSIS")
    print("-" * 70)
    print(df.dtypes)

    grade_stats = (
        df.groupby("grade")
        ["return_5d"]
        .mean()
        .sort_values(
            ascending=False
        )
    )

    print(
        grade_stats.astype(float).round(2)
    )

    # --------------------------------
    # Sector Analysis
    # --------------------------------

    print("\n" + "-" * 70)
    print("SECTOR ANALYSIS")
    print("-" * 70)

    sector_stats = (
        df.groupby("sector")
        ["return_5d"]
        .mean()
        .sort_values(
            ascending=False
        )
    )

    print(
        sector_stats.astype(float).round(2)
    )

    # --------------------------------
    # Score Bucket Analysis
    # --------------------------------

    print("\n" + "-" * 70)
    print("SCORE BUCKET ANALYSIS")
    print("-" * 70)

    df["bucket"] = pd.qcut(
        df["intelligence_score"],
        q=5,
        labels=[
            "Bottom20",
            "20-40",
            "40-60",
            "60-80",
            "Top20"
        ],
        duplicates="drop"
    )

    bucket_stats = (
        df.groupby("bucket")
        ["return_5d"]
        .mean()
    )

    print(
        bucket_stats.astype(float).round(2)
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":

    performance_report()