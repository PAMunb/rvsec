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
file-based intermediate consumed by `rv-doc-arch-generate`. The model is a single JSON file
written once per run; `out/` is temporary, so the model is regenerated, never cited.

## Supporting Files

- `reference/model-schema.md` — the exact schema of `architecture-model.json`. **Read it
  first.** Your output must conform to it.
- `../rv-doc-arch/reference/views-and-beyond.md` — the method (view categories, styles,
  stakeholder→view selection). Use it to fill `styles`, `views_selected`, `views_excluded`.
  Read its section 6 (C4 level per view) before filling `components[].kind`: a uv module
  is never a runtime container.
- `scripts/group_coupling.py` — the external-coupling ratio of the target (step 2c).
- `.claude/documentation-principles.md` — the repository's documentation principles.

## Argument

`$ARGUMENTS` is a target spec:
- `system` — the whole RV-Android workspace (every uv workspace module).
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

One metric covers both languages: the external-coupling ratio (step 2c), counted from
`import` lines alone, so it needs no toolchain for either.

Both normalize into the same `architecture-model.json` schema, so generation is language-agnostic.

## Documentation Guidelines

Follow `.claude/documentation-principles.md`. Specific to this phase: every
style/decision/NFR entry needs concrete evidence (a file, a class, a build rule); omit what
you cannot substantiate.

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
    │  Expand $ARGUMENTS into (path, language, kind) units
    ▼
STEP 2: COLLECT (per unit) ──────────────────────────────────────►
    │  module → rv-analyze-module ; file/slice → rv-analyze-file ;
    │  Java/other → generic structural pass ; whole target → coupling ratio
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
- `system` → every workspace member under `modules/` (the `[tool.uv.workspace]` members and
  excludes in the root `pyproject.toml`), all `python`.
- `subsystem:<name>` → read `../rv-doc-arch/subsystems.yaml`, take every path list under the
  key (`python:`, `java:`, and others such as `shell:` or `docker:`). Verify each path
  exists with `ls`. Non-Python, non-Java lists go to the generic pass.

The manifest mixes module roots with single files and package directories, so classify
every Python entry by what the path is; each kind goes to a different analysis skill in
step 2:

| Entry | Example | Kind |
|-------|---------|------|
| a module root `modules/<name>` | `modules/rv-tools` | module |
| a single `.py` file | `modules/rv-android-core/src/rv_android_core/util/jar_resolver.py` | file |
| a package directory inside a module | `modules/rv-android-core/src/rv_android_core/domain` | package slice |

Record the resulting `language_mix` (count modules and rough LOC per language).

### 2. Collect

**2a. Python units** — dispatch by the kind from step 1. `rv-analyze-module` takes a module
*name* and analyzes the whole module; `rv-analyze-file` takes one file *path*. Never pass a
path to `rv-analyze-module`.

| Kind | Invoke | Argument |
|------|--------|----------|
| module | `rv-analyze-module` | the module name, e.g. `rv-tools` |
| file | `rv-analyze-file` | the path as listed |
| package slice | `rv-analyze-file` once per `.py` file in the directory (skip an `__init__.py` that only re-exports) | each file path |

A slice stays a slice: do not widen it to `rv-analyze-module` on the owning module, because
the rest of that module is outside the target. Use the Context / Structural / Interaction /
Behavioral findings of each result. For inter-module dependencies invoke once, with the
module names the target touches (module entries plus the owners of file and slice entries):

```
Skill tool: skill="rv-analyze-dependencies", args="<module-name or empty for all>"
```

Optionally (only if maintainability/complexity is a documented concern) invoke
`rv-analyze-complexity` / `rv-analyze-dead-code`.

**2b. Java / Maven units** — do a structural pass without a Java toolchain:
- Parse the module hierarchy from `pom.xml` (aggregator `<modules>` list, parent/child).
- `Grep`/`Glob` the source tree for packages, top-level classes, and entry points
  (e.g. `@Command`, `public static void main`, `public final class`).
- Extract external dependencies from `<dependencyManagement>` / `<dependencies>`.
- Identify the process boundary: how is this engine invoked from elsewhere (e.g. a fat
  JAR run via `java -jar`)? Grep the calling Python module for `subprocess`, `-jar`, the
  JAR name.

**Other languages** — same generic approach: read the build file, map directories to
units, grep for entry points and dependencies.

**2c. Coupling ratio** — run once for the whole target, from the rv-android root:

```bash
python3 .claude/skills/rv-doc-arch-analyze/scripts/group_coupling.py <target>
# <target>: subsystem:<name> | module:<name>; for `system`, run it per module
```

It prints, per language and overall, external / (internal + external) over deduplicated
first-party import edges of non-test files (Python: packages under `modules/*/src/`; Java:
classes defined in the target, plus `br.unb.*` outside it), and the most-imported external
targets; the script's docstring has the counting rules. Edges into the foundation's
cross-cutting packages (`rv_android_core` logging, error, validation, constants) are shown
apart as `x-cut` and left out of the ratio: they are the Aspects style, not a boundary leak.
Indicative bands: below 0.3, mostly self-contained; 0.3–0.5, leans on outside code (name
those contracts in the doc); above 0.5, check the listed targets: a lower layer (domain
models in `rv_android_core`) is expected in a layered style, a peer module is a boundary
question for the rationale. `java -jar` and JSON contracts are not imports and do not show
up; record them in `relations[].mechanism`. Store the result in `coupling` (see schema).

Populate `modules[]`, `components[]`, and `relations[]`. Set `modules[].source` to
`rv-analyze-module`, `rv-analyze-file`, or `generic` accordingly.

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

Record `source_commits` first: for each git repository the target's paths live in,

```bash
git -C <repo> rev-parse --short HEAD
git -C <repo> status --porcelain -- <target paths in that repo>   # non-empty → dirty
```

Write `out/arch/<target-slug>/architecture-model.json` conforming to `model-schema.md`.

## Verification Checklist

- [ ] Target resolved to concrete, existing paths; `language_mix` reflects reality.
- [ ] Each Python entry went to the skill for its kind (module → `rv-analyze-module` by
      name; file or package slice → `rv-analyze-file` per file); Java/other via generic pass.
- [ ] `coupling` filled from `group_coupling.py`, with the top external targets.
- [ ] `relations[]` includes any cross-language/process boundary with its `mechanism`.
- [ ] Each `styles` entry has evidence + confidence; `views_selected` each have a reason.
- [ ] `sdd{}` populated where a domain mapping exists; empty (not invented) otherwise.
- [ ] **Depth present**: `primer`, `walkthrough` (with a concrete named example traced per
      stage), and `scenarios[]` are written. No `how_it_works` / `why_separate` /
      `decisions[].narrative` / `nfrs[].support` is a bare one-liner where a paragraph is due.
- [ ] `source_commits` recorded for every repository the target spans.
- [ ] JSON is valid and conforms to `model-schema.md`.
- [ ] Follows `.claude/documentation-principles.md`; evidence-based only.

## Output

`out/arch/<target-slug>/architecture-model.json`. Report the path and a one-line summary
(modules analyzed, languages, views selected) so the orchestrator can proceed to generate.
