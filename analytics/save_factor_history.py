import sqlite3
from pathlib import Path

from analytics.stock_scoring import get_stock_scores
from analytics.stock_scoring_v2 import get_stock_scores_v2

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def save_factor_history():

    # -----------------------------
    # Load V1
    # -----------------------------

    v1 = get_stock_scores()

    # -----------------------------
    # Load V2
    # -----------------------------

    v2 = get_stock_scores_v2()

    # -----------------------------
    # Merge Models
    # -----------------------------

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

    conn = sqlite3.connect(str(DB_PATH))

    latest_date = conn.execute(
        """
        SELECT MAX(trade_date)
        FROM stocks_daily
        """
    ).fetchone()[0]

    # -----------------------------
    # Remove Existing Snapshot
    # -----------------------------

    conn.execute(
        """
        DELETE FROM factor_history
        WHERE trade_date = ?
        """,
        (latest_date,)
    )

    # -----------------------------
    # Save All Stocks
    # -----------------------------

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
                latest_date,
                row["symbol"],
                row["sector"],
                float(row["change_pct"]),
                float(row["sector_strength"]),
                float(row["position_pct"]),
                float(row["total_score"]),
                float(row["intelligence_score"])
            )
        )

    conn.commit()
    conn.close()

    print(
        f"\nSaved {len(df)} factor records "
        f"for {latest_date}"
    )


if __name__ == "__main__":

    save_factor_history()