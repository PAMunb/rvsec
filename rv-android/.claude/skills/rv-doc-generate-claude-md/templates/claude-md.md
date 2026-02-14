# [Module Name]

## Overview

[1–2 paragraphs: what this module does, its role in rv-android, primary use cases.
Include the module's layer: core infrastructure, service, orchestration, or tool.]

## Architecture

### Directory Structure

```
src/[package]/
├── domain/        # Domain models and types
├── services/      # Business logic
├── ...
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| [ClassName] | `src/[package]/[file].py` | [one-line description] |

### Patterns

[Design patterns in use: factory, strategy, observer, component-based, etc.
For each pattern, name it and state where it's implemented.]

## Key Files

| File | Purpose |
|------|---------|
| `src/[package]/[main].py` | [Entry point / main class] |
| `src/[package]/[config].py` | [Configuration models] |

## Entry Points

[How to invoke this module:]

```bash
# CLI (if applicable)
poetry run [command] [args]
```

```python
# Programmatic
from [package] import [MainClass]
instance = MainClass(config)
result = instance.run()
```

## Dependencies

### Depends On

- **rv-android-core**: [what it uses — ErrorHandler, domain models, constants]
- **[other module]**: [what it uses]

### Depended On By

- **[module]**: [what it uses from this module]

## Configuration

| Variable / Setting | Purpose | Default | Required |
|-------------------|---------|---------|----------|
| `ENV_VAR` | [what it controls] | [default] | Yes/No |

## Development

### Commands

```bash
# Install (from repo root)
poetry install

# Run tests
cd modules/[module-name]
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/ -v

# Run specific test
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/test_[file].py -v -k "test_name"
```

### Testing

| Category | Path | Purpose | Speed |
|----------|------|---------|-------|
| unit | `tests/unit/` | Isolated tests | Fast |
| integration | `tests/integration/` | Cross-module tests | Medium |

## Key Patterns

[Patterns specific to this module that a developer or LLM needs to understand
to work with the code effectively. Include pattern name, file location, and
brief explanation of how it works in this module.]
