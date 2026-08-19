import unittest
import pandas as pd
from research.v2_track_c_interaction_evidence_synthesis import synthesize

KEYS=["scenario","factor_a","state_a","factor_b","state_b"]

def cov(**kw):
    d={"scenario":"TREND_UP","factor_a":"trend_score","state_a":"HIGH","factor_b":"momentum_score","state_b":"HIGH",
       "total_candidate_observations":49,"total_scenario_episodes":19,"episodes_with_candidate":13,"episode_coverage_pct":68.4,
       "qualifying_episodes_ge_20":0,"max_episode_observations":13,"mean_observations_per_occupied_episode":3.7,
       "median_observations_per_occupied_episode":3,"max_episode_concentration_pct":26.5}
    d.update(kw); return pd.DataFrame([d])

def oos(**kw):
    d={"scenario":"TREND_UP","factor_a":"trend_score","state_a":"HIGH","factor_b":"momentum_score","state_b":"HIGH",
       "observations":50,"up_pct":76.0,"mean_return_5d":1.2,"oos_folds":3,"oos_stability":"STABLE"}
    d.update(kw); return pd.DataFrame([d])

class T(unittest.TestCase):
    def test_candidate_matching(self):
        r=synthesize(cov(), pd.DataFrame(), oos())
        self.assertEqual(len(r),1); self.assertEqual(r.iloc[0].oos_observations,50)
    def test_missing_oos(self):
        r=synthesize(cov(), pd.DataFrame(), oos().iloc[0:0])
        self.assertEqual(r.iloc[0].evidence_classification,"NO_OOS_EVIDENCE")
    def test_zero_observation(self):
        r=synthesize(cov(total_candidate_observations=0), pd.DataFrame(), oos())
        self.assertEqual(r.iloc[0].evidence_classification,"NO_HISTORICAL_EVIDENCE")
    def test_sparse(self):
        r=synthesize(cov(), pd.DataFrame(), oos(oos_stability="SINGLE_FOLD",oos_folds=1))
        self.assertEqual(r.iloc[0].evidence_classification,"RECURRENT_BUT_SPARSE")
    def test_ge20_is_not_auto_stable(self):
        r=synthesize(cov(qualifying_episodes_ge_20=1,max_episode_observations=26), pd.DataFrame(), oos(oos_stability="SINGLE_FOLD",oos_folds=1))
        self.assertEqual(r.iloc[0].evidence_classification,"RECURRENT_BUT_SPARSE")
    def test_multi_source_class(self):
        r=synthesize(cov(qualifying_episodes_ge_20=2), pd.DataFrame(), oos())
        self.assertEqual(r.iloc[0].evidence_classification,"MULTI_SOURCE_REPEATABLE_EVIDENCE")
    def test_deterministic(self):
        a=synthesize(cov(),pd.DataFrame(),oos()); b=synthesize(cov(),pd.DataFrame(),oos()); pd.testing.assert_frame_equal(a,b)
    def test_inputs_not_mutated(self):
        a=cov(); b=a.copy(deep=True); synthesize(a,pd.DataFrame(),oos()); pd.testing.assert_frame_equal(a,b)
    def test_required_validation(self):
        with self.assertRaises(ValueError): synthesize(cov().drop(columns=["episode_coverage_pct"]),pd.DataFrame(),oos())
    def test_conservative_insufficient(self):
        r=synthesize(cov(qualifying_episodes_ge_20=3),pd.DataFrame(),oos(oos_stability="INSUFFICIENT_EPISODES",oos_folds=2))
        self.assertNotEqual(r.iloc[0].evidence_classification,"MULTI_SOURCE_REPEATABLE_EVIDENCE")

if __name__=="__main__": unittest.main()