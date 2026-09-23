# Length of stay

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

Status: **shadow**. Department: Bed management.

Prediction time: At admission, before current-admission outcomes.

Ridge regression on log1p length of stay; separate calibration residuals form a 90% split-conformal interval. LightGBM is a comparator.

Synthetic LOS is generator-dependent. Temporal change violates exchangeability, so 90% conformal coverage is measured on the holdout and is not guaranteed. Intervals describe individual admission uncertainty, not a confidence interval for a mean.

## Measured results

- n: 181
- mae_days: 3.243857929626617
- rmse_days: 5.2466722290220105
- conformal_coverage: 0.9005524861878453
- nominal_coverage: 0.9
- conformal_radius_days: 6.205433875894503
- mean_interval_width_days: 10.02810182136895

## Comparators

- Training median LOS: {"mae_days": 3.3449724716083487}
- LightGBM log-LOS comparator: {"mae_days": 3.2702957762380027}

## Gates

- PASS temporal_outcome_embargo: Discharge precedes the next partition for training and calibration.
- PASS mae_better_than_median: Held-out MAE compared against the training median.
- PASS holdout_coverage_at_least_085: Prespecified coverage floor of 85% for nominal 90% intervals.
- REFUSED clinical_validation: Synthetic simulation only.

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
    "n_train": 574,
    "n_calibration": 175,
    "n_test": 181,
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
  "live_scoring": true,
  "model_type": "regression",
  "conformal_quantile_rule": "ceil((n_calibration+1)*0.90)-th absolute calibration residual, clipped to n_calibration"
}
```
