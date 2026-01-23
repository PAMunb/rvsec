---
name: rv-refactor-constants
description: Extract magic values to named constants. Use when improving code readability, centralizing configuration, or preparing for configuration changes.
argument-hint: [file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Extract Constants: $ARGUMENTS

## Steps

1. **Read the file** at $ARGUMENTS

2. **Identify magic values**:
   - Numeric literals (timeouts, limits, thresholds)
   - String literals (paths, URLs, messages)
   - Repeated values
   - Configuration-like values

3. **Categorize constants**:
   - Module-level (this file only)
   - Package-level (shared in package)
   - Project-level (shared across modules)

4. **Create constants**:
   - Use SCREAMING_SNAKE_CASE
   - Add type hints
   - Add docstrings for non-obvious values

5. **Replace magic values** with constants

6. **Verify** no behavior change

## Constant Locations

```
# Module-level (top of file)
TIMEOUT_SECONDS = 30

# Package-level (constants.py in package)
# package/constants.py
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Project-level (for rv-agent)
# rv_agent/constants.py
```

## Common Magic Values to Extract

| Type | Example | Constant Name |
|------|---------|---------------|
| Timeout | `30` | `TIMEOUT_SECONDS` |
| Retry count | `3` | `MAX_RETRIES` |
| Threshold | `0.7` | `LLM_RATIO_THRESHOLD` |
| Path | `"/tmp/logs"` | `LOG_DIRECTORY` |
| URL | `"http://..."` | `API_ENDPOINT` |
| Size limit | `1000` | `MAX_BUFFER_SIZE` |

## Output Format

```
## Constants Extraction: [filename]

### Magic Values Found
| Value | Occurrences | Context |
|-------|-------------|---------|
| 30 | 3 | timeout parameter |
| 0.7 | 2 | LLM ratio |

### Constants Created

```python
# Module constants
TIMEOUT_SECONDS: int = 30
"""Default timeout for operations in seconds."""

LLM_RATIO: float = 0.7
"""Ratio of LLM vs algorithm decisions in multimode."""
```

### Replacements Made
| File | Line | Before | After |
|------|------|--------|-------|
| file.py | 50 | `timeout=30` | `timeout=TIMEOUT_SECONDS` |

### Verification
- Tests: [pass/fail]
- Behavior: unchanged
```

## Guidelines

- Don't extract one-time literals that are self-explanatory
- Group related constants together
- Use type hints for clarity
- Add docstrings for non-obvious values
- Consider if value should be configurable (env var, config file)
