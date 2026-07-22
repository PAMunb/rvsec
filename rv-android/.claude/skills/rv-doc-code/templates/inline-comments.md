# Inline Comment Patterns

Conventions for inline comments in RV-Android Python code.

---

## Section Dividers

Use in constants and configuration files to group related values.

**Format**: `# === LABEL ===` (all caps label, spaces around `===`)

```python
# === EMULATOR CONFIGURATION ===
EMULATOR_BOOT_TIMEOUT = 120
EMULATOR_WAIT_INTERVAL = 5
EMULATOR_MAX_RETRIES = 3

# === COVERAGE CONSTANTS ===
COVERAGE_LOG_TAG = "RVSEC-COV"
COVERAGE_FLUSH_INTERVAL = 30

# === TOOL DEFAULTS ===
DEFAULT_TIMEOUT = 300
DEFAULT_EVENTS = 5000
```

**When to use**: Constants files, large configuration blocks, module-level variable groups.

**When NOT to use**: Inside functions (use Phase/Step markers instead).

---

## Phase Markers

Use in orchestration code (controllers, executors, coordinators) to mark execution phases.

**Format**: `# Phase N: <description>`

```python
def execute(self):
    # Phase 1: Initialize components with shared context
    context = self.get_task_context()
    self._initialize_components(context)

    # Phase 2: Coordinated execution with emulator lifecycle
    self._start_emulator()
    self._execute_coordinated_components(context)

    # Phase 3: Cleanup and result collection
    self._stop_emulator()
    self._collect_results()
```

**When to use**: Methods that coordinate multiple subsystems in sequence. The method reads like a narrative of the execution flow.

**When NOT to use**: Simple methods with 2-3 lines. Methods that are purely algorithmic (use Step markers).

---

## Step Markers

Use in algorithmic code with sequential processing steps.

**Format**: `# Step N: <description>`

```python
def detect_package(self, apk):
    # Step 1: Extract manifest package and component list
    manifest_package = apk.get_package()
    components = self._extract_components(apk)

    # Step 2: Filter framework components (androidx, android.*)
    app_components = [c for c in components if not self.is_framework(c)]

    # Step 3: Apply detection heuristics in priority order
    result = self._apply_heuristics(manifest_package, app_components)

    # Step 4: Validate and return result with confidence score
    return self._validate_result(result)
```

**When to use**: Algorithms, data processing pipelines, multi-step computations.

**When NOT to use**: Orchestration code (use Phase markers). Simple sequential code where each step is self-evident.

---

## WHY Blocks

Use before complex or non-obvious operations to explain rationale.

**Format**: Multi-line `#` comments, placed BEFORE the code they explain.

```python
# The manifest package can differ from the actual code package in apps
# using build flavors or game engines (e.g., Unity uses com.unity3d.*
# internally but the manifest declares the publisher's package).
# We resolve this by analyzing component declarations.
if manifest_package != detected_package:
    result = self._resolve_discrepancy(manifest_package, detected_package)
```

```python
# SGLang lacks official tool calling support for Qwen3-VL, with native
# tool calls succeeding only ~50% of the time. We try native first and
# fall back to XML/JSON parsing, achieving 100% combined success rate.
try:
    response = self._native_tool_call(messages)
except ToolCallParseError:
    response = self._fallback_xml_parse(messages)
```

**Rules**:
- Explain WHY, not WHAT
- Place BEFORE the code, not after
- No blank lines within a WHY block
- Multi-line for complex reasoning

---

## TODO/FIXME Format

**Format**: `# TODO(context): description` or `# FIXME(context): description`

Context is a module name, issue number, or topic in parentheses.

```python
# TODO(rv-agent): Add retry logic for LLM timeout responses
# TODO(#42): Support parallel emulator execution
# FIXME(rv-coverage): Coverage flush may miss events during rapid transitions
# TODO(performance): Cache similarity scores to avoid recomputation
```

**Rules**:
- Always include context in parentheses
- Description starts with a verb (imperative mood)
- No bare `# TODO:` or `# FIXME:` without context

---

## Logical Block Dividers

Use `# ---` to separate logical blocks within a long method when Phase/Step markers are not appropriate.

```python
def configure(self, config):
    self.timeout = config.get("timeout", DEFAULT_TIMEOUT)
    self.retries = config.get("retries", DEFAULT_RETRIES)

    # ---

    self.emulator = EmulatorManager(self.timeout)
    self.coverage = CoverageTracker(self.config)
```

**When to use**: Sparingly, when a method has distinct logical groups that don't merit Phase/Step labels.

---

## When NOT to Comment

Per P1 (Simplicity), do not add comments that restate the code.

```python
# BAD — restates the code
# Check if the list is empty
if not items:
    return []

# BAD — obvious from the code
# Set timeout to 30 seconds
timeout = 30

# BAD — type information belongs in signatures
# result is a string
result = process(data)
```

```python
# GOOD — explains WHY
# Empty component list means the APK contains only framework code
# (e.g., test stubs) — fall back to manifest package
if not items:
    return PackageDetectionResult(manifest_package=pkg, ...)

# GOOD — explains a non-obvious value
# 30s matches the emulator boot timeout to avoid premature failures
timeout = 30
```
