import unittest

from research.candidate_gate_runner import (
    _adapter_agreement,
    _adapter_conditional,
    _adapter_interaction,
    _adapter_regime,
    _direct_gate_from_summary,
    _parse_window_spreads,
)


class CandidateGateRunnerTests(unittest.TestCase):

    def test_parse_regime_windows(self):
        text = """
        WINDOW 1
        Spread        : +0.1456%

        WINDOW 2
        Spread        : -1.6343%

        WINDOW 3
        Spread        : -0.2730%
        """

        self.assertEqual(
            _parse_window_spreads(text),
            [0.1456, -1.6343, -0.2730],
        )

    def test_regime_adapter(self):
        text = """
        WINDOW 1
        Spread : +0.5000%

        WINDOW 2
        Spread : -0.2500%
        """

        result = _adapter_regime(text)

        self.assertEqual(result["windows"], 2)
        self.assertEqual(
            result["spreads"],
            [0.5, -0.25],
        )

    def test_conditional_adapter(self):
        text = """
        OOS SUMMARY
        {'days': 100, 'average_spread': -0.4472943,
         'median_spread': -0.21694,
         'positive_day_pct': 44.0}
        """

        result = _adapter_conditional(text)

        self.assertEqual(result["windows"], 100)
        self.assertAlmostEqual(
            result["average"],
            -0.4472943,
        )
        self.assertAlmostEqual(
            result["median"],
            -0.21694,
        )
        self.assertEqual(
            result["positive_pct"],
            44.0,
        )

    def test_agreement_adapter(self):
        text = """
        AGREEMENT-CONDITIONED OOS

        condition  days  mean_spread  median_spread  positive_day_pct  worst_day  best_day
        ALL_DAYS   100      -0.5486        -0.4737             42.00    -5.7562    4.6171
        """

        result = _adapter_agreement(text)

        self.assertEqual(result["windows"], 100)
        self.assertAlmostEqual(result["average"], -0.5486)
        self.assertAlmostEqual(result["median"], -0.4737)
        self.assertAlmostEqual(result["positive_pct"], 42.0)
        self.assertAlmostEqual(result["worst"], -5.7562)
        self.assertAlmostEqual(result["best"], 4.6171)

    def test_interaction_adapter(self):
        text = """
        Incremental   : -0.0315%
        Incremental   : +0.0000%
        Incremental   : -0.0027%
        """

        result = _adapter_interaction(text)

        self.assertEqual(
            result["spreads"],
            [-0.0315, 0.0, -0.0027],
        )

    def test_summary_gate_fails_negative_candidate(self):
        result = _direct_gate_from_summary(
            {
                "windows": 100,
                "average": -0.35,
                "median": -0.40,
                "positive_pct": 41.0,
                "worst": -4.96,
                "best": 4.07,
            }
        )

        self.assertEqual(result["decision"], "FAIL")

    def test_summary_gate_passes_strong_candidate(self):
        result = _direct_gate_from_summary(
            {
                "windows": 10,
                "average": 0.50,
                "median": 0.40,
                "positive_pct": 70.0,
                "worst": -1.0,
                "best": 2.0,
            }
        )

        self.assertEqual(result["decision"], "PASS")

    def test_runner_candidate_count(self):
        from research.candidate_gate_runner import CANDIDATES

        self.assertEqual(len(CANDIDATES), 6)

    def test_runner_candidates_are_research_modules(self):
        from research.candidate_gate_runner import CANDIDATES

        self.assertTrue(
            all(
                candidate.module.startswith("research.")
                for candidate in CANDIDATES
            )
        )


if __name__ == "__main__":
    unittest.main()
