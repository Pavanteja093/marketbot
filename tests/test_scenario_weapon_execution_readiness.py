import unittest
from pathlib import Path
import pandas as pd

import scenario_weapon_execution_readiness as mod


class ExecutionReadinessTests(unittest.TestCase):
    def test_track_b_ready_when_exact_overlap_reaches_20(self):
        dates = pd.date_range('2026-01-01', periods=20, freq='D')
        queue = pd.DataFrame([{
            'scenario_id':'S1','primary_scenario':'TREND_UP','fingerprint':'FP1',
            'candidate':'TRACK_B_BASELINE_FAILURE','scenario_observations':20,
            'oos_windows':0,'target_oos_windows':10,'eligibility_status':'RESEARCHABLE_NO_EVIDENCE',
            'research_priority':'HIGH','queue_priority':'P1','queue_action':'START_OOS_RESEARCH'
        }])
        original_history = mod._load_scenario_history
        original_dates = mod._candidate_dates
        mod._load_scenario_history = lambda db: pd.DataFrame({'trade_date':dates,'scenario_id':['S1']*20,'fingerprint':['FP1']*20})
        mod._candidate_dates = lambda db: {'TRACK_B_BASELINE_FAILURE':set(dates), 'TRACK_B_CONDITIONAL_SCORE':set(), 'TRACK_B_FACTOR_AGREEMENT':set()}
        try:
            out=mod.audit(queue, Path('dummy.db'))
            self.assertEqual(out.iloc[0].execution_readiness,'READY_FOR_OOS')
            self.assertEqual(out.iloc[0].overlap_oos_dates,20)
        finally:
            mod._load_scenario_history=original_history
            mod._candidate_dates=original_dates

    def test_track_b_blocks_with_only_ten_overlap(self):
        dates = pd.date_range('2026-01-01', periods=25, freq='D')
        queue = pd.DataFrame([{
            'scenario_id':'S1','primary_scenario':'TREND_UP','fingerprint':'FP1',
            'candidate':'TRACK_B_BASELINE_FAILURE','scenario_observations':25,
            'oos_windows':5,'target_oos_windows':10,'eligibility_status':'EVIDENCE_PRESENT_EARLY',
            'research_priority':'HIGH','queue_priority':'P0','queue_action':'CONTINUE_OOS'
        }])
        original_history=mod._load_scenario_history; original_dates=mod._candidate_dates
        mod._load_scenario_history=lambda db: pd.DataFrame({'trade_date':dates,'scenario_id':['S1']*25,'fingerprint':['FP1']*25})
        mod._candidate_dates=lambda db: {'TRACK_B_BASELINE_FAILURE':set(dates[:10]),'TRACK_B_CONDITIONAL_SCORE':set(),'TRACK_B_FACTOR_AGREEMENT':set()}
        try:
            out=mod.audit(queue,Path('dummy.db'))
            self.assertEqual(out.iloc[0].execution_readiness,'BLOCKED_NO_HOLDOUT')
            self.assertEqual(out.iloc[0].overlap_oos_dates,10)
        finally:
            mod._load_scenario_history=original_history; mod._candidate_dates=original_dates

    def test_track_c_requires_140_dates(self):
        dates=pd.date_range('2026-01-01',periods=25,freq='D')
        queue=pd.DataFrame([{
            'scenario_id':'S1','primary_scenario':'TREND_UP','fingerprint':'FP1',
            'candidate':'TRACK_C_FACTOR_INTERACTION','scenario_observations':25,
            'oos_windows':0,'target_oos_windows':10,'eligibility_status':'RESEARCHABLE_NO_EVIDENCE',
            'research_priority':'HIGH','queue_priority':'P1','queue_action':'START_OOS_RESEARCH'
        }])
        original_history=mod._load_scenario_history; original_dates=mod._candidate_dates
        mod._load_scenario_history=lambda db: pd.DataFrame({'trade_date':dates,'scenario_id':['S1']*25,'fingerprint':['FP1']*25})
        mod._candidate_dates=lambda db: {'TRACK_B_BASELINE_FAILURE':set(),'TRACK_B_CONDITIONAL_SCORE':set(),'TRACK_B_FACTOR_AGREEMENT':set()}
        try:
            out=mod.audit(queue,Path('dummy.db'))
            self.assertEqual(out.iloc[0].execution_readiness,'BLOCKED_NO_HOLDOUT')
            self.assertEqual(out.iloc[0].methodology_min_observations,140)
        finally:
            mod._load_scenario_history=original_history; mod._candidate_dates=original_dates


if __name__=='__main__':
    unittest.main(verbosity=2)
