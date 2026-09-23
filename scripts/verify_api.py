"""Verify local token/purpose gates, live scoring, and separately committed D1 audit."""
import json,sqlite3,subprocess,sys
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];BASE='http://localhost:5188';PURPOSE='Automated verification of the synthetic workflow'
def check_statement(r):assert 'not a medical device' in r.json()['statement']
def main():
    database=None
    for p in (ROOT/'.wrangler/state/v3/d1').rglob('*.sqlite'):
        with sqlite3.connect(p) as c:
            if c.execute("SELECT name FROM sqlite_master WHERE name='audit_events'").fetchone():database=p
    assert database,'Local audit database unavailable'
    s=requests.Session();r=s.post(BASE+'/api/v1/patients',json={'purpose':PURPOSE});assert r.status_code==401;check_statement(r)
    s.get(BASE+'/signin-with-chatgpt?return_to=/patients');r=s.post(BASE+'/api/v1/session',json={});assert r.status_code==200;token=r.json()['token'];headers={'Authorization':'Bearer '+token}
    r=s.post(BASE+'/api/v1/patients',headers=headers,json={'purpose':''});assert r.status_code==400;assert 'patients' not in r.json()
    r=s.post(BASE+'/api/v1/patients',headers=headers,json={'purpose':PURPOSE});assert r.status_code==200;data=r.json();check_statement(r);assert len(data['patients'])==60;audit=data['audit']['id']
    code='import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute("SELECT count(*) FROM audit_events WHERE id LIKE ?",(sys.argv[2]+":%",)).fetchone()[0])'
    observed=subprocess.check_output([sys.executable,'-c',code,str(database),audit],text=True);assert int(observed)==60
    pid=next(p['id'] for p in data['patients'] if p['risk'] is not None)
    d=s.post(BASE+'/api/v1/patients/'+pid,headers=headers,json={'purpose':PURPOSE});assert d.status_code==200;assert d.json()['audit']['id'];assert d.json()['scores']
    forecast=s.post(BASE+'/api/v1/score/ed_arrivals',headers=headers,json={'purpose':PURPOSE,'horizon':14});assert forecast.status_code==200;assert len(forecast.json()['forecast'])==14;assert forecast.json()['forecast'][0]['arrivals']==0.75
    for contacted in [True,False]:
        r=s.post(BASE+'/api/v1/contact',headers=headers,json={'purpose':PURPOSE,'person_id':pid,'contacted':contacted});assert r.status_code==200
        with sqlite3.connect(database) as c:assert c.execute('SELECT contacted FROM care_contacts WHERE person_id=?',(pid,)).fetchone()[0]==int(contacted)
    with sqlite3.connect(database) as c:c.execute("CREATE TRIGGER test_block_audit BEFORE INSERT ON audit_events BEGIN SELECT RAISE(FAIL, 'deliberate audit failure'); END")
    try:
        r=s.post(BASE+'/api/v1/patients/'+pid,headers=headers,json={'purpose':PURPOSE});assert r.status_code==503;assert 'patient' not in r.json();assert r.json()['patient_data_withheld']
    finally:
        with sqlite3.connect(database) as c:c.execute('DROP TRIGGER test_block_audit')
    routes=['','ed','inpatient','beds','icu','primary-care','pharmacy','lab','imaging','surgery','finance','informatics','cohorts','measures','models','monitoring','quality','explore','report','patients','audit']
    for route in routes:
        r=s.get(BASE+'/'+route);assert r.status_code==200,route;assert 'not a medical device' in r.text,route
    result={'routes_verified':len(routes),'unauthorized_refused':True,'empty_purpose_refused':True,'audit_observed_in_separate_process':True,'patient_payload_withheld_when_audit_fails':True,'contact_persisted_independently':True,'live_forecast_verified':True,'audit_backend':'local Cloudflare D1 SQLite, not Postgres'}
    (ROOT/'results/api-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
