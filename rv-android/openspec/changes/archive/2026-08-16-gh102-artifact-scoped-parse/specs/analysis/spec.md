## Purpose

The analysis domain turns a GATOR analysis artefact into the method and window universe against which coverage is measured. This delta settles a question that the domain had been answering twice: **who decides which classes belong to the application under study.**

The answer is the producer, and it decides once. When rv-android runs a static analysis it passes `-clientParam codePackage=<key>` to GATOR, and GATOR removes from its output every class outside that key, reporting the count it removed. What lands in the JSON's `reachability` member is therefore already the application's own method universe — it *is* the 100% of coverage, the whole denominator. The member is named `reachability` because each of its entries carries reachability flags (`reachable`, `reachesTarget`, `directlyReachesTarget`); the name does not describe a subset relation, and the entries outside those flags are not somewhere else.

Until this change the consumer asked the question a second time. `StaticAnalysisParser` received a package key from its caller and dropped every class whose name did not contain it. That second filter is not a safety net: over an artefact scoped by the producer it can only be a no-op or a loss. Which of the two it is depends on whether the caller's key happens to agree with the producer's, and nothing guarantees that it does — the artefact deliberately does not record the key that filtered it (the `package` member is the manifest package as GATOR read it), and the caller resolves its key from the APK. When an application is built with `applicationIdSuffix`, the declared applicationId is strictly longer than its own class namespace, contains none of it, and the filter empties the universe. Coverage then reports zero over a run whose logcat is full of executed methods.

Windows are a different case, and the change keeps the distinction rather than flattening it. GATOR scopes `reachability` but does not scope `windows`, so framework and library activities (`androidx.activity.ComponentActivity`, `androidx.compose.ui.tooling.PreviewActivity`, `com.canhub.cropper.CropImageActivity`, `leakcanary.internal.activity.LeakActivity`) appear there and would inflate the activity denominator if admitted. The scoping test they need is already inside the artefact: an `ACTIVITY` window belongs to the application exactly when its class is present in `reachability`. That test needs no key, cannot disagree with the producer, and was verified to reproduce the key-based decision on every activity of the Estudo 03 corpus.

The result is that the consumption path stops holding an opinion about packages. Choosing a scope remains a real decision, but it belongs to whoever *runs* an analysis, is recorded when they run it, and is already baked into the artefact by the time anyone reads it.

## Data Contracts

### Input
- `analysis_file: str` — path to the GATOR analysis JSON, already scoped by the producer (`rv-static-analysis`, `rv-platform`)
- `data["reachability"]: list[dict]` — the application's complete method universe; each entry carries `className`, `methods`, `componentType`, `isMain` and the reachability flags
- `data["windows"]: list[dict]` — window descriptors of every type, **not** scoped by the producer

### Output
- `StaticAnalysisData.classes: Classes` — every entry of `reachability`, unfiltered
- `StaticAnalysisData.windows: Windows` — non-`ACTIVITY` windows unconditionally, plus `ACTIVITY` windows whose class is present in `reachability`

### Side-Effects
- **[Coverage]**: `LogcatRepository` denominators (`total_classes`, `total_methods`, `total_activities`, `total_reachable_methods`, `total_target_methods`) are the counts of the above, so any class dropped here is a method that coverage can never report as executed

### Error
- None added. A missing or unparseable section degrades to an empty section as it does today (INV-ANA-06).

## Invariants

- **INV-ANA-59**: The `StaticAnalysisParser` MUST load every entry of the `reachability` member of an analysis artefact and MUST NOT filter that member by any package key. The artefact is scoped by its producer, so the parsed method universe MUST equal the artefact's `reachability` member exactly, and the coverage denominator MUST equal that universe.
- **INV-ANA-60**: The `StaticAnalysisParser` MUST scope `ACTIVITY` windows by membership in the artefact's `reachability` member: an `ACTIVITY` window MUST be admitted if and only if its normalized class name is present there. Window types other than `ACTIVITY` MUST be admitted unconditionally, because they can be system-provided overlays triggered by application code. No package key MUST participate in this decision.
- **INV-ANA-61**: No function on the analysis **consumption** path — `StaticAnalysisParser.parse_file`, `read_static_analysis_files`, and their callers in `rv-platform` — MUST accept, resolve, or pass a package key. Resolving a scope is a **production**-path concern only.
- **INV-ANA-58** (narrowed): No component of the analysis pipeline MUST derive a filtering key from an existing analysis artefact. The `package` member of a GATOR JSON is the manifest package as GATOR read it and MUST NOT be treated as the key that filtered that file. A run that **performs** an analysis MUST record the key it used and its origin; it MUST NOT infer, repair, or override a key on the basis of a stored artefact. The invariant no longer constrains parsing, because parsing no longer uses a key.

## ADDED Requirements

### Requirement: The Analysis Artefact Defines Its Own Scope (FR04, FR05, FR06, FR12)

The parser MUST treat the analysis artefact as authoritative about which classes belong to the application. It MUST load the `reachability` member whole, and it MUST NOT apply any package-based filter to it. The producer already removed out-of-scope classes when it wrote the file; a second filter over that output cannot add information and can only remove some of it.

`ACTIVITY` windows MUST be scoped by membership in `reachability`, because the producer does not scope the `windows` member. Windows of other types MUST continue to be admitted unconditionally.

Neither `StaticAnalysisParser.parse_file` nor `read_static_analysis_files` MUST accept a package argument, and no caller on the consumption path MUST resolve one.

#### Scenario: An applicationId that scopes nothing no longer empties the universe

- **WHEN** `io.keepalive.android_133.apk.json` is parsed, whose `package` member reads `io.keepalive.android.debug` while its 203 `reachability` entries are named `io.keepalive.android.*`
- **THEN** the parser MUST report 203 classes and 949 methods
- **AND** `LogcatRepository` MUST be initialized with those 203 classes and 949 methods
- **AND** `cov_method` MUST be computed over 949 as denominator, so a run whose logcat carries `RVSEC-COV` lines MUST NOT report `0.00`

#### Scenario: A framework activity present in windows but absent from reachability is excluded

- **WHEN** an artefact lists `androidx.compose.ui.tooling.PreviewActivity` as an `ACTIVITY` window and does not list it in `reachability`
- **THEN** that window MUST NOT be admitted
- **AND** it MUST NOT be counted in `total_activities`, so `cov_act` MUST NOT be diluted by an activity the application does not own

#### Scenario: A non-ACTIVITY window is admitted regardless of reachability

- **WHEN** an artefact lists a `DIALOG` window whose class is absent from `reachability`
- **THEN** that window MUST be admitted, because a dialog can be a system-provided overlay triggered by application code

#### Scenario: The consumption path carries no key

- **WHEN** `rv-platform` loads static data for a task, or re-parses the artefact while reconstructing a repository from logcat on resume
- **THEN** it MUST call `read_static_analysis_files` with the results directory and APK name only
- **AND** it MUST NOT read `App.code_package`, so the parsed universe MUST be identical whether or not `PackageDetector` is enabled for the run

## MODIFIED Requirements

### Requirement: Analysis Key Provenance Is Recorded, Never Inferred (FR04, FR05, FR06, NFR06)

Every static analysis run MUST record the package key it filtered on and the origin of that key (`manifest` or `detector`), at the time the analysis is performed, in the run's own output. The record exists because the analysis artefact cannot carry the information: GATOR writes the manifest package into the JSON's `package` member irrespective of the `codePackage` client parameter it was invoked with, so the file is silent about its own scope.

The requirement governs the **production** path only. A run that performs an analysis chooses a scope, passes it to GATOR as `-clientParam codePackage=`, and records it. A run that merely reads an artefact chooses nothing: it consumes the file at the scope the producer gave it, so there is no key to record, to recover, or to disagree about. When two artefacts of a corpus were produced under different keys, that remains a data-management fact about the corpus, and no component MUST resolve it silently in either direction.

#### Scenario: The key and its origin are recorded with the analysis

- **WHEN** a static analysis runs over `org.fossify.calendar_20.apk` with the detector disabled, so that the resolved key is the declared `org.fossify.calendar.debug`
- **THEN** the run's record MUST state the key `org.fossify.calendar.debug` and the origin `manifest`
- **AND** the same key MUST be the one passed to GATOR as `-clientParam codePackage=`

#### Scenario: A stored artefact never supplies a key, because none is wanted

- **WHEN** an analysis JSON exists at `<results_dir>/<apk>.json` whose `package` member reads `org.fossify.calendar.debug`, and a later run parses it
- **THEN** the parser MUST load the artefact at the scope its producer gave it
- **AND** the `package` member MUST NOT be read as a filtering key, and no other key MUST be resolved for the parse

## REMOVED Requirements

### Requirement: Class and Window Filtering by `code_package` (INV-ANA-03)

**Reason**: The rule required `StaticAnalysisParser` to receive `App.code_package` and to filter the `reachability` and `windows` members by substring containment of that key. The filter re-scoped an artefact that its producer had already scoped, which cannot add information. Measured over the Estudo 03 corpus of 162 APKs: 0 of 215430 parsed classes fell outside the producer key, so the class filter never removed anything legitimate, while for the 75 applications built with `applicationIdSuffix` it removed everything and drove measured coverage to zero. Where a resolved key was longer than the producer key it silently truncated the denominator instead (7987 classes to 78 for `org.wikipedia_50595`; 3171 to 140 for `com.jerboa_87`).

INV-ANA-03 is deleted, not weakened or made conditional (P3). Its useful half — keeping framework activities out of the activity denominator — is preserved by INV-ANA-60, which derives the same decision from the artefact instead of from a key, and which reproduces the key-based decision on 1526 of 1526 activities across the corpus.

**Migration**: None. `parse_file` and `read_static_analysis_files` lose their package parameter and callers stop supplying one. `App.code_package` itself is unchanged and remains in use on the production path and by `rv-instrumentation-ajc`.
