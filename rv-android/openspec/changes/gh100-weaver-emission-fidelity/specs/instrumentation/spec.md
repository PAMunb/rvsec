## Purpose

This delta covers three connected properties of the DEX-native instrumentation pipeline: that the weaver emits every monitor call an advice carries, that it reports what it did, and that the validation layer which checks the first two does not rest on the same assumption that the defect rests on.

The first property is emission cardinality. A JavaMOP advice in the production descriptor may carry more than one `monitorCall` — the descriptor holds 115 advices, 17 of them with N > 1 — because the JavaMOP fusion stage merges advices whose position and pointcut coincide. The weaver has two emission paths: the wrapper path, which synthesises a static wrapper method and iterates the monitor calls correctly, and the inline path, which splices the invoke directly at the call site. The inline path reads `getMonitorCalls().get(0)` and drops the rest. Because `WrapperEmitter.shouldWrap` is `"after".equals(position)` and every fused advice in the production descriptor is `after`, the path that truncates is reached through the explicit constructor `continue`, and the events lost are concentrated: 7 advices and 9 events, 8 of them error emitters — 7 raising `UnsatisfiedConstraint`, one `UnsafeAlgorithm` — and the ninth, `SecureRandomSpec`/`c3`, a state transition that raises nothing itself but gates a later violation. The observable signature is an entire `ErrorType` category — `UnsatisfiedConstraint` — reading zero across 97,018 events while the independent AspectJ weaver reports 43 for the same specification set.

The second property is reporting. The weaver computes counters and has a `--results-json` option to write them, but that option lives only on the `batch` subcommand while the production Python path calls the single-APK `instrument` subcommand. The consequence is not a formatting problem downstream: the file is never written, which is why the results tree holds 289 `instrument_errors.json` and no `instrument_results.json` at all. Counters matter here beyond hygiene, because repairing emission cardinality increases the number of invokes spliced at a site and can push a method over its register budget; without counters that discard is invisible.

The third property is the integrity of the validation instrument. Layer 3 of the validation framework compares event *sets* produced by the `ajc` and `dexlib2` variants for the same APK against a ground-truth oracle, and it was pre-registered in April 2026 with an oracle whose event #8 is one of the nine that the truncation erases. It has never run to a verdict. Three of the four blockers are self-inflicted: the oracle minimum of three stands against two oracle files, one of them an empty template; the static differ used to attribute a wrapper to a spec reads `getMonitorCalls().get(0)`, so it shares the premise of the defect it would have to observe and cannot see the repair; and the comparator does not parse the violation line the device actually emits. Four unit-test fixtures inherit the `get(0)` premise; no advice with N > 1 is exercised anywhere in the suite.

The parsing blocker is the one that would have made a green verdict meaningless. `ErrorCollector.java:37` logs a violation as seven comma-separated fields under the `RVSEC` tag — `spec,classQualifiedName,className,methodName,location,errorType,expecting` — which is what `logcat_parser.py:319` in `rv-android` reads and what produced the 55,169-event paired record. A line recorded on 2026-08-06 reads, verbatim:

```
08-06 18:17:04.465  3144  3457 V RVSEC   : TrustManagerFactorySpec,okhttp3.internal.platform.Platform,Platform,platformTrustManager,Platform.kt:80,UnsafeAlgorithm,expecting one of PKIX,SunX509 but found .
```

Three properties of that line matter and none of them is optional. The tag is padded to a fixed width, so it reads `RVSEC   :` and a pattern anchored on the literal `RVSEC:` finds nothing. The last field carries commas of its own (`PKIX,SunX509`), so fields 0 through 5 are positional and everything from 6 on is rejoined. And the class arrives twice, fully qualified in field 1 and short in field 2, which is what lets a hand-written oracle name `MessageDigestUtil` and a derived one name `okhttp3.internal.platform.Platform` and both be matchable against the same line. `TraceComparator.RVSEC_LINE` instead expects `[Spec] ErrorType: message`, a bracketed shape nothing in the pipeline emits: not `ErrorCollector`, and not `ErrorDescription.toString()` either, whose ` at ` separator the pattern's mandatory `:` or `-` rejects. The pattern was copied verbatim from `rv-android/scripts/drive_cryptoapp.py:89-94`, and its javadoc names that script as its authority — one parser justified by another parser rather than by the producer. Every trace Layer 3 has ever scored is therefore a reconstruction written in the invented shape, including the fixtures of its own unit tests. A comparator that cannot read the recording cannot certify anything about it, and a gate built on that comparator reports success without having read the evidence.

The same reconstruction hid a second gap. The canonical hand-validated oracle states in its own description that "presence of the (spec, errorType, class, method) tuple is sufficient" and declares `location: { class, method }` on all eight of its events, but `TraceComparator.matched` compares only `(spec, errorType)` and the message substring. Location has been documentary since the comparator was written. The consequence is measurable on the paired record: `MessageDigestSpec` is reported once by `ajc` at `jh.h.c` in one APK and once by `dexlib2` at `okio.ByteString.digest$okio` in a different APK — two unrelated misuses that the comparator scores as one agreement, granting a true positive that was not earned and suppressing the false positive that was.

The resolution for the oracle minimum is provenance, not volume. A ground-truth oracle derived from a run of the pipeline under test is circular, which is exactly the objection recorded when the layer was declared N/A in May 2026. An oracle derived from an execution of a **different, independent weaver** is not circular in the same way: it states what an independent implementation of the same specification observed, and it is admissible as ground truth for the implementation under test provided it is frozen before the comparison runs. Two such sources already exist on disk and require no new execution: 55,169 paired `ajc` × `dexlib2` events over 8 APKs run under both variants, and the JVM `-javaagent` control group, which is the only regime in the record where `UnsatisfiedConstraint` is observable at all.

The runtime arm of Layer 3 — driving a single APK deterministically inside a booted emulator and comparing the captured logcat — is not part of this delta. It would require a UI driver executing inside the platform's emulator session, reachable only as a new tool plugin, and that scope was declined. The substituted acceptance criterion is Java-side and narrower: it proves that the monitor invokes are emitted and reach the woven DEX, not that they arrive in logcat at runtime.

## Data Contracts

### Input

- `descriptor: AspectDescriptor` — the JavaMOP-emitted descriptor; each `AdviceSpec` carries `monitorCalls: List<MonitorCall>` with size ≥ 1 (source: `descriptor-reader`)
- `events_fair_csv: Path` — paired `ajc` × `dexlib2` event records used to derive the L3-b oracle (source: `out/run_jca_compare_consolidated/events_fair.csv`)
- `control_group_errors_csv: Path` — the JVM `-javaagent` AspectJ control-group events used to derive the L3-c oracle (source: the campaign results tree, read-only)

### Output

- `instrument_results.json` — per-APK weaver counters written by the production instrumentation path (destination: the APK's output directory, consumed by `rv-instrumentation-dexlib2`)
- `InstrumentationResults` — the parsed counters (destination: `rv-instrumentation-core`, consumed by the platform's result processing)
- `validator/oracles/<apkBaseName>-oracle.yaml` — derived oracles, one per APK, each carrying its provenance block and each expected event's `location` (destination: the Layer-3 comparator)
- `validator/traces/<apkBaseName>/{ajc,dexlib2}.logcat` — the reconstructed trace pair for each derived oracle, written in the collector's own line format so the comparator reads reconstruction and recording through one code path

### Side-Effects

- **[Filesystem]**: the production instrumentation path writes one results JSON per APK, alongside the existing error JSON
- **[Log]**: the resolved `android.jar` path is written to the weaver log at instrumentation start
- **[Build]**: repairing emission cardinality increases the number of invokes spliced per site, which may trigger register-pressure handling in the mutator

### Error

- `UnsupportedAspectConstructError` — raised by pointcut parsing when an expression cannot be parsed, replacing the current silent always-match
- `IllegalStateException` — raised by the wrapper registry when a key already bound to a different advice would be overwritten

## Invariants

- **INV-INS-104**: An advice carrying N `monitorCalls` MUST emit exactly N monitor invokes, in descriptor order, on **every** emission path — inline and wrapper alike. No emission path may read only the first element of `monitorCalls`.

- **INV-INS-105**: The production single-APK instrumentation path MUST write a results JSON for every APK it processes, successful or not. A results tree containing `instrument_errors.json` files and no `instrument_results.json` file is a violation of this invariant, not a reporting preference.

- **INV-INS-106**: No component of the validator MAY attribute a woven artefact to a specification by reading only the first element of `monitorCalls`. A validator that shares the emission premise cannot certify the emission contract.

- **INV-INS-107**: A ground-truth oracle MAY be derived from recorded execution data only when the recording comes from a weaver implementation **other than** the one under validation, and the derived YAML is frozen — content-addressed, with its source file and derivation script named in a provenance block — before the Layer-3 comparison that consumes it runs. An oracle derived from the implementation under test is inadmissible.

- **INV-INS-108**: An acceptance test for an emission repair MUST be executed against the pre-repair code and its failure recorded as an artefact of the change before the repair is integrated. A test that has only ever been observed passing does not establish that it discriminates.

- **INV-INS-116**: A Layer-3 oracle MUST key its expected events on `(apk, class, method, spec)` — the unique-misuse unit defined in the journal article at `results-rq1.tex:41` and implemented at `data-analysis/repair_summary_outcome.py:53`. The comparator that consumes it MUST match on every element of that key the oracle declares. An oracle keyed more finely than the comparator matches makes the gate weaker than the evidence it rests on; a comparator matching more finely than the oracle keys rejects agreements the ground truth never claimed. Neither direction is acceptable, and what a comparator happens to do today is not an argument for changing the unit.

- **INV-INS-117**: The Layer-3 comparator MUST parse the violation line the on-device collector emits (`ErrorCollector.java:37`), and its parsing MUST be justified against that producer. A parser accepted on the authority of another parser is not evidence that the format is right: the shape `TraceComparator.RVSEC_LINE` has matched since gh52 is emitted by nothing in the pipeline, and every trace the layer has scored was written to fit it.

## ADDED Requirements

### Requirement: Emission Cardinality for Fused Advices

The weaver SHALL emit one monitor invoke per entry of an advice's `monitorCalls` list, preserving descriptor order, on both the inline and the wrapper emission path. Advices are fused by JavaMOP when position and pointcut coincide, so an advice with N > 1 is a normal descriptor shape and not an edge case: the production descriptor `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` holds 115 advices of which 17 carry more than one monitor call.

The inline path currently reads `getMonitorCalls().get(0)` at `EmitContext.java:51-52`, in `MonitorInvokeBuilder.java:238-241` (reached from `:50`, `:136` and `:217`), at `StaticInitializationEmitter.java:145-148` and at `AfterThrowingEmitter.java:72`. The wrapper path at `WrapperEmitter.java:637` already iterates correctly and is the reference behaviour. Because `WrapperEmitter.shouldWrap(a)` is `"after".equals(a.getPosition())` and every fused advice in the production descriptor is `after`, the truncating path is reached through the explicit constructor `continue` at `WrapperEmitter.java:215-219`.

Repairing cardinality increases the invokes spliced per site. The change SHALL read the weaver counters after the repair to establish whether any site was discarded under register pressure, and record the result.

#### Scenario: Fused advice with three monitor calls emits three invokes inline

- **WHEN** the weaver processes an advice whose `monitorCalls` list has 3 entries and whose emission plan resolves to the inline path
- **THEN** the woven method MUST contain 3 `invoke-static` instructions to the monitor, one per entry
- **AND** their order MUST match the order of `monitorCalls` in the descriptor
- **AND** the same advice emitted through the wrapper path MUST produce the same 3 invokes in the same order

#### Scenario: The nine erased events reach the woven DEX

- **WHEN** an APK is woven with the `jca_android` specification set after this change
- **THEN** the 9 events previously dropped by the inline path MUST appear as `invoke-static` instructions in the woven DEX
- **AND** the 8 of them that raise an error MUST include `SecretKeySpecSpec`/`UnsatisfiedConstraint`
- **AND** the ninth, `SecureRandomSpec`/`c3`, MUST be emitted too — it raises nothing itself, so a criterion demanding an error from all 9 would fail against a correct weave

#### Scenario: Register pressure after cardinality repair is observed, not assumed

- **WHEN** the weaver counters are read after the repair over the same APK set used before it
- **THEN** the number of sites discarded under register pressure MUST be recorded in the change
- **AND** an increase MUST be reported explicitly rather than absorbed as a silent cost

### Requirement: Wrapper Registry Key Uniqueness

The wrapper registry SHALL NOT overwrite an entry already bound to a different advice. The key computed at `DexWeaver.java:145` collides for distinct advices, and `:159` writes without a guard. The key is the call site's own `MethodReference` and cannot be widened, so the collision has to be removed where it is created — in the emitter, by emitting one wrapper per original call whose body fires every advice bound to it (D-B1); a guard at the registry write cannot resolve it on its own, because dropping the second binding is as wrong as overwriting the first. The collision has a direction — it fabricates violations by binding a call site to the wrong specification — and it is also the mechanism by which a corrected specification allow-list is read from a variable that never gets written, which is why issue #101 depends on this requirement and on nothing else in this change.

#### Scenario: Two advices producing the same registry key

- **WHEN** two distinct advices compute the same wrapper registry key
- **THEN** the registry MUST NOT silently overwrite the first binding
- **AND** the weaver MUST either disambiguate the key or fail loud, never bind the second advice's wrapper to the first advice's site

#### Scenario: Allow-list variable is written after the guard is in place

- **WHEN** a specification whose event lives in the empty parameter slice is woven
- **THEN** the variable the allow-list is compared against MUST be written
- **AND** a corrected allow-list MUST become observable in the reported events

### Requirement: Fail-Closed Pointcut Parsing

`parseCommonPointcut` SHALL raise `UnsupportedAspectConstructError` when it cannot parse a pointcut expression, rather than returning a matcher that matches everything. A fail-open parse produces instrumentation that is wrong with neither error nor warning, and code review cannot catch it because the source that fails to parse is machine-generated.

#### Scenario: Unparseable pointcut fails the weave

- **WHEN** `parseCommonPointcut` encounters an expression it does not recognise
- **THEN** it MUST raise `UnsupportedAspectConstructError` naming the expression and the aspect
- **AND** the weave MUST fail rather than produce an APK instrumented against an always-true matcher

### Requirement: Instrumentation Result Reporting on the Production Path

The production single-APK instrumentation path SHALL write a results JSON carrying the weaver counters, and the Python layer SHALL parse it into `InstrumentationResults`. Today `--results-json` exists only on the `batch` subcommand (`InstrumentationCli.java:129-137`) while production instruments through the `instrument` subcommand (`dexlib_instrumentation.py:245-252`), so the file is never produced — the evidence is 289 `instrument_errors.json` and zero `instrument_results.json` in the results tree. Repairing `_parse_results_json` or `InstrumentationResults` alone restores nothing, because the input does not exist.

The weaver SHALL additionally log the resolved `android.jar` path at instrumentation start, so that a mismatch between the expected and the actually resolved platform jar is diagnosable from the log alone.

#### Scenario: Production instrumentation produces counters

- **WHEN** an APK is instrumented through the production path used by `rv-experiment`
- **THEN** a results JSON MUST be written for that APK
- **AND** `rv-instrumentation-dexlib2` MUST parse it into an `InstrumentationResults` instance
- **AND** the counters MUST be available to the platform's result processing

#### Scenario: Resolved android.jar is diagnosable from the log

- **WHEN** the weaver begins instrumenting an APK
- **THEN** the resolved `android.jar` path MUST appear in the weaver log
- **AND** the log line MUST make it possible to tell which platform jar was used without re-running the resolution

### Requirement: Validator Independence from the Emission Premise

No component of the validator SHALL attribute a woven artefact to a specification by reading only the first element of `monitorCalls`. `BaksmaliDiffer.java:216` does exactly that today, which makes the static oracle structurally unable to observe the repair it is meant to certify. The unit-test fixtures that build advices the same way — `EmitPlanShapeTest:74`, `StaticInitializationEmitterSignatureTest:143-154`, `AfterThrowingEmitterTest:60/77/105/121` — SHALL exercise at least one advice with N > 1, since no test in the suite does so today.

#### Scenario: Static differ attributes a multi-call advice correctly

- **WHEN** `BaksmaliDiffer` encounters a woven wrapper generated from an advice with 3 monitor calls
- **THEN** it MUST attribute the artefact using all 3 calls, not the first
- **AND** the Layer-1 hook comparison MUST reflect the repaired emission

#### Scenario: Fixtures exercise N greater than one

- **WHEN** the emitter test suite runs
- **THEN** at least one fixture MUST construct an advice with more than one monitor call
- **AND** its assertions MUST fail if any emission path truncates to the first call

### Requirement: Pre-Fix Red Evidence for Emission Repairs

The acceptance tests for the emission repairs — V0 (an advice with N `monitorCalls` emits N invokes, in descriptor order) and V2 (the 9 previously dropped events appear as `invoke-static` in the woven DEX) — SHALL be executed against the pre-repair code and their failure recorded as an artefact of this change before any repair is integrated.

This is not process ceremony. The defect this change repairs survived because a discriminating instrument was replaced by an aggregate that cannot observe it: the truncation removes additional monitor calls from a site that remains woven, so method coverage is byte-identical with and without the defect. A test first observed after the fix cannot distinguish "the repair works" from "the test never discriminated".

#### Scenario: Red evidence precedes the repair

- **WHEN** the change is ready to integrate the emission repairs
- **THEN** V0 and V2 MUST already have been executed against the pre-repair code
- **AND** their failing output MUST be committed as an artefact of the change
- **AND** the repair commit MUST reference that artefact
- **AND** the descriptor and generated monitor sources used by the failing run MUST be content-addressed in the recorded artefact, and the post-repair run MUST use exactly those inputs — a green run over different inputs does not answer the red one

#### Scenario: A test that passes before the fix is rejected as evidence

- **WHEN** an acceptance test for an emission repair passes against the pre-repair code
- **THEN** that test MUST NOT be accepted as evidence for the repair
- **AND** the change MUST record why it does not discriminate, and replace it

### Requirement: Layer-3 Trace Parsing and Matching Fidelity

The Layer-3 comparator SHALL read the violation line format the on-device collector emits, and SHALL match an observed event against an oracle event on every key element the oracle declares.

The producer is `ErrorCollector.java:37`, which logs `ErrorSummary.toString()` followed by the `expecting` text under the `RVSEC` tag: seven fields, `spec,classQualifiedName,className,methodName,location,errorType,expecting`. Fields 0 through 5 are positional; field 6 onward is rejoined, because the `expecting` text carries commas of its own. The logcat tag is padded to a fixed column, so it appears as `RVSEC   :` rather than `RVSEC:`. `rv-android`'s `logcat_parser.py:319` already reads exactly this and is the reference implementation; the two SHALL agree, and where they disagree the producer decides.

The class arrives twice on every line — fully qualified in field 1, short in field 2. An oracle's `location.class` SHALL match against either, because the two admissible provenances name classes differently: the hand-validated `cryptoapp` oracle names `MessageDigestUtil`, while an oracle derived from a recorded campaign names `okhttp3.internal.platform.Platform`. Requiring one form would make one whole provenance class unmatchable.

Matching on location is not an enhancement; it is what the oracles already claim. `cryptoapp-oracle.yaml` states that "presence of the `(spec, errorType, class, method)` tuple is sufficient" and declares `location: { class, method }` on all eight of its events, and `TraceComparator.matched` has never read either field. Until it does, two unrelated misuses of the same specification in different classes score as one agreement.

#### Scenario: The comparator reads a line the device actually emitted

- **WHEN** `parseObserved` is given a logcat containing a line whose tag is `RVSEC` and whose message carries the seven collector fields
- **THEN** it MUST yield an observed event whose spec, error type, qualified class, short class and method come from fields 0, 5, 1, 2 and 3 respectively
- **AND** the message MUST be fields 6 onward rejoined with commas, so an `expecting` text such as `expecting one of PKIX,SunX509 but found .` survives intact
- **AND** the padded tag form `RVSEC   :` MUST be accepted, since that is how logcat writes it

#### Scenario: An event at a different site is not an agreement

- **WHEN** an oracle event declares `location: { class: jh.h, method: c }` for a specification, and the observed trace reports that same specification and error type at `okio.ByteString.digest$okio`
- **THEN** the oracle event MUST count as a false negative for that pipeline, not a true positive
- **AND** the observed event MUST count as a false positive, since it matches no oracle entry
- **AND** an oracle event that declares no location MUST keep matching on `(spec, errorType)` alone, so an oracle may under-specify deliberately but never by accident

#### Scenario: A parser is justified against the producer, not against another parser

- **WHEN** the trace parsing behaviour of the comparator is changed or extended
- **THEN** the change MUST cite the producing code and a recorded line that exhibits the format
- **AND** citing another parser's agreement MUST NOT be accepted as justification, because that is how the current pattern — copied from `drive_cryptoapp.py:89-94` and never checked against `ErrorCollector` — survived from gh52 to this change

## MODIFIED Requirements

### Requirement: Ground-Truth Oracle Diversity for Equivalence Claims

The claim that `dexlib2` is behaviorally equivalent to `ajc` on APKs that `ajc` handles correctly MUST be supported by at least three ground-truth oracles exercising disjoint profiles, each with an expected-event list committed to `validator/oracles/<name>-oracle.yaml` BEFORE Layer-3 or Layer-4 execution (so that oracles are not retrofitted to observed behavior of the implementation under test).

An oracle's expected-event list MUST be established by one of two admissible provenances, and the YAML MUST declare which one in a provenance block:

- **Hand-validated** — the list is derived from source inspection or manual UI validation, with source files, line numbers or validation steps cited.
- **Derived from an independent weaver** — the list is derived from recorded executions of a weaver implementation **other than** the one under validation, with the source data file, its content hash, and the derivation script named. This provenance is admissible because it states what an independent implementation of the same specification observed; it is NOT admissible when the recording comes from the implementation under test, which would be circular.

The three mandatory profiles are:

1. **Java-only, single DEX, pre-R8** — baseline profile. Canonical APK: `cryptoapp` with 8 known violations (see `docs/20260423_plano_validacao.md` §3.4 oracle table). Provenance: hand-validated.
2. **Paired-execution profile (L3-b)** — the profile that discriminates the wrapper-collision defect. Derived from the 55,169 paired `ajc` × `dexlib2` events over the 8 APKs executed under both variants, recorded in `out/run_jca_compare_consolidated/events_fair.csv`. Provenance: derived from an independent weaver.
3. **Control-group profile (L3-c)** — the profile that discriminates the inline-truncation defect. Derived from the JVM `-javaagent` AspectJ control group, which is the only recorded regime in which `ErrorType.UnsatisfiedConstraint` is observable at all. Provenance: derived from an independent weaver. The provenance filter that selects which control-group records enter the oracle MUST be stated in the YAML and justified in the change.

A derived oracle SHALL be written one file per APK, named `<apkBaseName>-oracle.yaml` after the convention `TraceComparator.resolveOracleForApk` implements — the `.apk` suffix and any trailing `_<digits>` version suffix stripped. This is not a filing preference. `apk` is the first element of the key INV-INS-116 mandates, and it is the one element a violation line does not carry: the collector logs class, method, specification and error type, never the APK. The only place the APK is recoverable is the oracle's identity and the result-tree filename, so an oracle pooling several APKs into one file cannot honour the key at all, and in batch mode is never resolved for any APK.

A derivation reading a recorded campaign SHALL repair frame-form `(class, method)` values before keying, and SHALL declare the repair in the provenance block. When the on-device summarizer failed to split a stack frame it copied the whole frame — source position included — into both columns, so the line number silently joined the key and one misuse counted once per line. The repair is the algorithm the producer now performs at `ErrorDescription.FRAME_SUFFIX`: strip a trailing parenthesised group that contains no nested parenthesis and ends in `:<digits>`, then split the remainder at its last dot. The repair rule in the article's `data-analysis/repair_frame_keys.py` SHALL NOT be substituted for it: that rule additionally requires the stripped group to look like `File.ext:NN`, which the campaign's `(Unknown Source:1)` and `(r8-map-id-…:17)` forms do not satisfy, and it therefore repairs none of the 2,476 affected rows of `events_fair.csv`. Two rules that agree on the article's own sheets disagree here, and the producer's is the one that describes this data.

Provenance admission SHALL be enforced on the path that executes the comparison. `OracleLoader` decides admission today, but `TraceComparator.compare` lists the oracle directory itself and `run_phase5_validators.sh` never invokes the `oracles` subcommand before `layer3`, so a circular or unattributed oracle is scored normally by the gate it was written to be excluded from. An admission rule that only the operator can trigger is not an admission rule.

The multidex profile from JCA-400, mandated by the earlier form of this requirement and never written, is NOT one of the three. Its absence MUST carry an entry in `docs/LIMITATIONS.md` naming the unverified profile.

Additional oracles MAY be added, but dropping below three is permitted only if `LIMITATIONS.md` carries an explicit entry naming the unverified profile and acknowledging the reviewer scrutiny that concession invites. A single oracle (cryptoapp alone) is insufficient for Phase-6 promotion.

The runtime per-APK arm of Layer 3 — driving one APK deterministically inside a booted emulator and comparing the captured logcat — is out of scope of the current change and remains unexecuted. The substituted acceptance criterion for emission repairs is Java-side (V0 and V2 under `Requirement: Pre-Fix Red Evidence for Emission Repairs`), and it proves emission and arrival in the woven DEX, not arrival in logcat at runtime. That substitution MUST be stated wherever a Layer-3 verdict is reported, so the weaker claim is not read as the stronger one.

A Layer-3 verdict obtained from derived oracles in this change is **characterization, not certification**, and MUST be reported as such. Both sides available to L3-b and L3-c are frozen pre-repair recordings: the comparison can show that the defect is present and what shape it takes, but it cannot flip from red to green when the repair lands, because a green side would require a fresh `dexlib2` execution over the same APKs — an emulator session (L3-a) or a corpus re-run (V4), both out of scope. A gate clause that reads a derived-oracle verdict as evidence that the repair worked claims what frozen data cannot deliver.

#### Scenario: Layer 3 runs against three oracles

- **WHEN** `TraceComparator` is invoked for the ratification gate
- **THEN** at least three oracle YAMLs MUST be present in `validator/oracles/`
- **AND** each oracle MUST carry a provenance block declaring hand-validated or derived-from-an-independent-weaver
- **AND** each oracle MUST satisfy its expected event list with F1 ≥ 0.98 and κ ≥ 0.9 under both variants
- **AND** the report MUST name the three oracles, their profiles and their provenances in its header

#### Scenario: Oracle derived from the implementation under test is rejected

- **WHEN** an oracle YAML declares a provenance whose source recording came from the `dexlib2` pipeline being validated
- **THEN** `OracleLoader` MUST reject it
- **AND** the rejection message MUST name the circularity, not merely report a malformed file

#### Scenario: Oracle added after execution

- **WHEN** a new oracle YAML is committed after a Layer-3 run already produced a report
- **THEN** the report MUST be regenerated with the new oracle before any gate ratification
- **AND** the commit message MUST cite the expected events and their provenance explicitly (source files, line numbers, manual UI validation steps, or the source recording's content hash and derivation script) — never "observed in run X" of the implementation under test

#### Scenario: Derived oracle is frozen before the comparison

- **WHEN** an oracle derived from an independent weaver's recording is used in a Layer-3 comparison
- **THEN** the YAML MUST already carry the content hash of its source data and the name of its derivation script
- **AND** re-deriving it after the comparison, for any reason, MUST invalidate that comparison's verdict

#### Scenario: Derived oracle is written per APK and keyed on the article's unit

- **WHEN** an oracle is derived from a recorded campaign spanning more than one APK
- **THEN** one oracle file MUST be written per APK, named `<apkBaseName>-oracle.yaml` after `TraceComparator.resolveOracleForApk`
- **AND** each expected event MUST carry the `class` and `method` of its site, so the file keys on `(apk, class, method, spec)`
- **AND** the derivation MUST repair frame-form values with the producer's rule and say so in the provenance block

#### Scenario: A circular oracle reaches the comparison

- **WHEN** `TraceComparator` is invoked for a Layer-3 verdict over a directory containing an oracle whose provenance names the implementation under test
- **THEN** that oracle MUST NOT contribute to the verdict
- **AND** its rejection MUST appear in the report, so a shortfall is visible rather than silent
- **AND** listing the directory without consulting the admission rule MUST NOT be how the comparison selects its oracles

#### Scenario: A derived-oracle verdict is reported as characterization

- **WHEN** a Layer-3 verdict obtained from L3-b or L3-c is recorded in this change
- **THEN** it MUST state that both sides are frozen pre-repair recordings
- **AND** it MUST state that the verdict documents the defect rather than certifying its repair
- **AND** it MUST name what a certifying verdict would require — a fresh `dexlib2` run, meaning L3-a or V4 — and that neither ran

#### Scenario: Multidex profile unavailable

- **WHEN** a ratification gate is scheduled and no multidex oracle has been committed to `validator/oracles/`
- **THEN** `docs/LIMITATIONS.md` MUST carry an entry "multidex profile unverified" naming the scrutiny this invites
- **AND** the three mandatory profiles above MUST all be present — no silent continuation on two
