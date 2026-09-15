## Purpose

This delta teaches the logcat parser (`modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`) the two evidence keys that `jca_android` appends to non-observation envelopes, `vfp` and `vcls`, and states what it does with the new label codes of the same set: nothing specific.

`_parse_envelope` (`:376-429`) already accepts any `key=value` pair, and `_apply_envelope` (`:462-495`) copies only `code`, `ev`, `obj`, `val`, `exp` and `msg` onto the record, so the evidence keys survive only inside `message`. An analysis that wants them would have to re-parse the message. The parser therefore copies them onto two new record fields. The codes need no parser change: codes are opaque strings to every module under `modules/*/src` (no module keeps a list of families), and the label codes are new numbers inside the existing `-NOBS-` and `-ORDER-` families, so a reader that separates families keeps separating them correctly. What a label means is read from `codes.csv`, not from the parser.

## Data Contracts

### Input
- `RVSEC` logcat line whose seventh field is a v1 envelope, optionally ending in ` vfp='…'` and ` vcls='…'`

### Output
- `RvErrorLog.value_fingerprint: str` — the `vfp` value, `""` when absent
- `RvErrorLog.value_class: str` — the `vcls` value, `""` when absent
- `RvErrorLog.message` — unchanged, the whole envelope including the evidence keys

### Side-Effects
- None beyond the existing counters; an evidence value containing `:::` increments `envelope_forbidden_chars` exactly as any other value does (INV-ANA-63)

### Error
- None; a malformed evidence value follows the existing truncation rules

## Invariants

- **INV-ANA-72**: `_apply_envelope` MUST copy `vfp` into `RvErrorLog.value_fingerprint` and `vcls` into `RvErrorLog.value_class`, and MUST leave both `""` when the key is absent. The parser MUST NOT interpret, validate or classify either value, and MUST NOT branch on the family or label of `code`.

## ADDED Requirements

### Requirement: Evidence Keys Are Parsed into Their Own Record Fields

The parser SHALL copy the evidence keys of a v1 envelope into dedicated fields of `RvErrorLog` (INV-ANA-72) and SHALL keep `message` verbatim, so the same record serves both the identity rule of `core` (which removes the keys from `unique_msg`) and an analysis that reads the evidence. A record whose envelope has no evidence key gets empty fields and is otherwise identical to what the parser produces today; no counter moves for it.

#### Scenario: a non-observation envelope with a trust-manager class

- **WHEN** a logcat line contains `RVSEC: SSLContextSpec,okhttp3.internal.platform.Platform,Platform,newSslSocketFactory,Platform.kt:168,UnsatisfiedConstraint,v=1 code=SSLCONTEXT-NOBS-06 ev=init obj=SSLContext val='' exp='trust managers issued by a TrustManagerFactory' msg='a trust manager of an application class was passed to SSLContext.init' vcls='com.example.TrustAll'`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `code=SSLCONTEXT-NOBS-06`, `event=init`, `value_fingerprint=""` and `value_class=com.example.TrustAll`
- **AND** `message` MUST be the whole envelope from `v=1` to the closing `'` of `vcls`
- **AND** no `sentinel_*` counter MUST be incremented

#### Scenario: an envelope without evidence is unchanged

- **WHEN** a logcat line carries `v=1 code=MESSAGEDIGEST-ALG-01 ev=update obj=MessageDigest val='MD2' exp='SHA-256' msg='expecting one of SHA-256 but found MD2'`
- **THEN** `value_fingerprint` and `value_class` MUST be `""`
- **AND** every other field and counter MUST be what the parser produced before this requirement

#### Scenario: a label code is an ordinary code

- **WHEN** a record carries `code=KEYPAIR-ORDER-01`
- **THEN** the parser MUST store it verbatim in `code`
- **AND** no parser branch MUST depend on the suffix `-01` or on the family `ORDER`
