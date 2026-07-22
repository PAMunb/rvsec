---
name: rv-doc-arch-generate
description: >-
  Generate a single-file Views-and-Beyond architecture document from architecture-model.json.
  Use as the second phase of /rv-doc-arch, after rv-doc-arch-analyze has written the model.
  Produces one docs/architecture/<target>.md (Part I beyond-views + Part II views + appendices).
  Do NOT use to analyze code — that is /rv-doc-arch-analyze.
argument-hint: [system | module:<name> | subsystem:<name>]
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Write, Bash
---

# Generate Architecture Document: $ARGUMENTS

Reads `out/arch/<target-slug>/architecture-model.json` and writes a single Views-and-Beyond
document to `docs/architecture/<target>.md`. Does not analyze code — it consumes the model
produced by `rv-doc-arch-analyze` (it may re-read source only to quote a class name or path).

## Supporting Files

- `templates/architecture-template.md` — the output skeleton. Fill every `{{placeholder}}`;
  delete sections and views the model did not select.
- `../rv-doc-arch-analyze/reference/model-schema.md` — the model's field meanings.
- `../rv-doc-arch/reference/views-and-beyond.md` — the method (5-section view template,
  styles, Part I structure).

## Single-file output

Unlike the upstream `agente-documentador` suite (which splits ~70 files), this produces
**one document** with an anchored table of contents. Output path:
- `subsystem:<name>` → `docs/architecture/<name>.md`
- `system` → `docs/architecture/system.md`
- `module:<name>` → `docs/architecture/<name>.md` (this is the Views-and-Beyond view; it
  does **not** replace the per-module 4+1 doc at `modules/<name>/docs/architecture.md`).

## Documentation Guidelines

**Audience and purpose (read this first).** The reader is a **new engineer with no prior
exposure to this target**. The document is their on-ramp: by reading it top to bottom they
must understand *what* the subsystem does, *how* it works (following a concrete worked
example), and *why* it is shaped this way. Write for that person.

1. **Narrative first (CLAUDE.md P2).** Every section opens with **prose in full sentences**
   that explains and connects. Tables are **supplements** for quick reference — never the body
   of a section. A section that is only a table is wrong. Explain reasons inline; when behavior
   has a non-obvious cause, say why right there.
2. **Use the model's depth.** The model carries `primer`, `walkthrough`, per-module
   `how_it_works` / `why_separate` / `gotchas`, `components[].narrative`, `decisions[].narrative`,
   `nfrs[].support`, and `scenarios[]`. Render these as prose paragraphs and a worked-example
   walkthrough. Do not compress a paragraph back into a table cell.
3. **Language**: English only.
4. **Tone**: Professional, objective. No promotional language ("modern", "elegant", etc.).
5. **Current state only**: no migration/history narration.
6. **Faithful to the model**: do not introduce elements, decisions, or NFRs absent from the
   model. If a narrative field is thin or missing, report it (the analyze phase should be
   re-run) rather than inventing depth or re-analyzing the code here.

## Diagram Guidelines

Use Mermaid with the `neutral` theme (`%%{init: {'theme': 'neutral'}}%%`). Avoid reserved
IDs (`graph`, `subgraph`, `end`, `style`, `class`, `default`). Diagram types: `flowchart`,
`sequenceDiagram`, `classDiagram`, `stateDiagram-v2`.

## Workflow

```
STEP 1: LOAD MODEL ──────────────────────────────────────────────►
    │  Read + validate out/arch/<target-slug>/architecture-model.json
    ▼
STEP 2: PART I ──────────────────────────────────────────────────►
    │  overview, context diagram, core components, mapping, rationale, artifacts, directory
    ▼
STEP 3: PART II ─────────────────────────────────────────────────►
    │  one section per selected view (5 sub-sections each)
    ▼
STEP 4: APPENDICES + SDD ────────────────────────────────────────►
    │  dependencies, data model (if any), specification traceability
    ▼
STEP 5: WRITE ───────────────────────────────────────────────────►
    │  docs/architecture/<target>.md
    ▼
VERIFY ──────────────────────────────────────────────────────────►
```

## Steps

### 1. Load model

```bash
ls out/arch/<target-slug>/architecture-model.json
```

Read it. If it is missing, stop and instruct the caller to run `rv-doc-arch-analyze` first
(do not analyze code here). Validate it against `model-schema.md`.

### 2. Part I — Beyond Views

Fill the template's Part I, rendering the model's narrative fields as prose:
- **Documentation overview** — purpose, scope, audience (from `target`/`scope`/`generated_for`).
- **Conceptual primer** — render `primer`: `what` in plain language, `why_this_approach`
  (naming the rejected alternative + trade-off), and `key_concepts` as a short defined-terms
  list. This is the newcomer's on-ramp; write it as readable paragraphs.
- **System overview & context** — narrate `external_systems` in prose; draw the single context
  diagram (external actors/systems around the target). All views reference this one.
- **How it works — end to end** — render `walkthrough` as a numbered narrative: state the
  example, then walk each stage with its `narrative` + `concrete_detail`. This section is the
  heart of the onboarding; do not reduce it to a list of stage names.
- **Core components** — for each component a reader must understand, write its `narrative` as
  a paragraph; keep the summary table as a quick index beneath the prose.
- **Mapping between views** — from `relations[]`, in prose: which modules realize which runtime
  components, which components deploy/install where. Make any cross-language boundary
  (a `subprocess`/JAR `mechanism`) explicit and explain what crosses it.
- **Rationale** — render each `decisions[].narrative` as a paragraph (the tension, the rejected
  alternative, the failure mode if absent); keep the decision table as an index. Narrate the
  `styles` and render `nfrs[].support` as prose with the table as a summary.
- **Output artifacts** — table from `output_artifacts[]`, with a sentence of context each.
- **Directory** — glossary/acronyms used, references.

### 3. Part II — Views

For each entry in `views_selected`, emit one view using the **5-section** structure
(primary presentation, element catalog, context [reference Part I], variability, rationale).
Lead each view with a short prose paragraph orienting the reader to what this view shows and
why it matters; the diagram and catalog support that prose. For module-view elements, fold in
the relevant `modules[].how_it_works` / `why_separate` / `gotchas` as paragraphs (the catalog
table stays as a quick reference). Build the primary diagram from the relevant
`components`/`modules`/`relations`; every diagram node must also appear in the catalog. Write
each view's rationale as prose. Delete any view template block not in `views_selected`; mention
`views_excluded` briefly only where it aids understanding.

Render `scenarios[]` as a **Scenarios** subsection (WHEN/THEN/AND with the concrete values and
`why` from the model), placed under the view whose behavior it illustrates (or in the C&C view
by default).

### 4. Appendices + SDD

- **Dependencies appendix** — external dependencies per language (from the model).
- **Data model appendix** — only if the model has data entities; otherwise delete it.
- **Specification traceability** — fill from `sdd{}`: FRs, invariants (with where enforced),
  NFRs. If `sdd{}` is partial (cross-tree subsystem), state which parts map and which do not.

### 5. Write

```bash
mkdir -p docs/architecture
```

Write `docs/architecture/<target>.md`.

## Verification Checklist

- [ ] Document built from the model; no invented elements/decisions/NFRs.
- [ ] **Reads as onboarding narrative**: every section opens with prose; no section is just a
      table. A newcomer could understand the subsystem from a top-to-bottom read.
- [ ] **Primer**, **How it works — end to end** (worked example traced per stage), and
      **Scenarios** (WHEN/THEN/AND with concrete values) are all present and substantive.
- [ ] Per-component depth rendered (`how_it_works` / `why_separate` / `gotchas`,
      `decisions[].narrative`, `nfrs[].support`) as paragraphs, not table cells.
- [ ] Exactly the `views_selected` views are present, each with all 5 sections.
- [ ] Every Mermaid diagram node also appears in that view's element catalog.
- [ ] Cross-language/process boundary is explicit in Mapping (if `language_mix` > 1).
- [ ] SDD traceability filled where the model maps; gaps stated, not faked.
- [ ] All `{{placeholders}}` replaced; TOC anchors resolve; English; neutral-theme diagrams.
- [ ] Per-module 4+1 docs and ADRs referenced (not duplicated).

## Output

`docs/architecture/<target>.md`. Report the path and section/view counts.
