import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "market_intelligence.db"


def update_v2_outcomes():
    """
    Populate prediction_outcomes from completed V2 signal history.

    Contract:
    - Source: signal_history_v2
    - Outcome source: forward_returns.return_5d
    - Target: prediction_outcomes
    - No scoring, weights, prediction labels, or schema changes.
    - Only rows with a completed 5-day forward return are processed.
    """

    conn = sqlite3.connect(DB_PATH)

    required_tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    required = {
        "signal_history_v2",
        "forward_returns",
        "prediction_outcomes",
    }

    missing = sorted(required - required_tables)

    if missing:
        conn.close()
        raise RuntimeError(
            "V2 outcome tracking requires missing tables: "
            + ", ".join(missing)
        )

    rows = conn.execute(
        """
        SELECT
            s.trade_date,
            s.index_name,
            s.rank,
            s.intelligence_score,
            f.return_5d
        FROM signal_history_v2 AS s
        INNER JOIN forward_returns AS f
            ON DATE(f.trade_date) = DATE(s.trade_date)
           AND f.index_name = s.index_name
        WHERE f.return_5d IS NOT NULL
        ORDER BY s.trade_date, s.rank
        """
    ).fetchall()

    processed = 0

    for trade_date, index_name, rank, intelligence_score, return_5d in rows:
        conn.execute(
            """
            DELETE FROM prediction_outcomes
            WHERE prediction_date = ?
              AND index_name = ?
              AND rank = ?
            """,
            (
                trade_date,
                index_name,
                rank,
            ),
        )

        conn.execute(
            """
            INSERT INTO prediction_outcomes
            (
                prediction_date,
                index_name,
                rank,
                intelligence_score,
                return_5d
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                trade_date,
                index_name,
                rank,
                intelligence_score,
                return_5d,
            ),
        )

        processed += 1

    conn.commit()

    outcome_count = conn.execute(
        "SELECT COUNT(*) FROM prediction_outcomes"
    ).fetchone()[0]

    conn.close()

    print("\n" + "=" * 70)
    print("V2 OUTCOME TRACKER")
    print("=" * 70)
    print(f"Completed V2 outcomes processed : {processed:,}")
    print(f"Prediction outcome rows         : {outcome_count:,}")

    if processed == 0:
        print(
            "No completed 5-day outcomes are available yet. "
            "This is expected for recent signals."
        )

    print("STATUS: SUCCESS")

    return processed


if __name__ == "__main__":
    update_v2_outcomes()


