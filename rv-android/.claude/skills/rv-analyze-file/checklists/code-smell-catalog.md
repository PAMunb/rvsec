# Code Smell Catalog

Catalog of code smells detectable at the single-file level, with severity and fix suggestions. Use as a reference during file analysis.

## How to Use

1. During file analysis, check for each smell category below
2. For each detected smell, record: name, location (line/function), severity, suggested fix
3. Python-specific smells should be checked in addition to general smells
4. Report findings sorted by severity (high first)

---

## Bloaters

Code that has grown too large to work with effectively.

| Smell | Detection Heuristic | Severity | Suggested Refactoring |
|-------|---------------------|----------|-----------------------|
| Long Method | Function > 30 lines or CC > 10 | High | Extract Method |
| Large Class | Class > 300 lines or > 15 methods | High | Extract Class |
| Long Parameter List | Function > 5 parameters | Medium | Introduce Parameter Object |
| Primitive Obsession | Same validation repeated for str/int values | Medium | Replace with Value Object |
| Data Clumps | Same 3+ variables grouped in multiple places | Medium | Extract Class / dataclass |

## Object-Orientation Abusers

Patterns that misuse or underuse OO principles.

| Smell | Detection Heuristic | Severity | Suggested Refactoring |
|-------|---------------------|----------|-----------------------|
| Switch Statements | `isinstance` chain or string-based type dispatch in 3+ places | Medium | Replace Conditional with Polymorphism |
| Refused Bequest | Subclass overrides parent methods to do nothing or raise | Medium | Replace Inheritance with Delegation |
| Temporary Field | Instance attribute only used in some methods, None otherwise | Low | Extract Class for those methods |
| Alternative Classes | Two classes with different names but same interface/purpose | Medium | Merge or extract shared interface |

## Change Preventers

Patterns that make changes unnecessarily difficult.

| Smell | Detection Heuristic | Severity | Suggested Refactoring |
|-------|---------------------|----------|-----------------------|
| Divergent Change | File changed for unrelated reasons in git history | High | Extract Class by responsibility |
| Shotgun Surgery | Single logical change requires edits to 5+ locations | High | Move Method to centralize |
| Parallel Inheritance | Adding a subclass requires adding a subclass elsewhere | Medium | Merge hierarchies |

## Dispensables

Code that could be removed without affecting functionality.

| Smell | Detection Heuristic | Severity | Suggested Refactoring |
|-------|---------------------|----------|-----------------------|
| Excessive Comments | Comments explain obvious code, or code needs comments to be understood | Low | Rename for clarity, Extract Method |
| Dead Code | Functions/variables never referenced | Medium | Remove (check false-positive-patterns first) |
| Duplicate Code | Same logic in 2+ locations within the file | High | Extract Method |
| Speculative Generality | Abstract class with 1 implementor, unused parameters | Medium | Collapse Hierarchy, Remove Parameter |
| Data Class | Class with only fields and getters, no behavior | Low | Move behavior into the class, or accept as DTO |

## Couplers

Patterns that create excessive coupling between components.

| Smell | Detection Heuristic | Severity | Suggested Refactoring |
|-------|---------------------|----------|-----------------------|
| Feature Envy | Method accesses another object's data more than its own | Medium | Move Method |
| Inappropriate Intimacy | Class accesses private/internal members of another class | High | Move Method, Extract Class |
| Message Chains | `a.b().c().d()` chains longer than 3 levels | Medium | Hide Delegate, Extract Method |
| Middle Man | Class delegates all work to another class | Low | Remove Middle Man (inline) |

## Python-Specific Smells

| Smell | Detection Heuristic | Severity | Why It Matters |
|-------|---------------------|----------|----------------|
| Mutable Default Argument | `def f(x=[]):` or `def f(x={}):` | High | Shared across calls, causes subtle bugs |
| Bare Except | `except:` without exception type | High | Catches SystemExit, KeyboardInterrupt |
| Global State Mutation | Function modifies module-level variables | Medium | Hidden side effects, hard to test |
| String Type Checking | `type(x) == str` instead of `isinstance(x, str)` | Low | Breaks inheritance |
| Nested Comprehension | 2+ levels of comprehension nesting | Medium | Unreadable, extract to loop or helper |
| Magic __methods__ Misuse | `__del__`, `__getattr__` with side effects | Medium | Unpredictable execution timing |
| Star Import | `from module import *` | Medium | Namespace pollution, unclear dependencies |
| Mutable Class Variable | `class C: items = []` shared across instances | High | Shared state between instances |
| Broad isinstance | `isinstance(x, (str, int, float, list, dict))` | Low | Consider protocol or ABC instead |
| f-string in Exception | `raise ValueError(f"...")` without context | Low | Prefer structured error with attributes |

## Severity Guide

| Severity | Criteria | Action |
|----------|----------|--------|
| High | Causes bugs, prevents testing, or blocks changes | Fix before extending the file |
| Medium | Reduces readability or maintainability | Fix on next touch |
| Low | Minor quality issue, cosmetic | Fix if convenient |

## Quick Reference: Smell → Category

| Category | Smells |
|----------|--------|
| Bloaters | Long Method, Large Class, Long Parameter List, Primitive Obsession, Data Clumps |
| OO Abusers | Switch Statements, Refused Bequest, Temporary Field, Alternative Classes |
| Change Preventers | Divergent Change, Shotgun Surgery, Parallel Inheritance |
| Dispensables | Excessive Comments, Dead Code, Duplicate Code, Speculative Generality, Data Class |
| Couplers | Feature Envy, Inappropriate Intimacy, Message Chains, Middle Man |
| Python-Specific | Mutable Default, Bare Except, Global State, String Type Check, Nested Comprehension, Star Import, Mutable Class Var |
