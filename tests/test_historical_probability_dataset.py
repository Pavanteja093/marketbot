import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from research.historical_probability_dataset import (
    DOWN,
    FLAT,
    UP,
    build_dataset,
    classify_return,
    run,
)


def make_sources():
    dates = pd.to_datetime(
        ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
    )
    factors = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": ["A", "A", "B", "B"],
            "sector": ["BANK", "BANK", "IT", "IT"],
            "change_pct": [1.0, -1.0, 0.2, 0.3],
            "sector_strength": [0.1, 0.2, 0.3, 0.4],
            "intelligence_score": [70, 71, 72, 73],
            "rank": [1, 2, 1, 2],
        }
    )
    scenarios = pd.DataFrame(
        {
            "trade_date": dates,
            "index_name": ["NIFTY50"] * 4,
            "primary_scenario": ["TREND_UP", "TREND_DOWN", "FLAT", "CHOPPY"],
            "scenario_id": ["S1", "S2", "S3", "S4"],
            "fingerprint": ["F1", "F2", "F3", "F4"],
        }
    )
    returns = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": ["A", "A", "B", "B"],
            "return_1d": [1, -1, 0.1, 0.1],
            "return_5d": [0.8, -0.8, 0.5, -0.5],
            "return_10d": [1, -1, 0.2, -0.2],
            "return_20d": [2, -2, 0.4, -0.4],
        }
    )
    return factors, scenarios, returns


class HistoricalProbabilityDatasetTests(unittest.TestCase):
    def test_correct_up_down_flat_classification(self):
        labels = classify_return(
            pd.Series([0.51, -0.51, 0.50, -0.50, 0.0])
        )
        self.assertEqual(labels.tolist(), [UP, DOWN, FLAT, FLAT, FLAT])

    def test_date_alignment(self):
        f, s, r = make_sources()
        result = build_dataset(f, s, r)
        self.assertEqual(len(result), 4)
        self.assertEqual(
            result.loc[result["index_name"] == "A", "scenario"].tolist(),
            ["TREND_UP", "TREND_DOWN"],
        )

    def test_future_leakage_prevention(self):
        f, s, r = make_sources()
        future = s.copy()
        future.loc[0, "trade_date"] = pd.Timestamp("2026-01-10")
        result = build_dataset(f, future, r)
        self.assertEqual(len(result), 3)
        self.assertNotIn("2026-01-10", set(result["trade_date"]))

    def test_duplicate_prevention(self):
        f, s, r = make_sources()
        duplicate = pd.concat([f, f.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            build_dataset(duplicate, s, r)

    def test_scenario_preservation(self):
        f, s, r = make_sources()
        result = build_dataset(f, s, r)
        self.assertEqual(
            result.loc[0, ["scenario", "scenario_id", "fingerprint"]].tolist(),
            ["TREND_UP", "S1", "F1"],
        )

    def test_missing_data_is_excluded(self):
        f, s, r = make_sources()
        r.loc[1, "return_5d"] = None
        result = build_dataset(f, s, r)
        self.assertEqual(len(result), 3)

    def test_deterministic_output(self):
        f, s, r = make_sources()
        a = build_dataset(f, s, r)
        b = build_dataset(
            f.sample(frac=1, random_state=7),
            s.sample(frac=1, random_state=8),
            r.sample(frac=1, random_state=9),
        )
        pd.testing.assert_frame_equal(a, b)

    def test_source_immutability(self):
        f, s, r = make_sources()
        f0, s0, r0 = f.copy(deep=True), s.copy(deep=True), r.copy(deep=True)
        build_dataset(f, s, r)
        pd.testing.assert_frame_equal(f, f0)
        pd.testing.assert_frame_equal(s, s0)
        pd.testing.assert_frame_equal(r, r0)

    def test_no_sqlite_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            conn = sqlite3.connect(db)
            conn.executescript(
                """
                CREATE TABLE factor_history (
                    trade_date DATE, symbol TEXT, sector TEXT,
                    change_pct REAL, sector_strength REAL,
                    intelligence_score REAL, rank INTEGER
                );
                CREATE TABLE market_scenario_history (
                    trade_date DATE, index_name TEXT, primary_scenario TEXT,
                    scenario_id TEXT, fingerprint TEXT
                );
                CREATE TABLE forward_returns (
                    trade_date DATE, symbol TEXT,
                    return_1d REAL, return_5d REAL,
                    return_10d REAL, return_20d REAL
                );
                """
            )
            f, s, r = make_sources()
            f.to_sql("factor_history", conn, if_exists="append", index=False)
            s.to_sql("market_scenario_history", conn, if_exists="append", index=False)
            r.to_sql("forward_returns", conn, if_exists="append", index=False)
            conn.commit()
            conn.close()

            before = db.read_bytes()
            out = Path(tmp) / "dataset.csv"
            run(db, out)
            after = db.read_bytes()

            self.assertEqual(before, after)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
