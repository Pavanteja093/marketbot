import unittest
from research.v2_validation_report import build_report, classify


class V2ValidationReportTests(unittest.TestCase):
    def test_zero_outcomes(self):
        report = build_report(rows=[], permutations=100, bootstrap_iterations=100)
        self.assertEqual(report["classification"], "INSUFFICIENT DATA")
        self.assertEqual(report["sample_size"], 0)
        self.assertEqual(report["production_action"], "NO CHANGE")

    def test_early_sample(self):
        rows = [
            ("2026-01-01", "A.NS", "AUTO", 1, 90.0, 5.0),
            ("2026-01-01", "B.NS", "IT", 2, 80.0, 3.0),
            ("2026-01-01", "C.NS", "BANKING", 3, 70.0, 1.0),
        ]
        report = build_report(rows=rows, permutations=100, bootstrap_iterations=100)
        self.assertEqual(report["classification"], "EARLY / EXPLORATORY")
        self.assertEqual(report["sample_size"], 3)
        self.assertEqual(report["production_action"], "NO CHANGE")

    def test_classification_thresholds(self):
        self.assertEqual(classify(0, {}), "INSUFFICIENT DATA")
        self.assertEqual(classify(29, {}), "EARLY / EXPLORATORY")
        self.assertEqual(classify(30, {}), "DEVELOPING EVIDENCE")
        self.assertEqual(classify(99, {}), "DEVELOPING EVIDENCE")

    def test_supportive_requires_strong_evidence(self):
        stats = {"pearson_p_value": 0.01, "spearman_p_value": 0.02,
                 "top10_vs_universe_spread": 1.5}
        self.assertEqual(classify(200, stats), "STATISTICALLY SUPPORTIVE")

    def test_no_predictive_evidence(self):
        stats = {"pearson_p_value": 0.70, "spearman_p_value": 0.80,
                 "top10_vs_universe_spread": -0.5}
        self.assertEqual(classify(100, stats), "NO PREDICTIVE EVIDENCE")


if __name__ == "__main__":
    unittest.main()
