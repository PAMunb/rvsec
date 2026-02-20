# Dead Code Analysis Reference

Consolidated reference for module-scoped dead code analysis. Contains categories, false-positive patterns, and removal guidelines.

---

## Dead Code Categories

| # | Category | Priority | Detection | Action |
|---|----------|----------|-----------|--------|
| 1 | Unreachable code (after return/raise, `if False:`) | P1 | pyflakes, vulture | Remove immediately |
| 2 | Unused imports | P1 | pyflakes F401, vulture | Remove immediately (check `__all__`, re-exports, TYPE_CHECKING) |
| 3 | Unused functions/methods | P2 | vulture + cross-ref Grep | Remove after verifying no dynamic callers |
| 4 | Unused variables | P2 | pyflakes, vulture | Remove after confirming no side effects in assignment |
| 5 | Unused classes | P2 | vulture + cross-ref Grep | Remove after checking factories/registries |
| 6 | Commented-out code (3+ lines) | P1 | LLM pattern match | Remove immediately (VCS preserves history) |
| 7 | Redundant code (duplicate logic, passthrough wrappers) | P3 | LLM analysis | Investigate before removing |
| 8 | Obsolete feature flags (always-on/always-off) | P3 | Grep for flag usage | Investigate, then inline active branch |

**Priority**: P1 = remove immediately (zero risk), P2 = remove after dynamic usage search (low risk), P3 = investigate first (medium risk).

---

## False Positive Patterns

Before classifying code as dead, check these — code may be alive through:

### Dynamic Dispatch
- `getattr()`, `globals()[]`, `locals()[]` — function names as strings
- Dictionary dispatch: `handlers = {"start": handle_start}`
- `importlib.import_module()`, `__import__()` — runtime module loading
- `pkgutil.iter_modules()` — plugin discovery

### Framework Entry Points
- `@click.command`, `@click.group`, `@app.command` — CLI commands
- `@pytest.fixture` in `conftest.py` — auto-discovered by pytest
- `@abstractmethod` — exists to be overridden
- `@field_validator`, `@model_validator` — Pydantic validators
- `__post_init__` — dataclass lifecycle
- `signal.signal()`, `atexit.register()` — signal handlers

### Registries and Exports
- `@register`, `@registry` — decorator-based registration
- `__init_subclass__` metaclass registration
- `__all__` list — public API exports
- `pyproject.toml [project.scripts]` — CLI entry points

### rv-android Specific
- `@error_handler` decorators (rv-android-core)
- TaskExecutor component lifecycle: `initialize()`, `cleanup()` (rv-platform)
- ToolFactory: tools registered by name string (rv-tools)
- LangGraph nodes: registered in graph builder (rv-agent)
- Strategy pattern: selected at runtime by config (rv-agent)

**Rule**: If uncertain, mark as "investigate" — false removal is worse than false retention.

---

## Removal Guidelines

1. **One commit per category**: Group removals for clean git history
2. **Grep after removal**: Search for dangling references to deleted names
3. **Run tests**: Full test suite after each removal batch
4. **Update docs**: Remove references from CLAUDE.md, architecture.md
