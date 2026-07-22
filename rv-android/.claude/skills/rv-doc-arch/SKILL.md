---
name: rv-doc-arch
description: >-
  Generate Views-and-Beyond architecture documentation (single file) for a target: the
  whole system, one module, or a named subsystem (possibly cross-language). Orchestrates
  analyze then generate. Use for system/subsystem-level architecture docs based on the SEI
  "Views and Beyond" method. Do NOT use for per-module 4+1 docs (use /rv-doc-architecture)
  or ADRs (use /rv-doc-adr).
argument-hint: [system | module:<name> | subsystem:<name>]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash, Skill
---

# Architecture Documentation (Views and Beyond): $ARGUMENTS

Orchestrates a two-phase, file-based pipeline that produces one Views-and-Beyond document
for the target. There is no database: analysis writes an intermediate JSON, generation
reads it. This is the system/subsystem complement to the per-module `rv-doc-architecture`
(4+1) skill — the two coexist and do not overwrite each other.

```
                ┌──────────────────────────────────────────────┐
   $ARGUMENTS ─►│ rv-doc-arch (this skill)                     │
                │  resolve target → analyze → generate         │
                └───────┬──────────────────────────┬───────────┘
                        ▼                          ▼
        rv-doc-arch-analyze            rv-doc-arch-generate
        (reuses rv-analyze-* for       (fills the single-file
         Python; generic pass for       Views-and-Beyond template)
         Java/Maven)
                        │                          │
                        ▼                          ▼
        out/arch/<slug>/                docs/architecture/<target>.md
        architecture-model.json
```

## Supporting Files

- `subsystems.yaml` — named subsystems (cross-language path groups), e.g. `instrumentation`.
- `reference/views-and-beyond.md` — the method: view categories, styles, the 5-section view
  template, stakeholder→view selection, beyond-views structure.

## Relationship to existing skills (no overwrite)

| Existing skill (kept) | This suite (new) |
|-----------------------|------------------|
| `rv-doc-architecture` — per-module, 4+1, writes `modules/<m>/docs/architecture.md` | `rv-doc-arch` — system/subsystem, Views-and-Beyond, writes `docs/architecture/<target>.md` |
| `rv-doc-adr` — authors ADRs | referenced (not replaced); decisions link to ADRs |

The new suite never writes to `modules/<m>/docs/` or to other skills' directories.

## Argument

`$ARGUMENTS` is a target spec:
- `system` — the whole RV-Android workspace.
- `module:<name>` — one module (Views-and-Beyond view of it; complements its 4+1 doc).
- `subsystem:<name>` — a key from `subsystems.yaml`, which may span languages/trees.

If `$ARGUMENTS` is empty, ask which target to document (system, a module, or a subsystem
from `subsystems.yaml`).

## Workflow

```
STEP 1: RESOLVE ─────────────────────────────────────────────────►
    │  Validate the target; for subsystem:<name> confirm it exists in subsystems.yaml
    ▼
STEP 2: ANALYZE ─────────────────────────────────────────────────►
    │  Invoke rv-doc-arch-analyze → out/arch/<slug>/architecture-model.json
    ▼
STEP 3: GENERATE ────────────────────────────────────────────────►
    │  Invoke rv-doc-arch-generate → docs/architecture/<target>.md
    ▼
STEP 4: REPORT ──────────────────────────────────────────────────►
    │  Path, views produced, and a pointer to rv-doc-adr for formal decisions
    ▼
VERIFY ──────────────────────────────────────────────────────────►
```

## Steps

### 1. Resolve target

- Parse `$ARGUMENTS` into `scope` (`system` | `module` | `subsystem`) and name.
- For `subsystem:<name>`, read `subsystems.yaml` and confirm the key exists; if not, list
  the available subsystems and stop.
- Compute `<target-slug>` = target with `:` → `-` (e.g. `subsystem-instrumentation`).

### 2. Analyze

```
Skill tool: skill="rv-doc-arch-analyze", args="$ARGUMENTS"
```

Wait for it to write `out/arch/<target-slug>/architecture-model.json`. If it reports
missing paths or an empty model, stop and surface the problem.

### 3. Generate

```
Skill tool: skill="rv-doc-arch-generate", args="$ARGUMENTS"
```

Wait for it to write `docs/architecture/<target>.md`.

### 4. Report

Report the output path and the views produced. Remind the user that significant
architectural decisions surfaced in the Rationale can be formalized with `/rv-doc-adr`
(this suite references ADRs but does not author them).

## Verification Checklist

- [ ] Target resolved correctly; subsystem (if any) found in `subsystems.yaml`.
- [ ] `architecture-model.json` exists and is non-empty before generating.
- [ ] `docs/architecture/<target>.md` written; no existing module/skill files modified.
- [ ] Output is a single file with selected views and SDD traceability.

## Notes

- **No Neo4j / no database.** The intermediate `architecture-model.json` is the only shared
  state, and it is regenerable. The upstream `agente-documentador` suite uses a graph
  because it analyzes arbitrary repos in parallel processes; this suite targets one known
  workspace, so a file suffices.
- **Cross-language targets** (e.g. `subsystem:instrumentation`) are expected: analyze uses
  `rv-analyze-*` for Python and a generic structural pass for Java/Maven, normalizing both
  into one model so the document is language-agnostic.
