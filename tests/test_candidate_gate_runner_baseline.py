import unittest

from research.candidate_gate_runner import _adapter_baseline


class BaselineAdapterRegressionTests(unittest.TestCase):

    def test_baseline_oos_table_is_parsed(self):
        text = """
        OVERALL BASELINE OOS
        days  mean_spread  median_spread  positive_day_pct  worst_day  best_day
        100   -0.3577      -0.4014        41.0              -4.9624    4.0734
        """

        result = _adapter_baseline(text)

        self.assertEqual(result["windows"], 100)
        self.assertAlmostEqual(result["average"], -0.3577)
        self.assertAlmostEqual(result["median"], -0.4014)
        self.assertAlmostEqual(result["positive_pct"], 41.0)
        self.assertAlmostEqual(result["worst"], -4.9624)
        self.assertAlmostEqual(result["best"], 4.0734)

    def test_baseline_gate_is_negative_candidate(self):
        text = """
        OVERALL BASELINE OOS
        days  mean_spread  median_spread  positive_day_pct  worst_day  best_day
        100   -0.3577      -0.4014        41.0              -4.9624    4.0734
        """

        result = _adapter_baseline(text)

        from research.candidate_gate_runner import _direct_gate_from_summary

        gate = _direct_gate_from_summary(result)

        self.assertEqual(gate["decision"], "FAIL")
        self.assertEqual(gate["passed_checks"], 1)
        self.assertEqual(gate["total_checks"], 5)


if __name__ == "__main__":
    unittest.main()
