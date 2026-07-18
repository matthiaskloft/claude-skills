---
name: keras-ops
user_invocable: true
description: >
  Use when writing or modifying code that performs tensor math in BayesFlow
  extensions — loss functions, custom Keras layers, network forward passes,
  or approximator overrides. Triggers on: tensor operations, keras.ops,
  backend agnostic, loss function, custom layer, stop_gradient,
  convert_to_tensor, network layer, compute_metrics.
---

# Keras 3 Backend-Agnostic Tensor Math

## Golden Rule

ALL tensor math MUST use `keras.ops.*`. Never use raw `torch.*`, `jax.*`,
or `numpy` on Keras tensors. The BayesFlow ecosystem targets Keras 3
multi-backend (PyTorch, JAX, TensorFlow).

```python
import keras

# CORRECT
x = keras.ops.sum(tensor, axis=-1)
y = keras.ops.exp(tensor)
z = keras.ops.where(mask, a, b)

# WRONG — breaks on non-PyTorch backends
x = torch.sum(tensor, dim=-1)
y = np.exp(tensor)  # numpy on a Keras tensor
```

## Boundary Crossing: numpy <-> Keras

When passing numpy arrays into Keras compute paths:
```python
# Convert numpy to Keras tensor at the boundary
tensor = keras.ops.convert_to_tensor(numpy_array)
```

When extracting scalars for Python-level logic:
```python
# Use float() only for Python scalars, not tensor ops
scalar = float(keras.ops.mean(tensor))  # OK for logging
```

## Backend-Specific Code Guards

Only for truly backend-specific features (gradient checkpointing, CUDA cache):

```python
if keras.backend.backend() == "torch":
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
```

Never put backend-specific code in the main compute path.

Detached sampling and chunked log-prob (memory-saving patterns that build on
`stop_gradient`/`concatenate`) live in the `bayesflow-memory` skill — see
Strategies 4 and 5 there.

## Pattern: STE (Straight-Through Estimator)

Differentiable hard indicator for calibration loss:
```python
def ste_indicator(x):
    hard = keras.ops.cast(x > 0, dtype=x.dtype)
    # Forward: hard indicator. Backward: identity gradient.
    return x + keras.ops.stop_gradient(hard - x)
```

## Common Mistakes

- Using `torch.sum()` or `np.sum()` on Keras tensors — breaks JAX/TF backends
- Forgetting `stop_gradient()` on sampling paths — doubles activation memory
- Using `.item()` on Keras tensors — not supported; use `float()` for scalars
- Using `.float()` or `.to(dtype)` — use `keras.ops.cast(x, "float32")`
- `keras.ops.shape()` returns a tuple, not a tensor — no gradient flows through it
- Mixing numpy and Keras ops in one expression — convert at boundaries instead
