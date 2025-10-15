# Contributing to EmberGuide

Thank you for your interest in contributing to EmberGuide! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Code Style & Conventions](#code-style--conventions)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)
- [Adding New Features](#adding-new-features)

---

## Code of Conduct

This project is a research and public-service tool. All contributors are expected to:
- Be respectful and constructive in discussions
- Follow responsible disclosure for security issues
- Respect data provider licenses (NASA, ECMWF, USGS, Copernicus)
- Never imply the tool is suitable for tactical/life-safety decisions

---

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please:
1. Check the [existing issues](https://github.com/yourusername/ember-guide/issues)
2. Verify you're using the latest version
3. Test with the offline evaluation (`make eval`) to isolate data vs code issues

**Bug reports should include:**
- Python version and OS
- Minimal reproduction steps
- Expected vs actual behavior
- Relevant log output or error messages
- If data-related: timestamps and region

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
- Check [Discussions](https://github.com/yourusername/ember-guide/discussions) first
- Clearly describe the use case
- Consider whether it aligns with the research/communication scope (not tactical operations)
- Suggest how it would be evaluated (metrics, test cases)

### Contributing Code

We welcome:
- Bug fixes
- Documentation improvements
- New tests or test fixtures
- Performance optimizations
- ML module improvements (with evaluation results)
- New data sources (with proper attribution)

---

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- (Optional) NASA Earthdata and Copernicus CDS accounts for live data

### Initial Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/ember-guide.git
cd ember-guide

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (including dev tools)
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Verify setup with offline evaluation
make eval
```

### Development Tools

We use:
- **ruff**: Linting and import sorting
- **black**: Code formatting
- **mypy**: Type checking
- **pytest**: Testing
- **pre-commit**: Git hooks for consistency

---

## Code Style & Conventions

### Python Style

- **Python 3.11+** with type hints for all functions
- **Black** formatting (line length 100)
- **Ruff** linting (configured in `pyproject.toml`)
- **Mypy** strict mode for type checking

```python
# Good: Type hints, small pure functions
def compute_rh(temp_c: float, dewpoint_c: float) -> float:
    """
    Compute relative humidity from temperature and dew point.
    
    Args:
        temp_c: Temperature in Celsius
        dewpoint_c: Dew point in Celsius
        
    Returns:
        Relative humidity (0–100%)
    """
    # ... implementation
    return rh
```

### Configuration

- **No hardcoded paths**: Use `configs/*.yml` and environment variables
- **Respect `.cursorignore`**: Never commit `.env*` files or credentials
- **Pin random seeds**: All stochastic operations must be reproducible

### Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: Prefix with `_` (e.g., `_internal_helper`)

### Documentation

- **Docstrings**: Google style for all public functions/classes
- **Type hints**: Required for function signatures
- **Inline comments**: Explain *why*, not *what*
- **README updates**: If you add a new module, update the relevant README

---

## Testing Requirements

### Test Structure

```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Multi-component tests
├── fixtures/          # Golden test data
│   ├── input/
│   └── expected/
└── conftest.py        # Shared fixtures
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/unit/test_spread.py

# With coverage
pytest --cov=src --cov-report=html

# Fast only (skip slow integration tests)
pytest -m "not slow"
```

### Writing Tests

- **Use pytest fixtures** for shared setup
- **Golden fixtures** for raster/tile outputs (store small representative samples)
- **Deterministic tests**: Pin seeds, use fixed timestamps
- **Test edge cases**: Empty inputs, missing data, boundary conditions

```python
import pytest
from src.spread import compute_spread_risk

def test_spread_risk_zero_wind():
    """Spread risk should be minimal with zero wind and flat terrain."""
    risk = compute_spread_risk(wind_speed=0.0, slope=0.0, rh=50.0)
    assert risk < 0.1

@pytest.mark.parametrize("wind_speed,expected_min", [
    (5.0, 0.3),
    (10.0, 0.5),
    (20.0, 0.7),
])
def test_spread_risk_increases_with_wind(wind_speed, expected_min):
    """Higher wind should increase spread risk."""
    risk = compute_spread_risk(wind_speed=wind_speed, slope=0.0, rh=50.0)
    assert risk >= expected_min
```

### Determinism & Reproducibility

All tests must pass with fixed random seeds:

```python
import numpy as np
np.random.seed(42)  # Or use pytest fixtures
```

Golden fixtures for raster outputs:
- Store small (e.g., 100×100) representative samples
- Use checksums to verify exact reproduction
- Document the generation process in `tests/fixtures/README.md`

---

## Pull Request Process

### Before Submitting

1. **Run all checks locally:**
   ```bash
   make lint    # ruff + black check
   make typecheck  # mypy
   make test    # pytest
   ```

2. **Update documentation:**
   - Docstrings for new functions
   - README if adding new features
   - CHANGELOG.md (if applicable)

3. **Add tests:**
   - Unit tests for new functions
   - Integration tests for new features
   - Golden fixtures if changing raster outputs

4. **Check determinism:**
   - Run tests multiple times to ensure consistency
   - Verify `make eval` produces identical results

### PR Checklist

- [ ] Code follows style guidelines (black, ruff, mypy)
- [ ] All tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated (docstrings, READMEs)
- [ ] No hardcoded paths or credentials
- [ ] Deterministic (fixed seeds for stochastic code)
- [ ] Commit messages are clear and descriptive

### PR Description Template

```markdown
## Summary
Brief description of changes.

## Motivation
Why is this change needed? What problem does it solve?

## Changes
- Bullet list of key changes
- Link to related issues (#123)

## Testing
- How was this tested?
- Any new test cases added?

## Screenshots (if UI changes)

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### Review Process

1. Automated checks (lint, type, test) must pass
2. At least one maintainer review required
3. Address feedback and push updates
4. Maintainer will merge when approved

---

## Project Structure

```
ember-guide/
├── configs/          # YAML configs (active fires, model params)
├── src/
│   ├── ingest/       # Data fetching (FIRMS, ERA5, SRTM)
│   ├── prep/         # Grid alignment, clustering
│   ├── spread/       # Baseline spread model
│   ├── calibration/  # ML calibration module
│   ├── tiles/        # GeoTIFF → PNG tiles
│   └── utils/        # Shared utilities
├── api/              # FastAPI backend
├── ui/               # Streamlit frontend
├── ml/               # ML modules (denoiser, downscaler)
│   ├── models/       # Trained models
│   └── training/     # Training scripts
├── pipeline/         # Orchestration scripts
├── data/             # Data directory (gitignored except structure)
│   ├── raw/
│   ├── interim/
│   └── products/
├── eval/             # Evaluation framework
│   └── snapshot/     # Fixed historical test cases
├── tests/            # Test suite
└── docs/             # Additional documentation
```

---

## Adding New Features

### Adding a Pipeline Step

1. Implement in `src/<module>/`
2. Add configuration to `configs/*.yml`
3. Update `pipeline/run.py` orchestration
4. Add unit tests in `tests/unit/`
5. Add integration test with golden fixture
6. Update `pipeline/README.md`

### Adding an API Endpoint

1. Define schema in `api/contracts.py`
2. Implement endpoint in `api/routes/`
3. Add OpenAPI documentation
4. Add endpoint test in `tests/api/`
5. Update `api/README.md`

### Adding an ML Module

1. Implement in `ml/<module_name>/`
2. Create `MODEL_CARD.md` with:
   - Architecture
   - Training data splits (by region/year)
   - Evaluation metrics
   - Limitations
3. Add toggle flag in config
4. Ensure deterministic training (fixed seed)
5. Add tests in `tests/ml/`
6. Update `ml/README.md`

### Adding a Data Source

1. Implement fetcher in `src/ingest/`
2. Document license and attribution in `docs/DATA_SOURCES.md`
3. Add to UI footer attribution
4. Add tests with mock data
5. Update `data/README.md`

---

## Determinism & Guardrails

EmberGuide is a research tool. Code must be:

### Auditable
- Fixed random seeds for all stochastic operations
- Versioned configs and model artifacts
- Logs should record exact code/config/data versions

### Deterministic
- Same inputs → same outputs (bit-for-bit when possible)
- Use `seed` parameters for Monte Carlo sampling
- Record perturbation parameters in metadata

### Responsible
- Never imply tactical/operational use in code comments or docs
- Always include disclaimer in UI and API responses
- Respect data provider licenses (see `docs/DATA_SOURCES.md`)

---

## Questions?

- **General questions**: [GitHub Discussions](https://github.com/yourusername/ember-guide/discussions)
- **Bug reports**: [GitHub Issues](https://github.com/yourusername/ember-guide/issues)
- **Security issues**: Email maintainer directly (see README)

Thank you for contributing to EmberGuide! 🔥🗺️

