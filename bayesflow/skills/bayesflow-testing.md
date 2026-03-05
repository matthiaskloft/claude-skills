---
description: >
  Use when writing, modifying, or debugging tests for BayesFlow extension
  packages. Triggers on: write tests, add test, test pattern, conftest, pytest,
  test coverage, unit test, integration test, test file, test suite.
---

# Testing Patterns for BayesFlow Extensions

## CRITICAL: conftest.py Setup

The Keras backend MUST be set before any bayesflow or keras import. Place this
in `tests/conftest.py`:

```python
import os
os.environ["KERAS_BACKEND"] = "torch"  # MUST be before any import

import pytest
# Now safe to import bayesflow/keras
```

**Why**: Keras 3 reads `KERAS_BACKEND` once at first import. If bayesflow or
keras is imported before the env var is set, it defaults to TensorFlow, and
switching backends mid-process is impossible.

## Test Structure

Mirror the `src/` layout:
```
tests/
├── conftest.py              # KERAS_BACKEND setup + shared fixtures
├── test_simulators.py       # Simulator shape/output tests
├── test_adapters.py         # Adapter pipeline tests
├── test_networks.py         # Network forward-pass shape tests
└── test_models/
    └── test_mymodel.py      # Config roundtrip + integration tests
```

## Shape Testing (Simulators)

Verify `simulator.sample()` returns correct keys and shapes:

```python
def test_simulator_output_shapes():
    rng = np.random.default_rng(42)
    sim = make_my_simulator(prior_spec=..., rng=rng)
    batch_size = 8
    output = sim.sample((batch_size,))

    assert isinstance(output, dict)
    assert "params" in output
    assert "data" in output
    assert output["params"].shape[0] == batch_size
    assert output["data"].dtype == np.float32
```

## Config Roundtrip Tests

Verify serialization for all config dataclasses:

```python
def test_config_roundtrip():
    config = MyConfig(lr=1e-3, depth=4)
    restored = MyConfig.from_dict(config.to_dict())
    assert config == restored

def test_config_independence():
    c1 = MyConfig()
    c2 = MyConfig()
    c1.lr = 0.1
    assert c2.lr != 0.1  # No shared mutable state
```

## Mock-Based BayesFlow Testing

For testing approximator overrides (e.g., calibration loss) without real
training, mock the inference network:

```python
from unittest.mock import MagicMock
import keras

def make_mock_inference_network(param_dim=2, n_samples=50):
    mock = MagicMock()
    mock.sample.return_value = keras.ops.zeros((8, n_samples, param_dim))
    mock.log_prob.return_value = keras.ops.zeros((8,))
    return mock

def make_mock_summary_network():
    mock = MagicMock()
    mock.return_value = keras.ops.zeros((8, 16))  # (batch, summary_dim)
    return mock
```

## Invariance / Equivariance Testing (IRT pattern)

For architectures with symmetry properties:

```python
def test_person_invariance(summary_net):
    """Permuting persons should not change per-item output."""
    x = np.random.randn(2, 10, 5).astype(np.float32)  # (B, P, I)
    perm = np.random.permutation(10)
    x_perm = x[:, perm, :]

    y = summary_net(keras.ops.convert_to_tensor(x))
    y_perm = summary_net(keras.ops.convert_to_tensor(x_perm))
    np.testing.assert_allclose(y, y_perm, atol=1e-5)

def test_item_equivariance(summary_net):
    """Permuting items should permute the output correspondingly."""
    x = np.random.randn(2, 10, 5).astype(np.float32)
    perm = np.random.permutation(5)
    x_perm = x[:, :, perm]

    y = summary_net(keras.ops.convert_to_tensor(x))
    y_perm = summary_net(keras.ops.convert_to_tensor(x_perm))
    np.testing.assert_allclose(y[:, perm, :], y_perm, atol=1e-5)
```

## Adapter Pipeline Tests

Verify the full transform chain produces correct output schema:

```python
def test_adapter_output_schema():
    sim = make_my_simulator(...)
    adapter = make_my_adapter(sim)
    raw = sim.sample((4,))
    processed = adapter(raw)

    assert "inference_variables" in processed
    assert "summary_variables" in processed
    assert processed["inference_variables"].shape[0] == 4
```

## Deterministic RNG

Always seed for reproducibility:
```python
rng = np.random.default_rng(42)
```

Never use `np.random.seed()` (global state) or unseeded generators in tests.

## CI Matrix

Standard GitHub Actions setup for BayesFlow packages:
- Python: 3.11, 3.12, 3.13
- Backend: PyTorch (`KERAS_BACKEND=torch`)
- Trigger: push/PR to main

## Common Mistakes

- Importing bayesflow before setting KERAS_BACKEND → entire test suite uses wrong backend
- Non-deterministic tests due to unseeded RNG → flaky CI
- Testing with real training runs instead of mocks → slow tests (minutes vs seconds)
- Missing shape assertions → off-by-one in batch/feature dimensions goes undetected
- Using `assert x == y` for float arrays → use `np.testing.assert_allclose(x, y, atol=)`
