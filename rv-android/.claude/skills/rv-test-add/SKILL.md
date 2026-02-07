---
name: rv-test-add
description: >-
  Add a single test file for an existing function or class. Use for quick test additions to existing code.
  Do NOT use for: implementing new features with tests, bug fixes requiring regression tests, or full TDD workflow.
  Use /rv-tdd for implementing features with strict RED-GREEN-REFACTOR cycles.
argument-hint: [file-path] [function-or-class-name]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Skill
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

## Guiding Principles

When designing and writing tests, you must adhere to the following fundamental software engineering principles.

### Core Objectives of Testing
A test is a process of executing a program with the intent of finding an error. A good test case is one that has a high probability of finding an as-yet-undiscovered error. A successful test is one that uncovers an as-yet-undiscovered error.

### Test Design Principles

Your test suite should be designed, not just randomly written. Justify your test case choices based on these design principles.

1.  **Traceability to Requirements**: All test cases should be traceable to customer requirements. This ensures the system is validated against what it is supposed to do.

2.  **Black-Box Testing (Behavioral)**: Focus on the functional requirements of the software. You treat the component as a "black box" and test its behavior from the outside.
    *   **Equivalence Partitioning**: Divide the input domain into classes of data from which test cases are derived. This avoids redundant testing. For a given input range, create partitions for invalid values below, valid values within, and invalid values above the range.
    *   **Boundary Value Analysis (BVA)**: A technique that complements equivalence partitioning. Design test cases that focus on the "edges" of the input domain (e.g., min, max, just inside/outside boundaries), as this is where many errors occur.

3.  **White-Box Testing (Structural)**: Focus on the internal logic of the software.
    *   **Basis Path Testing**: A core white-box technique. Your goal is to ensure that all statements and conditions within a function have been executed at least once. This involves analyzing the code's control flow graph.

4.  **Test Independence**: Each test should be independent of others. Avoid creating tests that rely on the state or output of other tests to function.

5.  **Verifiability**: The expected outcome of a test must be clearly defined and verifiable. Assertions should be specific and unambiguous.

### Quality Attributes for Testing
- **Reliability**: Does the code perform its intended function correctly under normal conditions?
- **Robustness**: How does the code handle invalid inputs, unexpected conditions, and errors?
- **Testability**: Is the code designed in a way that facilitates testing (e.g., through modularity, low coupling, and dependency injection)?

Always justify your test design decisions based on these principles.

## Requirement for Principle-Based Justification

During the execution of this task, you must explain how your test designs and decisions align with the Guiding Principles above. When creating test cases, include a justification such as:

- "I am creating test cases based on the **Equivalence Partitioning** principle by defining these valid and invalid input classes..."
- "To adhere to **Boundary Value Analysis**, I am testing the following edge cases: ..."
- "This set of tests is designed to satisfy **Basis Path Testing** by ensuring all branches in the function are executed."
- "This test case validates the requirement [Requirement ID], ensuring **Traceability to Requirements**."

This ensures that test design is transparent and grounded in solid software engineering fundamentals.

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

2. **Analyze the code** - Use the **Skill tool**:
   ```
   Skill tool: skill="rv-analyze-file", args="[file-path]"
   ```
   The skill will identify:
   - Function/class purpose and structure
   - Input parameters and types
   - Return values
   - Dependencies and imports

   Additionally, manually identify:
   - Edge cases and error conditions

3. **Plan test cases** using test case design guidelines:

   **Partition Testing** (identify equivalence classes):
   - What are the valid input ranges? → Test middle values
   - What are the boundaries? → Test min, max, min-1, max+1
   - What inputs are invalid? → Test for proper error handling

   **Guideline-Based Testing** (common defect patterns):
   | Input Type | Test With |
   |------------|-----------|
   | Collections | Empty, single item, many items |
   | Strings | Empty, whitespace, special chars |
   | Numbers | Zero, negative, very large |
   | Objects | None/null |

   **Categories to cover**:
   - Happy path scenarios
   - Boundary values (edges of valid ranges)
   - Edge cases (empty, null, single element)
   - Error cases (invalid input, exceptions)
   - State transitions (if stateful object)

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

7. **Verify test fails** (RED phase) - Use the **Skill tool**:
   ```
   Skill tool: skill="rv-test-run", args="$MODULE tests/[category]/test_$FILE.py"
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
