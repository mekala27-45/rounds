import unittest
import numpy as np
import pandas as pd
from evaluate import binary_metrics, decision_curve, conformal_quantile, temporal_splits, fdr_adjust, unavailable

class EvaluationTests(unittest.TestCase):
    def test_perfect_probabilities(self):
        m=binary_metrics([0,0,1,1],[0,0,1,1]);self.assertEqual(m['auroc'],1);self.assertEqual(m['brier'],0);self.assertEqual(m['ece'],0)
    def test_reversed_probabilities_fail_discrimination(self):
        self.assertEqual(binary_metrics([0,0,1,1],[1,1,0,0])['auroc'],0)
    def test_no_outcomes_not_scored(self):
        self.assertIsNone(binary_metrics([],[])['auroc'])
        with self.assertRaises(ValueError):decision_curve([],[])
    def test_decision_net_benefit_is_arithmetic(self):
        d=decision_curve([0,0,1,1],[.1,.1,.9,.9]);r=next(x for x in d if x['threshold']==.5);self.assertEqual(r['model'],.5);self.assertEqual(r['all'],0)
    def test_conformal_finite_sample_quantile(self):
        self.assertEqual(conformal_quantile(np.arange(1,20),.9),18)
        with self.assertRaises(ValueError):conformal_quantile([])
    def test_temporal_label_embargo_and_censoring(self):
        d=pd.DataFrame({'prediction_time':['2020-02-01','2020-07-01','2022-03-01','2023-07-01','2024-08-01','2024-09-01'],'discharge_time':['2020-02-02','2020-07-02','2022-03-02','2023-07-02','2024-08-02','2024-09-02'],'age':[60]*6,'target_readmit30':[1,0,1,0,1,np.nan]})
        tr,va,te,_=temporal_splits(d,'target_readmit30');self.assertEqual((len(tr),len(va),len(te)),(1,1,1));self.assertEqual(te.index.tolist(),[4])
    def test_bh_adjustment(self):
        np.testing.assert_allclose(fdr_adjust([.01,.04,.03]),[.03,.04,.04])
    def test_unavailable_refuses_clinical_claim(self):
        c=unavailable('x','x','x','x','Missing outcome');self.assertEqual(c['metrics'],{});self.assertFalse(c['gates'][0]['passed']);self.assertFalse(c['contract']['live_scoring'])

if __name__=='__main__':unittest.main()
