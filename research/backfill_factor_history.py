import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

sys.path.append(
    str(BASE_DIR / "analytics")
)

from analytics.stock_scoring import get_stock_scores
from analytics.stock_scoring_v2 import get_stock_scores_v2


def backfill_factor_history():

    conn = sqlite3.connect(str(DB_PATH))

    # --------------------------------
    # Clean Existing Data
    # --------------------------------

    conn.execute(
        """
        DELETE FROM factor_history
        """
    )

    conn.commit()

    # --------------------------------
    # Get Historical Dates
    # --------------------------------

    dates = conn.execute(
        """
        SELECT DISTINCT trade_date
        FROM stocks_daily
        ORDER BY trade_date
        """
    ).fetchall()

    dates = [x[0] for x in dates]

    total_saved = 0

    print(
        f"\nFound {len(dates)} trading dates."
    )

    # --------------------------------
    # Process Each Date
    # --------------------------------

    for trade_date in dates:

        try:

            v1 = get_stock_scores(
                trade_date
            )

            v2 = get_stock_scores_v2(
                trade_date
            )

            df = v1.merge(
                v2[
                    [
                        "symbol",
                        "position_pct",
                        "intelligence_score"
                    ]
                ],
                on="symbol",
                how="left"
            )

            for _, row in df.iterrows():

                conn.execute(
                    """
                    INSERT INTO factor_history
                    (
                        trade_date,
                        symbol,
                        sector,
                        change_pct,
                        sector_strength,
                        position_pct,
                        total_score,
                        intelligence_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trade_date,
                        row["symbol"],
                        row["sector"],
                        float(row["change_pct"]),
                        float(row["sector_strength"]),
                        float(row["position_pct"]),
                        float(row["total_score"]),
                        float(row["intelligence_score"])
                    )
                )

                total_saved += 1

            print(
                f"Processed: {trade_date}"
            )

        except Exception as e:

            print(
                f"Failed: {trade_date}"
            )

            print(e)

    conn.commit()
    conn.close()

    print(
        f"\nSaved {total_saved} "
        f"factor records."
    )


if __name__ == "__main__":

    backfill_factor_history()