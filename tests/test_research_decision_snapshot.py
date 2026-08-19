from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import research.research_decision_snapshot as snapshot_module
from research.research_decision_snapshot import CANDIDATES, OUTPUT_COLUMNS, build_snapshot


class ResearchDecisionSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.original_gate = snapshot_module._gate_module

        class FakeGate:
            @staticmethod
            def evaluate(frame):
                s = pd.to_numeric(frame["spread"], errors="coerce").dropna()
                checks = {
                    "minimum_windows": len(s) >= 5,
                    "positive_window_rate": (s > 0).mean() * 100 >= 60,
                    "average_spread": s.mean() > 0,
                    "median_spread": s.median() > 0,
                    "worst_window": s.min() >= -2,
                }
                passed = sum(checks.values())
                decision = (
                    "PASS"
                    if passed == 5
                    else "REVIEW"
                    if passed >= 3
                    else "FAIL"
                )
                return {
                    "decision": decision,
                    "metrics": {
                        "windows": len(s),
                        "average_spread": float(s.mean()),
                        "median_spread": float(s.median()),
                        "positive_window_pct": float((s > 0).mean() * 100),
                        "worst_window": float(s.min()),
                    },
                }

        snapshot_module._gate_module = lambda: FakeGate

    def tearDown(self):
        snapshot_module._gate_module = self.original_gate

    def _results(self):
        return pd.DataFrame(
            [
                {
                    "candidate": "Baseline Failure Decomposition",
                    "spreads": [0.5, 0.4, 0.3, 0.2, 0.1],
                },
                {
                    "candidate": "Conditional Score",
                    "spreads": [-0.5, -0.4, -0.3, -0.2, -0.1],
                },
                {
                    "candidate": "Factor Agreement",
                    "spreads": [1.0, 1.0, 1.0, -3.0, -3.0],
                },
                {
                    "candidate": "C3.3 Factor Interaction",
                    "spreads": [-0.01, -0.02, -0.03, -0.01, -0.02],
                },
                {
                    "candidate": "C2.2 Regime-Aware",
                    "spreads": [-0.6, -0.7, -0.8, -0.5, -0.7],
                },
            ]
        )

    def test_six_candidates_are_represented(self):
        result = build_snapshot(self._results())
        self.assertEqual(len(result), 6)
        self.assertEqual(
            set(result["candidate"]),
            {item["candidate"] for item in CANDIDATES},
        )

    def test_strong_candidate_receives_pass(self):
        result = build_snapshot(self._results())
        row = result[result["candidate"] == "TRACK_B_BASELINE_FAILURE"].iloc[0]
        self.assertEqual(row["decision"], "PASS")

    def test_weak_candidate_receives_fail(self):
        result = build_snapshot(self._results())
        row = result[result["candidate"] == "TRACK_B_CONDITIONAL_SCORE"].iloc[0]
        self.assertEqual(row["decision"], "FAIL")

    def test_borderline_candidate_receives_review(self):
        result = build_snapshot(self._results())
        row = result[result["candidate"] == "TRACK_B_FACTOR_AGREEMENT"].iloc[0]
        self.assertEqual(row["decision"], "REVIEW")

    def test_insufficient_evidence_is_not_fail(self):
        source = pd.DataFrame(
            [{"candidate": "C3.3 Factor Interaction", "spreads": []}]
        )
        result = build_snapshot(source)
        row = result[result["candidate"] == "TRACK_C_FACTOR_INTERACTION"].iloc[0]
        self.assertEqual(row["decision"], "NO_RESULT")
        self.assertEqual(row["evidence_status"], "INSUFFICIENT_DATA")

    def test_missing_candidate_does_not_crash(self):
        source = pd.DataFrame(
            [{"candidate": "Conditional Score", "decision": "FAIL", "observations": 100}]
        )
        result = build_snapshot(source)
        self.assertEqual(len(result), 6)
        row = result[result["candidate"] == "TRACK_C_SCENARIO_WEAPON"].iloc[0]
        self.assertEqual(row["decision"], "NO_RESULT")
        self.assertEqual(row["evidence_status"], "UNAVAILABLE")

    def test_output_columns_exist(self):
        result = build_snapshot(self._results())
        self.assertEqual(list(result.columns), OUTPUT_COLUMNS)

    def test_input_data_is_not_mutated(self):
        source = self._results()
        before = source.copy(deep=True)
        build_snapshot(source)
        pd.testing.assert_frame_equal(source, before)

    def test_no_database_writes_occur(self):
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("CREATE TABLE marker(value INTEGER)")
            conn.execute("INSERT INTO marker VALUES (1)")
            conn.commit()

            before = conn.execute("SELECT * FROM marker").fetchall()
            build_snapshot(self._results())
            after = conn.execute("SELECT * FROM marker").fetchall()

            self.assertEqual(before, after)
        finally:
            conn.close()

    def test_deterministic_output(self):
        first = build_snapshot(self._results())
        second = build_snapshot(self._results())
        pd.testing.assert_frame_equal(first, second)


if __name__ == "__main__":
    unittest.main()
