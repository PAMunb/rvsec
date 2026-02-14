# Circular Dependency Detection

Patterns and resolution strategies for circular dependencies in Python modules.

## How to Use

1. Build the import graph using static analysis of `import` and `from ... import` statements
2. Run cycle detection (Tarjan's algorithm or DFS) to find strongly connected components
3. Classify each cycle using the categories below
4. Select resolution strategy based on the decision matrix

---

## Detection Method

Build a directed graph where:
- Each node is a Python module (file)
- Each edge is an import relationship (A imports B → edge A→B)

Find cycles using Tarjan's algorithm for strongly connected components (SCCs). Any SCC with 2+ nodes is a circular dependency.

```
For each .py file:
    Parse imports (import X, from X import Y)
    Resolve to absolute module paths
    Add edge: current_file → imported_module

Run Tarjan's SCC algorithm on the graph
Report all components with size > 1
```

## Circular Dependency Categories

### Direct Circle
Module A imports B, module B imports A.

```
A ──imports──► B
B ──imports──► A
```

**Severity**: High. Causes `ImportError` at runtime if both modules use module-level symbols from each other.

### Transitive Circle
A → B → C → A (or longer chains).

```
A ──► B ──► C ──► A
```

**Severity**: Medium. May work at runtime if imports happen in the right order, but fragile.

### Type-Only Circle
Circular import exists only because of type annotations (not runtime usage).

```python
# module_a.py
from __future__ import annotations
from module_b import TypeB  # Only used in type hints

# module_b.py
from __future__ import annotations
from module_a import TypeA  # Only used in type hints
```

**Severity**: Low. Can be resolved with `TYPE_CHECKING` guard.

## Resolution Strategies

### 1. TYPE_CHECKING Guard

**When**: Circle exists only for type annotations, no runtime dependency.

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from module_b import TypeB
```

**Pros**: Minimal code change, no architectural impact.
**Cons**: Only works for type hints, not runtime imports.

### 2. Dependency Inversion

**When**: Two modules have a runtime circular dependency through a concrete class.

Extract an interface/protocol in the lower-level module. The higher-level module depends on the protocol, not the concrete class.

```
Before: A ──► B ──► A
After:  A ──► Protocol (in A or shared)
        B ──► Protocol
```

**Pros**: Clean architectural fix, follows SOLID principles.
**Cons**: Adds a protocol/ABC that must be maintained.

### 3. Extract Common Module

**When**: Both modules share types or utilities that cause the cycle.

Move shared code to a new module that both depend on.

```
Before: A ◄──► B (both need SharedType)
After:  A ──► Common
        B ──► Common
```

**Pros**: Eliminates cycle completely, shared code has a clear home.
**Cons**: New module to maintain; only justified if shared code is substantial.

### 4. Merge Modules

**When**: The circular dependency indicates the two modules are too tightly coupled to exist independently.

Merge into a single module. If the result is too large, split by a different axis.

**Pros**: Simplest fix, acknowledges reality of coupling.
**Cons**: Larger module; may violate single-responsibility if overdone.

### 5. Event-Based Decoupling

**When**: The circular call is a notification pattern (A calls B to notify, B calls A to query).

Replace direct calls with an event/callback mechanism.

**Pros**: Full decoupling, modules become independently testable.
**Cons**: Adds indirection; only justified if modules truly should be independent. Avoid if only one subscriber exists (P1: direct call > event bus with one subscriber).

### 6. Lazy Import

**When**: Quick fix needed; architectural change deferred.

Move the import inside the function that uses it.

```python
def process():
    from module_b import helper  # Lazy import
    return helper()
```

**Pros**: Immediate fix, no structural change.
**Cons**: Hides the dependency, makes it invisible to static analysis. Use only as a temporary measure.

## Decision Matrix

| Circle Type | First Choice | Second Choice | Avoid |
|------------|-------------|---------------|-------|
| Type-only | TYPE_CHECKING guard | Dependency Inversion | Lazy Import |
| Direct (2 modules, shared types) | Extract Common | Merge Modules | Event Decoupling |
| Direct (2 modules, call cycle) | Dependency Inversion | Merge Modules | Lazy Import |
| Transitive (3+ modules) | Extract Common | Dependency Inversion | Merge all |
| Tight coupling (many shared symbols) | Merge Modules | Extract Common | Lazy Import |

## rv-android Specific Notes

- **rv-platform ↔ rv-tools**: ToolFactory in rv-tools creates tool instances that reference platform types. Resolved via protocol in rv-android-core.
- **rv-agent internal**: Agent nodes may reference each other through the shared state object. This is not a circular dependency — the state object is the mediator.
- **Module boundaries**: Defined by `pyproject.toml` dependencies. If a cycle appears in pyproject.toml, it is a hard architectural issue. If it appears only in runtime imports within a module, it is a code organization issue.
