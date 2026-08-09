import sqlite3
from pathlib import Path

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(
    str(BASE_DIR / "analytics")
    )

from analytics.stock_scoring_v2 import get_stock_scores_v2

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def save_prediction_history():

    df = get_stock_scores_v2()

    conn = sqlite3.connect(str(DB_PATH))

    conn.execute("""
    CREATE TABLE IF NOT EXISTS prediction_history (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        trade_date DATE,

        symbol TEXT,

        sector TEXT,

        rank INTEGER,

        grade TEXT,

        intelligence_score REAL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(trade_date, symbol)
    )
    """)

    latest_date = conn.execute(
        """
        SELECT MAX(trade_date)
        FROM stocks_daily
        """
    ).fetchone()[0]

    conn.execute(
        """
        DELETE FROM prediction_history
        WHERE trade_date = ?
        """,
        (latest_date,)
    )

    for rank, (_, row) in enumerate(
        df.iterrows(),
        start=1
    ):

        conn.execute(
            """
            INSERT INTO prediction_history
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
                latest_date,
                row["symbol"],
                row["sector"],
                rank,
                row["grade"],
                float(row["intelligence_score"])
            )
        )

    conn.commit()
    conn.close()

    print(
        f"\nSaved {len(df)} predictions "
        f"for {latest_date}"
    )


if __name__ == "__main__":

    save_prediction_history()
