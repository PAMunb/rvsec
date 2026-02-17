# Audit Report Template

Use this template when running `/rv-doc-code <target> --audit`.

---

## Template

````markdown
## Code Documentation Audit: <target>

**Date**: <YYYY-MM-DD>
**Scope**: <module name, file path, or directory>

### Summary

| Metric | Count | % |
|--------|-------|---|
| Total elements (modules + classes + functions) | X | 100% |
| With docstrings | Y | Y/X% |
| Missing (Tier 1 — required) | A | — |
| Missing (Tier 2 — recommended) | B | — |
| Skippable (Tier 3 / P1) | D | — |

### Docstring Coverage by File

| File | Classes | Functions | Coverage | Tier 1 Gaps |
|------|---------|-----------|----------|-------------|
| file1.py | 2/2 | 8/10 | 83% | missing Raises in execute() |
| file2.py | 1/1 | 5/5 | 100% | — |
| file3.py | 0/0 | 3/6 | 50% | missing docstring on process(), validate() |

### Inline Comment Assessment

| File | Phase/Step Markers | WHY Blocks | Section Dividers | TODO Format |
|------|-------------------|------------|------------------|-------------|
| executor.py | OK | 1 missing | N/A | 2 non-standard |
| constants.py | N/A | N/A | OK | — |
| strategy.py | Missing phases | 3 missing | N/A | OK |

### Quality Issues

1. **<Issue category>**: <count> occurrences — <files> — Fix: <recommendation>
2. **<Issue category>**: <count> occurrences — <files> — Fix: <recommendation>

### Recommendations

Priority-ordered list of actions:

1. <Most impactful improvement>
2. <Second priority>
3. <Third priority>
````

---

## Issue Categories

Use these standardized categories in the Quality Issues section:

| Category | Description |
|----------|-------------|
| **Missing Tier 1 docstring** | Public element without docstring |
| **Incomplete docstring** | Missing Args, Returns, or Raises section |
| **Restating code** | Comment that repeats what the code says |
| **Non-standard TODO** | TODO/FIXME without parenthetical context |
| **Missing WHY block** | Complex logic without rationale explanation |
| **Promotional language** | Uses "elegant", "modern", etc. (P4 violation) |
| **Migration history** | References old code or changes (P4 violation) |
| **Types in docstring** | Type info in Args instead of signatures |
| **Missing ### sections** | Primary component without architectural sections |
| **Over-documented** | Docstring on self-evident code (P1 violation) |
