---
name: rv-test-add
description: >-
  Add a single test file for an existing function or class. Use for quick test additions to existing code.
  Do NOT use for: implementing new features with tests, bug fixes requiring regression tests, or full TDD workflow.
  Use /rv-tdd for implementing features with strict RED-GREEN-REFACTOR cycles.
argument-hint: [file-path] [function-or-class-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Add Tests: $ARGUMENTS

## TDD Workflow Integration

This skill follows **Test-Driven Development** principles from superpowers:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor while keeping tests green

## MCP Integration

- **context7**: Fetch pytest docs if needed (`/pytest-dev/pytest`)
- **sequential-thinking**: Plan test cases systematically

## Test Type Decision Tree

Use this to determine the appropriate test category:

```
START: Write test for [target]
  │
  ├─ Is it a mathematical/structural property?
  │    YES → tests/property/ (Hypothesis PBT)
  │    NO → continue
  │
  ├─ Does it compare complex output against saved baseline?
  │    YES → tests/snapshot/
  │    NO → continue
  │
  ├─ Does it require device/LLM server?
  │    YES → tests/online/
  │    NO → continue
  │
  ├─ Does it measure performance/latency?
  │    YES → tests/performance/
  │    NO → continue
  │
  ├─ Is it reproducing a fixed bug?
  │    YES → tests/regression/
  │    NO → continue
  │
  ├─ Does it test multiple components together?
  │    YES → tests/integration/
  │    NO → continue
  │
  ├─ Is it a complete end-to-end workflow?
  │    YES → tests/system/
  │    NO → continue
  │
  ├─ Is it a quick sanity check?
  │    YES → tests/smoke/
  │    NO → continue
  │
  └─ Default (isolated function/class test)
       → tests/unit/
```

## Steps

1. **Parse arguments**:
   - File path containing code to test
   - Optional: specific function or class name

2. **Analyze the code**:
   ```
   Invoke /rv-analyze-file [file-path]
   ```
   The skill will identify:
   - Function/class purpose and structure
   - Input parameters and types
   - Return values
   - Dependencies and imports

   Additionally, manually identify:
   - Edge cases and error conditions

3. **Plan test cases** using sequential-thinking:
   - Happy path scenarios
   - Edge cases (empty, null, boundary values)
   - Error cases (invalid input, exceptions)
   - Integration points (mocked dependencies)

4. **Determine test location** (use decision tree above):
   - Unit tests: `tests/unit/` - isolated, mocked
   - Integration tests: `tests/integration/` - multiple components
   - Property tests: `tests/property/` - Hypothesis PBT
   - Regression tests: `tests/regression/` - bug prevention
   - Snapshot tests: `tests/snapshot/` - baseline comparison
   - Smoke tests: `tests/smoke/` - quick sanity
   - Online tests: `tests/online/` - requires device/LLM
   - Performance tests: `tests/performance/` - latency/throughput

5. **Create test file**:
   - Follow naming: `test_<source_file>.py`
   - Use pytest fixtures
   - Include docstrings

6. **Write test cases**:
   - One assertion per test when possible
   - Descriptive test names
   - Mock external dependencies

7. **Verify test fails** (RED phase):
   ```
   Invoke /rv-test-run $MODULE tests/[category]/test_$FILE.py
   ```

   Confirm test fails with expected error. If test passes immediately,
   it's not testing the right thing - revise the test.

## Test Template

```python
"""Tests for [module.component]."""

import pytest
from unittest.mock import Mock, patch

from package.module import TargetClass, target_function


class TestTargetClass:
    """Tests for TargetClass."""

    @pytest.fixture
    def instance(self):
        """Create test instance."""
        return TargetClass()

    def test_method_happy_path(self, instance):
        """Test method with valid input."""
        result = instance.method(valid_input)
        assert result == expected

    def test_method_edge_case(self, instance):
        """Test method with edge case."""
        result = instance.method(edge_input)
        assert result == expected

    def test_method_raises_on_invalid(self, instance):
        """Test method raises on invalid input."""
        with pytest.raises(ValueError):
            instance.method(invalid_input)


def test_target_function():
    """Test standalone function."""
    result = target_function(input)
    assert result == expected
```

## Output Format

```
## Tests Created: [target]

### Test File
- **Path**: tests/unit/test_[name].py
- **Tests**: X test cases

### Test Cases
1. `test_happy_path` - Normal operation
2. `test_edge_case` - Edge case handling
3. `test_error_handling` - Error cases

### Run Command
```bash
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/test_[name].py -v
```

### Test Results
- Passed: X
- Failed: Y (with details if any)
```

## Guidelines

- Test behavior, not implementation
- Use descriptive test names that explain the scenario
- Mock external dependencies (LLM, device, network)
- Use fixtures for common setup
- Keep tests fast and isolated
