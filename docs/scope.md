# Delivery scope

This is a finished, deployed sample demonstration, not fulfillment of every research and infrastructure item in the supplied day-long brief.

| Area | Delivered | Boundary |
| --- | --- | --- |
| Population | Official seeded Synthea Massachusetts sample and paired FHIR/CSV subset | The separate full-population run is not performed |
| Data platform | Allowlisted de-identification, patient-consistent date shifts, private parquet warehouse, tested cohort SQL | OMOP-shaped subset, not full CDM or HIPAA certification; no dbt implementation |
| Departments | Executive overview and every named department route, measured metrics, table/chart controls, source labels, method and clinician objections | Several clinical analyses are explicitly unavailable rather than approximated |
| Models | Temporal readmission, LOS, hospitalization and billed-claim evaluations; daily arrivals backtest; live linear scoring and aggregate forecasting | Readmission predicts at admission, not discharge. Registry models use annual indices, not visit-triggered indices. NEWS2 cannot be evaluated |
| Model governance | Baselines, calibration, decision curves, descriptive subgroups, quality gates and model cards | The complete eleven-part contract is not achieved; continuous monitoring is not running; models remain shadow demonstrations |
| External evidence | CMS aggregate benchmarks, CDC county context and a separate UCI benchmark | No locked-model transport validation, spatial patient join, clinical-need outcome or causal disparity claim |
| Patient workflow | Purpose gate, ephemeral token, server-only payload, historical scores, saved contact checkboxes, audit view | Limited synthetic worklist; not a current discharge worklist or production clinical workflow |
| Persistence | D1 audit writes verified from a separate local connection and process; failure withholds patient data | D1 replaces the brief's Neon Postgres; Fly and GitHub Pages are not used |
| Interoperability | Paired Patient, Encounter and Condition source reconciliation | Not full FHIR resource validation or a live FHIR service |
| NLP | Dictionary and negation sanity check against structured descriptions | No clinical-note generalization or scispaCy claim |
| Quality | Observed checks and separate deliberately injected challenges | Not a complete OHDSI Data Quality Dashboard port |
| Exports | Generated memo, model cards, results and formula-driven quality workbook | No Power BI project, demo video, notebooks or manufactured commit history |

Outstanding clinical analyses include risk-adjusted mortality, survival/Cox models, age-standardized incidence, medication adherence/MME/interactions, validated laboratory reference flags and eGFR, adjudicated surgery returns, occupancy capacity forecasting, and certified quality specifications. Source limitations are described on the relevant pages.

Published model results may be weak or unavailable. That is a result, not a condition to hide. The safety statement is shared across the application and API response bodies.
