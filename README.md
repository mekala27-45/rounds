# rounds

I recommend keeping the readmission model in shadow evaluation. Its held-out AUROC is 0.594 and Brier score is 0.0936; the published quality gates do not support promotion. This is evidence about a synthetic generator, not a basis for clinical deployment.

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

## Measured sample

| label | value | unit | note |
| --- | --- | --- | --- |
| Synthetic patients | 2000 |  |  |
| Inpatient admissions | 1969 |  |  |
| 30-day all-cause return | 9.11 | % | Complete follow-up; simplified |
| Median inpatient stay | 3.01 | days |  |

## Run the application

```sh
npm ci
npm run dev
```

See [the runbook](docs/runbook.md) for local D1 migrations and verification. See [measured results](RESULTS.md), [the board memo](report/memo.md), [architecture](ARCHITECTURE.md), and [the delivery scope](docs/scope.md).

## Department map

| department | headline | route |
| --- | --- | --- |
| ed | Emergency encounters | /ed |
| inpatient | Inpatient admissions | /inpatient |
| beds | Median stay | /beds |
| icu | NEWS2 eligibility | /icu |
| primary-care | Living patients | /primary-care |
| pharmacy | Medication records | /pharmacy |
| lab | Numeric observations | /lab |
| imaging | Imaging instances | /imaging |
| surgery | Procedure records | /surgery |
| finance | Recorded encounter claims | /finance |
| informatics | Patients de-identified | /informatics |

The executive scorecard is `/`. Additional routes cover cohorts, measures, models, monitoring, data quality, browser SQL, patient access, audit and the board memo.

## Reproduce

The committed measured artifacts support `python scripts/assemble_evidence.py --check`. Pipeline scripts and exact source generation commands are retained under `pipeline/` and `docs/`. Raw Synthea and UCI files stay outside publication. All public tables are aggregates; the limited server-only patient payload requires an audited access session.

## Delivery scope

This sample release uses a Vinext/React application on Sites with D1-backed audit storage. The full 20,000-person run, certified clinical measures, full OMOP 5.4 mapping, complete model contract, rolling production monitoring and the original Fly/Neon architecture are not claimed. Patient-level artifacts are absent from the public bundle.

Code: Apache-2.0. Synthea output is generated data. External aggregate sources and the UCI CC BY 4.0 benchmark retain their provenance in [external sources](docs/external-sources.md). IBM Plex fonts use the SIL Open Font License.
