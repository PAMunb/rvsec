# Complexity Reduction Techniques

Measurable complexity reduction techniques with expected impact on metrics. Use to set concrete improvement targets.

## How to Use

1. Identify the function or method with high complexity (CC > 10 or cognitive > 15)
2. Select applicable techniques from the catalog below
3. Apply techniques in order of impact (highest reduction first)
4. Measure before/after to confirm improvement

---

## Technique Catalog

### 1. Extract Method

**What**: Move a coherent block of code into a named function.

**When**: A function does multiple things at different abstraction levels. Comments mark logical sections.

**Impact**:
- Cyclomatic: Splits CC across functions (original CC drops by extracted branches)
- Cognitive: Reduces nesting and length in the original function
- LOC: Net increase of 2–3 lines (signature + call), but each function is shorter

**Example**:
```python
# Before (CC=12)
def process(data):
    # validate
    if not data: ...
    if len(data) > MAX: ...
    # transform
    for item in data: ...
    # save
    db.insert(result)

# After (CC=4 + CC=2 + CC=6)
def process(data):
    validate(data)
    result = transform(data)
    save(result)
```

### 2. Replace Nested Conditionals with Guard Clauses

**What**: Convert nested if/else chains into early returns.

**When**: Function has 3+ levels of nesting from precondition checks.

**Impact**:
- Cyclomatic: Unchanged (same number of branches)
- Cognitive: Reduces by 1–3 levels of nesting (significant improvement)
- LOC: Slight decrease (removes else blocks)

**Example**:
```python
# Before (nesting depth 4)
def process(item):
    if item is not None:
        if item.is_valid():
            if item.has_data():
                return transform(item)
    return None

# After (nesting depth 1)
def process(item):
    if item is None:
        return None
    if not item.is_valid():
        return None
    if not item.has_data():
        return None
    return transform(item)
```

### 3. Replace Loop with Comprehension

**What**: Convert simple for-loops with append into list/dict comprehensions.

**When**: Loop body is a single expression (filter + transform).

**Impact**:
- Cyclomatic: Reduces by 1 (loop becomes expression)
- Cognitive: Reduces if the comprehension is simple; increases if nested
- LOC: Reduces by 2–4 lines

**Caution**: Nested comprehensions (2+ levels) are worse than explicit loops. Only use for single-level transformations.

### 4. Introduce Early Return

**What**: Return from a function as soon as the result is determined, instead of setting a variable and returning at the end.

**When**: Function has a result variable that is set in multiple branches.

**Impact**:
- Cyclomatic: Unchanged
- Cognitive: Reduces by eliminating the need to track the result variable
- LOC: Slight decrease

### 5. Replace Flag Arguments with Separate Methods

**What**: Split a function that behaves differently based on a boolean flag into two focused functions.

**When**: Function has `if flag:` that selects between two entirely different behaviors.

**Impact**:
- Cyclomatic: Each new function has roughly half the original CC
- Cognitive: Significant reduction (no mental branching on flag)
- LOC: Net increase of 3–5 lines (two signatures), but each function is clearer

### 6. Decompose Conditional

**What**: Extract complex boolean expressions into named variables or functions.

**When**: Condition has 3+ parts joined by `and`/`or`, or uses negation that makes intent unclear.

**Impact**:
- Cyclomatic: Unchanged
- Cognitive: Significant reduction (named condition is self-documenting)
- LOC: Increase of 1–2 lines per extracted condition

**Example**:
```python
# Before
if user.age >= 18 and user.has_license and not user.is_suspended and user.balance > 0:

# After
is_eligible = user.age >= 18 and user.has_license
is_active = not user.is_suspended and user.balance > 0
if is_eligible and is_active:
```

### 7. Consolidate Duplicate Conditional Fragments

**What**: Move identical code out of all branches of a conditional.

**When**: Same statement appears in every branch of an if/elif/else.

**Impact**:
- Cyclomatic: Unchanged
- Cognitive: Slight reduction (less code to read per branch)
- LOC: Reduces by (N-1) × duplicated lines, where N = number of branches

### 8. Replace Temp with Query

**What**: Replace a temporary variable with a method call or expression.

**When**: Variable is assigned once and used once, and the expression is readable.

**Impact**:
- Cyclomatic: Unchanged
- Cognitive: Mixed (fewer variables to track, but inline expression may be longer)
- LOC: Reduces by 1 per eliminated variable

**Caution**: Only apply when the expression is short and self-explanatory. Long expressions should keep the named variable.

---

## Impact Summary Table

| Technique | CC Reduction | Cognitive Reduction | LOC Change |
|-----------|-------------|--------------------|-----------|
| Extract Method | −30–50% per extraction | −20–40% | +2–3 net |
| Guard Clauses | 0% | −30–50% (nesting) | −5–10% |
| Comprehension | −1 per loop | Variable | −30–50% per loop |
| Early Return | 0% | −10–20% | −5% |
| Separate Methods | −40–60% per function | −40–60% | +3–5 net |
| Decompose Conditional | 0% | −20–30% | +1–2 |
| Consolidate Fragments | 0% | −5–10% | −(N-1) lines |
| Replace Temp | 0% | ±5% | −1 per temp |

## When NOT to Simplify

| Scenario | Why |
|----------|-----|
| Performance-critical inner loops | Extraction adds function call overhead |
| Already-clear 3-line patterns | Extraction creates unnecessary indirection (P1) |
| Framework requirements | Some frameworks require specific patterns (e.g., LangGraph node structure) |
| Code under active development | Wait for the design to stabilize before simplifying |
