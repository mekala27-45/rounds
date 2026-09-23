# Measured results

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

| label | value | unit | note |
| --- | --- | --- | --- |
| Synthetic patients | 2000 |  |  |
| Inpatient admissions | 1969 |  |  |
| 30-day all-cause return | 9.11 | % | Complete follow-up; simplified |
| Median inpatient stay | 3.01 | days |  |

## Model evaluation

| model | status | AUROC | Brier | MAE |
| --- | --- | --- | --- | --- |
| readmit30 | shadow | 0.5939569536423841 | 0.09360791866666772 | n/a |
| los | shadow | n/a | n/a | 3.243857929626617 |
| ed_arrivals | shadow | n/a | n/a | n/a |
| hosp12m | shadow | 0.6971269487750558 | 0.03290022009219866 | n/a |
| highcost | shadow | 0.7463352553114123 | 0.08816683065810464 | n/a |
| deterioration | unavailable | n/a | n/a | n/a |

## Simplified measures

| name | numerator | denominator | value | unit |
| --- | --- | --- | --- | --- |
| 30-day all-cause inpatient return | 175 | 1922 | 9.11 | % |
| Wellness visit in past year | 1478 | 1825 | 80.99 | % |
| Diabetes: recent HbA1c recorded | 112 | 113 | 99.12 | % |
| Hypertension: recent systolic BP recorded | 349 | 352 | 99.15 | % |
| CKD: recent creatinine recorded | 87 | 109 | 79.82 | % |
| Obesity: recent BMI recorded | 697 | 794 | 87.78 | % |
| Adults: recent blood pressure recorded | 1099 | 1424 | 77.18 | % |
| Adults: recent BMI recorded | 1097 | 1424 | 77.04 | % |
| Influenza immunization recorded | 1452 | 1825 | 79.56 | % |
| Readmission follow-up completeness | 1922 | 1969 | 97.61 | % |

## Quality and interoperability

| name | checked | failed | status |
| --- | --- | --- | --- |
| visit_occurrence person link | 290264 | 0 | pass |
| condition_occurrence person link | 170242 | 0 | pass |
| drug_exposure person link | 144423 | 0 | pass |
| procedure_occurrence person link | 858056 | 0 | pass |
| measurement person link | 2061403 | 0 | pass |
| imaging person link | 118428 | 0 | pass |
| immunization person link | 106181 | 0 | pass |
| observation_period person link | 2000 | 0 | pass |
| Encounter date order | 290264 | 0 | pass |
| Unique patient hashes | 2000 | 0 | pass |
| Readmission censoring | 1969 | 0 | pass |
| Numeric measurement parse | 2061403 | 0 | pass |
| Known encounter classes | 290264 | 0 | pass |

| resource | fhir_rows | csv_rows | exact_multiset_match |
| --- | --- | --- | --- |
| Patient | 300 | 300 | True |
| Encounter | 42555 | 42555 | True |
| Condition | 26828 | 26828 | True |

## Dictionary sanity check

| entity | precision | recall | f1 |
| --- | --- | --- | --- |
| condition | 1.0 | 1.0 | 1.0 |
| medication | 1.0 | 1.0 | 1.0 |
| procedure | 1.0 | 1.0 | 1.0 |

This is a lexical extraction sanity check on exact source descriptions, not independent clinical NLP validation.

## Boundaries

This sample release uses a Vinext/React application on Sites with D1-backed audit storage. The full 20,000-person run, certified clinical measures, full OMOP 5.4 mapping, complete model contract, rolling production monitoring and the original Fly/Neon architecture are not claimed. Patient-level artifacts are absent from the public bundle.
