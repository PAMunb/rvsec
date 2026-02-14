# False Positive Patterns

Patterns where code appears dead but is actually used through dynamic dispatch, framework conventions, or indirect references. Check these before recommending removal.

## How to Use

1. Before classifying any code as dead, scan this checklist for matching patterns
2. If the code matches a pattern below, mark it as "alive (dynamic)" and explain why
3. If uncertain, recommend investigation rather than removal
4. Include the matched pattern name in your analysis report

---

## Dynamic Import Patterns

### importlib / __import__

Code loaded at runtime via `importlib.import_module()` or `__import__()`. The module name may be constructed from variables, making static analysis blind to the dependency.

**Detection**: Search for `importlib.import_module`, `__import__`, and `importlib.util.spec_from_file_location` in the codebase. Trace the module name argument to see which modules could be loaded.

### Plugin Discovery

Modules discovered by scanning a directory or package at runtime. Common in plugin architectures.

```python
for module in pkgutil.iter_modules(package.__path__):
    importlib.import_module(f"{package.__name__}.{module.name}")
```

**Detection**: Search for `pkgutil.iter_modules`, `importlib.import_module` in loops.

## Registry and Factory Patterns

### Decorator-Based Registration

Classes or functions registered via decorator. The decorator call is the only "usage" — no direct import at the call site.

```python
@tool_registry.register("monkey")
class MonkeyTool:
    ...
```

**Detection**: Search for `@register`, `@registry`, or any decorator that adds to a collection. The decorated symbol IS used — through the registry.

### Metaclass Registration

Classes auto-registered by their metaclass upon definition.

**Detection**: Check if the class inherits from a base with a custom `__init_subclass__` or metaclass that registers subclasses.

## String-Based Dispatch

### getattr / globals

Functions called via `getattr(obj, method_name)()` or `globals()[name]()`. The function name is a string, invisible to static import analysis.

**Detection**: Search for `getattr(`, `globals()[`, `locals()[` patterns. If a function name matches a string used in dispatch, it is alive.

### Dictionary Dispatch

Functions stored in a dictionary and called by key.

```python
handlers = {"start": handle_start, "stop": handle_stop}
handlers[action]()
```

**Detection**: Search for dictionaries whose values are function references.

## Framework Entry Points

### pyproject.toml Scripts

Functions referenced in `[project.scripts]` are entry points that may not be imported anywhere in the codebase.

**Detection**: Check `pyproject.toml` for `[project.scripts]` entries.

### Click/Typer Commands

CLI commands defined with `@click.command()` or `@app.command()`. The framework calls them, not user code.

**Detection**: Search for `@click.command`, `@click.group`, `@app.command`.

## Test Infrastructure

### conftest.py Fixtures

Fixtures defined in `conftest.py` are auto-discovered by pytest. They may not be imported anywhere explicitly.

**Detection**: Any function decorated with `@pytest.fixture` in a `conftest.py` file is alive.

### Parametrize Indirect

Test parameters that reference fixture names as strings.

```python
@pytest.mark.parametrize("fixture_name", [...], indirect=True)
```

**Detection**: Search for `indirect=True` in parametrize decorators.

## Pydantic and Dataclass Validators

### field_validator / model_validator

Methods decorated with `@field_validator` or `@model_validator` are called by the Pydantic framework, not user code.

```python
@field_validator("email")
@classmethod
def validate_email(cls, v):
    ...
```

**Detection**: Search for `@field_validator`, `@model_validator`, `@validator` (v1).

### __post_init__

Dataclass `__post_init__` methods are called automatically after `__init__`.

**Detection**: Any `__post_init__` method in a `@dataclass` class is alive.

## Module-Level Exports

### __all__

Symbols listed in `__all__` are part of the public API even if not imported within the same package.

**Detection**: Check if the symbol appears in the module's `__all__` list.

## Abstract Methods

Methods defined in abstract base classes with `@abstractmethod`. They exist to be overridden, not called directly.

**Detection**: Check for `@abstractmethod` decorator. The method is alive if any concrete subclass exists.

## Signal Handlers and Callbacks

### Event Callbacks

Functions registered as callbacks via `signal.signal()`, `atexit.register()`, or framework-specific event systems.

**Detection**: Search for `signal.signal`, `atexit.register`, `.connect(`, `.subscribe(`.

## rv-android Specific Patterns

| Pattern | Location | Why It Looks Dead |
|---------|----------|------------------|
| ErrorHandler decorators | rv-android-core | `@error_handler` wraps functions; the decorator is the caller |
| TaskExecutor component lifecycle | rv-platform | `initialize()`, `cleanup()` called by framework, not user code |
| ToolFactory registration | rv-tools | Tools registered by name string, instantiated via factory |
| LangGraph node functions | rv-agent | Nodes registered in graph builder, called by LangGraph runtime |
| Strategy pattern implementations | rv-agent | Strategies selected at runtime based on configuration |

**Rule**: If in doubt, mark as "investigate" rather than "dead". False removal is worse than false retention.
