# Module Docstring Templates

Templates for module-level (`"""..."""` at top of file) docstrings.

---

## Tier 1 — Primary Module (with ### sections)

Use for: entry points, controllers, orchestrators, strategies, key components.

```python
"""
<Imperative summary — what this module does in one sentence.>

<1-3 paragraphs explaining purpose, design rationale, and how the module
fits into the broader system. Self-contained for a reader who has not
seen the implementation.>

### Architectural Decisions:

- <Decision>: <rationale>
- <Decision>: <rationale>

### Role in the System:

- <Where it fits — what calls it, what it calls>
- <Key relationships with other modules>

### Integration Points:

- Input: <what it receives and from where>
- Output: <what it produces and for whom>
- Dependencies: <key module dependencies>
"""
```

**Example** (from executor pattern):

```python
"""
Manage task execution through component-based architecture.

This module coordinates individual task execution within rv-platform,
handling emulator lifecycle, tool execution, and coverage collection.
The component-based design allows each execution phase to be independently
configured and tested.

### Architectural Decisions:

- Component-based execution: each phase (emulator, coverage, tool) is
  an independent component registered at runtime
- Dependency injection: components receive context rather than
  managing their own dependencies

### Role in the System:

- Receives tasks from ExecutionController in rv-platform
- Coordinates emulator, logcat, coverage, and tool components
- Reports execution results back to the platform

### Integration Points:

- Input: Task from ExecutionController, Tool from ToolFactory
- Output: TaskResult with execution status and coverage data
- Dependencies: rv-android-core (ErrorHandler, logging), rv-tools (Tool interface)
"""
```

---

## Tier 1 — Utility Module (no ### sections)

Use for: utility/helper modules with non-trivial logic but no orchestration role.

```python
"""
<Imperative summary.>

<1-2 paragraphs explaining what the module provides and how it is used
by other parts of the system.>
"""
```

**Example**:

```python
"""
String similarity algorithms for package name matching.

Provide Levenshtein, Jaro-Winkler, and combined similarity metrics
used by PackageDetector to resolve package name discrepancies between
AndroidManifest.xml and actual code organization.
"""
```

---

## Tier 2 — Simple Module

Use for: straightforward modules with clear purpose.

```python
"""
<One-line imperative summary.>
"""
```

---

## Skip

Do NOT add module docstrings to:
- `__init__.py` with only re-exports or empty
- Test files (test_*.py)
- Configuration files
