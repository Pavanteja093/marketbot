import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def backfill_prediction_history():

    print("\n" + "=" * 70)
    print("MARKETBOT HISTORICAL PREDICTION BACKFILL")
    print("=" * 70)

    conn = sqlite3.connect(str(DB_PATH))

    # --------------------------------------------------
    # LOAD HISTORICAL FACTOR SCORES
    # --------------------------------------------------

    df = pd.read_sql(
        """
        SELECT
            DATE(trade_date) AS trade_date,
            index_name,
            intelligence_score,
            rs_grade,
            trend_grade,
            momentum_grade,
            volatility_grade,
            liquidity_grade

        FROM factor_history

        WHERE intelligence_score IS NOT NULL

        ORDER BY trade_date, intelligence_score DESC
        """,
        conn
    )

    print(
        f"\nFactor records loaded : {len(df):,}"
    )

    if df.empty:

        conn.close()

        print("\nNo factor history available.")
        return

    # --------------------------------------------------
    # CREATE TABLE IF NEEDED
    # --------------------------------------------------

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            trade_date DATE,

            index_name TEXT,

            sector TEXT,

            rank INTEGER,

            grade TEXT,

            intelligence_score REAL,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            prediction TEXT,

            confidence REAL,

            risk TEXT,

            future_return_5d REAL,

            future_return_20d REAL,

            prediction_correct INTEGER,

            UNIQUE(trade_date, index_name)
        )
        """
    )

    # --------------------------------------------------
    # BACKFILL DATE BY DATE
    # --------------------------------------------------

    total_saved = 0

    dates = df["trade_date"].dropna().unique()

    print(
        f"Trading dates         : {len(dates):,}"
    )

    for trade_date in dates:

        day = df[
            df["trade_date"] == trade_date
        ].copy()

        day = day.sort_values(
            "intelligence_score",
            ascending=False
        ).reset_index(drop=True)

        day["rank"] = (
            day.index + 1
        )

        # --------------------------------------------------
        # INSERT HISTORICAL RANKINGS
        # --------------------------------------------------

        for _, row in day.iterrows():

            grade = None

            # Use the existing strongest grade available.
            for candidate in [
                row.get("trend_grade"),
                row.get("momentum_grade"),
                row.get("volatility_grade"),
                row.get("liquidity_grade"),
                row.get("rs_grade"),
            ]:

                if pd.notna(candidate):

                    grade = str(candidate)

                    break

            conn.execute(
                """
                INSERT OR REPLACE INTO
                prediction_history
                (
                    trade_date,
                    index_name,
                    sector,
                    rank,
                    grade,
                    intelligence_score,
                    prediction,
                    confidence,
                    risk
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_date,
                    row["index_name"],
                    None,
                    int(row["rank"]),
                    grade,
                    float(
                        row["intelligence_score"]
                    ),
                    None,
                    None,
                    None
                )
            )

            total_saved += 1

        if (
            total_saved > 0
            and (
                len(
                    df[
                        df["trade_date"]
                        <= trade_date
                    ]
                )
                % 1000 == 0
            )
        ):

            conn.commit()

    conn.commit()

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM prediction_history
        """
    ).fetchone()[0]

    dates_count = conn.execute(
        """
        SELECT COUNT(DISTINCT trade_date)
        FROM prediction_history
        """
    ).fetchone()[0]

    symbols = conn.execute(
        """
        SELECT COUNT(DISTINCT index_name)
        FROM prediction_history
        """
    ).fetchone()[0]

    date_range = conn.execute(
        """
        SELECT
            MIN(trade_date),
            MAX(trade_date)
        FROM prediction_history
        """
    ).fetchone()

    conn.close()

    print("\n" + "=" * 70)
    print("HISTORICAL PREDICTION BACKFILL COMPLETE")
    print("=" * 70)

    print(
        f"Records written       : {total_saved:,}"
    )

    print(
        f"Database rows         : {total:,}"
    )

    print(
        f"Trading dates         : {dates_count:,}"
    )

    print(
        f"Symbols               : {symbols:,}"
    )

    print(
        f"Date range            : "
        f"{date_range[0]} → {date_range[1]}"
    )

    print("=" * 70)


if __name__ == "__main__":

    backfill_prediction_history()