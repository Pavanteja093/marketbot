import unittest

import numpy as np
import pandas as pd

from research.scenario_weapon_candidate import (
    Config,
    WEAPONS,
    evaluate_day,
    score_weapon,
    summarize,
)


class ScenarioWeaponCandidateTests(unittest.TestCase):

    def make_frame(self, n=20):
        return pd.DataFrame(
            {
                "index_name": [
                    f"S{i:02d}.NS"
                    for i in range(n)
                ],
                "trend_score": np.arange(n, dtype=float),
                "momentum_score": np.arange(
                    n, 0, -1, dtype=float
                ),
                "relative_strength": np.linspace(
                    10, 30, n
                ),
                "volatility_score": np.linspace(
                    20, 40, n
                ),
                "liquidity_score": np.linspace(
                    30, 50, n
                ),
                "return_5d": np.linspace(
                    -2, 2, n
                ),
            }
        )

    def test_weapons_are_fixed_and_small(self):
        self.assertEqual(len(WEAPONS), 4)

        for factors in WEAPONS.values():
            self.assertIn(len(factors), (2, 3))

    def test_score_is_finite(self):
        frame = self.make_frame()

        score = score_weapon(
            frame,
            WEAPONS["TREND_MOMENTUM"],
        )

        self.assertEqual(len(score), len(frame))
        self.assertTrue(
            np.isfinite(score).all()
        )

    def test_score_does_not_mutate_input(self):
        frame = self.make_frame()
        original = frame.copy(deep=True)

        score_weapon(
            frame,
            WEAPONS["RELATIVE_STRENGTH_TREND"],
        )

        pd.testing.assert_frame_equal(
            frame,
            original,
        )

    def test_evaluate_day_returns_spread(self):
        frame = self.make_frame()

        result = evaluate_day(
            frame,
            WEAPONS["TREND_MOMENTUM"],
            min_stocks=10,
        )

        self.assertIsNotNone(result)
        self.assertIn("spread", result)
        self.assertTrue(
            np.isfinite(result["spread"])
        )

    def test_evaluate_day_rejects_small_sample(self):
        frame = self.make_frame(8)

        result = evaluate_day(
            frame,
            WEAPONS["TREND_MOMENTUM"],
            min_stocks=10,
        )

        self.assertIsNone(result)

    def test_summary(self):
        results = pd.DataFrame(
            {
                "weapon": [
                    "TREND_MOMENTUM",
                    "TREND_MOMENTUM",
                    "TREND_MOMENTUM",
                ],
                "scenario": [
                    "TREND_UP",
                    "TREND_UP",
                    "TREND_UP",
                ],
                "spread": [
                    1.0,
                    -0.5,
                    0.5,
                ],
            }
        )

        summary = summarize(results)

        self.assertEqual(len(summary), 1)
        self.assertEqual(
            summary.iloc[0]["days"],
            3,
        )
        self.assertAlmostEqual(
            summary.iloc[0]["mean_spread"],
            1 / 3,
        )
        self.assertAlmostEqual(
            summary.iloc[0]["positive_day_pct"],
            66.6666666667,
            places=5,
        )

    def test_config_is_conservative(self):
        config = Config()

        self.assertEqual(
            config.train_days,
            120,
        )

        self.assertEqual(
            config.test_days,
            20,
        )

        self.assertEqual(
            config.min_stocks,
            10,
        )


if __name__ == "__main__":
    unittest.main()
