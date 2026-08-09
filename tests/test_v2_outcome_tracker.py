import sqlite3
import tempfile
import unittest
from pathlib import Path

from learning.v2_outcome_tracker import update_v2_outcomes


class V2OutcomeTrackerTests(unittest.TestCase):

    def test_completed_signal_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"

            conn = sqlite3.connect(db)

            conn.executescript("""
                CREATE TABLE signal_history_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date DATE,
                    index_name TEXT,
                    sector TEXT,
                    intelligence_score REAL,
                    rank INTEGER,
                    created_at TIMESTAMP
                );

                CREATE TABLE forward_returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date DATE,
                    index_name TEXT,
                    return_1d REAL,
                    return_5d REAL,
                    return_10d REAL,
                    return_20d REAL
                );

                CREATE TABLE prediction_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_date DATE,
                    index_name TEXT,
                    rank INTEGER,
                    intelligence_score REAL,
                    return_5d REAL,
                    created_at TIMESTAMP
                );
            """)

            conn.execute("""
                INSERT INTO signal_history_v2
                (trade_date, index_name, sector, intelligence_score, rank)
                VALUES ('2026-07-01', 'TEST.NS', 'TEST', 80.0, 1)
            """)

            conn.execute("""
                INSERT INTO forward_returns
                (trade_date, index_name, return_5d)
                VALUES ('2026-07-01', 'TEST.NS', 2.5)
            """)

            conn.commit()
            conn.close()

            # Point the module at the temporary database.
            import learning.v2_outcome_tracker as tracker
            original = tracker.DB_PATH
            tracker.DB_PATH = db

            try:
                self.assertEqual(tracker.update_v2_outcomes(), 1)

                conn = sqlite3.connect(db)
                row = conn.execute("""
                    SELECT prediction_date, index_name, rank,
                           intelligence_score, return_5d
                    FROM prediction_outcomes
                """).fetchone()
                conn.close()

                self.assertEqual(
                    row,
                    ("2026-07-01", "TEST.NS", 1, 80.0, 2.5),
                )
            finally:
                tracker.DB_PATH = original


if __name__ == "__main__":
    unittest.main()
