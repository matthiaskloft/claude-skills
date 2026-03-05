---
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

## Common Operations Reference

| Operation | keras.ops | NOT this |
|-----------|-----------|----------|
| Sum | `keras.ops.sum(x, axis=)` | `torch.sum()`, `np.sum()` |
| Mean | `keras.ops.mean(x, axis=)` | `x.mean()` |
| Exp/Log | `keras.ops.exp(x)` / `keras.ops.log(x)` | `torch.exp()` |
| Reshape | `keras.ops.reshape(x, shape)` | `x.view()`, `x.reshape()` |
| Concat | `keras.ops.concatenate([a, b], axis=)` | `torch.cat()` |
| Expand | `keras.ops.expand_dims(x, axis=)` | `x.unsqueeze()` |
| Sort | `keras.ops.sort(x, axis=)` | `torch.sort()` |
| Where | `keras.ops.where(cond, x, y)` | `torch.where()` |
| Cast | `keras.ops.cast(x, "float32")` | `x.float()`, `float(x)` |
| Stop grad | `keras.ops.stop_gradient(x)` | `x.detach()`, `torch.no_grad()` |
| Linspace | `keras.ops.linspace(0, 1, n)` | `torch.linspace()` |
| ReLU | `keras.ops.relu(x)` | `torch.relu()` |
| Shape | `keras.ops.shape(x)` | `x.shape` (ok for static) |

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

## Pattern: Detached Sampling

Cut gradients on sampling paths to save memory (calibration loss pattern):
```python
# Sample from inference network but DON'T backprop through sampling
samples = keras.ops.stop_gradient(
    self.inference_network.sample(n_samples, conditions)
)
# Only backprop through log_prob evaluation
log_probs = self.inference_network.log_prob(samples, conditions)
```

## Pattern: Chunked Log-Prob

Process large posterior sample sets in memory-bounded chunks:
```python
chunk_size = self.log_prob_chunk_size or n_samples
log_probs_list = []
for i in range(0, n_samples, chunk_size):
    chunk = samples[:, i:i+chunk_size]
    lp = self.inference_network.log_prob(chunk, conditions)
    log_probs_list.append(lp)
log_probs = keras.ops.concatenate(log_probs_list, axis=1)
```

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
