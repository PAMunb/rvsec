## Purpose

The `core` capability owns `RvErrorLog`, the domain record of one runtime-verification violation, and with it the identity under which violations are deduplicated: `unique_msg` is both the `__hash__` and the `__eq__` of the record (`modules/rv-android-core/src/rv_android_core/domain/log.py`). This change touches that identity for one reason. In the published dataset 72.93 % of the 97,018 violation records carry the literal `unknown` as their message, and the identity `class:::method:::spec:::error_type:::message` therefore collapses every event of a specification that reports `unknown` into one key per method — per-event attribution is impossible for any consumer of the record. The specification-side repair (the message envelope `v=1 code=… ev=… …` emitted by the successor set `jca_android`) puts the offending event and a stable code into the message; the domain side has to admit them into the identity, or the repair changes the text of the message and nothing about how violations are counted.

`unique_msg` therefore gains two parts, `code` and `event`, read from the envelope keys `code=` and `ev=`, and becomes a seven-part key. A record produced by the frozen `jca` (no envelope) carries the sentinel `UNSPECIFIED` in both parts, so its key is well-formed and distinguishable from a record whose envelope named the event. Because the key is the identity, this is a declared count discontinuity: a `unique_errors` computed before this change and one computed after it are not comparable numbers, and every report of a deduplicated count MUST say which era it belongs to. The change also closes a construction leak: today the same f-string is written in five places (`log.py:113`, `rv_platform/components/result_processor.py:631,:999,:1038`, `scripts/regenerate_results/regenerate_container.py:244`), so a change to the key in one place silently forks the identity in the others. After this change the key is built in exactly one place, `RvErrorLog.unique_msg`, and the other four call it.

The `source` field stays outside the identity (INV-CORE-40): two occurrences of one misuse at different lines are still one misuse. What enters is the event and its code, which are properties of *what* was violated, not of *where*.

## Data Contracts

Only the entries this change alters are restated; every other input, output, side-effect and error of the capability is unchanged.

### Input

- `RvErrorLog.message: str` -- the violation description as the monitor emitted it (source: `logcat_parser`, the CSV collector, or a persisted `tasks.json`). When the emitter is an envelope-producing set the message is `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'`; when it is not, the message is free text. In both cases it MUST NOT contain the substring `:::`
- `RvErrorLog.code: str` -- the `code=` value of the envelope, or the sentinel `UNSPECIFIED` when the message carries no envelope (source: the parser that built the record)
- `RvErrorLog.event: str` -- the `ev=` value of the envelope, or `UNSPECIFIED` when the message carries no envelope (source: the parser that built the record)

### Output

- `RvErrorLog.unique_msg: str` -- computed, `f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{code}:::{event}:::{message}"`, seven `:::`-separated parts (destination: `LogcatRepository` dedupe, `errors.csv`, `results.json`, every reader that splits on `:::`)
- `RvErrorLog.to_dict()` -- additionally carries the keys `code` and `event` (destination: `tasks.json`, `errors.csv`)

### Side-Effects

- **[Counts]**: `unique_errors` and every figure derived from it (`mop_errors_unique`, the `unique_msg` column of `errors.csv`) change value for any input where two records of one `(class, method, spec, error_type, message)` differ in `code` or `event`; the change is a declared discontinuity, not a defect

### Error

- (none added) -- `RvErrorLog` does not sanitize or reject the message; the `:::` prohibition is enforced by the producer (the envelope grammar forbids it inside values) and detected by the readers, which count a key with a part count other than seven as unparsed (INV-CORE-56)

## Invariants

- **INV-CORE-25** (restated, replacing the entry of the same number): `RvErrorLog.unique_msg` MUST be computed as `"{class_full_name}:::{method}:::{spec}:::{error_type}:::{code}:::{event}:::{message}"` — seven `:::`-separated parts, `code` and `event` read from the message envelope (`code=`, `ev=`) or equal to the sentinel `UNSPECIFIED` when the message carries no envelope. Two `RvErrorLog` instances with the same `unique_msg` MUST be considered equal. The key MUST be built in exactly one place, `RvErrorLog.unique_msg` in `rv_android_core/domain/log.py`; no other module MUST assemble it from the fields.
- **INV-CORE-41** (restated, replacing the entry of the same number): `RvErrorLog.unique_msg` counts at event granularity (`class:::method:::spec:::error_type:::code:::event:::message`) and is deliberately finer than the `(apk, class, method, spec)` key used for unique-misuse analysis. Any documentation or export that reports `unique_errors` MUST NOT present it as equivalent to a unique-misuse count, and MUST state which identity era the count belongs to — five-part (before this change) or seven-part (after it) — because counts of the two eras are not comparable.
- **INV-CORE-56**: The `message` part of `unique_msg` MUST NOT contain the substring `:::`. The producer of the message (the monitor's envelope grammar) forbids it inside every value; `RvErrorLog` MUST NOT rewrite the message to hide a violation of that rule, and a reader that splits `unique_msg` on `:::` and finds a part count other than seven MUST count the record as unparsed rather than reinterpret it.
- **INV-CORE-57**: Every published deduplicated count of violations MUST carry the identity era it was computed under. A count of the seven-part era MUST NOT be compared to a count of the five-part era without the discontinuity being stated beside the comparison, and the discontinuity measured on the same input MUST be non-zero where that input's records carry an `ev=` envelope — a zero difference there would mean `code` and `event` added no information to the identity, which is the failure the change exists to remove; on a pre-envelope input (the published dataset, comp162) the difference is zero by construction and is labelled so, not read as a failure.

## RENAMED Requirements

- FROM: `### Requirement: Event Granularity of unique_msg Is Documented, Not Changed (FR13)`
- TO: `### Requirement: Event Granularity of unique_msg Is Extended and Declared (FR13)`

## MODIFIED Requirements

### Requirement: Event Granularity of unique_msg Is Extended and Declared (FR13)

`RvErrorLog.unique_msg` MUST be `"{class_full_name}:::{method}:::{spec}:::{error_type}:::{code}:::{event}:::{message}"`
(INV-CORE-25). `code` and `event` are the `code=` and `ev=` values of the message envelope the monitor emitted; when the
message carries no envelope — every record produced by the frozen `jca` set, and every record persisted before this
change — both parts MUST be the sentinel `UNSPECIFIED`, never an empty string, so a legacy record has a readable
seven-part key that is distinguishable from an envelope record whose event was named. The `message` part MUST NOT
contain `:::` (INV-CORE-56): the producer forbids it inside every envelope value, the model does not rewrite the
message to hide a violation of that rule, and a reader that finds a part count other than seven counts the record
as unparsed — a separator inside a part makes the key unreadable to every consumer that splits on it.

The key MUST be built in exactly one place, `RvErrorLog.unique_msg` in `rv_android_core/domain/log.py`. The four
other construction sites in the tree — `rv_platform/components/result_processor.py:631`, `:999`, `:1038` and
`scripts/regenerate_results/regenerate_container.py:244` — MUST be deleted, and each caller MUST obtain the key
from the domain object (P3). A key assembled elsewhere from the fields would fork the identity the moment the
domain formula changed, which is what this change does.

Because `unique_msg` is `__hash__` and `__eq__` of `RvErrorLog`, the identity of a violation record changes with
this requirement. That is a declared count discontinuity, not a side effect: every deduplicated count computed
before this change (five-part identity) is not comparable to one computed after it (seven-part identity), and any
report of `unique_errors`, `mop_errors_unique` or the `unique_msg` column MUST say which era it belongs to
(INV-CORE-41, INV-CORE-57). The discontinuity measured on the same envelope-carrying input MUST be non-zero; on a pre-envelope input it is zero by construction and is labelled so.

The model documentation MUST state that this key counts at event granularity and is finer than the
`(apk, class, method, spec)` key used to count unique misuses in the thesis and the journal article, and MUST give
the reason: `error_type` separates a sequence violation from a constraint violation in the same method, `event` and
`code` name the transition of the automaton that failed, and `message` names the offending parameter, so two events
under one method are two different misuses.

The documentation MUST state the consequence explicitly — that `unique_errors` and the `mop_errors_unique` column
derived from it are not numerically comparable to a unique-misuse count, nor across identity eras — so that a
reader comparing the two figures does not conclude that one is defective.

#### Scenario: an envelope message yields code and event parts

- **WHEN** an `RvErrorLog` is created with `class_full_name` = `com.apk.axml.APKParser`, `method` = `getCertificateFingerprint`,
  `spec` = `MessageDigestSpec`, `error_type` = `ForbiddenMethod`, `code` = `MD-FORB-01`, `event` = `g1` and
  `message` = `v=1 code=MD-FORB-01 ev=g1 obj=MessageDigest val='MD5' exp='SHA-256, SHA-384, SHA-512' msg='digest not allowed'`
- **THEN** `unique_msg` MUST be
  `com.apk.axml.APKParser:::getCertificateFingerprint:::MessageDigestSpec:::ForbiddenMethod:::MD-FORB-01:::g1:::v=1 code=MD-FORB-01 ev=g1 obj=MessageDigest val='MD5' exp='SHA-256, SHA-384, SHA-512' msg='digest not allowed'`
- **AND** splitting it on `:::` MUST yield exactly seven parts, the fifth being `MD-FORB-01` and the sixth `g1`

#### Scenario: a legacy `unknown` message yields the sentinels

- **WHEN** an `RvErrorLog` is created from a record of the frozen `jca` set with `class_full_name` = `okio.ByteString`,
  `method` = `digest$okio`, `spec` = `MessageDigestSpec`, `error_type` = `SequenceViolation` and `message` = `unknown`, no envelope present
- **THEN** `code` MUST be `UNSPECIFIED` and `event` MUST be `UNSPECIFIED`
- **AND** `unique_msg` MUST be `okio.ByteString:::digest$okio:::MessageDigestSpec:::SequenceViolation:::UNSPECIFIED:::UNSPECIFIED:::unknown`
- **AND** two such records MUST compare equal and hash equal, so a legacy campaign deduplicates exactly as its records allow

#### Scenario: distinct events under one message remain distinct

- **WHEN** two violations occur in `com.apk.axml.APKParser.getCertificateFingerprint` under `MessageDigestSpec` with the same
  `error_type` and the same `message`, one with `event` = `g1` and one with `event` = `d1`
- **THEN** their `unique_msg` values MUST differ
- **AND** `unique_errors` MUST count them as 2
- **AND** the `(apk, class, method, spec)` analysis key MUST count them as 1 unique misuse
- **AND** both counts MUST be understood as correct at their own granularity

#### Scenario: a message containing the separator is counted, not reinterpreted

- **WHEN** a record reaches a reader with `message` = `expecting one of {A:::B} but found C.` and its `unique_msg` therefore splits into eight parts on `:::`
- **THEN** the reader MUST count the record as unparsed
- **AND** MUST NOT take the fifth and sixth parts as `code` and `event`
- **AND** the record MUST NOT be silently dropped from the row total

#### Scenario: the key has one constructor

- **WHEN** the tree is searched for the f-string pattern `:::{` outside `rv_android_core/domain/log.py`
- **THEN** `rv_platform/components/result_processor.py` and `scripts/regenerate_results/regenerate_container.py` MUST contain no occurrence
- **AND** each of those callers MUST read `unique_msg` from the `RvErrorLog` (or its `to_dict()`), never assemble it

#### Scenario: the discontinuity is declared and non-zero

- **WHEN** `unique_errors` is computed for a corpus whose records carry `ev=` envelopes (the differential-harness traces of the change, or the device logcat of its integration task) once with the five-part identity and once with the seven-part identity
- **THEN** the two figures MUST be published side by side, each labelled with its era
- **AND** their difference MUST be non-zero
- **AND** neither figure MUST be presented as a correction of the other

#### Scenario: a pre-envelope corpus is zero by construction

- **WHEN** the same two computations run on `experimento-comp162` or the published dataset, whose records carry no envelope and whose `event` is therefore the sentinel on every row
- **THEN** the two figures are equal, MUST be published labelled `zero by construction`, and MUST NOT be read as the failure of the seven-part identity

### Requirement: RvErrorLog Preserves the Source Location in the Written Schema (FR13, FR14)

`RvErrorLog.to_dict()` MUST include the `source` field, and the per-run `errors.csv` produced by
`ResultProcessorComponent` MUST carry a corresponding `source` column placed after `method`. The
field MUST remain outside `unique_msg`, `__eq__` and `__hash__`, so that preserving it cannot
change `unique_errors`, `total_errors`, or any coverage or MOP metric.

The distinction this requirement encodes is between *excluding a field from the identity of a
violation* and *discarding it*. The source position must not identify a violation — two
occurrences of the same misuse at different lines are one misuse — but it is still the most
direct pointer to where the violation happened, and it is the evidence needed to audit a
frame-form normalization after a campaign has run.

Because the column set of `errors.csv` is a contract shared with `rvsec-dataset` and the
article's analysis scripts, the change MUST be verified against those consumers before it lands:
readers that address columns by name tolerate an added column, readers that address them
positionally do not.

#### Scenario: source survives serialization

- **WHEN** an `RvErrorLog` is created with `class_full_name` = `okio.ByteString`,
  `method` = `digest$okio`, `source` = `ByteString.kt:83`
- **THEN** `to_dict()` MUST contain the key `source` with value `ByteString.kt:83`

#### Scenario: source does not affect identity

- **WHEN** two `RvErrorLog` instances agree on `class_full_name`, `method`, `spec`,
  `error_type`, `code`, `event` and `message` but carry `source` = `ByteString.kt:83` and `ByteString.kt:84`
- **THEN** their `unique_msg` values MUST be identical
- **AND** `error1 == error2` MUST return True
- **AND** `hash(error1) == hash(error2)` MUST return True
- **AND** registering both in a `LogcatRepository` MUST yield `unique_errors` = 1

#### Scenario: errors.csv carries the source column

- **WHEN** `ResultProcessorComponent` generates `errors.csv` for a completed task
- **THEN** the header MUST be
  `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg`
- **AND** each row MUST carry the originating record's `source` value in that column
