import sqlite3
import tempfile
import unittest
from pathlib import Path

from research.rebuild_market_scenario_history import rebuild


class ScenarioHistoryRebuildTests(unittest.TestCase):

    def _create_db(self, path: Path):
        conn = sqlite3.connect(path)

        conn.execute(
            """
            CREATE TABLE indices_daily (
                id INTEGER PRIMARY KEY,
                trade_date DATE,
                index_name TEXT,
                open REAL,
                high REAL,
                low REAL,
                previous_close REAL,
                close REAL,
                price_change REAL,
                change_pct REAL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE market_scenario_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date DATE NOT NULL,
                index_name TEXT NOT NULL,
                primary_scenario TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                trend REAL,
                volatility REAL,
                daily_return REAL,
                range_pct REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, index_name)
            )
            """
        )

        return conn

    def _insert_history(self, conn, rows):
        conn.executemany(
            """
            INSERT INTO indices_daily
            (
                trade_date,
                index_name,
                open,
                high,
                low,
                previous_close,
                close,
                price_change,
                change_pct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def test_rebuild_creates_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"

            conn = self._create_db(db)

            rows = []

            for i in range(80):
                close = 100 + i * 0.5

                rows.append(
                    (
                        f"2025-01-{(i % 28) + 1:02d}",
                        "NIFTY50",
                        close,
                        close + 1,
                        close - 1,
                        close - 0.5,
                        close,
                        0.5,
                        0.5,
                    )
                )

            # Use unique dates instead of the simple day-of-month pattern.
            rows = []

            import pandas as pd

            dates = pd.date_range(
                "2025-01-01",
                periods=80,
                freq="D",
            )

            for i, date in enumerate(dates):
                close = 100 + i * 0.5

                rows.append(
                    (
                        date.strftime("%Y-%m-%d"),
                        "NIFTY50",
                        close,
                        close + 1,
                        close - 1,
                        close - 0.5,
                        close,
                        0.5,
                        0.5,
                    )
                )

            self._insert_history(conn, rows)
            conn.commit()
            conn.close()

            result = rebuild(db)

            self.assertEqual(result["source_rows"], 80)
            self.assertEqual(result["scenario_rows"], 80)
            self.assertEqual(result["rows_inserted"], 80)

            conn = sqlite3.connect(db)

            count = conn.execute(
                "SELECT COUNT(*) FROM market_scenario_history"
            ).fetchone()[0]

            conn.close()

            self.assertEqual(count, 80)

    def test_rebuild_preserves_existing_fingerprint_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"

            conn = self._create_db(db)

            import pandas as pd

            dates = pd.date_range(
                "2025-01-01",
                periods=80,
                freq="D",
            )

            rows = []

            for i, date in enumerate(dates):
                close = 100 + i * 0.5

                rows.append(
                    (
                        date.strftime("%Y-%m-%d"),
                        "NIFTY50",
                        close,
                        close + 1,
                        close - 1,
                        close - 0.5,
                        close,
                        0.5,
                        0.5,
                    )
                )

            self._insert_history(conn, rows)
            conn.commit()
            conn.close()

            first = rebuild(db)

            conn = sqlite3.connect(db)

            fingerprint, scenario_id = conn.execute(
                """
                SELECT fingerprint, scenario_id
                FROM market_scenario_history
                ORDER BY id
                LIMIT 1
                """
            ).fetchone()

            conn.close()

            second = rebuild(db)

            self.assertEqual(
                second["scenario_rows"],
                first["scenario_rows"],
            )

            conn = sqlite3.connect(db)

            preserved_id = conn.execute(
                """
                SELECT scenario_id
                FROM market_scenario_history
                WHERE fingerprint = ?
                LIMIT 1
                """,
                (fingerprint,),
            ).fetchone()[0]

            conn.close()

            self.assertEqual(
                preserved_id,
                scenario_id,
            )

    def test_rebuild_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"

            conn = self._create_db(db)

            import pandas as pd

            dates = pd.date_range(
                "2025-01-01",
                periods=80,
                freq="D",
            )

            rows = []

            for i, date in enumerate(dates):
                close = 100 + i * 0.5

                rows.append(
                    (
                        date.strftime("%Y-%m-%d"),
                        "NIFTY50",
                        close,
                        close + 1,
                        close - 1,
                        close - 0.5,
                        close,
                        0.5,
                        0.5,
                    )
                )

            self._insert_history(conn, rows)
            conn.commit()
            conn.close()

            first = rebuild(db)
            second = rebuild(db)

            self.assertEqual(
                first["scenario_rows"],
                second["scenario_rows"],
            )

            self.assertEqual(
                first["unique_fingerprints"],
                second["unique_fingerprints"],
            )

            self.assertEqual(
                first["unique_scenario_ids"],
                second["unique_scenario_ids"],
            )


if __name__ == "__main__":
    unittest.main()