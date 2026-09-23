"""Meaningful release gates over the actual published and server-only artifacts."""
import json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def test_claim_gate():subprocess.run([sys.executable,str(ROOT/'scripts/assemble_evidence.py'),'--check'],check=True)
def test_public_bundle_has_no_patient_ids():
    ids=[p['id'] for p in read('data/private/patients.json')['patients']]
    for path in (ROOT/'public').rglob('*'):
        if path.is_file() and path.suffix in ['.json','.js','.html','.md']:
            text=path.read_text(encoding='utf8');assert not any(pid in text for pid in ids),path
def test_built_client_contains_no_patient_ids():
    ids=[p['id'] for p in read('data/private/patients.json')['patients']]
    files=list((ROOT/'dist/client').rglob('*.js'));assert files
    for p in files:assert not any(pid in p.read_text(encoding='utf8') for pid in ids),p
def test_every_model_has_prediction_time_and_boundaries():
    models=read('results/manifest.json')['models'];assert len(models)==6
    for m in models:
        assert m['prediction_time'];assert m['limitation'];assert m['gates'];assert m['contract']['clinical_use'] is False
def test_failed_readmission_gate_is_visible():
    m=next(x for x in read('results/manifest.json')['models'] if x['id']=='readmit30');assert m['status']=='shadow';assert any(not g['passed'] for g in m['gates'])
def test_small_published_subgroups_are_suppressed():
    for m in read('public/results/bundle.json')['models']:
        for row in m['subgroups']:assert row.get('n') is None or row['n']>=5
def test_statement_and_all_departments():
    m=read('public/results/bundle.json');assert len(m['departments'])==11;assert 'not a medical device' in m['statement'];assert m['overview']['metrics'];assert len(m['cohorts'])==10;assert len(m['measures'])==10
def test_reference_downloads_exist():
    for name in ['rounds-board-memo.md','rounds-quality-scorecard.xlsx']:assert (ROOT/'public/downloads'/name).is_file()
def test_no_em_dash_in_authored_product_or_generated_claims():
    files=list((ROOT/'app').rglob('*.tsx'))+[ROOT/'components'/name for name in ['analytics-ui.tsx','rounds-app.tsx','evidence-views.tsx','patient-views.tsx']]+[ROOT/name for name in ['README.md','RESULTS.md','report/memo.md']]
    for p in files:assert '\u2014' not in p.read_text(encoding='utf8'),p
