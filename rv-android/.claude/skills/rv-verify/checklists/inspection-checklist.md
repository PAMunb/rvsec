# Code Inspection Checklist

Systematic checklist for peer code review. Use during manual inspection to catch defects that automated tools miss.

---

## How to Use This Checklist

1. **Before review**: Read the code to understand its purpose
2. **During review**: Check each category systematically
3. **After review**: Document findings with file:line references
4. **Follow-up**: Verify fixes were made correctly

---

## Inspection Categories

### 1. Data Faults

| Check | Question | Look For |
|-------|----------|----------|
| Initialization | Are all variables initialized before use? | Uninitialized variables, None checks |
| Constants | Have all magic numbers been named? | Hardcoded values that should be constants |
| Array bounds | Is the upper bound correct (size or size-1)? | Off-by-one errors in loops |
| String delimiters | If using strings, is delimiter explicitly assigned? | Missing null terminators (C/C++) |
| Buffer overflow | Is there any possibility of buffer overflow? | Unbounded string operations, array access |
| Type coercion | Are implicit type conversions safe? | Integer overflow, float precision loss |

**Python-specific**:
- [ ] Mutable default arguments (e.g., `def foo(items=[])`)
- [ ] Variable shadowing (local hiding global)
- [ ] Late binding closures in loops

---

### 2. Control Faults

| Check | Question | Look For |
|-------|----------|----------|
| Conditions | Is each conditional statement correct? | Inverted logic, missing conditions |
| Loop termination | Is each loop certain to terminate? | Infinite loops, missing break conditions |
| Bracketing | Are compound statements correctly bracketed? | Missing braces, indentation errors |
| Case coverage | In switch/match, are all cases handled? | Missing cases, fall-through bugs |
| Break statements | If break required after each case, is it present? | Missing break in switch |
| Exception flow | Is the exception flow correct? | Catching too broad, swallowing exceptions |

**Python-specific**:
- [ ] `if x` vs `if x is not None` (empty collections are falsy)
- [ ] `except:` catching all exceptions including SystemExit
- [ ] `else` clause on loops (executes if no break)

---

### 3. Input/Output Faults

| Check | Question | Look For |
|-------|----------|----------|
| Input usage | Are all input variables used? | Unused parameters |
| Output assignment | Are all outputs assigned before return? | Unassigned return values |
| Input validation | Can unexpected inputs cause corruption? | Missing validation, type errors |
| Resource cleanup | Are files/connections properly closed? | Missing close(), context managers |
| Encoding | Is character encoding handled correctly? | Implicit encoding assumptions |

**Python-specific**:
- [ ] Using `with` for file operations
- [ ] Proper handling of binary vs text mode
- [ ] Encoding specified for file operations (`encoding='utf-8'`)

---

### 4. Interface Faults

| Check | Question | Look For |
|-------|----------|----------|
| Parameter count | Do calls have the correct number of parameters? | Missing/extra arguments |
| Parameter types | Do formal and actual parameter types match? | Type mismatches |
| Parameter order | Are parameters in the right order? | Swapped arguments |
| Shared memory | Do components have same model of shared data? | Inconsistent data structures |
| API contracts | Are API preconditions/postconditions met? | Contract violations |
| Return values | Are return values checked? | Ignored return values, unchecked errors |

**Python-specific**:
- [ ] `*args` and `**kwargs` used correctly
- [ ] Keyword-only arguments used where appropriate
- [ ] Method resolution order (MRO) in multiple inheritance

---

### 5. Storage Management Faults

| Check | Question | Look For |
|-------|----------|----------|
| Link reassignment | If linked structure modified, are all links correct? | Broken references, orphaned nodes |
| Dynamic allocation | If dynamic storage used, is space allocated correctly? | Memory leaks, double allocation |
| Deallocation | Is space explicitly deallocated when no longer needed? | Resource leaks |
| Reference cycles | Could circular references prevent garbage collection? | Memory leaks in complex structures |

**Python-specific**:
- [ ] Circular references with `__del__` methods
- [ ] Large objects not released (assign to None if needed)
- [ ] Generator exhaustion handling

---

### 6. Exception Management Faults

| Check | Question | Look For |
|-------|----------|----------|
| Error conditions | Have all possible error conditions been taken into account? | Missing error handling |
| Exception specificity | Are exceptions specific enough? | Over-broad exception catching |
| Error messages | Do error messages provide useful information? | Cryptic or missing messages |
| Recovery | Is recovery from errors handled correctly? | Partial state after errors |
| Logging | Are errors logged appropriately? | Silent failures |

**Python-specific**:
- [ ] Using `raise from` for exception chaining
- [ ] Not catching `BaseException` (catches KeyboardInterrupt)
- [ ] Proper use of `finally` for cleanup
- [ ] Context managers for resource cleanup

---

## Severity Classification

| Severity | Description | Action |
|----------|-------------|--------|
| **CRITICAL** | Crash, data loss, security breach | Block merge |
| **MAJOR** | Incorrect behavior, potential bugs | Must fix before merge |
| **MINOR** | Code quality, maintainability | Should fix, can defer |
| **STYLE** | Formatting, naming conventions | Nice to fix |

---

## Review Record Template

```markdown
## Code Review: [Component/PR]

**Reviewer**: [name]
**Date**: [YYYY-MM-DD]
**Files Reviewed**: [list]

### Findings

| # | File:Line | Severity | Category | Description |
|---|-----------|----------|----------|-------------|
| 1 | foo.py:42 | MAJOR | Data | Uninitialized variable `count` |
| 2 | bar.py:15 | MINOR | Interface | Return value not checked |

### Summary
- Critical: X
- Major: Y
- Minor: Z
- Style: W

### Verdict
[ ] Approved
[ ] Approved with minor changes
[ ] Changes requested
[ ] Rejected
```

---

## Automated vs Manual Checks

| Check Type | Automated Tools | Manual Review Needed |
|------------|-----------------|---------------------|
| Syntax errors | Linters, compilers | No |
| Type errors | mypy, pyright | Partially |
| Style issues | black, flake8 | No |
| Security patterns | bandit | Yes (context needed) |
| Logic errors | Tests | Yes |
| Design issues | None | Yes |
| Performance | Profilers | Yes |
| Documentation | None | Yes |

**Key insight**: Automated tools catch ~25-60% of defects. Manual inspection catches the rest.
