## Purpose

A violation report is the only thing the runtime-verification pipeline leaves behind about a misuse: one logcat line per deduplicated `ErrorDescription`, later one row of `errors.csv`. In the published dataset 72.93 % of those rows carry the literal `unknown` as their message, because 25 of the 51 report sites of the `jca` set call the three-argument `ErrorDescription` constructor, whose fourth argument defaults to `"unknown"` (`rvsec-core/.../eh/ErrorDescription.java:34-36`); a further 8,843 rows read `but found .` because 16 of the 17 active `but found` sites interpolate a monitor field that is still empty when the event fires. The `@fail` handler that produces every `InvalidSequenceOfMethodCalls` names neither the event that triggered it nor the state it came from, so the record cannot be attributed to an event even when the specification is read next to it.

Illegibility is not the whole of it. The set also accuses the wrong things. Under the frozen `jca` allow-lists, `KeyStore.getInstance("AndroidKeyStore")` is reported 2,005 times across 11 apps, `SSLContext.getInstance("TLS")` 8,648 times across 60 apps, and `TrustManagerFactory.getInstance("X509")` 643 times across 3 apps — every one of them a correct call on Android 11. Those three values account for 11,296 of the 11,409 events in the tier of the published measurement that has primary-source evidence, and none of them is a misuse: `AndroidKeyStore` and `TLS` are in the generated api30 rule and simply absent from the hand-written Java SE list, and `X509` is Conscrypt's registered alias of `PKIX`. A message that is perfectly legible about a verdict the platform contradicts is not an improvement.

This delta therefore gives the instrumentation pipeline both a message contract and a verdict anchored in the platform it runs on: a successor specification set `jca_android` at a new directory, seeded from the frozen `jca` and targeted at Android API 30; allow-lists transcribed literally from the `CONSTRAINTS` clauses of the generated api30 CrySL rules, under a declared normalisation rule derived from Conscrypt; no predicate at all, so no verdict depends on cross-specification bookkeeping the rules never asked for; a versioned `key=value` envelope every report site emits, with the offending event name recorded by the event body itself; a weaver counter that measures how many advices a merged wrapper fires at an incompatible `args()` arity, without changing what fires; the collector's line escaped and null-guarded; the orphan-event and structural checks over the generated monitor as executable gates for any set, with the CrySL rule as an input so the gate stops calling a correct encoding a defect; and a differential harness that replays the same traces through the monitors generated before and after a repair, because two earlier changes (gh100 D-B1, gh101 Groups 3/3b) each moved a defect instead of removing it while every static gate stayed green.

The frozen `jca` set stays frozen. The derived Android set gh101 built is not the seed and receives no repair: the 2026-08-08 audit judged it NOT READY, so deriving from it would carry an unaudited instrument forward. Its directory is renamed to `jca_android_bug_predicate/` and stops being selectable — the name records what set it aside, a predicate regime whose defects the audit measured — and the name `jca_android` is rebound to the successor set. Nothing is deleted: the archived directory stays in the tree, and reproducing the audit means pointing `RVSEC_HOME` at the commit it was run against. Everything the successor set differs from `jca` by is a recorded hunk, so a reader can still tell a platform allow-list from a repair, and every departure from a literal transcription of the api30 rule is a recorded divergence with its evidence. The `generic` and `generic_new` sets are outside this contract: none of their 145 files passes through `ErrorCollector`, and none has ever run in a campaign.

## Data Contracts

### Input
- `specification_set: str` — `"jca"`, `"jca_android"`, `"generic"` or `"custom"` (`ExperimentConfig`, `rv_experiment/config.py`); resolves to a directory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`. The enumeration keeps four values: `jca_android` is rebound to the successor set, not added beside the derived one, and `jca_android_bug_predicate` is not a value it accepts.
- `MetaCrySL/generated/api30/<Class>.cryptsl` — the generated CrySL rules for Android API 30, read by the allow-list conformance gate as the oracle. MetaCrySL itself is never edited by this contract; only its already-generated output is read.
- `MultiSpec_1RuntimeMonitor.java` — the generated monitor of a set (`results/<run>/monitors/`), read by the structural gates and the harness.
- `MultiSpec_1MonitorAspect.json` — the advice descriptor the dexlib2 weaver consumes (`WrapperEmitter.generate`).
- `data/jca_android/divergence_record.csv`, `data/jca_android/conformance_record.csv`, `data/jca_android/alias_table.csv`, `data/jca_android/gate_allowlist.csv`, `data/jca_android/predicate_removal.csv`, `data/jca_android/constraint_table.csv`, `rvsec-mop/src/main/resources/jca_android/codes.csv` — the records the gates read.

### Output
- One logcat line per report: `RVSEC: spec,classQualifiedName,className,methodName,location,errorType,<envelope>` (logcat `ErrorCollector.java:36-40`); the seventh field is the envelope of `Requirement: Violation Report Message Envelope`.
- `instrument_results.json` counter `advicesExcludedByArity` (per APK, `BatchRunner` counts map) — a measurement, not the effect of a filter.
- Harness evidence: `evidence/harness/<spec>-<task>.md` per repair task, before/after trace verdicts.

### Side-Effects
- **[Filesystem]**: `rvsec-mop/src/main/resources/jca_android/` renamed to `rvsec-mop/src/main/resources/jca_android_bug_predicate/` and then recreated with the seed; `data/jca_android/` created; two new classes created under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` — one holding the Cipher transformation tables of the successor set, one holding its alias table as code; `rvsec-mop/src/test/` created as the JVM harness home.
- **[Generation]**: the structural gates and the harness generate monitors in a scratch directory (`RVSEC_HOME` required); generation is not parallelisable and `TMPDIR` MUST be off tmpfs (`CipherSpec` at 17 events needs 3.3 GB).

### Error
- `pytest` failure — a gate violation without an allowlist entry; a freeze-check failure on `jca`; a `jca_android`/`jca` hunk without a divergence-record entry; a report site with three arguments; an unexpanded `__EVENTNAME` in a generated monitor; any occurrence of `ExecutionContext` in a `.mop` of the successor set; an allow-list entry that is neither in the corresponding api30 `CONSTRAINTS` clause nor covered by the declared normalisation rule nor recorded as a divergence; an edit reaching `CipherTransformationUtil.java` or `AndroidCipherTransformationUtil.java`; an alias row of the in-code table that differs from `data/jca_android/alias_table.csv`.
- `IllegalStateException` (weaver) — unchanged guard on wrapper registry collisions; an arity mismatch is counted and never raises.

## Invariants

- **INV-INS-09** (restated, replacing the entry of the same number): Specification sets MUST NOT be mixed within a single generation or instrumentation run. The `specification_set` field in `ExperimentConfig` MUST be one of `"jca"`, `"jca_android"`, `"generic"`, or `"custom"`. If `"custom"` is specified, `custom_specs_dir` MUST be provided; each of the other three resolves to its directory from the set name alone, with no path supplied by the caller. The enumeration is closed and does not grow with this contract — `jca_android` is rebound to the successor set — so a value outside it is rejected by name and a stale or mistyped `custom` path can never silently select an uncorrected instrument. `jca_android_bug_predicate` MUST be rejected like any other unknown value, even though it names a directory that exists.
- **INV-INS-113** (restated, replacing the entry of the same number): Every `.mop` of the archived set `jca_android_bug_predicate` carries a conformance verdict against the generated rules for its target API level — anchored to a named rule, or declared uncontradicted with the rule that was checked, or declared to have no anchor with the reason — and a file with no verdict is unverified, not verbatim. The invariant binds `jca_android_bug_predicate` and the record it was measured with (`data/gh101/`), which the rename does not rewrite; `jca_android` is outside it and carries `data/jca_android/conformance_record.csv` per INV-INS-125, where the vocabulary is transcription, recorded divergence and `deferred-constant`, not anchored/uncontradicted/no-anchor.
- **INV-INS-118**: `jca_android` MUST be seeded from the frozen `jca` — never from the archived `jca_android_bug_predicate` — and MUST differ from that seed only by hunks entered in `data/jca_android/divergence_record.csv` with a reason and the task that introduced them. The seed is the 23 `.mop` files of `jca` minus `RandomStringPassword.mop` and `SecretKeySpec.mop`, which INV-INS-128 removes; the set therefore holds 21 specifications. The freeze of `jca` (INV-INS-109) is unaffected: no task of this contract edits `jca/`, `CipherTransformationUtil.java` or `AndroidCipherTransformationUtil.java`, and the existing freeze gate MUST stay green — with the three gh101 gate scripts (`gh101_divergence_record.py`, `gh101_predicate_pairing_check.py`, `gh101_conformance_check.py` — two test invocations in `tests/parity/test_gh101_specset_gates.py`) repointed at the archive `jca_android_bug_predicate`, which is the set they describe; the gh101 record itself is not edited. An unrecorded hunk between the seed and the set is a defect.
- **INV-INS-119**: Every `new ErrorDescription(` in `jca_android` MUST use the four-argument constructor, and the fourth argument MUST be a v1 envelope. No report emitted from `jca_android` may carry the message `unknown` or an observed value that is empty because a monitor field was interpolated before any event wrote it: a `but found` message MUST interpolate the value read from the target object the reporting event binds (`getAlgorithm()`, `getType()`, `getProtocol()`), or the argument where the event binds it, and never a monitor field.
- **INV-INS-120**: The monitor generator MUST expand the macro `__EVENTNAME` to the name of the event a report site belongs to — in an event body to the declared name of that event, in a handler body to the name of the event that last transitioned the monitor, and to the sentinel `none` when no event has transitioned it. No specification file MUST carry hand-written event-name bookkeeping. No generated Java MUST contain the unexpanded literal `__EVENTNAME`. Two events of one specification MUST NOT share a name (the generated monitor merges their transition rows silently — `GCMParameterSpecSpec` today).
- **INV-INS-121**: A report message MUST agree with the check that guards it: every numeric literal in the message equals the literal of the guarding `condition()`; the `ErrorType` matches what the condition tests (a constraint on an argument is `UnsatisfiedConstraint`, an algorithm outside the allow-list is `UnsafeAlgorithm`, a call the rule's `FORBIDDEN` clause names is `ForbiddenMethod`); an expected list in a message is the file's allow-list, joined, never a hand-written subset or the literal `...`.
- **INV-INS-122**: When `WrapperEmitter` groups advices into one merged wrapper for a concrete call, it MUST NOT remove any advice from the group. It MUST instead decide, per advice, whether the advice's positional `args()` arity is compatible with that call, under three clauses: an advice with no `args()` clause is never counted (absence means "no positional constraint"); the arity is read from `ArgsPC.types()`, so a trailing `..` means "at least"; the decision is taken in the grouping loop, where the concrete overload's parameter count is known. Every incompatible advice MUST be counted into the results JSON as `advicesExcludedByArity`, and the wrapper MUST fire exactly the same advices it fires today. Measuring before filtering is deliberate: a filter would change what every campaign reports in the same commit that first measures how much there is to change.
- **INV-INS-123**: For any specification set, the structural gates over the generated monitor MUST run as pytest and MUST fail on a violation not named in `data/<set>/gate_allowlist.csv` with a reason: G-ERE (every symbol named in an `ere` or `fsm` has an event declaration — run before generation, since the generator drops an undeclared symbol silently), G-2 (an event with a transition row to `fail` from every state — INV-INS-110 — **and** no clause of the corresponding CrySL rule that the event encodes: `CONSTRAINTS`, `REQUIRES` or `FORBIDDEN` on the frozen `jca`; `CONSTRAINTS` or `FORBIDDEN` on `jca_android`, which encodes no `REQUIRES` by construction), G-2a (an event that never changes state: `∀s δ(s,e)=s`), G-2b′ (an event redundant at the start state: `δ(q0,e)=q0`), G-2c (a state unreachable from `q0` or from which no accepting state is reachable), G-2d (the highest-index state is not the `fail` category), G-6′ (the number of `Prop_N_event_*` methods differs from the number of `Prop_N_transition_*` rows). A green gate over a set with a known defect is a bug in the gate; the frozen `jca`, where the answers are known (G-ERE 1, G-2 3 `orphan-without-clause` under the mechanical mapping, G-2a 1, G-2b′ 8, G-2c 1, G-2d 2, G-6′ 1), is the baseline every extension is run against first. G-CONF (INV-INS-127) and G-PRED (INV-INS-128) run beside these but are not structural: they read the `.mop` sources and the api30 rules, not the generated monitor.
- **INV-INS-124**: No repair task on an automaton, a message, an allow-list or a wrapper rule of this contract MAY close without the differential harness having replayed the same traces through the monitor generated before and through the monitor generated after the repair, with the per-trace verdicts of both committed as evidence. A repair that changes which call is accused, without changing whether the trace is accused, is a moved defect and MUST be recorded as such, not as a fix.
- **INV-INS-125**: The oracle of `jca_android` is the generated api30 CrySL rule and nothing else, recorded per specification in `data/jca_android/conformance_record.csv`. The recommendation-versus-availability split the derived set carried does not apply here, because the successor set targets one declared platform — Android 11 / API 30, Conscrypt branch `android11-release` — and on a single platform an algorithm that is not available cannot be recommended. Three and only three kinds of departure from a literal transcription are admissible, and each MUST be recorded. Two are entered in `data/jca_android/divergence_record.csv`: an entry of the declared normalisation table (INV-INS-127), and a value the api30 rule omits that the platform provably carries, cited to a platform source. The third is entered in `data/jca_android/conformance_record.csv` as a **`deferred-constant`**: a `CONSTRAINTS` clause the api30 rule declares and this change does not begin to check, recorded with the rule file and clause, the reason it is deferred, and the statement that leaving it out adds no accusation — the class that exists because transcribing a constant the set has never run changes what is accused without before/after evidence. A constant that is neither transcribed nor entered as a `deferred-constant` row is a defect, and G-CONF MUST fail on it. The departure rule is asymmetric in one direction only: a value the api30 rule admits is admitted by the set, whatever the frozen `jca` thought of it, and a value the rule omits is added only against platform evidence. In `jca_android`, `UnsafeAlgorithm` (code KIND `ALG`) therefore means "value outside the api30 allow-list of the platform", not "cryptographically insecure": `MD5` and `SHA-1` are admitted by the api30 `MessageDigest` rule and are no longer reported; the `ErrorType` name is kept for continuity with `jca` and the meaning shift is declared, not hidden. Any report comparing counts across `jca`, the archived `jca_android_bug_predicate` and `jca_android` MUST carry the caveat that the sets answer to different oracles.
- **INV-INS-126**: The dedupe identity of a violation report (`ErrorSummary.equals`/`hashCode`, `rvsec-core`) MUST include the report's `code` and `event` in addition to `spec`, `error`, `class`, `method` and `location`. The message free text stays outside it. Because every dedupe count published before this contract used the five-field identity, the count discontinuity MUST be measured before the identity change is integrated — on the E3 trial, where it is zero by construction (its records carry no envelope) and is recorded as the five-field baseline, and on an input whose records carry `ev=` (the differential-harness traces or the device logcat), where it MUST be non-zero.
- **INV-INS-127**: Every allow-list of `jca_android` MUST be a literal transcription of the `CONSTRAINTS` clause of the corresponding rule in `MetaCrySL/generated/api30/`, compared under one declared normalisation rule: comparison is case-insensitive, and an observed value matches a list entry if a row of the set's alias table maps it to that entry. The gate that checks this is **G-CONF**. The alias table is a file of its own, `data/jca_android/alias_table.csv`, and MUST NOT be folded into the conformance record or expanded into the allow-lists. Each alias row MUST name its primary source and the specification it applies to, and every row MUST cite the Conscrypt `android11-release` branch by file and line: there is no second class of row and no exemption from the pointer. An observed spelling that no registration in that file explains MUST NOT be given a row at all; it belongs in `data/jca_android/divergence_record.csv`, where its evidence is declared for what it is. The one measured case is `OAEPWithSHA1AndMGF1Padding`, whose observed form carries no hyphen in `SHA1` while the api30 rule writes `OAEPwithSHA-1andMGF1Padding` and Conscrypt registers only hyphenated spellings (`OpenSSLProvider.java:338`, alias at `:339-340`), so it has no line to cite and is recorded as a divergence carrying behavioural evidence instead. Resolution happens at runtime through a utility class in `rvsec-core` that carries the table as code and that each `jca_android` specification names in its call (INV-INS-112), never by reading the CSV at runtime; a test MUST assert that the in-code table and the CSV are equal, so the record and the instrument cannot drift. A list entry with no clause behind it, and an alias with no pointer behind it, are the same defect: a verdict whose authority cannot be checked.
- **INV-INS-128**: No `.mop` of `jca_android` MUST contain the identifier `ExecutionContext` — no `validate`, no `setProperty`, no `remove`. The gate that checks this is **G-PRED**, a grep. The set carries no predicate, so no verdict of one specification depends on state another specification wrote. INV-INS-111 (every written `Property` is read or recorded) is therefore vacuous for this set, and gh101's `predicate_omissions.csv` — which records a `Property` written and never read — has nothing to hold and is not carried. What this set carries instead is `data/jca_android/predicate_removal.csv`, one row per removed site — 55 rows: the 21 predicate-reading events, the 9 `remove(...)` sites and the 25 `setObjectAsInAcceptingState`/`unsetObjectAsInAcceptingState` calls, classified as guard, total-loss, partial-loss, provenance, remove or accepting-state; the 46 `setProperty` deletions, the 21 `import` deletions and the one comment (`MessageDigestSpec.mop:25`) are divergence-record entries, one per file, not rows. The two file names denote different records and MUST NOT be used interchangeably. The detections the removal costs MUST be enumerated there and in the divergence record rather than absorbed silently.
- **INV-INS-129**: Every generated monitor dispatcher that acquires the generated file's global lock MUST release it on every exit path, including an exception raised inside the guarded region. The generator MUST emit the framing that guarantees it; no generated dispatcher MUST acquire the lock outside such framing. The reason is that the lock is one object shared by every specification of the set and every other dispatcher waits on it by spinning (`tryLock()` inside a `Thread.yield()` loop), so a single unreleased acquisition does not fail one report — it converts the instrumented application into a busy-wait that never reports again and never terminates, and nothing in the record says so. The repair MUST be behaviour-preserving on non-throwing paths: regenerating any set MUST differ from its pre-change monitor only in the framing, the event-name table of INV-INS-120 and the expanded macro.

## ADDED Requirements

### Requirement: Successor Specification Set `jca_android`

The system SHALL rebind the name `jca_android` to a new specification set at `rvsec-mop/src/main/resources/jca_android/`, seeded from the frozen `jca` and selectable by name. Nothing is added to the enumeration of selectable sets: it keeps its four values, and what changes is which directory the second of them resolves to. The set exists because neither JCA set that existed before is available as a target: `jca` is frozen (it produced the published measurements), and the derived Android set was judged NOT READY by the 2026-08-08 audit, so seeding from it would carry an unaudited instrument forward under a new name. Every specification-side change of this contract — allow-lists, messages, automata, pointcuts — lands in `jca_android` alone.

Before the seed is written, the directory that held the derived set SHALL be renamed to `rvsec-mop/src/main/resources/jca_android_bug_predicate/`, and the archived set SHALL NOT be selectable by `--specification-set` or by `ExperimentConfig.specification_set`. It is preserved and not deleted, because it is the instrument the 2026-08-08 audit assessed and the reference a reader of that audit needs; reproducing the audit is done by pointing `RVSEC_HOME` at the commit the audit was run against, not by naming the set in a new run. The name states why the set was set aside — a predicate regime whose defects the audit measured, which is exactly what the successor removes rather than repairs (INV-INS-128) — so a reader who meets the directory does not have to reconstruct the reason from the change history.

The seed SHALL be the 23 `.mop` files of `jca` byte-for-byte, minus the two the removal of predicates dissolves: `RandomStringPassword.mop` and `SecretKeySpec.mop` are pure predicate propagators — each exists only to write a `Property` another specification reads — and once no specification reads a `Property` there is nothing left in them to monitor. The set therefore holds **21** specifications, and the two absences are the first two entries of its divergence record.

The set SHALL carry six records under `data/jca_android/` — a divergence record naming every hunk by which it differs from its seed (INV-INS-118); a conformance record naming the api30 rule each specification answers to (INV-INS-125); an alias table, a file of its own, one row per normalisation entry with its source pointer (INV-INS-127); a gate allowlist for structural-gate exceptions with reasons (INV-INS-123); a predicate-removal record, one row per removed predicate site (INV-INS-128); and a constraint table, `constraint_table.csv` (`spec,cryptsl_line,mop_line,verdict`; verdicts `CRYSL-NAO-IMPLEMENTADO`, `IGUAL`, `MOP-SEM-BASE`, `MOP-MAIS-PERMISSIVO`, `DIVERGENTE`, `MOP-MAIS-RESTRITIVO`), the row-level clause-by-clause comparison of every api30 `CONSTRAINTS` clause with the seed that G-CONF's report on the frozen `jca` reproduces — plus `codes.csv` beside the `.mop` files, the table of failure codes its envelopes emit. It SHALL NOT carry a `predicate_omissions.csv`: that record, which gh101 uses for a `Property` written and never read, has nothing to hold in a set that writes none, and its name SHALL NOT be reused for the removal record.

The set SHALL be reachable at every site that enumerates specification sets: `valid_spec_sets` and the directory mapping in `rv_experiment/config.py`, the `click.Choice(["jca", "jca_android", "generic", "custom"])` on `--specification-set` at `rv_experiment/__main__.py:443`, INV-INS-09, INV-EXP-03 clause (f), and the mapping paragraph of `Just-in-Time Sub-Module Configuration`. None of those lists grows — `jca_android` is already in all of them — so what each site MUST be checked for is that the name now resolves to the successor set and that no site offers `jca_android_bug_predicate`. A set reachable only through `custom` with a hand-written path is a set a mistyped path silently swaps for the uncorrected one, which is why the archived directory is left with no name at all rather than a second value.

#### Scenario: `jca_android` is selected by name

- **WHEN** `ExperimentConfig.specification_set` is `"jca_android"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`
- **AND** the directory MUST contain exactly 21 `.mop` files and `codes.csv`
- **AND** `custom_specs_dir` MUST NOT be required

#### Scenario: the seed is the frozen set minus two files

- **WHEN** the set is first created and `diff -r` is taken over the `*.mop` files of `jca/` and `jca_android/`
- **THEN** the only differences MUST be `RandomStringPassword.mop` and `SecretKeySpec.mop` present in `jca/` and absent from `jca_android/`
- **AND** every one of the remaining 21 files MUST be byte-identical between the two directories
- **AND** `codes.csv` MUST be the only non-`.mop` file `jca_android/` adds
- **AND** the freeze gate `tests/parity/test_gh101_specset_gates.py::test_frozen_paths_byte_identical_to_base_commit` MUST still pass

#### Scenario: the seed is not taken from the archived derived set

- **WHEN** the provenance check compares each seeded file against both `jca/` and `jca_android_bug_predicate/`
- **THEN** every seeded file MUST match its `jca/` counterpart byte-for-byte
- **AND** a file matching `jca_android_bug_predicate/` where the two differ MUST fail the check naming the file, because the archived set carries the allow-list content the 2026-08-08 audit judged NOT READY

#### Scenario: the derived set is archived and unreachable by name

- **WHEN** the tree is inspected after the seed has been written
- **THEN** `rvsec-mop/src/main/resources/jca_android_bug_predicate/` MUST exist and MUST hold the 23 `.mop` files the derived set had before the rename, byte-unchanged
- **AND** no `click.Choice` value, no `valid_spec_sets` entry and no directory-mapping branch MUST name it, so `--specification-set jca_android_bug_predicate` MUST be rejected with the four accepted values
- **AND** `data/gh101/divergence_record.csv` MUST still describe it, since archiving preserves the record of what it was rather than restating it

#### Scenario: a repair lands in `jca_android`

- **WHEN** a task edits `jca_android/TrustManagerFactorySpec.mop`
- **THEN** `data/jca_android/divergence_record.csv` MUST gain one entry per hunk naming the reason and the task
- **AND** the gate that recomputes the hunks between `jca/` and `jca_android/` MUST report every hunk as recorded
- **AND** `jca/TrustManagerFactorySpec.mop` MUST be byte-identical to commit `7e7acb69`

### Requirement: Allow-List Conformance to the Generated api30 Rules

Every allow-list of `jca_android` SHALL be a literal transcription of the `CONSTRAINTS` clause of the corresponding rule in `MetaCrySL/generated/api30/`, and a gate SHALL compare the two mechanically for all 21 specifications (INV-INS-127). This is what makes the successor set an Android instrument rather than a Java SE instrument with an Android name: the frozen `jca` lists were written by hand against the Java SE providers, and the three values that dominate the published measurement — `AndroidKeyStore`, `TLS`, `X509` — are correct on Android 11 and wrong only against those lists. MetaCrySL is not modified by this contract; the rules under `generated/api30/` are read as they stand.

Literal transcription alone leaves roughly three thousand of those events unresolved, because the rule writes the JCA standard name and the app writes what Conscrypt registers. The set SHALL therefore declare one normalisation rule and apply it uniformly: **comparison is case-insensitive**, and an observed value matches a list entry when a row of the set's **alias table** maps it to that entry. The alias table is derived from the Conscrypt `android11-release` branch — 158 rows, 114 of them flagged `in_api30_allowlist=yes` and 44 `no`; 9 rows belong to services no specification of the set covers (`AlgorithmParameters`, 8 rows, 5 `yes`/3 `no`; `SecretKeyFactory`, 1 row, `yes`) and are kept with their flag, so of the 114 `yes` rows 108 are in services the 21 specifications cover and resolve at run time, and 6 are `yes` against a rule the set does not carry — and every row SHALL carry its primary-source pointer: `X509` → `PKIX` from `OpenSSLProvider.java:90`, `SHA1` and `SHA` → `SHA-1` from `OpenSSLProvider.java:115-116`, `SHA256` → `SHA-256` from `OpenSSLProvider.java:124`. Every row SHALL carry such a pointer, and a spelling no registration in that file explains SHALL NOT be given a row: the one measured case is the padding token `OAEPWithSHA1AndMGF1Padding`, which the api30 rule writes as `OAEPwithSHA-1andMGF1Padding` and which Conscrypt registers only in its hyphenated form (`OpenSSLProvider.java:338`, alias at `:339-340`), and which is therefore recorded as a divergence with behavioural evidence rather than normalised by the table (INV-INS-127). Uniform case-insensitivity also removes a second inconsistency the frozen set carries by accident: it compares case-sensitively in eight specifications (`Mac`, `Signature`, `SecureRandom`, `KeyGenerator`, `TrustManagerFactory`, `KeyManagerFactory`, `KeyStore`, `KeyPairGenerator`) and through `.toUpperCase()` in three (`MessageDigest`, `SSLContext`, `SecretKeySpecSpec`), so the same string is a misuse in one specification and not in another.

The alias table SHALL live in **`data/jca_android/alias_table.csv`, a file of its own** — not a column of the conformance record, which answers a different question (which api30 rule a specification transcribes) and would make the 158 rows illegible inside 21 — and each row SHALL name the specification it applies to. Resolution SHALL happen **at runtime, and not by reading the CSV**: a new utility class under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` SHALL carry the table as code, each `jca_android` allow-list check SHALL name that class in its call, and a test SHALL assert that the in-code table equals the CSV row for row. This is the pattern INV-INS-112 already fixes for the `Cipher` transformation tables — the specification names the utility it calls, nothing selects between tables at runtime, and no shared mutable key exists — and it is what keeps the frozen `jca` out of reach: no `jca` specification names the class, so no verdict of the frozen set moves.

Expanding the aliases into the allow-lists instead SHALL NOT be done, for three reasons. (a) It cannot express what is being decided: case-insensitive comparison is not expansible, so an expanded list would have to enumerate every spelling of every entry in every case. (b) It destroys the gate: an expanded list is no longer equal to the api30 clause, so G-CONF has nothing left to compare and the whole conformance argument collapses into a diff nobody can read. (c) It repeats the exact defect this contract removes — the frozen `jca` already resolves aliases by mixing them into the allow-list, which is why `KeyGeneratorSpec`, `MacSpec` and `SecretKeySpecSpec` carry `HMAC-SHA256`, `HMAC/SHA256` and `PBEWITHHMACSHA-256` as if they were algorithms the platform offers, and why nobody can tell from the file which entries came from a rule and which from a provider registration.

Where the transcription and the platform disagree, the set SHALL follow one asymmetric rule, applied in both directions and recorded either way.

**Where the api30 rule ADMITS a value, the set admits it, and the detection the frozen `jca` performed there is lost.** This is a decision, not a pending item: the single oracle is what makes the set's verdicts checkable, and re-adding a value the rule allows because the researcher prefers a stricter list would restore exactly the JSE-era preference-as-fact that produced the `TLS` and `AndroidKeyStore` reports. The largest case is measured. The api30 `MessageDigest` rule admits `MD5` and `SHA-1`, and the api30 `Signature` rule admits `MD5withRSA` and `SHA1withRSA`; the published dataset carries **6,048** `MessageDigestSpec` / `UnsafeAlgorithm` rows, of which **3,552** are `MD5` and **2,340** are `SHA-1`, `SHA1` or `SHA`. Those **5,892** rows — 97.4 % of that specification's `UnsafeAlgorithm` reports (36.4 % of all its 16,183 reports) and 6.1 % of the 97,018 rows of the corpus — stop being reported. The loss SHALL be entered in the conformance record against `MessageDigestSpec` and `SignatureSpec` with these numbers, so that no later reader mistakes the silence for a regression.

**Where the api30 rule OMITS a value the platform provably carries, the list receives it**, and the divergence record SHALL carry an entry citing the platform source. The rule never runs the other way: nothing the api30 rule admits is ever removed, and nothing is ever added on preference alone. Two cases are proved and SHALL be taken.

The first is **`EC` in the `KeyPairGenerator` allow-list, with `keySize in {256}`** — kept against the literal rule, not added: the seed already carries it (`jca/KeyPairGeneratorSpec.mop:22`, `validate` at `:34`), and a literal transcription would remove it. The generated rule reads `alg in {"DSA", "DH", "RSA"}` and then `alg in {"EC"} => keySize in {256}` — since CrySL `CONSTRAINTS` are conjunctive, the second clause is unreachable and `EC` is rejected outright. The cause is a modelling defect in MetaCrySL and the divergence entry SHALL name it: `samples/jca/android/11plus/KeyPairGenerator.ref:2` writes `define algorithm = {"EC"};`, which fills a `${algorithm}` hole, but `samples/jca/base/KeyPairGenerator.cryptsl:27` writes the list as a literal instead of `alg in ${algorithm}`, so the `define` is discarded in silence. The same tier uses the same idiom in `KeyGenerator.ref` and it works, because the base rule there does have the hole; only three base rules fix a literal list (`KeyManagerFactory`, `KeyPairGenerator`, `TrustManagerFactory`) and only `KeyPairGenerator` has an Android `.ref` trying to extend one. The root fix is `alg in ${algorithm}` in the base rule and is explicitly not performed here. Transcribing this one literally would manufacture exactly the class of spec-artefact this contract exists to remove: `EC` is the algorithm Android recommends for `AndroidKeyStore` keys.

The second is **`SHA1withECDSA`, `SHA256withECDSA`, `SHA384withECDSA` and `SHA512withECDSA` in the `SignatureSpec` allow-list**. The api30 rule lists only `SHA224withECDSA`, because the one MetaCrySL tier that touches ECDSA at all is `20plus` and it names that single algorithm; the four others were never modelled. That they exist on API 30 is not inferred but read off the platform: Conscrypt `android11-release` registers `Alg.Alias.Signature` entries whose targets are those algorithm names — `OpenSSLProvider.java:270` and `:271` point at `SHA1withECDSA`, `:286` at `SHA256withECDSA`, `:293` at `SHA384withECDSA`, `:300` at `SHA512withECDSA` — and a provider cannot register an alias to a service it does not implement. Without this entry `SHA256withECDSA` becomes a false positive, and it is the algorithm Android documents for EC keys in the `AndroidKeyStore`, the same keys the `EC` divergence above admits; the frozen `jca` already accepted it, so a literal transcription would make the successor set report a misuse where its own predecessor reported none.

The `Cipher` transformation tables SHALL stay in Java and SHALL live in a **new class** under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`, because `CipherSpec` is the one specification that carries no list of its own and the two existing utilities are both untouchable — `CipherTransformationUtil.java` belongs to the frozen `jca` and `AndroidCipherTransformationUtil.java` belongs to the archived `jca_android_bug_predicate`. The new class SHALL transcribe the `CONSTRAINTS` of `generated/api30/Cipher.cryptsl`, `jca_android/CipherSpec.mop` SHALL name it, and G-CONF SHALL read that class for `CipherSpec` and the `.mop` file for the other 20 specifications (INV-INS-112: the specification names the utility it calls, and no runtime switch selects it). The alias utility of the normalisation rule is the same pattern applied a second time, in the same package.

#### Scenario: the constraint table is what G-CONF reproduces on the seed

- **WHEN** G-CONF runs on the frozen `jca` with `generated/api30/` as its oracle
- **THEN** its per-clause report MUST equal `data/jca_android/constraint_table.csv` row for row — `spec`, `cryptsl_line`, `mop_line` and the verdict among `CRYSL-NAO-IMPLEMENTADO`, `IGUAL`, `MOP-SEM-BASE`, `MOP-MAIS-PERMISSIVO`, `DIVERGENTE`, `MOP-MAIS-RESTRITIVO`
- **AND** every `CRYSL-NAO-IMPLEMENTADO` row MUST have a matching `deferred-constant` row in `data/jca_android/conformance_record.csv` (INV-INS-125), so no declared clause is left neither transcribed nor deferred

#### Scenario: the keystore list is transcribed

- **WHEN** the conformance gate compares `jca_android/KeyStoreSpec.mop` with `generated/api30/KeyStore.cryptsl`
- **THEN** the specification's allow-list MUST be exactly `AndroidKeyStore, PKCS12, BKS, BouncyCastle, AndroidCAStore`, the members of the clause `keyStoreAlg in {"AndroidKeyStore", "PKCS12", "BKS", "BouncyCastle", "AndroidCAStore"}`
- **AND** `KeyStore.getInstance("AndroidKeyStore")` MUST produce no report, where the frozen `jca` produces `InvalidKeyStoreType` — 2,005 events over 11 apps and 12 misuses in the published measurement

#### Scenario: the TLS protocol list is transcribed

- **WHEN** the conformance gate compares `jca_android/SSLContextSpec.mop` with `generated/api30/SSLContext.cryptsl`
- **THEN** the specification's allow-list MUST be exactly `Default, TLSv1.2, TLSv1.1, SSL, TLSv1, TLS, TLSv1.3`
- **AND** `SSLContext.getInstance("TLS")` MUST produce no report, where the frozen `jca` produces `UnsafeProtocol` — 8,648 events over 60 apps and 65 misuses, the single largest contributor to the published count

#### Scenario: a list the rule makes narrower is narrowed

- **WHEN** the conformance gate compares `jca_android/SecureRandomSpec.mop` with `generated/api30/SecureRandom.cryptsl`
- **THEN** the specification's allow-list MUST be exactly `SHA1PRNG`
- **AND** the values the frozen list carries and the rule omits (`Windows-PRNG`, `NativePRNG`) MUST be absent, because they name providers that do not exist on Android 11
- **AND** the narrowing MUST NOT be entered in the divergence record, since it is the transcription itself and not a departure from it

#### Scenario: an alias matches and a non-alias does not

- **WHEN** `TrustManagerFactory.getInstance("X509")` fires against the transcribed list `PKIX`
- **THEN** the alias row `X509 → PKIX`, sourced to Conscrypt `OpenSSLProvider.java:90`, MUST make it match and no report MUST be emitted — 643 events over 3 apps and 5 misuses in the published measurement
- **AND** `TrustManagerFactory.getInstance("SunX509")` MUST still be reported with `error_type=UnsafeAlgorithm`, because `SunX509` is neither in the api30 clause `algo in {"PKIX"}` nor a row of the alias table
- **AND** the alias row MUST appear in `data/jca_android/alias_table.csv` naming `TrustManagerFactorySpec`, and the transcribed allow-list of `TrustManagerFactorySpec.mop` MUST still read exactly `PKIX`, so the alias never enters the list it resolves against

#### Scenario: the alias table is code at runtime and a file on disk

- **WHEN** the allow-list check of `jca_android/TrustManagerFactorySpec.mop` resolves `X509`
- **THEN** it MUST call the alias utility class under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` by name, and no runtime read of `alias_table.csv` MUST occur
- **AND** a test MUST assert that the class's table and `data/jca_android/alias_table.csv` hold the same rows, so a row added to one and not the other fails
- **AND** no `.mop` of `jca` MUST name that class, so the frozen set's verdicts are unchanged by its existence

#### Scenario: case alone does not make a misuse

- **WHEN** `Signature.getInstance("SHA256WITHRSA")` fires against the transcribed list, which carries `SHA256withRSA`
- **THEN** the case-insensitive comparison MUST make it match and no report MUST be emitted — 4 events over 1 app and 1 misuse in the published measurement
- **AND** no alias row MUST be needed for it, since the two strings differ only in case

#### Scenario: `EC` is admitted as a recorded divergence

- **WHEN** the conformance gate compares `jca_android/KeyPairGeneratorSpec.mop` with `generated/api30/KeyPairGenerator.cryptsl`
- **THEN** the specification's allow-list MUST be `DSA, DH, RSA, EC`, one entry wider than the clause `alg in {"DSA", "DH", "RSA"}` — `EC` kept from the seed against the literal rule, not added to it — and its RSA key sizes MUST be `{4096, 2048}` (`KeyPairGenerator.cryptsl:51`), so the seed's acceptance of `3072` (`validate`, `:30`) is a transcription hunk entered in the conformance record
- **AND** `data/jca_android/divergence_record.csv` MUST carry an entry naming `EC`, its `keySize in {256}` companion clause, and the MetaCrySL defect (`11plus/KeyPairGenerator.ref:2` defines `algorithm` while `base/KeyPairGenerator.cryptsl:27` writes the list literally instead of `alg in ${algorithm}`, so the define is discarded)
- **AND** the entry MUST also record that a literal transcription would be a regression against the frozen set, whose list at `jca/KeyPairGeneratorSpec.mop:22` already reads `RSA, EC, DSA, DiffieHellman, DH`
- **AND** without that entry the gate MUST fail, so the exception cannot be taken twice or taken silently

#### Scenario: the ECDSA signature algorithms the rule omits are added on platform evidence

- **WHEN** G-CONF compares `jca_android/SignatureSpec.mop` with `generated/api30/Signature.cryptsl`, whose ECDSA content is the single entry `SHA224withECDSA`
- **THEN** the specification's allow-list MUST additionally carry `SHA1withECDSA`, `SHA256withECDSA`, `SHA384withECDSA` and `SHA512withECDSA`
- **AND** `data/jca_android/divergence_record.csv` MUST carry an entry per added algorithm citing the Conscrypt registration that proves it exists on API 30 (`OpenSSLProvider.java:270,271` for `SHA1withECDSA`, `:286`, `:293` and `:300` for the other three) and naming the modelling gap — only the `20plus` tier touches ECDSA and it names one algorithm
- **AND** `Signature.getInstance("SHA256withECDSA")` MUST produce no report, where a literal transcription would report a misuse the frozen `jca` did not report

#### Scenario: a value the rule admits is admitted and the loss is declared

- **WHEN** G-CONF compares `jca_android/MessageDigestSpec.mop` with `generated/api30/MessageDigest.cryptsl`, whose `CONSTRAINTS` admit `MD5` and `SHA-1`
- **THEN** the specification's allow-list MUST admit them, and `MessageDigest.getInstance("MD5")` MUST produce no report
- **AND** `data/jca_android/conformance_record.csv` MUST record the detection lost: 5,892 of the 6,048 `MessageDigestSpec` / `UnsafeAlgorithm` rows of the published dataset (3,552 `MD5`, 2,340 `SHA-1`/`SHA1`/`SHA`), 97.4 % of that specification's `UnsafeAlgorithm` reports (36.4 % of all its reports) and 6.1 % of the corpus
- **AND** the entry MUST NOT be a divergence: the set follows its oracle here, and re-narrowing the list on preference would be the departure

#### Scenario: the Cipher tables live in a new Java class

- **WHEN** the conformance gate resolves the allow-list of `CipherSpec`
- **THEN** it MUST read the new class under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` that `jca_android/CipherSpec.mop` names, not a `.mop` list
- **AND** the class's algorithm table MUST be `ChaCha20, AES_128, ARC4, RSA, DESede, AES, BLOWFISH, AES_256`, the members of `part(0,"/",transformation) in {...}` in `generated/api30/Cipher.cryptsl`
- **AND** the observed transformation `RSA/ECB/OAEPWithSHA1AndMGF1Padding` — 109 events over 1 app and 1 misuse in the published measurement, spelled without the hyphen in `SHA1` — MUST NOT be closed by an alias-table row: the api30 rule writes `OAEPwithSHA-1andMGF1Padding`, Conscrypt registers `RSA/ECB/OAEPWithSHA-1AndMGF1Padding` (`OpenSSLProvider.java:338`) and the alias `RSA/None/OAEPWithSHA-1AndMGF1Padding` (`:339-340`), both hyphenated, and the unhyphenated spelling appears in no registration of that file, so no row could carry the pointer INV-INS-127 requires
- **AND** because `CipherSpec.g1` is an `after … returning(Cipher c)` advice, the 109 calls returned a `Cipher`, which is behavioural proof that some other platform provider accepts the spelling; the case MUST therefore be entered in `data/jca_android/divergence_record.csv` as a divergence whose evidence is labelled **behavioural**, with identifying that provider recorded as execution work
- **AND** `CipherTransformationUtil.java` and `AndroidCipherTransformationUtil.java` MUST both be byte-unchanged, so the frozen and the derived sets keep the verdicts they were measured with

### Requirement: The Successor Set Carries No Predicate

No `.mop` of `jca_android` SHALL reference `ExecutionContext` — not `validate`, not `setProperty`, not `remove` (INV-INS-128). A predicate makes one specification's verdict depend on state another specification wrote at another point in the trace, and on Android that dependency is the largest single source of reports nobody can act on: the report names the call that read the predicate, never the call that failed to write it, so the message cannot say what the developer must change. The gate is **G-PRED**, a grep, so it cannot drift. It is the regime the archived `jca_android_bug_predicate` is named after: that set tried to repair the predicate graph and the audit measured the result, which is why the successor removes the machinery instead of inheriting it.

The cost SHALL be stated rather than absorbed, one row per removed site in `data/jca_android/predicate_removal.csv` — the file name is not `predicate_omissions.csv`, which in gh101 records a `Property` written and never read, a different thing this set cannot have. Of the 21 events that read a predicate in 8 of the 21 files the seed keeps (all inside `condition()`), **10 read one only as a guard**: removing those is a net gain, because a guard that fails today makes the event vanish, the automaton advance from the wrong cause, and the specification fall silent exactly where it was meant to speak. The remaining **11 accuse on a predicate basis** — by their transition row, not by their body: an all-`fail` row accuses through `@fail` whatever the body says — and those accusations are lost — seven of them entirely (`IvParameterSpec c3/c4`, `PBEKeySpecSpec err2/err3`, `SecureRandomSpec c3/setSeed3`, `SecretKeySpecSpec c3`, whose allow-list half then goes with the transcription because the rule declares nothing about `alg`), one in part (`PBEParameterSpecSpec c3` keeps its iteration-count half), and three by cross-specification key provenance (`CipherSpec i2`, `MacSpec i1/i2`, all reading `GENERATED_KEY`). The last three cost nothing in practice and the measurement says so: keys obtained from `AndroidKeyStore`, Tink or `KeyGenParameterSpec` never carry `GENERATED_KEY`, which is why 11,620 events over 80 misuses in 25 apps already fail that provenance check for a reason that has nothing to do with misuse.

The removal also retires **9 `remove(...)` sites** — 4 deprecated one-argument `remove(Property)`, 5 two-argument `remove(Property, Object)` — against **2 `NEGATES` clauses in the whole api30 catalogue**, exactly one of which a site encodes (`PBEKeySpecSpec:72` in `clearPassword`, `NEGATES speccedKey after cP`). The store was doing four times more invalidation bookkeeping than the rules ever asked for, and each of those sites is a place where one specification could silently disarm another.

#### Scenario: the predicate gate finds no reader and no writer

- **WHEN** the predicate gate scans every `.mop` under `jca_android/`
- **THEN** it MUST find zero occurrences of the identifier `ExecutionContext`
- **AND** a single occurrence MUST fail the gate naming the file and the line, whether it is a `validate`, a `setProperty` or a `remove`
- **AND** no `data/jca_android/predicate_omissions.csv` MUST exist, since INV-INS-111 has nothing to constrain in a set that writes no `Property`
- **AND** `data/jca_android/predicate_removal.csv` MUST account for all 21 predicate-reading events, the 9 `remove(...)` sites and the 25 `setObjectAsInAcceptingState`/`unsetObjectAsInAcceptingState` calls of the seed (55 rows; the 46 `setProperty` deletions, the 21 `import` deletions and the comment at `MessageDigestSpec.mop:25`, in 19 of the 21 files, are divergence entries, not rows), classified as guard, total-loss, partial-loss, provenance, remove or accepting-state
- **AND** every predicate-only accuser (an event with an all-`fail` transition row whose only guard was the predicate) MUST have its declaration deleted, not its `condition()` emptied — kept, it would accuse on every legitimate call of its pointcut

#### Scenario: the two pure propagators cease to exist

- **WHEN** `RandomStringPassword.mop` and `SecretKeySpec.mop` are examined after their `ExecutionContext` statements are removed
- **THEN** neither file MUST retain a report site or an automaton branch that any event can reach, since each existed only to write a `Property`
- **AND** both MUST be absent from `jca_android/`, leaving 21 specifications
- **AND** `data/jca_android/divergence_record.csv` MUST carry one entry per removed file naming it as a pure propagator

#### Scenario: a lost accusation is declared

- **WHEN** the trace `KeyStore.getInstance("AndroidKeyStore"); ks.getKey(alias, null); Cipher.init(ENCRYPT_MODE, key)` is replayed through `CipherSpec` before and after the removal
- **THEN** the frozen snapshot MUST report at `Cipher.init` because `key` carries no `GENERATED_KEY`, and the `jca_android` snapshot MUST report nothing
- **AND** the divergence record MUST carry that difference as a lost detection, not as a repair
- **AND** the harness output MUST be committed as the evidence for it (INV-INS-124)

#### Scenario: a silencing guard is removed

- **WHEN** an event whose `condition()` reads a predicate that no producer in the set writes is compared before and after the removal
- **THEN** the frozen snapshot MUST show the event never firing, so the specification never speaks at that call
- **AND** the `jca_android` snapshot MUST show the event firing and its allow-list check running
- **AND** the divergence record MUST classify the hunk as a recovered check, distinguishing it from the 11 lost accusations

### Requirement: Violation Report Message Envelope

Every report site in `jca_android` SHALL call the four-argument `ErrorDescription` constructor, and the fourth argument SHALL be a v1 envelope:

```
v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<free text>'
```

`code` is the failure identifier of the site, one per `@fail` (`<SPEC>-ORDER-00`) and one per value site, listed in `jca_android/codes.csv` and cross-checked by the message-property gate; `ev` is the name of the event that fired, obtained from the `__EVENTNAME` macro the generator expands (INV-INS-120); `obj` is the simple class of the monitored object; `val` and `exp` carry the observed and the expected value, both quoted with `'`, a literal `'` escaped as `\'`; `msg` is the human sentence. There is no `st=` field: state indices are assigned after minimisation and do not follow declaration order, so a spec-side state name would be silently wrong. Commas are allowed inside values (27 % of today's messages contain them and every consumer rejoins field 7); `\n` and `:::` are not, because the first splits the logcat line and the second is the separator of `unique_msg`. Truncation is the consumer's problem to detect: the producer bounds `val` to 512 characters and the parser treats an unclosed quote as a truncated record.

`ErrorType` (`rvsec-core/.../eh/ErrorType.java`) SHALL gain `ForbiddenMethod`, with the `code` prefix `FORB` in `codes.csv`. A CrySL `FORBIDDEN` clause is not a predicate — it names a constructor or method that must never be called at all — and the set already encodes two of them, at `PBEKeySpecSpec.mop:24,30`, where they are reported as `InvalidSequenceOfMethodCalls`. That type says the calls arrived in the wrong order, which tells the developer to reorder something that no reordering can fix. `RequiredPredicate` SHALL NOT be added: `REQUIRES` clauses are what INV-INS-128 removes from this set, and an `ErrorType` no site can emit is a promise the enum makes and the specifications break.

The 16 sites whose message reads `but found` and interpolates a monitor field (`currentAlgorithmInstance`, `currentTransformation`, `currentKSType`, `currentProtocol`, `algorithm`) SHALL interpolate instead the value read from the target object the reporting event binds — `getAlgorithm()` on `Cipher`, `KeyGenerator`, `KeyPairGenerator`, `Mac`, `MessageDigest`, `Signature`, `KeyManagerFactory`, `TrustManagerFactory`; `getType()` on `KeyStore`; `getProtocol()` on `SSLContext` — because none of those events binds the algorithm, type or protocol argument (only the `getInstance` events do; `SecureRandomSpec.mop:82`, in `g4`, already interpolates its argument and stays). The field is empty until an instantiation event writes it in the same parameter slice, which is the mechanism behind the 8,843 empty labels; the getter has no such gap.

Message text SHALL agree with the check that guards it (INV-INS-121). The census this contract starts from — measured on the frozen `jca`, carried into `jca_android` by the seed — is: `PBEKeySpecSpec.mop:50` and `PBEParameterSpecSpec.mop:50` say `1000` where the condition tests `10000`, and the api30 `PBEKeySpec` rule agrees with the condition at `>= 10000`; `PBEParameterSpecSpec.mop:49` reports `UnsafeAlgorithm` for an iteration-count constraint and MUST report `UnsatisfiedConstraint`; `PBEKeySpecSpec.mop:24,30` report `InvalidSequenceOfMethodCalls` for a forbidden constructor and MUST report `ForbiddenMethod`; `SecretKeySpecSpec.mop:48,55` report `UnsatisfiedConstraint` for half an algorithm test; `MessageDigestSpec.mop:70,92` (and the commented `:58`, un-commented by the message repair) list three algorithms where the allow-list at `:16` has six; `CipherSpec.mop:61,76` name two accepted transformations and elide the rest with a literal `...`; `KeyGeneratorSpec.mop:64` and `KeyStoreSpec.mop:68` lack the space after `expecting one of`; `MacSpec.mop:62` lacks the verb; `SecretKeySpecSpec.mop:49` says `keyMaterial.length is not randomized` where `:46` tests the array; `KeyPairGeneratorSpec.mop:71-72` is unreachable because `validate()` returns `false` for every algorithm outside its `switch`; leading spaces at `MacSpec.mop:50`, `KeyManagerFactorySpec.mop:55`, `KeyPairGeneratorSpec.mop:72`, `SecretKeySpecSpec.mop:49,56`; and `ErrorDescription.toString()` (`:143`) prefixes `expecting`, so a consumer of `toString()` sees it twice in front of a message that itself starts with `expecting` — the logcat collector emits `getErrorSummary()+","+getExpecting()` (`ErrorCollector.java:38`) and `errors.csv` carries the envelope as written, so the duplication is recorded as a `toString()`-only artefact and is not a rule on `msg`, whose `expecting one of … but found …` idiom stays. Correcting these is a precondition of the envelope, not a consequence: an envelope around a lying sentence certifies the lie with a `code`.

#### Scenario: a `@fail` handler names its event

- **WHEN** `jca_android/TrustManagerFactorySpec` reaches `fail` on event `init` after `g1` and `g2` were never seen
- **THEN** the report's message MUST be `v=1 code=TMF-ORDER-00 ev=init obj=TrustManagerFactory val='' exp='' msg='init() before getInstance()'` (free text as authored)
- **AND** the record's `error_type` MUST be `InvalidSequenceOfMethodCalls`
- **AND** the envelope MUST be composed before `__RESET` runs

#### Scenario: a value site interpolates the argument

- **WHEN** `jca_android/TrustManagerFactorySpec.g3` fires for `getInstance("SunX509")`
- **THEN** the message MUST be `v=1 code=TMF-ALG-01 ev=g3 obj=TrustManagerFactory val='SunX509' exp='PKIX' msg='expecting one of PKIX but found SunX509'`
- **AND** `val` MUST come from the bound argument `alg`, never from `currentAlgorithmInstance`
- **AND** `exp` MUST be the transcribed api30 list joined, so the message and the allow-list cannot drift apart

#### Scenario: a forbidden constructor reports as forbidden

- **WHEN** `jca_android/PBEKeySpecSpec` fires the site at `:24`, which today reports `InvalidSequenceOfMethodCalls`
- **THEN** the record's `error_type` MUST be `ForbiddenMethod` and the envelope's `code` MUST carry the `FORB` prefix
- **AND** `ErrorType` MUST NOT contain `RequiredPredicate`, since no site of the set can emit it

#### Scenario: no three-argument site remains

- **WHEN** the message-property gate scans `jca_android/*.mop`
- **THEN** it MUST find zero `new ErrorDescription(` calls with three arguments (the frozen `jca` has 25: 21 `@fail` blocks, `IvParameterSpec.mop:48,55`, `PBEKeySpecSpec.mop:24,30`)
- **AND** every `code` it finds MUST exist in `codes.csv`, and every `codes.csv` row MUST be emitted by exactly one site

#### Scenario: a numeric literal disagrees with its guard

- **WHEN** a message says `>= 1000` and the `condition()` guarding it tests `< 10000`
- **THEN** the message-property gate MUST fail naming the file, the line and the two literals

### Requirement: Event-Name Emission by the Monitor Generator

A specification SHALL obtain the name of the offending event by writing the macro `__EVENTNAME` where its envelope needs `ev=`, and the generator SHALL expand it (INV-INS-120). No specification file carries a bookkeeping field or a bookkeeping statement: the information the macro exposes is one the generated monitor already holds, and duplicating it by hand in every event body of every set is what this contract exists to avoid.

The expansion has two forms, because a report site is either inside an event body or inside a handler. Inside an **event body** the name is known when the monitor is generated, so `__EVENTNAME` becomes a string literal and costs nothing at runtime. Inside a **handler body** — the `@fail` case, which is 21 of the 25 sites that render `unknown` today — the offending event is only known at runtime, and the monitor already records it: the atomic/table monitor shape packs the event index into `pairValue` and exposes `getLastEvent()`, and the non-atomic shape keeps a `RVM_lastevent` field and inherits `getLastEvent()` from `AbstractSynchronizedMonitor.java:21`. The generator SHALL therefore emit, once per monitor class, a table of event names indexed by the same event index the transition dispatch uses, and expand `__EVENTNAME` in a handler to a lookup in that table through `this.getLastEvent()` — the same expansion in both monitor shapes. The table and the indices SHALL be produced by one iteration over the specification's event definitions, so that a name and its index cannot disagree.

Two properties make the handler form correct, both verified on the generated monitor of the frozen `jca`: the handler is a method of the monitor class whose event index is being read, and `__RESET` — which clears that index — is substituted *after* the report call, so the offending event is still recorded when the envelope is composed. An event that fails its `condition()` never runs its body and never transitions, because the generator emits the guard before the body; it therefore can never be reported as the offending event.

Two residues are declared rather than hidden. Where a `@fail` handler does not call `__RESET`, the category flags survive and the next event re-runs the handler while the recorded index has already moved — `KeyPairGeneratorSpec` is the only such handler in the set and it gains `__RESET`. The second residue the lineage declared — `KeyGeneratorSpec.g3` (`:47`) and `MessageDigestSpec.g4` (`:55`) testing the field `currentAlgorithmInstance` instead of the argument `alg`, so that two events might pass their guards on one call and dispatch order decide which is recorded — does not exist: `g1` is emitted first in the same wrapper (`MonitorWrappers.java:192-193`, `:357-358`) on the same object-indexed monitor and writes the field before the sibling's condition runs, and the field is initialised to `""`, so the sibling fires exactly when `!contains(alg)`. It is recorded in the conformance record as a checked non-defect (the equivalence rests on declaration order) and not repaired.

#### Scenario: the macro expands to a literal inside an event body

- **WHEN** a specification writes `__EVENTNAME` inside the body of `event g3`
- **THEN** the generated event method MUST carry the string literal `"g3"` at that position
- **AND** no field and no runtime lookup MUST be emitted for it

#### Scenario: the macro expands to the offending event inside a `@fail`

- **WHEN** a specification writes `__EVENTNAME` inside `@fail` and a trace drives the monitor into `fail` through event `init`
- **THEN** the composed envelope MUST carry `ev=init`
- **AND** this MUST hold for a specification of each monitor shape — one whose monitor derives the index from `pairValue` and one that keeps a `RVM_lastevent` field
- **AND** a handler that runs before any event has transitioned the monitor MUST render `ev=none`, never an out-of-range lookup

#### Scenario: no unexpanded macro reaches the generated Java

- **WHEN** monitors are generated for any specification set
- **THEN** the literal `__EVENTNAME` MUST NOT appear anywhere in the generated Java
- **AND** the generation step MUST fail closed if it does, naming the file and line, because an unexpanded macro would otherwise reach the compiler as an undefined identifier or, worse, be silently reported as text

#### Scenario: two events share a name

- **WHEN** a specification declares `event c1` twice (as `GCMParameterSpecSpec.mop:23,34` does today, where the second is the misnamed `c2` the rule declares)
- **THEN** the lint MUST fail, because the generated monitor would carry two `Prop_1_event_c1` methods and one `c1` transition row (gate G-6′)

### Requirement: The Generated Dispatcher Releases Its Lock on Every Exit

Every dispatcher the monitor generator emits serialises its work behind one `ReentrantLock` shared by the whole generated file. The generator SHALL emit that region so the lock is released whatever path leaves it, exception included (INV-INS-129).

Today it does not. Measured on the frozen control monitor (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`, 2026-08-18): one lock at `:9005`, 134 acquisitions of the form `while (!MultiSpec_1_RVMLock.tryLock()) { Thread.yield(); }`, 134 matching `unlock()` calls, and no `finally` block anywhere in the file. The failure this permits is worse than a lost report, and that is why it is stated as its own contract rather than left to the specifications. A monitored call whose `condition()`, event body or `@fail` handler throws unwinds past the `unlock()`; the lock stays held by a thread that is no longer inside the region; and because the waiting form is a spin rather than a block, the next monitored call of **any** specification enters an unbounded `Thread.yield()` loop. The application stops progressing, the instrumentation stops emitting, and the run is indistinguishable from a timeout.

The path is reachable in the set this contract seeds from: `KeyPairGeneratorSpec.mop:29` switches on a field that only the `getInstance` events write, and `KeyPairGenerator.getInstance(String, Provider)` is bound by no pointcut, so a generator obtained through that overload reaches `initialize(int)` with the field `null` and `switch(null)` raises inside the guarded region. Repairing that one field (a specification repair) closes one door; this requirement closes the class, because any future guard or handler can raise.

The repair SHALL change nothing else about the dispatcher — not which advices fire, not the identity of the lock, not the spin loop — and SHALL be verified by regeneration rather than by inspection.

#### Scenario: a handler throws and the next event still runs

- **WHEN** a monitored call enters a dispatcher, acquires the lock, and the specification's `condition()` or handler raises a `RuntimeException`
- **THEN** the exception MUST propagate to the application as it does today
- **AND** the lock MUST be released before it propagates, so a subsequent monitored call of any specification **from another thread** acquires it and completes (the lock is reentrant: the throwing thread itself would re-enter regardless, so a same-thread second call proves nothing)

#### Scenario: regeneration is otherwise byte-identical

- **WHEN** the frozen `jca` and the archived `jca_android_bug_predicate` are regenerated with the repaired generator and diffed against the frozen control monitor
- **THEN** the only differences MUST be the lock framing, the event-name table (INV-INS-120) and the expanded `__EVENTNAME`
- **AND** the count of acquisitions MUST still equal the count of releases, now with every acquisition inside the framing

### Requirement: Arity Mismatch Is Measured, Not Filtered, in Wrapper Grouping

When `WrapperEmitter` groups the advices bound to one concrete call into a single merged wrapper (`WrapperEmitter.java:246-274`, decision D-B1 of gh100), it SHALL NOT remove any advice from the group. It SHALL instead evaluate, per advice, whether the advice's positional `args()` arity is compatible with the call's parameter count, under three clauses (INV-INS-122): an advice with no `args()` clause is never counted; the arity is the length of `ArgsPC.types()`, with a trailing `..` meaning "at least this many" (`ArgsPC.names()` drops the `..` and would make `args(transformation, ..)` look like fixed arity 1); the evaluation runs inside the grouping loop, the only place where the advice and the concrete overload coexist. Every incompatible advice SHALL be counted per APK as `advicesExcludedByArity` and reach `instrument_results.json` through `BatchRunner`'s counts map, beside `wrappersGenerated`. The name is kept because the counter measures exactly the population a filter would exclude.

Counting before filtering is the point of this contract, not a step towards it. Today `getInstance(String)` fires the two-argument advice's monitor call because the group is keyed on the call alone; the rule the lineage first wrote — drop any advice whose `args` length differs from the call's — would have dropped the **25** `after` advices that have parameters and no `args()`, counted on the frozen descriptor, and **none of them is a constructor advice** (constructor advices carry an empty parameter list, so they were never in this population at all). That is why the clause exempting them exists, and the corrected count makes the reason stronger rather than weaker: the rule the lineage wrote first would have silenced 25 advices, not 16, among them `SSLContextSpec_init` and `MessageDigestSpec_update`, which alone raise 2,629 of the 3,950 legible rows of the E3 trial (66.6 %: 1,466 and 1,163). A filter shipped together with the specification-side repairs would change what every campaign reports in the same commit that first measures how much there is to change, and no measurement afterwards could separate the two contributions — the same conflation `The Java SE Specification Set Is Frozen` records for allow-list versus repair. The counter is published first; whether to filter is decided against the number it produces.

The reach of the measurement SHALL be stated wherever it is reported, because it is partial by construction: the evaluation runs in the wrapper grouping loop, and that loop admits only `after` advices (`WrapperEmitter.java:161-163`) and skips constructors explicitly. Nothing outside `pointcut-engine` reads `args()` at all, and `PointcutMatcher.matchArgs` accepts the binding form (`args(alg)`, `args(alg, *)`) unconditionally, so the advices the wrapper path never sees are never counted. On the frozen descriptor (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json`) the 115 advices split as follows: **48** are wrapper-path `after` advices carrying `args()` — the only population the counter can evaluate; **44** carry no `args()` clause at all and clause 1 never counts them — 35 of the 44 are `after` advices, and 25 of those 35 declare parameters, which is the population the lineage's first rule would have dropped; **9** are `before` advices with `args()` (`CipherSpec_i1/i2`, `MacSpec_i1`, `SecureRandomSpec_next1/next2`, `SignatureSpec_i1/i2/i3/i4`); and **14** are `after`-on-constructor advices with `args()` (`DHGenParameterSpecSpec_c1`, `GCMParameterSpecSpec_c1_3`, `GCMParameterSpecSpec_c1_4`, `IvParameterSpecSpec_c1`, `IvParameterSpecSpec_c2`, `KeyPairSpec_c1`, `PBEKeySpecSpec_f1`, `PBEKeySpecSpec_f2`, `PBEKeySpecSpec_c1`, `PBEParameterSpecSpec_c1`, `PBEParameterSpecSpec_c2`, `SecretKeySpecSpec_c1`, `SecretKeySpecSpec_c2`, `SecureRandomSpec_c2`). The last two groups, 23 advices, are outside the wrapper path and the counter is blind to them. Four of the fourteen sit on the four non-`@fail` three-argument report sites of the frozen set: `PBEKeySpecSpec_f1/f2` are the sites at `PBEKeySpecSpec.mop:24,30`, which become `ForbiddenMethod`; the events `IvParameterSpecSpec_c1/c2` are guards, not report sites, but at advice level the `monitorCalls` of the `IvParameterSpecSpec_c1` advice fires both `c1Event` and `c3Event` (`.aj:305-310`), so that advice does sit on the `c3/c4` report sites at `IvParameterSpec.mop:48,55` — sites the predicate removal deletes from `jca_android`. A report from those sites may name its event and its observed value and still have been raised by an advice an arity check would have excluded, without the counter ever seeing it. Closing this at its root means the binding-form check in `PointcutMatcher`, which is recorded as future work.

#### Scenario: an incompatible advice is counted and still fires

- **WHEN** a descriptor carrying only the `TrustManagerFactory` group is woven, `TrustManagerFactory.getInstance(String)` is wrapped and the group carries `g1` with `args(alg)`, `g3` with `args(alg)` and `g2` with `args(alg, *)`
- **THEN** the merged wrapper MUST still fire all three monitor calls, exactly as it does today
- **AND** `advicesExcludedByArity` MUST be `1` for that APK — the unit is advice/overload pairs, and the single pair is `g2` (arity 2) against the one-parameter overload; on the full frozen `jca` descriptor the same rule yields 10 pairs over 4 advices (`SecureRandomSpec_g2` ×3 and `_g4` ×5, `KeyManagerFactorySpec_g2` ×1 besides this one)
- **AND** no `IllegalStateException` MUST be raised and no advice MUST be dropped

#### Scenario: an advice with no `args()` is never counted

- **WHEN** the frozen `jca` descriptor is grouped
- **THEN** the counter MUST evaluate only the 48 wrapper-path `after` advices that carry `args()`
- **AND** the 44 advices with no `args()` clause MUST contribute `0` to `advicesExcludedByArity`, including the 25 wrapper-path ones that declare parameters (`CipherSpec_wkb1`, `CipherSpec_f1`, `CipherSpec_f2`, `KeyGeneratorSpec_gk1`, `KeyManagerFactorySpec_gkm1`, `KeyPairGeneratorSpec_gen`, `KeyPairSpec_gpu`, `KeyPairSpec_gpr`, `KeyStoreSpec_gk1`, `MacSpec_update`, `MacSpec_f1`, `MessageDigestSpec_update`, `MessageDigestSpec_d1`, `MessageDigestSpec_d2`, `PBEKeySpecSpec_c2`, `RandomStringPasswordSpec_gb`, `SecretKeySpec_e1`, `SecureRandomSpec_setSeed1`, `SecureRandomSpec_genSeed`, `SecureRandomSpec_next3`, `SecureRandomSpec_ints`, `SignatureSpec_s1`, `SSLContextSpec_init`, `SSLContextSpec_engine`, `TrustManagerFactorySpec_gtm1`), none of which is a constructor advice
- **AND** two of those 25, `RandomStringPasswordSpec_gb` and `SecretKeySpec_e1`, belong to the two specifications the successor set does not carry (INV-INS-128), so the same population on `jca_android` is 23 and the report MUST name the set it was taken on
- **AND** the 23 advices outside the wrapper path — the 9 `before` and the 14 `after`-on-constructor — MUST contribute `0` as well, and the report of the counter MUST say so rather than let `0` read as "none present"

#### Scenario: trailing `..` is honoured

- **WHEN** an advice declares `args(transformation, ..)` and the concrete call has two parameters
- **THEN** the advice MUST be judged compatible (arity ≥ 1) and MUST NOT be counted
- **AND** the arity MUST be read from `ArgsPC.types()`, since `ArgsPC.names()` drops the `..` and would report a fixed arity of 1

#### Scenario: the counter reaches the results JSON

- **WHEN** a batch instrumentation run completes
- **THEN** `instrument_results.json` MUST carry `advicesExcludedByArity` per APK beside `wrappersGenerated`
- **AND** an APK whose descriptor contains no incompatible advice MUST carry the key with value `0`, never omit it

### Requirement: Violation Line Emission by the Collector

The logcat `ErrorCollector` (`rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java`) SHALL emit `getErrorSummary() + "," + escape(getExpecting().trim())`, where `escape` replaces `\n` with `\\n` and leaves commas untouched, and SHALL guard a `null` expecting value with the sentinel envelope `v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''` instead of throwing. Today the escaping method exists and its call is commented out (`:38`), so a newline inside a message becomes a second logcat line the parser reads as a fabricated record. The CSV collector (`rvsec-logger-csv`) already escapes; both collectors SHALL agree on the escaping rule.

`ViolationRecorder.makeRelevantList` (`rv-monitor-rt/.../ViolationRecorder.java:87-105`) SHALL exclude a monitoring-runtime frame whose `fileName` is `null` instead of including it: today the per-frame filter is fail-open, `getLineOfCode()` returns `relevantStack.get(0)`, and a runtime frame without debug information becomes the reported `location` — which is part of the dedupe identity.

#### Scenario: a message with a newline

- **WHEN** a specification composes an envelope whose `msg` contains `\n`
- **THEN** exactly one logcat line MUST be emitted, with the newline escaped
- **AND** the parser MUST recover the message with the newline restored

#### Scenario: a runtime frame without file name

- **WHEN** the top of the stack at report time is `com.runtimeverification.rvmonitor...` with `fileName == null`
- **THEN** it MUST NOT be the reported `location`
- **AND** the first application frame below it MUST be

### Requirement: Executable Structural Gates for a Specification Set

The orphan-event check (`scripts/gh101_monitor_transition_check.py`, G-2, INV-INS-110) SHALL run as a pytest parametrised by set, together with the structural companions computable on the same transition tables and the pre-generation symbol check (INV-INS-123): G-ERE symbol declaration, G-2 orphan, G-2a inertia, G-2b′ redundancy at `q0`, G-2c dead states, G-2d sink is not `fail`, G-6′ event-name injectivity. Each gate SHALL read the generated monitor of the set — both `AbstractAtomicMonitor` and `AbstractSynchronizedMonitor` shapes — and SHALL fail on any hit not named in `data/<set>/gate_allowlist.csv` with a reason.

**G-2 SHALL take the CrySL rule as a second input.** The gate as first written reported 18 orphan events on the frozen `jca` and every one of them was read as a defect; checked against `generated/api30/`, 17 of the 18 are the correct encoding of a `CONSTRAINTS`, `REQUIRES` or `FORBIDDEN` clause, which by definition names no position in the `ORDER` and therefore cannot appear in the automaton. A gate that calls a correct encoding a defect is worse than no gate, because it spends the reviewer's attention on 17 false positives and buries the one real hit: `MessageDigestSpec.mop:74-76`, the event `reset`, whose body is empty and which no clause of the `MessageDigest` rule accounts for. That hit is not a dormant one. `reset` carries no `condition()` either, so nothing gates it, and the generator writes it the transition row `{4,4,4,4,4}` against a `fail` state of 4 — every woven `MessageDigest.reset()` accuses, whatever the algorithm, and the handler's `__RESET` returns the monitor to state 0 so the call that follows accuses again. Exactly three orphans of the frozen set have no `condition()`: this one and `PBEKeySpecSpec.f1`/`f2`, which encode a `FORBIDDEN` clause and are supposed to accuse on sight. The missing clause is what G-2 tests; the missing guard is what says how much the repair costs. G-2 SHALL therefore fire only where an event is orphaned in the automaton **and** no clause of the corresponding rule accounts for it, — on `jca_android` only a `CONSTRAINTS` or `FORBIDDEN` clause clears, because the set encodes no `REQUIRES` — and SHALL name the rule and clause it consulted when it clears one.

**G-ERE SHALL be added**: every symbol named in a specification's `ere` or `fsm` SHALL have an event declaration, checked before generation. It is a safe extension with no false positive by construction — a symbol either resolves or it does not — and it catches the one defect no downstream gate can see: `GCMParameterSpecSpec.mop:48` names `c2` in its `ere` while the specification declares `c1` twice (`:23,34`, the second of which is the misnamed `c2`), and the generator drops the unresolved symbol in silence.

On the frozen `jca` the expected hits are therefore 1 (G-ERE, `GCMParameterSpecSpec`), 3 (G-2 `orphan-without-clause` under the mechanical clause mapping — `MessageDigestSpec.reset`, `PBEKeySpecSpec.err2`, `SecretKeySpecSpec.c3` — down from 18 raw orphans once the rule is consulted; the reading 17/1 is reached only through `gate_allowlist.csv` rows, which the test MUST name), 1 (G-2a, `SecretKeySpec.e1`), 8 (G-2b′), 1 (G-2c), 2 (G-2d, `SecretKeySpec` and `RandomStringPasswordSpec`, which have no `fail` category), 1 (G-6′, `GCMParameterSpecSpec`); a gate that reports fewer on `jca` is wrong, and a G-2 that still reports 18 has not been given its second input. Four of the `jca` baseline hits — the G-2a hit, one G-2b′ hit (`SecretKeySpec.e1`) and both G-2d hits — belong to specifications `jca_android` does not carry, so the successor set's baseline is not the frozen set's.

A `.mop` lint SHALL run before generation and fail closed on: an ERE or FSM symbol not declared as an event (this is G-ERE); two events with one name; unbalanced parentheses (`SecretKeySpecSpec.mop:27-30`); a report site with three arguments (INV-INS-119); any occurrence of `ExecutionContext` in a file of `jca_android` (INV-INS-128); a hand-written event-name bookkeeping field or statement, which INV-INS-120 forbids now that the generator emits the name. The message-property gate SHALL enforce INV-INS-121 and the `codes.csv` cross-check; **G-CONF** SHALL enforce the allow-list conformance of INV-INS-127 and **G-PRED** the predicate absence of INV-INS-128. The three gate names outside the structural family are mnemonic and not numbered — G-ERE for the `ere` symbol check, G-CONF for conformance, G-PRED for predicates — because a number would suggest an ordering in a family that has none.

The gate the lineage proposed as G-2b ("the out-alphabet of the unsafe state contains the out-alphabet of the safe state") is NOT adopted: minimisation merges the unsafe state into `start` precisely when the alphabets are equal, so the gate is vacuous where it should bite; and the absorbing-state repair it implies was considered and rejected in gh101 D-S9 (two repair philosophies in one set; a false positive traded for a false negative). The residue it targets — a violating branch does not absorb the calls that follow — is recorded in `data/gh101/frozen_set_debt.md`, not gated.

#### Scenario: the gates reproduce the known baseline

- **WHEN** the gate suite runs on `results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java` with `generated/api30/` as G-2's second input
- **THEN** it MUST report exactly 1 / 3 / 1 / 8 / 1 / 2 / 1 hits for G-ERE / G-2 / G-2a / G-2b′ / G-2c / G-2d / G-6′, the three G-2 hits being the `orphan-without-clause` set of the mechanical mapping
- **AND** with `data/jca/gate_allowlist.csv` naming them, the suite MUST pass

#### Scenario: G-2 clears an orphan the rule accounts for

- **WHEN** `PBEKeySpecSpec.f1` is orphaned in the automaton and the `PBEKeySpec` api30 rule carries a `FORBIDDEN` clause naming the constructor it binds
- **THEN** G-2 MUST NOT fire, and MUST record the rule and clause that cleared it
- **AND** the same run MUST still fire on `MessageDigestSpec.reset` (`:74-76`), whose body is empty, which no clause accounts for, and which no `condition()` gates — and, under the mechanical mapping, on `PBEKeySpecSpec.err2` (tests `RANDOMIZED[password]`; the rule requires `randomized[salt]` only) and `SecretKeySpecSpec.c3` (tests an algorithm list the rule does not declare), the frozen baseline being 3

#### Scenario: a repair leaves an orphan

- **WHEN** an event of `jca_android` is bound, absent from its `fsm`/`ere`, and matched by no `CONSTRAINTS` or `FORBIDDEN` clause of its rule (`REQUIRES` does not clear on this set)
- **THEN** G-2 MUST fail naming the specification, the event and the rule it consulted

#### Scenario: an undeclared symbol

- **WHEN** a `.mop` `ere` names `c2` and no `event c2` exists
- **THEN** G-ERE MUST fail before any monitor is generated (today the generator drops the symbol silently)
- **AND** it MUST name the file, the line of the `ere` and the symbol

### Requirement: Differential Harness for Specification Repairs

The system SHALL provide a harness (`scripts/gh104_diff_harness.py` + a JVM trace runner under `rvsec-mop/src/test/`) that, given two snapshots of a specification set and a file of traces per specification, generates the monitor of each snapshot in scratch and replays every trace through both, reporting per trace and per snapshot: accused or not, at which event, with which envelope, and a per-trace class among `unchanged`, `moved`, `removed`, `introduced`. Traces are keyed by API call and resolved against each snapshot's own pointcuts, because two snapshots of one comparison need not share an event alphabet; the trace runner (`TraceRunner`, with its self-test `TraceRunnerTest`) SHALL resolve each trace line against the snapshot's generated **static event dispatchers** (`MultiSpec_1RuntimeMonitor.<Spec>_<event>Event(...)`), not against `mop/MonitorWrappers.java`, so that `before` advices (`MessageDigestSpec.reset`) and inline-woven events are replayable — the harness evidence the automata repairs require depends on it. It exists because static gates measure the artefact and not its behaviour: gh100's wrapper merge removed 12 silently discarded wrappers and created advices of incompatible arity firing at the same site (`wrappersGenerated 96→84` was reported as success); gh101's Group 3/3b removed 18 all-`fail` rows and moved the accusation to the next call. Neither was visible to a gate that counts rows.

No repair task of the allow-list, automata, message or wrapper groups SHALL close without its harness output committed (INV-INS-124); for the allow-list and predicate work of the seed group, which lands in the same wave as the harness, the output is produced as soon as the harness exists and before the automata group starts. The traces SHALL include, for every specification, at least one legitimate sequence, one sequence per authored violating branch, one sequence per value the allow-list transcription newly admits, and the separating traces the audit recorded. Trace replay runs on the JVM, not on a device; device validation is a separate task that uses `rv-experiment run` and is never performed by hand.

#### Scenario: a transcription removes an accusation

- **WHEN** the trace `SSLContext.getInstance("TLS"); init(km, tm, rnd)` is replayed through `SSLContextSpec` in the frozen snapshot and in `jca_android`
- **THEN** the harness MUST report an accusation in the frozen snapshot and none in `jca_android`
- **AND** the task record MUST classify the difference as a corrected verdict, citing the api30 clause `protocol in {"Default", "TLSv1.2", "TLSv1.1", "SSL", "TLSv1", "TLS", "TLSv1.3"}`

#### Scenario: a repair moves the accusation

- **WHEN** a trace `getInstance("SunX509"); init(ks)` is replayed through `TrustManagerFactorySpec` before and after an orphan repair
- **THEN** the harness MUST report the accusation at `getInstance` before and at `init` after
- **AND** the task record MUST classify the result as a moved defect, with the residue named

#### Scenario: a repair removes the report

- **WHEN** a legitimate trace `getInstance("PKIX"); init(ks); getTrustManagers()` is replayed
- **THEN** both snapshots MUST report no accusation
- **AND** any snapshot that accuses it MUST fail the task

### Requirement: Dedupe Identity of a Violation Report

`ErrorSummary.equals` and `hashCode` (`rvsec-core/.../eh/ErrorSummary.java:73-120`) SHALL compare `(spec, error, classQualifiedName, methodName, location, code, event)`; the message free text stays outside (INV-INS-126). Today the identity is the first five, and every specification has at most one `@fail`, so a `code` alone would be a function of `spec` and would refine nothing; it is `event` that separates the causes the record conflates. `ErrorDescriptionTest.hashCodeMatchesEquals` SHALL be rewritten to fix the seven fields.

The change is device-side (it needs re-instrumentation) and creates two eras of every dedupe count. Before it is integrated, the count discontinuity SHALL be measured on the E3 trial (`experimento-comp162`, 19,664 rows, 6,344 distinct 8-tuples `(apk, rep, tool, spec, class, method, source, message)` today; the `ErrorSummary` 5-tuple `(spec, error, class, method, location)` gives 409) by recomputing identities with `event` taken from the envelope, and declared in the change's records — on that trial the two figures are equal by construction (its records predate the envelope, every `event` is the sentinel), which is recorded, not treated as a failure; the number that decides is the same recomputation on an input whose records carry `ev=` (the differential-harness traces or the device logcat of the integration group), and there it MUST be non-zero, otherwise the identity change is a no-op and MUST NOT land.

#### Scenario: two events, one site

- **WHEN** `KeyManagerFactorySpec` reports `InvalidSequenceOfMethodCalls` at `TlsUtil.newKeyManager:191` once from `ev=init` and once from `ev=gkm1`
- **THEN** the collector MUST emit two lines
- **AND** the five-field identity would have emitted one

#### Scenario: the discontinuity is measured

- **WHEN** the E3 trial's identities are recomputed with `event`
- **THEN** the number of identities MUST be recorded next to the 8-tuple count 6,344 and the `ErrorSummary` 5-tuple count 409, with the definition of the recomputation, and labelled zero-by-construction where the trial carries no envelope
- **AND** the same recomputation MUST be run on an input whose records carry `ev=` (harness traces or the device logcat)
- **AND** if the two numbers are equal on that input the identity change MUST NOT be integrated

## MODIFIED Requirements

### Requirement: Specification Set Support (FR03)

The system MUST support multiple, independent specification sets for different API monitoring domains. Each specification set represents a collection of `.mop` files targeting a specific category of API usage patterns. The system MUST ensure that specification sets are never mixed within a single experiment run.

Five specification sets exist under `rvsec-mop/src/main/resources/`; three of them are selectable by name — `jca`, `jca_android`, `generic` — beside `custom`, which takes a directory from the caller:

1. **JCA (Java Cryptography Architecture)** -- 23 specifications derived from CrySL rules, detecting misuses of cryptographic APIs. This set is frozen against the measurements published from it:
   - `CipherSpec.mop`: Cipher initialization and usage sequences. Unlike the other 22, it carries no allow-list of its own and delegates its transformation constraints to shared Java (`rvsec-core`), naming the utility it calls
   - `MessageDigestSpec.mop`: Hash algorithm validation
   - `SSLContextSpec.mop`: TLS protocol validation
   - `SecretKeySpecSpec.mop`: Key specification validation
   - `KeyGeneratorSpec.mop`: Key generation operation sequences
   - `SignatureSpec.mop`: Digital signature operation sequences
   - `MacSpec.mop`: Message Authentication Code operation sequences
   - `KeyStoreSpec.mop`: Keystore operation sequences
   - And 15 additional specifications covering SecureRandom, PBE, IvParameterSpec, etc.

2. **JCA Android, archived** (`jca_android_bug_predicate`) -- the same 23 specifications, derived against generated CrySL rules for a declared Android API level. The derivation altered allow-list content only. Repairs to the platform-independent portion landed here under gh101, and each resulting divergence is entered in `data/gh101/divergence_record.csv` with its reason (INV-INS-109). Its `CipherSpec` names its own transformation utility, `AndroidCipherTransformationUtil`, whose tables come from the generated `Cipher` rule. The set was judged NOT READY by the 2026-08-08 audit and receives no further repair. It is preserved under this name — which records what set it aside, a predicate regime the audit measured — and is **not selectable**: it has no `click.Choice` value and no directory-mapping entry, and reproducing the audit means pointing `RVSEC_HOME` at the commit the audit was run against. It is not the seed of the successor set.

3. **JCA Android** (`jca_android`) -- the successor set, to which the name is rebound: **21** specifications, seeded byte-for-byte from the frozen `jca` and carrying every specification-side change of the legible-report programme — allow-lists transcribed from the generated api30 CrySL rules under a declared normalisation rule, message envelopes, automaton and pointcut repairs. It carries no predicate at all: no `.mop` references `ExecutionContext`, which is why the two pure predicate propagators of the seed (`RandomStringPassword.mop`, `SecretKeySpec.mop`) do not exist in it (INV-INS-128). Its oracle is the api30 rule alone (INV-INS-125); every hunk by which it differs from its seed is entered in `data/jca_android/divergence_record.csv` (INV-INS-118). Its `CipherSpec` names a new transformation utility under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`, transcribed from `generated/api30/Cipher.cryptsl`. It carries `codes.csv`, the table of failure codes its envelopes emit.

4. **Generic (FSM)** -- 118 specifications from the JavaMOP specification database, detecting general API pattern violations such as Iterator hasNext/next ordering, stream resource management, and collection modification during iteration. This set reports through `Log.v` directly, not through `ErrorCollector`, and has never run in a campaign; its report contract is outside the legible-report programme and recorded as debt.

5. **Generic (new)** -- 27 curated specifications with descriptive names, such as `Closeable_MeaninglessClose`, `Map_UnsafeIterator`, `InputStream_ManipulateAfterClose`. Same report path and same status as the previous set.

The specification set is determined by the `specification_set` field in `ExperimentConfig`, which maps to a subdirectory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`. The `get_monitored_operations_config()` JIT method resolves the mapping:
- `"jca"` maps to `{mop_base_dir}/jca/`
- `"jca_android"` maps to `{mop_base_dir}/jca_android/`
- `"generic"` maps to `{mop_base_dir}/generic/`
- `"custom"` uses `custom_specs_dir` (MUST be explicitly provided)

`{mop_base_dir}/jca_android_bug_predicate/` has no entry: it exists in the tree and is deliberately unreachable by name.

Every set that carries corrections MUST be selectable by name. Reaching such a set through `"custom"` with a hand-written path is not acceptable, because a mistyped path silently selects the uncorrected instrument. The converse also holds and is why the archived set has no name: a set that must not be run in a new campaign is best given no value at all, rather than a value a reader might take for an offer.

When no `mop_specs_dir` is explicitly provided to `RVGeneratorConfig`, it defaults to the JCA specification set.

Specifications within a set MAY communicate through `Property` constants written and read via `ExecutionContext`, and where they do, those constants form a contract across specifications governed by `Requirement: Predicate Contract Between Specifications`, not a per-specification implementation detail. That contract binds `jca` and the archived `jca_android_bug_predicate`; `jca_android` is outside it by construction, because it writes and reads no `Property`.

#### Scenario: JCA specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`
- **AND** the directory MUST contain 23 `.mop` files

#### Scenario: The archived derived set is not selectable

- **WHEN** `ExperimentConfig.specification_set` is `"jca_android_bug_predicate"`
- **THEN** `ExperimentConfig.validate()` MUST raise `ValueError` listing `jca`, `jca_android`, `generic`, `custom`
- **AND** the directory `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate/` MUST nevertheless exist, holding the 23 `.mop` files of the derived set unchanged
- **AND** no mapping branch MUST resolve any accepted value to it

#### Scenario: JCA Android specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca_android"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`
- **AND** the directory MUST contain 21 `.mop` files and `codes.csv`
- **AND** `RandomStringPassword.mop` and `SecretKeySpec.mop` MUST NOT be among them
- **AND** `custom_specs_dir` MUST NOT be required

#### Scenario: The archived derived set keeps its own divergence record

- **WHEN** the diff between `jca/` and `jca_android_bug_predicate/` is taken
- **THEN** hunks outside allow-list content MUST be present, since gh101's repairs were confined to that set
- **AND** every such hunk MUST be named by an entry in `data/gh101/divergence_record.csv`, which the rename does not rewrite

#### Scenario: Successor set diverges from the frozen set

- **WHEN** the diff between `jca/` and `jca_android/` is taken after the repairs have landed
- **THEN** every hunk MUST be named by an entry in `data/jca_android/divergence_record.csv`
- **AND** every allow-list hunk MUST additionally be traceable to a `CONSTRAINTS` clause of `generated/api30/`, to a row of the alias table, or to a recorded MetaCrySL defect (INV-INS-127)
- **AND** the `jca/` directory MUST be byte-identical to commit `7e7acb69`

#### Scenario: Generic specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"generic"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/`

#### Scenario: Custom specification set with valid directory

- **WHEN** `ExperimentConfig.specification_set` is `"custom"` and `custom_specs_dir` points to a directory containing `.mop` files
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` set to `custom_specs_dir`
- **AND** the directory MUST be validated to contain at least one `.mop` file

#### Scenario: Custom specification set without directory

- **WHEN** `ExperimentConfig.specification_set` is `"custom"` and `custom_specs_dir` is `None`
- **THEN** `get_monitored_operations_config()` MUST raise a `ConfigurationError` with message indicating that `custom_specs_dir` is required

#### Scenario: Invalid specification set value

- **WHEN** `ExperimentConfig.specification_set` is set to a value not in the supported set
- **THEN** `ExperimentConfig.validate()` MUST raise a `ValueError` with message listing the valid specification sets
- **AND** the names `"jca_android_v2"` and `"jca_android_bug_predicate"` MUST be rejected like any other unknown value — the first is a working name the successor set never carried, the second names a directory that exists and is deliberately not offered

#### Scenario: Default specification set when using RVGeneratorConfig directly

- **WHEN** `RVGeneratorConfig` is created with only `rvsec_root` (no explicit `mop_specs_dir`)
- **THEN** `mop_specs_dir` MUST default to `{rvsec_root}/rvsec/rvsec-mop/src/main/resources/jca/`

### Requirement: The Java SE Specification Set Is Frozen

The `jca` specification set, together with the `CipherTransformationUtil` its `CipherSpec` delegates to, SHALL remain byte-identical to its state at commit `7e7acb69`. A specification set that has produced published measurements is an experimental instrument, and altering it retroactively invalidates the reproduction of every result computed with it.

Corrections to the platform-independent portion of a specification — an event binding, a pointcut signature, membership of an event in its own automaton, a handler, a report message, or an allow-list — SHALL therefore be applied to a set other than `jca`, even though the same defect is present in `jca`: the derived set under gh101, now archived as `jca_android_bug_predicate`, and the successor set `jca_android` under the legible-report programme. Each such correction SHALL be entered in that set's divergence record naming the hunk, the reason, and the task that introduced it. Divergence between the sets outside allow-lists is the expected outcome; divergence that is not recorded is not.

Two consequences SHALL be carried in the change's records rather than left to be inferred. The `jca` set knowingly retains its defects and the spurious reports they produce, so results measured under it are reproducible without being correct. And a difference in outcome between `jca` and any other set can no longer be attributed to the platform allow-list alone, because it may equally arise from a repair present in one set only; no measurement separates the two contributions after the fact. `jca_android` widens that gap deliberately — it changes allow-lists, messages, automata and the predicate regime at once — so every comparison against it MUST name which of those it is attributing the difference to, and the differential harness exists to make that attribution per trace rather than per campaign.

The freeze governs what the instrument **states** — the specifications and the transformation tables the frozen `CipherSpec` delegates to — and not the runtime it executes on. Additive changes to shared Java are admissible where the frozen set cannot observe them at all: a new `Property` constant that no `jca` specification references, or a new class that no `jca` specification imports, leaves the frozen set's generated monitor unchanged. The new transformation utility `jca_android/CipherSpec.mop` names is admissible on exactly this ground: it is a new class in `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` that neither `CipherTransformationUtil` nor `AndroidCipherTransformationUtil` is edited to accommodate, and that no `jca` specification imports. The alias utility of INV-INS-127 is admissible on the same ground and for the same reason.

A **repair to shared runtime code the frozen set does reference** is also admissible, under two conditions and not otherwise. The repair MUST apply identically to both sets — shared code MUST NOT branch on the active specification set, because that would place the frozen set's verdict under state set outside its own specification, which is the hazard INV-INS-112 exists to prevent. And its effect on the frozen set MUST be enumerated site by site in the change's records rather than assumed absent. A defect in the machinery is not made correct by having been present when a measurement was taken, and a rule forbidding its repair would forbid repairing the weaver as well. The legible-report programme makes three such repairs — the collector's escaping and null guard, the arity counter in the weaver, and the dedupe identity — and enumerates their effect on `jca` in its records; the arity counter changes no behaviour by construction (INV-INS-122), and the dedupe identity changes what `jca` reports and is declared as a count discontinuity, not hidden.

The distinction is between a correction of what counts as a misuse, which is confined to a non-frozen set, and a correction of the mechanism that decides it, which is not confinable and is therefore recorded.

#### Scenario: Correction reaches the frozen set

- **WHEN** a layer-2 correction is applied to a file under `jca/`, or to `CipherTransformationUtil.java`
- **THEN** the freeze check MUST fail against the base commit
- **AND** the correction MUST be moved to a non-frozen set, however clearly it repairs a real defect

#### Scenario: Correction does not land in the archived derived set

- **WHEN** a binding defect present in `jca` and in `jca_android_bug_predicate` is corrected
- **THEN** the correction MUST land in `jca_android`, never in the archived directory, which receives no repair from this contract
- **AND** the freeze check MUST pass and both `jca/` and `jca_android_bug_predicate/` MUST stay byte-unchanged
- **AND** both MUST retain the defect, recorded as knowingly retained

#### Scenario: Correction lands in the successor set

- **WHEN** a report message of `jca` is rewritten in `jca_android` only
- **THEN** the freeze check MUST pass
- **AND** `data/jca_android/divergence_record.csv` MUST gain an entry naming the hunk and the reason
- **AND** the `jca` set MUST keep emitting `unknown` at that site, recorded as knowingly retained

#### Scenario: Divergence appears without a record entry

- **WHEN** the two sets differ outside allow-list content in a hunk that no divergence-record entry names
- **THEN** the check MUST fail
- **AND** the hunk MUST either gain an entry with its reason or be reverted

#### Scenario: Shared Java gains a symbol the frozen set cannot observe

- **WHEN** `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` gains the transformation utility `jca_android/CipherSpec.mop` names, and no `jca` specification imports it
- **THEN** the freeze check MUST pass
- **AND** the monitor generated from the `jca` set MUST be unchanged, which is what makes the addition admissible
- **AND** `CipherTransformationUtil.java` and `AndroidCipherTransformationUtil.java` MUST both be byte-unchanged

#### Scenario: Shared runtime code the frozen set references is repaired

- **WHEN** a defect is corrected in `rvsec-core` code that specifications of both sets call
- **THEN** the repair MUST apply identically to both sets, with no branch on the active specification set
- **AND** the sites at which the frozen set's behaviour changes MUST be enumerated in the change's records
- **AND** the freeze check passing MUST NOT be reported as evidence that the frozen set's behaviour is unchanged

### Requirement: Derivation Provenance of the Android Specification Set

The archived set `rvsec-mop/src/main/resources/jca_android_bug_predicate/` — the derived Android set gh101 built, renamed and no longer selectable — is a derivation of the `jca` set against generated CrySL rules for a declared Android API level, and that derivation altered allow-list content and nothing else: the platform-dependent portion of a CrySL rule is the membership constraint, while `ORDER`, `REQUIRES`, `ENSURES` and `NEGATES` describe API semantics and do not vary with API level. This requirement now describes that archived set and only it. It is frozen with the set: the 23 files are byte-identical to the pre-rename `jca_android` at `pre-rename-head`, and no task of this contract or any later one applies a derivation run or a repair to them.

Each specification of the archived set carries a conformance verdict against the generated rules — **anchored** (a named generated rule contradicted the `jca` allow-list and the allow-list was changed to follow it), **uncontradicted** (the generated rule was checked and does not contradict the inherited allow-list), or **no anchor** (no generated rule corresponds, with the reason stated) — recorded in `data/gh101/` (INV-INS-113). That vocabulary belongs to the archived set. The successor set `jca_android` is not a derivation of `jca` in this sense and does not carry these verdicts: it is governed by `Requirement: Successor Specification Set `jca_android``, `Requirement: Allow-List Conformance to the Generated api30 Rules` and `Requirement: The Successor Set Carries No Predicate` of this delta, its allow-lists are literal transcriptions checked by G-CONF, and its record is `data/jca_android/conformance_record.csv` (INV-INS-125), whose vocabulary is transcription, recorded divergence and `deferred-constant`.

The archived set's profile models **availability, not recommendation**, and a report comparing violation counts across `jca` and `jca_android_bug_predicate` MUST carry that caveat. The successor set targets one declared platform, on which the split does not arise (INV-INS-125); a comparison that includes `jca_android` MUST carry the caveat that the three sets answer to different oracles.

#### Scenario: The archived set is byte-identical to its pre-rename state

- **WHEN** `git diff --stat --find-renames pre-rename-head -- rvsec-mop/src/main/resources/jca_android rvsec-mop/src/main/resources/jca_android_bug_predicate` is taken after the rename
- **THEN** it MUST show 23 renames with zero insertions and zero deletions
- **AND** `data/gh101/divergence_record.csv` and `data/gh101/conformance_record.csv` MUST be unchanged, still describing the archived set under its old name

#### Scenario: A derivation or repair reaches the archived set

- **WHEN** a task would change an allow-list, an event, a binding, a pointcut, an `fsm` row, a handler or an `ExecutionContext` call in a file under `jca_android_bug_predicate/`
- **THEN** the change MUST be rejected: the archived set receives no derivation run and no repair
- **AND** the correction, if it is one, MUST land in `jca_android` under `Requirement: The Java SE Specification Set Is Frozen`

#### Scenario: A verdict of the archived set is not carried into the successor

- **WHEN** `data/jca_android/conformance_record.csv` is checked for a `MessageDigestSpec` row
- **THEN** the row MUST name `generated/api30/MessageDigest.cryptsl` as the transcribed rule and record the lost detection (5,892 rows) as a transcription
- **AND** it MUST NOT carry the verdict `anchored`, `uncontradicted` or `no anchor`, which describe the archived set's derivation and not a literal transcription

### Requirement: Cipher Transformation Tables of the Derived Set

The `Cipher` transformation tables consulted by the archived set `jca_android_bug_predicate` — the admissible algorithms, their modes, and per mode the admissible paddings — originate in the generated CrySL rule for its declared API level and are reached by `jca_android_bug_predicate/CipherSpec.mop` naming its own utility, `AndroidCipherTransformationUtil` (`rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`), rather than by any runtime selection over a shared one. This requirement now describes that archived pair and only it: the utility belongs to the archived set, is frozen with it, and SHALL stay byte-unchanged, exactly as `CipherTransformationUtil` stays byte-unchanged for the frozen `jca`.

`CipherSpec` is the only specification of any JCA set with no allow-list of its own: it delegates to `isValid(transformation)` in shared Java, where the tables are method locals. Selection by the *specification* rather than by the *runtime* is what keeps each set's verdict its own — a shared utility parameterised by the active set would place the `jca` verdict under the control of state set elsewhere (INV-INS-112) — and the successor set applies the same pattern a third time: `jca_android/CipherSpec.mop` names a **new** class in the same package, transcribed from `generated/api30/Cipher.cryptsl` and checked by G-CONF, under `Requirement: Allow-List Conformance to the Generated api30 Rules`. Three sets, three utilities, none selected at runtime.

#### Scenario: The archived utility is unchanged

- **WHEN** the freeze check runs after any task of this contract
- **THEN** `AndroidCipherTransformationUtil.java` and `CipherTransformationUtil.java` MUST both be byte-identical to `pre-rename-head`
- **AND** `jca_android_bug_predicate/CipherSpec.mop` MUST still name `AndroidCipherTransformationUtil`, and no `.mop` of `jca_android` MUST name it

#### Scenario: Java SE set behaviour is unchanged

- **WHEN** the `jca` set is active
- **THEN** `isValid` MUST return the same verdict it returns today for every transformation
- **AND** that MUST hold because the class it calls was not modified, not because a test asserts it

#### Scenario: A shared table selected at runtime is proposed

- **WHEN** an implementation would give two or three of the sets one utility whose tables are chosen by the active specification set
- **THEN** it MUST be rejected under INV-INS-112
- **AND** the reason MUST be recorded as the frozen set's verdict depending on state set outside its own specification
