# {MODULE_NAME}

{ONE_LINE_DESCRIPTION}

## Overview

{2-3 sentences explaining what the module does and its role in rv-android}

## Installation

```bash
# Install all rv-android modules (from project root)
uv sync
```

This module is part of the RV-Android uv workspace. All modules are installed in editable mode — source changes are reflected immediately.

## Quick Start

### Programmatic Usage

```python
from {package} import {MainClass}

# Basic usage example
config = {MainClass}Config(
    option1="value",
    option2=123
)
instance = {MainClass}(config)
result = instance.run()
```

### CLI Usage

```bash
uv run {cli-command} --option value
```

## Features

- **{Feature 1}**: Brief description
- **{Feature 2}**: Brief description
- **{Feature 3}**: Brief description

## Configuration

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `option_name` | str | `"default"` | What it does |
| `timeout` | int | `300` | Timeout in seconds |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `VAR_NAME` | What it does | Yes/No |

## Usage Examples

### Example 1: {Use Case Title}

```python
# Detailed code example with comments
```

### Example 2: {Use Case Title}

```bash
# CLI example with options
```

## Dependencies

### Internal (rv-android)

| Module | Purpose |
|--------|---------|
| rv-android-core | Foundation infrastructure |
| {other-module} | {purpose} |

### External

| Package | Purpose |
|---------|---------|
| {package-name} | {purpose} |

## Documentation

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](./CLAUDE.md) | Development reference for Claude Code |
| [Architecture](./docs/architecture.md) | Detailed architecture documentation |

## Testing

```bash
# From project root
uv run pytest modules/{module-name}/tests/ -v

# With coverage
uv run pytest modules/{module-name}/tests/ --cov=modules/{module-name}/src --cov-report=html
```

## License

Part of the rv-android project.
