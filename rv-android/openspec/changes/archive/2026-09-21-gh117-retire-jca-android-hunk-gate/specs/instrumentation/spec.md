## Purpose

This delta retires the per-hunk account of `jca_android` against its frozen seed `jca`, and pins the anchor convention of the set's label-code table.

`jca_android` was seeded byte-for-byte from `jca`, and every hunk by which it departed was enumerated in `data/jca_android/divergence_record.csv`, keyed by a digest of the hunk's changed lines and checked both ways by `scripts/gh104_divergence_record.py --check` from `tests/parity/test_gh104_specset_gates.py`. The key makes every edit re-key the rows it touches: a rewrite of the set's comments invalidated 168 rows and left 227 hunks unrecorded, and the gate turned CI red. The question the record answered — how the successor differs from the seed, and why — has no consumer since `jca` left use. What governs `jca_android` is its own oracle: the pinned expert rules through G-CONF, the predicate graph through G-PRED2, the label-code table and the message gate. The per-hunk clause of INV-INS-118 is therefore withdrawn, with its script and its test, and the record keeps only the narrative rows other gates read. The seed provenance, the freeze of `jca`, the membership-by-count clause and the archived set's own record under `data/gh101/` are unchanged.

The label-code table `rvsec-mop/src/main/resources/jca_android/codes.csv` anchors each code at the line that emits it. The documentation-convention requirement said only "the line each code is emitted from", and a re-anchoring pass read it as the line of the envelope that spells `code=`, one or two lines below the `ErrorCollector.instance().addError(` call the message gate compares. The requirement now names the `addError(` line.

## Data Contracts

### Input
- `data/jca_android/divergence_record.csv` — header `file,hunk,kind,summary,reason,task`; read by `scripts/gh104_gates.py` (`read_records`, `backing_record`, by specification and kind) and by `scripts/gh109_coverage_matrix.py` (`oracle-wart` rows naming a rule path)
- `rvsec-mop/src/main/resources/jca_android/codes.csv` — `file_line` read by `scripts/gh104_message_gate.py` (`code-anchor`)

### Output
- `data/jca_android/divergence_record.csv` — narrative rows only; `hunk` empty in every row
- `rvsec-mop/src/main/resources/jca_android/codes.csv` — `file_line` = `<Spec>.mop:<N>`, N the line of the emitting `addError(` call

### Side-Effects
- **[CI]**: the cross-cutting gate step no longer runs a per-hunk check of `jca_android`

### Error
- G-CONF failure `record: unbacked` — an allow-list difference with no backing row; the narrative row that backs it must exist with an empty `hunk`
- message-gate `code-anchor` finding — a `file_line` that does not name the emitting `addError(` line


## Invariants

- **INV-INS-109**: The `jca` specification set and the `CipherTransformationUtil` it delegates to MUST remain byte-identical to their state at this change's base commit, and every divergence between the archived derived set `jca_android_bug_predicate` and `jca` outside allow-list content MUST appear in `data/gh101/divergence_record.csv` with its reason. An unrecorded divergence of that set is a defect; a recorded one is a deliberate repair confined to it. The successor set `jca_android` is not enumerated against `jca` (INV-INS-118). Any edit reaching the frozen paths fails the check regardless of its merit.

- **INV-INS-118**: `jca_android` MUST be seeded from the frozen `jca` — never from the archived `jca_android_bug_predicate` — and no gate compares the set with its seed hunk by hunk: `jca` serves no experiment, so the set answers to its own oracle — the pinned expert rules (G-CONF), the predicate graph (G-PRED2), the label-code table and the message gate — and a per-hunk account against the seed is invalidated by any edit, a comment edit included. `data/jca_android/divergence_record.csv` carries narrative rows only, each with an empty `hunk` column: the departures of a value list from its expert clause that G-CONF reads (`api30-omits`, `platform-value`, `oracle-wart`, `spelling-variant`) and the recorded `behavioural`, `gate-scope`, `value-decision` and `set-archived` decisions. The seed is all 23 `.mop` files of `jca` (D-11). The set's membership is the tree's count, which a gate enumerates rather than asserts as a literal: 47 `.mop` files today — 22 of the seed (`RandomStringPassword.mop` left the set: it cannot accuse under any trace and writes no predicate), the junction specification `IvChainJunction.mop`, and the specifications added for rule coverage. Membership is what the count asserts, not predicate sites. The freeze of `jca` (INV-INS-109) is unaffected: nothing seeds or repairs `jca_android` by editing `jca/`, `CipherTransformationUtil.java`, `AndroidCipherTransformationUtil.java` or `ExecutionContext.java`, and the freeze gate MUST stay green, with the three gh101 gate scripts (`gh101_divergence_record.py`, `gh101_predicate_pairing_check.py`, `gh101_conformance_check.py` — two test invocations in `tests/parity/test_gh101_specset_gates.py`) pointed at the archive `jca_android_bug_predicate`, which is the set they describe.

- **INV-INS-141**: INV-INS-128 binds the frozen `jca` only; the predicate contract of `jca_android` is INV-INS-130/131/137, and the requirement "Predicate Sites of the Frozen Seed and Their Record in the Successor Set" asserts no per-file count equality over `jca_android`. G-2 admits `REQUIRES` accusers on `jca_android` (INV-INS-123), and constraint provenance (G-CONF) holds. The departure of `jca_android` from the seed's predicate machinery is accounted site by site in `predicate_graph.csv`, which is keyed for it; no record enumerates it hunk by hunk (INV-INS-118). The gate code that reads predicate sites MUST recognise the store, or it produces false verdicts: in `gh104_gates.py`, `accept_requires` and the `PREDICATE_CALL` regex; in `gh104_message_gate.py`, `_clause_family`, which classifies an orphan's clause family and cannot read it from an emptied `condition(...)`; in `tests/parity/test_gh104_specset_gates.py`, the census constants that describe the frozen `jca` and not the successor; and in `data/jca_android/gate_allowlist.csv`, the justifications of rows that cite a condition read.

- **INV-INS-147**: `jca_android` MUST contain zero `setObjectAsInAcceptingState`/`unsetObjectAsInAcceptingState` calls. The store does not offer the bookkeeping; the 25 calls the seed carries (19 set / 6 unset) are absent from the successor, whose predicate sites `predicate_graph.csv` inventories (INV-INS-141). Production has zero readers of that bookkeeping: the maintained readers (`Assertions.mustBe…InAcceptingState`) live in the `rvsec-agent` test corpus, which weaves the frozen `jca`.

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

3. **JCA Android** (`jca_android`) -- the successor set, to which the name is rebound: **23** specifications, seeded byte-for-byte from the frozen `jca` and carrying every specification-side change of the legible-report programme — allow-lists transcribed from the generated api30 CrySL rules under a declared normalisation rule, message envelopes, automaton and pointcut repairs. It carries no predicate at all: no `.mop` references `ExecutionContext`, which is why the two pure predicate propagators of the seed (`RandomStringPassword.mop`, `SecretKeySpec.mop`) do not exist in it (INV-INS-128). Its oracle is the api30 rule alone (INV-INS-125); no record enumerates the hunks by which it differs from its seed; `data/jca_android/divergence_record.csv` carries narrative rows only (INV-INS-118). Its `CipherSpec` names a new transformation utility under `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`, transcribed from `generated/api30/Cipher.cryptsl`. It carries `codes.csv`, the table of failure codes its envelopes emit.

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
- **AND** the directory MUST contain the seed's 23 `.mop` files and `codes.csv`
- **AND** `RandomStringPassword.mop` and `SecretKeySpec.mop` MUST be among them — D-11 withdrew their removal
- **AND** a later change MAY add files to the set: gh105 adds `IvChainJunction.mop`, taking the tree to 24, and restates the count in its own delta, so a reader MUST take the cardinality from the delta that owns the addition and never from a literal frozen here
- **AND** `custom_specs_dir` MUST NOT be required

#### Scenario: The archived derived set keeps its own divergence record

- **WHEN** the diff between `jca/` and `jca_android_bug_predicate/` is taken
- **THEN** hunks outside allow-list content MUST be present, since gh101's repairs were confined to that set
- **AND** every such hunk MUST be named by an entry in `data/gh101/divergence_record.csv`, which the rename does not rewrite

#### Scenario: Derived set diverges from the frozen set

- **WHEN** the diff between `jca/` and `jca_android/` is taken after the repairs have landed
- **THEN** a gate MUST NOT require a `data/jca_android/divergence_record.csv` row per hunk, since the successor set answers to its own oracle and not to the seed (INV-INS-118)
- **AND** every allow-list value of `jca_android` that differs from its expert clause MUST be backed by a `conformance_record.csv` row or a narrative `divergence_record.csv` row, which G-CONF checks (INV-INS-127)
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

Corrections to the platform-independent portion of a specification — an event binding, a pointcut signature, membership of an event in its own automaton, a handler, a report message, or an allow-list — SHALL therefore be applied to a set other than `jca`, even though the same defect is present in `jca`: the derived set under gh101, now archived as `jca_android_bug_predicate`, and the successor set `jca_android` under the legible-report programme. In the archived set each such correction is entered in `data/gh101/divergence_record.csv` naming the hunk, the reason and the task that introduced it, and a divergence there that is not recorded is a defect. In `jca_android` corrections are not enumerated against `jca`: the set is measured against its own oracle — the pinned expert rules, the predicate graph, the label-code table and the message gate — because `jca` serves no experiment, and a per-hunk account against it is invalidated by any edit, a comment edit included (INV-INS-118).

Two consequences SHALL be carried in the change's records rather than left to be inferred. The `jca` set knowingly retains its defects and the spurious reports they produce, so results measured under it are reproducible without being correct. And a difference in outcome between `jca` and any other set can no longer be attributed to the platform allow-list alone, because it may equally arise from a repair present in one set only; no measurement separates the two contributions after the fact. `jca_android` widens that gap deliberately — it changes allow-lists, messages, automata and the predicate regime at once — so every comparison against it MUST name which of those it is attributing the difference to, and the differential harness exists to make that attribution per trace rather than per campaign.

The freeze governs what the instrument **states** — the specifications and the transformation tables the frozen `CipherSpec` delegates to — and not the runtime it executes on, and not the monitor a `.mop` generates. Reproducing a published measurement is done by pinning the toolchain, and the pin SHALL name the **JDK**: the state numbering a generated monitor carries depends on the JDK that ran the generation, because the ERE-to-FSM conversion of the logic repository returns its states in a different order, so a monitor regenerated under a different JDK is isomorphic to the frozen control — same automaton, same verdicts, different state labels — and not byte-identical to it. Any diff of a regenerated monitor against an existing control MUST therefore name the JDK that produced the control (`data/gh104/evidence/g_regeneration.md`), and a gate MUST NOT read a raw state number as an identity. Additive changes to shared Java are admissible where the frozen set cannot observe them at all: a new `Property` constant that no `jca` specification references, or a new class that no `jca` specification imports, leaves the frozen set's generated monitor unchanged. The new transformation utility `jca_android/CipherSpec.mop` names is admissible on exactly this ground: it is a new class in `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` that neither `CipherTransformationUtil` nor `AndroidCipherTransformationUtil` is edited to accommodate, and that no `jca` specification imports. The alias utility of INV-INS-127 is admissible on the same ground and for the same reason.

A **repair to shared runtime code the frozen set does reference** is also admissible, under two conditions and not otherwise. The repair MUST apply identically to both sets — shared code MUST NOT branch on the active specification set, because that would place the frozen set's verdict under state set outside its own specification, which is the hazard INV-INS-112 exists to prevent. And its effect on the frozen set MUST be enumerated site by site in the change's records rather than assumed absent, unless the researcher declares it as a count discontinuity instead, as for the weaver repairs below (decision of 2026-09-15). A defect in the machinery is not made correct by having been present when a measurement was taken, and a rule forbidding its repair would forbid repairing the weaver as well. The legible-report programme makes four such repairs that change what a `jca` run executes — the collector's escaping and null sentinel (`ErrorCollector`), the `ViolationRecorder` frame filter that fills `location`, the lock framing of the generated dispatcher (INV-INS-129), and the `ErrorSummary` dedupe identity — and enumerates their effect on `jca` in its records, in the consumer-matrix task of the transport group; the five weaver repairs of gh114 — positional arity, framework subtypes, branch targets, nested types and after-finally (INV-INS-159 to INV-INS-163) — change what a `jca` run executes and are declared as a count discontinuity, not enumerated; and the dedupe identity changes what `jca` reports and is declared as a count discontinuity, not hidden.

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

#### Scenario: Correction lands in the derived set

- **WHEN** a report message of `jca` is rewritten in `jca_android` only
- **THEN** the freeze check MUST pass
- **AND** a `data/jca_android/divergence_record.csv` row MUST NOT be required for the hunk (INV-INS-118)
- **AND** the `jca` set MUST keep emitting `unknown` at that site, recorded as knowingly retained

#### Scenario: Divergence appears without a record entry

- **WHEN** `jca/` and the archived `jca_android_bug_predicate/` differ outside allow-list content in a hunk that no entry of `data/gh101/divergence_record.csv` names
- **THEN** the check MUST fail
- **AND** the hunk MUST either gain an entry with its reason or be reverted

#### Scenario: Shared Java gains a symbol the frozen set cannot observe

- **WHEN** `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` gains the transformation utility `jca_android/CipherSpec.mop` names, and no `jca` specification imports it
- **THEN** the freeze check MUST pass
- **AND** the monitor generated from the `jca` set MUST be unchanged, which is what makes the addition admissible
- **AND** `CipherTransformationUtil.java` and `AndroidCipherTransformationUtil.java` MUST both be byte-unchanged

#### Scenario: Shared runtime code the frozen set references is repaired

- **WHEN** a defect is corrected in runtime code that specifications of both sets execute — the collector's escape and null sentinel, the `ViolationRecorder` frame filter, the generated dispatcher's lock framing, or the `ErrorSummary` identity
- **THEN** the repair MUST apply identically to both sets, with no branch on the active specification set
- **AND** the four sites and their effect on a `jca` run MUST be enumerated in the change's records — a `jca` message with a comma or newline now arrives intact instead of splitting the line; a `jca` report whose frame is in the monitor now carries the application frame as `location`; a `jca` handler that throws now releases the lock instead of converting the run into a busy-wait; a `jca` record's `unique_msg` now has seven parts and the counts are discontinuous with the baseline — and the consumer-matrix task of the transport group records them
- **AND** the freeze check passing MUST NOT be reported as evidence that the frozen set's behaviour is unchanged

### Requirement: Successor Specification Set `jca_android`

The system SHALL rebind the name `jca_android` to a new specification set at `rvsec-mop/src/main/resources/jca_android/`, seeded from the frozen `jca` and selectable by name. Nothing is added to the enumeration of selectable sets: it keeps its four values, and what changes is which directory the second of them resolves to. The set exists because neither JCA set that existed before is available as a target: `jca` is frozen (it produced the published measurements), and the derived Android set was judged NOT READY by the 2026-08-08 audit, so seeding from it would carry an unaudited instrument forward under a new name. Every specification-side change of this contract — allow-lists, messages, automata, pointcuts — lands in `jca_android` alone.

Before the seed is written, the directory that held the derived set SHALL be renamed to `rvsec-mop/src/main/resources/jca_android_bug_predicate/`, and the archived set SHALL NOT be selectable by `--specification-set` or by `ExperimentConfig.specification_set`. It is preserved and not deleted, because it is the instrument the 2026-08-08 audit assessed and the reference a reader of that audit needs; reproducing the audit is done by pointing `RVSEC_HOME` at the commit the audit was run against, not by naming the set in a new run. The name states why the set was set aside — a predicate regime whose defects the audit measured, which is exactly what the successor removes rather than repairs (INV-INS-128) — so a reader who meets the directory does not have to reconstruct the reason from the change history.

The seed SHALL be the 23 `.mop` files of `jca` byte-for-byte, `RandomStringPassword.mop` and `SecretKeySpec.mop` included: they are pure predicate propagators — each exists only to write a `Property` another specification reads — and since the predicates are carried over unchanged, they still have work to do. The set therefore holds **23** specifications.

The set SHALL carry five records under `data/jca_android/` — a divergence record of narrative rows, each with an empty `hunk` column, carrying the departures of a value list from its expert clause that G-CONF reads and the recorded behavioural, gate-scope and value decisions (INV-INS-118); a conformance record naming, per specification, the expert rule its value clauses answer to and the api30 rule its ORDER and predicate clauses answer to (INV-INS-125); an alias table, a file of its own, one row per normalisation entry with its source pointer (INV-INS-127); a gate allowlist for structural-gate exceptions with reasons (INV-INS-123); a predicate-removal record, one row per removed predicate site (INV-INS-128); and a constraint table, `constraint_table.csv` (`spec,cryptsl_line,mop_line,verdict`; verdicts `CRYSL-NAO-IMPLEMENTADO`, `IGUAL`, `MOP-SEM-BASE`, `MOP-MAIS-PERMISSIVO`, `DIVERGENTE`, `MOP-MAIS-RESTRITIVO`), the row-level clause-by-clause comparison of every api30 `CONSTRAINTS` clause with the seed that G-CONF's report on the frozen `jca` reproduces — plus `codes.csv` beside the `.mop` files, the table of failure codes its envelopes emit. It SHALL NOT carry a `predicate_omissions.csv`: that record, which gh101 uses for a `Property` written and never read, has nothing to hold in a set that writes none, and its name SHALL NOT be reused for the removal record.

The set SHALL be reachable at every site that enumerates specification sets: `valid_spec_sets` and the directory mapping in `rv_experiment/config.py`, the `click.Choice(["jca", "jca_android", "generic", "custom"])` on `--specification-set` at `rv_experiment/__main__.py:443`, INV-INS-09, INV-EXP-03 clause (f), and the mapping paragraph of `Just-in-Time Sub-Module Configuration`. None of those lists grows — `jca_android` is already in all of them — so what each site MUST be checked for is that the name now resolves to the successor set and that no site offers `jca_android_bug_predicate`. A set reachable only through `custom` with a hand-written path is a set a mistyped path silently swaps for the uncorrected one, which is why the archived directory is left with no name at all rather than a second value.

#### Scenario: `jca_android` is selected by name

- **WHEN** `ExperimentConfig.specification_set` is `"jca_android"`
- **THEN** `get_monitored_operations_config()` MUST create an `RVGeneratorConfig` with `mop_specs_dir` pointing to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/`
- **AND** the directory MUST contain exactly 23 `.mop` files and `codes.csv`
- **AND** `custom_specs_dir` MUST NOT be required

#### Scenario: the seed is the frozen set, whole

- **WHEN** the set is first created and `diff -r` is taken over the `*.mop` files of `jca/` and `jca_android/`
- **THEN** there MUST be no file present in one directory and absent from the other — D-11 withdrew the removal of `RandomStringPassword.mop` and `SecretKeySpec.mop`, and both MUST be present in `jca_android/`
- **AND** every one of the 23 files MUST be byte-identical between the two directories
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
- **THEN** a `data/jca_android/divergence_record.csv` row MUST NOT be required per hunk, and a gate MUST NOT recompute the hunks between `jca/` and `jca_android/` (INV-INS-118)
- **AND** when the edit makes an allow-list differ from its expert clause, G-CONF MUST find a backing row in `conformance_record.csv` or a narrative row in `divergence_record.csv`, or fail naming the clause
- **AND** `jca/TrustManagerFactorySpec.mop` MUST be byte-identical to commit `7e7acb69`

### Requirement: Documentation Convention of the `jca_android` Specification Set

Every comment of a `.mop` file under `rvsec-mop/src/main/resources/jca_android/`, and of the helper classes `Property`, `PredicateStore`, `PredicateVerdict`, `ConscryptAliasTable`, `CipherTransformationNormalizer`, `ErrorType`, `ErrorDescription`, `ErrorSummary` and `Evidence` in `rvsec-core`, SHALL be self-contained: a reader MUST be able to understand it with the file open and nothing else. A comment SHALL describe what the code does now (P4) and SHALL NOT refer to anything outside the code and the CrySL rules — no change, issue, invariant, decision, task, date, record under `data/jca_android/`, report, measurement, other specification set, or line of any file — and SHALL NOT use promotional or bias language ("modern", "sophisticated", "elegant", "state-of-the-art", "cutting-edge", "advanced") (INV-INS-169). The set's own `codes.csv`, which maps each report code to its site, MAY be named.

The documentation of the `.mop` set SHALL be detailed. Every event, predicate read and predicate write carries its own comment, even where a neighbouring event realises the same rule label, and a comment explains its site completely rather than briefly: the reader of a specification is reconstructing why a check exists or is absent, and a comment left out because the code looked self-evident is indistinguishable from an omission. A comment that already complies with this requirement SHALL be kept as it is.

**Java helper classes.** The helper classes SHALL follow the Java documentation convention written in the "Documentation conventions" section of `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md`, which maps the `rv-doc-code` conventions onto Javadoc and keeps the house style of that module: (1) depth by tier — full Javadoc for public API and orchestrators, summary with `@param`/`@return` for internal methods over ten lines, one line for small helpers, and no Javadoc for self-evident accessors, setters and `toString`; (2) a package or class Javadoc opens with a noun phrase saying what it is, a method Javadoc with an imperative sentence ending in a period; (3) class sections are topical `<h2>`/`<h3>` headings, not a fixed vocabulary; (4) `@param`, `@return` and `@throws` carry no types, and `@throws` states its condition with "when" or "if"; (5) a field with meaningful state carries a one-line Javadoc; (6) a `@return` of a map or JSON document lists its keys; (7) inside a method, `// Phase N:` marks orchestration phases, `// Step N:` marks algorithm steps, and a rationale block sits directly above the code it explains; (8) contracts use `MUST`/`MUST NOT` and `Precondition:`/`Postcondition:`; (9) code is cited with `{@code}` and `{@link}`, and every `{@link}` target exists; (10) no invariant, decision, task, change or issue identifier, date, `file:line`, reference to `architecture.md` or to a report, history narrative, or promotional language; (11) `TODO(topic)` and `FIXME(topic)` name a module or topic, never an issue number. Unlike the `.mop` set, trivial Java members are not documented: a comment is written only where it tells the reader something the signature does not.

**Relation to the CrySL rule.** The file header SHALL name the class the specification monitors and the CrySL rule it transcribes, summarise what the specification checks (the order, the value constraints, the predicates it requires and ensures), and state the divergences from the rule and the reach limits of the monitor. Its `@see` SHALL point to the rule in `CROSSINGTUD/Crypto-API-Rules` at commit `6d844ab402229aaefa4c5e45bf080987b787624b`, not at a moving branch or a ruleset release: that commit holds the JCA rules the specifications transcribe, and it is byte-identical to the rule set the CogniCrypt 5.0.1 baseline ran. Where a specification admits a value its cited rule does not list, the header SHALL state it as behaviour; in the set this is `CipherSpec`, which also admits `CCM` for AES, with `NoPadding`. Each event, predicate read and predicate write SHALL say which label or clause of the rule it realises, **quoting the clause by its text** — its section (`EVENTS`, `ORDER`, `CONSTRAINTS`, `REQUIRES`, `ENSURES`, `NEGATES`, `FORBIDDEN`), its label, and the clause between backticks — and SHALL NOT cite it by line number, because the clause text identifies the clause in every version of the rule and a line number identifies it in one.

**Mechanism.** Where the placement or shape of the code is not obvious at the site, the comment SHALL explain it where it appears, even when the same explanation appears in another file: that a clause is checked in the event body because a `condition(...)` guard runs before the transition and would silence a violating call; that a predicate write is staged in a field because a handler receives no event arguments and runs after the transition is decided; that an `@fail` handler of a single-symbol order cannot fire and is written because the generator expects it; that a read separates a violated predicate from an unobserved one because the second is as often a reach limit of the instrumentation as a misuse. A comment MAY name another specification of the set, and its event, as the producer or consumer of a predicate, provided the comment is understandable without opening that file.

**Divergences and constraints of the toolchain.** A difference between the specification and its rule SHALL be stated as behaviour with its technical reason, never as the decision that produced it. A constraint of the monitor generator that fixes the shape of a file — the 17-event ceiling, the deduplication of imports by class name across the merged monitor — SHALL be stated briefly where it applies.

**Scope of the review.** A change that reviews comments under this requirement SHALL rewrite only the comments that do not comply, SHALL leave every non-comment token of the files unchanged, and SHALL update the `file_line` column of `jca_android/codes.csv` afterwards, so that each row names the line of the `ErrorCollector.instance().addError(` call that emits its code — not the line of the envelope that spells `code=`, which sits one or two lines below. That line is what the `code-anchor` check of `scripts/gh104_message_gate.py` compares, and what a reader follows from a report back to the site that made it. `CipherTransformationUtil` SHALL NOT be edited, because the `jca` set freezes it byte-identical. `data/jca_android/NEW_SPEC_CONVENTIONS.md` SHALL state this convention, so a specification added to the set is written under it.

#### Scenario: a value constraint is cited by its text

- **WHEN** the comment above the digest list of `MGF1ParameterSpecSpec.mop` relates the list to its rule
- **THEN** it MUST quote the clause as `CONSTRAINTS` of `MGF1ParameterSpec.crysl`: `mdName in {"SHA-256", "SHA-384", "SHA-512"}`
- **AND** it MUST NOT contain `MGF1ParameterSpec.crysl:14` or any other line number

#### Scenario: a mechanism is explained instead of cited

- **WHEN** a comment of `CipherSpec.mop` explains why the key-origin read of event `i2` is in the event body
- **THEN** it MUST say that a `condition(...)` guard compiles to an early return ahead of the body and of the transition, so a key whose producer was never observed would drop the `init` out of the automaton and the next call would be reported as a wrong call sequence
- **AND** it MUST NOT contain `INV-INS-133`, a decision identifier, or the words "used to"

#### Scenario: a reach limit is stated as behaviour

- **WHEN** the comment of `MGF1ParameterSpecSpec.mop` explains objects obtained from the static constant `MGF1ParameterSpec.SHA256`
- **THEN** it MUST say that the constant is built inside the platform, where nothing is instrumented, so the constructor event never fires for it and the object carries no `preparedMGF1` predicate
- **AND** it MAY say that `OAEPParameterSpecSpec` therefore reports such an object as not observed rather than as a violation
- **AND** it MUST NOT cite the invariant that separates the two report families or a campaign count

#### Scenario: a file that exists because of a generator limit says why

- **WHEN** the header of `IvChainJunction.mop` explains why the file exists beside `CipherSpec.mop`
- **THEN** it MUST say that the clauses it reads bind the parameter-spec, `SecureRandom` and plaintext arguments of `Cipher` calls that `CipherSpec`'s events do not bind, and that `CipherSpec` cannot gain an event because it already declares 17, the most the monitor generator can build
- **AND** it MUST NOT justify the file's name by the changes, traces or reports that cite it

#### Scenario: the header cites the upstream rule at the pinned commit

- **WHEN** the header of `CipherSpec.mop` is read
- **THEN** its `@see` MUST be `https://github.com/CROSSINGTUD/Crypto-API-Rules/blob/6d844ab402229aaefa4c5e45bf080987b787624b/JavaCryptographicArchitecture/src/Cipher.crysl`
- **AND** the header MUST state that the specification also admits `CCM` for AES, with `NoPadding`, which that rule does not list
- **AND** no other header of the set MUST carry such a statement, because the other 48 rules the set answers to are identical to the cited commit

#### Scenario: the rewrite leaves the code unchanged

- **WHEN** the comments of `KeyStoreSpec.mop` are rewritten
- **THEN** removing every comment from the file before and after the rewrite MUST yield the same token sequence
- **AND** the `file_line` of every `KEYSTORE-*` row of `jca_android/codes.csv` MUST name the line of the `addError(` call that emits that code after the rewrite
- **AND** the message gate over `jca_android` MUST report zero `code-anchor` findings

#### Scenario: a compliant comment is kept and every event keeps its own comment

- **WHEN** the comments of `MGF1ParameterSpecSpec.mop` and `CipherSpec.mop` are reviewed, and the field comment `Bound only on the conforming branch, which is what carries the object to `@match`.` of `MGF1ParameterSpecSpec.mop` already complies
- **THEN** that comment MUST be left byte-identical
- **AND** each of the five `update` events `u1`–`u5` of `CipherSpec.mop` MUST carry its own comment naming the rule's `Update` label and the overload it binds, even though all five realise the same label
- **AND** a comment MAY say that a report code is registered in the set's `codes.csv`, and MUST NOT name `data/jca_android/predicate_ledger.csv` or any other record under `data/jca_android/`
- **AND** no comment MUST describe the set or its checks as "modern", "sophisticated", "elegant", "state-of-the-art", "cutting-edge" or "advanced"

#### Scenario: a helper class follows the same convention

- **WHEN** the class comment of `CipherTransformationNormalizer.java` is rewritten
- **THEN** it MUST describe what the normaliser resolves and folds before delegating to `CipherTransformationUtil`, and MUST NOT name a class that is no longer in the tree, a decision identifier or a task
- **AND** `CipherTransformationUtil.java` MUST be byte-identical before and after the change
- **AND** a self-evident member such as a plain getter MUST carry no Javadoc, while `PredicateStore.validate` MUST carry a method Javadoc opening with an imperative sentence and stating what each `PredicateVerdict` answer means

#### Scenario: the Java convention is written where the module keeps its conventions

- **WHEN** `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/CLAUDE.md` is read after the change
- **THEN** it MUST contain a section titled "Documentation conventions" that states the eleven rules of the Java convention of this requirement
- **AND** that section MUST NOT cite invariant, decision, task or issue identifiers, and MUST NOT refer to `architecture.md` sections as a substitute for an explanation

#### Scenario: the next specification is written under the convention

- **WHEN** an author opens `data/jca_android/NEW_SPEC_CONVENTIONS.md` to write a new specification for the set
- **THEN** the document MUST state the comment convention of this requirement: self-contained comments, clauses quoted by text, no line numbers, no references outside the code and the rules
- **AND** its own guidance MUST NOT cite invariants, decisions or line numbers of `.mop` files

### Requirement: Predicate Sites of the Frozen Seed and Their Record in the Successor Set

Every `ExecutionContext` site of the frozen `jca` SHALL be present in `jca` itself at the same event and unrewritten (INV-INS-128): 134 lines across its 23 files — 23 `import`, 27 `validate(`, 49 `setProperty(`, 9 `remove(`, 25 `setObjectAsInAcceptingState`/`unsetObjectAsInAcceptingState` and the comment at `MessageDigestSpec.mop:25`. No `condition()` of `jca` loses a predicate conjunct, no predicate-only accuser loses its declaration, no `@match`/`@match1` body is emptied. The gate is **G-PRED**, a grep, so it cannot drift, and it runs over `jca` only.

`jca_android` is seeded from those 23 files and carries no `ExecutionContext` site (INV-INS-130). Its predicates go through the set's own store (INV-INS-131), placed by INV-INS-133/134 and inventoried in `data/jca_android/predicate_graph.csv` under the closure gate G-PRED2 (INV-INS-137). The departure of `jca_android` from the seed's predicate sites is accounted site by site in `predicate_graph.csv` (INV-INS-141), and a departure that changes what is accused carries its satisfy/violate trace pair through the differential harness (INV-INS-144). No per-file count equality with the seed is asserted over `jca_android`.

Deleting the seed's predicate machinery without a replacement is not an admissible form of this departure: it deletes detection at 11 of the 21 predicate-reading events of the seed — seven entirely (`IvParameterSpec c3/c4`, `PBEKeySpecSpec err2/err3`, `SecureRandomSpec c3/setSeed3`, `SecretKeySpecSpec c3`), one in part (`PBEParameterSpecSpec c3`) and three by cross-specification key provenance (`CipherSpec i2`, `MacSpec i1/i2`). The store is what carries those detections into the successor set.

#### Scenario: the predicate gate finds every site of the seed

- **WHEN** G-PRED compares every `.mop` under `jca/` against the frozen census
- **THEN** every `ExecutionContext` site MUST be present at the same event, with the same `Property` and argument
- **AND** a missing or rewritten site MUST fail the gate naming the file, the event and the kind — `validate`, `setProperty`, `remove` or accepting-state
- **AND** the per-file counts MUST sum to 134 over the 23 files
- **AND** G-PRED MUST NOT run over `jca_android`, where `grep -rlw 'ExecutionContext' --include='*.mop'` returns nothing

#### Scenario: the two pure propagators are carried over

- **WHEN** the two pure predicate propagators of the seed, `RandomStringPassword.mop` and `SecretKeySpec.mop`, are looked up in `jca_android`
- **THEN** `SecretKeySpec.mop` MUST be present and its predicate sites MUST go through the store, its `e1` read recorded in `predicate_graph.csv` with disposition `propagation` — a propagation read is recorded, never armed with a report site
- **AND** `RandomStringPassword.mop` MUST be absent: it cannot accuse under any trace and writes no predicate, so the set loses no report by it

### Requirement: Reformulated Scope of G-PRED and Retirement of `rvsec-mop-defsuses`

G-PRED (gh104) SHALL be the byte-identity lock of the frozen `jca` predicate machinery and SHALL NOT apply to `jca_android`, whose predicate contract is carried by INV-INS-130/131/137 (INV-INS-141). The gh104 gate code that reads predicate sites SHALL recognise the `jca_android` store: in `gh104_gates.py`, `accept_requires`, which decides whether G-2 admits a `REQUIRES` clause family, and the `PREDICATE_CALL` regex, which covers the store and arity N.

`rvsec-mop-defsuses` SHALL NOT be part of the reactor: its copy lives in `backup/gh105-retired/rvsec-mop-defsuses/` and no pom lists it (P3 — its `main()` pointed at an absolute path under an alias the JVM cannot resolve, `DefsUsesGraph.java:65-66`, its extractor discarded the object argument and every negated read, and it knew nothing of the automaton). Def/use closure over predicates is G-PRED2 over `predicate_graph.csv`, which carries everything that module discarded.

#### Scenario: The jca lock is untouched

- **WHEN** the gh104 gates run
- **THEN** G-PRED over `jca` MUST be green, byte for byte
- **AND** G-PRED MUST NOT run over `jca_android`
- **AND** G-2's `accept_requires` MUST recognize the store's read sites

#### Scenario: The dead module is retired completely

- **WHEN** the reactor tree is inspected
- **THEN** `rvsec/rvsec-mop-defsuses/` MUST NOT exist and `rvsec/rvsec/pom.xml` `<modules>` MUST NOT list it
- **AND** `grep -r "defsuses"` over the reactor MUST return no reference outside documentation and the historical record (module CLAUDE.md rows, `docs/`, archived changes, the `check_no_legacy_mop.py` skip list, the retired copy under `backup/` — which is tracked, not gitignored, and so lies inside the grepped tree — and the active `gh48-project-finalization` artifacts, whose `defsuses` rows are that change's own to update)
- **AND** the reactor MUST build

#### Scenario: The successor set departs from its seed's predicates by record

- **WHEN** the requirement "Predicate Sites of the Frozen Seed and Their Record in the Successor Set" is evaluated against `jca_android`
- **THEN** no per-file count equality with the seed (summing to 134) MUST be asserted — the departure is accounted site by site in `predicate_graph.csv` (INV-INS-141)
- **AND** a pure propagator of the seed carries a propagation read that is recorded, never armed

### Requirement: Producer Specifications for Expert Rules

Each new specification SHALL be written against its expert rule alone: the event alphabet realizes the rule's EVENTS (overloads fused per the existing fusion rules), the automaton realizes the rule's ORDER, every value CONSTRAINT is transcribed with an accusing branch (INV-INS-152), predicates are written at the ORDER acceptance point and read in event bodies per the gh105 substrate rules, and every accusation site has a `codes.csv` row. Platform viability is verified before writing (INV-INS-154).

The same obligations bind a specification **already in the set** when a verified finding shows it departs from its rule: the alphabet obligation is INV-INS-157 (the rule's anonymous argument position is realized for every platform overload), the accusation obligation is INV-INS-152 (a value clause living only in `condition(...)` is defective), the value-semantics obligation is INV-INS-153 (producer and reader of one predicate resolve spellings the same way), and the wiring obligation is INV-INS-151 read from the writing end (a predicate three sites read is written). A repair under these obligations changes what the instrument accuses, and SHALL therefore be stated as a ratified decision with a divergence-record row, never applied as silent hygiene.

#### Scenario: Trivial parameter-spec rule becomes a specification

- **WHEN** a rule with `ORDER = Con` and value constraints (e.g. `ECGenParameterSpec.crysl`: `stdName` in the admitted curve list, ensuring `preparedEC`) is implemented
- **THEN** the specification MUST accuse on construction with a name outside the list, write `preparedEC` only on the conforming branch, and declare no events beyond the rule's alphabet
- **AND** the generated monitor MUST be inspected as an artifact (INV-INS-145), never trusted from the generator's exit code

#### Scenario: Value clause transcribed as a silent guard is rejected

- **WHEN** a new or edited specification carries a value constraint only as `condition(...)` on the event, so the violating call takes no transition and emits nothing
- **THEN** the specification MUST be treated as defective under INV-INS-152
- **AND** the repair MUST fuse the test into the event body with an accuser on the violated branch, following the existing `IvParameterSpec` fusion form

#### Scenario: Existing specification narrows the rule's alphabet

- **WHEN** an expert rule writes `getInstance(algorithm, _)` and the platform jar declares three overloads, and the specification's pointcut names only two of them
- **THEN** the specification MUST be treated as departing from the rule under INV-INS-157, because the unnamed route emits no event at all: its value clause cannot accuse, and the object's next observed call draws an ORDER verdict the rule does not state
- **AND** the repair MUST add the missing overload to the same fused event rather than create a second event, so the automaton is untouched and only the alphabet widens to the rule's own

#### Scenario: Producer and reader of one predicate disagree on spelling

- **WHEN** a producer writes `generatedKey` with the algorithm name its own rule ensures (a PBE family name from `SecretKeyFactory.crysl:22-25`) and the consuming site queries with a folded family name derived from the transformation
- **THEN** the store answers VIOLATED for a program that satisfied both rules, which INV-INS-153 defines as a defect of the set rather than a legitimate verdict
- **AND** the repair MUST be made on the side that departed from the letter — here the reader, which SHALL accept the rule's own spelling as well as the folded family name — and MUST NOT introduce a value neither rule names

#### Scenario: Unobserved-predicate line reaches consolidation

- **WHEN** a results consumer aggregates a run whose report contains `-NOBS-` lines alongside `-CONSTR-` lines carrying the same `ErrorType`
- **THEN** the consumer MUST separate them on the `site_kind` column and MUST NOT count a `-NOBS-` line as conformance or as violation (INV-INS-158)
- **AND** the measurement of how often each site answers NOBS remains the harness checkpoint's business (task 7.3), not the consolidation's

#### Scenario: New specification enters the enforcement apparatus

- **WHEN** a new `.mop` is added to the set
- **THEN** it MUST enter every enumeration the apparatus derives — `codes.csv` bijection, predicate-graph rows for its predicate sites, an alphabet mapping (or a declared skip) for G-ORDER, and the re-pinned counting constants that CI enforces
- **AND** the additions MAY be batched per task group, but the final verification pass MUST show every gate green over the enlarged set
