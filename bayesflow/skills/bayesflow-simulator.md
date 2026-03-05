---
description: >
  Use when creating, modifying, or debugging BayesFlow 2.x simulators — data
  generating processes with prior, likelihood, and meta functions. Triggers on:
  create simulator, data generating process, prior function, likelihood function,
  simulation model, make_simulator, sampling function, generative model, DGP.
---

# BayesFlow 2.x Simulator Patterns

## Two Factory Approaches

### A) Subclass `Simulator` (variable-size data)

Use when the data dimensions vary across batches (e.g., different numbers of
items/persons per batch in IRT). Subclass `bayesflow.simulators.Simulator` and
implement `sample()`.

```python
from bayesflow.simulators import Simulator
from bayesflow.utils.decorators import allow_batch_size

class _MySimulator(Simulator):
    def __init__(self, n_obs: tuple[int, int], prior_spec):
        self._n_obs_range = (n_obs[0], n_obs[1])  # (lo, hi)
        self._sample_param = resolve_prior(prior_spec)
        self._rng = np.random.default_rng()

    @allow_batch_size
    def sample(self, batch_shape, **kwargs) -> dict[str, np.ndarray]:
        rng = self._rng
        B = int(np.prod(batch_shape))
        # Sizes drawn ONCE per batch, not per sample
        N = int(rng.integers(self._n_obs_range[0], self._n_obs_range[1] + 1))

        params = self._sample_param((B,), rng).astype(np.float32)
        data = self._generate_data(params, N, rng).astype(np.float32)

        return dict(
            params=params,
            data=data,
            n_obs=np.full((B, 1), N, dtype=np.float32),
        )
```

**Key rules:**
- `@allow_batch_size` decorator is REQUIRED — it handles batch_shape normalization
- Sizes are drawn per-batch so all samples stack cleanly (no padding/masking)
- Provide `clone_with_sizes()` method for creating validation simulators with different ranges

### B) Functional `make_simulator()` (fixed-size data)

Use when dimensions are constant or set by meta-parameters.

```python
import bayesflow as bf

def prior(shape, rng):
    return rng.normal(size=shape).astype(np.float32)

def likelihood(params, n_total, rng):
    # params from prior, n_total from meta
    data = rng.normal(loc=params, size=(*params.shape[:-1], n_total))
    return data.astype(np.float32)

def meta(shape, rng):
    n = rng.integers(50, 200, size=(*shape, 1)).astype(np.float32)
    return n

simulator = bf.simulators.make_simulator(
    prior_fn=prior,
    likelihood_fn=likelihood,
    meta_fn=meta,
)
```

## Critical Conventions

### Function signatures
- **Prior**: `(shape: tuple, rng: np.random.Generator) -> np.ndarray`
- **Likelihood**: receives prior draws + meta params + `rng`
- **Meta**: `(shape: tuple, rng: np.random.Generator) -> np.ndarray`

### RNG discipline
- ALWAYS accept `rng: np.random.Generator` — never use global `np.random`
- Store `self._rng = np.random.default_rng()` in `__init__`
- This ensures reproducibility with `np.random.default_rng(seed)`

### Output dict conventions
- Parameter keys must match adapter `inference_variables` mapping
- Data keys must match adapter `summary_variables` mapping
- Meta/context keys match adapter `inference_conditions` mapping
- ALL values must be `np.float32` — use `.astype(np.float32)`

### Config dataclasses
Group hyperparameters into frozen dataclasses for serialization:
```python
@dataclass
class PriorConfig:
    scale: float = 1.0
    df: float = 5.0
```

### Prior specification pattern
Use `PriorSpec = Prior | Callable` for flexible prior definitions:
```python
Prior("normal", loc=0, scale=1.0)       # Named distribution
Prior("lognormal", loc=0, scale=0.3)    # Lognormal
lambda shape, rng: rng.gamma(2, 1, shape)  # Custom callable
```

**Never use silent defaults for critical priors** — force explicit specification
to prevent train/validation prior mismatches.

## Common Mistakes

- Forgetting `@allow_batch_size` decorator → batch_shape errors
- Drawing sizes per-sample instead of per-batch → ragged arrays that can't stack
- Using `np.random.normal()` instead of `rng.normal()` → non-reproducible
- Returning `float64` instead of `float32` → dtype mismatch in adapter/network
- Missing context keys (n_obs, n_items) → adapter can't pass design info to inference net
