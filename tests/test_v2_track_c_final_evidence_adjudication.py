from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from research.v2_track_c_final_evidence_adjudication import adjudicate


KEYS = ["scenario", "factor_a", "state_a", "factor_b", "state_b"]


def key_row(factor_a="trend_score", factor_b="momentum_score"):
    return {
        "scenario": "TREND_UP",
        "factor_a": factor_a,
        "state_a": "HIGH",
        "factor_b": factor_b,
        "state_b": "HIGH",
    }


def evidence_row(**overrides):
    row = key_row()
    row.update({
        "total_candidate_observations": 100,
        "qualifying_episodes_ge_20": 2,
        "oos_observations": 500,
        "oos_oos_folds": 8,
        "oos_stability": "REPEATED",
        "evidence_classification": "RECURRENT_BUT_SPARSE",
    })
    row.update(overrides)
    return row


def temporal_row(**overrides):
    row = key_row()
    row.update({
        "episode_count": 4,
        "qualifying_episode_count_ge_20": 2,
        "total_observations": 100,
        "temporal_robustness_classification": "MULTI_EPISODE_STABLE",
    })
    row.update(overrides)
    return row


def null_row(**overrides):
    row = key_row()
    row.update({
        "observations": 100,
        "raw_p_value": 0.001,
        "adjusted_p_value": 0.001,
        "null_result": "NULL_SIGNAL_SURVIVES_MULTIPLE_TESTING",
    })
    row.update(overrides)
    return row


class FinalEvidenceAdjudicationTests(unittest.TestCase):

    def test_multi_source_support(self):
        result = adjudicate(
            pd.DataFrame([evidence_row()]),
            pd.DataFrame([temporal_row()]),
            pd.DataFrame([null_row()]),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result.iloc[0]["final_evidence_classification"],
            "MULTI_SOURCE_SUPPORT",
        )

    def test_zero_historical_evidence_requires_all_sources_zero(self):
        result = adjudicate(
            pd.DataFrame([evidence_row(total_candidate_observations=0)]),
            pd.DataFrame([temporal_row()]),
            pd.DataFrame([null_row()]),
        )
        self.assertNotEqual(
            result.iloc[0]["final_evidence_classification"],
            "NO_HISTORICAL_EVIDENCE",
        )
        self.assertEqual(
            result.iloc[0]["evidence_lineage_status"],
            "CROSS_ARTIFACT_OBSERVATION_MISMATCH",
        )

    def test_all_sources_zero_is_no_historical_evidence(self):
        result = adjudicate(
            pd.DataFrame([evidence_row(total_candidate_observations=0)]),
            pd.DataFrame([temporal_row(total_observations=0)]),
            pd.DataFrame([null_row(observations=0, raw_p_value=np.nan, adjusted_p_value=np.nan)]),
        )
        self.assertEqual(
            result.iloc[0]["final_evidence_classification"],
            "NO_HISTORICAL_EVIDENCE",
        )

    def test_temporal_positive_overrides_synthesis_zero(self):
        result = adjudicate(
            pd.DataFrame([evidence_row(total_candidate_observations=0)]),
            pd.DataFrame([temporal_row(total_observations=100)]),
            pd.DataFrame([null_row(observations=100)]),
        )
        self.assertEqual(
            result.iloc[0]["temporal_observations"], 100
        )
        self.assertEqual(
            result.iloc[0]["final_evidence_classification"],
            "MULTI_SOURCE_SUPPORT",
        )

    def test_temporal_inconsistency_blocks_promotion(self):
        result = adjudicate(
            pd.DataFrame([evidence_row()]),
            pd.DataFrame([
                temporal_row(
                    temporal_robustness_classification="MULTI_EPISODE_INCONSISTENT"
                )
            ]),
            pd.DataFrame([null_row()]),
        )
        self.assertEqual(
            result.iloc[0]["final_evidence_classification"],
            "NO_REPEATABLE_EVIDENCE",
        )

    def test_strict_two_episode_gate_is_preserved(self):
        result = adjudicate(
            pd.DataFrame([evidence_row(qualifying_episodes_ge_20=1)]),
            pd.DataFrame([temporal_row(qualifying_episode_count_ge_20=1)]),
            pd.DataFrame([null_row()]),
        )
        self.assertEqual(
            result.iloc[0]["final_evidence_classification"],
            "NO_REPEATABLE_EVIDENCE",
        )

    def test_oos_insufficiency_blocks_promotion(self):
        result = adjudicate(
            pd.DataFrame([evidence_row(oos_oos_folds=1, oos_stability="SINGLE_FOLD")]),
            pd.DataFrame([temporal_row()]),
            pd.DataFrame([null_row()]),
        )
        self.assertEqual(
            result.iloc[0]["final_evidence_classification"],
            "INSUFFICIENT_OOS_EVIDENCE",
        )

    def test_null_multiple_testing_failure_blocks_promotion(self):
        result = adjudicate(
            pd.DataFrame([evidence_row()]),
            pd.DataFrame([temporal_row()]),
            pd.DataFrame([
                null_row(
                    raw_p_value=0.004,
                    adjusted_p_value=1.0,
                    null_result="NULL_SIGNAL_PRESENT_BUT_INSUFFICIENT",
                )
            ]),
        )
        self.assertEqual(
            result.iloc[0]["final_evidence_classification"],
            "NO_REPEATABLE_EVIDENCE",
        )

    def test_missing_temporal_artifact_is_conservative(self):
        result = adjudicate(
            pd.DataFrame([evidence_row()]),
            pd.DataFrame(columns=list(KEYS) + [
                "episode_count",
                "qualifying_episode_count_ge_20",
                "total_observations",
                "temporal_robustness_classification",
            ]),
            pd.DataFrame([null_row()]),
        )
        self.assertEqual(
            result.iloc[0]["final_evidence_classification"],
            "INSUFFICIENT_TEMPORAL_EVIDENCE",
        )

    def test_candidate_matching(self):
        e = pd.DataFrame([
            evidence_row(),
            evidence_row(factor_a="volatility_score", factor_b="trend_score"),
        ])
        t = pd.DataFrame([
            temporal_row(),
            temporal_row(
                factor_a="volatility_score",
                factor_b="trend_score",
            ),
        ])
        n = pd.DataFrame([
            null_row(),
            null_row(
                factor_a="volatility_score",
                factor_b="trend_score",
            ),
        ])
        result = adjudicate(e, t, n)
        self.assertEqual(len(result), 2)
        self.assertEqual(
            set(result["factor_a"]),
            {"trend_score", "volatility_score"},
        )

    def test_inputs_are_not_mutated(self):
        e = pd.DataFrame([evidence_row()])
        t = pd.DataFrame([temporal_row()])
        n = pd.DataFrame([null_row()])
        e0, t0, n0 = e.copy(deep=True), t.copy(deep=True), n.copy(deep=True)
        adjudicate(e, t, n)
        pd.testing.assert_frame_equal(e, e0)
        pd.testing.assert_frame_equal(t, t0)
        pd.testing.assert_frame_equal(n, n0)

    def test_deterministic(self):
        e = pd.DataFrame([evidence_row()])
        t = pd.DataFrame([temporal_row()])
        n = pd.DataFrame([null_row()])
        a = adjudicate(e, t, n)
        b = adjudicate(e, t, n)
        pd.testing.assert_frame_equal(a, b)

    def test_required_column_validation(self):
        with self.assertRaises(ValueError):
            adjudicate(
                pd.DataFrame([key_row()]),
                pd.DataFrame([temporal_row()]),
                pd.DataFrame([null_row()]),
            )


if __name__ == "__main__":
    unittest.main()
