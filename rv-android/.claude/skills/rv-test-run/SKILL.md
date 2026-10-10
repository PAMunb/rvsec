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
   - Run from project root using uv workspace
   - Select pytest options based on scope

3. **Execute tests**

4. **Report results**

## Test Commands by Module

All commands run from the project root (uv workspace handles PYTHONPATH) and follow the CI
contract in `../.github/workflows/ci.yml` (the rvsec repository root, one level above rv-android): every pytest call carries `--import-mode=importlib -o "addopts="`
and targets **one module at a time**. Without `--import-mode=importlib`, the `conftest.py` files of
different modules collide during collection; `-o "addopts="` discards the per-module `addopts`
(several modules set `--cov=src` there, a path that does not exist when pytest runs from the root).

```bash
# rv-agent (most common)
uv run pytest modules/rv-agent/tests/unit/ --import-mode=importlib -o "addopts=" -v

# rv-android-core
uv run pytest modules/rv-android-core/tests/ --import-mode=importlib -o "addopts=" -v

# rv-platform
uv run pytest modules/rv-platform/tests/ --import-mode=importlib -o "addopts=" -v

# Generic pattern
uv run pytest modules/$MODULE/tests/ --import-mode=importlib -o "addopts=" -v

# All modules: one pytest process per module, as CI does (never `uv run pytest modules/`)
failed=0
for module in modules/*/; do
  [ -d "$module/tests" ] || continue
  echo "=== Testing $(basename "$module") ==="
  uv run pytest "$module/tests" \
    -m "not (slow or online or sglang or performance or dataset)" \
    --import-mode=importlib --tb=short -q -rs -o "addopts=" || failed=1
done
echo "failed=$failed"

# Cross-cutting gates at the repository root (CI runs them in a separate step)
uv run pytest tests/ -m "not (slow or online or sglang or performance or dataset)" \
  --import-mode=importlib --tb=short -q -rs -o "addopts="
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
uv run pytest modules/$MODULE/tests/unit/ --import-mode=importlib -o "addopts=" -v

# Property-based tests (Hypothesis)
uv run pytest modules/$MODULE/tests/property/ --import-mode=importlib -o "addopts=" -v --hypothesis-show-statistics

# Snapshot tests
uv run pytest modules/$MODULE/tests/snapshot/ --import-mode=importlib -o "addopts=" -v
# Update baselines (requires pytest-snapshot, which is not installed in the workspace)
uv run pytest modules/$MODULE/tests/snapshot/ --import-mode=importlib -o "addopts=" -v --snapshot-update

# Regression tests only
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" -m regression -v

# All fast tests (the CI marker filter)
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" -m "not (slow or online or sglang or performance or dataset)" -v

# Run by multiple markers
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" -m "regression or smoke" -v
```

## Common Options

Each option is appended to the module command
`uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts="`.

```bash
# Verbose
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" -v

# Stop on first failure
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" -x

# Run specific marker
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" -m "not slow"

# With coverage (explicit, because -o "addopts=" drops the modules' --cov=src)
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" --cov=modules/$MODULE/src --cov-report=html

# Parallel (requires pytest-xdist, which is not installed in the workspace)
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" -n auto

# Show print output
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" -s

# Run last failed
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" --lf

# Run with Hypothesis statistics
uv run pytest modules/$MODULE/tests --import-mode=importlib -o "addopts=" --hypothesis-show-statistics
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
3. Run specific test with `uv run pytest modules/$MODULE/tests/path/to/test.py::test_name --import-mode=importlib -o "addopts=" -v`
4. Use `--pdb` to drop into debugger on failure
