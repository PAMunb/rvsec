# Complexity Analysis Reference

Consolidated reference for module-scoped complexity analysis. Contains metric thresholds, refactoring indicators, and Python-specific signals.

---

## Complexity Thresholds

### Cyclomatic Complexity

Measures independent paths through a function. Each `if`, `elif`, `for`, `while`, `and`, `or`, `except`, and ternary adds one.

| Range | Category | Action |
|-------|----------|--------|
| 1–10 | Low | Acceptable |
| 11–20 | Moderate | Review; consider splitting |
| 21–50 | High | Must refactor before merge |
| 50+ | Very High | Refactor immediately; function is untestable |

### Cognitive Complexity (Sonar Model)

Measures how hard a function is to understand. Penalizes nesting, break in linear flow, and recursion.

| Range | Category | Action |
|-------|----------|--------|
| < 15 | OK | No action needed |
| 15–25 | Warning | Simplify if feasible |
| > 25 | Must simplify | Extract methods or reduce nesting |

### Halstead Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Volume (V) | N × log₂(η) | Total information content; compare relative values |
| Difficulty (D) | (η₁/2) × (N₂/η₂) | Error proneness; higher = more bug-prone |
| Effort (E) | D × V | Estimated mental effort; use for relative comparison |

### Maintainability Index

| Range | Category | Action |
|-------|----------|--------|
| > 85 | Good | Maintainable |
| 65–85 | Moderate | Monitor; refactor on next change |
| < 65 | Poor | Prioritize refactoring |

Formula: MI = 171 − 5.2 × ln(V) − 0.23 × CC − 16.2 × ln(LOC)

### Size Thresholds

| Scope | Threshold | Action if Exceeded |
|-------|-----------|-------------------|
| Function/method | 50 lines | Extract sub-functions |
| Class | 500 lines | Split responsibilities |
| File/module | 1000 lines | Split into submodules |

### Nesting Depth

| Depth | Category | Action |
|-------|----------|--------|
| 1–2 | OK | No action |
| 3 | Acceptable | Review readability |
| 4 | Warning | Use guard clauses or extract method |
| 5+ | Must refactor | Flatten with early returns, extract, or decompose |

### Parameter Count

| Count | Category | Action |
|-------|----------|--------|
| 0–3 | OK | No action |
| 4–5 | Acceptable | Consider parameter object if related |
| 6+ | Must refactor | Introduce parameter object or split function |

Exclude `self`/`cls` from count.

### Coupling Metrics

| Metric | Definition | Healthy Range |
|--------|-----------|---------------|
| Afferent coupling (Ca) | Modules that depend on this one | High Ca = stable abstraction needed |
| Efferent coupling (Ce) | Modules this one depends on | Ce > 7 = fragile, consider facade |
| Instability (I) | Ce / (Ca + Ce) | 0 = maximally stable, 1 = maximally unstable |

### Python-Specific Complexity Signals

| Signal | Threshold | Action |
|--------|-----------|--------|
| Nested comprehension | 2+ levels | Rewrite as explicit loop or extract helper |
| Decorator chain | 4+ decorators | Consolidate or document ordering |
| Star imports | Any `from X import *` | Replace with explicit imports |
| Dynamic attribute access | > 3 `getattr`/`setattr` in one function | Consider dictionary or class |
| Exception handler breadth | Bare `except:` or `except Exception` | Narrow to specific exceptions |

---

## Refactoring Indicators

### Smell-to-Refactoring Mapping

| Code Smell | Detection Heuristic | Refactoring Technique | Expected Reduction |
|-----------|---------------------|----------------------|-------------------|
| God Class | > 7 responsibilities, > 20 methods, > 15 fields | Extract Class | CC −30%, LOC −40% |
| Long Method | > 30 lines, > 3 indent levels, > 4 params | Extract Method | CC −50%, nesting −2 |
| Feature Envy | Method uses more data from another class than its own | Move Method | Coupling −1 per move |
| Data Clumps | Same 3+ params appear together in multiple signatures | Extract Class / Introduce Parameter Object | Param count −60% |
| Divergent Change | Class changed for unrelated reasons in different commits | Extract Class by responsibility | SRP violations −100% |
| Shotgun Surgery | One logical change touches 5+ files | Move Method, Inline Class | Files touched −50% |
| Primitive Obsession | Using str/int/dict where a domain object fits | Replace Primitive with Value Object | Type safety +100% |
| Switch Statements | Repeated type-checking on same field in 3+ locations | Replace Conditional with Polymorphism | CC per function −70% |
| Speculative Generality | Abstract class with 1 subclass, unused parameters | Collapse Hierarchy, Remove Middle Man | Class count −20%, LOC −15% |

### Severity Classification

| Severity | Criteria | SLA |
|----------|----------|-----|
| Critical | CC > 50, God Class > 30 methods | Refactor before next feature |
| High | CC 21–50, Long Method > 50 lines | Refactor within current sprint |
| Medium | CC 11–20, 3+ smell instances | Refactor on next touch |
| Low | Minor smells, cosmetic | Optional improvement |
