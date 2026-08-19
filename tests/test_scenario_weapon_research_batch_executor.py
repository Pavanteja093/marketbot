import sys
import types
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from research.scenario_weapon_research_batch_executor import (
    EXECUTABLE_BATCH_ACTIONS,
    REQUIRED_COLUMNS,
    SUPPORTED_CANDIDATES,
    TRACK_C_CANDIDATES,
    execute,
    load_batches,
    select_authorized_relationships,
)


def make_batches():
    rows = [
        {
            "batch_id": "B1",
            "batch_priority": "P0",
            "queue_priority": "P0",
            "research_priority": "HIGH",
            "scenario_id": "S1",
            "primary_scenario": "TREND_UP",
            "fingerprint": "FP1",
            "candidate": "TRACK_B_BASELINE_FAILURE",
            "scenario_observations": 30,
            "oos_windows": 5,
            "target_oos_windows": 10,
            "oos_gap_to_target": 5,
            "eligibility_status": "EVIDENCE_PRESENT_EARLY",
            "queue_action": "CONTINUE_OOS",
            "batch_action": "CONTINUE_OOS_BATCH",
            "batch_reason": "continue",
            "batch_rank": 1,
        },
        {
            "batch_id": "B2",
            "batch_priority": "P1",
            "queue_priority": "P1",
            "research_priority": "HIGH",
            "scenario_id": "S2",
            "primary_scenario": "TREND_DOWN",
            "fingerprint": "FP2",
            "candidate": "TRACK_B_CONDITIONAL_SCORE",
            "scenario_observations": 30,
            "oos_windows": 0,
            "target_oos_windows": 10,
            "oos_gap_to_target": 10,
            "eligibility_status": "RESEARCHABLE_NO_EVIDENCE",
            "queue_action": "START_OOS_RESEARCH",
            "batch_action": "START_OOS_BATCH",
            "batch_reason": "start",
            "batch_rank": 2,
        },
        {
            "batch_id": "B3",
            "batch_priority": "P3",
            "queue_priority": "P3",
            "research_priority": "LOW",
            "scenario_id": "S3",
            "primary_scenario": "RANGE",
            "fingerprint": "FP3",
            "candidate": "TRACK_C_SCENARIO_WEAPON",
            "scenario_observations": 2,
            "oos_windows": 0,
            "target_oos_windows": 10,
            "oos_gap_to_target": 10,
            "eligibility_status": "INSUFFICIENT_SCENARIO_HISTORY",
            "queue_action": "WAIT_FOR_SCENARIO_HISTORY",
            "batch_action": "WAIT_FOR_SCENARIO_HISTORY",
            "batch_reason": "wait",
            "batch_rank": 3,
        },
    ]
    return pd.DataFrame(rows)


class ExecutorTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_batches_validates_and_does_not_mutate_source(self):
        frame = make_batches()
        path = self.root / "batches.csv"
        frame.to_csv(path, index=False)
        loaded = load_batches(path)
        self.assertEqual(len(loaded), 3)
        self.assertEqual(
            set(loaded["batch_action"]),
            {
                "CONTINUE_OOS_BATCH",
                "START_OOS_BATCH",
                "WAIT_FOR_SCENARIO_HISTORY",
            },
        )
        pd.testing.assert_frame_equal(
            pd.read_csv(path),
            frame,
            check_dtype=False,
        )

    def test_wait_relationships_are_not_authorized(self):
        authorized = select_authorized_relationships(make_batches())
        self.assertEqual(len(authorized), 2)
        self.assertNotIn(
            "WAIT_FOR_SCENARIO_HISTORY",
            set(authorized["batch_action"]),
        )

    def test_batch_filter_is_exact(self):
        authorized = select_authorized_relationships(
            make_batches(),
            batch_id="B2",
        )
        self.assertEqual(len(authorized), 1)
        self.assertEqual(authorized.iloc[0]["scenario_id"], "S2")

    def test_execute_only_supported_candidates_and_exact_relationship(self):
        calls = {
            "baseline": 0,
            "conditional": 0,
            "agreement": 0,
            "attach": 0,
            "evaluate": 0,
            "track_c": 0,
        }

        adapter = types.SimpleNamespace()

        def baseline(_db):
            calls["baseline"] += 1
            return pd.DataFrame({
                "trade_date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03"]
                ),
                "candidate": ["TRACK_B_BASELINE_FAILURE"] * 3,
                "spread": [1.0, 2.0, 3.0],
            })

        def conditional(_db):
            calls["conditional"] += 1
            return pd.DataFrame({
                "trade_date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02"]
                ),
                "candidate": ["TRACK_B_CONDITIONAL_SCORE"] * 2,
                "spread": [4.0, 5.0],
            })

        def agreement(_db):
            calls["agreement"] += 1
            return pd.DataFrame({
                "trade_date": pd.to_datetime(
                    ["2026-01-01"]
                ),
                "candidate": ["TRACK_B_FACTOR_AGREEMENT"],
                "spread": [6.0],
            })

        def load_scenarios(_db):
            return pd.DataFrame({
                "trade_date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03"]
                ),
                "index_name": ["NIFTY50"] * 3,
                "primary_scenario": ["TREND_UP"] * 3,
                "scenario_id": ["S1", "S2", "S9"],
                "fingerprint": ["FP1", "FP2", "OTHER"],
            })

        def attach(evidence, scenarios):
            calls["attach"] += 1
            return evidence.merge(
                scenarios[
                    ["trade_date", "scenario_id", "fingerprint"]
                ],
                on="trade_date",
                how="left",
            )

        def evaluate(frame):
            calls["evaluate"] += 1
            return {
                "evidence_status": "OOS_EVALUATED",
                "research_status": "VALIDATION_READY",
                "train_observations": len(frame),
                "holdout_observations": 0,
                "train_start": frame["trade_date"].min(),
                "train_end": frame["trade_date"].max(),
                "holdout_start": None,
                "holdout_end": None,
                "train_average_spread": frame["spread"].mean(),
                "train_median_spread": frame["spread"].median(),
                "train_positive_day_pct": 100.0,
                "oos_average_spread": None,
                "oos_median_spread": None,
                "oos_positive_day_pct": None,
                "oos_worst_day": None,
                "oos_best_day": None,
                "oos_result": "OOS_RESULT_AVAILABLE",
            }

        adapter.load_baseline_results = baseline
        adapter.load_conditional_results = conditional
        adapter.load_agreement_results = agreement
        adapter.load_scenario_history = load_scenarios
        adapter.attach_scenarios = attach
        adapter.evaluate_holdout = evaluate

        track_c_adapter = types.SimpleNamespace()

        def execute_track_c_relationship(scenario_id, fingerprint, candidate, _db):
            calls["track_c"] += 1
            self.assertEqual(scenario_id, "S1")
            self.assertEqual(fingerprint, "FP1")
            self.assertEqual(candidate, "TRACK_C_SCENARIO_WEAPON")
            return {
                "candidate": candidate,
                "scenario_id": scenario_id,
                "fingerprint": fingerprint,
                "research_status": "EXECUTED",
                "oos_result": "OOS_AVAILABLE",
                "holdout_observations": 5,
                "scenario_matched_observations": 20,
                "execution_reason": "Track-C adapter executed exact relationship.",
                "oos_average_spread": 0.25,
                "oos_median_spread": 0.20,
                "oos_positive_day_pct": 60.0,
                "oos_worst_day": -1.0,
                "oos_best_day": 2.0,
            }

        track_c_adapter.execute_track_c_relationship = execute_track_c_relationship

        original = sys.modules.get("research.scenario_weapon_oos")
        original_track_c = sys.modules.get("research.scenario_weapon_track_c_oos_adapter")
        sys.modules["research.scenario_weapon_oos"] = adapter
        sys.modules["research.scenario_weapon_track_c_oos_adapter"] = track_c_adapter
        try:
            batches = make_batches()
            # Add another unsupported executable Track-C relationship.
            extra = batches.iloc[[0]].copy()
            extra["batch_id"] = "B4"
            extra["candidate"] = "TRACK_C_SCENARIO_WEAPON"
            extra["batch_action"] = "START_OOS_BATCH"
            extra["scenario_id"] = "S1"
            extra["fingerprint"] = "FP1"
            batches = pd.concat([batches, extra], ignore_index=True)
            batch_path = self.root / "batches.csv"
            output_path = self.root / "output.csv"
            batches.to_csv(batch_path, index=False)

            report = execute(
                db_path=self.root / "fake.db",
                batch_path=batch_path,
                output_path=output_path,
            )

            # B1/B2 use the unchanged Track-B paths; B4 uses the
            # candidate-specific Track-C adapter; B3 waits.
            self.assertEqual(len(report), 3)
            status_by_batch = dict(
                zip(report["batch_id"], report["execution_status"])
            )
            self.assertEqual(status_by_batch["B1"], "EXECUTED")
            self.assertEqual(status_by_batch["B2"], "EXECUTED")
            self.assertEqual(status_by_batch["B4"], "EXECUTED")

            # Track-B loaders execute at most once each, not once per
            # relationship. Track-C is routed through the independent adapter.
            self.assertEqual(calls["baseline"], 1)
            self.assertEqual(calls["conditional"], 1)
            self.assertEqual(calls["agreement"], 0)
            self.assertEqual(calls["attach"], 2)
            self.assertEqual(calls["evaluate"], 2)
            self.assertEqual(calls["track_c"], 1)

            # Exact scenario/fingerprint filtering was applied.
            b1 = report.loc[report["batch_id"] == "B1"].iloc[0]
            self.assertEqual(b1["scenario_matched_observations"], 1)
            self.assertEqual(b1["historical_observations"], 1)

            b2 = report.loc[report["batch_id"] == "B2"].iloc[0]
            self.assertEqual(b2["scenario_matched_observations"], 1)

            b4 = report.loc[report["batch_id"] == "B4"].iloc[0]
            self.assertEqual(b4["candidate"], "TRACK_C_SCENARIO_WEAPON")
            self.assertEqual(b4["scenario_id"], "S1")
            self.assertEqual(b4["fingerprint"], "FP1")
            self.assertEqual(b4["holdout_observations"], 5)
            self.assertEqual(b4["scenario_matched_observations"], 20)

            self.assertTrue(output_path.exists())
        finally:
            if original is None:
                sys.modules.pop("research.scenario_weapon_oos", None)
            else:
                sys.modules["research.scenario_weapon_oos"] = original
            if original_track_c is None:
                sys.modules.pop("research.scenario_weapon_track_c_oos_adapter", None)
            else:
                sys.modules["research.scenario_weapon_track_c_oos_adapter"] = original_track_c

    def test_track_c_candidates_are_explicitly_routed(self):
        self.assertEqual(
            TRACK_C_CANDIDATES,
            {
                "TRACK_C_FACTOR_INTERACTION",
                "TRACK_C_REGIME_AWARE",
                "TRACK_C_SCENARIO_WEAPON",
            },
        )

    def test_duplicate_relationships_raise(self):
        frame = make_batches()
        duplicate = frame.iloc[[0]].copy()
        bad = pd.concat([frame, duplicate], ignore_index=True)
        path = self.root / "bad.csv"
        bad.to_csv(path, index=False)
        with self.assertRaises(ValueError):
            load_batches(path)

    def test_missing_columns_raise(self):
        frame = make_batches().drop(columns=["batch_action"])
        path = self.root / "missing.csv"
        frame.to_csv(path, index=False)
        with self.assertRaises(ValueError):
            load_batches(path)


if __name__ == "__main__":
    unittest.main()
