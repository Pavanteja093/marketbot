import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


# ============================================================
# CONFIGURATION
# ============================================================

MIN_DATES_REQUIRED = 10
WINDOW_DATES = 20


# ============================================================
# LOAD MATCHED RESEARCH DATA
# ============================================================

def load_research_data():

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            f.trade_date,
            f.index_name,
            f.intelligence_score,
            r.return_1d,
            r.return_5d,
            r.return_10d,
            r.return_20d

        FROM factor_history f

        INNER JOIN forward_returns r
            ON DATE(f.trade_date) = DATE(r.trade_date)
            AND f.index_name = r.index_name

        WHERE f.intelligence_score IS NOT NULL

        ORDER BY
            DATE(f.trade_date),
            f.index_name
    """

    df = pd.read_sql(query, conn)

    conn.close()

    if not df.empty:
        df["trade_date"] = pd.to_datetime(df["trade_date"])

        numeric_columns = [
            "intelligence_score",
            "return_1d",
            "return_5d",
            "return_10d",
            "return_20d",
        ]

        for column in numeric_columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


# ============================================================
# WALK-FORWARD VALIDATION
# ============================================================

def walk_forward_validation():

    print("\n" + "=" * 70)
    print("MARKETBOT WALK-FORWARD VALIDATION")
    print("=" * 70)

    df = load_research_data()

    # --------------------------------------------------------
    # BASIC DATA CHECK
    # --------------------------------------------------------

    if df.empty:

        print("\nNo matched factor/outcome data found.")

        print("\nRequired relationship:")
        print("factor_history")
        print("       +")
        print("forward_returns")
        print("       ↓")
        print("matched trade_date + index_name")

        return

    unique_dates = (
        df["trade_date"]
        .dt.date
        .nunique()
    )

    unique_symbols = df["index_name"].nunique()

    print(f"\nMatched Records : {len(df)}")
    print(f"Trading Dates   : {unique_dates}")
    print(f"Symbols         : {unique_symbols}")

    print(
        f"Date Range      : "
        f"{df['trade_date'].min().date()} "
        f"to "
        f"{df['trade_date'].max().date()}"
    )

    # --------------------------------------------------------
    # CHECK WHETHER REAL TEMPORAL VALIDATION IS POSSIBLE
    # --------------------------------------------------------

    if unique_dates < MIN_DATES_REQUIRED:

        print("\n" + "!" * 70)
        print("INSUFFICIENT HISTORICAL FACTOR DATA")
        print("!" * 70)

        print(
            f"\nOnly {unique_dates} trading date(s) "
            f"are currently available in factor_history."
        )

        print(
            f"\nAt least {MIN_DATES_REQUIRED} trading dates "
            f"are required for temporal validation."
        )

        print("\nCurrent data situation:")

        print(
            f"  factor_history     : "
            f"{len(df)} matched records"
        )

        print(
            f"  forward_returns    : "
            f"12,244 records available"
        )

        print(
            "\nThe forward-return dataset is ready."
        )

        print(
            "The historical factor dataset is the "
            "current bottleneck."
        )

        print(
            "\nNEXT REQUIRED STEP:"
        )

        print(
            "Backfill factor_history across the "
            "historical stocks_daily period."
        )

        return

    # --------------------------------------------------------
    # WALK-FORWARD WINDOWS
    # --------------------------------------------------------

    dates = sorted(
        df["trade_date"].dt.normalize().unique()
    )

    results = []

    for end_position in range(
        WINDOW_DATES,
        len(dates) + 1,
    ):

        window_dates = dates[
            end_position - WINDOW_DATES:
            end_position
        ]

        sample = df[
            df["trade_date"]
            .dt.normalize()
            .isin(window_dates)
        ].copy()

        sample = sample.dropna(
            subset=[
                "intelligence_score",
                "return_5d",
            ]
        )

        if len(sample) < 20:
            continue

        correlation = sample[
            "intelligence_score"
        ].corr(
            sample["return_5d"]
        )

        results.append(
            {
                "window_end": window_dates[-1],
                "observations": len(sample),
                "correlation_5d": correlation,
                "mean_return_5d": sample[
                    "return_5d"
                ].mean(),
                "median_return_5d": sample[
                    "return_5d"
                ].median(),
            }
        )

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    if not results:

        print(
            "\nNo valid walk-forward windows "
            "could be constructed."
        )

        return

    result = pd.DataFrame(results)

    result["window_end"] = pd.to_datetime(
        result["window_end"]
    )

    print("\n" + "=" * 70)
    print("WALK-FORWARD RESULTS")
    print("=" * 70)

    print(
        result.to_string(index=False)
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    valid_correlations = result[
        "correlation_5d"
    ].dropna()

    if not valid_correlations.empty:

        print("\n" + "=" * 70)
        print("WALK-FORWARD SUMMARY")
        print("=" * 70)

        print(
            f"\nWindows Tested       : "
            f"{len(result)}"
        )

        print(
            f"Average Correlation  : "
            f"{valid_correlations.mean():.4f}"
        )

        print(
            f"Median Correlation   : "
            f"{valid_correlations.median():.4f}"
        )

        print(
            f"Positive Windows     : "
            f"{(valid_correlations > 0).sum()}"
        )

        print(
            f"Negative Windows     : "
            f"{(valid_correlations < 0).sum()}"
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    walk_forward_validation()