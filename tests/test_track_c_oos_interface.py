from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from research.track_c_oos_interface import (
    chronological_holdout,
    execute_batch,
    execute_relationship,
    filter_relationship,
    validate_relationships,
)


class TrackCOOSInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame({
            "trade_date": pd.date_range("2025-01-01", periods=40, freq="D"),
            "scenario_id": ["S1"] * 20 + ["S2"] * 20,
            "primary_scenario": ["TREND_UP"] * 40,
            "fingerprint": ["FP1"] * 20 + ["FP2"] * 20,
        })
        self.data = pd.DataFrame({
            "trade_date": pd.date_range("2025-01-01", periods=40, freq="D"),
            "candidate": ["TRACK_C_FACTOR_INTERACTION"] * 40,
            "value": range(40),
        })

    def test_candidate_isolation(self):
        d = self.data.copy()
        d.loc[0, "candidate"] = "OTHER"
        out = filter_relationship(d, self.history, "S1", "FP1", "TRACK_C_FACTOR_INTERACTION")
        self.assertTrue((out["candidate"] == "TRACK_C_FACTOR_INTERACTION").all())

    def test_scenario_id_isolation(self):
        out = filter_relationship(self.data, self.history, "S2", "FP2", "TRACK_C_FACTOR_INTERACTION")
        self.assertEqual(out["trade_date"].min(), pd.Timestamp("2025-01-21"))

    def test_fingerprint_isolation(self):
        out = filter_relationship(self.data, self.history, "S1", "FP1", "TRACK_C_FACTOR_INTERACTION")
        self.assertEqual(len(out), 20)
        self.assertTrue((out["trade_date"] < pd.Timestamp("2025-01-21")).all())

    def test_chronological_oos_enforcement(self):
        train, holdout = chronological_holdout(self.data, "trade_date", 20, 5)
        self.assertLess(train["trade_date"].max(), holdout["trade_date"].min())

    def test_insufficient_holdout_handling(self):
        self.assertIsNone(
            chronological_holdout(self.data.head(24), "trade_date", 20, 5)
        )

    def test_no_future_leakage(self):
        train, holdout = chronological_holdout(self.data, "trade_date", 20, 5)
        self.assertLess(train["trade_date"].max(), holdout["trade_date"].min())

    def test_duplicate_relationship_protection(self):
        frame = pd.DataFrame([
            {"scenario_id": "S1", "fingerprint": "FP1", "candidate": "TRACK_C_FACTOR_INTERACTION"},
            {"scenario_id": "S1", "fingerprint": "FP1", "candidate": "TRACK_C_FACTOR_INTERACTION"},
        ])
        with self.assertRaises(ValueError):
            validate_relationships(frame)

    def test_deterministic_output(self):
        frame = pd.DataFrame([
            {"scenario_id": "S2", "fingerprint": "FP2", "candidate": "TRACK_C_FACTOR_INTERACTION"},
            {"scenario_id": "S1", "fingerprint": "FP1", "candidate": "TRACK_C_FACTOR_INTERACTION"},
        ])
        fake = lambda s, f, c, db: {
            "candidate": c, "scenario_id": s, "fingerprint": f,
            "research_status": "INSUFFICIENT_HOLDOUT_HISTORY",
            "oos_result": "NOT_READY",
            "scenario_matched_observations": 0,
            "train_observations": 0, "holdout_observations": 0,
            "execution_reason": "test",
        }
        with patch("research.track_c_oos_interface.execute_relationship", side_effect=fake):
            a = execute_batch(frame)
        with patch("research.track_c_oos_interface.execute_relationship", side_effect=fake):
            b = execute_batch(frame)
        self.assertTrue(a.equals(b))

    def test_no_sqlite_writes(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "x.db"
            c = sqlite3.connect(db)
            c.execute("CREATE TABLE market_scenario_history "
                      "(trade_date TEXT, scenario_id TEXT, primary_scenario TEXT, fingerprint TEXT)")
            c.execute("INSERT INTO market_scenario_history VALUES "
                      "('2025-01-01','S1','TREND_UP','FP1')")
            c.commit()
            c.close()
            before = db.stat().st_mtime_ns
            with patch("research.track_c_oos_interface._import_candidate",
                       side_effect=ImportError("boundary")):
                with self.assertRaises(ImportError):
                    execute_relationship("S1", "FP1", "TRACK_C_FACTOR_INTERACTION", db)
            self.assertEqual(before, db.stat().st_mtime_ns)

    def test_source_immutability(self):
        d, h = self.data.copy(deep=True), self.history.copy(deep=True)
        d0, h0 = d.copy(deep=True), h.copy(deep=True)
        filter_relationship(d, h, "S1", "FP1", "TRACK_C_FACTOR_INTERACTION")
        self.assertTrue(d.equals(d0))
        self.assertTrue(h.equals(h0))

    def test_missing_identity_rejected(self):
        with self.assertRaises(ValueError):
            validate_relationships(pd.DataFrame(
                {"scenario_id": ["S1"], "fingerprint": [""], "candidate": ["TRACK_C_FACTOR_INTERACTION"]}
            ))


if __name__ == "__main__":
    unittest.main()
