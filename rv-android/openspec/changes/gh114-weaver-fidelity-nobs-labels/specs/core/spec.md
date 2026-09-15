## Purpose

This delta keeps the identity of a violation record stable when the monitor appends evidence to a non-observation report. The `instrumentation` delta of the same change adds two optional keys after `msg` in `-NOBS-` envelopes of `jca_android`: `vfp`, a truncated fingerprint of the value the monitor could not trace, and `vcls`, the runtime class of the bound object. Those values differ from object to object and from run to run by design — that is what makes them useful for triage — and `RvErrorLog.unique_msg`, which is `__hash__` and `__eq__` of the record and the source of every deduplicated count, embeds the whole message today (INV-CORE-25).

The identity therefore excludes the evidence keys while the record keeps them. No other part of the seven-part formula changes, no reader that splits `unique_msg` on `:::` sees a different part count, and a record without evidence keys has exactly the key it has today, so counts over envelopes that carry no evidence are unchanged.

## Data Contracts

### Input
- `RvErrorLog.message: str` — the envelope as the collector wrote it, possibly ending in ` vfp='…'` and/or ` vcls='…'`

### Output
- `RvErrorLog.unique_msg: str` — seven `:::`-separated parts whose seventh is the message without the trailing evidence keys

### Side-Effects
- None

### Error
- None; a message without an envelope or without evidence keys is used verbatim

## Invariants

- **INV-CORE-25**: `RvErrorLog.unique_msg` MUST be computed as `"{class_full_name}:::{method}:::{spec}:::{error_type}:::{code}:::{event}:::{identity_message}"` — seven `:::`-separated parts, `code` and `event` read from the message envelope (`code=`, `ev=`) or equal to the sentinel `UNSPECIFIED` when the message carries no envelope, and `identity_message` equal to `message` with the trailing evidence keys removed (INV-CORE-63). Two `RvErrorLog` instances with the same `unique_msg` MUST be considered equal. The key MUST be built in exactly one place, `RvErrorLog.unique_msg` in `rv_android_core/domain/log.py`; no other module MUST assemble it from the fields.
- **INV-CORE-63**: `identity_message` MUST be `message` with every trailing ` vfp='<value>'` and ` vcls='<value>'` that follows the closing quote of `msg` removed, and nothing else removed. A message with no evidence key MUST be its own `identity_message`, byte for byte.

## MODIFIED Requirements

### Requirement: Event Granularity of unique_msg Is Extended and Declared (FR13)

`RvErrorLog.unique_msg` MUST be `"{class_full_name}:::{method}:::{spec}:::{error_type}:::{code}:::{event}:::{message}"`
(INV-CORE-25), where `{message}` is the record's message with the evidence keys `vfp` and `vcls` removed (INV-CORE-63). `code` and `event` are the `code=` and `ev=` values of the message envelope the monitor emitted; when the
message carries no envelope — every record produced by the frozen `jca` set, and every record persisted before this
change — both parts MUST be the sentinel `UNSPECIFIED`, never an empty string, so a legacy record has a readable
seven-part key that is distinguishable from an envelope record whose event was named. The `message` part MUST NOT
contain `:::` (INV-CORE-56): the producer forbids it inside every envelope value, the model does not rewrite the
message to hide a violation of that rule, and a reader that finds a part count other than seven counts the record
as unparsed — a separator inside a part makes the key unreadable to every consumer that splits on it.

The evidence keys are removed from the identity because they carry per-object values — a fingerprint of the bytes the monitor could not trace, the classes of a trust-manager array — and a key that included them would make every run of the same misuse a different record, multiplying `unique_errors` and `mop_errors_unique` by the number of distinct values rather than counting misuses. They stay in `message` itself, and therefore in the `message` column of `errors.csv`, which is where an analysis reads them. Removal is exact: the two keys are recognised only in the trailing position the envelope grammar gives them, after `msg`, and a `vfp=` or `vcls=` inside a quoted value is not a key.

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

- **WHEN** an `RvErrorLog` is created with `class_full_name` = `com.example.vault.KeyDeriver`, `method` = `derive`,
  `spec` = `PBEKeySpecSpec`, `error_type` = `ForbiddenMethod`, `code` = `PBEKEYSPEC-FORB-01`, `event` = `f1` and
  `message` = `v=1 code=PBEKEYSPEC-FORB-01 ev=f1 obj=PBEKeySpec val='PBEKeySpec(char[])' exp='PBEKeySpec(char[],byte[],int,int)' msg='forbidden constructor'` (the `<SPEC>` token of a code is the specification name without its `Spec` suffix, upper-cased — `PBEKEYSPEC`, `MESSAGEDIGEST`, `TRUSTMANAGERFACTORY`; list-valued `exp` values are joined with `,`)
- **THEN** `unique_msg` MUST be
  `com.example.vault.KeyDeriver:::derive:::PBEKeySpecSpec:::ForbiddenMethod:::PBEKEYSPEC-FORB-01:::f1:::v=1 code=PBEKEYSPEC-FORB-01 ev=f1 obj=PBEKeySpec val='PBEKeySpec(char[])' exp='PBEKeySpec(char[],byte[],int,int)' msg='forbidden constructor'`
- **AND** splitting it on `:::` MUST yield exactly seven parts, the fifth being `PBEKEYSPEC-FORB-01` and the sixth `f1`

#### Scenario: a legacy `unknown` message yields the sentinels

- **WHEN** an `RvErrorLog` is created from a record of the frozen `jca` set with `class_full_name` = `okio.ByteString`,
  `method` = `digest$okio`, `spec` = `MessageDigestSpec`, `error_type` = `SequenceViolation` and `message` = `unknown`, no envelope present
- **THEN** `code` MUST be `UNSPECIFIED` and `event` MUST be `UNSPECIFIED`
- **AND** `unique_msg` MUST be `okio.ByteString:::digest$okio:::MessageDigestSpec:::SequenceViolation:::UNSPECIFIED:::UNSPECIFIED:::unknown`
- **AND** two such records MUST compare equal and hash equal, so a legacy campaign deduplicates exactly as its records allow

#### Scenario: distinct offending parameters remain distinct events

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

#### Scenario: evidence keys do not split the identity

- **WHEN** two `RvErrorLog` records have the same class, method, spec, error type, code `SECRETKEYSPEC-NOBS-00` and event `c1`, and messages that differ only in `vfp='sha256:1111111111111111'` and `vfp='sha256:2222222222222222'` after `msg`
- **THEN** their `unique_msg` values MUST be equal and end in `msg='…'` with no `vfp`
- **AND** each record's `message` MUST still contain its own `vfp`
- **AND** `unique_errors` MUST count them as 1
