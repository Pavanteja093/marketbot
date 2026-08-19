import unittest

from research.v2_performance import analyze


class V2PerformanceTests(unittest.TestCase):

    def test_empty_data(self):
        result = analyze([])
        self.assertEqual(result["sample_size"], 0)
        self.assertIsNone(result["pearson_score_return"])

    def test_score_return_analysis(self):
        rows = [
            ("2026-01-01", "A.NS", "AUTO", 1, 90.0, 5.0),
            ("2026-01-01", "B.NS", "BANKING", 2, 80.0, 3.0),
            ("2026-01-01", "C.NS", "IT", 3, 70.0, 1.0),
            ("2026-01-02", "D.NS", "AUTO", 1, 85.0, 4.0),
            ("2026-01-02", "E.NS", "IT", 2, 65.0, -1.0),
        ]

        result = analyze(rows)

        self.assertEqual(result["sample_size"], 5)
        self.assertAlmostEqual(result["mean_return_5d"], 2.4)
        self.assertEqual(result["top1"]["n"], 2)
        self.assertEqual(result["top3"]["n"], 5)
        self.assertGreater(result["pearson_score_return"], 0)
        self.assertEqual(result["score_buckets"]["80+"]["n"], 3)


if __name__ == "__main__":
    unittest.main()
