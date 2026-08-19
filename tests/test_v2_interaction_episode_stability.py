import unittest
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'research')); import v2_interaction_episode_stability as m

class InteractionEpisodeStabilityTests(unittest.TestCase):
    def test_state_thresholds_are_train_only(self):
        train = pd.DataFrame({
            'scenario':['A']*4,
            'x':[1.,2.,3.,4.],
            'y':[4.,3.,2.,1.],
        })
        test = pd.DataFrame({
            'scenario':['A','A'],
            'x':[100.,0.],
            'y':[100.,0.],
        })
        tr, te = m.state_frame(train,test,'x','y')
        self.assertEqual(tr['state_a'].tolist(), ['LOW','LOW','HIGH','HIGH'])
        self.assertEqual(te['state_a'].tolist(), ['HIGH','LOW'])
        self.assertEqual(te['state_b'].tolist(), ['HIGH','LOW'])

    def test_laplace_baseline_is_finite(self):
        p = m.scenario_baseline(pd.DataFrame({'scenario':['A','A'], 'label':['UP','UP']}), 'A')
        self.assertAlmostEqual(float(p.sum()), 1.0)
        self.assertTrue((p > 0).all())

    def test_stability_requires_three_episodes(self):
        # The production module uses MIN_REPEAT_EPISODES=3.
        self.assertEqual(m.MIN_REPEAT_EPISODES, 3)

if __name__ == '__main__':
    unittest.main(verbosity=2)


