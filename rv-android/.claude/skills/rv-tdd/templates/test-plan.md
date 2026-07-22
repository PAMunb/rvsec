# Test Plan Template

Use this template to document the test plan before writing any code.

---

## Test Plan

### Feature: `[feature or function name]`
### Target: `[file path]`
### Date: `[YYYY-MM-DD]`

---

## 1. Requirements Summary

### What We're Testing

[Brief description of the feature/function being implemented]

### Acceptance Criteria

1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]

### Input/Output Specification

| Input | Type | Valid Range | Description |
|-------|------|-------------|-------------|
| param1 | str | non-empty | Description |
| param2 | int | > 0 | Description |

| Output | Type | Description |
|--------|------|-------------|
| result | bool | True if valid |

---

## 2. Test Cases

### Unit Tests

#### Happy Path

| Test Name | Input | Expected Output | Description |
|-----------|-------|-----------------|-------------|
| `test_[feature]_valid_input` | valid data | expected result | Normal operation |
| `test_[feature]_typical_case` | typical data | expected result | Common usage |

#### Edge Cases

| Test Name | Input | Expected Output | Description |
|-----------|-------|-----------------|-------------|
| `test_[feature]_empty_input` | "" / [] / None | defined behavior | Empty handling |
| `test_[feature]_boundary_min` | min value | expected result | Lower boundary |
| `test_[feature]_boundary_max` | max value | expected result | Upper boundary |

#### Error Cases

| Test Name | Input | Expected | Description |
|-----------|-------|----------|-------------|
| `test_[feature]_invalid_type` | wrong type | TypeError | Type validation |
| `test_[feature]_invalid_value` | invalid value | ValueError | Value validation |
| `test_[feature]_none_input` | None | defined behavior | Null handling |

### Integration Tests (if needed)

| Test Name | Components | Description |
|-----------|------------|-------------|
| `test_[feature]_with_[dep]` | A + B | Integration test |

---

## 3. Mocking Strategy

### Dependencies to Mock

| Dependency | Mock Behavior | Reason |
|------------|---------------|--------|
| external_api | return fixed data | Isolation |
| database | in-memory | Speed |
| llm_client | return preset response | Determinism |

### Mock Implementation

```python
@pytest.fixture
def mock_dependency():
    with patch('module.dependency') as mock:
        mock.return_value = expected_value
        yield mock
```

---

## 4. Test File Structure

### Location

```
tests/
└── unit/
    └── test_[module].py
```

### File Template

```python
"""Tests for [module.feature]."""

import pytest
from unittest.mock import Mock, patch

from package.module import TargetClass, target_function


class TestTargetFeature:
    """Tests for [feature]."""

    @pytest.fixture
    def instance(self):
        """Create test instance."""
        return TargetClass()

    # Happy path tests
    def test_valid_input(self, instance):
        ...

    # Edge case tests
    def test_empty_input(self, instance):
        ...

    # Error case tests
    def test_invalid_type(self, instance):
        ...
```

---

## 5. Approval

**Plan Status**: PENDING / APPROVED / REJECTED

**Test Count**: X tests planned

**Coverage Target**: X% of new code

**User Notes**: [any feedback]
