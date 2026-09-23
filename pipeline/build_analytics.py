"""Rebuild Rounds artifacts from official synthetic CSV. Run from any directory."""
from pathlib import Path
import hashlib, hmac, json, secrets, re, os
import datetime as dt
import pandas as pd
import duckdb
from privacy_gate import validate_private_payload

BASE=Path(os.environ.get('ROUNDS_DATA_ROOT',Path(__file__).resolve().parents[1]/'data'))
OUT=BASE/'processed'; OUT.mkdir(exist_ok=True)
WARE=OUT/'warehouse'; WARE.mkdir(exist_ok=True)
RAW=Path(os.environ.get('ROUNDS_RAW_CSV',BASE/'raw'/'csv'))
ASOF=pd.Timestamp('2026-09-22 00:00:00')
STATEMENT='This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.'
SALTFILE=BASE/'.deid-salt'
if not SALTFILE.exists(): SALTFILE.write_bytes(secrets.token_bytes(32))
SALT=SALTFILE.read_bytes()
def hid(value, namespace='person'):
 return hmac.new(SALT,(namespace+':'+str(value)).encode(),hashlib.sha256).hexdigest()[:20]
def offset(value):
 return int(hmac.new(SALT,('date:'+str(value)).encode(),hashlib.sha256).hexdigest()[:8],16)%361-180
def clean_json(value):
 if isinstance(value,dict): return {k:clean_json(v) for k,v in value.items()}
 if isinstance(value,list): return [clean_json(v) for v in value]
 if isinstance(value,(pd.Timestamp,dt.datetime,dt.date)): return value.isoformat()
 if pd.isna(value): return None
 if hasattr(value,'item'): return value.item()
 return value
def dump(name,data): (OUT/name).write_text(json.dumps(clean_json(data),indent=2,allow_nan=False),encoding='utf8')
c=duckdb.connect(); c.execute("SET memory_limit='1400MB'; SET threads=2;")
for table in ['patients','encounters','conditions','medications','observations','procedures','imaging_studies','immunizations','payers']:
 c.execute(f"CREATE VIEW raw_{table} AS SELECT * FROM read_csv('{(RAW/(table+'.csv')).as_posix()}',header=true,all_varchar=true)")
# Only allowlisted columns leave this transient identity map. No names, address,
# SSN, phone, source UUID, free text values, geographic coordinates, or income.
p=pd.read_csv(RAW/'patients.csv',dtype=str).fillna('')
maps=pd.DataFrame({'raw_id':p.Id,'person_id':p.Id.map(hid),'shift_days':p.Id.map(offset),'birth':pd.to_datetime(p.BIRTHDATE),'death':pd.to_datetime(p.DEATHDATE,errors='coerce'),'sex':p.GENDER,'race':p.RACE,'ethnicity':p.ETHNICITY})
c.register('identity_map',maps)
c.execute(f"""CREATE TABLE person AS SELECT person_id,sex,race,ethnicity,
least(90,date_diff('year',birth, timestamp '{ASOF}')) age,
CASE WHEN date_diff('year',birth,timestamp '{ASOF}')>=90 THEN '90+' WHEN date_diff('year',birth,timestamp '{ASOF}')<18 THEN '0-17' ELSE cast(floor(date_diff('year',birth,timestamp '{ASOF}')/10)*10 as integer)||'-'||cast(floor(date_diff('year',birth,timestamp '{ASOF}')/10)*10+9 as integer) END age_band,
birth+shift_days*interval 1 day birth_datetime,
death+shift_days*interval 1 day death_datetime,
timestamp '{ASOF}'+shift_days*interval 1 day observation_end
FROM identity_map""")
e=pd.read_csv(RAW/'encounters.csv',usecols=['Id'],dtype=str)
em=pd.DataFrame({'raw_visit':e.Id,'visit_occurrence_id':e.Id.map(lambda x:hid(x,'visit'))}); c.register('encounter_map',em)
c.execute("""CREATE TABLE visit_occurrence AS SELECT em.visit_occurrence_id,p.person_id,
try_cast(r.START AS TIMESTAMP)+p.shift_days*interval 1 day visit_start_datetime,
try_cast(r.STOP AS TIMESTAMP)+p.shift_days*interval 1 day visit_end_datetime,
r.ENCOUNTERCLASS visit_class,r.CODE visit_source_value,r.DESCRIPTION visit_source_description,
try_cast(r.TOTAL_CLAIM_COST AS DOUBLE) total_claim_cost, coalesce(py.NAME,'Unknown') payer
FROM raw_encounters r JOIN identity_map p ON p.raw_id=r.PATIENT JOIN encounter_map em ON em.raw_visit=r.Id
LEFT JOIN raw_payers py ON py.Id=r.PAYER""")
for table,source,datecol in [('condition_occurrence','conditions','START'),('drug_exposure','medications','START'),('procedure_occurrence','procedures','START'),('immunization','immunizations','DATE')]:
 stop="try_cast(r.STOP AS TIMESTAMP)+p.shift_days*interval 1 day" if source in ['conditions','medications','procedures'] else 'NULL::TIMESTAMP'
 c.execute(f"""CREATE TABLE {table} AS SELECT p.person_id,em.visit_occurrence_id,
try_cast(r.{datecol} AS TIMESTAMP)+p.shift_days*interval 1 day event_datetime,{stop} end_datetime,
r.CODE source_code,r.DESCRIPTION source_description FROM raw_{source} r JOIN identity_map p ON p.raw_id=r.PATIENT
LEFT JOIN encounter_map em ON em.raw_visit=r.ENCOUNTER""")
c.execute("""CREATE TABLE measurement AS SELECT p.person_id,em.visit_occurrence_id,
try_cast(r.DATE AS TIMESTAMP)+p.shift_days*interval 1 day event_datetime,
r.CODE source_code,r.DESCRIPTION source_description,try_cast(r.VALUE AS DOUBLE) value_as_number,r.UNITS unit_source_value,r.CATEGORY category
FROM raw_observations r JOIN identity_map p ON p.raw_id=r.PATIENT LEFT JOIN encounter_map em ON em.raw_visit=r.ENCOUNTER
WHERE r.TYPE='numeric' AND r.CODE NOT IN ('63586-2','63512-8')""")
c.execute("""CREATE TABLE imaging AS SELECT p.person_id,em.visit_occurrence_id,
try_cast(r.DATE AS TIMESTAMP)+p.shift_days*interval 1 day event_datetime,r.MODALITY_CODE modality,r.MODALITY_DESCRIPTION modality_description,r.BODYSITE_DESCRIPTION body_site,r.PROCEDURE_CODE source_code
FROM raw_imaging_studies r JOIN identity_map p ON p.raw_id=r.PATIENT LEFT JOIN encounter_map em ON em.raw_visit=r.ENCOUNTER""")
c.execute("""CREATE TABLE observation_period AS SELECT p.person_id,min(v.visit_start_datetime) observation_start_datetime,p.observation_end observation_end_datetime FROM person p JOIN visit_occurrence v USING(person_id) GROUP BY ALL""")
# Original calendar dates are used only for non-person aggregate arrival counts.
c.execute("""COPY (WITH d AS (SELECT unnest(generate_series(date '2020-01-01', date '2026-09-21', interval 1 day))::date date), a AS (SELECT try_cast(START AS DATE) date,count(*) count FROM raw_encounters WHERE ENCOUNTERCLASS='emergency' GROUP BY 1) SELECT d.date,coalesce(a.count,0) count FROM d LEFT JOIN a USING(date) ORDER BY date) TO '"""+(OUT/'ed_daily.csv').as_posix()+"' (HEADER,DELIMITER ',')")
tables=['person','visit_occurrence','condition_occurrence','drug_exposure','procedure_occurrence','measurement','imaging','immunization','observation_period']
for t in tables:
 selection='SELECT * EXCLUDE(birth_datetime) FROM person' if t=='person' else f'SELECT * FROM {t}'
 c.execute(f"COPY ({selection}) TO '{(WARE/(t+'.parquet')).as_posix()}' (FORMAT PARQUET,COMPRESSION ZSTD)")
print('De-identification and warehouse complete.',flush=True)
# Admission-time features. Labels may use the future; feature subqueries cannot.
c.execute("""CREATE TABLE index_admissions AS SELECT v.visit_occurrence_id index_id,v.person_id,v.visit_start_datetime prediction_time,v.visit_end_datetime discharge_time,p.observation_end,p.birth_datetime,p.death_datetime,p.sex,p.race,p.ethnicity,p.age_band,v.payer,v.total_claim_cost,
greatest(0,least(90,floor(date_diff('day',p.birth_datetime,v.visit_start_datetime)/365.2425))) age,
epoch(v.visit_end_datetime-v.visit_start_datetime)/86400 target_los_days
FROM visit_occurrence v JOIN person p USING(person_id) WHERE visit_class='inpatient' AND visit_end_datetime>=visit_start_datetime""")
feature_sql="""SELECT i.*,
(SELECT count(*) FROM visit_occurrence v WHERE v.person_id=i.person_id AND v.visit_start_datetime<i.prediction_time AND v.visit_start_datetime>=i.prediction_time-interval 365 day AND v.visit_class='inpatient') prior_admissions_365,
(SELECT count(*) FROM visit_occurrence v WHERE v.person_id=i.person_id AND v.visit_start_datetime<i.prediction_time AND v.visit_start_datetime>=i.prediction_time-interval 365 day AND v.visit_class='emergency') prior_ed_365,
(SELECT count(*) FROM visit_occurrence v WHERE v.person_id=i.person_id AND v.visit_start_datetime<i.prediction_time AND v.visit_start_datetime>=i.prediction_time-interval 365 day) prior_visits_365,
(SELECT count(distinct source_code) FROM condition_occurrence x WHERE x.person_id=i.person_id AND x.event_datetime<date_trunc('day',i.prediction_time)) condition_count,
(SELECT count(distinct source_code) FROM drug_exposure x WHERE x.person_id=i.person_id AND x.event_datetime<i.prediction_time AND (x.end_datetime IS NULL OR x.end_datetime>=i.prediction_time)) medication_count
FROM {indices} i"""
c.execute('CREATE TABLE feature_base AS '+feature_sql.format(indices='index_admissions'))
c.execute("""CREATE TABLE features AS SELECT * EXCLUDE(birth_datetime,death_datetime),
discharge_time+interval 30 day<=observation_end AND (death_datetime IS NULL OR death_datetime>discharge_time+interval 30 day) readmit_eligible,
CASE WHEN discharge_time+interval 30 day<=observation_end AND (death_datetime IS NULL OR death_datetime>discharge_time+interval 30 day) THEN (SELECT count(*)>0 FROM visit_occurrence v WHERE v.person_id=f.person_id AND v.visit_class='inpatient' AND v.visit_start_datetime>f.discharge_time AND v.visit_start_datetime<=f.discharge_time+interval 30 day)::integer END target_readmit30,
discharge_time+interval 30 day label_available_at FROM feature_base f""")
c.execute(f"COPY features TO '{(OUT/'features.parquet').as_posix()}' (FORMAT PARQUET)")
print('Admission features ready.',flush=True)
# Annual primary-care-adjacent population index, explicitly not visit-triggered.
c.execute("""CREATE TABLE annual_indices AS SELECT p.person_id||'-'||y.index_year index_id,p.person_id,
make_date(y.index_year,1,1)+(p.observation_end-timestamp '2026-09-22') prediction_time,p.observation_end,p.birth_datetime,p.death_datetime,p.sex,p.race,p.ethnicity,p.age_band,'Unknown' payer,
least(90,floor(date_diff('day',p.birth_datetime,make_date(y.index_year,1,1)+(p.observation_end-timestamp '2026-09-22'))/365.2425)) age
FROM person p CROSS JOIN (SELECT unnest(range(2016,2027)) index_year) y
WHERE age>=18 AND (p.death_datetime IS NULL OR p.death_datetime>prediction_time)""")
c.execute('CREATE TABLE annual_base AS '+feature_sql.format(indices='annual_indices'))
c.execute("""CREATE TABLE hosp12m AS SELECT * EXCLUDE(birth_datetime,death_datetime),
prediction_time+interval 365 day<=observation_end AND (death_datetime IS NULL OR death_datetime>prediction_time+interval 365 day) hosp12m_eligible,
CASE WHEN prediction_time+interval 365 day<=observation_end AND (death_datetime IS NULL OR death_datetime>prediction_time+interval 365 day) THEN (SELECT count(*)>0 FROM visit_occurrence v WHERE v.person_id=a.person_id AND v.visit_class='inpatient' AND v.visit_start_datetime>a.prediction_time AND v.visit_start_datetime<=a.prediction_time+interval 365 day)::integer END target_hosp12m,
CASE WHEN prediction_time+interval 365 day<=observation_end AND (death_datetime IS NULL OR death_datetime>prediction_time+interval 365 day) THEN (SELECT coalesce(sum(total_claim_cost),0) FROM visit_occurrence v WHERE v.person_id=a.person_id AND v.visit_start_datetime>a.prediction_time AND v.visit_start_datetime<=a.prediction_time+interval 365 day) END target_next365_cost,
prediction_time+interval 365 day label_available_at FROM annual_base a""")
c.execute(f"COPY hosp12m TO '{(OUT/'hosp12m.parquet').as_posix()}' (FORMAT PARQUET)")
def scalar(sql): return c.execute(sql).fetchone()[0]
def rows(sql): return c.execute(sql).df().to_dict('records')
def metric(label,value,unit='',note=''): return dict(label=label,value=value,unit=unit,note=note)
def q(sql): return scalar(sql)
featuremeta={'statement':STATEMENT,'date_shift_max_days':180,'date_shift_min_days':-180,'calendar':'Patient date shift is constant and includes observation end; shifted-calendar temporal splits must use a 360-day boundary buffer or be labeled approximate.','readmit30':'All-cause inpatient return within 30 days after discharge; prediction features are admission-time only. Planned admissions and transfers are not adjudicated. Censored if complete 30-day follow-up is unavailable or death occurs in the window.','hosp12m':'Annual January 1 adult index, not a primary-care-visit model; 365-day follow-up and death censoring.','target_next365_cost':'Sum of encounter TOTAL_CLAIM_COST over 365 days; synthetic charge/utilization proxy, not paid costs or clinical need.','feature_columns':['age','prior_admissions_365','prior_ed_365','prior_visits_365','condition_count','medication_count'],'admission_rows':q('select count(*) from features'),'annual_rows':q('select count(*) from hosp12m')}
dump('feature-metadata.json',featuremeta)
print('Annual features ready.',flush=True)
cohort_specs=[('diabetes','Type 2 diabetes','Diabetes mellitus type 2'),('hypertension','Hypertension','Essential hypertension'),('ckd','Chronic kidney disease','Chronic kidney disease'),('copd','COPD','Chronic obstructive|Chronic bronchitis|Pulmonary emphysema'),('asthma','Asthma','Asthma'),('heart-failure','Heart failure','Heart failure'),('ischemic-heart','Ischemic heart disease','Ischemic heart disease'),('stroke','Stroke','Cerebrovascular accident|Stroke'),('obesity','Obesity','obesity'),('depression','Depression','depress')]
cohorts=[]
for cid,name,pattern in cohort_specs:
 codes=rows("SELECT DISTINCT source_code code,source_description description FROM condition_occurrence WHERE regexp_matches(source_description,?, 'i')".replace('?',"'"+pattern+"'"))
 codest="("+','.join("'"+x['code']+"'" for x in codes)+")" if codes else "('NONE')"
 sql=f"SELECT DISTINCT person_id FROM condition_occurrence WHERE source_code IN {codest}"
 c.execute(f'CREATE TABLE cohort_{cid.replace("-","_")} AS '+sql)
 n=q('select count(*) from ('+sql+')')
 cohorts.append(dict(id=cid,name=name,count=n,definition='Lifetime recorded diagnosis from the observed Synthea SNOMED descriptions. No validated phenotype or active-disease claim.',sql=sql,codes=codes,attrition=[{'label':'Generated patients','count':len(p)},{'label':'Recorded matching diagnosis','count':n}]))
alive=q('select count(*) from person where death_datetime is null')
admissions=q('select count(*) from features'); eligible=q('select count(*) from features where readmit_eligible'); returns=q('select coalesce(sum(target_readmit30),0) from features')
readrate=round(100*returns/eligible,2) if eligible else None
los=q('select median(target_los_days) from features')
ed=q("select count(*) from visit_occurrence where visit_class='emergency'")
edhours=q("select median(epoch(visit_end_datetime-visit_start_datetime)/3600) from visit_occurrence where visit_class='emergency'")
measures=[]
def measure(mid,name,num,den,definition,dept,exclusions='Deceased patients and missing or out-of-window observations excluded where stated.'):
 measures.append(dict(id=mid,name=name,numerator=int(num),denominator=int(den),value=round(100*num/den,2) if den else None,unit='%',definition=definition,exclusions=exclusions,department=dept))
measure('return30','30-day all-cause inpatient return',returns,eligible,'Simplified all-cause return; no planned-admission algorithm or transfer adjudication. Complete follow-up only. Lifetime index admissions.','inpatient','Discharge plus 30 days exceeds shifted observation end; death during follow-up. Not CMS-certified.')
measure('annual-wellness','Wellness visit in past year',q("select count(distinct v.person_id) from visit_occurrence v join person p using(person_id) where p.death_datetime is null and v.visit_class='wellness' and v.visit_start_datetime between p.observation_end-interval 365 day and p.observation_end"),alive,'Living patients with a recorded wellness encounter in the preceding 365 days.','primary-care')
for mid,name,cid,code in [('diabetes-a1c','Diabetes: recent HbA1c recorded','diabetes','4548-4'),('hypertension-bp','Hypertension: recent systolic BP recorded','hypertension','8480-6'),('ckd-creatinine','CKD: recent creatinine recorded','ckd','38483-4'),('obesity-bmi','Obesity: recent BMI recorded','obesity','39156-5')]:
 table='cohort_'+cid.replace('-','_')
 den=q(f'select count(*) from {table} h join person p using(person_id) where death_datetime is null')
 num=q(f"select count(distinct h.person_id) from {table} h join person p using(person_id) join measurement m using(person_id) where p.death_datetime is null and m.source_code='{code}' and m.event_datetime between p.observation_end-interval 365 day and p.observation_end")
 measure(mid,name,num,den,f'Simplified documentation measure: living lifetime {cid} cohort with LOINC {code} recorded during the prior 365 days. No clinical adequacy threshold.','primary-care')
measure('adult-bp','Adults: recent blood pressure recorded',q("select count(distinct p.person_id) from person p join measurement m using(person_id) where p.death_datetime is null and p.age>=18 and m.source_code='8480-6' and m.event_datetime between p.observation_end-interval 365 day and p.observation_end"),q('select count(*) from person where death_datetime is null and age>=18'),'Living adults with systolic blood pressure in the prior 365 days.','primary-care')
measure('adult-bmi','Adults: recent BMI recorded',q("select count(distinct p.person_id) from person p join measurement m using(person_id) where p.death_datetime is null and p.age>=18 and m.source_code='39156-5' and m.event_datetime between p.observation_end-interval 365 day and p.observation_end"),q('select count(*) from person where death_datetime is null and age>=18'),'Living adults with BMI documented in the prior 365 days.','primary-care')
measure('flu-record','Influenza immunization recorded',q("select count(distinct p.person_id) from person p join immunization i using(person_id) where p.death_datetime is null and lower(i.source_description) like '%influenza%' and i.event_datetime between p.observation_end-interval 365 day and p.observation_end"),alive,'Living patients with a source description containing influenza in the prior 365 days. Documentation-only; no age or seasonal eligibility certification.','primary-care')
measure('followup-coverage','Readmission follow-up completeness',eligible,admissions,'Admissions with an observable 30-day outcome window. Data coverage, not clinical performance.','informatics','No exclusions from admission denominator.')
trend=rows("SELECT strftime(visit_start_datetime,'%Y-%m') AS label,count(*) encounters,count(*) FILTER(WHERE visit_class='inpatient') admissions,NULL::DOUBLE readmission_rate FROM visit_occurrence WHERE visit_start_datetime>=date '2025-09-01' AND visit_start_datetime<date '2026-09-01' GROUP BY 1 ORDER BY 1")
def chart(sql): return rows(sql)
def dept(metrics,values,title,callout,method,limitation,pushback,detail=None):
 return dict(metrics=metrics,chart=values,chart_title=title,callout=callout,method=method,limitation=limitation,pushback=pushback,rows=detail if detail is not None else values)
departments={}
departments['ed']=dept([metric('Emergency encounters',ed,'','Lifetime source classification'),metric('Median visit duration',round(edhours,2),'hours','Encounter start to stop')],chart("select extract(hour from visit_start_datetime)::varchar AS label,count(*) AS value from visit_occurrence where visit_class='emergency' group by 1 order by cast(label as integer)"),'Arrival hour',f'{ed:,} emergency encounters are recorded across complete generated histories.','Source encounter class; duration from recorded start and stop.','No arrival, triage, boarding or admission-decision milestones; duration is not a validated operational throughput measure.','A clinical leader should not infer staffing needs from these generated arrival times.')
departments['inpatient']=dept([metric('Inpatient admissions',admissions),metric('30-day return rate',readrate,'%','All-cause; complete follow-up'),metric('Eligible discharges',eligible)],chart("select strftime(prediction_time,'%Y') AS label,count(*) AS value from features where prediction_time>=date '2016-01-01' group by 1 order by 1"),'Admissions by shifted calendar year',f'{returns:,} of {eligible:,} eligible discharges have a recorded 30-day return.','Inpatient source encounters; strict after-discharge next admission, with per-patient censoring.','Planned admissions, transfers and hospital-specific eligibility are not resolved. This is not a CMS readmission rate.','Care management should inspect labeling and synthetic-population validity before interpreting model ranks.')
departments['beds']=dept([metric('Median stay',round(los,2),'days'),metric('Bed capacity',None,'','Not in source')],chart("select case when target_los_days<1 then '<1 day' when target_los_days<3 then '1-2 days' when target_los_days<7 then '3-6 days' else '7+ days' end AS label,count(*) AS value from features group by 1 order by 1"),'Recorded length of stay','Length of stay is observable; installed beds and unit occupancy are not.','Elapsed time from inpatient encounter start to stop.','No staffed-bed denominator, unit assignment, ICU transfer, or capacity claim.','A bed manager would need local capacity and transfer feeds before using an occupancy forecast.')
departments['icu']=dept([metric('NEWS2 eligibility',None,'','Unavailable'),metric('ICU census',None,'','No reliable ICU unit field')],[],'Deterioration coverage','NEWS2 remains unavailable because oxygen support, consciousness and consistent simultaneous vital sets are missing.','Availability audit of required early-warning inputs.','No score is fabricated from incomplete observations.','A rapid-response team must see complete timed inputs and validated local thresholds.')
departments['primary-care']=dept([metric('Living patients',alive),metric('Diabetes registry',cohorts[0]['count']),metric('Hypertension registry',cohorts[1]['count'])],[{'label':x['name'],'value':x['count']} for x in cohorts],'Lifetime recorded cohorts','Registry membership records coded history and does not establish current disease severity.','Observed source-code sets define reusable cohorts; recent documentation uses per-patient observation end.','Definitions are not validated phenotypes. No external SVI or survival effect is asserted.','A primary care clinician should challenge stale codes and missing outside-system care.')
departments['pharmacy']=dept([metric('Medication records',q('select count(*) from drug_exposure')),metric('Recorded drug codes',q('select count(distinct source_code) from drug_exposure'))],chart('select source_description AS label,count(*) AS value from drug_exposure group by 1 order by 2 desc limit 8'),'Most recorded medications','Prescription records support utilization summaries, not refill adherence.','Count of Synthea medication exposure records by RxNorm source description.','No dispensing coverage, days supply validation, morphine-equivalent conversion, or PDC claim.','A pharmacist would reconcile duplicate orders and outside prescriptions before measuring adherence.')
departments['lab']=dept([metric('Numeric observations',q('select count(*) from measurement')),metric('Numeric code types',q('select count(distinct source_code) from measurement'))],chart("select source_description AS label,count(*) AS value from measurement where category='laboratory' group by 1 order by 2 desc limit 8"),'Laboratory observation volume','Numeric values and units are retained; clinical abnormality thresholds are not invented.','Allowlisted numeric observations; source descriptions and units retained.','Reference ranges and specimen timestamps were not validated. No eGFR or critical-result claim.','A laboratory director would require age-specific reference ranges and assay metadata.')
departments['imaging']=dept([metric('Imaging instances',q('select count(*) from imaging')),metric('Distinct imaging encounters',q('select count(distinct visit_occurrence_id) from imaging'))],chart('select modality_description AS label,count(*) AS value from imaging group by 1 order by 2 desc'),'Recorded imaging modalities','Each source row is an imaging instance, so counts are not equivalent to complete studies.','Count source imaging rows by modality.','Series and instance identifiers are dropped during de-identification; repeat-study validity is unmeasured.','A radiologist would ask whether multiple instances belong to the same study.')
departments['surgery']=dept([metric('Procedure records',q('select count(*) from procedure_occurrence'))],chart('select source_description AS label,count(*) AS value from procedure_occurrence group by 1 order by 2 desc limit 8'),'Most recorded procedures','Procedure records include routine care and are not all operations.','Source-coded procedure occurrences.','No validated operative episode, specialty, complication or planned-return algorithm.','A surgeon would require procedure grouping and episode attribution before comparing outcomes.')
departments['finance']=dept([metric('Recorded encounter claims',round(q('select sum(total_claim_cost) from visit_occurrence'),2),'USD','Synthetic billed-claim totals'),metric('Mean claim per encounter',round(q('select avg(total_claim_cost) from visit_occurrence'),2),'USD')],chart('select payer AS label,count(*) AS value from visit_occurrence group by 1 order by 2 desc'),'Payer mix by encounter','Generated claim amounts describe simulated utilization, not clinical need or real payments.','Encounter claim sums and encounter-weighted payer counts.','No financial reconciliation, paid-amount verification, or causal cost-versus-need finding.','Finance should reject a cost model as a proxy for patient need without direct fairness evaluation.')
checks=[]
def check(name,category,checked,failed): checks.append(dict(name=name,category=category,checked=int(checked),failed=int(failed),status='pass' if failed==0 else 'review'))
for table in tables[1:]: check(table+' person link','referential integrity',q(f'select count(*) from {table}'),q(f'select count(*) from {table} t left join person p using(person_id) where p.person_id is null'))
check('Encounter date order','temporal validity',q('select count(*) from visit_occurrence'),q('select count(*) from visit_occurrence where visit_end_datetime<visit_start_datetime'))
check('Unique patient hashes','uniqueness',len(p),len(p)-q('select count(distinct person_id) from person'))
check('Readmission censoring','outcome validity',admissions,q('select count(*) from features where not readmit_eligible and target_readmit30 is not null'))
check('Numeric measurement parse','completeness',q('select count(*) from measurement'),q('select count(*) from measurement where value_as_number is null'))
check('Known encounter classes','conformance',q('select count(*) from visit_occurrence'),q("select count(*) from visit_occurrence where visit_class not in ('ambulatory','wellness','outpatient','emergency','urgentcare','inpatient','snf','home','virtual','hospice')"))
terminology=[]
for t in ['condition_occurrence','drug_exposure','procedure_occurrence','measurement']:
 total=q(f'select count(*) from {t}'); mapped=q(f"select count(*) from {t} where source_code is not null and source_code<>''")
 terminology.append(dict(table=t,mapped=mapped,total=total,coverage=round(mapped/total*100,2),meaning='Source code present; not standard OMOP concept validation.'))
k=rows('select age_band,sex,race,count(*) n from person group by all')
kreport={'quasi_identifiers':['age_band','sex','race'],'minimum_k':min(x['n'] for x in k),'groups_below_5':sum(x['n']<5 for x in k),'patients_in_groups_below_5':sum(x['n'] for x in k if x['n']<5),'claim':'Diagnostic only. These synthetic records are not certified anonymous and row-level artifacts are private.'}
quality={'checks':checks,'summary':f'{sum(x["status"]=="pass" for x in checks)} of {len(checks)} observed-data checks pass. No defects were injected; detection sensitivity was not measured.','terminology':terminology,'k_anonymity':kreport}
departments['informatics']=dept([metric('Patients de-identified',len(p)),metric('Observed checks passing',sum(x['status']=='pass' for x in checks)),metric('Minimum diagnostic k',kreport['minimum_k'])],[{'label':x['table'],'value':x['coverage']} for x in terminology],'Source code presence','HMAC identifiers, consistent patient date shifts, allowlisted columns and private patient payloads are applied before analytics.','Reduced OMOP-shaped tables; source codes retained without licensed standard-concept mapping.','Not a complete OMOP CDM implementation, Safe Harbor certification, or evaluated defect-injection system.','A governance reviewer should distinguish source-code completeness from terminology mapping accuracy.',checks)
manifest={'statement':STATEMENT,'provenance':{'source':'Official Synthea synthetic Massachusetts population','population':'2,000-patient sample','patients':len(p),'seed':20260923,'as_of':'2026-09-22','version':'d9d07a6','encounters':q('select count(*) from visit_occurrence'),'date_basis':'Patient-level dates shifted by up to 180 days; intervals and observation ends preserved.'},'overview':{'metrics':[metric('Synthetic patients',len(p)),metric('Inpatient admissions',admissions),metric('30-day all-cause return',readrate,'%','Complete follow-up; simplified'),metric('Median inpatient stay',round(los,2),'days')],'trend':trend,'insights':[{'title':'Readmission windows are censored','text':f'{admissions-eligible} inpatient encounters lack an eligible complete 30-day outcome window.','route':'/departments/inpatient'},{'title':'Lifetime source records','text':f'{q("select count(*) from visit_occurrence"):,} encounters were processed from the generated sample.','route':'/departments/informatics'},{'title':'Clinical limits remain visible','text':'ICU census and NEWS2 remain unavailable because required fields are not present.','route':'/departments/icu'}]},'departments':departments,'cohorts':cohorts,'measures':measures,'quality':quality,'schema':[{'table':t,'columns':[{'name':x[0],'type':x[1]} for x in c.execute('describe '+t).fetchall()]} for t in tables]}
dump('warehouse-schema.json',{'statement':STATEMENT,'schema':[{ 'table':t,'columns':[{'name':x[0],'type':x[1]} for x in c.execute("describe select * from read_parquet('"+(WARE/(t+'.parquet')).as_posix()+"')").fetchall()]} for t in tables]})
manifest['schema']=[{'table':'department_metrics','columns':['department','label','value','unit','note']},{'table':'cohort_counts','columns':['cohort_id','sex','age_band','count','suppressed']},{'table':'measures','columns':['id','name','numerator','denominator','value','unit','definition','exclusions','department']},{'table':'monthly_activity','columns':['label','encounters','admissions','readmission_rate']}]
dump('manifest.json',manifest)
cube=[]
for cohort in cohorts:
 for r in rows('select p.sex,p.age_band,count(*) n from cohort_'+cohort['id'].replace('-','_')+' h join person p using(person_id) group by all'):
  cube.append({'cohort_id':cohort['id'],'sex':r['sex'],'age_band':r['age_band'],'count':r['n'] if r['n']>=5 else None,'suppressed':r['n']<5})
aggregate_tables={'statement':STATEMENT,'department_metrics':[{'department':key,**m} for key,d in departments.items() for m in d['metrics']], 'cohort_counts':cube,'measures':measures,'monthly_activity':trend,'suppression':'Cohort cells with fewer than 5 people are null. No person IDs or individual records. This is a synthetic demonstration, not a disclosure-control certification.'}
dump('aggregate-tables.json',aggregate_tables)
patients=[]
for r in rows('select * from features qualify row_number() over(partition by person_id order by prediction_time desc)=1 order by prediction_time desc limit 60'):
 pid=r['person_id']; person=rows(f"select * from person where person_id='{pid}'")[0]
 timeline=rows(f"select visit_start_datetime AS date,visit_class AS type,visit_source_description AS label from visit_occurrence where person_id='{pid}' order by date desc limit 10")
 labs=rows(f"select event_datetime AS date,source_description AS label,source_code code,value_as_number AS value,unit_source_value unit from measurement where person_id='{pid}' and category='laboratory' and event_datetime<=(select observation_end from person where person_id='{pid}') order by date desc limit 10")
 conditions=rows(f"select distinct source_description AS label from condition_occurrence where person_id='{pid}' order by label limit 10")
 patients.append({'id':pid,'age_band':person['age_band'],'sex':person['sex'],'index_admission':r['prediction_time'],'observation_end':r['observation_end'],'conditions':[x['label'] for x in conditions],'timeline':timeline,'labs':labs})
private_payload={'statement':STATEMENT,'patients':patients,'date_basis':'All dates shifted by a patient-specific fixed offset; do not interpret as actual dates.'}
validate_private_payload(private_payload)
dump('private-patients.json',private_payload)
c.execute(f"EXPORT DATABASE '{(OUT/'duckdb_export').as_posix()}' (FORMAT PARQUET)") if False else None
dump('build-summary.json',{'statement':STATEMENT,'warehouse_tables':len(tables),'patients':len(p),'private_patients':len(patients),'admission_rows':admissions,'readmit_eligible':eligible,'readmit_positive':int(returns),'annual_rows':featuremeta['annual_rows'],'cohorts':len(cohorts),'measures':len(measures),'observed_checks':len(checks),'failed_checks':sum(x['status']!='pass' for x in checks)})
print(json.dumps(clean_json({'patients':len(p),'admissions':admissions,'readmit_eligible':eligible,'returns':returns,'annual_rows':featuremeta['annual_rows'],'failed_checks':sum(x['status']!='pass' for x in checks)})),flush=True)



