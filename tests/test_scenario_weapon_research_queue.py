from __future__ import annotations

import unittest
import pandas as pd

from research.scenario_weapon_research_queue import (
    OUTPUT_COLUMNS,
    TARGET_OOS_WINDOWS,
    build_queue,
)


def row(
    scenario_id="UNEXPLORED_20",
    primary_scenario="TREND_DOWN",
    fingerprint="fp1",
    candidate="TRACK_B_BASELINE_FAILURE",
    observations=28,
    oos_windows=5,
    eligibility_status="EVIDENCE_PRESENT_EARLY",
    research_priority="HIGH",
):
    return {
        "scenario_id": scenario_id,
        "primary_scenario": primary_scenario,
        "fingerprint": fingerprint,
        "candidate": candidate,
        "scenario_observations": observations,
        "oos_windows": oos_windows,
        "oos_gap_to_10": max(10 - oos_windows, 0),
        "oos_gap_to_20": max(20 - oos_windows, 0),
        "evidence_status": "EARLY",
        "coverage_status": "EVIDENCE_PRESENT",
        "eligibility_status": eligibility_status,
        "research_priority": research_priority,
        "recommended_action": "CONTINUE_OOS",
    }


class ScenarioWeaponResearchQueueTests(unittest.TestCase):
    def test_deterministic_output(self):
        frame = pd.DataFrame([
            row(candidate="B"),
            row(candidate="A", oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="HIGH"),
            row(candidate="C", oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="MEDIUM"),
        ])
        first = build_queue(frame)
        second = build_queue(frame.sample(frac=1, random_state=7))
        pd.testing.assert_frame_equal(first, second)

    def test_input_is_not_mutated(self):
        frame = pd.DataFrame([row()])
        original = frame.copy(deep=True)
        build_queue(frame)
        pd.testing.assert_frame_equal(frame, original)

    def test_all_input_relationships_are_preserved(self):
        frame = pd.DataFrame([
            row(candidate="A"),
            row(candidate="B", scenario_id="UNEXPLORED_17", observations=15,
                oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="MEDIUM"),
            row(candidate="C", scenario_id="UNEXPLORED_1", observations=1,
                oos_windows=0,
                eligibility_status="INSUFFICIENT_SCENARIO_HISTORY",
                research_priority="LOW"),
        ])
        result = build_queue(frame)
        self.assertEqual(len(result), len(frame))
        self.assertEqual(
            set(zip(result.scenario_id, result.candidate)),
            set(zip(frame.scenario_id, frame.candidate)),
        )

    def test_p0_continuation_logic(self):
        result = build_queue(pd.DataFrame([
            row(oos_windows=5)
        ]))
        r = result.iloc[0]
        self.assertEqual(r.queue_priority, "P0")
        self.assertEqual(r.queue_action, "CONTINUE_OOS")
        self.assertEqual(r.oos_gap_to_target, 5)

    def test_p1_start_oos_logic(self):
        result = build_queue(pd.DataFrame([
            row(
                oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="HIGH",
                observations=28,
            )
        ]))
        r = result.iloc[0]
        self.assertEqual(r.queue_priority, "P1")
        self.assertEqual(r.queue_action, "START_OOS_RESEARCH")

    def test_p2_medium_coverage_logic(self):
        result = build_queue(pd.DataFrame([
            row(
                scenario_id="UNEXPLORED_17",
                observations=15,
                oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="MEDIUM",
            )
        ]))
        r = result.iloc[0]
        self.assertEqual(r.queue_priority, "P2")
        self.assertEqual(r.queue_action, "START_OOS_RESEARCH")

    def test_p3_insufficient_history_logic(self):
        result = build_queue(pd.DataFrame([
            row(
                observations=3,
                oos_windows=0,
                eligibility_status="INSUFFICIENT_SCENARIO_HISTORY",
                research_priority="LOW",
            )
        ]))
        r = result.iloc[0]
        self.assertEqual(r.queue_priority, "P3")
        self.assertEqual(r.queue_action, "WAIT_FOR_SCENARIO_HISTORY")

    def test_oos_gap_calculation(self):
        frame = pd.DataFrame([
            row(oos_windows=5),
            row(candidate="B", oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="HIGH"),
            row(candidate="C", oos_windows=10),
        ])
        result = build_queue(frame)
        gaps = dict(
            zip(
                result.candidate,
                result.oos_gap_to_target,
            )
        )
        self.assertEqual(
            gaps["TRACK_B_BASELINE_FAILURE"],
            5,
        )
        self.assertEqual(
            gaps["B"],
            10,
        )
        self.assertEqual(
            gaps["C"],
            0,
        )
        self.assertEqual(TARGET_OOS_WINDOWS, 10)

    def test_priority_ordering(self):
        frame = pd.DataFrame([
            row(candidate="P3", observations=2, oos_windows=0,
                eligibility_status="INSUFFICIENT_SCENARIO_HISTORY",
                research_priority="LOW"),
            row(candidate="P2", observations=15, oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="MEDIUM"),
            row(candidate="P1", observations=28, oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="HIGH"),
            row(candidate="P0", oos_windows=5),
        ])
        result = build_queue(frame)
        self.assertEqual(list(result.queue_priority), ["P0", "P1", "P2", "P3"])

    def test_high_research_priority_beats_medium_within_p1_start_work(self):
        frame = pd.DataFrame([
            row(candidate="MEDIUM", observations=28, oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="MEDIUM"),
            row(candidate="HIGH", observations=28, oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="HIGH"),
        ])
        result = build_queue(frame)
        self.assertEqual(result.iloc[0].candidate, "HIGH")

    def test_missing_required_columns(self):
        frame = pd.DataFrame([{"scenario_id": "UNEXPLORED_1"}])
        with self.assertRaises(ValueError) as ctx:
            build_queue(frame)
        self.assertIn("candidate", str(ctx.exception))

    def test_multiple_scenarios_and_weapons(self):
        frame = pd.DataFrame([
            row(scenario_id="UNEXPLORED_20", candidate="WEAPON_A", oos_windows=5),
            row(scenario_id="UNEXPLORED_20", candidate="WEAPON_B", oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="HIGH"),
            row(scenario_id="UNEXPLORED_17", candidate="WEAPON_A", observations=15,
                oos_windows=0,
                eligibility_status="RESEARCHABLE_NO_EVIDENCE",
                research_priority="MEDIUM"),
        ])
        result = build_queue(frame)
        self.assertEqual(len(result), 3)
        self.assertEqual(result.iloc[0].queue_priority, "P0")
        self.assertEqual(result.iloc[1].queue_priority, "P1")
        self.assertEqual(result.iloc[2].queue_priority, "P2")

    def test_output_columns(self):
        result = build_queue(pd.DataFrame([row()]))
        self.assertEqual(list(result.columns), OUTPUT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
