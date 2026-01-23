---
name: rv-test-run
description: >-
  Run tests for a module or file. Use when verifying changes, checking test status, or debugging test failures.
  Do NOT use for: writing tests (use /rv-test-add or /rv-tdd), full verification (use /rv-verify).
argument-hint: [module-name or test-path]
context: fork
agent: general-purpose
allowed-tools: Read, Bash
---

# Run Tests: $ARGUMENTS

## Steps

1. **Parse scope** from $ARGUMENTS:
   - Module name (e.g., "rv-agent"): run all tests
   - Test file path: run specific file
   - Test function (file::function): run specific test

2. **Build test command**:
   - Set PYTHONPATH for dependencies
   - Select pytest options based on scope

3. **Execute tests**

4. **Report results**

## Test Commands by Module

```bash
# rv-agent (most common)
cd modules/rv-agent
PYTHONPATH=../rv-android-core/src:../rv-screen-parser/src:src poetry run pytest tests/unit/ -v

# rv-android-core
cd modules/rv-android-core
poetry run pytest tests/ -v

# rv-platform
cd modules/rv-platform
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v

# Generic pattern
cd modules/$MODULE
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v
```

## Test Categories (rv-agent)

| Category | Path | Purpose | Marker | Speed |
|----------|------|---------|--------|-------|
| unit | tests/unit/ | Isolated tests, mocked | - | Fast |
| integration | tests/integration/ | Component tests | - | Medium |
| smoke | tests/smoke/ | Sanity checks | smoke | Fast |
| online | tests/online/ | Device/LLM required | online | Slow |
| performance | tests/performance/ | Latency tests | performance | Variable |
| regression | tests/regression/ | Bug prevention | regression | Medium |
| property | tests/property/ | Hypothesis PBT | hypothesis | Medium |
| snapshot | tests/snapshot/ | Baseline comparison | snapshot | Fast |
| system | tests/system/ | End-to-end complete | system | Slow |

## Run by Category

```bash
# Unit tests only (fast, no external deps)
pytest tests/unit/ -v

# Property-based tests (Hypothesis)
pytest tests/property/ -v --hypothesis-show-statistics

# Snapshot tests
pytest tests/snapshot/ -v
pytest tests/snapshot/ -v --snapshot-update  # Update baselines

# Regression tests only
pytest -m regression -v

# All fast tests (exclude slow/online)
pytest -m "not slow and not online" -v

# Run by multiple markers
pytest -m "regression or smoke" -v
```

## Common Options

```bash
# Verbose
pytest -v

# Stop on first failure
pytest -x

# Run specific marker
pytest -m "not slow"

# With coverage
pytest --cov=src --cov-report=html

# Parallel
pytest -n auto

# Show print output
pytest -s

# Run last failed
pytest --lf

# Run with Hypothesis statistics
pytest --hypothesis-show-statistics
```

## Output Format

```
## Test Results: [scope]

### Summary
- **Total**: X tests
- **Passed**: Y
- **Failed**: Z
- **Skipped**: W
- **Duration**: N seconds

### Failed Tests (if any)
| Test | Error |
|------|-------|
| test_name | [error message] |

### Next Steps
- [Recommendations based on results]
```

## Debugging Failed Tests

If tests fail:
1. Run with `-v` for verbose output
2. Run with `-s` to see print statements
3. Run specific test with `pytest path/to/test.py::test_name -v`
4. Use `--pdb` to drop into debugger on failure
