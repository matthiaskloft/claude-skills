---
description: >
  Use when implementing or running SBC (simulation-based calibration)
  validation, calibration diagnostics, coverage analysis, or quality
  threshold checks for BayesFlow models. Triggers on: SBC, simulation-based
  calibration, validation, coverage, calibration error, C2ST, condition grid,
  quality thresholds, diagnostic plots, validate model, check calibration.
---

# SBC Validation and Calibration Diagnostics

## Core Idea

Simulation-Based Calibration (SBC) validates neural posterior estimators by
checking that credible intervals achieve their nominal coverage. A well-
calibrated model's HPD ranks should be uniformly distributed.

## Condition Grid Validation

Test the model across its full design space, not just training conditions:

```python
from bayesflow_hpo import make_condition_grid

# Factorial grid of experimental conditions
conditions = make_condition_grid(
    n_total=[50, 100, 200, 500],
    effect_size=[0.1, 0.3, 0.5, 0.8],
    allocation_ratio=[0.3, 0.5, 0.7],
)
# Returns list of condition dicts, one per grid point (4 * 4 * 3 = 48)
```

For strict validation (IRT / RCT pattern):
```python
from bayesflow_rct import create_strict_validation_grid

# 144-condition grid for thorough parametric coverage testing
conditions = create_strict_validation_grid(
    n_values=[50, 100, 200, 500],
    effect_values=[0.1, 0.3, 0.5],
    alloc_values=[0.3, 0.5, 0.7],
    prior_df_values=[3, 10, 30, 100],
)
```

## Validation Dataset (Pre-compute and Cache)

Generate validation data ONCE and reuse across HPO trials:

```python
from bayesflow_hpo import ValidationDataset, generate_validation_dataset

# Generate and cache
val_data = generate_validation_dataset(
    simulator=simulator,
    adapter=adapter,
    conditions=conditions,
    n_sims_per_condition=500,
    n_post_draws=500,
    seed=42,
)

# Save / load for cross-session reuse
save_validation_dataset(val_data, "data/validation/")
val_data = load_validation_dataset("data/validation/")
```

For IRT variable-size data:
```python
from bayesflow_irt import build_multicondition_val_dataset

val_dataset = build_multicondition_val_dataset(
    simulator, adapter,
    num_conditions=50,         # Different (I, P) configs
    samples_per_condition=4,   # Samples per config
)
# Use as: fit_kwargs=dict(validation_data=val_dataset)
```

## Coverage Metrics

| Metric | What it measures | Good value |
|--------|------------------|------------|
| Calibration error | Deviation of rank distribution from uniform | < 0.02 |
| C2ST deviation | Classifier two-sample test (ranks vs uniform) | < 0.52 |
| Coverage error @ 90% | |observed coverage - 0.90| | < 0.05 |
| Coverage error @ 95% | |observed coverage - 0.95| | < 0.03 |

## Validation Pipeline

```python
from bayesflow_hpo import run_validation_pipeline, ValidationResult

result: ValidationResult = run_validation_pipeline(
    workflow=workflow,
    validation_data=val_data,
    metrics=["calibration_error", "c2st", "coverage_90", "coverage_95"],
)

# Per-condition and aggregate metrics
print(result.aggregate_metrics)
print(result.per_condition_metrics)
```

## Threshold-Based Quality Gates

Define pass/fail criteria for automated training:

```python
from bayesflow_rct import QualityThresholds, check_thresholds

thresholds = QualityThresholds(
    max_cal_error=0.02,
    max_c2st_deviation=0.52,
    max_coverage_error=0.05,
    max_iterations=5,
)

passed, scores = check_thresholds(metrics, thresholds)
```

### Train-Until-Threshold Loop

```python
from bayesflow_rct import train_until_threshold

result = train_until_threshold(
    build_workflow_fn=lambda hp: build_workflow(hp),
    train_fn=lambda wf: wf.fit(simulator, ...),
    validate_fn=lambda wf: run_validation(wf, val_data),
    hyperparams=best_trial.params,
    thresholds=thresholds,
)
```

## Calibration Floor

Finite samples create an irreducible minimum calibration error:

```python
from bayesflow_calibration_loss import estimate_calibration_floor

floor = estimate_calibration_floor(
    batch_size=32,       # calibration batch size
    n_samples=500,       # posterior samples per data point
    mode=0.0,            # 0.0=conservativeness, 1.0=full calibration
)
# ~0.005 — don't set target_calibration_error below this
```

## Diagnostic Plotting

```python
from bayesflow_rct import plot_diagnostic_dashboard

plot_diagnostic_dashboard(
    estimates=posterior_samples,
    targets=true_params,
    param_key="effect_size",
)
# Produces 2x2 grid: scatter, residual, rank histogram, coverage
```

## Common Mistakes

- **Validating only at training conditions** — overfits to specific designs;
  use a condition grid spanning the full design space
- **Too few posterior draws** — coverage estimates are noisy with < 200 draws;
  use 500+ for reliable metrics
- **Ignoring calibration floor** — setting `target_calibration_error` below
  the finite-sample floor causes the Lagrangian to push gamma too high
- **Not caching validation data** — regenerating 500 sims × 48 conditions per
  HPO trial wastes enormous compute; generate once and reuse
- **Single-point validation** — a single (N, effect_size) doesn't represent
  model performance across the design space
