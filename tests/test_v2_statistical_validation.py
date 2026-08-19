import unittest

from research.v2_statistical_validation import (
    bootstrap_mean_ci,
    mean_ci_95,
    pearson,
    spearman,
    validate,
)


class V2StatisticalValidationTests(unittest.TestCase):

    def test_insufficient_data(self):
        result = validate([])
        self.assertEqual(result["sample_size"], 0)
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result["pearson_p_value"])

    def test_correlations(self):
        xs = [1, 2, 3, 4, 5]
        ys = [2, 4, 6, 8, 10]

        self.assertAlmostEqual(pearson(xs, ys), 1.0)
        self.assertAlmostEqual(spearman(xs, ys), 1.0)

    def test_confidence_intervals(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]

        ci = mean_ci_95(values)
        bootstrap = bootstrap_mean_ci(values, iterations=500, seed=42)

        self.assertIsNotNone(ci)
        self.assertIsNotNone(bootstrap)
        self.assertLess(ci[0], ci[1])
        self.assertLess(bootstrap[0], bootstrap[1])

    def test_validation_metrics(self):
        rows = [
            ("2026-01-01", "A.NS", "AUTO", 1, 90.0, 5.0),
            ("2026-01-01", "B.NS", "IT", 2, 80.0, 3.0),
            ("2026-01-01", "C.NS", "BANKING", 3, 70.0, 1.0),
            ("2026-01-01", "D.NS", "AUTO", 11, 60.0, -2.0),
            ("2026-01-01", "E.NS", "IT", 12, 50.0, -3.0),
        ]

        result = validate(
            rows,
            permutations=200,
            bootstrap_iterations=200,
        )

        self.assertEqual(result["sample_size"], 5)
        self.assertEqual(result["status"], "VALID")
        self.assertGreater(result["pearson"], 0)
        self.assertGreater(result["spearman"], 0)
        self.assertGreater(result["top10_vs_universe_spread"], 0)
        self.assertIsNotNone(result["pearson_p_value"])
        self.assertIsNotNone(result["spearman_p_value"])


if __name__ == "__main__":
    unittest.main()
