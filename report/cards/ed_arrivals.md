# ED arrivals forecast

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

Status: **shadow**. Department: Emergency department.

Prediction time: Before each next calendar day; only earlier daily counts available.

Rolling mean of four previous same-weekday counts; sequential one-day backtest against last-day and last-week baselines.

A synthetic population is not a hospital catchment. Counts omit real staffing, epidemic, weather, and holiday effects. This is a count forecast, not a patient risk model.

## Measured results

- n_days: 180
- mae_arrivals: 0.7291666666666666
- rmse_arrivals: 0.8860414462340035
- mean_arrivals: 0.7222222222222222

## Comparators

- Last observed day: {"mae_arrivals": 0.8222222222222222}
- Same weekday last week: {"mae_arrivals": 0.8333333333333334}

## Gates

- PASS rolling_origin_no_lookahead: Every prediction is computed only from counts before its own date.
- PASS mae_better_than_seasonal_naive: Compared over the same final 180 daily observations.
- REFUSED operational_validation: No real hospital operations validation.

## Evaluation contract

```json
{
  "statement": "This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.",
  "clinical_use": false,
  "population": "Synthea Massachusetts, seed 20260923",
  "model_type": "forecast",
  "live_scoring": true,
  "backtest_start": "2026-03-26",
  "backtest_end": "2026-09-21",
  "forecast_date": "2026-09-22",
  "next_day_forecast": 0.75
}
```
