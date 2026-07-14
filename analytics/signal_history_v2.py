import sqlite3
from pathlib import Path

from analytics.stock_scoring_v2 import get_stock_scores_v2

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def save_signals_v2():

    df = get_stock_scores_v2()

    conn = sqlite3.connect(str(DB_PATH))

    latest_date = conn.execute(
        """
        SELECT MAX(trade_date)
        FROM stocks_daily
        """
    ).fetchone()[0]

    # ----------------------------------
    # Remove Existing Signals
    # ----------------------------------

    conn.execute(
        """
        DELETE FROM signal_history_v2
        WHERE trade_date = ?
        """,
        (latest_date,)
    )

    # ----------------------------------
    # Save Top 10 Signals
    # ----------------------------------

    top10 = df.head(10)

    for rank, (_, row) in enumerate(
        top10.iterrows(),
        start=1
    ):

        conn.execute(
            """
            INSERT INTO signal_history_v2
            (
                trade_date,
                symbol,
                sector,
                intelligence_score,
                rank
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                latest_date,
                row["symbol"],
                row["sector"],
                float(row["intelligence_score"]),
                rank
            )
        )

    conn.commit()

    conn.close()

    print(
        f"\nSaved {len(top10)} V2 signals "
        f"for {latest_date}"
    )


if __name__ == "__main__":

    save_signals_v2()