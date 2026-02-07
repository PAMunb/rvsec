---
name: rv-refactor-simplify
description: >-
  Simplify over-engineered or complex code. Use when reducing complexity,
  removing unnecessary abstractions, or applying KISS principle.
  Do NOT use for: extracting components (use /rv-refactor-extract),
  full module refactoring (use /rv-refactor).
argument-hint: [file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, Skill
---

# Simplify Code: $ARGUMENTS

## Guiding Principles

When simplifying code, you must be guided by fundamental software design principles that improve its quality and maintainability. Your goal is not just to make code shorter, but to make it better.

1.  **Simplicity (KISS Principle)**: All design should be as simple as possible, but no simpler. Avoid unnecessary complexity and "clever" code that is difficult for others to understand. A simple, clear design is easier to maintain and has fewer places for bugs to hide.

2.  **Reduce Cyclomatic Complexity**: Cyclomatic complexity measures the number of linearly independent paths through a program's source code. High complexity (e.g., many nested `if/else/for/while` statements) makes code harder to understand, test, and maintain.
    *   **Justification**: "I am replacing the nested `if` statements with a single guard clause. This reduces the **cyclomatic complexity** from 4 to 2 and makes the function's primary logic path clearer."

3.  **Increase Cohesion**: A cohesive module or function performs a single, well-defined task. If a function is doing too many things, it's a candidate for simplification, often by splitting it into smaller, more focused functions (which can then be handled by `/rv-refactor-extract`).
    *   **Justification**: "This function was both fetching data and formatting it. By simplifying it to only fetch data, I have increased its **cohesion** and made it more reusable."

4.  **Improve Clarity and Readability**: Code is read far more often than it is written. Simplifications should make the intent of the code more obvious to a human reader. This includes using clearer variable names, removing redundant logic, and preferring straightforward expressions.
    *   **Justification**: "I have simplified the boolean return statement. This improves **clarity** by removing redundant `if/else` branching and making the condition being returned more explicit."

## Requirement for Principle-Based Justification

When you propose a simplification, you **must** justify it using the principles above. Explain *why* the change improves the code's design.

- "This simplification is justified because it improves **readability** and reduces **cyclomatic complexity** by..."
- "I am applying the **KISS principle** here to remove an unnecessary layer of abstraction that was not being used."

This ensures that refactoring is deliberate and directly contributes to a better, more maintainable software architecture.

## Steps

1. **Analyze complexity** first - Use the **Skill tool**:
   ```
   Skill tool: skill="rv-analyze-complexity", args="$ARGUMENTS"
   ```
   This identifies the most complex areas that need simplification.

2. **Read and understand** the file at $ARGUMENTS

3. **Identify simplification opportunities**:
   - Unused parameters or variables
   - Over-abstracted code (unnecessary interfaces/base classes)
   - Duplicated code blocks
   - Complex conditionals
   - Unnecessary defensive code
   - Premature abstractions

4. **Plan simplifications**:
   - List specific changes
   - Ensure no functionality loss
   - Verify dependencies won't break

5. **Create backup** if major changes:
   ```bash
   cp path/to/file.py backup/file.py.bak
   ```

6. **Apply changes**:
   - Remove unused code
   - Inline trivial abstractions
   - Consolidate duplicated logic
   - Simplify conditionals

6. **Verify**:
   ```bash
   cd modules/$MODULE
   PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/ -v
   ```

## Common Simplifications

| Pattern | Before | After |
|---------|--------|-------|
| Nested ifs | `if x: if y:` | `if x and y:` |
| Boolean return | `if x: return True else: return False` | `return x` |
| Unnecessary else | `if x: return a else: return b` | `if x: return a; return b` |
| Single-use variable | `temp = f(); return temp` | `return f()` |
| Empty base class | `class X(Base): pass` | Remove if Base unused |

## Output Format

```
## Simplification Report: [filename]

### Before
- Lines: XXX
- Classes: Y
- Functions: Z
- Complexity issues: [list]

### Changes Made
1. **[Change 1]**: [reason]
   - Before: `code`
   - After: `code`

2. **[Change 2]**: [reason]

### After
- Lines: XXX (reduced by Y)
- Classes: Y
- Functions: Z

### Backup
- Created: backup/[filename].bak

### Verification
- Tests: [pass/fail]
- Imports: [ok/broken]
```

## Guidelines

- Three similar lines > premature abstraction
- Don't add helpers for one-time operations
- Don't design for hypothetical future
- If unused, delete completely
- Avoid backwards-compatibility hacks
