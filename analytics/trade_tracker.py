import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def save_recommendations(portfolio):

    if len(portfolio) == 0:
        return

    conn = sqlite3.connect(str(DB_PATH))

    for _, row in portfolio.iterrows():

        conn.execute(
            """
            INSERT INTO daily_recommendations (

                trade_date,
                symbol,
                regime,
                expected_return,
                confidence,
                weight_pct

            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                row["symbol"],
                row["regime"],
                float(row["expected_return"]),
                row["confidence"],
                float(row["weight_pct"])
            )
        )

    conn.commit()
    conn.close()