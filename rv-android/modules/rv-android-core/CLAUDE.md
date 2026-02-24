# CLAUDE.md - rv-android-core

## Purpose

rv-android-core is the foundational infrastructure module for the RV-Android framework, providing shared domain models, error handling, logging, and utility components used across all other modules. It establishes the architectural patterns and core abstractions that enable modular design, type-safe validation through Pydantic, and consistent behavior across the runtime verification system for Android applications.

## Architecture

### Key Patterns and Design Decisions

- **Singleton Pattern**: Core services (ErrorHandler, LoggingManager) use thread-safe singletons for global access
- **Pydantic Validation**: All domain models inherit from `BaseValidatedModel` for comprehensive validation and serialization
- **Decorator-Based Error Handling**: `@ErrorHandler.handle_errors()` provides Spring-like automatic error management
- **Template Method Pattern**: `AbstractTool` defines execution workflow for all testing tools

### Key Components

| Component | Purpose |
|-----------|---------|
| `ErrorHandler` | Unified error management with type-specific handlers and decorators |
| `LoggingManager` | Centralized logging with context injection and structured formatting |
| `BaseValidatedModel` | Pydantic base class for all validated domain models |
| `Command` | System command execution with timeout and process management |
| `AbstractTool` | Base class defining contract for all testing tools |

## Directory Structure

```
src/rv_android_core/
├── __init__.py
├── constants.py
├── analysis/
│   ├── __init__.py
│   └── base_analyzer.py          # Base class for analysis tools
├── commands/
│   ├── __init__.py
│   ├── command.py                # Command execution with validation
│   ├── command_exception.py
│   ├── command_not_found_error.py
│   └── command_result.py         # Structured command results
├── domain/
│   ├── __init__.py
│   ├── app.py                    # Android application model (APK metadata)
│   ├── classes.py                # Java class/method models
│   ├── dynamic_wtg.py            # Dynamic Window Transition Graph
│   ├── log.py                    # Coverage and error log models
│   ├── static.py                 # Static analysis data models
│   ├── task.py                   # Task configuration and execution models
│   ├── widget.py                 # Android UI widget models
│   └── wtg.py                    # Window Transition Graph models
├── event/
│   ├── __init__.py
│   ├── handler.py                # Event handler with callback and optional filter
│   └── models.py                 # Event types, channels, and event classes
├── tools/
│   ├── __init__.py
│   ├── abstract_tool.py          # Base class for testing tools
│   └── tool_spec.py              # Tool specification model
└── util/
    ├── __init__.py
    ├── decorators.py
    ├── diagnostics.py
    ├── jar_resolver.py           # JAR file resolution
    ├── json_helpers.py
    ├── utils.py
    ├── android/
    │   ├── __init__.py
    │   ├── android.py              # ADB operations (install, uninstall, boot)
    │   ├── emulator_manager.py     # Android emulator control
    │   ├── logcat_manager.py       # Logcat capture management
    │   ├── package_detector.py     # Code package detection (manifest vs implementation)
    │   ├── signature_normalizer.py # Inner class notation normalization (Outer.Inner -> Outer$Inner)
    │   └── repository_initializer.py
    ├── error/
    │   ├── __init__.py
    │   ├── error_handler.py      # Centralized error handling
    │   └── exceptions.py         # Exception hierarchy (~450 lines)
    ├── logging/
    │   ├── __init__.py
    │   ├── constants.py          # Logging constants
    │   ├── context_adapter.py    # Context-aware logging adapter
    │   ├── formatters.py         # JSON and structured formatters
    │   └── manager.py            # LoggingManager singleton
    └── validation/
        ├── __init__.py
        ├── base.py               # BaseValidatedModel
        ├── config.py             # Validation configuration
        └── decorators.py         # @validated_model decorator
```

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `domain/task.py` | Task, TaskConfiguration, TaskResult models | ~920 |
| `event/models.py` | Event types (17), channels, and event classes | ~330 |
| `util/error/error_handler.py` | ErrorHandler with 16 builtin handlers (absorbed/propagated) | ~370 |
| `util/error/exceptions.py` | Exception hierarchy (23 types) | ~195 |
| `util/logging/manager.py` | LoggingManager with context support | ~415 |
| `tools/abstract_tool.py` | AbstractTool base class | ~410 |
| `domain/widget.py` | Widget and WidgetEvent models | ~365 |
| `commands/command.py` | Command execution with validation | ~335 |
| `util/android/package_detector.py` | Detects code package vs manifest package (~27.5% APKs differ) | ~650 |
| `util/android/signature_normalizer.py` | Normalizes inner class notation in Soot signatures | ~350 |
| `util/android/android.py` | ADB operations (install, uninstall, permissions, boot) | ~250 |
| `constants.py` | File extensions, env var names (`EXTENSION_STATIC_ANALYSIS = ".json"`) | ~30 |

## Important: `package_name` vs `code_package`

The `App` model exposes two package properties:
- **`package_name`**: From AndroidManifest.xml. Use for device operations (install, launch, force-stop, monkey `-p` flag)
- **`code_package`**: Detected via `PackageDetector` from APK components. Use for static analysis parsing and class filtering

In ~27.5% of APKs, these differ (e.g., Godot games: manifest=`ir.hsn6.trans`, code=`org.godotengine.godot`). The `code_package` property is lazy-computed and logs a warning on mismatch.

## Dependencies

### Internal (rv-android modules)
- None (this is the core foundation module)

### External
- `pydantic` ^2.9.0 - Data validation and settings management
- `androguard` 3.4.0a1 - Android APK metadata extraction
- `psutil` ^7.0.0 - Process management utilities
- `networkx` ^3.5 - Graph data structures for WTG

## Testing

```bash
cd modules/rv-android-core

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test categories
uv run pytest tests/domain/ -v      # Domain model tests
uv run pytest tests/event/ -v       # Event system tests
uv run pytest tests/util/ -v        # Utility tests
uv run pytest tests/commands/ -v    # Command execution tests
```

## Common Tasks

### Using the Error Handler
```python
from rv_android_core.util.error.error_handler import ErrorHandler

# Decorator-based error handling
@ErrorHandler.handle_errors(component="MyComponent", phase="execution")
def risky_operation():
    # Errors automatically logged and handled
    pass

# Context manager for scoped error handling
with ErrorHandler.get_instance().error_context(component="MyComponent"):
    risky_operation()
```

### Creating Validated Domain Models
```python
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model
from pydantic import Field

@validated_model(['name', 'value'])
class MyModel(BaseValidatedModel):
    name: str = Field(..., description="Model name")
    value: int = Field(default=0, description="Model value")
```

### Using the Logging System
```python
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

logging_manager = LoggingManager.get_instance()
logger = logging_manager.get_logger(
    "my_module.my_class",
    {CONTEXT_COMPONENT: "MyComponent"}
)

# Context-aware logging
with logger.with_context(task_id="123"):
    logger.info("Processing task")
```

### Executing System Commands
```python
from rv_android_core.commands import Command, CommandResult

# Create and execute command with timeout
cmd = Command(command="adb", args=["devices"], timeout=30.0)
result: CommandResult = cmd.invoke()

if result.is_success():
    print(result.get_stdout_text())
```

### Creating Testing Tools
```python
from rv_android_core.tools import AbstractTool, ToolSpec
from rv_android_core.domain.task import Task
from rv_android_core.domain.app import App

class MyTool(AbstractTool):
    def __init__(self):
        super().__init__(
            name="mytool",
            description="My custom testing tool",
            process_pattern="mytool"
        )

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {"default": {"timeout": 300}}

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        return ToolSpec(name="mytool", tool_class=cls)

    def configure(self, config: Dict[str, Any]) -> None:
        self.timeout = config.get("timeout", 300)

    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        # Tool implementation here
        pass
```


## Development Notes

This module is part of the RV-Android uv workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `uv sync` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
uv sync             # Install/update all modules (also removes unused packages)
```

