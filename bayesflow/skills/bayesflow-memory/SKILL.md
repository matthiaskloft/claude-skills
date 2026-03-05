---
description: >
  Use when dealing with GPU memory issues, CUDA OOM errors, training crashes,
  or optimizing memory usage in BayesFlow training. Triggers on: OOM, out of
  memory, CUDA error, memory error, batch size, gradient checkpointing, memory
  probe, memory budget, VRAM, GPU memory.
---

# GPU Memory Management for BayesFlow Training

## OOM Detection

Detect CUDA out-of-memory errors in exception chains:

```python
from bayesflow_irt import is_oom_error

def is_oom_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "out of memory" in msg or "cudaerrormemoryallocation" in msg
```

## Strategy 1: Batch-Size Backoff

Automatic retry with halved batch size on OOM:

```python
from bayesflow_irt import fit_with_oom_retry, FitResult

result: FitResult = fit_with_oom_retry(
    approximator,
    simulator,
    start_batch_size=256,
    min_batch_size=8,
    backoff_factor=2,
    fit_kwargs=dict(
        epochs=50,
        num_batches=100,
        validation_data=val_dataset,
    ),
)
print(f"Trained with batch_size={result.batch_size} in {result.attempts} attempts")
```

**Recovery order**:
1. Reduce `item_chunk_size` (if summary net supports it) — same math, less peak memory
2. Halve `batch_size` when all chunk sizes exhausted
3. Raise `RuntimeError` if below `min_batch_size`

## Strategy 2: Gradient Checkpointing

Trade compute for memory by recomputing activations during backward pass:

```python
from bayesflow_irt import set_summary_memory_config

set_summary_memory_config(
    summary_net,
    item_chunk_size=None,          # or specific int
    gradient_checkpointing=True,   # recompute activations in backward pass
)
```

**Backend guard required** — only works with PyTorch:
```python
if keras.backend.backend() == "torch":
    import torch
    # torch.utils.checkpoint.checkpoint() used internally
```

## Strategy 3: Memory Probing

Automatically find the best memory configuration before training:

```python
from bayesflow_irt import probe_memory_config, MemoryProbeReport

report: MemoryProbeReport = probe_memory_config(
    approximator,
    simulator,
    batch_size=128,
    n_items=(15, 50),          # worst-case: uses max
    n_persons=(150, 500),
    early_stop=True,           # stop at first working config
)
# Automatically sets best config on the summary network
```

Probes a grid of `(item_chunk_size, gradient_checkpointing)` combinations
using a disposable model clone (original weights untouched).

## Strategy 4: Detached Sampling (Calibration Loss)

Cut gradients through the sampling path to halve activation memory:

```python
# In CalibratedContinuousApproximator.compute_metrics():
samples = keras.ops.stop_gradient(
    self.inference_network.sample(n_samples, conditions)
)
# Gradients only flow through log_prob, not through sample()
log_probs = self.inference_network.log_prob(samples, conditions)
```

## Strategy 5: Chunked Log-Prob

Process posterior samples in memory-bounded chunks:

```python
# Instead of one massive log_prob call:
chunk_size = 100  # process 100 samples at a time
log_probs_list = []
for i in range(0, n_samples, chunk_size):
    chunk = samples[:, i:i+chunk_size]
    lp = self.inference_network.log_prob(chunk, conditions)
    log_probs_list.append(lp)
log_probs = keras.ops.concatenate(log_probs_list, axis=1)
```

## Strategy 6: Analytical Memory Estimation

Estimate VRAM before training to set HPO constraints:

```python
from bayesflow_calibration_loss import estimate_calibration_memory

vram_mb = estimate_calibration_memory(
    batch_size=64,
    n_post_samples=500,
    param_dim=2,
)

from bayesflow_hpo import estimate_peak_memory_mb, exceeds_memory_budget

peak_mb = estimate_peak_memory_mb(trial_params)
if exceeds_memory_budget(peak_mb, budget_mb=8000):
    raise optuna.TrialPruned("Exceeds memory budget")
```

## Cache Clearing

Always clear GPU cache between OOM retries:

```python
from bayesflow_irt import safe_empty_cache

import gc
gc.collect()
safe_empty_cache()  # torch.cuda.empty_cache() if available, no-op otherwise
```

## Common Mistakes

- **No OOM recovery** — training crashes and loses all progress; always use
  `fit_with_oom_retry()` or manual try/except with `is_oom_error()`
- **Gradient checkpointing on non-PyTorch** — must guard with
  `keras.backend.backend() == "torch"` check
- **Missing stop_gradient** — without it, backprop through sampling path
  stores all intermediate activations (2x memory)
- **Not clearing cache** — `gc.collect()` alone doesn't free CUDA memory;
  must also call `torch.cuda.empty_cache()`
- **Probing with live model** — always clone the model for probing to avoid
  corrupting optimizer state
