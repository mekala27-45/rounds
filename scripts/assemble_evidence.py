"""Render the site bundle, memo and published numerical claims from measured evidence."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(name): return json.loads((ROOT/name).read_text(encoding='utf8'))
def output(path,text,check):
    p=ROOT/path
    if check:
        if not p.exists() or p.read_text(encoding='utf8')!=text: raise SystemExit(f'Claim gate failed: {path}')
    else:
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf8')
def table(rows,columns):
    return '| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'+'\n'.join('| '+' | '.join(str(r.get(c,'')) for c in columns)+' |' for r in rows)+'\n'
def main(check=False):
    m=read('results/base-manifest.json');models=read('results/models.json');external=read('public/results/external-summary.json');validation=read('public/results/validation.json')
    m['models']=models;m['validation']=validation;m['cohort_counts']=read('results/aggregate-tables.json')['cohort_counts'];m['uci']=read('public/results/uci-benchmark.json')
    for insight in m['overview']['insights']: insight['route']=insight['route'].split('/')[-1]
    for cohort in m['cohorts']: cohort['codes']=[c['code'] if isinstance(c,dict) else c for c in cohort['codes']]
    m['benchmarks']=[{'measure':r['name'],'national_rate_percent':r['nationalRate'],'period_start':r['start'],'period_end':r['end']} for r in external['cms']['nationalReadmissions'] if r['nationalRate'] is not None]
    m['social_context']=[{'county':r['county'],'population':r['population'],'state_relative_svi_percentile':r['overallPercentile']} for r in external['svi']['counties']]
    for model in models:
        for row in model.get('subgroups',[]):
            if row.get('n',0)<5:
                for key in list(row):
                    if key not in ['dimension','group','support']: row[key]=None
                row['support']='Suppressed: fewer than five observations'
    p=m['provenance'];readmit=next(x for x in models if x['id']=='readmit30');los=next(x for x in models if x['id']=='los');rate=m['measures'][0]
    sections=[
        {'heading':'The decision','text':f'I recommend keeping the readmission model in shadow evaluation. Its held-out AUROC is {readmit["metrics"]["auroc"]:.3f} and Brier score is {readmit["metrics"]["brier"]:.4f}; the published quality gates do not support promotion. This is evidence about a synthetic generator, not a basis for clinical deployment.'},
        {'heading':'What is working','text':f'The analytical foundation is reproducible. The pipeline processes {p["patients"]:,} generated people and {p["encounters"]:,} lifetime encounters. The paired exporter check reconciles {validation["fhir_reconciliation"]["patients_evaluated"]:,} people across Patient, Encounter and Condition. The defect challenge detects {validation["defect_challenge"]["detected_class_count"]} of {validation["defect_challenge"]["class_count"]} planted classes. These checks validate their stated scope, not full OMOP or clinical correctness.'},
        {'heading':'Where the headline needs restraint','text':f'The simplified all-cause inpatient return measure is {rate["numerator"]:,} of {rate["denominator"]:,} eligible discharges ({rate["value"]:.2f}%). It excludes incomplete follow-up and competing deaths, but has no planned-admission or transfer adjudication. It cannot be compared directly with a CMS condition-specific risk-standardized rate.'},
        {'heading':'The next investment, cost and risk','text':'I would fund a time-boxed joint review by an analyst and a clinician of outcome semantics, source coverage and prediction-time definitions before another model iteration. No monetary cost, savings, staffing return or intervention effect has been measured. The principal risk is treating retrospective synthetic performance as evidence of patient benefit.'},
        {'heading':'What would change my recommendation','text':'A governed external evaluation of the locked model, reliable dates and complete outcome windows, clinically reviewed features, subgroup evidence and a prospective workflow evaluation would justify revisiting the boundary. The UCI benchmark has a patient-disjoint split but no true dates; it is a separate benchmark, not temporal transport validation.'},
        {'heading':'Delivery boundary','text':'This sample release uses a Vinext/React application on Sites with D1-backed audit storage. The full 20,000-person run, certified clinical measures, full OMOP 5.4 mapping, complete model contract, rolling production monitoring and the original Fly/Neon architecture are not claimed. Patient-level artifacts are absent from the public bundle.'}
    ]
    m['memo']={'title':'Keep the readmission model in shadow. Build confidence in the workflow.','sections':sections}
    serialized=json.dumps(m,indent=2,allow_nan=False)+'\n'
    output('results/manifest.json',serialized,check);output('public/results/bundle.json',serialized,check)
    output('public/results/quality.json',json.dumps(m['quality'],indent=2)+'\n',check)
    memo='# '+m['memo']['title']+'\n\n'+m['statement']+'\n\n'+f'Source: {p["source"]}. Population: {p["population"]}. Seed: {p["seed"]}. As of: {p["as_of"]}.\n\n'+'\n\n'.join('## '+s['heading']+'\n\n'+s['text'] for s in sections)+'\n\n## Evidence appendix\n\n'+table(m['overview']['metrics'],['label','value','unit','note'])
    output('report/memo.md',memo,check);output('public/downloads/rounds-board-memo.md',memo,check)
    overview=table(m['overview']['metrics'],['label','value','unit','note'])
    modelrows=[{'model':x['id'],'status':x['status'],'AUROC':x['metrics'].get('auroc','n/a'),'Brier':x['metrics'].get('brier','n/a'),'MAE':x['metrics'].get('mae',x['metrics'].get('mae_days','n/a'))} for x in models]
    results='# Measured results\n\n'+m['statement']+'\n\n'+overview+'\n## Model evaluation\n\n'+table(modelrows,['model','status','AUROC','Brier','MAE'])+'\n## Simplified measures\n\n'+table(m['measures'],['name','numerator','denominator','value','unit'])+'\n## Quality and interoperability\n\n'+table(m['quality']['checks'],['name','checked','failed','status'])+'\n'+table(validation['fhir_reconciliation']['comparisons'],['resource','fhir_rows','csv_rows','exact_multiset_match'])+'\n## Dictionary sanity check\n\n'+table(validation['dictionary_nlp']['by_entity'],['entity','precision','recall','f1'])+'\n'+validation['dictionary_nlp']['limitations'][0]+'\n\n## Boundaries\n\n'+sections[-1]['text']+'\n'
    output('RESULTS.md',results,check)
    readme='# rounds\n\n'+sections[0]['text']+'\n\n'+m['statement']+'\n\n## Measured sample\n\n'+overview+'\n## Run the application\n\n```sh\nnpm ci\nnpm run dev\n```\n\nSee [the runbook](docs/runbook.md) for local D1 migrations and verification. See [measured results](RESULTS.md), [the board memo](report/memo.md), [architecture](ARCHITECTURE.md), and [the delivery scope](docs/scope.md).\n\n## Department map\n\n'+table([{'department':k,'headline':v['metrics'][0]['label'],'route':'/'+k} for k,v in m['departments'].items()],['department','headline','route'])+'\nThe executive scorecard is `/`. Additional routes cover cohorts, measures, models, monitoring, data quality, browser SQL, patient access, audit and the board memo.\n\n## Reproduce\n\nThe committed measured artifacts support `python scripts/assemble_evidence.py --check`. Pipeline scripts and exact source generation commands are retained under `pipeline/` and `docs/`. Raw Synthea and UCI files stay outside publication. All public tables are aggregates; the limited server-only patient payload requires an audited access session.\n\n## Delivery scope\n\n'+sections[-1]['text']+'\n\nCode: Apache-2.0. Synthea output is generated data. External aggregate sources and the UCI CC BY 4.0 benchmark retain their provenance in [external sources](docs/external-sources.md). IBM Plex fonts use the SIL Open Font License.\n'
    output('README.md',readme,check)
    print('Claim renderer verified.' if check else 'Rendered bundle, README, RESULTS and board memo.')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');main(parser.parse_args().check)
