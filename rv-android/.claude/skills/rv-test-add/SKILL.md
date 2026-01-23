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

## Steps

1. **Parse arguments**:
   - File path containing code to test
   - Optional: specific function or class name

2. **Analyze the code**:
   - Understand function/class purpose
   - Identify input parameters and types
   - Identify return values
   - Find edge cases and error conditions

3. **Plan test cases** using sequential-thinking:
   - Happy path scenarios
   - Edge cases (empty, null, boundary values)
   - Error cases (invalid input, exceptions)
   - Integration points (mocked dependencies)

4. **Determine test location**:
   - Unit tests: `tests/unit/`
   - Integration tests: `tests/integration/`
   - Mirror source structure

5. **Create test file**:
   - Follow naming: `test_<source_file>.py`
   - Use pytest fixtures
   - Include docstrings

6. **Write test cases**:
   - One assertion per test when possible
   - Descriptive test names
   - Mock external dependencies

7. **Run tests** to verify:
   ```bash
   cd modules/$MODULE
   PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/test_$FILE.py -v
   ```

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
