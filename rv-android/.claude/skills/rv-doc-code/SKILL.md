---
name: rv-doc-code
description: >-
  Generate or audit code-level documentation (docstrings + inline comments).
  Use when adding documentation to new code, updating after refactoring,
  or auditing documentation coverage in a module.
  Do NOT use for: README.md (use /rv-doc-readme), CLAUDE.md (use /rv-doc-generate-claude-md),
  architecture.md (use /rv-doc-architecture), ADRs (use /rv-doc-adr).
argument-hint: [module-name or file-path] [--audit]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

# Code Documentation: $ARGUMENTS

Generate or audit code-level documentation (docstrings + inline comments) for the specified target.

## Modes

| Mode | Trigger | Action |
|------|---------|--------|
| **Generate** | `/rv-doc-code rv-platform` | Add/update docstrings + inline comments |
| **Audit** | `/rv-doc-code rv-platform --audit` | Report-only coverage analysis |

Parse `$ARGUMENTS` to determine:
1. **Target**: module name (e.g., `rv-platform`) or file path (e.g., `modules/rv-agent/src/rv_agent/agent/rv_agent.py`)
2. **Mode**: if `--audit` is present, run audit mode; otherwise, run generate mode

## Supporting Files

Read these files for templates and conventions:

- **Templates**:
  - `templates/module-docstring.md` — Module-level docstring templates (Tier 1 with/without ### sections, Tier 2)
  - `templates/class-docstring.md` — Class-level docstring templates (primary, regular, dataclass)
  - `templates/function-docstring.md` — Function/method templates (Tier 1/2/3/Skip)
  - `templates/inline-comments.md` — Inline comment patterns (phases, steps, WHY, dividers, TODO)
  - `templates/audit-report.md` — Audit report output template

- **Checklists**:
  - `checklists/depth-assessment.md` — Decision trees for tier assignment
  - `checklists/quality-criteria.md` — Quality standards and anti-patterns

## Reference Files (Gold Standards)

Before generating documentation, read these files to calibrate quality:

- **Docstring gold standard**: `modules/rv-android-core/src/rv_android_core/util/android/package_detector.py`
- **Phase markers**: `modules/rv-platform/src/rv_platform/execution/executor.py`
- **Section dividers**: `modules/rv-android-core/src/rv_android_core/constants.py`

## RV-Android Docstring Conventions

These conventions are codified from existing code patterns in the codebase:

### Convention 1 — Architectural Narrative Sections

Primary components (entry points, controllers, orchestrators, strategies) use `###` headers in class/module docstrings. Fixed vocabulary only:

- `### Architectural Decisions:` — design choices and rationale
- `### Role in the System:` — where it fits in the module/system
- `### Key Features:` — main capabilities
- `### Integration Points:` — inputs, outputs, dependencies

Do NOT invent new section names. Not all sections are required — use only what applies.

### Convention 2 — Google-Style Format

- `Args:` — parameter descriptions (no types — types live in signatures)
- `Returns:` — return value description
- `Raises:` — exceptions the method itself raises
- `Example:` — runnable doctest examples for complex I/O

Summary line: imperative mood ("Calculate similarity score."), one line, ends with period.

### Convention 3 — Raises Documentation

- Methods containing `raise` statements: document in `Raises:` section
- Methods propagating specific exceptions: document in `Raises:` section
- Methods with `@ErrorHandler` decorator: do NOT duplicate handler exceptions

### Convention 4 — State Documentation in `__init__`

Classes with significant instance state include a `State:` section in `__init__`:

```python
def __init__(self, ...):
    """Initialize <purpose>.

    Args:
        ...

    State:
        self.attribute: Description. Lifecycle information.
    """
```

### Convention 5 — Dict Return Schema

Methods returning `Dict[str, Any]` document keys:

```python
def get_context(self) -> Dict[str, Any]:
    """Build context dictionary.

    Returns:
        Dictionary with keys:
        - "key_name" (type): Description
    """
```

### Convention 6 — TODO/FIXME Format

```python
# TODO(context): description
# FIXME(context): description
```

Context is module name, issue number, or topic: `TODO(rv-agent)`, `TODO(#42)`, `FIXME(rv-coverage)`.

---

## Workflow: Generate Mode

```
STEP 1: ANALYZE ─── Catalog all Python elements, existing docs
STEP 2: CLASSIFY ── Assign depth tier (1/2/3/Skip) per element
STEP 3: GENERATE ── Apply docstring templates + add inline comments
STEP 4: VERIFY ──── Syntax check, no test breakage
REPORT
```

### Step 1: Analyze Target

1. **Resolve target path**:
   - Module name → `modules/<name>/src/<package>/`
   - File path → use directly

2. **Catalog all Python files** in scope:
   ```
   Glob: modules/<target>/src/**/*.py
   ```

3. **For each file**, identify:
   - Module-level docstring (present/absent)
   - All classes with their methods
   - All standalone functions
   - Existing docstrings and their completeness
   - Existing inline comments (phases, steps, WHY blocks, section dividers)
   - TODO/FIXME annotations and their format

### Step 2: Classify Elements

Use the decision trees from `checklists/depth-assessment.md` to assign tiers:

| Tier | Depth | Elements |
|------|-------|----------|
| **1** | Full | Public API, primary components, `__init__` of public classes |
| **2** | Summary + Args + Returns | Internal methods >10 lines |
| **3** | 1-line or skip | Trivial private methods, small helpers |
| **Skip** | No docstring | Self-evident properties, `__repr__`, `__len__`, test files, empty `__init__.py` |

Present the classification summary to confirm scope before generating.

### Step 3: Generate Documentation

**Part A — Docstrings**:

For each element needing documentation:
1. Read the implementation to understand purpose and behavior
2. Select the appropriate template from `templates/`
3. Write the docstring following the conventions above
4. For Tier 1 primary components: include applicable `###` sections
5. For `__init__` with state: include `State:` section
6. For dict returns: document key schema

**Part B — Inline Comments**:

For each file:
1. **Orchestration code** (controllers, executors): add Phase markers if missing
2. **Algorithm code**: add Step markers if missing
3. **Complex logic**: add WHY blocks before non-obvious operations
4. **Constants files**: add section dividers if missing
5. **TODO/FIXME**: fix format to use `# TODO(context): description`

**Rules**:
- Do NOT add docstrings to elements classified as "Skip"
- Do NOT add comments that restate the code (P1)
- Do NOT use promotional language (P4)
- Do NOT reference migration history (P4)
- Preserve existing docstrings that already meet quality criteria — only update or add

### Step 4: Verify

1. **Syntax check**: ensure all modified files parse without errors
   ```bash
   python -m py_compile <file>
   ```

2. **Test check** (if module has tests):
   ```bash
   cd modules/<target> && uv run pytest tests/ -x -q 2>&1 | head -20
   ```

3. **Review quality**: spot-check against `checklists/quality-criteria.md`

### Report

```
## Documentation Generated: <target>

### Summary
- Files modified: N
- Docstrings added: X (Tier 1: A, Tier 2: B, Tier 3: C)
- Docstrings updated: Y
- Inline comments added: Z (Phase: P, Step: S, WHY: W, Dividers: D)
- TODO/FIXME reformatted: T

### Files Modified
- `path/to/file1.py` — 3 docstrings added, 1 WHY block
- `path/to/file2.py` — 1 docstring updated (added Raises section)

### Quality
- Syntax check: PASS
- Tests: PASS (or N/A)

### Skipped (per P1)
- N elements skipped as self-evident
```

---

## Workflow: Audit Mode

When `--audit` is in `$ARGUMENTS`, produce a report WITHOUT modifying any files.

### Step 1: Analyze (same as Generate Step 1)

### Step 2: Classify (same as Generate Step 2)

### Step 3: Generate Report

Use the template from `templates/audit-report.md` to produce:

1. **Summary table**: total elements, coverage percentage, gaps by tier
2. **Per-file coverage**: classes, functions, coverage %, Tier 1 gaps
3. **Inline comment assessment**: Phase/Step markers, WHY blocks, section dividers, TODO format
4. **Quality issues**: categorized with counts and file references
5. **Recommendations**: priority-ordered actions

Do NOT modify any files in audit mode.

---

## Integration Notes

This skill can be called after implementation by other skills:
- `/rv-feature` → after implementation phase, to document new code
- `/rv-refactor` → after restructuring, to update docstrings
- `/rv-tdd` → after GREEN/REFACTOR, to document new functions
- `/rv-verify` → optional docstring coverage check

These integrations are suggestions documented here — no changes to other skills are needed.

---

## Documentation Principles

All generated documentation must comply with RV-Android development principles:

| Principle | Application |
|-----------|-------------|
| **P1 Simplicity** | Skip self-evident code. No docstrings on trivial properties. No comments restating code. |
| **P2 Human-Readable** | Docstrings explain WHY, not just WHAT. Self-contained for readers. |
| **P3 No Backward Compat** | No "migrated from", "replaces old". Describe current behavior only. |
| **P4 Current-State** | No version history. No promotional language ("elegant", "modern"). |

## Rules

1. **Google-style only** — no reST, no NumPy style
2. **Imperative mood** — "Calculate score." not "Calculates score."
3. **No types in Args** — types belong in function signatures
4. **Fixed ### vocabulary** — only the 4 allowed section names
5. **Preserve existing good docs** — update, don't replace unnecessarily
6. **P1 governs depth** — when in doubt, less documentation is better than over-documentation
7. **English only** — all docstrings and comments in English
