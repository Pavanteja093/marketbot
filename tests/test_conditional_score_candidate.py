import unittest
import numpy as np
import pandas as pd
from research.conditional_score_candidate import FACTORS,MAX_WEIGHT,evaluate_day,fit_weights,profile_for_day,profile_weights,score_day
class ConditionalScoreTests(unittest.TestCase):
    def make_day(self,n=25):
        d={f:np.arange(n,dtype=float) for f in FACTORS}; d["return_5d"]=np.linspace(-1,2,n); return pd.DataFrame(d)
    def test_fit_weights_complete_and_capped(self):
        days=[]
        for i in range(40):
            x=self.make_day(); x["trade_date"]=pd.Timestamp("2025-01-01")+pd.Timedelta(days=i); days.append(x)
        w=fit_weights(pd.concat(days,ignore_index=True)); self.assertEqual(set(w),set(FACTORS)); self.assertAlmostEqual(sum(w.values()),1,9); self.assertLessEqual(max(w.values()),MAX_WEIGHT+1e-9)
    def test_profile_valid(self): self.assertIn(profile_for_day(self.make_day()),{"TREND","DEFENSIVE","VOLATILITY"})
    def test_profile_weights_normalize(self):
        for p in PROFILES if False else ("TREND","DEFENSIVE","VOLATILITY"):
            w=profile_weights({f:.2 for f in FACTORS},p); self.assertAlmostEqual(sum(w.values()),1,9)
    def test_score_finite(self): self.assertTrue(np.isfinite(score_day(self.make_day(),{f:.2 for f in FACTORS})).all())
    def test_evaluate(self):
        d=self.make_day(); r=evaluate_day(d,pd.Series(np.arange(len(d),dtype=float),index=d.index)); self.assertIsNotNone(r); self.assertGreater(r["spread"],0)
    def test_insufficient(self):
        d=self.make_day(9); self.assertIsNone(evaluate_day(d,pd.Series(np.arange(9,dtype=float),index=d.index)))
if __name__=="__main__": unittest.main()
