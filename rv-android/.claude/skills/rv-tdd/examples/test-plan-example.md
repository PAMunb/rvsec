# Test Plan Example

This is an example of an approved test plan for implementing email validation.

---

## Test Plan

### Feature: `validate_email`
### Target: `modules/rv-agent/src/rv_agent/utils/validation.py`
### Date: 2026-01-15

---

## 1. Requirements Summary

### What We're Testing

A function to validate email addresses for use in notification settings.

### Acceptance Criteria

1. Valid emails return True
2. Invalid emails return False
3. Empty/None input handled gracefully
4. Common edge cases covered (subdomains, plus addressing)

### Input/Output Specification

| Input | Type | Valid Range | Description |
|-------|------|-------------|-------------|
| email | str | any string | Email to validate |

| Output | Type | Description |
|--------|------|-------------|
| is_valid | bool | True if valid email format |

---

## 2. Test Cases

### Unit Tests

#### Happy Path

| Test Name | Input | Expected | Description |
|-----------|-------|----------|-------------|
| `test_validate_email_simple` | "user@example.com" | True | Basic email |
| `test_validate_email_subdomain` | "user@mail.example.com" | True | With subdomain |
| `test_validate_email_plus` | "user+tag@example.com" | True | Plus addressing |

#### Edge Cases

| Test Name | Input | Expected | Description |
|-----------|-------|----------|-------------|
| `test_validate_email_empty` | "" | False | Empty string |
| `test_validate_email_none` | None | False | None input |
| `test_validate_email_long_tld` | "user@example.museum" | True | Long TLD |

#### Error Cases

| Test Name | Input | Expected | Description |
|-----------|-------|----------|-------------|
| `test_validate_email_no_at` | "userexample.com" | False | Missing @ |
| `test_validate_email_no_domain` | "user@" | False | No domain |
| `test_validate_email_spaces` | "user @example.com" | False | Has spaces |

---

## 3. Mocking Strategy

No mocking needed - pure function with no dependencies.

---

## 4. Test File Structure

### Location

```
tests/unit/utils/test_validation.py
```

### Implementation

```python
"""Tests for validation utilities."""

import pytest
from rv_agent.utils.validation import validate_email


class TestValidateEmail:
    """Tests for validate_email function."""

    # Happy path
    def test_simple_email(self):
        assert validate_email("user@example.com") is True

    def test_subdomain_email(self):
        assert validate_email("user@mail.example.com") is True

    def test_plus_addressing(self):
        assert validate_email("user+tag@example.com") is True

    # Edge cases
    def test_empty_string(self):
        assert validate_email("") is False

    def test_none_input(self):
        assert validate_email(None) is False

    # Error cases
    def test_missing_at(self):
        assert validate_email("userexample.com") is False

    def test_no_domain(self):
        assert validate_email("user@") is False

    def test_has_spaces(self):
        assert validate_email("user @example.com") is False
```

---

## 5. Approval

**Plan Status**: APPROVED

**Test Count**: 9 tests planned

**Coverage Target**: 100% of validate_email function

**User Notes**: Approved. Make sure to handle unicode emails in future iteration.
