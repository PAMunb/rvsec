# Complexity Analysis Reference

Consolidated reference for module-scoped complexity analysis. Contains metric thresholds, refactoring indicators, and Python-specific signals.

This file is the single source of numeric thresholds (CC, MI, size, nesting, parameters, coupling) for the analysis, review, and refactoring skills. Other skills point here instead of restating numbers; a change to a threshold is made here only.

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

### Maintainability Index

`radon mi` prints MI normalized to 0–100 (the non-normalized value, which includes a comment term, times 100/171). The bands below are compared directly against that printed number. They are the classic 65/85 bands of the original 0–171 scale converted to radon's scale (65 × 100/171 ≈ 38, 85 × 100/171 ≈ 50); applying 65/85 to the printed number would mark over a third of the workspace's files as Poor. Radon's own letter grades (A > 19, B 10–19, C ≤ 9) are a different, more lenient scale: a file graded A can still fall in the Poor band.

| Range (radon's printed MI) | Category | Action |
|-------|----------|--------|
| > 50 | Good | Maintainable |
| 38–50 | Moderate | Monitor; refactor on next change |
| < 38 | Poor | Prioritize refactoring |

Files in the Poor band: `uv run radon mi modules/<module>/src/ -s | awk -F'[()]' '$(NF-1)+0 < 38'`.

### Size Thresholds

Lines are SLOC as reported by `radon raw`.

| Scope | Review | Must split |
|-------|--------|------------|
| Function/method | — | > 50 lines: extract sub-functions |
| Class | — | > 500 lines: split responsibilities |
| File | > 500 lines | > 1000 lines: split into submodules |

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
| Afferent coupling (Ca) | Workspace modules that depend on this one | High Ca = stable abstraction needed |
| Efferent coupling (Ce) | Workspace modules this one depends on | Ce > 7 = fragile, consider facade |
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
| God Class | > 7 responsibilities, > 20 methods, > 15 fields, or over the class size limit | Extract Class | CC −30%, LOC −40% |
| Long Method | Over the function size limit, nesting 4+, or 6+ params (tables above) | Extract Method | CC −50%, nesting −2 |
| Feature Envy | Method uses more data from another class than its own | Move Method | Coupling −1 per move |
| Data Clumps | Same 3+ params appear together in multiple signatures | Extract Class / Introduce Parameter Object | Param count −60% |
| Divergent Change | File changed for unrelated reasons in different commits (see Change-History Smells) | Extract Class by responsibility | SRP violations −100% |
| Shotgun Surgery | One logical change touches 5+ source files (see Change-History Smells) | Move Method, Inline Class | Files touched −50% |
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

### Change-History Smells

Divergent Change and Shotgun Surgery cannot be seen in one snapshot of the code; they are read from `git log`. Run from the rv-android root for a file `F`, over its last 30 `feat`/`fix` commits (formatting, renames, and bulk cleanups would otherwise dominate; `--grep` matches any message line, so skip an occasional commit of another type):

```bash
# Divergent Change: do the subjects name unrelated concerns? Cite the commits as evidence.
git log -n 30 -E --grep='^(feat|fix)' --format='%h %s' -- "$F"

# Shotgun Surgery: non-test .py files changed by each of those commits (5+ = smell)
git log -n 30 -E --grep='^(feat|fix)' --relative --full-diff --format='@%h %s' --name-only -- "$F" \
  | awk '/^@/{if(h)print n"\t"h; h=$0; n=0; next} /\.py$/ && !/(^|\/)tests?\//{n++} END{if(h)print n"\t"h}' \
  | sort -rn | head

# Co-change partners: files that keep changing with F (candidates for Move Method)
git log -n 30 -E --grep='^(feat|fix)' --relative --full-diff --format= --name-only -- "$F" \
  | grep '\.py$' | grep -vE '(^|/)tests?/' | grep -vxF "$F" | sort | uniq -c | sort -rn | head
```
