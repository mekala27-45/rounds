"""Reproducible, synthetic-only model evaluation and private scoring artifacts."""
from __future__ import annotations
import argparse
import os
import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMClassifier, LGBMRegressor

ROOT = Path(os.environ.get('ROUNDS_EVALUATION_OUTPUT',Path(__file__).resolve().parents[1]/'results'/'evaluation'))
ROOT.mkdir(parents=True,exist_ok=True)
DATA = Path(os.environ.get('ROUNDS_EVALUATION_DATA',Path(__file__).resolve().parents[1]/'data'/'sample'))
SEED = 20260923
FEATURES = ['age','prior_admissions_365','prior_ed_365','prior_visits_365','condition_count','medication_count']
STATEMENT = 'This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.'

def clean(value):
    if isinstance(value, dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple,np.ndarray)): return [clean(v) for v in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,float)): return float(value) if math.isfinite(value) else None
    if isinstance(value, (np.bool_,)): return bool(value)
    if isinstance(value, (pd.Timestamp,datetime)): return value.isoformat()
    return value

def save(name, obj): (ROOT/name).write_text(json.dumps(clean(obj),indent=2,allow_nan=False),encoding='utf8')

def calibration(y,p):
    y=np.asarray(y); p=np.asarray(p); bins=[]
    for lo,hi in zip(np.linspace(0,1,11)[:-1],np.linspace(0,1,11)[1:]):
        m=(p>=lo)&((p<hi) if hi<1 else (p<=hi))
        if m.sum(): bins.append({'predicted':float(p[m].mean()),'observed':float(y[m].mean()),'n':int(m.sum()),'lower':float(lo),'upper':float(hi)})
    return bins

def binary_metrics(y,p):
    y=np.asarray(y,dtype=int); p=np.asarray(p,dtype=float); bins=calibration(y,p)
    return {'n':len(y),'positives':int(y.sum()),'positive_rate':float(y.mean()) if len(y) else None,
        'auroc':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
        'auprc':float(average_precision_score(y,p)) if y.sum()>0 else None,
        'brier':float(brier_score_loss(y,p)) if len(y) else None,
        'ece':sum(b['n']*abs(b['observed']-b['predicted']) for b in bins)/len(y) if len(y) else None}

def decision_curve(y,p):
    y=np.asarray(y,dtype=int); p=np.asarray(p); n=len(y)
    if not n:raise ValueError('Decision curves require labeled outcomes')
    return [{'threshold':t,'model':float(((p>=t)&(y==1)).sum()/n-((p>=t)&(y==0)).sum()/n*t/(1-t)),
             'all':float(y.mean()-(1-y.mean())*t/(1-t)),'none':0.0} for t in [.02,.05,.1,.15,.2,.3,.4,.5]]

def fdr_adjust(pvals):
    p=np.asarray(pvals,float); order=np.argsort(p); ranked=p[order]; adjusted=np.minimum.accumulate((ranked*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]
    out=np.empty(len(p));out[order]=np.minimum(1,adjusted);return out.tolist()

def subgroups(frame,y,p):
    out=[]
    for dimension in ['sex','age_band','race','ethnicity','payer']:
        if dimension not in frame:continue
        vals=frame[dimension].fillna('Unknown').astype(str).to_numpy()
        for group in sorted(set(vals)):
            mask=vals==group; yy=np.asarray(y)[mask]; pp=np.asarray(p)[mask]
            row={'dimension':'age' if dimension=='age_band' else dimension,'group':group,**binary_metrics(yy,pp)}
            var=float(np.sum(pp*(1-pp))); z=float((np.sum(yy)-np.sum(pp))/math.sqrt(var)) if var>0 else 0
            row.update({'predicted_rate':float(pp.mean()),'calibration_p':float(2*norm.sf(abs(z))),
                'support':'adequate' if len(yy)>=50 and yy.sum()>=5 and (1-yy).sum()>=5 else 'limited',
                'sensitivity_at_20pct':float(((pp>=.2)&(yy==1)).sum()/yy.sum()) if yy.sum() else None})
            out.append(row)
    adequate=[x for x in out if x['support']=='adequate']
    for row,q in zip(adequate,fdr_adjust([x['calibration_p'] for x in adequate])):row['calibration_q_bh']=q
    for row in out:
        if row['support']=='limited':row['calibration_p']=None;row['calibration_q_bh']=None
    return out

def cluster_auc_ci(frame,y,p,n_boot=200):
    if len(set(y))<2:return None
    groups=frame['person_id'].to_numpy(); unique=np.unique(groups); ix={g:np.where(groups==g)[0] for g in unique}; rng=np.random.default_rng(SEED); scores=[]
    for _ in range(n_boot):
        sample=np.concatenate([ix[g] for g in rng.choice(unique,len(unique),replace=True)])
        if len(np.unique(np.asarray(y)[sample]))==2:scores.append(roc_auc_score(np.asarray(y)[sample],np.asarray(p)[sample]))
    return {'lower':float(np.quantile(scores,.025)),'upper':float(np.quantile(scores,.975)),'method':f'{n_boot} patient-cluster bootstrap replicates','valid_replicates':len(scores)} if scores else None

def conformal_quantile(residuals,coverage=.9):
    a=np.sort(np.asarray(residuals,float)); k=min(len(a),math.ceil((len(a)+1)*coverage))
    if not len(a):raise ValueError('Calibration residuals are required')
    return float(a[k-1])

def dt(series):return pd.to_datetime(series,utc=True,format='mixed')

def temporal_splits(frame,target,horizon_days=30,los=False):
    d=frame.copy(); d['_time']=dt(d['prediction_time']);
    d=d.loc[(d['_time']>=pd.Timestamp('2010-01-01',tz='UTC')) & (d['age']>=18) & d[target].notna()].copy()
    c1=pd.Timestamp('2021-01-01',tz='UTC'); c2=pd.Timestamp('2024-01-01',tz='UTC'); buffer=pd.Timedelta(days=180)
    if los: complete=dt(d['discharge_time'])
    elif target=='target_readmit30':complete=dt(d['discharge_time'])+pd.Timedelta(days=30)
    else:complete=d['_time']+pd.Timedelta(days=horizon_days)
    train=d.loc[(d['_time']<c1-buffer)&(complete<c1-buffer)].copy()
    val=d.loc[(d['_time']>=c1+buffer)&(d['_time']<c2-buffer)&(complete<c2-buffer)].copy()
    test=d.loc[d['_time']>=c2+buffer].copy()
    return train,val,test,{'train_start':'2010-01-01','train_label_end_exclusive':(c1-buffer).date().isoformat(),'calibration_start':(c1+buffer).date().isoformat(),'calibration_label_end_exclusive':(c2-buffer).date().isoformat(),'test_start':(c2+buffer).date().isoformat(),'calendar':'per-person shifted synthetic dates, protected by a 360-day between-partition buffer','outcome_embargo':'Label windows finish at least 360 shifted-calendar days before the next partition. Because individual shifts are bounded by +/-180 days, true chronology between partitions is preserved.','boundary_buffer_each_side_days':180,'n_train':len(train),'n_calibration':len(val),'n_test':len(test),'same_patients_can_recur':True}

def preprocess(train,frames):
    med=train[FEATURES].apply(pd.to_numeric,errors='coerce').median().fillna(0).to_numpy()
    raw=[np.where(np.isfinite(f[FEATURES].apply(pd.to_numeric,errors='coerce').to_numpy(float)),f[FEATURES].apply(pd.to_numeric,errors='coerce').to_numpy(float),med) for f in frames]
    scaler=StandardScaler().fit(raw[0]); return [scaler.transform(x) for x in raw],med,scaler

def fit_calibrator(raw,y):
    if len(np.unique(y))!=2 or min(np.bincount(np.asarray(y,int),minlength=2))<5:return None
    cal=LogisticRegression(C=1e6,max_iter=1000,random_state=SEED).fit(np.asarray(raw).reshape(-1,1),y);return cal

def calibrated(raw,cal):return expit(raw) if cal is None else cal.predict_proba(np.asarray(raw).reshape(-1,1))[:,1]

def linear_artifact(model,med,scaler,cal=None):
    return {'type':'calibrated_logistic' if isinstance(model,LogisticRegression) else 'log1p_ridge','feature_names':FEATURES,'medians':med.tolist(),'means':scaler.mean_.tolist(),'scales':scaler.scale_.tolist(),
        'coefficients':model.coef_.reshape(-1).tolist(),'intercept':float(np.asarray(model.intercept_).reshape(-1)[0]),
        'calibration_slope':float(cal.coef_[0,0]) if cal is not None else 1.0,'calibration_intercept':float(cal.intercept_[0]) if cal is not None else 0.0}

def unavailable(id,name,dept,prediction,reason):
    return {'id':id,'name':name,'department':dept,'prediction_time':prediction,'status':'unavailable','method':'Not evaluated','limitation':reason,'metrics':{},'baselines':[],'calibration':[],'decision_curve':[],'subgroups':[],
        'gates':[{'name':'outcome_and_features_available','passed':False,'reason':reason}],
        'contract':{'statement':STATEMENT,'clinical_use':False,'population':'Synthea Massachusetts, seed 20260923','live_scoring':False}}

def binary_model(frame,target,id,name,dept,horizon_days=30):
    train,val,test,split=temporal_splits(frame,target,horizon_days)
    pred_time='At inpatient admission, before any event at or after admission' if id=='readmit30' else 'At the annual January 1 registry index date'
    if min(len(train),len(val),len(test))<30 or len(train[target].unique())<2 or len(test[target].unique())<2:
        card=unavailable(id,name,dept,pred_time,'Insufficient labeled temporal partitions for genuine model evaluation.');card['contract']['split']=split;return card,None,[]
    xx,med,scaler=preprocess(train,[train,val,test]); xtr,xv,xt=xx
    ytr=train[target].astype(int).to_numpy(); yv=val[target].astype(int).to_numpy(); yt=test[target].astype(int).to_numpy()
    lr=LogisticRegression(C=.5,max_iter=2000,random_state=SEED).fit(xtr,ytr)
    lr_cal=fit_calibrator(lr.decision_function(xv),yv); lr_pred=calibrated(lr.decision_function(xt),lr_cal)
    lgb=LGBMClassifier(n_estimators=160,learning_rate=.035,num_leaves=12,min_child_samples=40,reg_lambda=3,random_state=SEED,n_jobs=2,verbosity=-1).fit(xtr,ytr)
    gb_cal=fit_calibrator(lgb.predict(xv,raw_score=True),yv);gb_pred=calibrated(lgb.predict(xt,raw_score=True),gb_cal)
    base=np.full(len(test),float(ytr.mean())); metrics=binary_metrics(yt,lr_pred);metrics['auroc_ci95']=cluster_auc_ci(test,yt,lr_pred)
    baseline=binary_metrics(yt,base); comparison=binary_metrics(yt,gb_pred)
    groups=subgroups(test,yt,lr_pred);adequate=[g for g in groups if g['support']=='adequate']
    gates=[{'name':'temporal_outcome_embargo','passed':True,'reason':'Each training/calibration label window finishes before the next temporal partition.'},
        {'name':'calibrator_support','passed':lr_cal is not None,'reason':'Platt calibration requires at least five cases from each class in the separate calibration partition.'},
        {'name':'brier_better_than_constant','passed':metrics['brier']<baseline['brier'],'reason':f"Held-out Brier {metrics['brier']:.4f}; training-prevalence baseline {baseline['brier']:.4f}."},
        {'name':'auroc_at_least_065','passed':bool(metrics['auroc']>=.65),'reason':'Prespecified research demonstration discrimination gate: AUROC >= 0.65.'},
        {'name':'ece_at_most_005','passed':bool(metrics['ece']<=.05),'reason':'Prespecified equal-width, ten-bin expected calibration error <= 0.05.'},
        {'name':'subgroup_support','passed':bool(groups and all(g['support']=='adequate' for g in groups)),'reason':'Every reported subgroup needs n >= 50 and at least five positive and negative examples. Sparse groups remain visible.'},
        {'name':'clinical_validation','passed':False,'reason':'Synthetic retrospective evaluation is not clinical validation.'}]
    art=linear_artifact(lr,med,scaler,lr_cal);art.update({'id':id,'prediction_time':pred_time,'status':'shadow','target':target,'threshold':.2,'statement':STATEMENT})
    reconstructed=expit((xt@np.array(art['coefficients'])+art['intercept'])*art['calibration_slope']+art['calibration_intercept'])
    np.testing.assert_allclose(reconstructed,lr_pred,atol=1e-12)
    card={'id':id,'name':name,'department':dept,'prediction_time':pred_time,'status':'shadow','method':'Standardized, L2 logistic regression with separate temporal Platt calibration; LightGBM evaluated as comparator.',
        'limitation':'Synthetic retrospective results only. A 360-day partition buffer protects temporal order despite per-person date shifts. Patients can recur across partitions; patient-cluster bootstrap intervals account for repeated test patients. Sparse subgroup results are descriptive. All-cause readmission includes planned returns and transfers that have not been adjudicated.' if id=='readmit30' else 'Synthetic retrospective annual-index model. A 360-day partition buffer protects temporal order despite per-person date shifts. Patients can recur across partitions. Future hospitalization is a utilization outcome, not a complete measure of clinical need. Sparse subgroups limit inference.',
        'metrics':metrics,'baselines':[{'name':'Training-prevalence constant',**baseline},{'name':'Uncalibrated logistic regression',**binary_metrics(yt,lr.predict_proba(xt)[:,1])},{'name':'Temporally calibrated LightGBM comparator',**comparison}],
        'calibration':calibration(yt,lr_pred),'decision_curve':decision_curve(yt,lr_pred),'subgroups':groups,'gates':gates,
        'contract':{'statement':STATEMENT,'clinical_use':False,'population':'Synthea Massachusetts, seed 20260923','split':split,'features':FEATURES,'feature_availability':'Strictly prior to prediction time. No discharge disposition, LOS, future costs, or outcomes are model inputs.','deployment_choice':'Logistic regression prespecified for transparent live scoring; comparator does not replace it based on test performance.','calibration_method':'Platt sigmoid fitted to separate chronological calibration data' if lr_cal is not None else 'Unavailable; raw logistic probabilities retained','model_type':'binary','live_scoring':True,'multiple_comparisons':'Benjamini-Hochberg across displayed subgroup calibration-residual tests; normal-approximation, descriptive only.','patient_overlap_train_test':len(set(train.person_id)&set(test.person_id))}}
    frame=frame.loc[frame.age>=18].copy()
    art['input_domain']={'minimum_age':18,'maximum_age':90,'nonnegative_features':FEATURES,'scope':'Synthetic adults only, no clinical validation'}
    allx=np.where(np.isfinite(frame[FEATURES].apply(pd.to_numeric,errors='coerce').to_numpy(float)),frame[FEATURES].apply(pd.to_numeric,errors='coerce').to_numpy(float),med);z=scaler.transform(allx); p=calibrated(lr.decision_function(z),lr_cal)
    rows=[]
    for k,(_,r) in enumerate(frame.iterrows()):
        contributions=z[k]*lr.coef_[0]*art['calibration_slope']; top=np.argsort(np.abs(contributions))[::-1][:3]
        rows.append({'index_id':str(r['index_id']),'person_id':str(r['person_id']),'prediction_time':r['prediction_time'],'model_id':id,'risk':float(p[k]),'features':dict(zip(FEATURES,allx[k].tolist())),'explanations':[{'feature':FEATURES[j],'contribution_log_odds':float(contributions[j]),'direction':'increases' if contributions[j]>=0 else 'decreases'} for j in top],'explanation_method':'Exact linear contribution to calibrated log odds relative to training feature means, not causal attribution.'})
    return card,art,rows

def los_model(frame):
    train,val,test,split=temporal_splits(frame,'target_los_days',los=True)
    if min(map(len,[train,val,test]))<30:return unavailable('los','Length of stay','Bed management','At admission','Insufficient complete temporal admission partitions.'),None,[]
    xx,med,scaler=preprocess(train,[train,val,test]); xtr,xv,xt=xx; ytr=train.target_los_days.to_numpy(float);yv=val.target_los_days.to_numpy(float);yt=test.target_los_days.to_numpy(float)
    lr=Ridge(alpha=10).fit(xtr,np.log1p(ytr));vp=np.maximum(0,np.expm1(lr.predict(xv)));p=np.maximum(0,np.expm1(lr.predict(xt)));q=conformal_quantile(np.abs(yv-vp));lo=np.maximum(0,p-q);hi=p+q
    gb=LGBMRegressor(n_estimators=160,num_leaves=12,min_child_samples=40,learning_rate=.035,reg_lambda=3,verbosity=-1,random_state=SEED,n_jobs=2).fit(xtr,np.log1p(ytr));gp=np.maximum(0,np.expm1(gb.predict(xt)))
    base=np.full(len(test),np.median(ytr));mae=float(mean_absolute_error(yt,p));baseline=float(mean_absolute_error(yt,base));coverage=float(np.mean((yt>=lo)&(yt<=hi)))
    art=linear_artifact(lr,med,scaler);art.update({'id':'los','conformal_radius_days':q,'nominal_coverage':.9,'statement':STATEMENT,'status':'shadow'})
    card={'id':'los','name':'Length of stay','department':'Bed management','prediction_time':'At admission, before current-admission outcomes','status':'shadow','method':'Ridge regression on log1p length of stay; separate calibration residuals form a 90% split-conformal interval. LightGBM is a comparator.',
        'limitation':'Synthetic LOS is generator-dependent. Temporal change violates exchangeability, so 90% conformal coverage is measured on the holdout and is not guaranteed. Intervals describe individual admission uncertainty, not a confidence interval for a mean.',
        'metrics':{'n':len(yt),'mae_days':mae,'rmse_days':float(math.sqrt(mean_squared_error(yt,p))),'conformal_coverage':coverage,'nominal_coverage':.9,'conformal_radius_days':q,'mean_interval_width_days':float(np.mean(hi-lo))},
        'baselines':[{'name':'Training median LOS','mae_days':baseline},{'name':'LightGBM log-LOS comparator','mae_days':float(mean_absolute_error(yt,gp))}],
        'calibration':[],'decision_curve':[],'subgroups':[],
        'gates':[{'name':'temporal_outcome_embargo','passed':True,'reason':'Discharge precedes the next partition for training and calibration.'},{'name':'mae_better_than_median','passed':mae<baseline,'reason':'Held-out MAE compared against the training median.'},{'name':'holdout_coverage_at_least_085','passed':coverage>=.85,'reason':'Prespecified coverage floor of 85% for nominal 90% intervals.'},{'name':'clinical_validation','passed':False,'reason':'Synthetic simulation only.'}],
        'contract':{'statement':STATEMENT,'clinical_use':False,'population':'Synthea Massachusetts, seed 20260923','split':split,'features':FEATURES,'live_scoring':True,'model_type':'regression','conformal_quantile_rule':'ceil((n_calibration+1)*0.90)-th absolute calibration residual, clipped to n_calibration'}}
    rows=[]
    for k,(_,r) in enumerate(test.iterrows()):
        rows.append({'index_id':str(r['index_id']),'person_id':str(r['person_id']),'prediction_time':r['prediction_time'],'model_id':'los','predicted_days':float(p[k]),'lower_days':float(lo[k]),'upper_days':float(hi[k]),'features':{f:float(r[f]) for f in FEATURES}})
    return card,art,rows

def ed_model(path):
    d=pd.read_csv(path) if path.suffix=='.csv' else pd.read_parquet(path); datecol=next((c for c in ['date','day','DATE'] if c in d),None);countcol=next((c for c in ['count','arrivals','ed_arrivals','n'] if c in d),None)
    if not datecol or not countcol:return unavailable('ed_arrivals','ED arrivals','Emergency department','Before each next calendar day','Daily aggregate schema unsupported.'),None
    d['date']=dt(d[datecol]); d=d.sort_values('date'); d=d.loc[d.date>=pd.Timestamp('2020-01-01',tz='UTC')];series=d.set_index('date')[countcol].astype(float).asfreq('D',fill_value=0); y=series.to_numpy();dates=series.index
    if len(y)<180:return unavailable('ed_arrivals','ED arrivals','Emergency department','Before each next calendar day','Fewer than 180 complete daily observations.'),None
    start=max(56,len(y)-180); pred=[];naive=[];seasonal=[];actual=[];daily=[]
    for i in range(start,len(y)):
        p=float(np.mean([y[i-j] for j in [7,14,21,28] if i>=j]));n=float(y[i-1]);s=float(y[i-7]);pred.append(p);naive.append(n);seasonal.append(s);actual.append(y[i]);daily.append({'date':dates[i].date().isoformat(),'observed':float(y[i]),'predicted':p,'naive':n,'seasonal':s})
    metrics={'n_days':len(actual),'mae_arrivals':float(mean_absolute_error(actual,pred)),'rmse_arrivals':float(math.sqrt(mean_squared_error(actual,pred))),'mean_arrivals':float(np.mean(actual))};bm=float(mean_absolute_error(actual,seasonal));pred_next=float(np.mean([y[len(y)-j] for j in [7,14,21,28]]))
    card={'id':'ed_arrivals','name':'ED arrivals forecast','department':'Emergency department','prediction_time':'Before each next calendar day; only earlier daily counts available','status':'shadow','method':'Rolling mean of four previous same-weekday counts; sequential one-day backtest against last-day and last-week baselines.','limitation':'A synthetic population is not a hospital catchment. Counts omit real staffing, epidemic, weather, and holiday effects. This is a count forecast, not a patient risk model.','metrics':metrics,'baselines':[{'name':'Last observed day','mae_arrivals':float(mean_absolute_error(actual,naive))},{'name':'Same weekday last week','mae_arrivals':bm}], 'calibration':[],'decision_curve':[],'subgroups':[],'backtest':daily,
        'gates':[{'name':'rolling_origin_no_lookahead','passed':True,'reason':'Every prediction is computed only from counts before its own date.'},{'name':'mae_better_than_seasonal_naive','passed':metrics['mae_arrivals']<bm,'reason':'Compared over the same final 180 daily observations.'},{'name':'operational_validation','passed':False,'reason':'No real hospital operations validation.'}],
        'contract':{'statement':STATEMENT,'clinical_use':False,'population':'Synthea Massachusetts, seed 20260923','model_type':'forecast','live_scoring':True,'backtest_start':dates[start].date().isoformat(),'backtest_end':dates[-1].date().isoformat(),'forecast_date':(dates[-1]+pd.Timedelta(days=1)).date().isoformat(),'next_day_forecast':pred_next}}
    art={'id':'ed_arrivals','type':'weekday_mean4','last_date':dates[-1].date().isoformat(),'last_28_counts':y[-28:].tolist(),'next_day_forecast':pred_next,'statement':STATEMENT}
    return card,art

def uci_benchmark():
    path=Path(os.environ.get('ROUNDS_UCI_CSV',ROOT.parents[1]/'data'/'external'/'diabetic_data.csv'))
    if not path.exists():return {'status':'unavailable','reason':'UCI source file unavailable'}
    d=pd.read_csv(path);d=d.loc[d.gender.isin(['Male','Female'])].copy();d['age_mid']=d.age.str.extract(r'\[(\d+)')[0].astype(float)+5;d=d.loc[d.age_mid>=18]
    cols=['age_mid','number_outpatient','number_emergency','number_inpatient'];d['partition']=d.patient_nbr.astype(str).map(lambda s:int(hashlib.sha256((str(SEED)+s).encode()).hexdigest()[:8],16)%100)
    tr=d.loc[d.partition<70];va=d.loc[(d.partition>=70)&(d.partition<85)];te=d.loc[d.partition>=85];sc=StandardScaler().fit(tr[cols]);lr=LogisticRegression(C=.5,max_iter=1000,random_state=SEED).fit(sc.transform(tr[cols]),(tr.readmitted=='<30').astype(int));cal=fit_calibrator(lr.decision_function(sc.transform(va[cols])),(va.readmitted=='<30').astype(int));p=calibrated(lr.decision_function(sc.transform(te[cols])),cal);y=(te.readmitted=='<30').astype(int).to_numpy()
    return {'status':'separate_benchmark','source':'https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008','license':'CC BY 4.0','method':'Patient-disjoint deterministic hash split 70/15/15, logistic baseline with held-out Platt calibration. Features are age-band midpoint and recorded prior-year outpatient, ED, and inpatient visit counts.','features':cols,'split':{'train_encounters':len(tr),'calibration_encounters':len(va),'test_encounters':len(te),'train_patients':tr.patient_nbr.nunique(),'test_patients':te.patient_nbr.nunique(),'patient_overlap':len(set(tr.patient_nbr)&set(te.patient_nbr))},'metrics':binary_metrics(y,p),'calibration':calibration(y,p),'decision_curve':decision_curve(y,p),'transported_model':False,'temporal_validation':False,'limitation':'Retrained independent benchmark, not external validation of the locked Synthea model. UCI lacks real dates and timestamped feature availability. Outcome and feature semantics differ. No UCI patient-level records are exported.'}

def cost_model(frame,all_risks):
    if 'target_next365_cost' not in frame:return unavailable('highcost','Cost versus clinical need','Revenue cycle and finance','Annual registry index date','Future synthetic billed-claim amounts are unavailable.'),None,[]
    tr,_,_,_=temporal_splits(frame,'target_next365_cost',365)
    if len(tr)<30:return unavailable('highcost','Cost versus clinical need','Revenue cycle and finance','Annual registry index date','Insufficient prior-period complete cost labels.'),None,[]
    threshold=float(tr.target_next365_cost.quantile(.9));d=frame.copy();d['target_highcost']=np.where(d.target_next365_cost.notna(),(d.target_next365_cost>threshold).astype(float),np.nan)
    card,art,rows=binary_model(d,'target_highcost','highcost','Future billed-claim proxy','Revenue cycle and finance',365)
    if art is None:return card,art,rows
    art['cost_target_threshold']=threshold;art['cost_definition']='Sum of future 365-day encounter TOTAL_CLAIM_COST, synthetic billed claims, not paid costs.'
    card['metrics']['training_90th_percentile_cost_threshold']=threshold
    card['limitation']='The target is future synthetic billed encounter claims above a training-period threshold, not paid costs, treatment benefit, or clinical need. Comparing it with hospitalization risk is a proxy-choice demonstration; hospitalization is also utilization, not ground-truth need. No real-world causal or fairness conclusion follows.'
    card['contract']['cost_target']={'threshold':threshold,'definition':art['cost_definition'],'threshold_fit':'Training partition only; fixed in calibration and test','clinical_need':False}
    _,_,test,_=temporal_splits(d,'target_highcost',365);cost={r['index_id']:r['risk'] for r in rows};need={r['index_id']:r['risk'] for r in all_risks if r['model_id']=='hosp12m'};test=test.loc[test.index_id.isin(need)].copy()
    if len(test):
        test['_cost_score']=test.index_id.map(cost);test['_hosp_score']=test.index_id.map(need);k=math.ceil(.1*len(test));cost_selected=set(test.sort_values(['_cost_score','index_id'],ascending=[False,True]).head(k).index_id);hosp_selected=set(test.sort_values(['_hosp_score','index_id'],ascending=[False,True]).head(k).index_id);test['_cost_selected']=test.index_id.isin(cost_selected);test['_hosp_selected']=test.index_id.isin(hosp_selected)
        comparison=[]
        for dimension in ['race','ethnicity','sex','payer']:
            for group,g in test.groupby(dimension,dropna=False):comparison.append({'dimension':dimension,'group':str(group),'n':len(g),'cost_selection_rate':float(g._cost_selected.mean()),'hospitalization_selection_rate':float(g._hosp_selected.mean()),'future_hospitalization_rate':float(g.target_hosp12m.mean()),'selection_rate_difference':float(g._cost_selected.mean()-g._hosp_selected.mean())})
        card['proxy_comparison']={'n':len(test),'capacity_fraction':.1,'selected_per_model':k,'selection_overlap':len(cost_selected&hosp_selected),'method':'Same top-decile capacity, deterministic ID tie-breaking, fixed held-out population. Descriptive target-choice comparison, not causal disparity attribution.','groups':comparison}
    return card,art,rows

def main():
    warnings.filterwarnings('ignore',message='X does not have valid feature names')
    models=[];private=[];risks=[]
    admissions=DATA/'features.parquet'; registry=DATA/'hosp12m.parquet'
    if admissions.exists():
        frame=pd.read_parquet(admissions)
        c,a,r=binary_model(frame,'target_readmit30','readmit30','30-day readmission risk','Inpatient and care management');models.append(c);private.extend([a] if a else []);risks+=r
        c,a,r=los_model(frame);models.append(c);private.extend([a] if a else []);risks+=r
    else:raise FileNotFoundError(admissions)
    edpath=next((DATA/n for n in ['ed_daily.csv','ed_daily.parquet','ed-daily.csv'] if (DATA/n).exists()),None)
    if edpath:c,a=ed_model(edpath);models.append(c);private.extend([a] if a else [])
    else:models.append(unavailable('ed_arrivals','ED arrivals forecast','Emergency department','Before each next day','Complete daily ED counts are unavailable.'))
    if registry.exists():
        registry_frame=pd.read_parquet(registry)
        c,a,r=binary_model(registry_frame,'target_hosp12m','hosp12m','12-month hospitalization risk','Primary care and population health',365);models.append(c);private.extend([a] if a else []);risks+=r
        c,a,r=cost_model(registry_frame,risks);models.append(c);private.extend([a] if a else []);risks+=r
    else:models.append(unavailable('hosp12m','12-month hospitalization risk','Primary care and population health','Annual registry index date','Complete one-year feature/outcome cohort unavailable.'))
    if not any(m['id']=='highcost' for m in models):models.append(unavailable('highcost','Cost versus clinical need','Revenue cycle and finance','Annual registry index date','Future cost labels unavailable.'))
    models.append(unavailable('deterioration','NEWS2 deterioration assessment','ICU and rapid response','At the complete observation set','Synthea does not provide a reliable concurrent full NEWS2 observation set, including supplemental oxygen and new confusion, paired with a defensible deterioration outcome. A partial score is not imputed as normal.'))
    save('models.json',models);save('private-models.json',private);save('private-risks.json',risks);save('uci-benchmark.json',uci_benchmark())
    latest={}
    for r in risks:
        k=(r['person_id'],r['model_id'])
        if k not in latest or r['prediction_time']>latest[k]['prediction_time']:latest[k]=r
    save('private-latest-risks.json',list(latest.values()))
    save('evaluation-manifest.json',{'generated_at':datetime.now(timezone.utc).isoformat(),'seed':SEED,'statement':STATEMENT,'features':FEATURES,'source_sha256':{str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in [admissions,registry] if p.exists()},'software':{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__},'models':[{'id':m['id'],'status':m['status'],'metrics':m['metrics']} for m in models]})
    print(json.dumps(clean([{'id':m['id'],'status':m['status'],'metrics':m['metrics']} for m in models]),indent=2))

if __name__=='__main__':main()
