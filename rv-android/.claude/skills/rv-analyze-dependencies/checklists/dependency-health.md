# Dependency Health

Health metrics for evaluating module dependency graphs. Use to classify dependency relationships as healthy, concerning, or problematic.

## How to Use

1. Build the dependency graph from `pyproject.toml` and import analysis
2. Compute the metrics below for each module
3. Flag violations of direction rules and threshold breaches
4. Report health assessment with specific metrics and recommended actions

---

## rv-android Dependency Direction Rules

Dependencies must flow in one direction. Reverse dependencies create coupling that prevents independent development and testing.

```
rv-android-core (foundation)
    ↓
rv-tools, rv-uiautomator (shared components)
    ↓
rv-platform, rv-static-analysis, rv-coverage, rv-screen-parser (services)
    ↓
rv-agent, rv-instrumentation, rv-monitor-generator (consumers)
    ↓
rv-experiment, rv-agent-validation (orchestration)
```

**Rule**: A module may depend on modules above it in this diagram but never on modules below it or at the same level (unless explicitly documented).

## Allowed Dependency Matrix

| Module | May Depend On |
|--------|--------------|
| rv-android-core | (none — foundation) |
| rv-tools | rv-android-core |
| rv-uiautomator | rv-android-core |
| rv-platform | rv-android-core, rv-tools |
| rv-static-analysis | rv-android-core |
| rv-coverage | rv-android-core |
| rv-screen-parser | rv-android-core |
| rv-agent | rv-android-core, rv-tools, rv-uiautomator, rv-screen-parser |
| rv-instrumentation | rv-android-core, rv-monitor-generator |
| rv-monitor-generator | rv-android-core |
| rv-experiment | rv-android-core, rv-platform, rv-tools |
| rv-agent-validation | rv-android-core, rv-agent, rv-experiment |

Any dependency not in this matrix is a violation. Report with: source module, target module, import path.

## Fan-In / Fan-Out Analysis

| Metric | Definition | Healthy Range | Interpretation |
|--------|-----------|---------------|----------------|
| Fan-in (Ca) | Number of modules that depend on this one | High is OK for abstractions | High fan-in = must be stable and abstract |
| Fan-out (Ce) | Number of modules this one depends on | ≤ 5 for most modules | High fan-out = fragile, breaks when dependencies change |

**Expected fan-in for rv-android:**
- rv-android-core: 11 (all modules) — this is correct, it is the foundation
- rv-tools: 3–4 — shared by platform, agent, experiment
- Others: 0–2 — specialized modules

## Instability Metric

**I = Ce / (Ca + Ce)**

| Range | Category | Meaning |
|-------|----------|---------|
| 0.0–0.3 | Stable | Hard to change; many modules depend on it |
| 0.3–0.7 | Balanced | Moderate coupling |
| 0.7–1.0 | Unstable | Easy to change; depends on many, few depend on it |

**Stable Dependencies Principle (SDP)**: A module should only depend on modules more stable than itself. If module A (I=0.8) depends on module B (I=0.3), that is correct. If A (I=0.3) depends on B (I=0.8), the dependency is fragile.

## Abstractness Metric

**A = abstract types / total types**

Where "abstract types" includes: abstract classes, protocols, ABCs, interfaces.

| Range | Category |
|-------|----------|
| 0.0–0.3 | Concrete (implementation-heavy) |
| 0.3–0.7 | Balanced |
| 0.7–1.0 | Abstract (contract-heavy) |

## Distance from Main Sequence

**D = |A + I − 1|**

Measures how well a module balances abstractness and stability.

| Range | Category | Action |
|-------|----------|--------|
| 0.0–0.2 | Ideal | On the main sequence |
| 0.2–0.4 | Acceptable | Minor imbalance |
| 0.4+ | Problematic | Too concrete and stable (Zone of Pain) or too abstract and unstable (Zone of Uselessness) |

## Dependency Depth

Maximum chain length from any module to a leaf dependency.

| Depth | Category | Action |
|-------|----------|--------|
| 1–3 | OK | Normal for modular architecture |
| 4 | Warning | Review if intermediate modules add value |
| 5+ | Must refactor | Introduce facade or merge intermediate modules |

## Robert C. Martin Package Coupling Principles

| Principle | Rule | Violation Indicator |
|-----------|------|-------------------|
| ADP (Acyclic Dependencies) | No cycles in the dependency graph | Tarjan's algorithm finds a strongly connected component |
| SDP (Stable Dependencies) | Depend in the direction of stability | Module with I=0.3 depends on module with I=0.8 |
| SAP (Stable Abstractions) | Stable packages should be abstract | Module with I=0.2 and A=0.1 (concrete and stable = Zone of Pain) |
