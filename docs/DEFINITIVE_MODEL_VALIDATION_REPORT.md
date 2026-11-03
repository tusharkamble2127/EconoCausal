# DEFINITIVE MODEL VALIDATION REPORT

## 1. Executive Summary

The production pipeline was executed with EconML `LinearDML`, `RandomForestRegressor` nuisance models, `discrete_treatment=False`, and `random_state=42`. The seed-42 run and all five additional requested runs completed successfully. Software-path checks passed: leakage audit, confidence-service checks, DoWhy identification/refutation, and the canonical backend suite.

The canonical backend suite was run with `backend\.venv_py312\Scripts\python.exe -m pytest tests -q` from `backend`: **218 passed, 0 failed, 0 skipped** in 907.99 seconds. The run emitted 35,351 dependency and numerical warnings; no test failures occurred.

The model is **not validated for causal-estimation quality**. At the baseline, estimated ATE at 10 was `0.0008905` versus true ATE `0.0209151` (95.74% relative error), with ITE Pearson correlation `0.2504`. The dominant explanation is a confirmed model-specification mismatch: the generator is nonlinear on the probability scale, while production `LinearDML` estimates a linear continuous-dose effect.

## 2. Production Model Configuration

- Estimator: EconML `LinearDML`
- Nuisance models: `RandomForestRegressor`
- Treatment: continuous (`discrete_treatment=False`)
- Random state: `42`
- Feature builder: `backend/app/pipeline/features.py::engineer`
- ITE code: `backend/app/pipeline/dml_model.py::estimate_ite`, using `est.effect(X, T0=0, T1=level)`
- Features: `tenure_months`, `past_purchase_frequency`, `loyalty_score`, `avg_order_value`
- Generator: `generate_mock_data.generate(n=2000, seed=42)`

## 3. Ground-Truth Definition

For customer features `L`, the validation generator defines:

```text
true_ITE(L) = expit(eta0 + L*theta) - expit(eta0)
```

Production `LinearDML` estimates:

```text
estimated_ITE(L) = estimated_marginal_effect(X) * L
```

The generator's logistic probability response is nonlinear in treatment. `LinearDML`'s linear dose assumption is therefore not the same functional form. This is not automatically a software bug.

## 4. Baseline Results

- Sample count: `2000`
- Treatment distribution: `0=$854`, `10=$105`, `20=$1041`
- Estimated ITE: mean `0.0008905`, std `0.0199061`, min `-0.0517116`, max `0.0644417`
- True ITE: mean `0.0209151`, std `0.0073294`, min `0.0059496`, max `0.0349234`
- ITE MAE: `0.0234401`
- ITE RMSE / PEHE: `0.0278909`
- Pearson correlation: `0.2503559`
- True ATE at 10: `0.0209151`
- Estimated ATE at 10: `0.0008905`
- ATE absolute error: `0.0200246`
- ATE relative error: `0.9574243`

| Level | Training status | True ATE | Estimated ATE | ITE MAE |
|---:|---|---:|---:|---:|
| 5 | interpolated | 0.0104556 | 0.0004452 | 0.0117152 |
| 10 | observed | 0.0209151 | 0.0008905 | 0.0234401 |
| 15 | interpolated | 0.0313666 | 0.0013357 | 0.0351668 |
| 20 | observed | 0.0417985 | 0.0017809 | 0.0468866 |
| 25 | extrapolated | 0.0521987 | 0.0022262 | 0.0585905 |
| 30 | extrapolated | 0.0625554 | 0.0026714 | 0.0702711 |

## 5. Multi-Seed Results

All six runs completed: `n=2000` seeds `42, 7, 123, 456, 789`, and `n=1500` seed `42`.

| Metric | Mean | Sample SD | Min | Max |
|---|---:|---:|---:|---:|
| ITE MAE | 0.0226625 | 0.0079240 | 0.0074696 | 0.0306689 |
| ITE RMSE | 0.0278329 | 0.0098639 | 0.0092661 | 0.0387165 |
| PEHE | 0.0278329 | 0.0098639 | 0.0092661 | 0.0387165 |
| ITE correlation | 0.1624941 | 0.6227778 | -0.8162533 | 0.8824578 |
| True ATE | 0.0209965 | 0.0001045 | 0.0208545 | 0.0211261 |
| Estimated ATE | 0.0236421 | 0.0139346 | 0.0008905 | 0.0445291 |
| ATE absolute error | 0.0093205 | 0.0098825 | 0.0011497 | 0.0235727 |
| ATE relative error | 0.4445302 | 0.4722668 | 0.0551279 | 1.1248429 |

The large cross-seed variation in correlation and ATE error is consistent with poor specification/finite-sample behavior, not a successful accuracy validation.

## 6. Manual ITE Verification

Twenty customers were independently checked at levels 10 and 20 using the actual trained `LinearDML` runtime and `est.effect(X, T0=0, T1=level)`.

- Level 10: mean absolute error `0.0235099`; maximum `0.0544950`
- Level 20: mean absolute error `0.0471490`; maximum `0.1094008`
- Combined: mean absolute error `0.0353295`; maximum `0.1094008`

The customer-level records are in `artifacts/definitive_validation/manual_ite_validation.csv`.

## 7. Confidence Score Verification

The actual implementations inspected were `confidence_service.py::compute` and `recommendation_service.py::_compute_recommendations`.

All requested checks passed:

1. `chosen_ite` matched the selected customer and discount.
2. CI bounds matched the same customer and discount.
3. Confidence recomputation received the correct chosen ITE.
4. Zero discount returned score `0` and `Insufficient Evidence`.
5. Missing, NaN, infinite, and reversed intervals returned score `0`.
6. Scores were bounded on `[0,1]`.
7. Changing chosen ITE changed confidence (`0.935` to `0.954` in the sensitivity case).
8. A wider interval lowered confidence (`0.935` to `0.566`).
9. A narrower interval improved confidence (`0.566` to `0.975` in the wide/narrow comparison).
10. Failed refutation lowered confidence (`0.935` to `0.785`).
11. Evidence fields were internally consistent.

EconML runtime intervals were centered on the runtime point estimate to within `8.33e-17` maximum absolute error. Persisted versus runtime CI bounds differed by at most `4.996e-15`. This centering is expected: EconML `NormalInferenceResults.conf_int` uses symmetric normal quantiles around the point estimate (`econml/inference/_inference.py:1054-1076`), not a separate asymmetric interval calculation.

## 8. Leakage Audit

Overall: **PASS**.

| Check | Result | Responsible source |
|---|---|---|
| Treatment absent from X | PASS | `features.py::engineer` |
| Outcome absent from X | PASS | `features.py::engineer` |
| Customer ID absent from X | PASS | `features.py::engineer`, `NON_FEATURE_COLUMNS` |
| Dataset ID absent from X | PASS | `features.py::engineer`, `NON_FEATURE_COLUMNS` |
| True ITE absent from training | PASS | `features.py::engineer`, `dml_model.py::train` |
| True theta absent from training | PASS | pipeline code-token audit |
| No target-derived preprocessing features | PASS | `features.py::engineer` |
| No explicit test-target training leak | PASS | `dml_model.py::train`; LinearDML internal CV |
| Synthetic truth validation-only | PASS | generator/pipeline source audit |

Runtime X contained only the four intended confounders.

## 9. Controlled Treatment-Effect Experiment

Only the validation generator's effect multiplier changed. Production model code was unchanged.

| Experiment | Multiplier | True ATE@10 | Estimated ATE@10 | Mean confidence |
|---|---:|---:|---:|---:|
| Baseline | 1.0x | 0.0209151 | 0.0008905 | 0.2817185 |
| Increased | 2.0x | 0.0417985 | 0.0245842 | 0.3076985 |
| Decreased | 0.5x | 0.0104556 | -0.0090365 | 0.1911440 |

The estimated ATE and mean estimated ITE moved in the expected direction relative to baseline for increased and decreased effects. The decreased-effect estimate crossed below zero even though true ATE remained positive, showing that direction-of-change is not evidence of accurate sign or magnitude. Recommendation allocations were 1000 zero/1000 30 for baseline and increased effect; decreased effect allocated 1307 zero and 693 at 30.

## 10. Treatment-Dose Interpolation/Extrapolation

Observed training levels were exactly `0, 10, 20`.

- `5` and `15`: interpolated
- `25` and `30`: extrapolated
- `10` and `20`: observed

The model's linear dose form explicitly extrapolates beyond the observed treatment support. Levels 25 and 30 must not be described as directly learned from observed treatment levels.

## 11. DoWhy Validation

The production `causal_graph` path was executed on the seed-42 data.

- Identification success: **PASS**
- Estimator success: **PASS**
- Estimator: `backdoor.linear_regression`
- Estimated effect per unit treatment: `0.0005461516`
- Implied ATE at 10: `0.0054615156`
- Refutation methods: `placebo_treatment`, `random_common_cause`, `data_subset`
- Refutation result: all three passed
- Overall refutation pass: **PASS**
- Runtime: `11.6450` seconds

DoWhy's linear estimator is itself a linear approximation to the nonlinear generator and should not be interpreted as independent proof of the `LinearDML` estimate.

## 12. Model-Specification Finding

Across all 14,000 customer-level predictions in the baseline artifact:

- Mean absolute difference between linear dose approximation and nonlinear true ITE: `0.1030283`
- RMSE: `0.1298613`
- Maximum absolute difference: `0.3398207`
- Pearson correlation: `0.9921136`

Finding: **model-specification mismatch**, not automatically an implementation bug. The high correlation of the latent linear quantity with true ITE does not remove the probability-scale nonlinearity or the large absolute discrepancy.

## 13. Limitations

- Validation uses a synthetic logistic DGP, not real customer behavior.
- Only treatment values `0, 10, 20` were observed; 25 and 30 are extrapolations.
- LinearDML assumes a linear continuous treatment effect and linear outcome structure around the nuisance residuals.
- DoWhy identification uses a linear regression estimator, which is also misspecified for the logistic DGP.
- Confidence intervals measure estimator uncertainty under the fitted model; they do not correct model misspecification.
- Multi-seed variability is substantial, especially for ITE correlation and ATE error.

## 14. Final Verdict

- **SOFTWARE IMPLEMENTATION CORRECTNESS: PASS for the executed paths.** The production run completed, source/runtime leakage checks passed, confidence-service behavior passed, DoWhy identification/refutation passed, and the canonical backend suite passed 218/218 tests.
- **CAUSAL ESTIMATION QUALITY: FAIL / NOT VALIDATED.** Baseline ATE relative error was 95.74%, ITE correlation was 0.2504, and multi-seed accuracy was unstable.
- **CONFIDENCE SCORE CORRECTNESS: PASS for implementation behavior.** The score uses the selected customer/discount ITE and CI, is bounded, responds correctly to uncertainty/refutation/zero-discount cases, and uses EconML-centered intervals as implemented.
- **MODEL-SPECIFICATION LIMITATION: CONFIRMED.** The nonlinear synthetic ground truth and linear continuous-dose `LinearDML` assumption are materially different.

**Overall: the software paths are operational, but the causal model is not validated for accurate treatment-effect estimation.**

Artifacts: `artifacts/definitive_validation/`

