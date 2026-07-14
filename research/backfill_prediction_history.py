import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"

sys.path.append(
    str(BASE_DIR / "analytics")
)

from analytics.stock_scoring_v2 import get_stock_scores_v2


def backfill_predictions():

    conn = sqlite3.connect(str(DB_PATH))

    conn.execute(
    """
    DELETE FROM prediction_history
    """
    )

    # -----------------------------------
    # Get All Historical Dates
    # -----------------------------------

    dates = conn.execute(
        """
        SELECT DISTINCT trade_date
        FROM stocks_daily
        ORDER BY trade_date
        """
    ).fetchall()

    dates = [x[0] for x in dates]

    print(
        f"\nFound {len(dates)} trading dates."
    )

    total_saved = 0

    # -----------------------------------
    # Process Each Date
    # -----------------------------------

    for trade_date in dates:

        try:

            df = get_stock_scores_v2(
                trade_date
            )

            if len(df) == 0:
                continue

            # -----------------------------
            # Ranking
            # -----------------------------

            df = df.sort_values(
                "intelligence_score",
                ascending=False
            )

            df = df.reset_index(
                drop=True
            )

            # -----------------------------
            # Save Predictions
            # -----------------------------

            for rank, (_, row) in enumerate(
                df.iterrows(),
                start=1
            ):

                conn.execute(
                    """
                    INSERT OR IGNORE INTO
                    prediction_history
                    (
                        trade_date,
                        symbol,
                        sector,
                        rank,
                        grade,
                        intelligence_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trade_date,
                        row["symbol"],
                        row["sector"],
                        rank,
                        row["grade"],
                        float(
                            row["intelligence_score"]
                        )
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
        f"historical predictions."
    )


if __name__ == "__main__":

    backfill_predictions()