# File Analysis Reference

Consolidated reference for single-file qualitative analysis. Contains the 8 analysis dimensions, code smell catalog, and health scoring.

---

## 8 Analysis Dimensions (priority order)

### 1. Structure
What the file contains: imports (stdlib → third-party → internal), classes, functions, constants, file length.

### 2. Responsibilities
Single Responsibility assessment. Can you describe the file's purpose in one sentence? How many distinct responsibilities?
- 1–2 responsibilities = OK. 3+ = splitting opportunity.

### 3. Dependencies
What the file imports and what depends on it.
- \> 10 internal imports = high coupling. > 5 third-party imports = broad external surface.
- Check for circular dependency risk, import-time side effects.

### 4. Complexity
Function-level metrics: CC, nesting depth, function length, parameter count.
- For precise metrics, defer to `/rv-analyze-file-complexity` (radon).

### 5. Error Handling
try/except quality: specific exceptions, proper propagation, cleanup patterns (`with`, `finally`).
- Red flags: bare `except:`, `except: pass`, generic error messages, no cleanup for resources.

### 6. API Surface
Public interface: functions, classes, constants, `__all__`, docstrings, type annotations.
- \> 15 public symbols = broad API, consider splitting. 0% docstrings = documentation debt.

### 7. Configuration
Magic values, environment reads, default values, configuration attributes.
- \> 3 magic values = extract to constants. `os.environ.get` without default = fragile.

### 8. Testing
Testability: pure functions (easy) vs side-effect functions (need mocks), external dependencies, state management.

---

## Health Score

| Score | Criteria |
|-------|----------|
| A (Healthy) | 0–1 issues, well-structured |
| B (Good) | 2–3 minor issues, no critical |
| C (Needs Attention) | 4–5 issues or 1 critical |
| D (Needs Refactoring) | 6+ issues or 2+ critical |
| F (Critical) | Must refactor before extending |

---

## Code Smell Catalog

### Bloaters
| Smell | Heuristic | Severity |
|-------|-----------|----------|
| Long Method | > 30 lines or CC > 10 | High |
| Large Class | > 300 lines or > 15 methods | High |
| Long Parameter List | > 5 parameters | Medium |
| Primitive Obsession | Same validation repeated for str/int | Medium |
| Data Clumps | Same 3+ variables grouped in multiple places | Medium |

### OO Abusers
| Smell | Heuristic | Severity |
|-------|-----------|----------|
| Switch Statements | isinstance chain or string dispatch 3+ places | Medium |
| Refused Bequest | Subclass overrides to do nothing/raise | Medium |
| Temporary Field | Attribute only used in some methods | Low |

### Change Preventers
| Smell | Heuristic | Severity |
|-------|-----------|----------|
| Divergent Change | File changed for unrelated reasons | High |
| Shotgun Surgery | Single change requires 5+ edits | High |

### Dispensables
| Smell | Heuristic | Severity |
|-------|-----------|----------|
| Dead Code | Functions/variables never referenced | Medium |
| Duplicate Code | Same logic in 2+ locations | High |
| Speculative Generality | Abstract with 1 implementor | Medium |

### Couplers
| Smell | Heuristic | Severity |
|-------|-----------|----------|
| Feature Envy | Method uses another object's data more than its own | Medium |
| Inappropriate Intimacy | Accesses private members of another class | High |
| Message Chains | `a.b().c().d()` 3+ levels | Medium |

### Python-Specific
| Smell | Heuristic | Severity |
|-------|-----------|----------|
| Mutable Default Argument | `def f(x=[])` | High |
| Bare Except | `except:` without type | High |
| Global State Mutation | Modifies module-level variables | Medium |
| Star Import | `from X import *` | Medium |
| Mutable Class Variable | `class C: items = []` | High |
| Nested Comprehension | 2+ levels | Medium |
