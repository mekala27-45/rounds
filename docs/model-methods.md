# Reproducible model evaluation

This is a portfolio demonstration on synthetic data. It is not a medical device, has not been validated for clinical use, and must not be used to make decisions about real patients.

Run from the project root using the installed virtual environment:

```powershell
& .venv/Scripts/python.exe .cache/rounds-external/evaluation/evaluate.py
& .venv/Scripts/python.exe -m unittest discover -s .cache/rounds-external/evaluation -p test_evaluation.py -v
node .cache/rounds-external/evaluation/verify-scoring.mjs
& .venv/Scripts/python.exe .cache/rounds-external/evaluation/render_cards.py
```

The generator reads only de-identified Synthea feature artifacts from `.cache/rounds-data/processed`. The separate UCI benchmark reads the isolated official UCI source; it exports aggregate evaluation only. No UCI records belong in any Site bundle.

`models.json` contains six public aggregate model cards, including methods, measured metrics, baselines, calibration bins, decision curves, subgroup results, gates, and limitations. `model-cards/` and `RESULTS.md` are rendered from those values. `evaluation-manifest.json` records source hashes and software versions. `uci-benchmark.json` is a separately retrained benchmark, not transported-model external validation. It cannot support a temporal claim because the UCI extract has no actual dates.

`private-models.json` holds fitted logistic/scaler coefficients, fitted calibration parameters, LOS regression coefficients and conformal radius, and the ED forecasting state. `private-risks.json` contains synthetic patient/index features, predictions, and exact linear explanation contributions. `private-latest-risks.json` retains each person's latest index per model. Keep all private files server-side behind the token and audit boundary. The API can calculate predictions from the tiny coefficient file and patient feature rows, so uploading the full risks file is optional.

JavaScript scoring contract:

```javascript
const raw = model.intercept + model.feature_names.reduce((sum, name, i) =>
  sum + ((features[name] - model.means[i]) / model.scales[i]) * model.coefficients[i], 0);
const risk = 1 / (1 + Math.exp(-(raw * model.calibration_slope + model.calibration_intercept)));
const predictedDays = Math.max(0, Math.expm1(raw)); // LOS only
const interval = [Math.max(0, predictedDays - model.conformal_radius_days),
  predictedDays + model.conformal_radius_days];
```

Every binary model uses only age, prior-year inpatient/ED/all visits, pre-index condition count, and pre-index medication count. Protected demographics are used for the audit, not as model inputs. The logistic model was chosen in advance for transparent live scoring; the LightGBM comparator is not selected using test performance. Platt calibration is fitted on a separate chronological partition. Same-day conditions with only date precision are excluded from admission features. Discharge disposition, realized LOS, future costs, and target labels are not inputs.

The date-shift bound is plus or minus 180 days per person. Chronological partitions leave a 360-day gap between the previous partition's completed label windows and the next partition's predictions. This preserves order even for the worst pair of shifts. The exact resulting cutoff dates, cohort counts, and overlaps are recorded in each card. Patients may appear in multiple partitions; confidence intervals use patient-cluster bootstrap resampling in the test partition. These are simulated calendar results, not real clinical temporal validation.

The future-cost target is the sum of synthetic billed encounter claims over the next year exceeding the training-partition 90th percentile. It is neither paid cost nor healthcare need. Its top-decile selection is compared with a hospitalization-risk model at the same capacity. Hospitalization is also utilization, so the comparison illustrates target choice without claiming to reproduce causal real-world inequity.

NEWS2 remains unavailable: concurrent oxygen, consciousness, and a defensible deterioration outcome are not all established. Missing clinical observations are not imputed as normal. Failed quality gates remain visible and all computable models remain shadow demonstrations.

The independent Node process in `verify-scoring.mjs` reconstructs exported Python predictions and refuses a mismatch or an empty check. `scoring-verification.json` records its actual count and maximum difference. Unit tests cover known analytical metric values, deliberately reversed predictions, empty-evidence refusal, decision-curve arithmetic, the finite-sample conformal quantile, temporal censoring and label embargo, and multiplicity correction.
