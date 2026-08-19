import unittest

import pandas as pd

from research.candidate_gate import evaluate


class CandidateGateTests(unittest.TestCase):

    def test_strong_candidate_passes(self):
        results = pd.DataFrame({"spread": [0.5, 0.8, 0.3, 1.0, 0.7]})
        result = evaluate(results)

        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["passed_checks"], 5)
        self.assertEqual(result["total_checks"], 5)

    def test_insufficient_windows_requires_review(self):
        results = pd.DataFrame({"spread": [0.5, 0.8, 0.3, 1.0]})
        result = evaluate(results)

        self.assertEqual(result["decision"], "REVIEW")
        self.assertFalse(result["checks"]["minimum_windows"])

    def test_three_checks_pass_means_review(self):
        results = pd.DataFrame({"spread": [1.0, 1.0, 1.0, -3.0, -3.0]})
        result = evaluate(results)

        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(result["passed_checks"], 3)

    def test_bad_candidate_fails(self):
        results = pd.DataFrame({"spread": [-3.0, -3.0, -3.0, -3.0, -3.0]})
        result = evaluate(results)

        self.assertEqual(result["decision"], "FAIL")

    def test_nan_values_are_ignored(self):
        results = pd.DataFrame({
            "spread": [1.0, 1.0, float("nan"), 1.0, 1.0, 1.0]
        })
        result = evaluate(results)

        self.assertEqual(result["metrics"]["windows"], 5)
        self.assertEqual(result["decision"], "PASS")

    def test_missing_spread_column_does_not_crash(self):
        results = pd.DataFrame({"other_column": [1, 2, 3]})
        result = evaluate(results)

        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["metrics"]["windows"], 0)

    def test_custom_rules_are_applied(self):
        results = pd.DataFrame({"spread": [0.5, 0.8, 0.3, 1.0, 0.7]})
        result = evaluate(results, {"min_windows": 10})

        self.assertFalse(result["checks"]["minimum_windows"])
        self.assertEqual(result["decision"], "REVIEW")

    def test_metrics_are_returned(self):
        results = pd.DataFrame({"spread": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = evaluate(results)

        self.assertEqual(result["metrics"]["windows"], 5)
        self.assertEqual(result["metrics"]["average_spread"], 3.0)
        self.assertEqual(result["metrics"]["median_spread"], 3.0)
        self.assertEqual(result["metrics"]["positive_window_pct"], 100.0)
        self.assertEqual(result["metrics"]["worst_window"], 1.0)


if __name__ == "__main__":
    unittest.main()