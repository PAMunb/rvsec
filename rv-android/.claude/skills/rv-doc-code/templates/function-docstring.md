# Function/Method Docstring Templates

Templates for function and method docstrings at three depth tiers.

---

## Tier 1 — Public Method (full)

Use for: all public methods (no `_` prefix).

```python
def method_name(self, arg1: Type1, arg2: Type2) -> ReturnType:
    """<Imperative summary in one sentence.>

    <Optional 1-2 sentences with additional context, design rationale,
    or explanation of non-obvious behavior.>

    Args:
        arg1: Description of first argument. Mention constraints or
            valid values when relevant.
        arg2: Description of second argument.

    Returns:
        Description of return value. For complex types, describe
        the structure.

    Raises:
        ValueError: When arg1 is invalid.
        FileNotFoundError: When the target path does not exist.

    Example:
        >>> instance = ClassName()
        >>> result = instance.method_name(value1, value2)
        >>> result.field
        'expected_value'
    """
```

**Example**:

```python
def detect_package(self, apk: APK) -> PackageDetectionResult:
    """Detect actual package name of APK using priority-based heuristics.

    Apply six detection strategies in order of confidence to resolve
    discrepancies between manifest package and actual code organization.

    Args:
        apk: Androguard APK instance (already loaded).

    Returns:
        PackageDetectionResult with manifest_package, code_package,
        confidence, detection_method, and supporting data.

    Raises:
        ValueError: When apk has no valid AndroidManifest.xml.

    Example:
        >>> detector = PackageDetector()
        >>> result = detector.detect_package(apk)
        >>> result.code_package
        'com.example.app'
    """
```

---

## Tier 1 — `__init__` with State Section

Use for: `__init__` of public classes with significant instance state.

```python
def __init__(self, arg1: Type1, arg2: Type2):
    """Initialize <class purpose>.

    Args:
        arg1: Description.
        arg2: Description.

    State:
        self.attribute1: Description. Initial value and lifecycle.
        self.attribute2: Description. When and how it changes.
    """
```

**Example**:

```python
def __init__(self, task: Task, tool: Tool, task_storage: TaskStorage = None):
    """Initialize executor with task and tool.

    Args:
        task: Task to execute, containing APK and configuration.
        tool: Tool implementation for test execution.
        task_storage: Optional storage for persisting task state.

    State:
        self.components: Registered execution components. Empty until
            register_component() is called.
        self.is_initialized: False until execute() runs initialization phase.
        self.performance_data: Populated during execute() with timing metrics.
    """
```

---

## Tier 1 — Dict Return with Schema

Use for: methods returning `Dict[str, Any]` or untyped dicts.

```python
def get_context(self) -> Dict[str, Any]:
    """<Imperative summary.>

    Returns:
        Dictionary with keys:
        - "key_name" (type): Description
        - "other_key" (type): Description
    """
```

**Example**:

```python
def get_task_context(self) -> Dict[str, Any]:
    """Build standard context dictionary for component execution.

    Returns:
        Dictionary with keys:
        - "task_id" (str): Unique task identifier
        - "apk_name" (str): APK file name without extension
        - "tool_name" (str): Tool name with variant (e.g., "monkey:random")
        - "output_dir" (Path): Task-specific output directory
        - "app" (AppInstance): Application instance with package info
    """
```

---

## Tier 2 — Internal Method (summary + Args + Returns)

Use for: protected methods (`_` prefix) with >10 lines.

```python
def _internal_method(self, arg1: Type1) -> ReturnType:
    """<Imperative summary.>

    Args:
        arg1: Description.

    Returns:
        Description.
    """
```

**Example**:

```python
def _initialize_components(self, context: Dict[str, Any]) -> None:
    """Initialize all registered components with shared context.

    Args:
        context: Task execution context from get_task_context().
    """
```

---

## Tier 3 — Trivial Private Method (1-line)

Use for: protected methods ≤10 lines with clear names.

```python
def _publish_task_started_event(self) -> None:
    """Log task execution start."""
```

---

## Skip — Self-Evident (no docstring needed)

Per P1, do not add docstrings to self-evident code:

```python
# No docstring needed — name + type signature are sufficient
@property
def task_id(self) -> str:
    return self.task.id

@property
def is_running(self) -> bool:
    return self._state == State.RUNNING

def __repr__(self) -> str:
    return f"Task({self.task_id})"

def __len__(self) -> int:
    return len(self.items)
```
