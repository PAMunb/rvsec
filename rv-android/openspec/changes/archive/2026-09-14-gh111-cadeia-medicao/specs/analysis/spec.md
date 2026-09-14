## Purpose

The analysis capability produces and consumes the **coverage denominator**: the set of classes and methods that a run treats as the application's own, together with three reachability predicates over each method. Everything downstream — the crossing against runtime events, the `cov_class` and `cov_method` columns, the comparisons between tools — is a fraction whose bottom half this capability decides.

Producing that denominator is a two-stage classification inside GATOR, and the two stages are answered by **different scope keys**. Soot marks every class it reads from the APK's DEX files as an application class; `AnalysisEntrypoint` then demotes some of them to library, guarded by the package name it reads from the manifest; and `RvsecAnalysisClient` filters what survived, preferring the `codePackage` client parameter over the manifest. When the manifest package is not a prefix of any compiled class — which happens in every APK built with a Gradle `applicationIdSuffix`, and in 75 of the 162 artefacts of the article corpus — the guard is dead, and any class the library deny-list matches is demoted. Four corpus artefacts collapse to 1, 2, 6 and 21 classes this way, and two of them publish `cov_class = 100.00%`. This change makes both stages answer to the same key.

Consuming the denominator is the parser's job, and it has been transforming what it reads. `SignatureNormalizer` converts a dot to a dollar whenever both sides start with an uppercase letter, on the theory that GATOR might emit inner classes in dotted form. GATOR does not: `SootClass.getName()` is the JVM binary name, so every dot between two capitalized segments in its output is a **package boundary**, and the heuristic is always wrong there. Both weavers that produce the runtime side emit the same binary name — dexlib2 converts the DEX descriptor at the emission point, ajc reads `Class.getName()` — so the two sides of the crossing already agree byte for byte, and the normalizer is the only thing that breaks the agreement. It is applied to the class name and not to the method signature, so when it fires it produces an internally inconsistent record.

The third theme is accounting. The crossing discards unmatched classes and unmatched signatures at `logger.debug` with no counter; `ParserDiagnostics` counts several conditions and is never serialized; `_percentage` returns `0.0` for `0/0`, so an empty denominator is indistinguishable from an application that covered nothing, and a degenerate denominator of one class publishes 100%. No repair in this chain is verifiable until the chain says what it dropped.

## Data Contracts

### Input
- `codePackage: str` — the scope key, delivered to GATOR as `-clientParam codePackage=<value>` (source: `rv-static-analysis/config.py:395-397`, ultimately `App.code_package`)
- `codePackageSource: str` — the key's origin (`manifest`, `manifest-neutralized` or `detector`), delivered on its own client parameter beside the key, because nothing else carries it across the boundary (INV-ANA-66)
- `manifestLocation: str` — path to the decoded `AndroidManifest.xml` (source: apktool output; read by `AnalysisEntrypoint.java:87-94`)
- `libraryPackageFile: str` — path to `libPackages.txt`, 2,170 patterns (source: `rv-android/lib/gator/gator:95`, passed unconditionally)
- `reachability[]: list[dict]` — the artefact member holding `className` (JVM binary name) and `methods[].signature` (complete Soot signature `<class: retType name(p1,p2)>`)

### Output
- `code_package: str` and `code_package_source: str` — the effective scope key and its origin, recorded in the analysis artefact
- `class_defs_under_key: int` — the number of compiled classes under the effective key that survive `isAppClass`, counted at write time and recorded in the analysis artefact (INV-ANA-66); it is a **net** count, never the raw one
- `Classes` / `Windows` domain objects — class names and signatures **as the artefact spells them**, with no transformation
- `ParserDiagnostics` — discard counters split by scope, serialized

### Side-Effects
- **[GATOR]**: `SootClass.setLibraryClass()` mutates the Scene; the demotion is irreversible within the run
- **[Filesystem]**: the analysis artefact records the key that produced it and the compiled-class count under that key
- **[Filesystem]**: a stored artefact whose recorded key differs from the run's effective key is regenerated rather than reused

### Error
- `DenominatorImplausibleError` — raised when the denominator gate refuses an empty or degenerate result

## Invariants

- **INV-ANA-65**: `AnalysisEntrypoint` MUST resolve the package that guards the application/library demotion from `Configs.getClientParamCode("codePackage=")`, falling back to the manifest `package` attribute only when the client parameter is absent. The guard at `AnalysisEntrypoint.java:119` and the filter at `RvsecAnalysisClient.java:90` MUST resolve to the same value in every run, so that the set the guard protects is exactly the set the client will filter.

- **INV-ANA-66**: The analysis artefact MUST record the scope key that produced it, that key's origin, and the count of compiled classes under that key. The `package` member MUST continue to hold the manifest package as GATOR read it (INV-ANA-58 unchanged), and the effective key MUST be recorded in a distinct member, so that no reader has to infer one from the other. The count — `class_defs_under_key` — MUST be recorded beside the key, because it is what makes the denominator gate a **pure predicate over the artefact**: evaluable at every consumption point, including resume and `--process-results`, which re-parse `.apk.json` with no APK within reach. It MUST be produced by applying `RvsecAnalysisClient.isAppClass` — the very predicate that filters the parsed side — to the compiled universe under the key, which the client reads from `Scene.getClasses()`; the demotion does not shrink that set, because `setLibraryClass()` reclassifies a class without removing it. One predicate, both sides: the ratio the gate computes then compares like with like by construction, and no consumer is asked to perform a subtraction for which it holds a count and not the names. The origin MUST reach the producer on a channel of its own, `-clientParam codePackageSource=<manifest|manifest-neutralized|detector>`: `codePackage=` is today the only key that crosses that boundary, `code_package_source` lives on the Python side in a log line the run does not even write to disk (INV-CORE-62), and nothing else carries it.

- **INV-ANA-67**: The `StaticAnalysisParser` MUST store class names, window names and method signatures exactly as the artefact spells them. No normalization, repair or transformation of any identifier MUST occur on the consumption path. The producers of both sides of the crossing emit the JVM binary name, so any transformation applied to one side alone breaks an agreement that already holds.

- **INV-ANA-68**: `ParserDiagnostics` MUST count every discarded runtime event, separating **out-of-scope** discards (the class is not under the effective scope key — the application did not own it) from **in-scope** discards (the class is under the key but absent from the denominator, or present with a signature that does not match), with a third counter, **unclassified**, for discards under a key of `None` (INV-CORE-60). The three are different failures and MUST NOT be summed with each other. None of the three MUST enter `ParserDiagnostics.discarded_lines` (`domain/coverage.py:541-556`): they count lines that **did** become records, the same reason that property already excludes the sentinel and grammar counters — so the INV-ANA-62 identity (records registered plus counted lines equals lines read) holds unchanged. The counters MUST be serialized by `to_dict()`; `unmatched_out_of_scope` and `unmatched_in_scope` MUST reach the run's CSV output as columns (INV-PLT-34), while `unmatched_unclassified` is serialized but has no published column — a row with no key is `measured=false`, which already carries the fact (INV-PLT-36).

- **INV-ANA-69**: The denominator gate MUST refuse three distinct conditions and MUST fail loudly rather than publishing a percentage: an **empty** denominator (`reachability` holds no entries); a **compiled universe of zero** (`class_defs_under_key == 0`, which under the default policy is the state of 75 of the 162 corpus APKs and makes `parsed / compiled_under_key` a `ZeroDivisionError` rather than a refusal); and a **degenerate** denominator, whose ratio of parsed to compiled classes under the key falls below `0.15`. The ratio MUST be computed over a compiled count that `isAppClass` has already filtered at write time (INV-ANA-66), so that both of its terms answer to one predicate. The gate divides; it MUST NOT attempt a subtraction of its own, holding a count and not the names. A denominator of one class out of a compiled universe of 771 is not empty, and a gate testing only for emptiness would have admitted all four of the collapsed corpus artefacts. The gate covers the **class** universe only: `cov_reachable`, `cov_reaches_target` and `cov_directly_reaches_target` are published columns carrying denominators of their own that the gate does not inspect, and those denominators still answer to `libPackages.txt` — the demotion shapes `Hierarchy.appClasses` (`Hierarchy.java:305` → `FlowgraphRebuilder.java:72`), and from it the `reachable`, `reachesTarget` and `directlyReachesTarget` predicates. What the repair of INV-ANA-65 takes away from the deny-list is the **class** denominator, not those three.

- **INV-ANA-70**: A stored analysis artefact MUST NOT be reused as a cache hit unless the key it records equals the run's effective scope key. Today `StaticAnalyzer._execute_command` treats the mere **existence** of `<apk>.apk.json` as a hit (`static_analysis.py:323-335`, whose comment states *"We do not validate content"*); the filename carries no key (`:198-200`); and the artefact's `package` member holds the manifest package whatever key filtered the file — so nothing recovers the producing key. The standalone `--force` flag was dead code — declared at `modules/rv-static-analysis/src/rv_static_analysis/__main__.py:214` and `:236` and never read — so before this change no invalidation path existed at all. This change makes it real: `--force` MUST discard the artefact the cache would answer with, before the analysis runs, and it is the one **deliberate** invalidation path. The key comparison is the automatic one, and the two are not substitutes: the comparison fires only when the keys disagree, and an operator re-measuring the same key against a rebuilt jar needs a way to say so. A run whose scope-key policy changed MUST regenerate the artefact or abort naming both keys; it MUST NOT evaluate an artefact produced under one key against another, which is exactly what a denominator gate wired over a stale cache hit would do.

- **INV-ANA-71**: Generated resource classes MUST leave the denominator at **every** package segment, not only at the scope key's root. `RvsecAnalysisClient.isAppClass` takes the suffix left after the key and tests it against `.R`, `.R$*` and `.BuildConfig`, so it removes `<key>.R` and keeps `<key>.<module>.R` — and a key that is an *ancestor* of the resource namespace escapes it entirely. Measured over the 162 corpus artefacts, **505** such classes sit in the denominator today (117 in `app.pachli_50` alone, 33 in `com.blacksquircle.ui_10028`), carrying 547 methods of which **zero** are non-trivial: they are constant tables with nothing to cover, and their only effect is to depress `cov_class`. The test MUST therefore be on the **last segment** of the class name — `R`, `R$*`, `BuildConfig`, `Manifest`, `Manifest$*` — wherever that segment sits under the key. Output of annotation processors (`_Factory`, `_Impl`, `_MembersInjector`, `$$serializer`, `Hilt_*`, `Dagger*`, DataBinding) is deliberately **not** covered: 5,816 such classes carry 36,264 non-trivial methods that execute at runtime, so removing them would redefine the denominator rather than close a leak. That measurement is recorded as an open question, not acted on here. **BREAKING for measurement.**

- **INV-ANA-60**: **AMENDED.** The base invariant (`openspec/specs/analysis/spec.md:394`) admits an `ACTIVITY` window if and only if its **normalized** class name is present in `reachability`. INV-ANA-67 forbids any normalization on the consumption path, so the word *normalized* MUST be struck from INV-ANA-60 when this change is archived, or the two invariants contradict each other in the merged specification. Both sides of that membership test are compared in the artefact's own spelling; nothing else in INV-ANA-60 changes.

- **INV-ANA-02**: **WITHDRAWN.** The invariant mandates that `StaticAnalysisParser` apply `SignatureNormalizer` to all class names and method signatures. Verification shows the transformation is always wrong on well-formed GATOR output and has no correct case in this pipeline. It was written on the belief — recorded in `docs/NOVO/06_normalizacao_inner_classes.md`, a document external to this repository's tree, cited as provenance only — that AspectJ emits a dollar where Soot emits a dot. Today's aspect cannot settle that question, because it is not the aspect that produced the data in dispute: the corpus in question was woven by an aspect reading `thisJoinPointStaticPart.getSignature().getDeclaringTypeName()` and emitting the `%s:::%s:::%s` form (`git show 16ca70b2^:rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj:40`) — the very API the old framing nominated as the culprit. What settles it is the raw logcat: of the 17 distinct `RVSEC-COV` class names recorded for `com.hwloc.lstopo_271`, every dollar sits at genuine nesting (`About$1`, `MainActivity$MenuItems`) and every package boundary is a dot (`com.hwloc.lstopo.ZoomView.ZoomView`). The spurious dollar never existed in the logcat, so it came from the normalizer itself. The invariant is also unenforceable as written: it claims the normalizer is applied in all three JSON sections and to method signatures, and the implementation applies it to two sections and to no signature. INV-ANA-67 replaces it with the opposite rule.

## ADDED Requirements

### Requirement: The Demotion Guard Resolves Scope From the Code Key

`AnalysisEntrypoint` SHALL guard the application-to-library demotion with the same scope key the analysis client uses to filter its results. It MUST read `Configs.getClientParamCode("codePackage=")` and MUST fall back to the manifest `package` attribute only when that client parameter is absent. `Configs.clientParams` is populated by `Main.main` before `setupAndInvokeSoot()` runs, so no new dependency between `sootandroid` and `client` is introduced.

The rescue branch that admits classes named in an `<activity>` element MUST remain unchanged. With the guard repaired it stops being load-bearing for application classes and becomes what it was written to be — a safety net for components Soot misclassified — so widening it to services, receivers and providers MUST NOT be part of this change.

#### Scenario: An APK whose manifest package carries a build-type suffix
- **WHEN** `br.com.colman.petals_3040000.apk` is analysed with manifest `package = br.com.colman.petals.debug` and `-clientParam codePackage=br.com.colman.petals`
- **THEN** the guard MUST protect the 771 classes under `br.com.colman.petals`
- **AND** the `libPackages.txt` pattern `br.com.*` MUST NOT demote them
- **AND** the artefact MUST report 762 application classes instead of 1 — the 771 the guard protects, minus the nine generated classes (`.R`, `.R$*`) that `RvsecAnalysisClient.isAppClass` strips before writing

#### Scenario: An APK whose code package matches no library pattern
- **WHEN** `app.pachli_50.apk` is analysed with manifest `package = app.pachli.current` and `codePackage = app.pachli`
- **THEN** the application class count MUST be 6467 both before and after the repair
- **AND** the repair MUST be invariant for every application whose package matches no `libPackages.txt` pattern

#### Scenario: The client parameter is absent
- **WHEN** GATOR is invoked without `-clientParam codePackage=`
- **THEN** the guard MUST use the manifest `package` attribute
- **AND** the demotion MUST proceed exactly as it does under a manifest-key guard: no class protected or demoted differently than when the parameter is never supplied

### Requirement: The Artefact Records the Key That Produced It

A run that performs an analysis SHALL record the effective scope key and its origin in the artefact it writes. The `package` member MUST keep holding the manifest package as GATOR read it, because INV-ANA-58 forbids treating it as the filtering key; the effective key MUST occupy a distinct member so that the two are never conflated.

Measured over the 162 artefacts of the article corpus, zero classes start with the recorded `package` and 162 of 162 start with the neutralized key — the artefact today records a value that describes nothing about its own contents.

The run SHALL also record `class_defs_under_key`: the number of compiled classes whose name starts with the effective key, counted from the `class_defs` tables of the APK's DEX files at the moment the artefact is written. The reason is the wiring site of the denominator gate. The gate needs two numbers — what was parsed and what was compiled — and only the producer holds both: the parser's entry points are `parse_file(file_path)` (`static_analysis_parser.py:205`) and `read_static_analysis_files(results_dir, apk)` (`:267-286`, where `apk` is a filename **string**), so neither sees an APK, and INV-ANA-61 forbids passing a package key into that module at all (its docstring states *"No package key reaches this module"*). Recording the count at write time resolves that contradiction instead of arguing with it: the gate becomes a **pure predicate over the artefact**, evaluable wherever the artefact is read — including resume and `--process-results`, which re-parse `.apk.json` long after the APK is out of reach.

#### Scenario: A run with a neutralized key
- **WHEN** an analysis runs with manifest package `org.fossify.paint.debug` and effective key `org.fossify.paint`
- **THEN** the artefact `package` member MUST be `org.fossify.paint.debug`
- **AND** the artefact MUST record `org.fossify.paint` as the effective key
- **AND** it MUST record the origin of that key

#### Scenario: The artefact carries its own compiled-class count
- **WHEN** `br.com.colman.petals_3040000.apk` is analysed with effective key `br.com.colman.petals`, and 771 compiled classes carry a name starting with that key, nine of them generated resource classes
- **THEN** the artefact MUST record `class_defs_under_key = 762` beside the effective key — the count after `isAppClass`, the same predicate that filtered the parsed side
- **AND** it MUST NOT record the raw 771, which no consumer could correct: the gate receives a count, never the names it would need to filter
- **AND** a later `--process-results` run over the same results directory MUST be able to evaluate the denominator gate from the artefact alone, with no APK on hand and no package key passed to the parser

### Requirement: Generated Resource Classes Leave the Denominator at Every Segment

The analysis client SHALL exclude generated resource classes from the classes it writes, testing the **last segment** of each class name rather than the suffix that follows the scope key.

The filter exists and is correct in intent; it leaks by construction. `isAppClass` computes `className.substring(filterPackage.length())` and compares that suffix to `.R`, `.R$*` and `.BuildConfig`, which answers only for a resource class sitting directly under the key. Two shapes escape it, and both are ordinary: a multi-module application, whose modules each generate their own `R` (`app.pachli.core.database.R`, `com.blacksquircle.ui.feature.editor.R$drawable`), and a scope key that is an ancestor of the resource namespace, where the whole suffix `.screenshottile.R` matches none of the three patterns.

These classes are not app code by any reading: over the 162 corpus artefacts their 547 methods contain **zero** non-trivial members — no method that a test could call, nothing to cover — so their entire contribution is to enlarge the `cov_class` denominator with classes whose coverage can never rise above zero.

#### Scenario: A multi-module application

- **WHEN** `app.pachli_50.apk` is analysed with effective key `app.pachli` and its compiled classes include `app.pachli.core.database.R` and `app.pachli.feature.intentrouter.R$id`
- **THEN** neither class MUST appear in `reachability`
- **AND** the 117 classes of that shape now present in the artefact MUST all be absent
- **AND** `class_defs_under_key` MUST be counted with the same predicate, so the gate's ratio is unaffected by the repair

#### Scenario: A scope key that is an ancestor of the resource namespace

- **WHEN** `com.github.cvzi.screenshottile_148.apk` is analysed under the detector-elected key `com.github.cvzi`, and the application's resource classes are named `com.github.cvzi.screenshottile.R` and `…R$*`
- **THEN** those classes MUST NOT be counted, even though the suffix left after the key is `.screenshottile.R` and matches no root-anchored pattern
- **AND** the denominator asserted for this APK MUST be the value measured **after** this repair — the pre-repair 550 counted the leaked resource classes and MUST NOT be carried forward as the expected number

#### Scenario: Annotation-processor output stays

- **WHEN** an artefact holds `com.example.MainViewModel_Factory`, `com.example.AppDatabase_Impl` and `com.example.Model$$serializer`
- **THEN** all three MUST remain in the denominator
- **AND** the rule MUST NOT be widened to them by analogy, because they carry methods that execute at runtime and their removal would be a redefinition of what the denominator means


### Requirement: The Crossing Counts What It Discards

The coverage crossing SHALL count every runtime event it does not register, and SHALL classify each discard as out-of-scope or in-scope. An out-of-scope discard means the event's class does not start with the effective key — the application does not own that code, and the discard is correct. An in-scope discard means the class is under the key but the denominator does not contain it, or contains it under a signature that does not match — which is a defect in the chain and MUST be visible.

Both counts SHALL be serialized and SHALL reach the run's CSV output. Without them no repair in this chain is verifiable, and no scope-key rule is safe, because no rule is total.

#### Scenario: A runtime event from a bundled library
- **WHEN** `RVSEC-COV` reports `<okhttp3.internal.Util: void closeQuietly(java.io.Closeable)>` and the effective key is `br.com.colman.petals`
- **THEN** the event MUST be discarded
- **AND** the out-of-scope counter MUST be incremented
- **AND** the in-scope counter MUST NOT be incremented

#### Scenario: A runtime event whose class is in scope but absent from the denominator
- **WHEN** `RVSEC-COV` reports a method of `br.com.colman.petals.settings.SettingsWorker`, the effective key is `br.com.colman.petals`, and that class is not present in the artefact's `reachability` member
- **THEN** the event MUST be discarded
- **AND** the in-scope counter MUST be incremented
- **AND** the counter MUST be serialized in the parser diagnostics and MUST appear in `summary.csv`

### Requirement: The Denominator Gate Refuses Empty and Degenerate Results

The analysis pipeline SHALL apply a plausibility gate to every denominator it produces or consumes, and the gate SHALL fail loudly. The gate reads the two numbers the artefact records — the size of its `reachability` member and `class_defs_under_key` — and it MUST refuse three conditions, each named separately in the failure:

1. **An empty denominator**: `reachability` holds no entries.
2. **A compiled universe of zero**: `class_defs_under_key == 0`. This MUST be tested as its own refusal case, before any division. It is not a corner case — the build-type suffix policy defaults to `False` and 75 of the 162 corpus APKs have zero compiled classes under their manifest key, so a gate written as `parsed / compiled_under_key` raises `ZeroDivisionError` in the default configuration instead of `DenominatorImplausibleError`, and reports nothing about the key that produced the state.
3. **A degenerate denominator**: the ratio of parsed classes to compiled classes under the key falls below `0.15` — the condition that publishes `cov_class = 100.00%` over one class.

The ratio SHALL be computed over a compiled count already filtered by `isAppClass` at write time (INV-ANA-66) — one predicate on both terms. Without that, the raw ratio is depressed by exactly the application's resource classes, which `isAppClass` strips from the parsed side alone. Measured over all 162 corpus artefacts, the raw healthy floor is `0.5610` (`org.cry.otp_31`, 23 of 41) and 17 of 158 healthy applications sit below `0.90` — among them `com.tananaev.passportreader`, at 18 of 28, whose ten missing classes are its `.R` plus nine `R$*`. The claim that healthy small applications sit at 100% is therefore false on the raw counts and true only after the subtraction. With the subtraction applied, all 158 healthy artefacts sit at exactly 1.0 (the corrected ratio is the client's own filter re-derived, so the agreement is exact) and the four collapsed artefacts sit between 0.0010 and 0.0393, so a threshold of `0.15` stands 3.8× above the collapsed ceiling and 6.7× below the healthy floor, inside a 25.5× separation, rather than being calibrated against either band. The calibration holds under the **neutralized** key: under the literal manifest key, 75 of the 162 have no compiled class at all (a `0/0` is not a low ratio, it is the zero-universe refusal above).

The gate covers the **class** universe only. `cov_reachable`, `cov_reaches_target` and `cov_directly_reaches_target` are published columns with denominators of their own (`reachable_methods_total`, `target_methods_total`) that the gate does not check; those predicates are shaped by `Hierarchy.appClasses` (`Hierarchy.java:305` → `FlowgraphRebuilder.java:72`), which `libPackages.txt` continues to govern even after the demotion guard is repaired. The repair takes the deny-list out of the **class** denominator, not out of those three.

The gate is an instrument of detection, not a redefinition of the denominator: the list GATOR produces inside the informed package remains the 100% by definition.

The 162 artefacts already on disk carry neither a recorded key nor `class_defs_under_key`, and `modules/rv-platform/src/rv_platform/components/result_processor.py:245-325` re-parses `.apk.json` on every resume and on every `--process-results` run, so these artefacts remain live inputs. An artefact that records no key SHALL be treated as one whose key is unknown, never as one whose key can be recovered: the key is `None`, the gate does not run, and the accounting degrades honestly rather than guessing. The key MUST NOT be re-derived from the artefact's `package` member — INV-ANA-58 forbids it, and re-derivation reproduces precisely the defect the recorded key exists to expose.

#### Scenario: A collapsed denominator
- **WHEN** an artefact for `br.com.colman.petals_3040000.apk` reports 1 class in `reachability` and records `class_defs_under_key = 762` under the effective key `br.com.colman.petals`
- **THEN** the ratio MUST be `1 / 762 ≈ 0.0013`, below the `0.15` threshold
- **AND** the gate MUST refuse the artefact
- **AND** the run MUST fail with a message naming the class count, the compiled count and the effective key
- **AND** the pipeline MUST NOT publish a coverage percentage for that APK

#### Scenario: An empty denominator
- **WHEN** an artefact's `reachability` member is empty
- **THEN** the gate MUST refuse the artefact
- **AND** the failure MUST name the effective key, because an empty result is the signature of a key that matches nothing

#### Scenario: No class is compiled under the effective key
- **WHEN** an artefact records `class_defs_under_key = 0` for effective key `br.com.colman.petals.debug`, the state of 75 of the 162 corpus APKs while the suffix-stripping policy is `False`
- **THEN** the gate MUST refuse the artefact on that condition alone, before computing any ratio
- **AND** the failure MUST name `br.com.colman.petals.debug` as the key under which zero classes were counted
- **AND** the run MUST NOT raise `ZeroDivisionError`

#### Scenario: A genuinely small application
- **WHEN** an artefact for `com.tananaev.passportreader` reports 18 classes in `reachability` and records `class_defs_under_key = 18`, its 28 compiled classes minus the ten generated ones — one `com.tananaev.passportreader.R` and nine `R$*` — that `isAppClass` removed at write time
- **THEN** the ratio MUST be `18 / 18 = 1.00`, above the `0.15` threshold
- **AND** the gate MUST admit the artefact with no warning
- **AND** the raw ratio `18 / 28 = 0.6429` MUST NOT be what the artefact records, because it would report a healthy application as an outlier

#### Scenario: A legacy artefact that records no key
- **WHEN** a resume or a `--process-results` run re-parses one of the 162 existing artefacts, which carries neither a recorded effective key nor `class_defs_under_key`
- **THEN** the effective key for that task MUST be `None`
- **AND** the gate MUST NOT run, because it has no compiled count to test against
- **AND** every discard MUST be counted as **unclassified**, not attributed to the in-scope counter, since without a key neither scope can be decided
- **AND** the two `unmatched_*` columns of that row MUST be empty, because no classification was possible
- **AND** the coverage cells MUST still be computed from the artefact's own denominator: the effective key classifies discards and nothing else, and all 162 stored artefacts carry a non-empty `reachability` (from 1 to 14,860 classes). Emptying their coverage would delete, on every resume and every `--process-results`, the measurement INV-PLT-15 and INV-PLT-16 exist to recover. `measured` answers to the denominator alone (INV-PLT-35), never to the presence of a recorded key
- **AND** no component MUST re-derive the key from the artefact's `package` member

### Requirement: A Stored Artefact Is Reused Only Under Its Own Key

A run that finds an analysis artefact already on disk SHALL compare the key that artefact records against the run's own effective scope key, and SHALL NOT reuse it silently when the two differ. It MUST either regenerate the artefact or abort with a message naming both keys.

Nothing in the pipeline today can make that comparison. `StaticAnalyzer._execute_command` treats the mere existence of `<apk>.apk.json` as a cache hit (`static_analysis.py:323-335`), and the code says so out loud: *"We do not validate content -- existence implies a previous run completed"*. The filename carries no key (`:198-200`), and neither does the content: the artefact's `package` member is the **manifest** package whatever key actually filtered the file. Before this change there was no invalidation path either — the standalone `--force` flag was declared twice at `modules/rv-static-analysis/src/rv_static_analysis/__main__.py:214` and `:236` and never read, so the only way to invalidate a stale artefact was to delete it by hand.

The consequence is specific to this change: a re-run whose scope-key policy changed reuses the artefact produced under the old policy, and the new denominator gate then evaluates an old artefact against a new key. The recorded key of INV-ANA-66 is what makes that mismatch detectable instead of invisible.

#### Scenario: A re-run under a changed scope-key policy
- **WHEN** `results/<id>/br.com.colman.petals_3040000.apk.json` records effective key `br.com.colman.petals.debug`, and the run is re-executed with the suffix-stripping policy enabled so that its effective key is `br.com.colman.petals`
- **THEN** the stored artefact MUST NOT be treated as a cache hit
- **AND** the run MUST regenerate it, or abort with a message naming both `br.com.colman.petals.debug` and `br.com.colman.petals`
- **AND** the denominator gate MUST NOT be evaluated over the stored artefact under the new key

#### Scenario: A re-run under the same key
- **WHEN** the stored artefact records effective key `app.pachli` and the run's effective key is `app.pachli`
- **THEN** the artefact MUST be reused as a cache hit, with GATOR not re-executed
- **AND** the reuse MUST follow the existing cache-hit path unchanged — the key comparison adds a condition to reuse, never a new way of reusing

#### Scenario: An explicit request to discard the cache
- **WHEN** the stored artefact records effective key `com.github.cvzi.screenshottile` and the run's effective key is the same, but the run is invoked with `--force`
- **THEN** the stored artefact MUST be discarded before the analysis runs, and GATOR MUST be re-executed
- **AND** the log MUST show `Executing analysis`, never `Analysis result already exists`
- **AND** this is the only path by which a matching key is deliberately not honoured — an A/B over one directory, or a re-measurement against a rebuilt jar, has no other way to say "measure again"

## MODIFIED Requirements

### Requirement: The Analysis Artefact Defines Its Own Scope (FR04, FR05, FR06, FR12)

The parser MUST treat the analysis artefact as authoritative about which classes belong to the application. It MUST load the `reachability` member whole, and it MUST NOT apply any package-based filter to it. The producer already removed out-of-scope classes when it wrote the file; a second filter over that output cannot add information and can only remove some of it.

The parser MUST also treat the artefact as authoritative about **how those classes are spelled**. It MUST store every class name, window name and method signature exactly as the artefact writes it, and MUST NOT apply `SignatureNormalizer` or any other transformation to an identifier on the consumption path. GATOR emits `SootClass.getName()`, the JVM binary name, in which a dot is always a package boundary and a dollar is always genuine nesting; both runtime producers emit the same form — the dexlib2 weaver converts the DEX type descriptor to a dotted FQN inside `SignatureFormatter.toFqn` before emitting, and the ajc aspect reads `method.getDeclaringClass().getName()`. The two sides of the crossing therefore agree without normalization, and the heuristic that converts a dot to a dollar when both adjacent segments start with an uppercase letter is always wrong at a capitalized package segment. The transformation was also applied inconsistently — to the class name and not to the method signature stored beside it — so when it fired it produced a record whose two halves disagreed.

`ACTIVITY` windows MUST be scoped by membership in `reachability`, because the producer does not scope the `windows` member. Windows of other types MUST continue to be admitted unconditionally. Both sides of that comparison MUST be read in the artefact's own spelling, which is why the two transformation sites are removed together: removing only the class-name site would leave windows dollar-separated and classes dotted, silently changing which activities are admitted.

Neither `StaticAnalysisParser.parse_file` nor `read_static_analysis_files` MUST accept a package argument, and no caller on the consumption path MUST resolve a **filtering** key for the parse. The **classification** key the crossing uses (INV-CORE-60) is a different thing: it is read from the artefact's own record (INV-ANA-66), never resolved from outside, and it filters nothing — reading a recorded key is not resolving one.

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

#### Scenario: A capitalized package segment is stored as written

- **WHEN** the artefact for `com.hwloc.lstopo_80283.apk` contains `className = com.hwloc.lstopo.ZoomView.ZoomView`, where `ZoomView` is both a package and a class
- **THEN** the parser MUST store `com.hwloc.lstopo.ZoomView.ZoomView`
- **AND** it MUST match the 1080 `RVSEC-COV` events that name the same string across the 99 archived logcats
- **AND** the previously produced `com.hwloc.lstopo.ZoomView$ZoomView`, which matched zero events in 99 of 99 logcats, MUST NOT occur

#### Scenario: A genuine inner class keeps its dollar

- **WHEN** the artefact contains `className = com.hwloc.lstopo.ZoomView.ZoomView$ZoomViewListener`
- **THEN** the parser MUST store it unchanged
- **AND** the dollar MUST survive, because the producer already spelled the nesting

#### Scenario: Windows and classes are compared in one spelling

- **WHEN** an `ACTIVITY` window named `br.com.colman.petals.MainActivity` is checked against the `reachability` member
- **THEN** both sides MUST be compared in the artefact's own spelling
- **AND** the admission decision MUST be unchanged from the artefact's point of view

### Requirement: Analysis Key Provenance Is Recorded, Never Inferred (FR04, FR05, FR06, NFR06)

Every static analysis run MUST record the package key it filtered on and the origin of that key (`manifest`, `manifest-neutralized` or `detector`), at the time the analysis is performed, in the run's own output — and, with this change, in the analysis artefact itself (INV-ANA-66). GATOR keeps writing the manifest package into the JSON's `package` member irrespective of the `codePackage` client parameter (INV-ANA-58 unchanged); the effective key now occupies a distinct member beside it, so the artefact stops being silent about its own scope.

The requirement still governs the **production** path: a run that performs an analysis chooses a scope, passes it to GATOR as `-clientParam codePackage=`, and records it. A run that merely reads an artefact still chooses nothing — it consumes the file at the scope the producer gave it — but where the artefact carries a record, that record is now read: it classifies discards at the crossing (INV-CORE-60) and feeds the denominator gate (INV-ANA-69), and a stored artefact is reused as a cache hit only under its own key (INV-ANA-70), so a disagreement between a run's key and an artefact's key is **detected**, never resolved silently in either direction. A legacy artefact that records no key supplies `None` — never a value recovered from the `package` member (INV-ANA-58).

#### Scenario: The key and its origin are recorded with the analysis

- **WHEN** a static analysis runs over `org.fossify.calendar_20.apk` with the detector disabled and no neutralization, so that the resolved key is the declared `org.fossify.calendar.debug`
- **THEN** the run's record MUST state the key `org.fossify.calendar.debug` and the origin `manifest`
- **AND** the same key MUST be the one passed to GATOR as `-clientParam codePackage=`
- **AND** the artefact written by the run MUST record that key, its origin and `class_defs_under_key` beside the manifest `package` member (INV-ANA-66)

#### Scenario: A stored artefact never supplies a key, because none is wanted

- **WHEN** an analysis JSON exists at `<results_dir>/<apk>.json`, produced before this change, whose `package` member reads `org.fossify.calendar.debug` and which records no effective key, and a later run parses it
- **THEN** the parser MUST load the artefact at the scope its producer gave it
- **AND** the `package` member MUST NOT be read as a filtering key, and no filtering key MUST be resolved for the parse — the effective key for that task is `None` and its discards are counted as unclassified, while its coverage is computed from the artefact's denominator exactly as before: the missing key costs the row its two `unmatched_*` cells, not its measurement

## REMOVED Requirements

(none — no named requirement of the main specification is removed. What this change deletes is
governed by an invariant rather than by a requirement: **INV-ANA-02 is withdrawn**, and with it the
`SignatureNormalizer` class, its test module and the two call sites at
`static_analysis_parser.py:371` and `:455`. That deletion is code-level and complete under P3 — no
adapter, wrapper, feature flag or `_unused` rename remains, and no re-export survives in any
`__init__.py`. The behaviour INV-ANA-02 used to mandate is now forbidden by INV-ANA-67 and by the
modified requirement above.)
