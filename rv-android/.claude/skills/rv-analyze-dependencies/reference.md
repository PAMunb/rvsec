# Dependency Analysis Reference

Consolidated reference for module dependency analysis. Contains allowed dependency matrix, health metrics, and circular dependency resolution.

---

## rv-android Dependency Layers

```
Layer 1 (Foundation):  rv-android-core
Layer 2 (Utilities):   rv-tools, rv-uiautomator, rv-screen-parser
Layer 3 (Analysis):    rv-static-analysis, rv-coverage, rv-monitor-generator
Layer 4 (Execution):   rv-agent, rv-instrumentation, rv-platform
Layer 5 (Experiment):  rv-experiment, rvagent-tool, aperv-tool
```

**Rule**: A module may depend on modules above it in this diagram but never on modules below it or at the same level (unless explicitly documented).

## Allowed Dependency Matrix

| Module | May Depend On |
|--------|--------------|
| rv-android-core | (none — foundation) |
| rv-tools | rv-android-core |
| rv-uiautomator | rv-android-core |
| rv-screen-parser | rv-android-core |
| rv-static-analysis | rv-android-core |
| rv-coverage | rv-android-core |
| rv-monitor-generator | rv-android-core |
| rv-platform | rv-android-core, rv-tools |
| rv-agent | rv-android-core, rv-tools, rv-uiautomator, rv-screen-parser |
| rv-instrumentation | rv-android-core, rv-monitor-generator |
| rv-experiment | rv-android-core, rv-platform, rv-tools |
| rvagent-tool | rv-android-core, rv-agent, rv-tools |
| aperv-tool | rv-android-core, rv-tools |

Any dependency not in this matrix is a **violation**.

---

## Health Metrics

### Fan-In / Fan-Out

| Metric | Definition | Healthy Range |
|--------|-----------|---------------|
| Fan-in (Ca) | Modules that depend on this one | High OK for abstractions (rv-android-core: 11+) |
| Fan-out (Ce) | Modules this one depends on | ≤ 5 for most modules |

### Instability: I = Ce / (Ca + Ce)

| Range | Category | Meaning |
|-------|----------|---------|
| 0.0–0.3 | Stable | Many depend on it; hard to change |
| 0.3–0.7 | Balanced | Moderate coupling |
| 0.7–1.0 | Unstable | Few depend on it; easy to change |

**SDP (Stable Dependencies Principle)**: Depend only on modules more stable than yourself.

### Dependency Depth

| Depth | Category | Action |
|-------|----------|--------|
| 1–3 | OK | Normal for modular architecture |
| 4 | Warning | Review intermediate modules |
| 5+ | Must refactor | Introduce facade or merge |

---

## Circular Dependency Detection

### Categories

| Type | Pattern | Severity | First Resolution |
|------|---------|----------|------------------|
| Type-only | Circular imports only in type hints | Low | `TYPE_CHECKING` guard |
| Direct | A imports B, B imports A (runtime) | High | Dependency Inversion or Extract Common |
| Transitive | A → B → C → A | Medium | Extract Common module |

### Resolution Strategies

1. **TYPE_CHECKING guard**: Move type-only imports under `if TYPE_CHECKING:`. Minimal change, no architectural impact.
2. **Dependency Inversion**: Extract protocol/ABC in lower-level module. Higher module depends on protocol, not concrete class.
3. **Extract Common Module**: Move shared types to a new module both depend on.
4. **Merge Modules**: When two modules are too tightly coupled to exist independently.
5. **Lazy Import**: Move import inside function. Temporary measure only — hides dependency from static analysis.

### rv-android Specific

- **rv-platform ↔ rv-tools**: Resolved via protocol in rv-android-core
- **rv-agent internal nodes**: Share state object (mediator pattern, not circular)
- **Module boundaries**: `pyproject.toml` cycles = architectural issue; runtime-only cycles = code organization issue
