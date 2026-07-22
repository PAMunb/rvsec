# Test Case Design Checklist

Guidelines for designing effective test cases based on software engineering best practices.

---

## 1. Partition Testing (Equivalence Partitioning)

Identify groups of inputs that should be processed the same way, then test representatives from each group.

### Process

1. **Identify input partitions**:
   - Valid inputs (expected to work)
   - Invalid inputs (expected to fail)
   - Boundary values (edges of valid range)

2. **Identify output partitions**:
   - Normal outputs
   - Error outputs
   - Edge case outputs

3. **Select test values**:
   - One from middle of each partition
   - Values at partition boundaries
   - Values just outside boundaries

### Example: Function accepting age (0-120)

| Partition | Values to Test | Expected |
|-----------|----------------|----------|
| Invalid (negative) | -1, -100 | Error |
| Boundary (lower) | 0, 1 | Valid |
| Valid (middle) | 25, 60 | Valid |
| Boundary (upper) | 119, 120 | Valid |
| Invalid (too high) | 121, 1000 | Error |

### Checklist

- [ ] All valid input partitions identified
- [ ] All invalid input partitions identified
- [ ] Boundary values identified for each partition
- [ ] At least one test per partition
- [ ] Boundary tests included (min, max, min-1, max+1)

---

## 2. Guideline-Based Testing

Use these guidelines to choose test cases that commonly reveal defects.

### General Guidelines

| Guideline | Test Case |
|-----------|-----------|
| Force all error messages | Input that triggers each error path |
| Test buffer/collection limits | Empty, one item, max items, overflow |
| Repeat same input | Same input multiple times consecutively |
| Force invalid outputs | Input that would cause invalid output |
| Test computation limits | Very large/small numbers, zero, negative |

### Collection/Sequence Guidelines

| Guideline | Test Case |
|-----------|-----------|
| Single element | Collection with exactly one item |
| Empty collection | Empty list/array/dict |
| Different sizes | Small (1-3), medium (10-20), large (100+) |
| First/middle/last | Access patterns for ordered collections |
| Null/None elements | Collections containing null values |

### String Guidelines

| Guideline | Test Case |
|-----------|-----------|
| Empty string | "" |
| Single character | "a" |
| Whitespace only | "   ", "\t\n" |
| Very long string | 10000+ characters |
| Special characters | Unicode, emoji, control chars |
| SQL/HTML injection | `'; DROP TABLE--`, `<script>` |

### Numeric Guidelines

| Guideline | Test Case |
|-----------|-----------|
| Zero | 0, 0.0 |
| Negative | -1, -MAX |
| Very small | 0.0001, MIN_FLOAT |
| Very large | MAX_INT, MAX_FLOAT |
| Precision | 0.1 + 0.2 (floating point) |

### Checklist

- [ ] Error message paths tested
- [ ] Empty/null inputs tested
- [ ] Boundary values tested
- [ ] Large inputs tested
- [ ] Special characters tested (if applicable)
- [ ] Zero/negative tested (if numeric)

---

## 3. State-Based Testing

For objects/systems with state, test all valid state transitions.

### Process

1. **Identify states**: List all possible states
2. **Identify transitions**: List valid state changes
3. **Test each transition**: Verify state changes correctly
4. **Test invalid transitions**: Verify rejection of invalid changes

### Example: Connection States

```
States: [Disconnected, Connecting, Connected, Error]

Transitions to test:
- Disconnected → Connecting (connect())
- Connecting → Connected (success)
- Connecting → Error (failure)
- Connected → Disconnected (disconnect())
- Error → Disconnected (reset())

Invalid transitions to test:
- Disconnected → Connected (should fail)
- Connected → Connecting (should fail)
```

### Checklist

- [ ] All states identified
- [ ] All valid transitions tested
- [ ] Invalid transitions tested (should fail gracefully)
- [ ] State preserved correctly after operations
- [ ] Initial state verified

---

## 4. Interface Testing (Component Integration)

For testing interactions between components.

### Types of Interfaces

| Type | What to Test |
|------|-------------|
| Parameter | Correct types, order, count of parameters |
| Return value | All possible return types/values |
| Exception | All exceptions that can be raised |
| Side effects | State changes, file writes, etc. |

### Guidelines

- [ ] Test with extreme parameter values
- [ ] Test with null/None parameters
- [ ] Test parameter type mismatches
- [ ] Test missing required parameters
- [ ] Test exception propagation
- [ ] Verify side effects occur correctly

### Error Classes to Test

| Error Type | How to Trigger |
|------------|----------------|
| Interface misuse | Wrong parameter types/order |
| Interface misunderstanding | Incorrect assumptions about behavior |
| Timing errors | Race conditions, async issues |

---

## 5. Test Case Template

Use this structure for each test case:

```python
def test_[behavior]_[condition]_[expected]():
    """
    Test that [behavior] when [condition] results in [expected].

    Partition: [which partition this tests]
    Guideline: [which guideline this follows]
    """
    # ARRANGE (Setup)
    input_value = ...
    expected_output = ...

    # ACT (Call)
    result = function_under_test(input_value)

    # ASSERT
    assert result == expected_output
```

### Naming Convention

```
test_<what>_<condition>_<expected>

Examples:
- test_calculate_with_zero_returns_zero
- test_parse_with_empty_string_raises_error
- test_connect_when_offline_transitions_to_connecting
```

---

## 6. Test Plan Checklist

Before writing tests, verify your plan covers:

### Coverage

- [ ] Happy path (normal operation)
- [ ] All input partitions
- [ ] All boundary values
- [ ] All error conditions
- [ ] State transitions (if stateful)
- [ ] Interface contracts (if component)

### Quality

- [ ] Each test tests ONE thing
- [ ] Test names describe behavior
- [ ] Tests are independent
- [ ] Tests are deterministic
- [ ] Tests are fast

### Risk-Based Prioritization

| Priority | Test Type | When |
|----------|-----------|------|
| HIGH | Happy path | Always |
| HIGH | Error handling | Always |
| HIGH | Boundary values | When ranges exist |
| MEDIUM | Edge cases | Complex logic |
| MEDIUM | State transitions | Stateful objects |
| LOW | Performance | After correctness |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│                  TEST CASE DESIGN                       │
├─────────────────────────────────────────────────────────┤
│ 1. PARTITION: Identify equivalence classes              │
│    → Test middle + boundaries of each                   │
│                                                         │
│ 2. GUIDELINES: Use experience-based rules               │
│    → Empty, null, zero, negative, overflow              │
│    → First, middle, last elements                       │
│    → Force all error paths                              │
│                                                         │
│ 3. STATE: Map states and transitions                    │
│    → Test all valid transitions                         │
│    → Test invalid transitions (should fail)             │
│                                                         │
│ 4. INTERFACE: Test component boundaries                 │
│    → Extreme values, nulls, wrong types                 │
│    → Exception handling                                 │
└─────────────────────────────────────────────────────────┘
```
