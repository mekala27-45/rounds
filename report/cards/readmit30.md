# 30-day readmission risk

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

Status: **shadow**. Department: Inpatient and care management.

Prediction time: At inpatient admission, before any event at or after admission.

Standardized, L2 logistic regression with separate temporal Platt calibration; LightGBM evaluated as comparator.

Synthetic retrospective results only. A 360-day partition buffer protects temporal order despite per-person date shifts. Patients can recur across partitions; patient-cluster bootstrap intervals account for repeated test patients. Sparse subgroup results are descriptive. All-cause readmission includes planned returns and transfers that have not been adjudicated.

## Measured results

- n: 167
- positives: 16
- positive_rate: 0.09580838323353294
- auroc: 0.5939569536423841
- auprc: 0.1145686466184585
- brier: 0.09360791866666772
- ece: 0.051371825029572604
- auroc_ci95: {"lower": 0.46218778567800917, "upper": 0.7215629984051039, "method": "200 patient-cluster bootstrap replicates", "valid_replicates": 200}

## Comparators

- Training-prevalence constant: {"n": 167, "positives": 16, "positive_rate": 0.09580838323353294, "auroc": 0.5, "auprc": 0.09580838323353294, "brier": 0.0876716203726815, "ece": 0.03228751209015726}
- Uncalibrated logistic regression: {"n": 167, "positives": 16, "positive_rate": 0.09580838323353294, "auroc": 0.5939569536423841, "auprc": 0.1145686466184585, "brier": 0.12357398644452389, "ece": 0.1022814930802166}
- Temporally calibrated LightGBM comparator: {"n": 167, "positives": 16, "positive_rate": 0.09580838323353294, "auroc": 0.6078228476821191, "auprc": 0.18967230252624764, "brier": 0.08858690855082015, "ece": 0.05828502053416772}

## Gates

- PASS temporal_outcome_embargo: Each training/calibration label window finishes before the next temporal partition.
- PASS calibrator_support: Platt calibration requires at least five cases from each class in the separate calibration partition.
- REFUSED brier_better_than_constant: Held-out Brier 0.0936; training-prevalence baseline 0.0877.
- REFUSED auroc_at_least_065: Prespecified research demonstration discrimination gate: AUROC >= 0.65.
- REFUSED ece_at_most_005: Prespecified equal-width, ten-bin expected calibration error <= 0.05.
- REFUSED subgroup_support: Every reported subgroup needs n >= 50 and at least five positive and negative examples. Sparse groups remain visible.
- REFUSED clinical_validation: Synthetic retrospective evaluation is not clinical validation.

## Evaluation contract

```json
{
  "statement": "This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.",
  "clinical_use": false,
  "population": "Synthea Massachusetts, seed 20260923",
  "split": {
    "train_start": "2010-01-01",
    "train_label_end_exclusive": "2020-07-05",
    "calibration_start": "2021-06-30",
    "calibration_label_end_exclusive": "2023-07-05",
    "test_start": "2024-06-29",
    "calendar": "per-person shifted synthetic dates, protected by a 360-day between-partition buffer",
    "outcome_embargo": "Label windows finish at least 360 shifted-calendar days before the next partition. Because individual shifts are bounded by +/-180 days, true chronology between partitions is preserved.",
    "boundary_buffer_each_side_days": 180,
    "n_train": 551,
    "n_calibration": 164,
    "n_test": 167,
    "same_patients_can_recur": true
  },
  "features": [
    "age",
    "prior_admissions_365",
    "prior_ed_365",
    "prior_visits_365",
    "condition_count",
    "medication_count"
  ],
  "feature_availability": "Strictly prior to prediction time. No discharge disposition, LOS, future costs, or outcomes are model inputs.",
  "deployment_choice": "Logistic regression prespecified for transparent live scoring; comparator does not replace it based on test performance.",
  "calibration_method": "Platt sigmoid fitted to separate chronological calibration data",
  "model_type": "binary",
  "live_scoring": true,
  "multiple_comparisons": "Benjamini-Hochberg across displayed subgroup calibration-residual tests; normal-approximation, descriptive only.",
  "patient_overlap_train_test": 39
}
```
