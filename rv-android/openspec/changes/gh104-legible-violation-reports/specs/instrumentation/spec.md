## Purpose

A violation report is the only thing the runtime-verification pipeline leaves behind about a misuse: one logcat line per deduplicated `ErrorDescription`, later one row of `errors.csv`. In the published dataset 72.93 % of those rows carry the literal `unknown` as their message, because 25 of the 51 report sites of the `jca` set call the three-argument `ErrorDescription` constructor, whose fourth argument defaults to `"unknown"` (`rvsec-core/.../eh/ErrorDescription.java:34-36`); a further 8,843 rows read `but found .` because 16 of the 17 active `but found` sites interpolate a monitor field that is still empty when the event fires. The `@fail` handler that produces every `InvalidSequenceOfMethodCalls` names neither the event that triggered it nor the state it came from, so the record cannot be attributed to an event even when the specification is read next to it.

This delta gives the instrumentation pipeline a message contract and the instruments to keep it: a successor specification set `jca_v2`, derived byte-identical from the frozen `jca` and the only place specification-side repairs land; a versioned `key=value` envelope every report site emits, with the offending event name recorded by the event body itself; a weaver rule so a merged wrapper fires only advices whose positional `args()` arity matches the call it wraps; the collector's line escaped and null-guarded; the orphan-event and structural checks over the generated monitor as executable gates for any set; and a differential harness that replays the same traces through the monitors generated before and after a repair, because two earlier changes (gh100 D-B1, gh101 Groups 3/3b) each moved a defect instead of removing it while every static gate stayed green.

The frozen `jca` set stays frozen; `jca_android` is not touched. Everything the successor set differs from `jca` by is a recorded hunk, so a reader can still tell platform allow-list from repair. The `generic` and `generic_new` sets are outside this contract: none of their 145 files passes through `ErrorCollector`, and none has ever run in a campaign.

## Data Contracts

### Input
- `specification_set: str` — `"jca"`, `"jca_android"`, `"jca_v2"`, `"generic"` or `"custom"` (`ExperimentConfig`, `rv_experiment/config.py`); resolves to a directory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`.
- `MultiSpec_1RuntimeMonitor.java` — the generated monitor of a set (`results/<run>/monitors/`), read by the structural gates and the harness.
- `MultiSpec_1MonitorAspect.json` — the advice descriptor the dexlib2 weaver consumes (`WrapperEmitter.generate`).
- `data/jca_v2/divergence_record.csv`, `data/jca_v2/conformance_record.csv`, `data/jca_v2/gate_allowlist.csv`, `rvsec-mop/src/main/resources/jca_v2/codes.csv` — the records the gates read.

### Output
- One logcat line per report: `RVSEC: spec,classQualifiedName,className,methodName,location,errorType,<envelope>` (logcat `ErrorCollector.java:36-40`); the seventh field is the envelope of `Requirement: Violation Report Message Envelope`.
- `instrument_results.json` counter `advicesExcludedByArity` (per APK, `BatchRunner` counts map).
- Harness evidence: `evidence/harness/<spec>-<task>.md` per repair task, before/after trace verdicts.

### Side-Effects
- **[Filesystem]**: `rvsec-mop/src/main/resources/jca_v2/` created; `data/jca_v2/` created; `rvsec-mop/src/test/` created as the JVM harness home.
- **[Generation]**: the structural gates and the harness generate monitors in a scratch directory (`RVSEC_HOME` required); generation is not parallelisable and `TMPDIR` MUST be off tmpfs (`CipherSpec` at 17 events needs 3.3 GB).

### Error
- `pytest` failure — a gate violation without an allowlist entry; a freeze-check failure on `jca`; a `jca_v2`/`jca` hunk without a divergence-record entry; a report site with three arguments; an event body without its bookkeeping line.
- `IllegalStateException` (weaver) — unchanged guard on wrapper registry collisions; arity exclusion is a count, never an exception.

## Invariants

- **INV-INS-09** (restated, replacing the entry of the same number): Specification sets MUST NOT be mixed within a single generation or instrumentation run. The `specification_set` field in `ExperimentConfig` MUST be one of `"jca"`, `"jca_android"`, `"jca_v2"`, `"generic"`, or `"custom"`. If `"custom"` is specified, `custom_specs_dir` MUST be provided; each of the other four resolves to its directory from the set name alone, with no path supplied by the caller. The enumeration is closed: a value outside it is rejected by name, so a stale or mistyped `custom` path can never silently select an uncorrected instrument.
- **INV-INS-118**: `jca_v2` MUST be derived from the frozen `jca` and differ from it only by hunks entered in `data/jca_v2/divergence_record.csv` with a reason and the task that introduced them. The freeze of `jca` (INV-INS-109) is unaffected: no task of this contract edits `jca/` or `CipherTransformationUtil.java`, and the existing freeze gate MUST stay green. An unrecorded hunk between the two sets is a defect.
- **INV-INS-119**: Every `new ErrorDescription(` in `jca_v2` MUST use the four-argument constructor, and the fourth argument MUST be a v1 envelope. No report emitted from `jca_v2` may carry the message `unknown` or an observed value that is empty because a monitor field was interpolated before any event wrote it: a `but found` message MUST interpolate the argument bound by the event that reports it.
- **INV-INS-120**: Every event body in `jca_v2` MUST begin with `lastEventName = "<event>";` where `<event>` is the event's declared name, and every `@fail` handler MUST compose its envelope's `ev=` from that field before `__RESET`. Two events of one specification MUST NOT share a name (the generated monitor merges their transition rows silently — `GCMParameterSpecSpec` today).
- **INV-INS-121**: A report message MUST agree with the check that guards it: every numeric literal in the message equals the literal of the guarding `condition()`; the `ErrorType` matches what the condition tests (a constraint on an argument is `UnsatisfiedConstraint`, an algorithm outside the allow-list is `UnsafeAlgorithm`); an expected list in a message is the file's allow-list, joined, never a hand-written subset or the literal `...`.
- **INV-INS-122**: When `WrapperEmitter` groups advices into one merged wrapper for a concrete call, an advice MUST enter the group only if its positional `args()` arity is compatible with that call: an advice with no `args()` clause is never filtered (absence means "no positional constraint"); the arity is read from `ArgsPC.types()`, so a trailing `..` means "at least"; the filter runs in the grouping loop, where the concrete overload's parameter count is known. Advices excluded by arity MUST be counted into the results JSON as `advicesExcludedByArity`; none may disappear silently.
- **INV-INS-123**: For any specification set, the structural gates over the generated monitor MUST run as pytest and MUST fail on a violation not named in `data/<set>/gate_allowlist.csv` with a reason: G-2 (an event with a transition row to `fail` from every state — INV-INS-110), G-2a (an event that never changes state: `∀s δ(s,e)=s`), G-2b′ (an event redundant at the start state: `δ(q0,e)=q0`), G-2c (a state unreachable from `q0` or from which no accepting state is reachable), G-2d (the highest-index state is not the `fail` category), G-6′ (the number of `Prop_N_event_*` methods differs from the number of `Prop_N_transition_*` rows). A green gate over a set with a known defect is a bug in the gate; the frozen `jca`, where the answers are known (18, 1, 8, 1, 2, 1), is the baseline every extension is run against first.
- **INV-INS-124**: No repair task on an automaton, a message or a wrapper rule of this contract MAY close without the differential harness having replayed the same traces through the monitor generated before and through the monitor generated after the repair, with the per-trace verdicts of both committed as evidence. A repair that changes which call is accused, without changing whether the trace is accused, is a moved defect and MUST be recorded as such, not as a fix.
- **INV-INS-125**: The oracle of `jca_v2` is chosen per clause family and recorded per specification in `data/jca_v2/conformance_record.csv`: MetaCrySL api30 for availability (Cipher catalogue, keystore types), CrySL 1.5.2 for recommendation (digest algorithms, TLS protocols). A specification MUST NOT mix the two anchors without the record naming which clause follows which, and any report comparing counts across `jca`, `jca_android` and `jca_v2` MUST carry that caveat.
- **INV-INS-126**: The dedupe identity of a violation report (`ErrorSummary.equals`/`hashCode`, `rvsec-core`) MUST include the report's `code` and `event` in addition to `spec`, `error`, `class`, `method` and `location`. The message free text stays outside it. Because every dedupe count published before this contract used the five-field identity, the count discontinuity MUST be measured on the E3 trial and declared non-zero before the identity change is integrated.

## ADDED Requirements

### Requirement: Successor Specification Set `jca_v2`

The system SHALL provide a fifth specification set, `jca_v2`, at `rvsec-mop/src/main/resources/jca_v2/`, created byte-identical from the frozen `jca` and selectable by name. It exists because the two other JCA sets are unavailable as targets: `jca` is frozen (it produced the published measurements), and `jca_android` was judged NOT READY by the 2026-08-08 audit and is not touched by this contract. Every specification-side repair of this contract — messages, automata, pointcuts, predicates — lands in `jca_v2` alone.

The set SHALL carry the same three records the derived set carries: a divergence record naming every hunk by which it differs from `jca` (INV-INS-118), a conformance record naming the oracle anchor per specification and clause family (INV-INS-125), and a gate allowlist for structural-gate exceptions with reasons (INV-INS-123). It SHALL also carry `codes.csv`, the table of failure codes its envelopes emit (`Requirement: Violation Report Message Envelope`).

The set SHALL be registered at every site that enumerates specification sets: `valid_spec_sets` and the directory mapping in `rv_experiment/config.py`, the `click.Choice` on `--specification-set` in `rv_experiment/__main__.py`, INV-INS-09, INV-EXP-03 clause (f), and the mapping paragraph of `Just-in-Time Sub-Module Configuration`. A closed enumeration left with four values states that the fifth does not exist.

#### Scenario: `jca_v2` is selected by name

- **WHEN** `ExperimentConfig.specification_set` is `"jca_v2"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_v2/`
- **AND** the directory MUST contain 23 `.mop` files and `codes.csv`
- **AND** `custom_specs_dir` MUST NOT be required

#### Scenario: the seed is byte-identical

- **WHEN** the set is first created
- **THEN** `diff -r jca/ jca_v2/` MUST be empty except for `codes.csv`
- **AND** the freeze gate `tests/parity/test_gh101_specset_gates.py::test_frozen_paths_byte_identical_to_base_commit` MUST still pass

#### Scenario: a repair lands in `jca_v2`

- **WHEN** a task edits `jca_v2/TrustManagerFactorySpec.mop`
- **THEN** `data/jca_v2/divergence_record.csv` MUST gain one entry per hunk naming the reason and the task
- **AND** the gate that recomputes the hunks between `jca/` and `jca_v2/` MUST report every hunk as recorded
- **AND** `jca/TrustManagerFactorySpec.mop` MUST be byte-identical to commit `7e7acb69`

### Requirement: Violation Report Message Envelope

Every report site in `jca_v2` SHALL call the four-argument `ErrorDescription` constructor, and the fourth argument SHALL be a v1 envelope:

```
v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<free text>'
```

`code` is the failure identifier of the site, one per `@fail` (`<SPEC>-ORDER-00`) and one per value site, listed in `jca_v2/codes.csv` and cross-checked by the message-property gate; `ev` is the name of the event that fired, taken from the bookkeeping field the event body writes (INV-INS-120); `obj` is the simple class of the monitored object; `val` and `exp` carry the observed and the expected value, both quoted with `'`, a literal `'` escaped as `\'`; `msg` is the human sentence. There is no `st=` field: state indices are assigned after minimisation and do not follow declaration order, so a spec-side state name would be silently wrong. Commas are allowed inside values (27 % of today's messages contain them and every consumer rejoins field 7); `\n` and `:::` are not, because the first splits the logcat line and the second is the separator of `unique_msg`. Truncation is the consumer's problem to detect: the producer bounds `val` to 512 characters and the parser treats an unclosed quote as a truncated record.

The 17 sites whose message reads `but found` SHALL interpolate the argument bound by the event that reports (`alg`, `transformation`, `type`, `protocol`), not the monitor field (`currentAlgorithmInstance`, `currentTransformation`, `currentKSType`, `currentProtocol`, `algorithm`) — the field is empty until an instantiation event writes it in the same parameter slice, which is the mechanism behind the 8,843 empty labels.

Message text SHALL agree with the check that guards it (INV-INS-121). The census this contract starts from — measured on the frozen `jca`, reproduced in `jca_v2` by construction — is: `PBEKeySpecSpec.mop:50` and `PBEParameterSpecSpec.mop:50` say `1000` where the condition tests `10000`; `PBEParameterSpecSpec.mop:49` reports `UnsafeAlgorithm` for an iteration-count constraint; `PBEKeySpecSpec.mop:24,30` report `InvalidSequenceOfMethodCalls` for a forbidden constructor; `SecretKeySpecSpec.mop:48,55` report `UnsatisfiedConstraint` for half an algorithm test; `MessageDigestSpec.mop:70,92` list three algorithms where the allow-list at `:16` has six; `CipherSpec.mop:61,76` carry the literal `...`; `KeyGeneratorSpec.mop:64` and `KeyStoreSpec.mop:68` lack the space after `expecting one of`; `MacSpec.mop:62` lacks the verb; `SecretKeySpecSpec.mop:49` says `keyMaterial.length is not randomized` where `:46` tests the array; `KeyPairGeneratorSpec.mop:71-72` is unreachable because `validate()` returns `false` for every algorithm outside its `switch`; leading spaces at `MacSpec.mop:50`, `KeyManagerFactorySpec.mop:55`, `KeyPairGeneratorSpec.mop:72`, `SecretKeySpecSpec.mop:49,56`; and `ErrorDescription.toString()` (`:143`) prefixes `expecting`, so every message that itself starts with `expecting` renders twice. Correcting these is a precondition of the envelope, not a consequence: an envelope around a lying sentence certifies the lie with a `code`.

#### Scenario: a `@fail` handler names its event

- **WHEN** `jca_v2/TrustManagerFactorySpec` reaches `fail` on event `init` after `g1` and `g2` were never seen
- **THEN** the report's message MUST be `v=1 code=TMF-ORDER-00 ev=init obj=TrustManagerFactory val='' exp='' msg='init() before getInstance()'` (free text as authored)
- **AND** the record's `error_type` MUST be `InvalidSequenceOfMethodCalls`
- **AND** the envelope MUST be composed before `__RESET` runs

#### Scenario: a value site interpolates the argument

- **WHEN** `jca_v2/TrustManagerFactorySpec.g3` fires for `getInstance("X509")`
- **THEN** the message MUST be `v=1 code=TMF-ALG-01 ev=g3 obj=TrustManagerFactory val='X509' exp='PKIX,SunX509' msg='expecting one of PKIX,SunX509 but found X509'`
- **AND** `val` MUST come from the bound argument `alg`, never from `currentAlgorithmInstance`

#### Scenario: no three-argument site remains

- **WHEN** the message-property gate scans `jca_v2/*.mop`
- **THEN** it MUST find zero `new ErrorDescription(` calls with three arguments (the frozen `jca` has 25: 21 `@fail` blocks, `IvParameterSpec.mop:48,55`, `PBEKeySpecSpec.mop:24,30`)
- **AND** every `code` it finds MUST exist in `codes.csv`, and every `codes.csv` row MUST be emitted by exactly one site

#### Scenario: a numeric literal disagrees with its guard

- **WHEN** a message says `>= 1000` and the `condition()` guarding it tests `< 10000`
- **THEN** the message-property gate MUST fail naming the file, the line and the two literals

### Requirement: Event-Name Bookkeeping in Specification Bodies

Every event body in `jca_v2` SHALL begin with `lastEventName = "<event>";`, where the string equals the event's declared name, and the specification's declarations block SHALL declare `String lastEventName = "";`. The mechanism relies on a property of the generator that is verified on 134/134 (`jca`) and 140/140 (`jca_android`) event methods of the generated monitors: the event body written in the `.mop` is inlined **before** the transition, and an event that fails its `condition()` returns without transitioning and therefore cannot be the event that reaches `fail`; the event that reaches `fail` is one that passed its guard and wrote its name.

Two residues are declared rather than hidden. Where a `@fail` handler does not call `__RESET`, the flags survive and the next event re-runs the handler with the previous name — `KeyPairGeneratorSpec` is the only such handler in the set and it gains `__RESET`. Where two events of one specification can pass their guards on the same call, dispatch order decides the name — `KeyGeneratorSpec.g3` (`:47`, testing the field instead of the argument) is that case and is repaired in the automata group.

#### Scenario: every body carries its name

- **WHEN** the `.mop` lint scans `jca_v2/*.mop`
- **THEN** for every `event <name> ... {` the first statement of the body MUST be `lastEventName = "<name>";`
- **AND** a body whose first statement names a different event MUST fail the lint

#### Scenario: two events share a name

- **WHEN** a specification declares `event c1` twice (as `GCMParameterSpecSpec.mop:23,34` does today)
- **THEN** the lint MUST fail, because the generated monitor would carry two `Prop_1_event_c1` methods and one `c1` transition row (gate G-6′)

### Requirement: Wrapper Grouping Honours `args()` Arity

When `WrapperEmitter` groups the advices bound to one concrete call into a single merged wrapper (`WrapperEmitter.java:246-274`, decision D-B1 of gh100), it SHALL admit an advice only if the advice's positional `args()` arity is compatible with the call's parameter count, under three clauses (INV-INS-122): an advice with no `args()` clause is never filtered; the arity is the length of `ArgsPC.types()`, with a trailing `..` meaning "at least this many" (`ArgsPC.names()` drops the `..` and would make `args(transformation, ..)` look like fixed arity 1); the filter runs inside the grouping loop, the only place where the advice and the concrete overload coexist. Today `getInstance(String)` fires the two-argument advice's monitor call because the group is keyed on the call alone; the rule the lineage first wrote — drop any advice whose `args` length differs from the call's — would have dropped the 16 `after` advices that have parameters and no `args()` (`SSLContextSpec.init` alone accounts for 1,466 legible rows of the E3 trial).

Excluded advices SHALL be counted per APK as `advicesExcludedByArity` and reach `instrument_results.json` through `BatchRunner`'s counts map, beside `wrappersGenerated`. `before` advices bypass wrappers (`WrapperEmitter.java:161-163`) and are outside this rule; the binding-form check in `PointcutMatcher` is recorded as future work.

#### Scenario: an advice with `args(a, *)` does not enter the one-argument wrapper

- **WHEN** `TrustManagerFactory.getInstance(String)` is wrapped and the descriptor carries `g1` with `args(alg)` and an advice with `args(alg, provider)`
- **THEN** the wrapper for the one-argument overload MUST fire `g1` only
- **AND** `advicesExcludedByArity` MUST be 1 for that APK

#### Scenario: the sixteen no-`args()` advices survive

- **WHEN** the frozen `jca` descriptor (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json`) is grouped
- **THEN** every one of the 13 wrapper-path `after` advices with parameters and no `args()` (`CipherOutputStreamSpec_w1`, `CipherSpec_wkb1`, `CipherSpec_f2`, `KeyStoreSpec_gk1`, `MacSpec_update`, `MacSpec_f1`, `MessageDigestSpec_update`, `MessageDigestSpec_d2`, `SecureRandomSpec_setSeed1`, `SecureRandomSpec_genSeed`, `SecureRandomSpec_ints`, `SSLContextSpec_init`, `SSLContextSpec_engine`) MUST remain in its wrapper
- **AND** the three constructor advices of the sixteen (`CipherInputStreamSpec_c1`, `CipherOutputStreamSpec_c1`, `HMACParameterSpecSpec_c`) never reach the wrapper path and are unaffected

#### Scenario: trailing `..` is honoured

- **WHEN** an advice declares `args(transformation, ..)` and the concrete call has two parameters
- **THEN** the advice MUST enter the group (arity ≥ 1)

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

The orphan-event check (`scripts/gh101_monitor_transition_check.py`, G-2, INV-INS-110) SHALL run as a pytest parametrised by set, together with the structural companions computable on the same transition tables (INV-INS-123): G-2a inertia, G-2b′ redundancy at `q0`, G-2c dead states, G-2d sink is not `fail`, G-6′ event-name injectivity. Each gate SHALL read the generated monitor of the set — both `AbstractAtomicMonitor` and `AbstractSynchronizedMonitor` shapes — and SHALL fail on any hit not named in `data/<set>/gate_allowlist.csv` with a reason. On the frozen `jca` the expected hits are 18 (G-2, ten specifications), 1 (G-2a, `SecretKeySpec.e1`), 8 (G-2b′), 1 (G-2c), 2 (G-2d, `SecretKeySpec` and `RandomStringPasswordSpec`, which have no `fail` category), 1 (G-6′, `GCMParameterSpecSpec`); a gate that reports fewer on `jca` is wrong.

A `.mop` lint SHALL run before generation and fail closed on: an ERE or FSM symbol not declared as an event (`GCMParameterSpecSpec.mop:48` references `c2`); two events with one name; unbalanced parentheses (`SecretKeySpecSpec.mop:27-30`); a body without its bookkeeping line (INV-INS-120); a report site with three arguments (INV-INS-119). The message-property gate SHALL enforce INV-INS-121 and the `codes.csv` cross-check.

The gate the lineage proposed as G-2b ("the out-alphabet of the unsafe state contains the out-alphabet of the safe state") is NOT adopted: minimisation merges the unsafe state into `start` precisely when the alphabets are equal, so the gate is vacuous where it should bite; and the absorbing-state repair it implies was considered and rejected in gh101 D-S9 (two repair philosophies in one set; a false positive traded for a false negative). The residue it targets — a violating branch does not absorb the calls that follow — is recorded in `data/gh101/frozen_set_debt.md`, not gated.

#### Scenario: the gates reproduce the known baseline

- **WHEN** the gate suite runs on `results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`
- **THEN** it MUST report exactly 18 / 1 / 8 / 1 / 2 / 1 hits for G-2 / G-2a / G-2b′ / G-2c / G-2d / G-6′
- **AND** with `data/jca/gate_allowlist.csv` naming them, the suite MUST pass

#### Scenario: a repair leaves an orphan

- **WHEN** an event of `jca_v2` is bound but absent from its `fsm`/`ere`
- **THEN** G-2 MUST fail naming the specification and the event

#### Scenario: an undeclared symbol

- **WHEN** a `.mop` `ere` names `c2` and no `event c2` exists
- **THEN** the lint MUST fail before any monitor is generated (today the generator drops the symbol silently)

### Requirement: Differential Harness for Specification Repairs

The system SHALL provide a harness (`scripts/gh104_diff_harness.py` + a JVM trace runner under `rvsec-mop/src/test/`) that, given two snapshots of a specification set and a file of traces per specification, generates the monitor of each snapshot in scratch and replays every trace through both, reporting per trace and per snapshot: accused or not, at which event, with which envelope. It exists because static gates measure the artefact and not its behaviour: gh100's wrapper merge removed 12 silently discarded wrappers and created advices of incompatible arity firing at the same site (`wrappersGenerated 96→84` was reported as success); gh101's Group 3/3b removed 18 all-`fail` rows and moved the accusation to the next call. Neither was visible to a gate that counts rows.

No repair task of the automata, message or wrapper groups SHALL close without its harness output committed (INV-INS-124). The traces SHALL include, for every specification, at least one legitimate sequence, one sequence per authored violating branch, and the separating traces the audit recorded. Trace replay runs on the JVM, not on a device; device validation is a separate task that uses `rv-experiment run` and is never performed by hand.

#### Scenario: a repair moves the accusation

- **WHEN** a trace `getInstance("X509"); init(ks)` is replayed through `TrustManagerFactorySpec` before and after an orphan repair
- **THEN** the harness MUST report the accusation at `getInstance` before and at `init` after
- **AND** the task record MUST classify the result as a moved defect, with the residue named

#### Scenario: a repair removes the report

- **WHEN** a legitimate trace `getInstance("PKIX"); init(ks); getTrustManagers()` is replayed
- **THEN** both snapshots MUST report no accusation
- **AND** any snapshot that accuses it MUST fail the task

### Requirement: Predicate Failure Reporting

`ErrorType` (`rvsec-core/.../eh/ErrorType.java`) SHALL gain `RequiredPredicate` (a `REQUIRES` clause not satisfied: the object was not produced by a monitored sequence) and `ForbiddenMethod` (a `FORBIDDEN` call), each with a `code` prefix (`REQ`, `FORB`) in `codes.csv`. In `jca_v2`, a predicate read SHALL live in the event body and report, not in `condition()`, where a failed requirement makes the event vanish silently and the automaton go to `fail` from the wrong cause; the automaton is co-edited so the moved read creates no orphan (G-2 stays green).

The predicate store `ExecutionContext` stays keyed by `equals`: commit `e204e2a4` reverted the identity keying that gh101 D-S10 introduced, and gh101's records (`data/gh101/README.md:308-317`, tasks 4b.1–4b.4) still describe the reverted state; this contract records that and does not re-key. Producers missing from the set (`SecretKeyFactory`, `*ParameterSpec`) SHALL be added as specifications or recorded in `data/jca_v2/predicate_omissions.csv` as unclosable with the CrySL reason, exactly as `data/gh101/predicate_omissions.csv` does (INV-INS-111).

#### Scenario: a REQUIRES read fails in the body

- **WHEN** `Cipher.init(mode, key)` fires with a `key` no monitored `KeyGenerator` produced
- **THEN** the report MUST carry `error_type=RequiredPredicate` and `code=CIP-REQ-01`
- **AND** the event MUST still transition, so no `InvalidSequenceOfMethodCalls` accompanies it

#### Scenario: a written constant without a reader

- **WHEN** the predicate pairing gate finds a `Property` written and never read
- **THEN** it MUST fail unless `data/jca_v2/predicate_omissions.csv` names the constant with its reason

### Requirement: Dedupe Identity of a Violation Report

`ErrorSummary.equals` and `hashCode` (`rvsec-core/.../eh/ErrorSummary.java:73-120`) SHALL compare `(spec, error, classQualifiedName, methodName, location, code, event)`; the message free text stays outside (INV-INS-126). Today the identity is the first five, and every specification has at most one `@fail`, so a `code` alone would be a function of `spec` and would refine nothing; it is `event` that separates the causes the record conflates. `ErrorDescriptionTest.hashCodeMatchesEquals` SHALL be rewritten to fix the seven fields.

The change is device-side (it needs re-instrumentation) and creates two eras of every dedupe count. Before it is integrated, the count discontinuity SHALL be measured on the E3 trial (`experimento-comp162`, 19,664 rows, 6,344 five-field identities today) by recomputing identities with `event` taken from the envelope, and declared in the change's records; it MUST be non-zero, otherwise the identity change is a no-op and MUST NOT land.

#### Scenario: two events, one site

- **WHEN** `KeyManagerFactorySpec` reports `InvalidSequenceOfMethodCalls` at `TlsUtil.newKeyManager:191` once from `ev=init` and once from `ev=gkm1`
- **THEN** the collector MUST emit two lines
- **AND** the five-field identity would have emitted one

#### Scenario: the discontinuity is measured

- **WHEN** the E3 trial's identities are recomputed with `event`
- **THEN** the number of identities MUST be recorded next to 6,344, with the definition of the recomputation
- **AND** if the two numbers are equal the identity change MUST NOT be integrated

## MODIFIED Requirements

### Requirement: Specification Set Support (FR03)

The system MUST support multiple, independent specification sets for different API monitoring domains. Each specification set represents a collection of `.mop` files targeting a specific category of API usage patterns. The system MUST ensure that specification sets are never mixed within a single experiment run.

Five predefined specification sets are supported:

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

2. **JCA Android** -- the same 23 specifications, derived against generated CrySL rules for a declared Android API level. The derivation altered allow-list content only. Repairs to the platform-independent portion landed here under gh101, and each resulting divergence is entered in the divergence record with its reason (INV-INS-109). Its `CipherSpec` names its own transformation utility, whose tables come from the generated `Cipher` rule. The set was judged NOT READY by the 2026-08-08 audit and receives no further repair from this contract.

3. **JCA v2** -- the successor set: the same 23 specifications, seeded byte-identical from the frozen `jca` and carrying every specification-side repair of the legible-report programme — message envelopes, event-name bookkeeping, automaton and pointcut repairs, predicate reporting. Its oracle is chosen per clause family (INV-INS-125); every hunk by which it differs from `jca` is entered in `data/jca_v2/divergence_record.csv` (INV-INS-118). It carries `codes.csv`, the table of failure codes its envelopes emit.

4. **Generic (FSM)** -- 118 specifications from the JavaMOP specification database, detecting general API pattern violations such as Iterator hasNext/next ordering, stream resource management, and collection modification during iteration. This set reports through `Log.v` directly, not through `ErrorCollector`, and has never run in a campaign; its report contract is outside the legible-report programme and recorded as debt.

5. **Generic (new)** -- 27 curated specifications with descriptive names, such as `Closeable_MeaninglessClose`, `Map_UnsafeIterator`, `InputStream_ManipulateAfterClose`. Same report path and same status as the previous set.

The specification set is determined by the `specification_set` field in `ExperimentConfig`, which maps to a subdirectory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`. The `get_monitored_operations_config()` JIT method resolves the mapping:
- `"jca"` maps to `{mop_base_dir}/jca/`
- `"jca_android"` maps to `{mop_base_dir}/jca_android/`
- `"jca_v2"` maps to `{mop_base_dir}/jca_v2/`
- `"generic"` maps to `{mop_base_dir}/generic/`
- `"custom"` uses `custom_specs_dir` (MUST be explicitly provided)

Every named set MUST be selectable by name. Reaching a set through `"custom"` with a hand-written path is not acceptable for a set that carries corrections, because a mistyped path silently selects the uncorrected instrument.

When no `mop_specs_dir` is explicitly provided to `RVGeneratorConfig`, it defaults to the JCA specification set.

Specifications within a set communicate through `Property` constants written and read via `ExecutionContext`. Those constants form a contract across specifications, governed by `Requirement: Predicate Contract Between Specifications`, not a per-specification implementation detail.

#### Scenario: JCA specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`
- **AND** the directory MUST contain 23 `.mop` files

#### Scenario: JCA Android specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca_android"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`
- **AND** the directory MUST contain 23 `.mop` files and no `.aj` file
- **AND** `custom_specs_dir` MUST NOT be required

#### Scenario: JCA v2 specification set selection

- **WHEN** `ExperimentConfig.specification_set` is `"jca_v2"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_v2/`
- **AND** the directory MUST contain 23 `.mop` files and `codes.csv`
- **AND** `custom_specs_dir` MUST NOT be required

#### Scenario: Derived set diverges from the frozen set

- **WHEN** the diff between the two set directories is taken after the corrections have landed
- **THEN** hunks outside allow-list content MUST be present, since the repairs are confined to the derived set
- **AND** every such hunk MUST be named by an entry in the divergence record

#### Scenario: Successor set diverges from the frozen set

- **WHEN** the diff between `jca/` and `jca_v2/` is taken after the repairs have landed
- **THEN** every hunk MUST be named by an entry in `data/jca_v2/divergence_record.csv`
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

#### Scenario: Default specification set when using RVGeneratorConfig directly

- **WHEN** `RVGeneratorConfig` is created with only `rvsec_root` (no explicit `mop_specs_dir`)
- **THEN** `mop_specs_dir` MUST default to `{rvsec_root}/rvsec/rvsec-mop/src/main/resources/jca/`

### Requirement: The Java SE Specification Set Is Frozen

The `jca` specification set, together with the `CipherTransformationUtil` its `CipherSpec` delegates to, SHALL remain byte-identical to its state at commit `7e7acb69`. A specification set that has produced published measurements is an experimental instrument, and altering it retroactively invalidates the reproduction of every result computed with it.

Corrections to the platform-independent portion of a specification — an event binding, a pointcut signature, membership of an event in its own automaton, a handler, a report message, or an `ExecutionContext` read or write — SHALL therefore be applied to a set other than `jca`, even though the same defect is present in `jca`: the derived set `jca_android` under gh101, the successor set `jca_v2` under the legible-report programme. Each such correction SHALL be entered in that set's divergence record naming the hunk, the reason, and the task that introduced it. Divergence between the sets outside allow-lists is the expected outcome; divergence that is not recorded is not.

Two consequences SHALL be carried in the change's records rather than left to be inferred. The `jca` set knowingly retains its defects and the spurious reports they produce, so results measured under it are reproducible without being correct. And a difference in outcome between `jca` and any other set can no longer be attributed to the platform allow-list alone, because it may equally arise from a repair present in one set only; no measurement separates the two contributions after the fact.

The freeze governs what the instrument **states** — the specifications and the transformation tables the frozen `CipherSpec` delegates to — and not the runtime it executes on. Additive changes to shared Java are admissible where the frozen set cannot observe them at all: a new `Property` constant that no `jca` specification references, or a new class that no `jca` specification imports, leaves the frozen set's generated monitor unchanged.

A **repair to shared runtime code the frozen set does reference** is also admissible, under two conditions and not otherwise. The repair MUST apply identically to both sets — shared code MUST NOT branch on the active specification set, because that would place the frozen set's verdict under state set outside its own specification, which is the hazard INV-INS-112 exists to prevent. And its effect on the frozen set MUST be enumerated site by site in the change's records rather than assumed absent. A defect in the machinery is not made correct by having been present when a measurement was taken, and a rule forbidding its repair would forbid repairing the weaver as well. The legible-report programme makes three such repairs — the collector's escaping and null guard, the wrapper arity rule, and the dedupe identity — and enumerates their effect on `jca` in its records; the last one changes what `jca` reports by construction and is declared as a count discontinuity, not hidden.

The distinction is between a correction of what counts as a misuse, which is confined to a non-frozen set, and a correction of the mechanism that decides it, which is not confinable and is therefore recorded.

#### Scenario: Correction reaches the frozen set

- **WHEN** a layer-2 correction is applied to a file under `jca/`, or to `CipherTransformationUtil.java`
- **THEN** the freeze check MUST fail against the base commit
- **AND** the correction MUST be moved to a non-frozen set, however clearly it repairs a real defect

#### Scenario: Correction lands in the derived set

- **WHEN** a binding defect present in both sets is corrected in `jca_android` only
- **THEN** the freeze check MUST pass
- **AND** the divergence record MUST gain an entry naming the hunk and the reason
- **AND** the `jca` set MUST retain the defect, recorded as knowingly retained

#### Scenario: Correction lands in the successor set

- **WHEN** a report message of `jca` is rewritten in `jca_v2` only
- **THEN** the freeze check MUST pass
- **AND** `data/jca_v2/divergence_record.csv` MUST gain an entry naming the hunk and the reason
- **AND** the `jca` set MUST keep emitting `unknown` at that site, recorded as knowingly retained

#### Scenario: Divergence appears without a record entry

- **WHEN** the two sets differ outside allow-list content in a hunk that no divergence-record entry names
- **THEN** the check MUST fail
- **AND** the hunk MUST either gain an entry with its reason or be reverted

#### Scenario: Shared Java gains a symbol the frozen set cannot observe

- **WHEN** `Property` gains a constant, or `rvsec-core` gains a class, that no `jca` specification references or imports
- **THEN** the freeze check MUST pass
- **AND** the monitor generated from the `jca` set MUST be unchanged, which is what makes the addition admissible

#### Scenario: Shared runtime code the frozen set references is repaired

- **WHEN** a defect is corrected in `rvsec-core` code that specifications of both sets call
- **THEN** the repair MUST apply identically to both sets, with no branch on the active specification set
- **AND** the sites at which the frozen set's behaviour changes MUST be enumerated in the change's records
- **AND** the freeze check passing MUST NOT be reported as evidence that the frozen set's behaviour is unchanged
