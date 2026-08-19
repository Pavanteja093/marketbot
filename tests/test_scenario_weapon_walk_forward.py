from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from research.scenario_weapon_walk_forward import (
    MIN_TRAIN_OBSERVATIONS,
    build_summary,
    build_walk_forward,
    evaluate_group,
)


class ScenarioWeaponWalkForwardTests(unittest.TestCase):

    def make_frame(self, spreads):
        dates = pd.date_range(
            "2026-01-01",
            periods=len(spreads),
            freq="D",
        )

        return pd.DataFrame(
            {
                "trade_date": dates,
                "candidate": "WEAPON_A",
                "scenario_id": "UNEXPLORED_1",
                "primary_scenario": "TREND_UP",
                "fingerprint": "FP_1",
                "spread": spreads,
            }
        )

    def test_insufficient_history_produces_no_windows(self):
        frame = self.make_frame([1, 2, 3, 4, 5, 6, 7, 8, 9])

        report, ledger = evaluate_group(frame)

        self.assertEqual(report, [])
        self.assertEqual(ledger, [])

    def test_walk_forward_is_chronological(self):
        frame = self.make_frame(
            [1, -1, 2, -2, 3, -3, 4, -4, 5, -5]
        )

        report, ledger = evaluate_group(frame)

        self.assertTrue(report)

        for row in report:
            self.assertLessEqual(
                row["train_end"],
                row["oos_start"],
            )

    def test_no_future_leakage(self):
        frame = self.make_frame(
            [1, 1, 1, 1, 1, 1, 1, 1, -100, -100]
        )

        report, ledger = evaluate_group(frame)

        self.assertTrue(report)

        first = report[0]

        self.assertEqual(
            first["train_observations"],
            MIN_TRAIN_OBSERVATIONS,
        )

        self.assertEqual(
            first["oos_average_spread"],
            1.0,
        )

    def test_multiple_oos_windows_are_created(self):
        frame = self.make_frame(
            list(range(1, 16))
        )

        report, ledger = evaluate_group(frame)

        self.assertGreater(len(report), 1)
        self.assertLessEqual(len(report), 5)

    def test_negative_oos_is_classified(self):
        frame = self.make_frame(
            [1, 1, 1, 1, 1, -5, -5, -5, -5, -5]
        )

        report, ledger = evaluate_group(frame)

        self.assertTrue(report)

        negative_rows = [
            row
            for row in report
            if row["oos_result"] == "NEGATIVE_OOS"
        ]

        self.assertTrue(negative_rows)

    def test_input_is_not_mutated(self):
        frame = self.make_frame(
            list(range(1, 11))
        )

        original = frame.copy(deep=True)

        build_walk_forward(frame)

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_summary_counts_positive_windows(self):
        frame = self.make_frame(
            [1, 1, 1, 1, 1, 2, 2, 2, -1, 2]
        )

        report, _ = evaluate_group(frame)

        summary = build_summary(
            pd.DataFrame(report)
        )

        self.assertEqual(
            len(summary),
            1,
        )

        self.assertGreaterEqual(
            int(summary.iloc[0]["oos_windows"]),
            1,
        )

    def test_build_walk_forward_supports_multiple_groups(self):
        first = self.make_frame(
            list(range(1, 11))
        )

        second = self.make_frame(
            list(range(-10, 0))
        )

        second["candidate"] = "WEAPON_B"
        second["scenario_id"] = "UNEXPLORED_2"
        second["primary_scenario"] = "TREND_DOWN"

        combined = pd.concat(
            [first, second],
            ignore_index=True,
        )

        report, ledger = build_walk_forward(
            combined
        )

        self.assertGreater(len(report), 0)
        self.assertGreater(len(ledger), 0)

        self.assertEqual(
            set(report["candidate"]),
            {"WEAPON_A", "WEAPON_B"},
        )

    def test_summary_is_deterministic(self):
        frame = self.make_frame(
            list(range(1, 16))
        )

        report, _ = evaluate_group(frame)

        summary_a = build_summary(
            pd.DataFrame(report)
        )

        summary_b = build_summary(
            pd.DataFrame(report)
        )

        pd.testing.assert_frame_equal(
            summary_a,
            summary_b,
        )


if __name__ == "__main__":
    unittest.main()
