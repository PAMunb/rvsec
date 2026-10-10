# Module Analysis Reference

Read at Step 1. Contains module sizing rules, the 4 modeling perspectives and their checklists.

---

## Module Sizing

The Step 1 table gives each module's LOC (physical lines), LLOC (logical lines, roughly
statements) and SLOC (source lines without comments/blanks) from `radon raw`, the module's
share of workspace LLOC, and its z-score `z = (LLOC − mean) / sd` with the sample standard
deviation over all workspace members. LLOC is the sizing unit because comments do not count
and a docstring of any length counts as one line, so documentation volume, which varies a
lot between modules here, barely moves it.

| Signal | Reading |
|--------|---------|
| z > 2 (flagged `>2σ`) | Oversized relative to its siblings: check whether it holds more than one functional area (separate packages with no imports between them, distinct actors in the interaction model). If yes, it is a split candidate; if it is one cohesive area, say so and move on |
| share > 20% | Same check even below 2σ: with ~17 modules, one module holding a fifth of the code concentrates change |
| share < 1% | Small. Not a problem by itself: deliberate seams (`rv-instrumentation` as a factory, `rv-instrumentation-core` as an ABC package, thin plugins) are small on purpose. Flag only if the module has no reason to be separate (no distinct dependency set, no separate consumer) |

A z-score is only a comparison inside this workspace, and the distribution is skewed (a few
large modules), so report the number, not a verdict: the recommendation comes from the
functional-area check.

---

## 4 Modeling Perspectives

| Perspective | What it Shows | Key Questions |
|-------------|---------------|---------------|
| **Context** | Module boundaries and environment | What is inside/outside? What triggers execution? |
| **Interaction** | Communication with actors and systems | Who initiates? What use cases? What message sequences? |
| **Structural** | Static organization and relationships | What classes? What patterns? What hierarchies? |
| **Behavioral** | Dynamic behavior during execution | Data-driven or event-driven? What states/flows? |

---

## Context Modeling Checklist

Analyze the module's context and boundaries:

1. **System Boundaries**: What functionality is inside this module? What is delegated to other modules?
2. **Adjacent Modules**: For each rv-android dependency:
   - What data flows between them?
   - What is the direction (depends-on, depended-by, bidirectional)?
3. **External Systems**: What external APIs, services, or hardware does it interact with?
   - Android device (adb), LLM server (HTTP), Java tools of the `rvsec` reactor run as
     subprocesses, and the files exchanged with them (`.mop`, descriptor JSON, `*.apk.json`)
4. **Process Triggers**: What initiates module execution?
   - CLI command, parent module call, event/callback, scheduler

---

## Interaction Modeling Checklist

Identify how the module interacts with actors and systems:

1. **Actors**: Who/what initiates interactions?
   - Human: CLI user, API consumer
   - System: parent module, scheduler, event bus
   - External: Android device, LLM server
2. **Use Cases**: For each discrete task the module supports, document:
   - Actor(s), stimulus, response, error handling
3. **Key Sequences** (for complex interactions only):
   - Trace message flow between components
   - Document alternative paths (error, timeout, retry)

---

## Structural Modeling Checklist

Analyze the static structure:

1. **Key Classes**: Main domain entities and services — name, responsibility, line count
2. **Associations**: Relationships between classes:
   - Dependency (uses), Association (has-a), Aggregation (contains), Composition (owns)
3. **Hierarchies**: Inheritance structures — ABC/Protocol → concrete implementations
4. **Design Patterns**: Recognize and document patterns used:
   - Factory, Strategy, Observer, Decorator, Facade, Registry, Builder, Template Method
5. **Coupling Assessment**: Treat each item as a signal to confirm in code, not as proof.
   - **Internals**: Do classes reach into other classes' private state (`_attr` access from
     outside, `setattr` on another object)?
   - **Direction**: Do dependencies point the way the layers say (see the matrix in
     `rv-analyze-dependencies/reference.md`)? Infrastructure types (subprocess `Command`,
     file paths of another module's outputs, HTTP clients) leaking into the module's domain
     logic is the smell to look for.
   - **Public surface**: Can you list what the module offers others — what its `__init__.py`
     / `__all__` exports — without naming storage details or internal services? If the
     list needs them, the boundary leaks.
   - **Neighbor types**: For each type this module imports from another workspace module, is
     it a type made for callers (exported result model, ABC) or that module's internal
     model/implementation? Rate the relation's strength with **Coupling Beyond Imports** in
     `rv-analyze-dependencies/reference.md` (contract < model < functional < intrusive);
     the same section covers files exchanged with the Java side.

---

## Behavioral Modeling Checklist

Analyze dynamic behavior:

1. **Behavior Type**: Is the module primarily data-driven (pipeline/ETL) or event-driven (state machine)?
2. **For Data-Driven Modules**:
   - Input → Processing steps → Output
   - Data transformations at each stage
   - Error/retry handling in the pipeline
3. **For Event-Driven Modules**:
   - What states can the module be in?
   - What stimuli trigger state transitions?
   - What actions occur on entry/exit/during each state?
4. **Key Scenarios**: Document happy path and top 2-3 error scenarios
5. **Common Patterns**: Pipeline, Request-Response, State Machine, Workflow orchestration

---

## Workspace Modules

Do not keep a copy of the module list here; read it from the sources:
- **Membership**: `[tool.uv.workspace]` in the root `pyproject.toml` (`members` minus
  `exclude`); `python3 .claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py`
  prints each member with its import package names, which do not all start with `rv_`
  (`aperv_tool`, `rvagent_tool`).
- **Roles**: the "Module map" table in the root `CLAUDE.md`, and the module's own `CLAUDE.md`.
- **Layers and allowed dependencies**: `rv-analyze-dependencies/reference.md`.
