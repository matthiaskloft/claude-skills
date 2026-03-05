---
description: >
  Use when creating, modifying, or debugging BayesFlow adapters — the data
  preprocessing pipelines that transform simulator output into the schema
  expected by summary and inference networks. Triggers on: create adapter,
  adapter pipeline, data preprocessing, transforms, standardization,
  inference_variables, summary_variables, inference_conditions, prior_moments,
  set_keys, adapter factory.
---

# BayesFlow Adapter Patterns

## Three Schema Slots

BayesFlow adapters map simulator output dicts into three named slots:

| Slot | Purpose | Consumed by |
|------|---------|-------------|
| `inference_variables` | Parameters to infer (target) | Inference network |
| `summary_variables` | Observed data | Summary network |
| `inference_conditions` | Context / meta-parameters | Inference network (as conditions) |

## Pipeline Order

Build the adapter in this order — transform BEFORE standardize:

```python
adapter = bf.adapters.Adapter()

# 1. Type conversion
adapter.to_array()
adapter.convert_dtype("float64", "float32")

# 2. Cross-key transforms (e.g., reparameterization)
adapter.add_transform(MyReparamTransform())  # runs LAST on inverse

# 3. Per-key transforms (log, one-hot, expand_dims)
adapter.expand_dims("param", axis=-1)
adapter.add_transform(FilterTransform(include="param", transform_constructor=LogTransform))

# 4. Standardize (AFTER transforms — standardize the transformed distribution)
adapter.standardize("param", mean=np.float32(mean), std=np.float32(std))

# 5. Concatenate and rename into schema slots
adapter.concatenate(["param_a", "param_b"], into="inference_variables")
adapter.rename("data", "summary_variables")
adapter.concatenate(["n_obs", "context"], into="inference_conditions")

# 6. Drop unused keys
adapter.keep(["inference_variables", "summary_variables", "inference_conditions"])
```

## Standardization: Prior Moments, Not Empirical

Use analytical prior moments for standardization — not batch statistics:

```python
from bayesflow_irt.priors import prior_moments

# Computes E[f(X)] and Std[f(X)] analytically from the prior specification
mean, std = prior_moments(prior_spec, "param_name", transform=np.log)
adapter.standardize("param", mean=np.float32(mean), std=np.float32(std))
```

**Why**: Empirical moments shift across batches (especially with variable-size
data), causing train/validation distribution shift. Prior moments are
deterministic and constant.

## Custom Transforms

### Elementwise (per-key)

Subclass `ElementwiseTransform` for transforms on single keys:

```python
from bayesflow.adapters.transforms import ElementwiseTransform

class LogTransform(ElementwiseTransform):
    def forward(self, data: np.ndarray, **kwargs) -> np.ndarray:
        return np.log(data)

    def inverse(self, data: np.ndarray, **kwargs) -> np.ndarray:
        return np.exp(data)

    def get_config(self) -> dict:
        return {}
```

Apply via `FilterTransform`:
```python
adapter.add_transform(FilterTransform(include="a", transform_constructor=LogTransform))
```

### Cross-key (reparameterization)

Subclass `Transform` for transforms that read/write multiple dict keys:

```python
from bayesflow.adapters.transforms import Transform

class LoadingReparam(Transform):
    def forward(self, data: dict, **kwargs) -> dict:
        data = dict(data)  # don't mutate input
        data["d"] = -(data["a"] * data["b"])
        del data["b"]
        return data

    def inverse(self, data: dict, **kwargs) -> dict:
        data = dict(data)
        data["b"] = -(data["d"] / data["a"])
        del data["d"]
        return data
```

**Ordering**: Cross-key transforms added FIRST in forward run LAST during
inversion — so they see original-scale parameters on the inverse path.

## Broadcast Specs

For set-level parameters that need broadcasting:

```python
# If param has shape (B, I) but needs (B, I, 1) to concatenate with (B, I, K)
adapter.expand_dims("param", axis=-1)
```

## AdapterSpec Pattern (declarative)

For HPO-compatible adapters, use the declarative `AdapterSpec` from bayesflow-hpo:

```python
spec = AdapterSpec(
    set_keys={"responses": "summary_variables"},
    param_keys={"a": {}, "b": {}},
    context_keys={"n_items": {}, "n_persons": {}},
    standardization={"a": (mean_a, std_a), "b": (mean_b, std_b)},
    broadcast_specs={"a": {"axis": -1}},
)
adapter = create_adapter(spec)
```

## Common Mistakes

- **Wrong pipeline order**: standardizing before transform means you standardize
  the wrong distribution (e.g., standardizing `a` then taking `log(a)`)
- **Missing inference_conditions**: context-dependent models silently ignore
  experimental design if conditions aren't passed through
- **Forgetting expand_dims**: concatenating `(B, I)` with `(B, I, K)` fails —
  add `axis=-1` first
- **Empirical standardization**: using `adapter.standardize("x")` without
  explicit mean/std triggers warm-up from training batches — unreliable with
  variable-size data
- **Mutating input dict**: always `data = dict(data)` in custom transforms
