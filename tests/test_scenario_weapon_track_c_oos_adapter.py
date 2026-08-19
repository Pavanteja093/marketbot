import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from research.scenario_weapon_track_c_oos_adapter import (
    TRACK_C_CANDIDATES,
    execute_track_c_relationship,
    filter_relationship,
)


class TrackCOOSAdapterTests(unittest.TestCase):
    def _db(self, rows=None):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        path = Path(tmp.name)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE market_scenario_history (trade_date TEXT, scenario_id TEXT, primary_scenario TEXT, fingerprint TEXT)")
        if rows:
            conn.executemany("INSERT INTO market_scenario_history VALUES (?, ?, ?, ?)", rows)
        conn.commit(); conn.close()
        return path

    def test_three_candidates_are_independent_routes(self):
        self.assertEqual(set(TRACK_C_CANDIDATES), {
            "TRACK_C_FACTOR_INTERACTION", "TRACK_C_REGIME_AWARE", "TRACK_C_SCENARIO_WEAPON"
        })

    def test_exact_scenario_and_fingerprint_filter(self):
        data = pd.DataFrame({"trade_date": pd.date_range("2026-01-01", periods=3), "x": [1, 2, 3]})
        history = pd.DataFrame({
            "trade_date": pd.to_datetime(["2026-01-01", "2026-01-03"]),
            "scenario_id": ["S1", "S1"], "fingerprint": ["FP1", "FP1"]
        })
        out = filter_relationship(data, history, "S1", "FP1")
        self.assertEqual(list(out.x), [1, 3])

    def test_wrong_relationship_returns_empty(self):
        data = pd.DataFrame({"trade_date": pd.to_datetime(["2026-01-01"]), "x": [1]})
        history = pd.DataFrame({"trade_date": pd.to_datetime(["2026-01-01"]), "scenario_id": ["S2"], "fingerprint": ["FP2"]})
        self.assertTrue(filter_relationship(data, history, "S1", "FP1").empty)

    def test_unauthorized_candidate_rejected(self):
        with self.assertRaises(ValueError):
            execute_track_c_relationship("S1", "FP1", "TRACK_X", Path("x.db"))

    def test_blank_relationship_rejected(self):
        with self.assertRaises(ValueError):
            execute_track_c_relationship("", "FP1", "TRACK_C_FACTOR_INTERACTION", Path("x.db"))

    def test_insufficient_history_is_not_fabricated(self):
        db = self._db([("2026-01-01", "S1", "TREND_UP", "FP1")])
        fake = type("Fake", (), {})()
        fake.load_data = lambda db: pd.DataFrame({"trade_date": pd.to_datetime(["2026-01-01"]), "v": [1]})
        fake.run_walk_forward = lambda df: (pd.DataFrame(), pd.DataFrame())
        with patch("research.scenario_weapon_track_c_oos_adapter.importlib.import_module", return_value=fake):
            result = execute_track_c_relationship("S1", "FP1", "TRACK_C_FACTOR_INTERACTION", db)
        self.assertEqual(result["research_status"], "INSUFFICIENT_HOLDOUT_HISTORY")
        self.assertEqual(result["oos_result"], "NOT_READY")

    def test_no_sqlite_write(self):
        db = self._db([("2026-01-01", "S1", "TREND_UP", "FP1")])
        before = sqlite3.connect(db).execute("SELECT COUNT(*) FROM market_scenario_history").fetchone()[0]
        fake = type("Fake", (), {})()
        fake.load_data = lambda db: pd.DataFrame({"trade_date": pd.to_datetime(["2026-01-01"]), "v": [1]})
        fake.run_walk_forward = lambda df: (pd.DataFrame(), pd.DataFrame())
        with patch("research.scenario_weapon_track_c_oos_adapter.importlib.import_module", return_value=fake):
            execute_track_c_relationship("S1", "FP1", "TRACK_C_FACTOR_INTERACTION", db)
        after = sqlite3.connect(db).execute("SELECT COUNT(*) FROM market_scenario_history").fetchone()[0]
        self.assertEqual(before, after)

    def test_input_immutability(self):
        data = pd.DataFrame({"trade_date": pd.date_range("2026-01-01", periods=2), "x": [1, 2]})
        history = pd.DataFrame({"trade_date": pd.date_range("2026-01-01", periods=2), "scenario_id": ["S1", "S1"], "fingerprint": ["FP1", "FP1"]})
        original = history.copy(deep=True)
        filter_relationship(data, history, "S1", "FP1")
        pd.testing.assert_frame_equal(history, original)

    def test_existing_oos_results_are_required(self):
        fake = pd.DataFrame({"spread": [1.0, 2.0, 3.0, 4.0, 5.0]})
        from research.scenario_weapon_track_c_oos_adapter import _normalise
        out = _normalise(fake, "TRACK_C_FACTOR_INTERACTION", "S1", "FP1")
        self.assertEqual(out["research_status"], "EXECUTED")
        self.assertEqual(out["oos_result"], "OOS_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
