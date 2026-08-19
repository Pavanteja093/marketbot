import unittest
import numpy as np
import pandas as pd
from research.baseline_failure_decomposition import FACTORS, Config, _cap_weights, add_baseline_score, attach_factor_diagnostics, build_failure_report, condition_summary, cross_sectional_ic, evaluate_day, fit_baseline_weights, run_walk_forward

class BaselineFailureDecompositionTests(unittest.TestCase):
    def make_day(self,n=20,date="2026-01-01"):
        return pd.DataFrame({"trade_date":pd.Timestamp(date),"entity":[f"S{i}" for i in range(n)],"relative_strength":np.linspace(0,1,n),"trend_score":np.linspace(1,0,n),"momentum_score":np.linspace(.2,.8,n),"volatility_score":np.linspace(.1,.9,n),"liquidity_score":np.linspace(.3,.7,n),"return_5d":np.linspace(-1,1,n)})
    def test_cross_sectional_ic_finite(self): self.assertTrue(np.isfinite(cross_sectional_ic(self.make_day(),"relative_strength")))
    def test_cap_weights_enforces_hard_cap(self):
        r=_cap_weights(pd.Series({f:v for f,v in zip(FACTORS,[10,2,1,1,1])}),.45); self.assertAlmostEqual(r.sum(),1); self.assertLessEqual(r.max(),.45+1e-9)
    def test_cap_weights_zero_signal_is_uniform(self): self.assertTrue(np.allclose(_cap_weights(pd.Series(0.,index=FACTORS),.45).values,.2))
    def test_fit_weights_complete(self):
        d=pd.concat([self.make_day(),self.make_day(date="2026-01-02")],ignore_index=True); r=fit_baseline_weights(d,Config()); self.assertEqual(set(r.index),set(FACTORS)); self.assertAlmostEqual(r.sum(),1); self.assertLessEqual(r.max(),.45+1e-9)
    def test_add_baseline_score_finite(self):
        r=add_baseline_score(self.make_day(),pd.Series(.2,index=FACTORS)); self.assertTrue(np.isfinite(r.baseline_score).all())
    def test_evaluate_day_rejects_small_cross_section(self):
        d=self.make_day(8); d["baseline_score"]=np.arange(8); self.assertIsNone(evaluate_day(d,10))
    def test_evaluate_day_returns_spread(self):
        d=self.make_day(); d["baseline_score"]=np.arange(len(d),dtype=float); r=evaluate_day(d,10); self.assertAlmostEqual(r["spread"],float(d.tail(4).return_5d.mean()-d.head(4).return_5d.mean()))
    def test_factor_diagnostics_contains_agreement(self):
        d=self.make_day(); ctx=pd.DataFrame({"trade_date":[pd.Timestamp("2026-01-01")],"direction_state":["UP"],"volatility_state":["NORMAL"],"breadth_state":["MIXED_BREADTH"],"dispersion_state":["NORMAL_DISPERSION"]}); r=attach_factor_diagnostics(d,ctx); self.assertIn("factor_agreement",r); self.assertIn("relative_strength_ic",r)
    def test_condition_summary(self):
        d=pd.DataFrame({"spread":[1.,-.5,.5],"direction_state":["UP","UP","DOWN"]}); r=condition_summary(d,"direction_state"); self.assertAlmostEqual(float(r[r.state=="UP"].iloc[0].mean_spread),.25)
    def test_build_failure_report_empty(self):
        r=build_failure_report(pd.DataFrame()); self.assertTrue(r["overall"].empty); self.assertIn("direction_state",r)
    def test_run_walk_forward_returns_frame(self):
        d=pd.concat([self.make_day(date="2025-01-01"),self.make_day(date="2025-01-02")],ignore_index=True); ctx=pd.DataFrame({"trade_date":pd.to_datetime(["2025-01-01","2025-01-02"]),"direction_state":["UP","DOWN"],"volatility_state":["LOW","HIGH"],"breadth_state":["BULLISH_BREADTH","BEARISH_BREADTH"],"dispersion_state":["NORMAL_DISPERSION","HIGH_DISPERSION"]}); r,_=run_walk_forward(d,ctx,Config(train_days=1,test_days=1,min_daily_obs=10)); self.assertIsInstance(r,pd.DataFrame)
    def test_helpers_do_not_mutate_input(self):
        d=self.make_day(); before=d.copy(deep=True); add_baseline_score(d,pd.Series(.2,index=FACTORS)); pd.testing.assert_frame_equal(d,before)

if __name__=="__main__": unittest.main()
