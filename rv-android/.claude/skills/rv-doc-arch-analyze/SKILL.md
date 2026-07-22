---
name: rv-doc-arch-analyze
description: >-
  Analyze a target (system, module, or subsystem) and produce architecture-model.json
  for Views-and-Beyond documentation. Use as the first phase of /rv-doc-arch. Handles
  Python (reuses rv-analyze-*) and Java/Maven (generic structural analysis) targets.
  Do NOT use to write the final document — that is /rv-doc-arch-generate.
argument-hint: [system | module:<name> | subsystem:<name>]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, Skill
---

# Analyze Architecture: $ARGUMENTS

Analyzes the target and writes `out/arch/<target-slug>/architecture-model.json`, the
file-based intermediate consumed by `rv-doc-arch-generate`. This phase replaces the Neo4j
graph used by the upstream `agente-documentador` suite: there is no database, the model is
a single JSON file, and analysis runs once before generation.

## Supporting Files

- `reference/model-schema.md` — the exact schema of `architecture-model.json`. **Read it
  first.** Your output must conform to it.
- `../rv-doc-arch/reference/views-and-beyond.md` — the method (view categories, styles,
  stakeholder→view selection). Use it to fill `styles`, `views_selected`, `views_excluded`.

## Argument

`$ARGUMENTS` is a target spec:
- `system` — the whole RV-Android workspace (the 16 modules).
- `module:<name>` — one module, e.g. `module:rv-agent`.
- `subsystem:<name>` — a named subsystem from `../rv-doc-arch/subsystems.yaml`, which may
  span multiple modules and **multiple languages/trees** (e.g. `subsystem:instrumentation`).

## Why two collectors

`rv-analyze-*` skills are Python-specific (radon, pyflakes, vulture, pyproject.toml). Some
targets include non-Python code (e.g. the instrumentation subsystem has a large Java/Maven
backend at `../rvsec/rvsec-android/rvsec-instrumentation-dexlib2`). Analysis therefore uses:

- **Python collector** — reuse existing skills (rich: structure, deps, patterns, smells).
- **Generic collector** — structural-only via Read/Grep/Glob + build-file parsing, for
  Java/Maven and any other language. No metrics that need a foreign toolchain.

Both normalize into the same `architecture-model.json` schema, so generation is language-agnostic.

## Documentation Guidelines

1. **Language**: English only.
2. **Evidence-based**: every style/decision/NFR entry needs concrete evidence (a file, a
   class, a build rule). Omit what you cannot substantiate — do not speculate.
3. **Current state only**: describe what exists now, not history.

## Depth requirement (this is the whole point)

The final document must read as **narrative onboarding for a new engineer** with no prior
exposure to the target — it explains *what* the subsystem does, *how* (with a concrete worked
example), and *why* (CLAUDE.md P2). The generator only renders; it does not re-analyze. So the
depth must originate **here**. The model's narrative fields (`primer`, `walkthrough`,
`modules[].how_it_works` / `.why_separate` / `.gotchas`, `components[].narrative`,
`decisions[].narrative`, `nfrs[].support`, `scenarios[]`) are **paragraphs of prose**, not
labels. A one-sentence `how_it_works` is a defect. Write full sentences, explain reasons
inline, and pin claims to concrete class/file/value names. See `reference/model-schema.md`.

## Workflow

```
STEP 1: RESOLVE TARGET ──────────────────────────────────────────►
    │  Expand $ARGUMENTS into a list of (path, language) units
    ▼
STEP 2: COLLECT (per unit) ──────────────────────────────────────►
    │  Python units → rv-analyze-* ; Java/other → generic structural pass
    ▼
STEP 3: INFER ───────────────────────────────────────────────────►
    │  styles (module/C&C/allocation), decisions, NFRs, external systems
    ▼
STEP 4: SELECT VIEWS ────────────────────────────────────────────►
    │  stakeholder → view mapping; record selected + excluded with reasons
    ▼
STEP 5: SDD TRACE ───────────────────────────────────────────────►
    │  map to openspec/specs/<domain>/spec.md + docs/PRD.md §7
    ▼
STEP 6: WRITE MODEL ─────────────────────────────────────────────►
    │  out/arch/<target-slug>/architecture-model.json (conforms to schema)
    ▼
VERIFY ──────────────────────────────────────────────────────────►
```

## Steps

### 1. Resolve target

- `module:<name>` → `[(modules/<name>, python)]`.
- `system` → every `modules/*/` (all `python`).
- `subsystem:<name>` → read `../rv-doc-arch/subsystems.yaml`, take the `python:` and
  `java:` (and any other language) path lists. Verify each path exists with `ls`.

Record the resulting `language_mix` (count modules and rough LOC per language).

### 2. Collect

**Python units** — for each Python module, invoke the existing analysis skills:

```
Skill tool: skill="rv-analyze-module", args="<module-name>"
```

Use its Context / Structural / Interaction / Behavioral findings. For inter-module
dependencies invoke once:

```
Skill tool: skill="rv-analyze-dependencies", args="<module-name or empty for all>"
```

Optionally (only if maintainability/complexity is a documented concern) invoke
`rv-analyze-complexity` / `rv-analyze-dead-code`.

**Java / Maven units** — do a structural pass without a Java toolchain:
- Parse the module hierarchy from `pom.xml` (aggregator `<modules>` list, parent/child).
- `Grep`/`Glob` the source tree for packages, top-level classes, and entry points
  (e.g. `@Command`, `public static void main`, `public final class`).
- Extract external dependencies from `<dependencyManagement>` / `<dependencies>`.
- Identify the process boundary: how is this engine invoked from elsewhere (e.g. a fat
  JAR run via `java -jar`)? Grep the calling Python module for `subprocess`, `-jar`, the
  JAR name.

**Other languages** — same generic approach: read the build file, map directories to
units, grep for entry points and dependencies.

Populate `modules[]`, `components[]`, and `relations[]`. Set `modules[].source` to
`rv-analyze-module` or `generic` accordingly.

For each significant module, write the narrative fields now, while the source is fresh:
`how_it_works` (a paragraph on internal mechanics, naming key classes and the data they
transform, and the tricky part), `why_separate` (why this is its own module — the design
tension the boundary protects), and `gotchas` (the non-obvious facts a maintainer must know).
Write `components[].narrative` for every runtime element a reader must understand to follow
the data flow. Do not defer this to generation — generation cannot recover what you do not record.

### 3. Infer styles, decisions, NFRs

Using `views-and-beyond.md`:
- Determine the predominant **module**, **C&C**, and **allocation** styles, each with
  evidence and a confidence. A subprocess/JAR boundary is a strong allocation (install)
  and C&C (client-server) signal; a strict dependency ordering is a layered signal.
- Capture **decisions** that shaped the structure. Prefer ones already encoded as
  invariants (INV-XX-NN) or existing ADRs — link them; do not author new ADRs here. For each,
  write `narrative`: the design tension, the rejected alternative, and the failure mode if the
  decision were absent — the *why*, not just the *what*.
- Capture **NFRs** the architecture supports, mapping to `docs/PRD.md` §7 IDs when possible.
  Write `support` as a paragraph naming the concrete mechanism, not a label.
- List **external_systems** and **output_artifacts**.

### 3b. Narrative spine (primer, walkthrough, scenarios)

This is what turns a structure into onboarding. Write:
- **primer** — the conceptual on-ramp a newcomer reads first: `what` (plain language, no
  undefined jargon), `why_this_approach` (name the rejected alternative and the trade-off),
  and `key_concepts` (define each term needed before the views).
- **walkthrough** — pick one concrete, named example (e.g. instrumenting a specific method
  call) and trace it through every stage of the pipeline, one `steps[]` entry per stage, each
  with prose `narrative` and a pinned `concrete_detail`. This is the single most valuable
  onboarding aid — do not skip it.
- **scenarios** — one WHEN/THEN/AND item per non-obvious behavior (e.g. register pressure,
  phase-tagged failure, optional-stage skipping, coverage exclusion), each with concrete
  values and a `why`. These satisfy CLAUDE.md P2's scenario requirement.

### 4. Select views

Pick the views to document for the likely stakeholders (table in `views-and-beyond.md`).
Record `views_selected` (with a reason each) and `views_excluded` (with why). For a
cross-language subsystem, always select an allocation view to expose the boundary.

### 5. SDD trace

Map the target to its domain spec via the table in `rv-doc-architecture`'s SKILL.md
(`openspec/specs/<domain>/spec.md`) and read it for FRs / invariants; read `docs/PRD.md`
§7 for NFRs. Populate `sdd{}`. If the target spans domains or has no clean mapping (common
for cross-tree subsystems), populate what applies and leave the rest empty.

### 6. Write the model

Create the directory and write the JSON:

```bash
mkdir -p out/arch/<target-slug>
```

Write `out/arch/<target-slug>/architecture-model.json` conforming to `model-schema.md`.

## Verification Checklist

- [ ] Target resolved to concrete, existing paths; `language_mix` reflects reality.
- [ ] Every Python module went through `rv-analyze-module`; Java/other via generic pass.
- [ ] `relations[]` includes any cross-language/process boundary with its `mechanism`.
- [ ] Each `styles` entry has evidence + confidence; `views_selected` each have a reason.
- [ ] `sdd{}` populated where a domain mapping exists; empty (not invented) otherwise.
- [ ] **Depth present**: `primer`, `walkthrough` (with a concrete named example traced per
      stage), and `scenarios[]` are written. No `how_it_works` / `why_separate` /
      `decisions[].narrative` / `nfrs[].support` is a bare one-liner where a paragraph is due.
- [ ] JSON is valid and conforms to `model-schema.md`.
- [ ] No history/promotional language; evidence-based only.

## Output

`out/arch/<target-slug>/architecture-model.json`. Report the path and a one-line summary
(modules analyzed, languages, views selected) so the orchestrator can proceed to generate.
