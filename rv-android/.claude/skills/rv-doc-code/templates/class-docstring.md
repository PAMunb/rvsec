# Class Docstring Templates

Templates for class-level docstrings.

---

## Tier 1 — Primary Component (with ### sections)

Use for: public classes with >5 methods or orchestration responsibility.

```python
class ClassName:
    """
    <Imperative summary — what this class does.>

    <1-2 paragraphs on purpose, design, and how it fits the system.>

    ### Architectural Decisions:

    - <Decision>: <rationale>

    ### Role in the System:

    - <Position in architecture — what uses it, what it uses>

    ### Key Features:

    - <Capability 1>
    - <Capability 2>

    ### Integration Points:

    - Input: <what it receives>
    - Output: <what it produces>
    - Components: <key collaborators>
    """
```

**Example**:

```python
class TaskExecutor:
    """
    Execute individual tasks using pluggable components.

    Orchestrate task execution through a component-based lifecycle:
    register components, initialize them with shared context, execute
    in coordinated phases, and clean up resources.

    ### Architectural Decisions:

    - Component-based: each execution phase is an independent component
    - Three-phase execution: initialization, coordinated execution, cleanup
    - Context sharing: all components receive the same task context dict

    ### Role in the System:

    - Central executor within rv-platform
    - Called by ExecutionController for each task in an experiment
    - Delegates to registered components for actual work

    ### Key Features:

    - Pluggable component registration
    - Coordinated emulator lifecycle management
    - Automatic resource cleanup on error

    ### Integration Points:

    - Input: Task, Tool, optional TaskStorage and ErrorHandler
    - Output: bool (success/failure), side effects via components
    - Components: EmulatorComponent, LogcatComponent, CoverageComponent, ToolComponent
    """
```

---

## Tier 1 — Regular Public Class (no ### sections)

Use for: public classes used by other modules but without orchestration role.

```python
class ClassName:
    """
    <Imperative summary.>

    <1-2 sentences on purpose and typical usage.>
    """
```

**Example**:

```python
class StringSimilarity:
    """
    Calculate string similarity using multiple distance metrics.

    Combine Levenshtein, Jaro-Winkler, and SequenceMatcher into a weighted
    score for robust package name matching. Used as fallback when component
    analysis produces ambiguous results.
    """
```

---

## Tier 1 — Dataclass / NamedTuple (with Attributes:)

Use for: data classes, named tuples, Pydantic models with significant fields.

```python
@dataclass
class ClassName:
    """<One-line summary.>

    Attributes:
        field_name: Description of field. Mention valid values or ranges
            when relevant.
        other_field: Description. Multi-line descriptions are indented
            4 spaces from field name.
    """
```

**Example**:

```python
@dataclass
class PackageDetectionResult:
    """Result of package detection analysis.

    Attributes:
        manifest_package: Package name declared in AndroidManifest.xml.
        code_package: Detected actual code package. May differ from manifest
            in apps with build variants or game engines.
        confidence: Detection confidence. Values: "high", "medium", "low".
        detection_method: Strategy that resolved the package. Values:
            "same_package", "single_package", "common_prefix",
            "most_common", "similarity", "manifest_fallback".
        all_packages: All distinct packages found in APK components.
        similarity_score: String similarity between manifest and code package (0.0-1.0).
        game_engine: Detected game engine runtime, or None.
    """
```

---

## Tier 2 — Internal Class

Use for: internal classes (_prefixed) with >10 methods.

```python
class _ClassName:
    """<Imperative summary.>"""
```

---

## Tier 3 — Small Helper

Use for: small internal classes (<3 methods).

```python
class _HelperName:
    """<One-line summary.>"""
```
