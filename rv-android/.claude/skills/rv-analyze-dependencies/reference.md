# Dependency Analysis Reference

Read **Layers and Allowed Matrix** and **Health Metrics** at Step 1. Read **Coupling Beyond
Imports** at Step 4, and whenever another skill (e.g. `/rv-impact-analyzer`) asks you to weigh
a relation by strength, distance and volatility.

---

## Layers and Allowed Matrix

The layers are derived from the `[project].dependencies` of each `modules/*/pyproject.toml`
and the module map in the root `CLAUDE.md`. A module sits one layer above the highest module
it is allowed to depend on.

```
L0 Foundation       rv-android-core
L1 Services         rv-tools, rv-screen-parser, rv-static-analysis, rv-coverage,
                    rv-monitor-generator, rv-instrumentation-core
L2 Specializations  rv-uiautomator, rv-instrumentation-ajc, rv-instrumentation-dexlib2
L3 Facades/agents   rv-instrumentation (variant factory), rv-agent
L4 Tool plugins     rvagent-tool, aperv-tool (AbstractTool implementations for rv-tools)
L5 Platform         rv-platform (composition root: registers the L4 plugins)
L6 Orchestration    rv-experiment
--  Temporary       aperv-llm-validation (outside the production set)
```

The matrix is the authority; the layers explain it. Any edge — declared or imported — that is
not in its module's row is a **violation**.

| Module | May depend on | Why |
|--------|---------------|-----|
| rv-android-core | (none) | Foundation; `AbstractTool`, domain models, `ErrorHandler` live here |
| rv-tools | rv-android-core | Tool registry + builtin tools |
| rv-screen-parser | rv-android-core | |
| rv-static-analysis | rv-android-core | |
| rv-coverage | rv-android-core | |
| rv-monitor-generator | rv-android-core | |
| rv-instrumentation-core | rv-android-core | `Instrumenter` ABC + result types; no variant deps, so no cycle |
| rv-uiautomator | rv-android-core, rv-screen-parser | |
| rv-instrumentation-ajc | rv-android-core, rv-instrumentation-core | Variant knows only the core ABC |
| rv-instrumentation-dexlib2 | rv-android-core, rv-instrumentation-core | Variant knows only the core ABC |
| rv-instrumentation | rv-instrumentation-core, rv-instrumentation-ajc, rv-instrumentation-dexlib2 | `get_instrumenter()` factory, re-exports the core API |
| rv-agent | rv-android-core, rv-screen-parser, rv-uiautomator, rv-static-analysis | |
| rvagent-tool | rv-android-core, rv-tools, rv-agent | Plugin wrapping rv-agent |
| aperv-tool | rv-android-core, rv-tools | Plugin wrapping `ape-rv.jar` |
| rv-platform | rv-android-core, rv-tools, rv-coverage, rv-static-analysis, rvagent-tool, aperv-tool | Registers the plugins at import (`rv_platform/__init__.py`) |
| rv-experiment | rv-android-core, rv-tools, rv-coverage, rv-static-analysis, rv-screen-parser, rv-monitor-generator, rv-instrumentation, rv-instrumentation-ajc, rv-instrumentation-dexlib2, rv-platform | Pre-processing drives generation + instrumentation; reads the variant configs directly |
| aperv-llm-validation | rv-android-core | Temporary; excluded from findings unless asked |

When a pyproject legitimately gains a dependency, update this table in the same change.

---

## Health Metrics

### Fan-in / fan-out

| Metric | Definition | Healthy range |
|--------|-----------|---------------|
| Ca (fan-in) | Workspace modules declaring a dependency on this one | High is fine for L0/L1 |
| Ce (fan-out) | Workspace modules this one declares | ≤ 5, except the L6 orchestrator |

### Instability I = Ce / (Ca + Ce)

| Range | Category | Meaning |
|-------|----------|---------|
| 0.0–0.3 | Stable | Many depend on it; changes ripple |
| 0.3–0.7 | Balanced | |
| 0.7–1.0 | Unstable | Few depend on it; cheap to change |

**Stable Dependencies Principle (SDP)**: every edge A → B should satisfy `I(B) < I(A)`.
The script prints the edges where it fails. A violation means a module that others rely on
(low I) is tied to one that churns (high I). Typical fixes: move the needed type down to the
stable side, or invert the edge through an ABC in a lower layer. Leaf-to-leaf edges between
two unstable modules (both I ≥ 0.7) are low severity.

### Dependency depth (longest declared chain)

| Depth | Category | Action |
|-------|----------|--------|
| 1–3 | OK | |
| 4–5 | Warning | Review intermediate modules |
| 6+ | Refactor | Only the L6 orchestrator may sit here |

---

## Circular Dependencies

| Type | Pattern | Severity | First resolution |
|------|---------|----------|------------------|
| Type-only | All edges of the cycle tagged `type` | Low | Keep under `TYPE_CHECKING` |
| Lazy | Cycle closed by a `lazy` import (inside a function) | Medium | The import hides a real dependency: move the needed code to the lower module or invert via an ABC |
| Direct | Two `top` imports, A ↔ B | High | Dependency inversion or extract common |
| Transitive | A → B → C → A | Medium | Extract common |

Resolution strategies, cheapest first: `TYPE_CHECKING` guard (type-only) · dependency
inversion (ABC/Protocol in the lower module) · extract the shared types to a lower module ·
merge the two modules. A lazy import is not a resolution: it hides the edge from the import
graph, not from the architecture.

---

## Coupling Beyond Imports

An import edge says that two modules are coupled, not how much. Rate every relation on three
axes, then diagnose with the table at the end. The relations to rate are: import edges with a
Step 3 finding, every data contract below, and every co-change pair with share ≥ 50% that has
no import edge.

### Strength — what the consumer has to know

| Level | Name | Meaning | Python / file signals |
|-------|------|---------|----------------------|
| 1 (weakest) | **Contract** | Consumer sees a structure built for integration, separate from the producer's internals | Imports only types re-exported in the producer's `__init__.py` / `__all__`; Pydantic result models made for callers (`rv_instrumentation_core` result types); a file format with a schema, version field, or a test that pins it |
| 2 | **Model** | Consumer uses the producer's own domain model or raw document shape | Imports from `<pkg>.domain`, `<pkg>.models`; reads a JSON by literal key names (`data["targetDistances"]`); parses a log line format the producer writes |
| 3 | **Functional** | Consumer must know what the producer does, not just what it returns | Call order that must be respected (generate monitors → instrument → run); the same rule restated in two places (a grammar or constant copied instead of imported); docstrings like "must match X in Y"; a flag the producer must be given for the consumer to work (`emit_descriptor=True`) |
| 4 (strongest) | **Intrusive** | Consumer depends on internals never meant for integration | Imports `_private` names or non-exported submodules; `monkeypatch`/`setattr` on another module outside tests; reads another module's output directory layout or internal file names; reflection or regex over another component's source |

Functional coupling is the one the import graph cannot see at all: a rule duplicated in two
modules couples them even with zero imports. Co-change is how it shows up.

### Distance — how far the change has to travel

| Distance | Boundary | Example |
|----------|----------|---------|
| Low | Same uv module | Two packages inside `rv_agent` |
| Medium | Different uv module, same Python process | `rv_platform` → `rv_coverage` |
| High | Process or language boundary | Python ↔ Java subprocess of the `rvsec` reactor (GATOR, JavaMOP, dexlib2 weaver, AJC); container (Docker image of a campaign); HTTP to the LLM server; `adb` to the emulator |

High distance means the two sides are built, versioned and deployed separately: a Java jar is
handed to `rv-android/lib/` by the reactor build, so a mismatch shows up only at run time.

### Volatility — how often the relation is exercised by change

Measured, not guessed: `scripts/cochange.sh` (the Step 4 command) counts commits that touched
the source of both units, Python modules and the Java modules of the parent `rvsec` repo alike.

| Level | Signal |
|-------|--------|
| High | ≥ 5 co-changes in the window, or share ≥ 50% |
| Low | < 3 co-changes and share < 30% |
| Medium | otherwise |

A high-share pair with no import edge is undeclared functional coupling until proven
otherwise: read two or three of the commits (`git log --format='%h %s' -- <path-a> <path-b>`)
and name the shared rule.

### Known data contracts across languages

Confirm each against the Step 4 grep (producer and consumer still reference it) and look for
new ones in the same output.

| Artifact | Producer | Consumers | What to check |
|----------|----------|-----------|---------------|
| JavaMOP JSON descriptors (`descriptor_glob` in `monitor_output_dir`) | JavaMOP (Java, `javamop/`), driven by rv-monitor-generator with the descriptor flag | rv-instrumentation-dexlib2 → the Java dexlib2 weaver (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2`) | Python only globs and passes the files; the shape is pinned by Jackson on the Java side. Strength is at least functional (the generator must emit them) |
| GATOR analysis document `<apk>.apk.json` | rvsec-gator (Java, `rvsec/rvsec-android/rvsec-gator`) via rv-static-analysis | rv-static-analysis, aperv-tool (`analysis/static_artifact.py`; `tools/aperv/tool.py` derives the MOP artifact from it), rv-experiment (presence check in pre-processing) | Which keys each consumer reads by name; whether the compact and full forms are both handled |
| `.mop` specifications | spec sets under `rvsec/rvsec-mop/src/main/resources/` | rv-monitor-generator (to JavaMOP), rv-experiment (spec-set selection), aperv-tool (MOP artifact derivation), rv-instrumentation-dexlib2 | File names and spec names used as keys across modules |
| Tool jars (`ape-rv.jar`, `instr-cli.jar`, GATOR, frame computer) | `rvsec` reactor build, copied into `rv-android/lib/` or a module's own `lib/` | aperv-tool, rv-instrumentation-*, rv-static-analysis, rv-tools builtins | CLI flags and exit codes the Python side relies on |
| Logcat line formats | instrumented app (Java monitors) | rv-coverage parsers, aperv-tool analysis | Grammar restated instead of shared (symmetric functional coupling) |

### Diagnosis

Rate each axis High or Low (Medium counts as High for strength ≥ functional, Low otherwise).

| Strength | Distance | Volatility | Diagnosis | Action |
|----------|----------|------------|-----------|--------|
| High | High | High | **Critical** — far apart, tightly bound, changing often | Introduce a versioned contract (schema + pinning test on both sides) or move the logic to one side |
| High | High | Low | Acceptable — tight but frozen (e.g. a stable jar CLI) | Pin it with a test so the freeze is checked |
| High | Low | any | Good — cohesion: things that change together live together | None |
| Low | High | any | Good — loose coupling across a boundary | None |
| Low | Low | High | **Attention** — weak link inside one module that changes a lot: unrelated things share a home | Consider splitting |
| Low | Low | Low | Acceptable — noise | None |

Report the rating of each axis with its evidence (file:line for strength, the boundary for
distance, the co-change count and share for volatility).
