"""Independent artifact and deliberate-failure tests; no clinical validation claim."""
from pathlib import Path
import json,unittest,copy,hashlib,hmac,re,os
import pandas as pd
import duckdb
from privacy_gate import validate_private_payload
BASE=Path(__file__).resolve().parents[2]; OUT=BASE/'data'/'sample'
class AnalyticsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.c=duckdb.connect()
  for path in OUT.glob('*.parquet'):
   cls.c.execute(f"create view {path.stem} as select * from read_parquet('{path.as_posix()}')")
  cls.f=pd.read_parquet(OUT/'features.parquet'); cls.annual=pd.read_parquet(OUT/'hosp12m.parquet')
  cls.manifest=json.loads((BASE/'results/base-manifest.json').read_text()); cls.payload=json.loads((BASE/'data/private/patients.json').read_text())
 def test_population_and_private_limit(self):
  self.assertEqual(self.c.sql('select count(*) from person').fetchone()[0],2000)
  self.assertEqual(len(self.payload['patients']),60)
  self.assertTrue(validate_private_payload(self.payload))
 def test_planted_identifier_rejected(self):
  planted=copy.deepcopy(self.payload); planted['patients'][0]['conditions'].append('SSN 123-45-6789')
  with self.assertRaises(ValueError): validate_private_payload(planted)
 def test_planted_direct_field_rejected(self):
  planted=copy.deepcopy(self.payload); planted['patients'][0]['name']='PLANTED IDENTIFIER'
  with self.assertRaises(ValueError): validate_private_payload(planted)
 def test_empty_payload_rejected(self):
  with self.assertRaises(ValueError): validate_private_payload({'patients':[]})
 def test_date_shift_preserves_intervals_and_observation_end(self):
  if not os.environ.get('ROUNDS_RAW_CSV'): self.skipTest('Raw Synthea path required for interval reconstruction')
  raw=pd.read_csv(Path(os.environ['ROUNDS_RAW_CSV'])/'encounters.csv',usecols=['Id','PATIENT','START','STOP'],dtype=str).sample(200,random_state=20260923)
  salt=(BASE/'data/.deid-salt').read_bytes()
  for r in raw.itertuples():
   eid=hmac.new(salt,('visit:'+r.Id).encode(),hashlib.sha256).hexdigest()[:20]
   shifted=self.c.execute('select v.visit_start_datetime,v.visit_end_datetime,p.observation_end from visit_occurrence v join person p using(person_id) where visit_occurrence_id=?',[eid]).fetchone()
   start=pd.Timestamp(r.START).tz_localize(None); end=pd.Timestamp(r.STOP).tz_localize(None)
   self.assertEqual(shifted[1]-shifted[0],end-start)
   delta=pd.Timestamp(shifted[0])-start
   self.assertEqual(pd.Timestamp(shifted[2])-pd.Timestamp('2026-09-22'),delta)
   self.assertLessEqual(abs(delta.days),180)
 def test_censored_readmission_is_null(self):
  f=self.f
  self.assertTrue(f.loc[~f.readmit_eligible,'target_readmit30'].isna().all())
  self.assertTrue((f.loc[f.readmit_eligible,'discharge_time']+pd.Timedelta(days=30)<=f.loc[f.readmit_eligible,'observation_end']).all())
  self.assertTrue(f.loc[f.readmit_eligible,'target_readmit30'].notna().all())
 def test_censoring_boundary_fixture(self):
  end=pd.Timestamp('2026-09-22'); eligible=lambda d:d+pd.Timedelta(days=30)<=end
  self.assertTrue(eligible(end-pd.Timedelta(days=30)))
  self.assertFalse(eligible(end-pd.Timedelta(days=29)))
 def test_hospitalization_censoring(self):
  f=self.annual; self.assertTrue(f.loc[~f.hosp12m_eligible,'target_hosp12m'].isna().all())
  self.assertTrue(f.loc[~f.hosp12m_eligible,'target_next365_cost'].isna().all())
 def test_point_in_time_features_200_rows(self):
  for r in self.f.sample(200,random_state=42).itertuples():
   values=self.c.execute("""select count(*) filter(where visit_class='inpatient'),count(*) filter(where visit_class='emergency'),count(*) from visit_occurrence where person_id=? and visit_start_datetime<? and visit_start_datetime>=?-interval 365 day""",[r.person_id,r.prediction_time,r.prediction_time]).fetchone()
   self.assertEqual(values,(r.prior_admissions_365,r.prior_ed_365,r.prior_visits_365))
   conditions=self.c.execute("select count(distinct source_code) from condition_occurrence where person_id=? and event_datetime<date_trunc('day',?::timestamp)",[r.person_id,r.prediction_time]).fetchone()[0]
   meds=self.c.execute('select count(distinct source_code) from drug_exposure where person_id=? and event_datetime<? and (end_datetime is null or end_datetime>=?)',[r.person_id,r.prediction_time,r.prediction_time]).fetchone()[0]
   self.assertEqual(conditions,r.condition_count); self.assertEqual(meds,r.medication_count)
 def test_measure_numerators_within_denominators(self):
  self.assertEqual(len(self.manifest['measures']),10)
  for m in self.manifest['measures']:
   self.assertLessEqual(m['numerator'],m['denominator']); self.assertGreaterEqual(m['numerator'],0)
   if m['denominator']: self.assertEqual(m['value'],round(100*m['numerator']/m['denominator'],2))
 def test_cohorts_match_published_sql(self):
  for h in self.manifest['cohorts']:
   self.assertEqual(self.c.sql('select count(*) from ('+h['sql']+')').fetchone()[0],h['count'])
 def test_public_assets_have_no_patient_ids(self):
  ids=set(self.c.sql('select person_id from person').df().person_id)
  for filename in ['manifest.json','aggregate-tables.json']:
   text=(BASE/'results'/filename).read_text(); self.assertFalse(any(x in text for x in ids)); self.assertNotIn('private-patients',text)
 def test_small_cohort_cells_suppressed(self):
  cube=json.loads((BASE/'results/aggregate-tables.json').read_text())['cohort_counts']
  self.assertTrue(len(cube)>0)
  for cell in cube:
   if cell['suppressed']: self.assertIsNone(cell['count'])
   else: self.assertGreaterEqual(cell['count'],5)
 def test_identifier_columns_absent(self):
  prohibited={'raw_id','ssn','drivers','passport','first','middle','last','address','zip','lat','lon','birth_datetime'}
  for path in OUT.glob('*.parquet'):
   cols={x[0].lower() for x in self.c.sql(f"describe select * from read_parquet('{path.as_posix()}')").fetchall()}
   self.assertFalse(cols&prohibited)
 def test_no_em_dash_and_statement(self):
  statement=self.manifest['statement']
  for file in ['manifest.json','aggregate-tables.json','private-patients.json']:
   text=({'manifest.json':BASE/'results/manifest.json','aggregate-tables.json':BASE/'results/aggregate-tables.json','private-patients.json':BASE/'data/private/patients.json'}[file]).read_text(); self.assertIn(statement,text); self.assertNotIn('\u2014',text)
if __name__=='__main__': unittest.main(verbosity=2)
