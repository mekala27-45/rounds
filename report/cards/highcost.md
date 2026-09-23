# Future billed-claim proxy

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

Status: **shadow**. Department: Revenue cycle and finance.

Prediction time: At the annual January 1 registry index date.

Standardized, L2 logistic regression with separate temporal Platt calibration; LightGBM evaluated as comparator.

The target is future synthetic billed encounter claims above a training-period threshold, not paid costs, treatment benefit, or clinical need. Comparing it with hospitalization risk is a proxy-choice demonstration; hospitalization is also utilization, not ground-truth need. No real-world causal or fairness conclusion follows.

## Measured results

- n: 1397
- positives: 155
- positive_rate: 0.11095204008589836
- auroc: 0.7463352553114123
- auprc: 0.381500109060407
- brier: 0.08816683065810464
- ece: 0.032657652436385506
- auroc_ci95: {"lower": 0.697757150189239, "upper": 0.7889585479036392, "method": "200 patient-cluster bootstrap replicates", "valid_replicates": 200}
- training_90th_percentile_cost_threshold: 30639.708000000006

## Comparators

- Training-prevalence constant: {"n": 1397, "positives": 155, "positive_rate": 0.11095204008589836, "auroc": 0.5, "auprc": 0.11095204008589836, "brier": 0.09875944948813094, "ece": 0.010851939985798253}
- Uncalibrated logistic regression: {"n": 1397, "positives": 155, "positive_rate": 0.11095204008589836, "auroc": 0.7463352553114123, "auprc": 0.381500109060407, "brier": 0.08662443300948876, "ece": 0.02488675035297477}
- Temporally calibrated LightGBM comparator: {"n": 1397, "positives": 155, "positive_rate": 0.11095204008589836, "auroc": 0.7654147836476026, "auprc": 0.4232529042781652, "brier": 0.0837648874667668, "ece": 0.03998254331327486}

## Gates

- PASS temporal_outcome_embargo: Each training/calibration label window finishes before the next temporal partition.
- PASS calibrator_support: Platt calibration requires at least five cases from each class in the separate calibration partition.
- PASS brier_better_than_constant: Held-out Brier 0.0882; training-prevalence baseline 0.0988.
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
  "patient_overlap_train_test": 1230,
  "cost_target": {
    "threshold": 30639.708000000006,
    "definition": "Sum of future 365-day encounter TOTAL_CLAIM_COST, synthetic billed claims, not paid costs.",
    "threshold_fit": "Training partition only; fixed in calibration and test",
    "clinical_need": false
  }
}
```

## Proxy comparison

```json
{
  "n": 1397,
  "capacity_fraction": 0.1,
  "selected_per_model": 140,
  "selection_overlap": 42,
  "method": "Same top-decile capacity, deterministic ID tie-breaking, fixed held-out population. Descriptive target-choice comparison, not causal disparity attribution.",
  "groups": [
    {
      "dimension": "race",
      "group": "asian",
      "n": 87,
      "cost_selection_rate": 0.09195402298850575,
      "hospitalization_selection_rate": 0.09195402298850575,
      "future_hospitalization_rate": 0.04597701149425287,
      "selection_rate_difference": 0.0
    },
    {
      "dimension": "race",
      "group": "black",
      "n": 107,
      "cost_selection_rate": 0.11214953271028037,
      "hospitalization_selection_rate": 0.09345794392523364,
      "future_hospitalization_rate": 0.028037383177570093,
      "selection_rate_difference": 0.01869158878504673
    },
    {
      "dimension": "race",
      "group": "hawaiian",
      "n": 18,
      "cost_selection_rate": 0.05555555555555555,
      "hospitalization_selection_rate": 0.1111111111111111,
      "future_hospitalization_rate": 0.05555555555555555,
      "selection_rate_difference": -0.05555555555555555
    },
    {
      "dimension": "race",
      "group": "native",
      "n": 9,
      "cost_selection_rate": 0.1111111111111111,
      "hospitalization_selection_rate": 0.1111111111111111,
      "future_hospitalization_rate": 0.0,
      "selection_rate_difference": 0.0
    },
    {
      "dimension": "race",
      "group": "other",
      "n": 12,
      "cost_selection_rate": 0.08333333333333333,
      "hospitalization_selection_rate": 0.16666666666666666,
      "future_hospitalization_rate": 0.0,
      "selection_rate_difference": -0.08333333333333333
    },
    {
      "dimension": "race",
      "group": "white",
      "n": 1164,
      "cost_selection_rate": 0.10051546391752578,
      "hospitalization_selection_rate": 0.10051546391752578,
      "future_hospitalization_rate": 0.03608247422680412,
      "selection_rate_difference": 0.0
    },
    {
      "dimension": "ethnicity",
      "group": "hispanic",
      "n": 160,
      "cost_selection_rate": 0.14375,
      "hospitalization_selection_rate": 0.1375,
      "future_hospitalization_rate": 0.04375,
      "selection_rate_difference": 0.006249999999999978
    },
    {
      "dimension": "ethnicity",
      "group": "nonhispanic",
      "n": 1237,
      "cost_selection_rate": 0.09458367016976556,
      "hospitalization_selection_rate": 0.09539207760711399,
      "future_hospitalization_rate": 0.034761519805982216,
      "selection_rate_difference": -0.0008084074373484323
    },
    {
      "dimension": "sex",
      "group": "F",
      "n": 677,
      "cost_selection_rate": 0.14918759231905465,
      "hospitalization_selection_rate": 0.1358936484490399,
      "future_hospitalization_rate": 0.03692762186115214,
      "selection_rate_difference": 0.013293943870014757
    },
    {
      "dimension": "sex",
      "group": "M",
      "n": 720,
      "cost_selection_rate": 0.05416666666666667,
      "hospitalization_selection_rate": 0.06666666666666667,
      "future_hospitalization_rate": 0.034722222222222224,
      "selection_rate_difference": -0.012499999999999997
    },
    {
      "dimension": "payer",
      "group": "Unknown",
      "n": 1397,
      "cost_selection_rate": 0.10021474588403723,
      "hospitalization_selection_rate": 0.10021474588403723,
      "future_hospitalization_rate": 0.03579098067287044,
      "selection_rate_difference": 0.0
    }
  ]
}
```
