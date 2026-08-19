import unittest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import importlib.util

MODULE_PATH = Path(__file__).resolve().parents[1] / 'research' / 'v2_track_c_interaction_null_validation.py'
spec = importlib.util.spec_from_file_location('nullmod', MODULE_PATH)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class NullValidationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = pd.DataFrame({
            'scenario':['TREND_UP']*30 + ['FLAT']*10,
            'label':['UP']*15+['DOWN']*10+['FLAT']*5+['UP']*5+['DOWN']*5,
            'return_5d':[1.0]*40,
        })
        self.search = pd.DataFrame([
            {'scenario':'TREND_UP','factor_a':'change_pct','factor_b':'trend_score','state_a':'HIGH','state_b':'HIGH','observations':6,'down_pct':0,'flat_pct':0,'up_pct':100,'mean_return_5d':1,'median_return_5d':1},
            {'scenario':'TREND_UP','factor_a':'intelligence_score','factor_b':'trend_score','state_a':'HIGH','state_b':'HIGH','observations':0,'down_pct':np.nan,'flat_pct':np.nan,'up_pct':np.nan,'mean_return_5d':np.nan,'median_return_5d':np.nan},
            {'scenario':'TREND_UP','factor_a':'relative_strength','factor_b':'trend_score','state_a':'HIGH','state_b':'HIGH','observations':6,'down_pct':50,'flat_pct':0,'up_pct':50,'mean_return_5d':0,'median_return_5d':0},
            {'scenario':'TREND_UP','factor_a':'trend_score','factor_b':'momentum_score','state_a':'HIGH','state_b':'HIGH','observations':6,'down_pct':50,'flat_pct':0,'up_pct':50,'mean_return_5d':0,'median_return_5d':0},
            {'scenario':'TREND_UP','factor_a':'trend_score','factor_b':'volatility_score','state_a':'HIGH','state_b':'HIGH','observations':6,'down_pct':50,'flat_pct':0,'up_pct':50,'mean_return_5d':0,'median_return_5d':0},
            {'scenario':'TREND_UP','factor_a':'trend_score','factor_b':'volatility_score','state_a':'HIGH','state_b':'LOW','observations':6,'down_pct':50,'flat_pct':0,'up_pct':50,'mean_return_5d':0,'median_return_5d':0},
        ])
    def test_candidate_matching_and_six_output(self):
        out=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        self.assertEqual(len(out),6); self.assertEqual(out.iloc[0].observations,6)
    def test_zero_observation(self):
        out=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        r=out[out.factor_a=='intelligence_score'].iloc[0]
        self.assertEqual(r.null_result,'NO_HISTORICAL_EVIDENCE'); self.assertEqual(r.permutations,0)
    def test_deterministic_seed(self):
        a=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        b=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        pd.testing.assert_frame_equal(a,b)
    def test_different_seed_changes_null_distribution(self):
        a=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        b=mod.validate(self.dataset,self.search,permutations=1000,seed=8)
        self.assertFalse(a.null_mean.equals(b.null_mean))
    def test_sample_size_preserved(self):
        out=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        self.assertTrue((out.loc[out.observations>0,'observations']==6).all())
    def test_empirical_p_nonzero(self):
        p=mod._empirical_p(np.array([1.,2.,3.]),3.)
        self.assertGreater(p,0); self.assertEqual(p,0.5)
    def test_scenario_restriction(self):
        labels=self.dataset[self.dataset.scenario=='TREND_UP'].label.map({'DOWN':0,'FLAT':1,'UP':2}).to_numpy()
        self.assertEqual(len(labels),30)
    def test_missing_columns(self):
        with self.assertRaises(ValueError): mod.validate(self.dataset.drop(columns='label'),self.search)
    def test_input_immutability(self):
        d=self.dataset.copy(deep=True); s=self.search.copy(deep=True)
        mod.validate(d,s,permutations=1000,seed=7)
        pd.testing.assert_frame_equal(d,self.dataset); pd.testing.assert_frame_equal(s,self.search)
    def test_conservative_classification(self):
        self.assertEqual(mod._classify(0.01,0.5,6)[0],'NULL_SIGNAL_PRESENT_BUT_INSUFFICIENT')
        self.assertEqual(mod._classify(0.01,0.01,6)[0],'NULL_SIGNAL_SURVIVES_MULTIPLE_TESTING')
        self.assertEqual(mod._classify(0.5,0.5,6)[0],'NULL_NOT_SIGNIFICANT')
    def test_missing_search_candidate_is_zero(self):
        s=self.search.iloc[:0].copy()
        out=mod.validate(self.dataset,s,permutations=1000,seed=7)
        self.assertEqual(len(out),6); self.assertTrue((out.observations==0).all())
    def test_no_sqlite_access(self):
        out=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        self.assertEqual(len(out),6)

    def test_null_distribution_generation(self):
        labels=np.array([0,0,1,2,2,2])
        rng=np.random.default_rng(1)
        null=mod._null_stats(labels,3,1000,rng)
        self.assertEqual(len(null),1000)
        self.assertTrue(np.isfinite(null).all())

    def test_multiple_testing_adjustment_is_conservative(self):
        out=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        x=out.loc[out.observations>0]
        self.assertTrue((x.adjusted_p_value >= x.raw_p_value).all())
        self.assertTrue((x.adjusted_p_value <= 1).all())

    def test_no_zero_empirical_p_value(self):
        out=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        self.assertTrue((out.loc[out.observations>0,'raw_p_value'] > 0).all())

    def test_output_columns(self):
        out=mod.validate(self.dataset,self.search,permutations=1000,seed=7)
        for c in ['candidate','raw_p_value','adjusted_p_value','null_result','research_action']:
            self.assertIn(c,out.columns)

if __name__=='__main__': unittest.main()
