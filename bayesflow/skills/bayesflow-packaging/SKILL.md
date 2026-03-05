---
description: >
  Use when adding new modules, exports, or dependencies to BayesFlow extension
  packages — managing __all__, pyproject.toml, optional extras, CI configuration,
  or package versioning. Triggers on: new module, add export, __all__,
  pyproject.toml, optional dependency, version, release, CI, package structure.
---

# BayesFlow Package Structure and API Management

## src-Layout Convention

All BayesFlow extension packages use the `src/` layout:

```
my_package/
├── src/my_package/
│   ├── __init__.py      # Public API exports + __all__
│   ├── module_a.py
│   └── module_b.py
├── tests/
│   ├── conftest.py
│   └── test_module_a.py
├── pyproject.toml
└── CLAUDE.md
```

In `pyproject.toml`:
```toml
[tool.setuptools.packages.find]
where = ["src"]
```

## `__all__` Management

**Every public symbol MUST appear in both the import AND `__all__`** in
`__init__.py`. When adding a new public function or class:

```python
# 1. Add the import
from .module_a import MyNewClass, my_new_function

# 2. Add to __all__
__all__ = [
    # ... existing exports ...
    "MyNewClass",
    "my_new_function",
]
```

**Omitting from `__all__` makes the symbol invisible** to `from package import *`
and IDE auto-completion for users.

## Version Detection Pattern

Standard version detection with editable-install fallback:

```python
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("my-package")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback for raw checkout
```

## pyproject.toml Template

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "my-package"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "bayesflow>=2.0",
    "keras>=3.9",
    "numpy",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "ruff", "mypy"]
notebooks = ["jupyter", "ipykernel", "notebook"]
calibration = ["bayesflow-calibration-loss>=0.1.0"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
strict = true
```

## Optional Dependency Extras

Pattern for features that require additional packages:

```toml
[project.optional-dependencies]
calibration = ["bayesflow-calibration-loss>=0.1.0"]
```

In code, use guarded imports:
```python
try:
    from bayesflow_calibration_loss import CalibrationMixin
    _HAS_CALIBRATION = True
except ImportError:
    _HAS_CALIBRATION = False

class CalibratedApproximator:
    def __init__(self, ...):
        if not _HAS_CALIBRATION:
            raise ImportError(
                "Install calibration extra: pip install my-package[calibration]"
            )
```

## CI Matrix

Standard GitHub Actions for BayesFlow packages:

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]

env:
  KERAS_BACKEND: torch

steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
  - run: pip install -e ".[dev]"
  - run: pytest tests/ -v --cov
  - run: ruff check src/
```

## Common Mistakes

- **Adding a public function but forgetting `__all__`** — invisible to users
  and IDEs
- **Wrong `target-version` in ruff** — allows syntax not supported by minimum
  Python version (e.g., `match` statement with target py311 but min py310)
- **Missing optional dependency group** — `import` fails for users who install
  the extra without the package declaring the dependency
- **Using `find_packages()` without `where`** — picks up `tests/` as a package
- **Hardcoding version** — use `importlib.metadata` pattern for editable installs
