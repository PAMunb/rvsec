# Dead Code Categories

Classification framework for dead code with priority-based removal guidelines.

## How to Use

1. Scan the target module for each dead code category below
2. Classify each finding by category and priority
3. Verify findings against the false-positive patterns checklist before recommending removal
4. Report findings grouped by priority (P1 first)

---

## Category 1: Unreachable Code

Code that can never execute due to control flow.

**Patterns**:
- Statements after `return`, `raise`, `break`, `continue`
- Code inside `if False:` or `if 0:` blocks
- Conditions that are always true/false (e.g., `if isinstance(x, str)` where x is always str)
- Branches eliminated by constant values

**Priority**: P1 — Remove immediately, zero risk.

**Detection**: AST analysis or linter rules (flake8, pylint unreachable warnings).

## Category 2: Unused Imports

Imported names that are never referenced in the module.

**Patterns**:
- `import module` where `module` is never used
- `from module import name` where `name` is never referenced
- Imports used only in deleted code

**Priority**: P1 — Remove immediately. Unused imports slow module loading and obscure actual dependencies.

**Detection**: `autoflake`, `flake8` F401, `pylint` unused-import.

**Caution**: Check for re-exports (`__all__`), side-effect imports, and `TYPE_CHECKING` usage before removing.

## Category 3: Unused Functions/Methods

Functions defined but never called from any code path.

**Patterns**:
- Module-level functions with zero callers
- Private methods (`_name`) never called within the class
- Helper functions left over from refactoring

**Priority**: P2 — Remove after verifying no dynamic callers exist.

**Detection**: Search for all references to the function name across the codebase. Check for string-based dispatch, decorators that register functions, and test fixtures.

## Category 4: Unused Variables

Variables assigned but never read.

**Patterns**:
- Local variables assigned and never referenced
- Loop variables only used for iteration count (`for x in range(n)` where x is unused — use `_`)
- Return values captured but ignored
- Instance attributes set in `__init__` but never accessed

**Priority**: P2 — Remove after confirming no side effects in the assignment expression.

**Detection**: `pylint` unused-variable, AST analysis for read/write sets.

## Category 5: Unused Classes

Classes defined but never instantiated, subclassed, or referenced as a type.

**Patterns**:
- Classes with zero instantiation sites
- Abstract base classes with no concrete subclasses
- Dataclasses never constructed
- Exception classes never raised

**Priority**: P2 — Remove after checking for dynamic instantiation (factories, registries).

**Detection**: Search for class name in constructors, type hints, isinstance checks, and string references.

## Category 6: Commented-Out Code

Executable code preserved in comments rather than being deleted.

**Patterns**:
- Blocks of commented Python code (indented, syntactically valid)
- `# old implementation:` followed by commented code
- TODO comments with attached dead code
- Sections marked `# DEPRECATED` or `# REMOVED`

**Priority**: P1 — Remove immediately. Version control preserves history. Commented code clutters, confuses, and rots.

**Detection**: Heuristic — look for comment blocks where the comment text is valid Python syntax. Lines starting with `# ` followed by Python keywords (`def`, `class`, `if`, `for`, `return`, `import`).

## Category 7: Redundant Code

Code that duplicates logic already present elsewhere or wraps without adding value.

**Patterns**:
- Wrapper functions that pass through all arguments without transformation
- Duplicate implementations of the same logic in different modules
- Utility functions that replicate standard library functionality
- Adapter classes with 1:1 method delegation and no added behavior

**Priority**: P3 — Investigate before removing. One copy may be the canonical source; identify which to keep.

**Detection**: Code similarity analysis. Look for functions with identical logic, different names.

## Category 8: Obsolete Feature Flags

Configuration flags that are always on or always off, never toggled.

**Patterns**:
- Boolean flags that are always `True` in all configurations
- Environment variables that are always set to the same value
- `if FEATURE_X:` where `FEATURE_X` has been `True` for all known deployments
- Configuration options documented but never changed from default

**Priority**: P3 — Investigate first. Remove the flag and inline the active branch.

**Detection**: Search for the flag name in all configuration files, environment setup, and command-line argument parsing.

## Priority Summary

| Priority | Criteria | Action | Risk |
|----------|----------|--------|------|
| P1 | Unreachable code, unused imports, commented-out code | Remove immediately | Zero — code is provably unused |
| P2 | Unused functions, variables, classes | Remove after search for dynamic usage | Low — may have dynamic callers |
| P3 | Redundant code, obsolete flags | Investigate, then remove or consolidate | Medium — requires understanding intent |

## Removal Guidelines

1. **Backup**: Move to `backup/` before deletion (per P3 principle, version control is the primary backup)
2. **One commit per category**: Group removals by category for clean git history
3. **Grep after removal**: Search for dangling references to deleted names
4. **Run tests**: Full test suite after each removal batch
5. **Update docs**: Remove references to deleted code from CLAUDE.md, architecture.md
