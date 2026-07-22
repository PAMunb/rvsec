# Test Design Techniques

Systematic test design techniques for creating effective tests. Use to ensure comprehensive test case selection.

## How to Use

1. Identify the unit under test (function, method, or class)
2. Apply techniques in order: Equivalence Partitioning → Boundary Value → Decision Table → State Transition → Error Guessing
3. For each technique, generate specific test cases
4. Name tests following the convention: `test_<unit>_<scenario>_<expected>`

---

## Technique 1: Equivalence Partitioning

Divide the input domain into classes where all values in a class are expected to produce equivalent behavior. Test one representative from each class.

### Valid Partitions

| Partition Type | Example | Test Case |
|---------------|---------|-----------|
| Normal input | `process_timeout(60)` | Typical value within range |
| Boundary-adjacent | `process_timeout(1)` | Just inside valid range |
| Typical usage | `process_timeout(300)` | Most common real-world value |

### Invalid Partitions

| Partition Type | Example | Expected Behavior |
|---------------|---------|------------------|
| Empty/None | `process_timeout(None)` | TypeError or ValueError |
| Wrong type | `process_timeout("sixty")` | TypeError |
| Out of range (low) | `process_timeout(-1)` | ValueError |
| Out of range (high) | `process_timeout(999999)` | ValueError or clamped |
| Zero | `process_timeout(0)` | Edge case — define expected behavior |

### Application to Collections

| Input | Partitions |
|-------|-----------|
| List | Empty `[]`, single `[x]`, multiple `[x, y, z]`, duplicates `[x, x]` |
| String | Empty `""`, single char `"a"`, normal `"hello"`, very long |
| Dict | Empty `{}`, single key, many keys, nested |

## Technique 2: Boundary Value Analysis

Test at the exact boundaries of each equivalence partition. Bugs cluster at boundaries.

### Numeric Boundaries

For a range [min, max]:
- `min - 1` (invalid, just below)
- `min` (valid, lower boundary)
- `min + 1` (valid, just above lower)
- Nominal (typical middle value)
- `max - 1` (valid, just below upper)
- `max` (valid, upper boundary)
- `max + 1` (invalid, just above)

### String Boundaries

| Boundary | Test Value |
|----------|-----------|
| Empty | `""` |
| Single character | `"a"` |
| Maximum length | `"a" * max_len` |
| Maximum + 1 | `"a" * (max_len + 1)` |

### Collection Boundaries

| Boundary | Test Value |
|----------|-----------|
| Empty | `[]` |
| Single element | `[x]` |
| Two elements | `[x, y]` (tests iteration) |
| Maximum size | `[x] * max_size` |

## Technique 3: Decision Table Testing

For functions with multiple conditions that interact, create a decision table.

### Structure

| Condition 1 | Condition 2 | Condition 3 | → Action |
|------------|------------|------------|----------|
| True | True | True | Action A |
| True | True | False | Action B |
| True | False | * | Action C |
| False | * | * | Action D |

`*` = don't care (any value produces same result).

### When to Use

- Function has 2+ boolean conditions
- Conditions interact (different combinations produce different results)
- Business logic with complex rules

### Simplification

- Collapse rows where a condition doesn't matter (use `*`)
- For n conditions, maximum 2^n rows; typically many can be collapsed

## Technique 4: State Transition Testing

For stateful components where behavior depends on current state.

### State Diagram Elements

1. **States**: Identify all possible states
2. **Transitions**: Map valid state changes with triggers
3. **Guards**: Conditions that must be true for transition
4. **Actions**: Side effects of transitions

### Test Coverage Levels

| Level | Coverage | Test Count |
|-------|----------|-----------|
| All states | Visit every state at least once | = number of states |
| All transitions | Exercise every valid transition | = number of transitions |
| Invalid transitions | Attempt transitions that should fail | = states × events − valid transitions |

### rv-agent Example

```
States: IDLE → PARSING → DECIDING → EXECUTING → LEARNING → IDLE
Valid: IDLE→PARSING, PARSING→DECIDING, DECIDING→EXECUTING, EXECUTING→LEARNING
Invalid: IDLE→EXECUTING, LEARNING→PARSING (skip states)
```

## Technique 5: Error Guessing

Based on experience and common Python pitfalls. Always include these cases.

| Category | Test Cases |
|----------|-----------|
| None arguments | Pass `None` for each parameter |
| Empty collections | Empty list, dict, set, string |
| Concurrency | Simultaneous calls if the code may be multi-threaded |
| Resource exhaustion | Very large inputs, deep recursion |
| Unicode | Non-ASCII characters in strings |
| Path separators | Windows vs Unix paths if applicable |
| Timezone | Datetime operations across timezones |
| Float precision | `0.1 + 0.2 != 0.3` |

## Test Naming Convention

```
test_<unit>_<scenario>_<expected>
```

| Part | Description | Example |
|------|-------------|---------|
| unit | Function or class being tested | `parse_action` |
| scenario | Input condition or state | `with_empty_string` |
| expected | Expected outcome | `returns_none` |

Full example: `test_parse_action_with_empty_string_returns_none`

## Test Structure: Arrange-Act-Assert

```python
def test_process_timeout_with_valid_value_returns_config():
    # Arrange
    timeout = 60

    # Act
    result = process_timeout(timeout)

    # Assert
    assert result.timeout == 60
```

**One assertion per test** (conceptually). Multiple `assert` statements are OK if they verify the same logical outcome.

## pytest-Specific Patterns

| Pattern | When to Use |
|---------|------------|
| `@pytest.mark.parametrize` | Testing multiple input/output pairs from equivalence partitioning |
| `@pytest.fixture` | Shared setup across tests in a file |
| `conftest.py` fixtures | Shared setup across test directories |
| `@pytest.mark.slow` | Tests that take > 1 second |
| `@pytest.mark.integration` | Tests that require external resources |
| `tmp_path` fixture | Tests that create temporary files |
| `monkeypatch` fixture | Replacing environment variables, module attributes |
