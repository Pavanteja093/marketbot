import sqlite3
import tempfile
import unittest
from pathlib import Path

from track_a.core import validate


class TrackATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "synthetic.db"

    def tearDown(self):
        import gc
        import shutil
        gc.collect()
        shutil.rmtree(self.tmp.name, ignore_errors=True)

    def make_schema(self, entity="index_name"):
        c = sqlite3.connect(self.db)
        c.executescript(f"""
        CREATE TABLE prediction_history (
            id INTEGER PRIMARY KEY,
            trade_date TEXT,
            {entity} TEXT,
            rank INTEGER,
            prediction TEXT
        );
        CREATE TABLE prediction_outcomes (
            id INTEGER PRIMARY KEY,
            prediction_date TEXT,
            {entity} TEXT,
            rank INTEGER,
            return_5d REAL
        );
        CREATE TABLE learning_history (
            id INTEGER PRIMARY KEY,
            trade_date TEXT,
            index_name TEXT,
            prediction TEXT,
            actual_outcome TEXT
        );
        CREATE TABLE direction_predictions (
            id INTEGER PRIMARY KEY,
            prediction_time TEXT,
            index_name TEXT,
            direction TEXT
        );
        CREATE TABLE market_prediction_history (
            id INTEGER PRIMARY KEY,
            trade_time TEXT,
            index_name TEXT,
            prediction TEXT
        );
        """)
        c.commit()
        c.close()

    def test_real_contract_matches(self):
        self.make_schema()
        c = sqlite3.connect(self.db)
        c.executemany(
            "INSERT INTO prediction_history VALUES (?, ?, ?, ?, ?)",
            [(1, "2026-08-03", "AAA", 1, None),
             (2, "2026-08-04", "AAA", 2, None),
             (3, "2026-08-05", "BBB", 1, None)]
        )
        c.executemany(
            "INSERT INTO prediction_outcomes VALUES (?, ?, ?, ?, ?)",
            [(1, "2026-08-03", "AAA", 1, 2.0),
             (2, "2026-08-04", "AAA", 2, -1.0)]
        )
        c.commit()
        c.close()

        r = validate(self.db)
        self.assertTrue(r.ok)
        self.assertEqual(r.prediction_history_rows, 3)
        self.assertEqual(r.prediction_outcomes_rows, 2)
        self.assertEqual(r.matched_outcome_rows, 2)
        self.assertEqual(r.unmatched_prediction_rows, 1)

    def test_symbol_variant_is_supported(self):
        self.make_schema(entity="symbol")
        c = sqlite3.connect(self.db)
        c.execute(
            "INSERT INTO prediction_history VALUES (1,'2026-08-03','AAA',1,NULL)"
        )
        c.execute(
            "INSERT INTO prediction_outcomes VALUES (1,'2026-08-03','AAA',1,2.0)"
        )
        c.commit()
        c.close()

        r = validate(self.db)
        self.assertTrue(r.ok)
        self.assertEqual(r.matched_outcome_rows, 1)

    def test_missing_future_outcome_is_not_false(self):
        self.make_schema()
        c = sqlite3.connect(self.db)
        c.execute(
            "INSERT INTO prediction_history VALUES (1,'2026-08-07','AAA',1,NULL)"
        )
        c.commit()
        c.close()

        r = validate(self.db)
        self.assertTrue(r.ok)
        self.assertEqual(r.unmatched_prediction_rows, 1)
        self.assertIn("not false outcomes", r.warnings[0])

    def test_learning_history_not_filled_from_stock_outcomes(self):
        self.make_schema()
        c = sqlite3.connect(self.db)
        c.execute(
            "INSERT INTO prediction_history VALUES (1,'2026-08-03','AAA',1,NULL)"
        )
        c.execute(
            "INSERT INTO prediction_outcomes VALUES (1,'2026-08-03','AAA',1,2.0)"
        )
        c.commit()
        c.close()

        r = validate(self.db)
        self.assertTrue(r.ok)
        self.assertEqual(r.learning_history_rows, 0)
        self.assertIn("intentionally not copied", r.learning_history_reason)

    def test_duplicate_outcome_key_is_critical(self):
        self.make_schema()
        c = sqlite3.connect(self.db)
        c.execute(
            "INSERT INTO prediction_history VALUES (1,'2026-08-03','AAA',1,NULL)"
        )
        c.executemany(
            "INSERT INTO prediction_outcomes VALUES (?, '2026-08-03','AAA',1,?)",
            [(1, 2.0), (2, 3.0)]
        )
        c.commit()
        c.close()

        r = validate(self.db)
        self.assertFalse(r.ok)
        self.assertTrue(r.critical_errors)

    def test_missing_required_table_is_critical(self):
        c = sqlite3.connect(self.db)
        c.execute(
            "CREATE TABLE prediction_history (trade_date TEXT,index_name TEXT,rank INTEGER)"
        )
        c.commit()
        c.close()

        r = validate(self.db)
        self.assertFalse(r.ok)
        self.assertTrue(r.critical_errors)

    def test_missing_required_column_is_critical(self):
        c = sqlite3.connect(self.db)
        c.executescript("""
            CREATE TABLE prediction_history (trade_date TEXT, index_name TEXT, rank INTEGER);
            CREATE TABLE prediction_outcomes (prediction_date TEXT, index_name TEXT, rank INTEGER);
        """)
        c.commit()
        c.close()

        r = validate(self.db)
        self.assertFalse(r.ok)
        self.assertTrue(any("return_5d" in x for x in r.critical_errors))

    def test_existing_learning_records_are_reported_not_created(self):
        self.make_schema()
        c = sqlite3.connect(self.db)
        c.execute(
            "INSERT INTO learning_history VALUES (1,'2026-08-03','NIFTY50','UP','UP')"
        )
        c.commit()
        c.close()

        r = validate(self.db)
        self.assertTrue(r.ok)
        self.assertEqual(r.learning_history_rows, 1)
        self.assertIn("contains market-direction", r.learning_history_reason)

    def test_validation_does_not_write_database(self):
        self.make_schema()
        with sqlite3.connect(self.db) as conn:
            before = conn.execute(
                "SELECT COUNT(*) FROM prediction_history"
            ).fetchone()[0]

        validate(self.db)

        with sqlite3.connect(self.db) as conn:
            after = conn.execute(
                "SELECT COUNT(*) FROM prediction_history"
            ).fetchone()[0]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
