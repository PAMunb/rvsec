# Refactoring Indicators

Catalog of code patterns that indicate refactoring need, mapped to specific refactoring techniques and expected complexity reduction.

## How to Use

1. During complexity analysis, identify which code smells are present
2. Look up the smell in the table below to find the recommended refactoring technique
3. Check the detection heuristics to confirm the smell is real (not a false positive)
4. Report findings with: smell name, location, recommended technique, expected impact

---

## Smell-to-Refactoring Mapping

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
| Parallel Inheritance | Adding subclass in one hierarchy requires subclass in another | Move Method, collapse hierarchy | Class count −30% |
| Speculative Generality | Abstract class with 1 subclass, unused parameters, methods named with "future" | Collapse Hierarchy, Remove Middle Man | Class count −20%, LOC −15% |

## Detailed Smell Descriptions

### God Class

**Indicators**: Class has many unrelated methods, multiple groups of fields that are used independently, class name is vague (Manager, Handler, Processor, Utility).

**Confirm by**: Group methods by which fields they access. If 3+ independent groups exist, the class has 3+ responsibilities.

**Refactoring**: Extract each responsibility group into its own class. The original class becomes a coordinator or is deleted.

### Long Method

**Indicators**: Function exceeds 30 logical lines, contains multiple levels of abstraction (high-level orchestration mixed with low-level details), requires scrolling to read.

**Confirm by**: Can you name what each section does? If sections have distinct purposes, they should be separate functions.

**Refactoring**: Extract Method for each logical section. Name extracted methods by what they do, not how.

### Feature Envy

**Indicators**: Method calls methods or accesses attributes of another object more than its own class. Often appears after Extract Class when methods were not moved.

**Confirm by**: Count references to `self` vs references to the other object. If other > self, the method belongs there.

**Refactoring**: Move Method to the class whose data it uses most. Pass minimal parameters.

### Data Clumps

**Indicators**: Same group of 3+ variables appears in multiple function signatures, constructor parameters, or field groups.

**Confirm by**: If removing one item from the group makes the others meaningless, they belong together.

**Refactoring**: Introduce Parameter Object or Extract Class. Use a dataclass or NamedTuple in Python.

### Primitive Obsession

**Indicators**: Validation logic repeated wherever the value is used (e.g., checking email format in 5 places). String constants used as type discriminators.

**Confirm by**: Search for the same validation/parsing pattern appearing in multiple locations.

**Refactoring**: Create a Value Object that encapsulates the value and its validation. In Python: `@dataclass(frozen=True)` or `NewType` for simple cases.

### Switch Statements / Type Checking

**Indicators**: `isinstance()` or string comparison chains on the same discriminator field in 3+ locations. Adding a new type requires editing multiple files.

**Confirm by**: Search for all `isinstance` or `type()` checks on the same base class.

**Refactoring**: Replace with polymorphism. Define method on base class, override in subclasses. For simple cases in Python, use `functools.singledispatch` or dictionary dispatch.

## Dead Code Patterns (Python-Specific)

| Pattern | Detection | Action |
|---------|-----------|--------|
| Code after `return`/`raise`/`break` | Unreachable statement analysis | Remove immediately (P1) |
| Unused imports | Not referenced in module | Remove with `autoflake` or manually (P1) |
| `pass` in non-empty block | Block already has statements | Remove `pass` (P1) |
| Assigned but never read | Variable set, never used downstream | Remove assignment (P2) |
| Empty `except: pass` | Exception swallowed silently | Log or re-raise (P2) |

## Severity Classification

| Severity | Criteria | SLA |
|----------|----------|-----|
| Critical | CC > 50, God Class > 30 methods | Refactor before next feature |
| High | CC 21–50, Long Method > 50 lines | Refactor within current sprint |
| Medium | CC 11–20, 3+ smell instances | Refactor on next touch |
| Low | Minor smells, cosmetic | Optional improvement |
