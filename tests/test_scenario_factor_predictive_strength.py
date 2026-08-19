import unittest
from unittest.mock import patch
import pandas as pd
from research.scenario_factor_predictive_strength import OUTPUT_COLUMNS, assess_predictive_strength

def row(scenario="CHOPPY", factor="intelligence_score", state="HIGH", obs=100, pct=60.0, mean=1.0):
    return {"primary_scenario":scenario,"factor":factor,"factor_state":state,"observations":obs,
            "scenario_dates":20,"symbols":30,"positive_5d_pct":pct,"mean_return_5d":mean,
            "median_return_5d":0.8,"worst_return_5d":-5.0,"best_return_5d":8.0}

class Tests(unittest.TestCase):
    def setUp(self):
        self.b=pd.DataFrame([{"primary_scenario":"CHOPPY","observations":1000,"mean_return_5d":0.2,"positive_5d_pct":50.0},
                             {"primary_scenario":"TREND_UP","observations":1000,"mean_return_5d":0.5,"positive_5d_pct":55.0}])
        self.g={"observations":5000,"mean_return_5d":0.3,"positive_5d_pct":52.0}
    def test_columns(self): self.assertEqual(list(assess_predictive_strength(pd.DataFrame([row()]),self.b,self.g).columns),OUTPUT_COLUMNS)
    def test_not_mutated(self):
        d=pd.DataFrame([row()]); before=d.copy(deep=True); assess_predictive_strength(d,self.b,self.g); pd.testing.assert_frame_equal(d,before)
    def test_lifts(self):
        r=assess_predictive_strength(pd.DataFrame([row()]),self.b,self.g).iloc[0]
        self.assertAlmostEqual(r.positive_rate_lift_vs_scenario,10); self.assertAlmostEqual(r.mean_return_lift_vs_scenario,.8); self.assertEqual(r.predictive_strength_status,"STRONG_POSITIVE")
    def test_negative(self): self.assertEqual(assess_predictive_strength(pd.DataFrame([row(pct=40,mean=-.5)]),self.b,self.g).iloc[0].predictive_strength_status,"NEGATIVE")
    def test_insufficient(self): self.assertEqual(assess_predictive_strength(pd.DataFrame([row(obs=29)]),self.b,self.g).iloc[0].predictive_strength_status,"INSUFFICIENT")
    def test_preserves_relationships(self):
        d=pd.DataFrame([row(state="HIGH"),row(state="MEDIUM",factor="trend_score",scenario="TREND_UP")]); o=assess_predictive_strength(d,self.b,self.g); self.assertEqual(len(o),2)
    def test_deterministic(self):
        d=pd.DataFrame([row(),row(state="LOW",obs=60,pct=55,mean=.4)]); pd.testing.assert_frame_equal(assess_predictive_strength(d,self.b,self.g),assess_predictive_strength(d,self.b,self.g))
    def test_missing(self):
        with self.assertRaises(ValueError): assess_predictive_strength(pd.DataFrame([row()]).drop(columns=["symbols"]),self.b,self.g)
    def test_core_has_no_sqlite_access(self):
        with patch("research.scenario_factor_predictive_strength.sqlite3.connect",side_effect=AssertionError):
            self.assertEqual(len(assess_predictive_strength(pd.DataFrame([row()]),self.b,self.g)),1)

if __name__ == "__main__": unittest.main()
