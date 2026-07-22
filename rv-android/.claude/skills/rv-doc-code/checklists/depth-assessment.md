# Depth Assessment: Tier Assignment Decision Tree

Use this checklist to assign documentation depth (Tier 1/2/3/Skip) to each Python element.

---

## Module-Level Docstrings

```
Is it an __init__.py with only re-exports?
    └── YES → Skip
    └── NO ──►

Is it a test file?
    └── YES → Tier 3 (1-line summary if any)
    └── NO ──►

Is it a primary component (entry point, controller, orchestrator, strategy)?
    └── YES → Tier 1 WITH ### sections
    └── NO ──►

Is it a utility/helper module with non-trivial logic?
    └── YES → Tier 1 WITHOUT ### sections
    └── NO → Tier 2 (1-line summary)
```

**### Section Vocabulary** (fixed — do not invent new names):
- `### Architectural Decisions:` — design choices and rationale
- `### Role in the System:` — where it fits in the module/system
- `### Key Features:` — main capabilities
- `### Integration Points:` — inputs, outputs, dependencies

---

## Class-Level Docstrings

```
Is it a public class with >5 methods or orchestration responsibility?
    └── YES → Tier 1 WITH ### sections
    └── NO ──►

Is it a public class (API surface, used by other modules)?
    └── YES → Tier 1 WITHOUT ### sections
    └── NO ──►

Is it a dataclass or NamedTuple?
    └── YES → Tier 1 with Attributes: section
    └── NO ──►

Is it an internal class (_prefixed or module-private)?
    └── YES, >10 methods → Tier 2
    └── YES, ≤10 methods → Tier 3
    └── NO ──►

Is it a small helper class (<3 methods)?
    └── YES → Tier 3 (1-line)
    └── NO → Tier 2
```

---

## Function/Method Docstrings

```
Is it a public function/method (no _ prefix)?
    └── YES → Tier 1 (full)
    └── NO ──►

Is it __init__ of a public class?
    └── YES → Tier 1 (with State: section if significant state)
    └── NO ──►

Is it a protected method (_prefix) with >10 lines?
    └── YES → Tier 2 (summary + Args + Returns)
    └── NO ──►

Is it a protected method ≤10 lines?
    └── YES → Tier 3 (1-line)
    └── NO ──►

Is it self-evident (≤3 lines, clear name, simple property)?
    └── YES → Skip (no docstring needed per P1)
    └── NO → Tier 3
```

---

## Raises Documentation Decision

```
Does the method contain `raise` statements?
    └── YES → Document in Raises: section
    └── NO ──►

Does it propagate specific exceptions from dependencies?
    └── YES → Document in Raises: section
    └── NO ──►

Does it use @ErrorHandler decorator?
    └── YES → Do NOT duplicate handler exceptions
    └── NO → No Raises: section needed
```

---

## Examples Section Decision

```
Is the return type complex (Dict[str, Any], nested structures)?
    └── YES → Include Example:
    └── NO ──►

Does it have non-obvious edge cases?
    └── YES → Include Example:
    └── NO ──►

Is it a simple getter, setter, or predicate?
    └── YES → Skip Example:
    └── NO → Consider Example: based on complexity
```

---

## Inline Comments Decision

```
Is this orchestration code (controller, executor, coordinator)?
    └── YES → Add Phase markers (# Phase N: description)
    └── NO ──►

Is this an algorithm with sequential steps?
    └── YES → Add Step markers (# Step N: description)
    └── NO ──►

Is there complex/non-obvious logic?
    └── YES → Add WHY block (multi-line # explanation)
    └── NO ──►

Is this a constants/configuration file?
    └── YES → Add section dividers (# === LABEL ===)
    └── NO → No special inline comments needed
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Example | Fix |
|-------------|---------|-----|
| Restating code | `# Check if list is empty` before `if not items:` | Explain WHY the check matters |
| Over-documenting trivials | Full docstring on `@property` that returns `self.name` | Skip |
| Promotional language | "Elegant solution for..." | State what it does, not how you feel |
| Migration history | "Migrated from old_module" | Describe current behavior only (P4) |
| Types in Args | `Args: name (str): The name` | Types belong in signatures, not docstrings |
| Documenting @ErrorHandler exceptions | Listing exceptions the decorator handles | Only document exceptions the method itself raises |
