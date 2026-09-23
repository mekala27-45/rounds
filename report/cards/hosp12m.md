# 12-month hospitalization risk

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

Status: **shadow**. Department: Primary care and population health.

Prediction time: At the annual January 1 registry index date.

Standardized, L2 logistic regression with separate temporal Platt calibration; LightGBM evaluated as comparator.

Synthetic retrospective annual-index model. A 360-day partition buffer protects temporal order despite per-person date shifts. Patients can recur across partitions. Future hospitalization is a utilization outcome, not a complete measure of clinical need. Sparse subgroups limit inference.

## Measured results

- n: 1397
- positives: 50
- positive_rate: 0.03579098067287044
- auroc: 0.6971269487750558
- auprc: 0.1233449664918784
- brier: 0.03290022009219866
- ece: 0.00232197549502728
- auroc_ci95: {"lower": 0.6196783342089704, "upper": 0.7637466302124161, "method": "200 patient-cluster bootstrap replicates", "valid_replicates": 200}

## Comparators

- Training-prevalence constant: {"n": 1397, "positives": 50, "positive_rate": 0.03579098067287044, "auroc": 0.5, "auprc": 0.03579098067287044, "brier": 0.03451996153768793, "ece": 0.0031583480402378114}
- Uncalibrated logistic regression: {"n": 1397, "positives": 50, "positive_rate": 0.03579098067287044, "auroc": 0.6971269487750558, "auprc": 0.1233449664918784, "brier": 0.03316532701733088, "ece": 0.004430537106658911}
- Temporally calibrated LightGBM comparator: {"n": 1397, "positives": 50, "positive_rate": 0.03579098067287044, "auroc": 0.7138827023014106, "auprc": 0.12219577355389802, "brier": 0.03358122182356914, "ece": 0.007026294036880781}

## Gates

- PASS temporal_outcome_embargo: Each training/calibration label window finishes before the next temporal partition.
- PASS calibrator_support: Platt calibration requires at least five cases from each class in the separate calibration partition.
- PASS brier_better_than_constant: Held-out Brier 0.0329; training-prevalence baseline 0.0345.
- PASS auroc_at_least_065: Prespecified research demonstration discrimination gate: AUROC >= 0.65.
- PASS ece_at_most_005: Prespecified equal-width, ten-bin expected calibration error <= 0.05.
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
    "n_train": 4995,
    "n_calibration": 1345,
    "n_test": 1397,
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
  "patient_overlap_train_test": 1230
}
```
