# Keep the readmission model in shadow. Build confidence in the workflow.

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

Source: Official Synthea synthetic Massachusetts population. Population: 2,000-patient sample. Seed: 20260923. As of: 2026-09-22.

## The decision

I recommend keeping the readmission model in shadow evaluation. Its held-out AUROC is 0.594 and Brier score is 0.0936; the published quality gates do not support promotion. This is evidence about a synthetic generator, not a basis for clinical deployment.

## What is working

The analytical foundation is reproducible. The pipeline processes 2,000 generated people and 290,264 lifetime encounters. The paired exporter check reconciles 300 people across Patient, Encounter and Condition. The defect challenge detects 7 of 7 planted classes. These checks validate their stated scope, not full OMOP or clinical correctness.

## Where the headline needs restraint

The simplified all-cause inpatient return measure is 175 of 1,922 eligible discharges (9.11%). It excludes incomplete follow-up and competing deaths, but has no planned-admission or transfer adjudication. It cannot be compared directly with a CMS condition-specific risk-standardized rate.

## The next investment, cost and risk

I would fund a time-boxed joint review by an analyst and a clinician of outcome semantics, source coverage and prediction-time definitions before another model iteration. No monetary cost, savings, staffing return or intervention effect has been measured. The principal risk is treating retrospective synthetic performance as evidence of patient benefit.

## What would change my recommendation

A governed external evaluation of the locked model, reliable dates and complete outcome windows, clinically reviewed features, subgroup evidence and a prospective workflow evaluation would justify revisiting the boundary. The UCI benchmark has a patient-disjoint split but no true dates; it is a separate benchmark, not temporal transport validation.

## Delivery boundary

This sample release uses a Vinext/React application on Sites with D1-backed audit storage. The full 20,000-person run, certified clinical measures, full OMOP 5.4 mapping, complete model contract, rolling production monitoring and the original Fly/Neon architecture are not claimed. Patient-level artifacts are absent from the public bundle.

## Evidence appendix

| label | value | unit | note |
| --- | --- | --- | --- |
| Synthetic patients | 2000 |  |  |
| Inpatient admissions | 1969 |  |  |
| 30-day all-cause return | 9.11 | % | Complete follow-up; simplified |
| Median inpatient stay | 3.01 | days |  |
