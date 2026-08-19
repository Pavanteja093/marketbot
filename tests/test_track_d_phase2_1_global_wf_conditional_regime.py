from __future__ import annotations
import unittest, numpy as np, pandas as pd
from research import track_d_phase2_1_global_wf_conditional_regime as m

def make_data(days=140,stocks=25):
    dates=pd.bdate_range('2025-01-01',periods=days); rng=np.random.default_rng(42); rows=[]
    for di,d in enumerate(dates):
        for s in range(stocks):
            f=float(s+rng.normal(0,.05)); rows.append({'trade_date':d,'index_name':f'S{s:02d}','scenario':'TREND_UP' if di%3 else 'CHOPPY','intelligence_score':f,'volatility_score':float(s+rng.normal(0,.05)),'trend_score':float(s+rng.normal(0,.05)),'return_1d':f*.01+rng.normal(0,.1),'return_5d':f*.02+rng.normal(0,.1),'return_10d':f*.03+rng.normal(0,.1),'return_20d':f*.04+rng.normal(0,.1)})
    return pd.DataFrame(rows)

class TrackDPhase21Tests(unittest.TestCase):
    def test_chronological_folds(self):
        folds=m.make_global_oos_folds(pd.bdate_range('2025-01-01',periods=180)); self.assertGreaterEqual(len(folds),4)
        for _,tr_end,te_start,te_end in folds:self.assertLess(tr_end,te_start); self.assertLessEqual(te_start,te_end)
    def test_no_leakage(self):
        for _,tr_end,te_start,_ in m.make_global_oos_folds(pd.bdate_range('2025-01-01',periods=180)):self.assertLess(tr_end,te_start)
    def test_regime_filtering(self):
        d=make_data(); r=m.validate(d,regimes=('TREND_UP',),factors=('intelligence_score',),horizons=(1,)); self.assertEqual(len(r),1); self.assertEqual(r.iloc[0].scenario,'TREND_UP')
    def test_spearman(self):self.assertAlmostEqual(m.spearman(pd.Series([1,2,3,4]),pd.Series([2,4,6,8])),1.0)
    def test_quintile_spread(self):
        tr=pd.DataFrame({'x':np.arange(100),'r':np.arange(100)}); te=pd.DataFrame({'x':np.arange(100),'r':np.arange(100)*2.0}); self.assertGreater(m.quintile_spread(tr,te,'x','r'),0)
    def test_insufficient_coverage(self):
        r=m.validate(make_data(10),regimes=('TREND_UP',),factors=('intelligence_score',),horizons=(1,),min_train_days=8,test_days=2); self.assertEqual(r.iloc[0].evidence_classification,'INSUFFICIENT_TEMPORAL_COVERAGE')
    def test_deterministic(self):
        d=make_data(); a=m.validate(d,regimes=('TREND_UP',),factors=('intelligence_score',),horizons=(1,)); b=m.validate(d,regimes=('TREND_UP',),factors=('intelligence_score',),horizons=(1,)); pd.testing.assert_frame_equal(a,b)
    def test_immutable(self):
        d=make_data(); before=d.copy(deep=True); m.validate(d,regimes=('TREND_UP',),factors=('intelligence_score',),horizons=(1,)); pd.testing.assert_frame_equal(d,before)
    def test_bh(self):
        a=m.benjamini_hochberg([.001,.01,.2,np.nan]); self.assertTrue(np.isnan(a[3])); self.assertTrue(all(0<=x<=1 for x in a[:3])); self.assertGreaterEqual(a[0],.001)
    def test_required_columns(self):
        with self.assertRaises(ValueError):m.validate(make_data().drop(columns=['trend_score']),regimes=('TREND_UP',),factors=('intelligence_score','trend_score'),horizons=(1,))
    def test_sign_test(self):self.assertLessEqual(m.sign_test_pvalue([1,1,1,1]),.125)

if __name__=='__main__':unittest.main()
