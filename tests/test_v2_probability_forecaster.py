import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from research.v2_probability_forecaster import (
    CLASSES,
    DOWN,
    FLAT,
    UP,
    ForecastConfig,
    classify_return,
    evaluate_probabilities,
    load_dataset,
    walk_forward,
)


class V2ProbabilityForecasterTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "synthetic.db"
        self._build_db()

    def tearDown(self):
        import gc
        import shutil

        gc.collect()
        shutil.rmtree(self.tmp.name, ignore_errors=True)

    def _build_db(self):
        conn = sqlite3.connect(self.db)
        try:
            conn.execute("""
                CREATE TABLE signal_history_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date DATE NOT NULL,
                    index_name TEXT NOT NULL,
                    sector TEXT,
                    intelligence_score REAL,
                    rank INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE forward_returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date DATE NOT NULL,
                    index_name TEXT NOT NULL,
                    return_1d REAL,
                    return_5d REAL,
                    return_10d REAL,
                    return_20d REAL
                )
            """)

            start = pd.Timestamp("2025-01-01")
            rows_signal = []
            rows_return = []

            # 90 trading observations per date across 3 symbols. The outcome
            # pattern is deterministic and contains all three classes.
            for day in range(90):
                date = start + pd.Timedelta(days=day)
                for rank, symbol in enumerate(("AAA", "BBB", "CCC"), start=1):
                    cycle = (day + rank) % 3
                    future = {0: 1.25, 1: 0.0, 2: -1.25}[cycle]
                    rows_signal.append(
                        (
                            date.date().isoformat(),
                            symbol,
                            "BANKING" if rank != 3 else "IT",
                            60.0 + rank + day * 0.05,
                            rank,
                        )
                    )
                    rows_return.append(
                        (
                            date.date().isoformat(),
                            symbol,
                            future,
                            future,
                            future,
                            future,
                        )
                    )

            conn.executemany(
                """
                INSERT INTO signal_history_v2
                (trade_date, index_name, sector, intelligence_score, rank)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows_signal,
            )
            conn.executemany(
                """
                INSERT INTO forward_returns
                (trade_date, index_name, return_1d, return_5d, return_10d, return_20d)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows_return,
            )
            conn.commit()
        finally:
            conn.close()

    def test_classify_return(self):
        values = pd.Series([-1.0, -0.50, -0.49, 0.0, 0.50, 0.51])
        result = classify_return(values, flat_threshold_pct=0.50).tolist()
        self.assertEqual(
            result,
            [DOWN, FLAT, FLAT, FLAT, FLAT, UP],
        )

    def test_load_dataset_uses_only_completed_v2_signals(self):
        df, features = load_dataset(self.db)
        self.assertEqual(len(df), 270)
        self.assertEqual(features, ["intelligence_score", "rank"])
        self.assertEqual(set(df["label"]), set(CLASSES))
        self.assertEqual(
            list(df.columns[:6]),
            [
                "trade_date",
                "index_name",
                "sector",
                "intelligence_score",
                "rank",
                "future_return",
            ],
        )

    def test_walk_forward_is_chronological(self):
        df, features = load_dataset(self.db)
        config = ForecastConfig(
            min_train_dates=40,
            test_dates=10,
            step_dates=10,
            min_class_count=5,
        )
        predictions, folds = walk_forward(df, features, config)

        successful = [f for f in folds if f["status"] == "SUCCESS"]
        self.assertTrue(successful)
        for fold in successful:
            self.assertLess(fold["train_end"], fold["test_start"])

        self.assertFalse(predictions.empty)
        self.assertTrue(
            (pd.to_numeric(predictions["p_down"]) >= 0).all()
        )
        self.assertTrue(
            (pd.to_numeric(predictions["p_flat"]) >= 0).all()
        )
        self.assertTrue(
            (pd.to_numeric(predictions["p_up"]) >= 0).all()
        )

        probability_sum = (
            predictions["p_down"]
            + predictions["p_flat"]
            + predictions["p_up"]
        )
        np.testing.assert_allclose(probability_sum.to_numpy(), 1.0, atol=1e-8)

    def test_probability_evaluation_returns_metrics(self):
        predictions = pd.DataFrame(
            {
                "actual": [DOWN, FLAT, UP, UP],
                "predicted": [DOWN, FLAT, UP, DOWN],
                "p_down": [0.80, 0.10, 0.05, 0.40],
                "p_flat": [0.10, 0.80, 0.10, 0.20],
                "p_up": [0.10, 0.10, 0.85, 0.40],
            }
        )
        metrics = evaluate_probabilities(predictions)
        self.assertEqual(metrics["n"], 4)
        for key in (
            "accuracy",
            "balanced_accuracy",
            "log_loss",
            "brier_multiclass",
            "multiclass_ece",
        ):
            self.assertIsInstance(metrics[key], float)

    def test_missing_required_table_fails(self):
        conn = sqlite3.connect(self.db)
        try:
            conn.execute("DROP TABLE forward_returns")
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(RuntimeError):
            load_dataset(self.db)

    def test_missing_required_column_fails(self):
        conn = sqlite3.connect(self.db)
        try:
            conn.execute("ALTER TABLE signal_history_v2 RENAME TO old_signal")
            conn.execute("""
                CREATE TABLE signal_history_v2 (
                    trade_date DATE,
                    index_name TEXT,
                    sector TEXT,
                    intelligence_score REAL
                )
            """)
            conn.execute("""
                INSERT INTO signal_history_v2
                SELECT trade_date, index_name, sector, intelligence_score
                FROM old_signal
            """)
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(RuntimeError):
            load_dataset(self.db)

    def test_validation_path_does_not_write_database(self):
        before = self.db.read_bytes()

        df, features = load_dataset(self.db)
        config = ForecastConfig(
            min_train_dates=40,
            test_dates=10,
            step_dates=10,
            min_class_count=5,
        )
        walk_forward(df, features, config)

        after = self.db.read_bytes()
        self.assertEqual(before, after)

    def test_insufficient_class_history_is_not_forecast(self):
        df, features = load_dataset(self.db)
        df.loc[df["label"] == UP, "label"] = FLAT

        config = ForecastConfig(
            min_train_dates=40,
            test_dates=10,
            step_dates=10,
            min_class_count=5,
        )
        _, folds = walk_forward(df, features, config)

        self.assertTrue(
            all(
                fold["status"] == "SKIPPED_INSUFFICIENT_CLASS_HISTORY"
                for fold in folds
            )
        )


if __name__ == "__main__":
    unittest.main()
