from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

MODULE_PATH = Path(__file__).resolve().parents[1] / "research" / "track_d_phase2_2_cross_sectional_oos.py"
spec = importlib.util.spec_from_file_location("track_d_phase2_2", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


FACTORS = list(mod.FACTORS)


def make_frame(days=120, stocks=20):
    dates = pd.date_range("2025-01-01", periods=days, freq="B")
    rows = []
    for d_i, date in enumerate(dates):
        scenario = mod.REGIMES[d_i % len(mod.REGIMES)]
        for s in range(stocks):
            row = {
                "trade_date": date,
                "index_name": f"S{s:02d}.NS",
                "scenario": scenario,
            }
            for j, factor in enumerate(FACTORS):
                row[factor] = float((s * 7 + d_i + j) % 100)
            for h in mod.HORIZONS:
                row[f"return_{h}d"] = float(s * 0.1 + d_i * 0.001 + h * 0.01)
            rows.append(row)
    return pd.DataFrame(rows)


class CrossSectionalOOSTests(unittest.TestCase):
    def test_chronological_oos_construction(self):
        dates = pd.date_range("2025-01-01", periods=120, freq="B")
        folds = mod.make_global_oos_folds(dates, min_train_days=80, test_days=20)
        self.assertEqual(len(folds), 2)
        self.assertLess(folds[0][1], folds[0][2])
        self.assertLess(folds[0][3], folds[1][2])

    def test_cross_sectional_ranking_is_within_date(self):
        df = pd.DataFrame({
            "trade_date": ["2025-01-01"] * 3 + ["2025-01-02"] * 3,
            "factor": [1, 2, 3, 100, 200, 300],
        })
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        ranks = mod.cross_sectional_rank(df, "factor")
        self.assertEqual(ranks.iloc[0], 1 / 3)
        self.assertEqual(ranks.iloc[2], 1.0)
        self.assertEqual(ranks.iloc[3], 1 / 3)
        self.assertEqual(ranks.iloc[5], 1.0)

    def test_no_cross_date_ranking_leakage(self):
        a = pd.DataFrame({"trade_date": ["2025-01-01"] * 3, "factor": [1, 2, 3]})
        b = pd.DataFrame({"trade_date": ["2025-01-01"] * 3 + ["2025-01-02"] * 100, "factor": [1, 2, 3] + list(range(100))})
        a["trade_date"] = pd.to_datetime(a["trade_date"])
        b["trade_date"] = pd.to_datetime(b["trade_date"])
        self.assertTrue(np.allclose(mod.cross_sectional_rank(a, "factor").to_numpy(), mod.cross_sectional_rank(b, "factor").iloc[:3].to_numpy()))

    def test_no_future_information_in_quintile_spread(self):
        day = pd.DataFrame({
            "trade_date": pd.to_datetime(["2025-01-02"] * 10),
            "index_name": [f"S{i}" for i in range(10)],
            "factor": range(10),
            "return_5d": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
        })
        ic, top, bottom, n = mod._daily_cross_sectional_stats(day, "factor", "return_5d")
        self.assertEqual(n, 10)
        self.assertGreater(ic, 0)
        self.assertGreater(top, bottom)

    def test_factor_horizon_coverage(self):
        result = mod.validate(make_frame(), min_train_days=80, test_days=20)
        self.assertEqual(set(result.factor), set(FACTORS))
        self.assertEqual(set(result.horizon_days), set(mod.HORIZONS))
        self.assertEqual(len(result), 6 * 7 * 4)

    def test_scenario_conditioning(self):
        df = make_frame()
        result = mod.validate(df, regimes=["TREND_UP"], min_train_days=80, test_days=20)
        self.assertTrue((result.scenario == "TREND_UP").all())

    def test_insufficient_sample_handling(self):
        df = make_frame(days=50, stocks=20)
        result = mod.validate(df, min_train_days=80, test_days=20)
        self.assertTrue((result.evidence_classification == "NO_DATA").all())

    def test_deterministic_output(self):
        df = make_frame()
        a = mod.validate(df)
        b = mod.validate(df)
        pd.testing.assert_frame_equal(a, b)

    def test_input_immutability(self):
        df = make_frame()
        before = df.copy(deep=True)
        mod.validate(df)
        pd.testing.assert_frame_equal(df, before)

    def test_required_column_validation(self):
        df = make_frame().drop(columns=["liquidity_score"])
        with self.assertRaises(ValueError):
            mod.validate(df)

    def test_quintile_spread(self):
        day = pd.DataFrame({
            "trade_date": pd.to_datetime(["2025-01-01"] * 10),
            "index_name": [f"S{i}" for i in range(10)],
            "factor": range(10),
            "return_5d": [0, 0, 0, 0, 0, 2, 2, 2, 2, 2],
        })
        _, top, bottom, _ = mod._daily_cross_sectional_stats(day, "factor", "return_5d")
        self.assertAlmostEqual(top - bottom, 2.0)

    def test_bh_adjustment_is_conservative(self):
        adjusted = mod.benjamini_hochberg([0.001, 0.01, 0.2, np.nan])
        self.assertGreaterEqual(adjusted[0], 0.001)
        self.assertGreaterEqual(adjusted[1], 0.01)
        self.assertTrue(np.isnan(adjusted[3]))

    def test_no_sqlite_writes(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE forward_returns (trade_date TEXT, index_name TEXT, return_1d REAL, return_5d REAL, return_10d REAL, return_20d REAL)")
            conn.commit()
            conn.close()
            before = db.read_bytes()
            mod.read_forward_returns(db)
            after = db.read_bytes()
            self.assertEqual(before, after)

    def test_join_contract_is_one_to_one(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE forward_returns (trade_date TEXT, index_name TEXT, return_1d REAL, return_5d REAL, return_10d REAL, return_20d REAL)")
            conn.executemany("INSERT INTO forward_returns VALUES (?,?,?,?,?,?)", [("2025-01-01", "S00.NS", 1, 1, 1, 1), ("2025-01-01", "S00.NS", 2, 2, 2, 2)])
            conn.commit(); conn.close()
            csv = Path(td) / "data.csv"
            make_frame(days=1, stocks=1).to_csv(csv, index=False)
            with self.assertRaises(ValueError):
                mod.load_dataset(csv, db)


if __name__ == "__main__":
    unittest.main()
