## Purpose

The static-analysis document (`<apk_name>.json`, written by GATOR) is the coverage denominator of every run and the source of the MOP artifact APE-RV reads. Since gh120 it carries, for every app method, the call-graph distance to every monitored target (`reachability[].methods[].targetDistances`, pairs `[i, d]` into `distanceTargets`). That one member made the documents 100 to 400 times larger: 2.16 GB for `org.wikipedia_50595`, 9.34 GB for `eu.darken.sdmse_10705000`. No consumer of `StaticAnalysisData` reads it — coverage uses seven fields per method, `componentType`/`isMain` per class and `codePackage` — yet `StaticAnalysisParser` read the file into one string and `json.loads`ed it, so the pairs were materialised as Python lists before being dropped. In the `e03mini-smoke` run of 2026-10-09 that parse OOM-killed 10 GiB campaign containers in the first task of the plain `ape` arm.

This delta changes how the document is read, not what is read from it. The parser walks the document as a stream of JSON events and never builds the distance members. Because a run reads the same document once per task and once more at result processing, the first read also writes a parsed copy beside the source — the same document without the two distance members, keyed by the source's SHA-256 — and every later read of an unchanged source parses the copy instead. The model the parser returns is the same in every case, so the metric definitions, the resume equivalence (INV-PLT-18) and every consumer of `StaticAnalysisData` are untouched.

The device-side consumer is touched in one sentence only: the derivation of the MOP artifact (`aperv` capability) also reads in streaming, so an unparseable document now fails in that streaming read instead of in `json.loads`.

## Data Contracts

### Input
- `<results_dir>/<apk_name>.json` — the full static-analysis document, any size; may be truncated by a killed producer (source: GATOR via `rvsec-analysis-client.jar`, copied by `StaticAnalysisComponent`)
- `<results_dir>/<apk_name>.static.json` — the parsed copy, when present (source: this capability)

### Output
- `StaticAnalysisData` — unchanged model (`classes`, `windows`, `wtg`, `components`, `complete`, `code_package`, `code_package_source`, `class_defs_under_key`) (destination: `rv-platform`, `rv-coverage`, `rv-agent`, `rv-screen-parser`)
- `<results_dir>/<apk_name>.static.json` — the source document without `distanceTargets` and `reachability[].methods[].targetDistances`, plus a top-level `source: {digest: "sha256:<hex>", generator: "rv-static-analysis/1"}` (destination: later reads of the same APK)

### Side-Effects
- **[Host filesystem]**: one `<apk_name>.static.json` per APK per results directory, written atomically (temporary file in the same directory, then rename); overwritten when the source's digest changes

### Error
- None raised to callers. A missing, unreadable or empty source yields an empty `StaticAnalysisData` as today (INV-ANA-06); a truncated source yields the members read in full (INV-ANA-81); a cache that cannot be written is logged and the parsed model is still returned.

## Invariants

- **INV-ANA-80**: `StaticAnalysisParser` SHALL read the analysis document as a stream of JSON events and SHALL NOT hold the file's text, nor any `targetDistances` or `distanceTargets` value, in memory. For every well-formed document the returned `StaticAnalysisData` SHALL equal the one produced by `json.loads` of the same file followed by today's section parsers.
- **INV-ANA-81**: When the document ends before its root object closes, the parser SHALL keep every top-level member whose value was read in full and SHALL drop the member being read when the input ended; `complete` SHALL be `False` unless the `complete` member itself was read. The recovery SHALL stay behind the `_recover_truncated_json` entry point.
- **INV-ANA-82**: `read_static_analysis_files(results_dir, apk)` SHALL reuse `<apk_name>.static.json` only when its recorded `source.digest` equals `"sha256:" +` the SHA-256 of the current `<apk_name>.json`. Any other state — absent, unreadable, unparseable, another digest — SHALL be a cache miss that re-reads the source and rewrites the copy.
- **INV-ANA-83**: Parsing `<apk_name>.static.json` SHALL yield a `StaticAnalysisData` equal to the one parsed from its source. The copy SHALL be written only from a source read without truncation, so a truncated source is re-read on every call.
- **INV-ANA-84**: The parsed copy is read only by `rv-static-analysis`. No module SHALL open a `*.static.json` except through `static_analysis_parser`, and the copy SHALL never be pushed to a device.

## ADDED Requirements

### Requirement: Streaming Read of the Analysis Document (NFR02, NFR04)

`StaticAnalysisParser` (`modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`) SHALL read the analysis document with `ijson` (C backend) in one pass of JSON events, building each top-level member as a Python value except `distanceTargets` and the `targetDistances` member of every `reachability[].methods[]` entry, whose events SHALL be consumed and discarded without building a value (INV-ANA-80). The section parsers (`_parse_classes`, `_parse_windows`, `_parse_transitions`, `_parse_components`) SHALL receive the same dict shape they receive today, so section independence and graceful degradation (INV-ANA-06) are unchanged.

A document that ends before its root object closes — the producer killed during its write, INV-ANA-31 — SHALL be recovered from the same pass: every top-level member read in full is kept, the member in progress and everything after it are dropped (INV-ANA-81). This is the behaviour `_recover_truncated_json` names, and the name stays. It is a superset of the bracket repair it replaces: that repair closed the root at the last `]` of the text, which failed whenever the last `]` closed a nested list rather than a top-level section.

#### Scenario: a gh120 document parses to the same model without its distances
- **WHEN** the parser reads `cryptoapp.apk.json` (fixture, 38 methods carrying `targetDistances`)
- **THEN** the returned `StaticAnalysisData` SHALL equal the one built from `json.loads` of the file by today's section parsers, class by class, method by method, window by window and transition by transition
- **AND** no `targetDistances` list SHALL have been materialised during the read

#### Scenario: a 2.16 GB document parses inside a campaign container
- **WHEN** the parser reads `org.wikipedia_50595.apk.json` (about 2.16 GB, 39,950 methods)
- **THEN** the process's peak resident memory SHALL stay below 3 GiB
- **AND** the model SHALL carry 39,950 methods and the document's windows and transitions

#### Scenario: a document truncated inside `transitions` keeps the earlier sections
- **WHEN** the file ends inside the 12th element of `transitions`, after `reachability` and `windows` were written in full
- **THEN** `classes` and `windows` SHALL be populated as from the complete document
- **AND** `wtg` SHALL be empty and `complete` SHALL be `False`
- **AND** no exception SHALL reach the caller

#### Scenario: a document with no complete top-level array yields an empty model
- **WHEN** the file ends inside the first element of `reachability`
- **THEN** the parser SHALL return a `StaticAnalysisData` with empty `classes`, `windows` and `wtg`
- **AND** `complete` SHALL be `False`

### Requirement: Parsed-Document Cache Beside the Source (NFR04)

`read_static_analysis_files(results_dir, apk)` — the entry point of `StaticAnalysisComponent` and `ResultProcessorComponent` — SHALL consult `<results_dir>/<apk_name>.static.json` before reading `<results_dir>/<apk_name>.json`:

1. compute the SHA-256 of the source in chunks;
2. when the copy exists and its `source.digest` equals `"sha256:" + <hex>`, parse the copy and return its model;
3. otherwise read the source in streaming (INV-ANA-80); when the read was not truncated, write the copy atomically — the document without `distanceTargets` and `targetDistances`, plus `source: {digest, generator: "rv-static-analysis/1"}` — and return the model.

The copy exists because one document is read many times on one host: once per task of the APK (each task is a fresh `Task` whose `static_data` is released when it finishes, INV-PLT-38) and once more per APK at result processing (INV-PLT-15). Keying it on the digest, not on the file's size or modification time, makes it a pure function of the source: a re-analysed APK whose new document lands under the same name is never answered by the old copy (INV-ANA-82). A truncated source is never cached (INV-ANA-83), so a later complete document under the same name cannot be shadowed by a recovery.

`parse_file(file_path)`, which `StaticAnalyzer` calls on the producer side with an explicit path, reads in streaming and does not use the cache.

#### Scenario: the second read of an unchanged source uses the copy
- **WHEN** `read_static_analysis_files("results/c_00/app.apk", "app.apk")` has run once on a complete `app.apk.json`
- **AND** it is called again with the source unchanged
- **THEN** the second call SHALL parse `app.apk.static.json` and SHALL NOT read `app.apk.json` beyond computing its digest
- **AND** the two returned models SHALL be equal

#### Scenario: a changed source regenerates the copy
- **WHEN** `app.apk.static.json` records `source.digest == "sha256:ab12…"` and `app.apk.json` now hashes to `cd34…`
- **THEN** the source SHALL be read in streaming and the copy overwritten with `source.digest == "sha256:cd34…"`

#### Scenario: a truncated source is not cached
- **WHEN** `app.apk.json` ends inside `transitions` and no copy exists
- **THEN** the recovered model SHALL be returned (INV-ANA-81)
- **AND** no `app.apk.static.json` SHALL exist afterwards

#### Scenario: an unwritable results directory still returns the model
- **WHEN** the copy's temporary file cannot be created because the directory is read-only
- **THEN** the parsed model SHALL be returned
- **AND** a warning naming the path SHALL be logged and no partial file SHALL remain

## MODIFIED Requirements

### Requirement: Derived MOP Artifact as a Device-Only Consumer (FR04, FR05, FR06)

The static-analysis chain SHALL gain exactly one new downstream consumer: the host-side derivation in
`aperv-tool` that projects the full JSON into `<results_dir>/<apk_name>.mop.json`. The derivation
SHALL read the full JSON and SHALL NOT modify it. The artifact SHALL be device input only — pushed by
`aperv-tool`, parsed by the jar, and read by nothing else.

The `"complete": true` sentinel SHALL NOT be a precondition of derivation. A document written by the
producer's first pass — valid JSON with populated `reachability` and `windows` per `INV-ANA-20`, and an
empty `transitions` array — SHALL yield an artifact whose `wtg` is empty and whose
`stats["wtgEdges"]` is `0`, which is how WTG absence reaches the device (`INV-DRV-08` in the `aperv`
capability). The sentinel keeps its producer-side meaning unchanged (`INV-ANA-31`) and remains
available to the consumers that do require completeness; the derivation is no longer one of them. A
genuinely interrupted write is still refused, one step earlier: the producer truncates its output file
on open, so a killed second pass leaves unparseable bytes that fail in the derivation's streaming read
before `derive()` runs. Unlike `StaticAnalysisParser`, the derivation does not recover a truncated
document (INV-ANA-81 governs the parser only).

#### Scenario: derivation leaves the producer output untouched
- **WHEN** `aperv-tool` derives an artifact for `com.example_1.apk`
- **THEN** `<results_dir>/com.example_1.apk.json` SHALL be byte-identical to its content before the
  derivation
- **AND** `<results_dir>/com.example_1.apk.mop.json` SHALL exist alongside it

#### Scenario: WTG-less analysis still yields an artifact
- **WHEN** the full JSON lacks the `"complete": true` sentinel because `WTGBuilder` did not finish, and
  it carries populated `reachability` and `windows` with `transitions: []`
- **THEN** a `*.mop.json` SHALL be produced for that app
- **AND** it SHALL carry `wtg == {}` and `stats["wtgEdges"] == 0`
- **AND** the MOP arm for that app SHALL run, with the jar disabling its WTG-dependent scoring passes
  through `MopData.hasWtgData()`

#### Scenario: unparseable analysis output still yields no artifact
- **WHEN** the full JSON is syntactically invalid because the producer was killed during its second
  write pass, which truncated the file on open
- **THEN** no `*.mop.json` SHALL be produced for that app
- **AND** the failure SHALL be raised by the streaming read in `_derive_mop_artifact()` as
  `RVToolExecutionError`, before `derive()` is reached

#### Scenario: producer is unaware of the derivation
- **WHEN** static analysis runs for an app
- **THEN** its output SHALL be identical whether or not an artifact is later derived from it
- **AND** no producer code path SHALL read, write or test for a `*.mop.json` (INV-ANA-54)

---

### Requirement: Full JSON Remains the Sole Metric Input (R9, NFR02)

Every metric computation, gate and offline consolidation path SHALL read the full static-analysis JSON
and logcat exclusively. On the host paths that go through `static_analysis_parser.read_static_analysis_files`,
"the full JSON" includes its parsed copy `<apk_name>.static.json` when the copy's recorded digest matches
the source (INV-ANA-82): the copy is the source document without `distanceTargets` and `targetDistances`,
which no metric reads, and it parses to the same `StaticAnalysisData` (INV-ANA-83). The frozen
definitions — *MOP coverage* over `directly_reaches_mop`, *unique misuse* keyed `(app, class, method,
specification)`, and the app-versus-library split by the `Mneut` prefix test — SHALL be unaffected,
because their input is unchanged.

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
- **THEN** it SHALL read `<results_dir>/<apk_name>.json` through `read_static_analysis_files`, which
  answers from `<apk_name>.static.json` when its digest matches and from the source otherwise
- **AND** the presence, absence or staleness of a `*.mop.json` SHALL have no effect on the result

#### Scenario: metrics are the same from the source and from its parsed copy
- **WHEN** `ResultProcessorComponent` processes a task once with no `<apk_name>.static.json` present and
  once with the copy written by an earlier task
- **THEN** `summary.csv` and `coverage.csv` SHALL be byte-identical between the two runs
