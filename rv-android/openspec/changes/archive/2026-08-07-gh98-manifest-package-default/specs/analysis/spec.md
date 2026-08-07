# Delta Spec: analysis — gh98-manifest-package-default

## Purpose

The static analysis pipeline turns an APK into a catalogue of the application's own classes, windows and methods: GATOR produces the window transition graph, GESDA the GUI elements, REACH the reachability of each method with respect to the monitored API. Every one of those outputs is scoped by a single string — the package that decides which classes count as the application's and which are the libraries it bundles. That string reaches the pipeline twice: as the `codePackage` client parameter on the GATOR invocation, and as the filter argument the `StaticAnalysisParser` applies when reading the resulting JSON.

What changes here is not how the filter works but where its value comes from. The pipeline used to receive a package that `PackageDetector` had elected, with no way to ask for anything else; it now receives the package the APK declares unless the user asked for the election. The parser's matching rule, the invocation's argument, and the reachability semantics are untouched: the same string arrives from a different decision.

The consequence worth stating for anyone reading an analysis output later is that the JSON does not record this decision. GATOR writes the manifest package into the artefact's `package` field regardless of which key filtered its contents, so an analysis JSON cannot report the scope it was produced under. Two analyses of one APK under two keys are indistinguishable from the files alone. The pipeline therefore MUST record the key it used at the moment it uses it, and MUST NOT attempt the reverse inference — reading a stored artefact to guess which key produced it, or silently substituting a key because a stored artefact appears to disagree with the one requested. Matching stored analyses to the keys they were measured under is data management, and belongs to whoever owns the corpus.

## Data Contracts

### Input
- `code_package: str` — the package that scopes app-owned classes, taken from `App.code_package` (the manifest package by default; the `PackageDetector` election when the user enabled it). Consumed by `StaticAnalysisParser` for class and window filtering, and passed to GATOR as `-clientParam codePackage=<value>`.
- `code_package_source: str` — `"manifest"` or `"detector"`, from `App.code_package_source`.

### Output
- The `sa_*` measurement block and the parsed `StaticAnalysisData`, scoped by `code_package` (destination: `rv-platform` coverage computation, results CSVs).
- The run's record of the analysis key: the `code_package` used and its `code_package_source`.

### Side-Effects
- **[Filesystem]**: the GATOR analysis JSON at `<results_dir>/<apk>.json`. Its `package` member holds the manifest package as GATOR read it, which is **not** necessarily the key that filtered the file's contents.

### Error
- No new error class. An analysis whose key matches no class in the APK completes and reports an empty catalogue; detecting that condition is the caller's responsibility, not the parser's.

## Invariants

- **INV-ANA-03**: The `StaticAnalysisParser` MUST receive `App.code_package` for class filtering, NOT `App.package_name`. The two are equal by default and differ only when the user enabled `PackageDetector`; the parser MUST NOT reason about which of the two produced the value. The parser MUST filter classes in the `reachability` section and windows in the `windows` section by verifying that class names contain the `code_package` string.

- **INV-ANA-14**: When — and only when — the user has enabled `PackageDetector`, it MUST apply detection heuristics in the following priority order: (1) same-as-manifest, (2) game engine detection, (3) single package, (4) common prefix, (5) most common (60%+ frequency), (6) string similarity (85%+ threshold), (7) manifest fallback. Each strategy returns early if a match is found. With the detector disabled — the default — none of these strategies MUST run.

- **INV-ANA-58**: No component of the analysis pipeline MUST derive a filtering key from an existing analysis artefact. The `package` member of a GATOR JSON is the manifest package as GATOR read it and MUST NOT be treated as the key that filtered that file. A run MUST record the key it used and its origin; it MUST NOT infer, repair, or override a key on the basis of a stored artefact.

## ADDED Requirements

### Requirement: Analysis Key Provenance Is Recorded, Never Inferred (FR04, FR05, FR06, NFR06)

Every static analysis run MUST record the package key it filtered on and the origin of that key (`manifest` or `detector`), at the time the analysis is performed, in the run's own output. The record exists because the analysis artefact cannot carry the information: GATOR writes the manifest package into the JSON's `package` member irrespective of the `codePackage` client parameter it was invoked with, so the file is silent about its own scope.

No component MUST attempt to recover the key from a stored artefact, and no component MUST substitute the caller's requested key with one derived from a stored artefact. When a previously produced JSON was measured under a different key than the current run resolves, the mismatch is a data-management fact about the corpus, and the tool MUST NOT resolve it silently in either direction.

#### Scenario: The key and its origin are recorded with the analysis

- **WHEN** a static analysis runs over `org.fossify.calendar_20.apk` with the detector disabled, so that the resolved key is the declared `org.fossify.calendar.debug`
- **THEN** the run's record MUST state the key `org.fossify.calendar.debug` and the origin `manifest`
- **AND** the same key MUST be the one passed to GATOR as `-clientParam codePackage=` and the one given to `StaticAnalysisParser`

#### Scenario: A stored artefact never supplies the key

- **WHEN** an analysis JSON exists at `<results_dir>/<apk>.json` whose `package` member reads `org.fossify.calendar.debug`, and a run re-parses it with a resolved key of `org.fossify.calendar`
- **THEN** the parser MUST filter using `org.fossify.calendar`, the key it was given
- **AND** the `package` member of the JSON MUST NOT be read as a filtering key, nor used to override the resolved one
