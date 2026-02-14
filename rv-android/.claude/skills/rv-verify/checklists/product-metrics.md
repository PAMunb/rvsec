# Product Metrics

Quantitative measures for assessing software quality. Use metrics to identify anomalous components that may have quality problems.

---

## Types of Metrics

### Control Metrics (Process)
- Measure the development process
- Example: defects found per phase, time to fix bugs

### Predictor Metrics (Product)
- Measure the software itself
- Help predict quality characteristics

This checklist focuses on **predictor metrics** (product metrics).

---

## Static Metrics

Collected by analyzing source code without execution.

### General Metrics

| Metric | Description | Tool | Threshold |
|--------|-------------|------|-----------|
| **Fan-in** | Number of callers of a function | custom | High = tightly coupled |
| **Fan-out** | Number of functions called | custom | High = complex control |
| **Lines of Code** | Size of component | wc, radon | File > 500 = review |
| **Cyclomatic Complexity** | Control flow complexity | radon cc | > 10 = too complex |
| **Maintainability Index** | Composite maintainability score | radon mi | < 40 = poor |
| **Identifier Length** | Average length of names | custom | Short = unclear |
| **Nesting Depth** | Maximum if/loop nesting | pylint | > 4 = refactor |

### Commands

```bash
# Cyclomatic complexity
poetry run radon cc src/ -a -s

# Maintainability index
poetry run radon mi src/ -s

# Raw metrics (LOC, comments, etc.)
poetry run radon raw src/ -s

# Halstead complexity metrics
poetry run radon hal src/
```

---

## Object-Oriented Metrics (CK Suite)

Metrics specifically designed for OO code.

| Metric | Name | Description | Interpretation |
|--------|------|-------------|----------------|
| **WMC** | Weighted Methods per Class | Sum of method complexities | High = hard to understand |
| **DIT** | Depth of Inheritance Tree | Levels in inheritance hierarchy | Deep = many classes to understand |
| **NOC** | Number of Children | Direct subclasses | High = validate base class carefully |
| **CBO** | Coupling Between Objects | Classes this class depends on | High = hard to change in isolation |
| **RFC** | Response For a Class | Methods potentially executed | High = complex, error-prone |
| **LCOM** | Lack of Cohesion in Methods | Methods without shared attributes | High = class should be split |

### Thresholds

| Metric | Good | Acceptable | Review Needed |
|--------|------|------------|---------------|
| WMC | ≤ 20 | 21-50 | > 50 |
| DIT | ≤ 3 | 4-5 | > 5 |
| NOC | ≤ 7 | 8-15 | > 15 |
| CBO | ≤ 9 | 10-14 | > 14 |
| RFC | ≤ 50 | 51-100 | > 100 |
| LCOM | ≤ 2 | 3-5 | > 5 |

### Commands

```bash
# For Python, use radon or wily
# radon provides cc (complexity) which correlates with WMC
poetry run radon cc src/ --total-average

# wily provides historical metrics
# pip install wily
wily build src/
wily report src/module.py
```

---

## Anomaly Detection Process

1. **Collect** metrics for all components
2. **Compute** mean and standard deviation
3. **Flag** components > 2 standard deviations from mean
4. **Analyze** flagged components manually

### Example Analysis

```
Component          CC    LOC    Status
──────────────────────────────────────
parser.py          8     150    OK
analyzer.py        12    280    REVIEW (CC > 10)
utils.py           3     80     OK
executor.py        25    650    ANOMALY (CC, LOC)
```

Components flagged as ANOMALY should be reviewed for:
- Possible refactoring opportunities
- Hidden bugs due to complexity
- Testing gaps (complex code needs more tests)

---

## Dynamic Metrics

Collected during program execution.

| Metric | Description | Tool |
|--------|-------------|------|
| Execution time | Time for specific operations | pytest-benchmark |
| Memory usage | Peak memory consumption | memory_profiler |
| Test coverage | % of code exercised by tests | pytest-cov |
| Failure rate | # failures per time period | logs, monitoring |

### Commands

```bash
# Test coverage
poetry run pytest --cov=src --cov-report=html

# Performance profiling
poetry run python -m cProfile -o profile.stats script.py
```

---

## Metric Relationships

Internal metrics correlate with (but don't guarantee) external quality:

```
Internal (Measurable)         External (Experienced)
─────────────────────────     ─────────────────────────
Cyclomatic Complexity    ───► Maintainability
Lines of Code            ───► Reliability (more bugs)
Depth of Inheritance     ───► Understandability
Coupling (CBO)           ───► Testability, Reusability
LCOM                     ───► Cohesion, Maintainability
Test Coverage            ───► Reliability
```

---

## Interpretation Guidelines

### High Complexity (CC > 10)
- **Risk**: Harder to test, more bugs, harder to maintain
- **Action**: Consider extracting methods, simplifying conditions

### Large Files (LOC > 500)
- **Risk**: Hard to navigate, likely contains unrelated code
- **Action**: Split into focused modules

### Deep Inheritance (DIT > 5)
- **Risk**: Changes at top affect many classes
- **Action**: Prefer composition over inheritance

### High Coupling (CBO > 14)
- **Risk**: Changes ripple to many classes
- **Action**: Introduce interfaces, reduce dependencies

### Low Cohesion (LCOM > 5)
- **Risk**: Class does too many things
- **Action**: Split into focused classes

---

## Quick Reference

```bash
# Full metrics analysis (from project root)

# Complexity
poetry run radon cc modules/$MODULE/src/ -a -s --total-average

# Maintainability
poetry run radon mi modules/$MODULE/src/ -s

# Coverage (if tests exist)
poetry run pytest modules/$MODULE/tests/ --cov=modules/$MODULE/src --cov-report=term-missing

# Security
poetry run bandit -r modules/$MODULE/src/ -f txt
```
