# Complexity Thresholds

Reference table of complexity metrics and their acceptable ranges for risk classification.

## How to Use

1. Compute metrics for the target code (function, class, or file level)
2. Compare each metric against the thresholds below
3. Flag anything in the "High" or "Very High" range as a refactoring candidate
4. Report findings with the metric name, actual value, and threshold category

---

## Cyclomatic Complexity

Measures independent paths through a function. Each `if`, `elif`, `for`, `while`, `and`, `or`, `except`, and ternary adds one.

| Range | Category | Action |
|-------|----------|--------|
| 1–10 | Low | Acceptable |
| 11–20 | Moderate | Review; consider splitting |
| 21–50 | High | Must refactor before merge |
| 50+ | Very High | Refactor immediately; function is untestable |

## Cognitive Complexity (Sonar Model)

Measures how hard a function is to understand. Penalizes nesting, break in linear flow, and recursion.

| Range | Category | Action |
|-------|----------|--------|
| < 15 | OK | No action needed |
| 15–25 | Warning | Simplify if feasible |
| > 25 | Must simplify | Extract methods or reduce nesting |

Key contributors: nested conditionals (+nesting increment), `break`/`continue` to labels, recursion, boolean sequences mixing `and`/`or`.

## Halstead Metrics

Derived from operator and operand counts. Useful for comparing alternative implementations.

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Volume (V) | N × log₂(η) | Total information content; compare relative values |
| Difficulty (D) | (η₁/2) × (N₂/η₂) | Error proneness; higher = more bug-prone |
| Effort (E) | D × V | Estimated mental effort; use for relative comparison |

Where N = total operators + operands, η = unique operators + operands.

## Maintainability Index

Composite metric combining Halstead Volume, Cyclomatic Complexity, and LOC.

| Range | Category | Action |
|-------|----------|--------|
| > 85 | Good | Maintainable |
| 65–85 | Moderate | Monitor; refactor on next change |
| < 65 | Poor | Prioritize refactoring |

Formula: MI = 171 − 5.2 × ln(V) − 0.23 × CC − 16.2 × ln(LOC)

## Lines of Code (LOC) Thresholds

| Scope | Threshold | Action if Exceeded |
|-------|-----------|-------------------|
| Function/method | 50 lines | Extract sub-functions |
| Class | 500 lines | Split responsibilities |
| File/module | 1000 lines | Split into submodules |

Blank lines and comments are excluded from these counts. Measure logical lines only.

## Nesting Depth

Maximum levels of indentation within a function.

| Depth | Category | Action |
|-------|----------|--------|
| 1–2 | OK | No action |
| 3 | Acceptable | Review readability |
| 4 | Warning | Use guard clauses or extract method |
| 5+ | Must refactor | Flatten with early returns, extract, or decompose |

## Parameter Count

Number of parameters in a function signature.

| Count | Category | Action |
|-------|----------|--------|
| 0–3 | OK | No action |
| 4–5 | Acceptable | Consider parameter object if related |
| 6+ | Must refactor | Introduce parameter object or split function |

Exclude `self`/`cls` from count. `*args`/`**kwargs` count as 1 each.

## Coupling Metrics

| Metric | Definition | Healthy Range |
|--------|-----------|---------------|
| Afferent coupling (Ca) | Modules that depend on this one | High Ca = stable abstraction needed |
| Efferent coupling (Ce) | Modules this one depends on | Ce > 7 = fragile, consider facade |
| Instability (I) | Ce / (Ca + Ce) | 0 = maximally stable, 1 = maximally unstable |

Stable modules (low I) should be abstract. Unstable modules (high I) should be concrete.

## Python-Specific Complexity Signals

| Signal | Threshold | Action |
|--------|-----------|--------|
| Nested comprehension | 2+ levels | Rewrite as explicit loop or extract helper |
| Decorator chain | 4+ decorators | Consolidate or document ordering |
| Star imports | Any `from X import *` | Replace with explicit imports |
| Dynamic attribute access | > 3 `getattr`/`setattr` in one function | Consider dictionary or class |
| Exception handler breadth | Bare `except:` or `except Exception` | Narrow to specific exceptions |
