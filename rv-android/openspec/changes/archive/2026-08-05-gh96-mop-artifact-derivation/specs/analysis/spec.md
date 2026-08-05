# Delta: analysis (gh96-mop-artifact-derivation)

## Purpose

This delta records what happens to the static-analysis data chain when a second, derived consumer is
attached to its output — and, more importantly, what does *not* happen to it.

The chain is unchanged end to end. `rv-static-analysis` still drives GATOR/GESDA/REACH, still writes
`<results_dir>/<apk_name>.json` with `reachability[]`, `windows[]`, `transitions[]`, `components{}`
and the `"complete": true` sentinel, and still speaks the neutral `*Target` vocabulary. No schema
field is added, renamed or removed, and no producer behaviour changes.

What is new is downstream and device-bound. `aperv-tool` now derives a compact, explorer-shaped MOP
artifact (`<apk_name>.mop.json`) from that JSON and pushes only the artifact to the device. The
derivation is specified in the `aperv` delta of this change, because the generator lives in that
module and its rules are that module's obligations. What belongs here is the chain-level consequence:
the full JSON acquires a second reader, and that reader's output must never flow back into the
analysis direction.

That constraint is the point of this delta. The frozen phase-2 metric definitions — *MOP coverage*
computed over `directly_reaches_mop`, *unique misuse* keyed `(app, class, method, specification)`, and
the app-versus-library split by the `Mneut` prefix test — read the full JSON and logcat, and nothing
else. The derived artifact is a lossy projection built for an explorer: it drops the call graph
entirely, compacts method signature lists to booleans, renames `reachesTarget` to `reachesMop`, and
merges dialog widgets into host activities. Any metric computed from it would silently answer a
different question than the one the study froze. The full JSON therefore stays byte-identical where it
is, and no analysis or metric path may read a `*.mop.json` — a constraint stated normatively here and
checked by an audit rather than left to convention.

The completion sentinel gains a second role without changing its definition. It remains the
producer's "write finished" bit, surfaced as `StaticAnalysisData.complete`; the derivation now treats
it as a **generation precondition** — a document without it never yields an artifact — which is where
the truncation check moves now that the device no longer performs one.

## Data Contracts

### Input
- `<results_dir>/<apk_name>.json` — the full static-analysis JSON, unchanged producer output. Read by
  the metric and consolidation paths, and by the `aperv-tool` derivation.

### Output
- `<results_dir>/<apk_name>.mop.json` — the derived compact MOP artifact. Its only consumers are the
  `aperv-tool` push path and, on the device, the jar. It is **not** an analysis input.

### Side-Effects
- **[Host filesystem]**: one derived artifact per app appears alongside the full JSON in the results
  directory. The full JSON is not written to.

### Error
- None introduced. Derivation errors are raised and handled inside `aperv-tool`; they do not
  propagate into any analysis path.

## Invariants

- **INV-ANA-53**: The full static-analysis JSON SHALL remain byte-identical after any derivation, and
  SHALL remain the sole static-analysis input of every metric computation, gate and offline
  consolidation path. No metric or analysis code SHALL read a `*.mop.json` artifact.
- **INV-ANA-54**: The derived artifact SHALL be a strict downstream projection: the producer, its
  schema and its `"complete": true` sentinel SHALL be unaffected by its existence, and no producer
  behaviour SHALL be conditioned on whether an artifact was derived.

## ADDED Requirements

### Requirement: Derived MOP Artifact as a Device-Only Consumer (FR04, FR05, FR06)

The static-analysis chain SHALL gain exactly one new downstream consumer: the host-side derivation in
`aperv-tool` that projects the full JSON into `<results_dir>/<apk_name>.mop.json`. The derivation
SHALL read the full JSON and SHALL NOT modify it. The artifact SHALL be device input only — pushed by
`aperv-tool`, parsed by the jar, and read by nothing else.

The `"complete": true` sentinel SHALL be a precondition of derivation: a document whose
`StaticAnalysisData.complete` is `False` SHALL NOT yield an artifact. This preserves the sentinel's
meaning (the producer reached the end of write) while moving the consequence of its absence from the
device to the host, where it fails loudly instead of degrading a run.

#### Scenario: derivation leaves the producer output untouched
- **WHEN** `aperv-tool` derives an artifact for `com.example_1.apk`
- **THEN** `<results_dir>/com.example_1.apk.json` SHALL be byte-identical to its content before the
  derivation
- **AND** `<results_dir>/com.example_1.apk.mop.json` SHALL exist alongside it

#### Scenario: truncated analysis yields no artifact
- **WHEN** the full JSON lacks the `"complete": true` sentinel because GATOR was killed mid-write
- **THEN** no `*.mop.json` SHALL be produced for that app
- **AND** the MOP arm for that app SHALL fail loudly rather than run without MOP guidance

#### Scenario: producer is unaware of the derivation
- **WHEN** static analysis runs for an app
- **THEN** its output SHALL be identical whether or not an artifact is later derived from it
- **AND** no producer code path SHALL read, write or test for a `*.mop.json` (INV-ANA-54)

---

### Requirement: Full JSON Remains the Sole Metric Input (R9, NFR02)

Every metric computation, gate and offline consolidation path SHALL read the full static-analysis JSON
and logcat exclusively. The frozen definitions — *MOP coverage* over `directly_reaches_mop`, *unique
misuse* keyed `(app, class, method, specification)`, and the app-versus-library split by the `Mneut`
prefix test — SHALL be unaffected by this change, because their input is unchanged.

No metric or analysis code SHALL read a `*.mop.json` artifact (INV-ANA-53). The artifact is a lossy
projection: it carries no `reachability` section, no method signatures, `reachesTarget` renamed to
`reachesMop`, `targetMethods` compacted to a boolean, and dialog widgets merged into host activities.
A metric computed over it would answer a different question under the same name. This SHALL be
enforced by an audit over the repository — a test asserting that no module outside `aperv-tool`
references the `.mop.json` suffix — rather than by convention. The audit test is itself the only
permitted match outside `aperv-tool`.

#### Scenario: metrics unchanged by the presence of an artifact
- **WHEN** the derivation runs for an app and the analysis pipeline then computes its
  `directly_reaches_mop` set
- **THEN** the set SHALL be computed from the full JSON
- **AND** it SHALL be identical to the value computed before this change

#### Scenario: audit catches an analysis path reading the artifact
- **WHEN** any module other than `aperv-tool` references a `.mop.json` path
- **THEN** the audit test SHALL fail naming the file and the reference
- **AND** the audit SHALL treat its own assertion text as the single permitted occurrence

#### Scenario: resume and offline consolidation re-parse the full JSON
- **WHEN** an experiment is resumed and `ResultProcessorComponent` re-resolves static data for an app
- **THEN** it SHALL re-parse `<results_dir>/<apk_name>.json`
- **AND** the presence, absence or staleness of a `*.mop.json` SHALL have no effect on the result
