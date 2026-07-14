import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def update_outcomes():

    conn = sqlite3.connect(str(DB_PATH))

    # -----------------------------
    # Create Table If Needed
    # -----------------------------

    conn.execute("""
    CREATE TABLE IF NOT EXISTS prediction_outcomes (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        prediction_date DATE,

        symbol TEXT,

        rank INTEGER,

        intelligence_score REAL,

        return_5d REAL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        UNIQUE(prediction_date, symbol)
    )
    """)

    # -----------------------------
    # Join Predictions To Outcomes
    # -----------------------------

    query = """
    SELECT

        p.trade_date AS prediction_date,
        p.symbol,
        p.rank,
        p.intelligence_score,

        f.return_5d

    FROM prediction_history p

    JOIN forward_returns f

        ON p.trade_date = f.trade_date
       AND p.symbol = f.symbol

    WHERE f.return_5d IS NOT NULL
    """

    df = pd.read_sql(query, conn)

    # -----------------------------
    # Clear Existing
    # -----------------------------

    conn.execute(
        "DELETE FROM prediction_outcomes"
    )

    # -----------------------------
    # Save Results
    # -----------------------------

    for _, row in df.iterrows():

        conn.execute(
            """
            INSERT OR REPLACE INTO
            prediction_outcomes
            (
                prediction_date,
                symbol,
                rank,
                intelligence_score,
                return_5d
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["prediction_date"],
                row["symbol"],
                int(row["rank"]),
                float(row["intelligence_score"]),
                float(row["return_5d"])
            )
        )

    conn.commit()
    conn.close()

    print(
        f"\nSaved {len(df)} prediction outcomes."
    )


if __name__ == "__main__":

    update_outcomes()