# campaign-analysis Delta Specification — Violation Readers Read the Envelope and the 13-Column Header

## Purpose

`analysis/violations.py` and the shipped reader `clock_logcat_join.py` (both under `modules/aperv-tool/src/aperv_tool/analysis/`) are the Layer-3 readers through which every violation of a campaign enters the library: `read_errors_csv` reads the consolidated `errors.csv` rv-platform writes, `read_logcat` / `parse_payload` decompose the `RVSEC` lines of a retained `.logcat`, and `clock_logcat_join` places the same payloads on the step clock. Layer 3 is where a change in the log format is meant to land and stop, and gh104 changes the log format twice: the seventh field of a `jca_android` report is now a versioned envelope `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'`, and `errors.csv` gains the columns `code` and `event` — with `unique_msg` growing to seven `:::` parts — so that per-event attribution, impossible on the published dataset, becomes a column read rather than a regex over free text.

This delta keeps the two rules that already govern the module and extends them to the fields it can now see. First, a header is a contract: `ERRORS_CSV_HEADER` is declared exactly as rv-platform writes it and any other header raises `ValueError`, because a silently renamed or missing column is worse than a stopped read — every downstream count would be computed over a column that is no longer what it says. The 10-column article dataset and the 11-column pre-change layout are therefore both rejected here; the E0 baseline of gh104 needs the historical layouts and reads them through a **declared separate reader** in the E0 baseline scripts, outside this module, so that the library never grows a compatibility branch that turns a header mismatch back into a guess. Second, nothing is dropped silently (INV-CAN-04): a `unique_msg` that does not split into seven parts, a payload whose envelope is malformed, and a payload whose last quote is unclosed — logcat truncates at 4068 bytes without a marker — are each kept as an event and each counted under a named counter, because the line is still a violation and the count is the gate.

The fixture rule is unchanged: cmp162 is a fixture, not a corpus. Its `errors.csv` files carry the 11-column pre-change layout and its `.logcat` messages are free text, so after this change they are read through the E0 baseline reader for parity and through synthetic fixtures for correctness; no number computed on them answers a research question.

## Data Contracts

### Input

- `errors.csv` — rv-platform's consolidated violation record, header exactly `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg` (13 columns; source: `result_processor`, platform INV-PLT-19 as revised by gh104). Read-only.
- `<apk>__<rep>__<timeout>__<arm>.logcat` — per-run raw logcat; only lines under the `RVSEC` tag are read, their payload being the seven comma-separated fields `spec,classQualifiedName,className,methodName,location,errorType,expecting` written by the logcat `ErrorCollector` (source: the run's retained logcat). Read-only.
- `payload: str` — the text after the tag of one `RVSEC` line, never the whole line (source: `read_tagged_lines`).

### Output

- `ViolationEvent` (frozen dataclass) — `spec`, `class_name`, `simple_class`, `method`, `location`, `violation_type`, `message` as today, plus `code`, `event`, `obj`, `val`, `exp`, `msg` parsed from the envelope in `message` (`""` when the message is not an envelope), and `shape_ok: bool` — `False` when the payload did not decompose into seven comma fields **or** when its envelope is malformed or truncated (destination: `frame`, `distinct`, `step_bundle`, `clock_logcat_join`).
- `LogcatDiagnostics` — returned by `read_logcat` beside the event list: `lines`, `shape_bad`, `envelope_malformed`, `envelope_truncated` (destination: gates, envelopes' `exclusions`).
- `pandas.DataFrame` from `read_errors_csv` — the CSV's columns with `time` renamed `violation_time_s`, plus `violation_type`, `code`, `event`, `unique_message` recovered from `unique_msg` (destination: outcome builders).
- `CsvDiagnostics` — the object `read_errors_csv` already returns beside the frame as `(rows, CsvDiagnostics)`, extended with `unique_msg_unparsed` and `unique_msg_disagrees` (the CSV's own `code`/`event` columns differ from the parts of `unique_msg` on the same row) beside its existing `rows` (destination: gates, envelopes' `exclusions`).

### Side-Effects

- **[Filesystem]**: none on inputs (INV-APV-35, INV-CAN-23). Nothing is written.
- **[Device]**: none.

### Error

- `ValueError` — `read_errors_csv` finds a header other than `ERRORS_CSV_HEADER`; the message names the file, the header found and the header expected. A 10-column article file and an 11-column pre-change file both raise it.
- `OSError` — the file cannot be read; a run with no logcat is the caller's to report.

## Invariants

- **INV-CAN-04** (restated, replacing the entry of the same number): No loader or reader SHALL silently drop a run, a record or a line. Every omission SHALL be counted and surfaced in the returned diagnostics. For the violation readers this means: a `unique_msg` that does not split into exactly seven `:::` parts is kept and counted under `unique_msg_unparsed`; a `unique_msg` whose `code`/`event` parts differ from the CSV columns of the same name is kept and counted under `unique_msg_disagrees`; an `RVSEC` payload with fewer than seven comma fields is kept whole in `message` and counted under `shape_bad`; a payload whose envelope does not match the v1 grammar is kept and counted under `envelope_malformed`; a payload whose last quoted value is unclosed is kept, its parsed fields stopping before that value, and counted under `envelope_truncated`. A read that returns events SHALL return the counters with them.

- **INV-CAN-25**: `ERRORS_CSV_HEADER` SHALL be the 13-tuple `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg` and `read_errors_csv` SHALL raise `ValueError` on any other header, naming the header expected. No reader under `analysis/` SHALL accept a historical `errors.csv` layout; a reader for the 10-column article dataset or the 11-column pre-change layout SHALL live outside the module, in the E0 baseline scripts, and SHALL be declared where its numbers are published.

- **INV-CAN-26**: `unique_msg` SHALL be read as exactly seven `:::`-joined parts in the order `class, method, spec, error_type, code, event, message`, with `violation_type = parts[3]`, `code = parts[4]`, `event = parts[5]`, `unique_message = parts[6]`; the module SHALL NOT compose a `unique_msg` itself — `core` owns its construction (INV-CORE-25/41) — and SHALL NOT infer a part count from the corpus.

## ADDED Requirements

### Requirement: Violation Readers Read the Envelope and the Consolidated Header (FR14, NFR06, NFR08)

`analysis/violations.py` SHALL declare `ERRORS_CSV_HEADER` as the 13-column header rv-platform writes after gh104 (INV-CAN-25) and `read_errors_csv(path)` SHALL raise `ValueError` on any other header, naming the header found and the header expected. It SHALL recover `violation_type`, `code`, `event` and `unique_message` from `unique_msg` split into exactly seven `:::` parts (INV-CAN-26); any other part count SHALL leave the four columns `""` — `unique_message` holding the raw `unique_msg` — and increment `unique_msg_unparsed` on the `CsvDiagnostics` the function already returns as the second element of its `(rows, CsvDiagnostics)` result, which gains the two counters rather than being introduced; a row whose recovered `code`/`event` differ from the CSV's `code`/`event` columns SHALL be kept and increment `unique_msg_disagrees`, because both are written by the same producer from the same object and a disagreement is a transport defect worth a number, not a choice the reader makes silently.

`parse_payload(payload)` SHALL split on `,` at most six times, so the seventh field keeps its commas, and SHALL then parse the seventh field as a v1 envelope: `v=1 code=… ev=… obj=… val='…' exp='…' msg='…'`, values single-quoted with `\'` as the escape, filling `code`, `event`, `obj`, `val`, `exp`, `msg` on `ViolationEvent`. When the seventh field is not an envelope (a legacy `unknown`, a free-text `expecting`, a cmp162 message) the six fields SHALL be `""` and `shape_ok` unaffected — a pre-change message is a legitimate shape, not a defect. When the envelope starts with `v=1` but does not match the grammar, or when its last quoted value is unclosed, `shape_ok` SHALL be `False`, the seven comma fields SHALL still be populated, the envelope fields parsed before the failure SHALL be kept, and `read_logcat` SHALL count the event under `envelope_malformed` or `envelope_truncated` respectively; `read_logcat` SHALL return `(events, LogcatDiagnostics)`. `clock_logcat_join` SHALL obtain `(spec, violation_type, message)` through the same `parse_payload`, so the two readers cannot disagree on a payload's shape.

The historical layouts are not this module's concern: the 10-column article dataset and the 11-column pre-change layout are read by a declared separate reader in the E0 baseline scripts. cmp162 remains a fixture, not a corpus.

#### Scenario: 13-column header is accepted

- **WHEN** `read_errors_csv` opens a file whose header is `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg` and whose one row has `unique_msg=okio.ByteString:::digest$okio:::MessageDigestSpec:::UnsafeAlgorithm:::MESSAGEDIGEST-ALG-01:::update:::v=1 code=MESSAGEDIGEST-ALG-01 ev=update obj=MessageDigest val='MD2' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384' msg='expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found MD2'`, `code=MESSAGEDIGEST-ALG-01`, `event=update`
- **THEN** the frame SHALL have one row with `violation_type=UnsafeAlgorithm`, `code=MESSAGEDIGEST-ALG-01`, `event=update`, `unique_message` equal to the envelope text, and `violation_time_s` from `time`
- **AND** `CsvDiagnostics` SHALL be `rows=1, unique_msg_unparsed=0, unique_msg_disagrees=0`

#### Scenario: 11-column pre-change header is rejected by name

- **WHEN** `read_errors_csv` opens a cmp162 `errors.csv` whose header is `apk,rep,timeout,tool,time,spec,class,method,source,message,unique_msg`
- **THEN** it SHALL raise `ValueError` whose message contains the path, the 11-column header found and the text `expected ['apk', 'rep', 'timeout', 'tool', 'time', 'spec', 'class', 'method', 'source', 'code', 'event', 'message', 'unique_msg']`
- **AND** no frame SHALL be returned; a 10-column article file SHALL raise the same error

#### Scenario: A five-part `unique_msg` is counted unparsed

- **WHEN** a row of a 13-column file carries `unique_msg=com.example.Hash:::digest:::MessageDigestSpec:::UnsafeAlgorithm:::unknown` (five parts) and `code=UNSPECIFIED`, `event=UNSPECIFIED`
- **THEN** the row SHALL be kept with `violation_type=""`, `code=""`, `event=""` and `unique_message` equal to the raw five-part string
- **AND** `unique_msg_unparsed` SHALL be 1 and `unique_msg_disagrees` SHALL be 0

#### Scenario: A truncated envelope is kept with `shape_ok=False` and counted

- **WHEN** `read_logcat` reads a run whose logcat carries the `RVSEC` payload `CipherSpec,com.example.Crypto,Crypto,doEncrypt,Crypto.java:15,UnsafeAlgorithm,v=1 code=CIPHER-ALG-02 ev=c1 obj=Cipher val='AES/ECB/PKCS5Padding' exp='AES/GCM/NoPadding,AES/CBC/PKCS7Pad` with no closing `'`
- **THEN** the returned event SHALL have `spec=CipherSpec`, `class_name=com.example.Crypto`, `simple_class=Crypto`, `method=doEncrypt`, `location=Crypto.java:15`, `violation_type=UnsafeAlgorithm`, `code=CIPHER-ALG-02`, `event=c1`, `obj=Cipher`, `val=AES/ECB/PKCS5Padding`, `exp=""`, `msg=""`, `shape_ok=False`
- **AND** `LogcatDiagnostics` SHALL be `lines=1, shape_bad=0, envelope_malformed=0, envelope_truncated=1`
- **AND** `distinct(events, key=("class_name", "method", "spec"))` SHALL count the event

#### Scenario: A pre-change free-text message is not a defect

- **WHEN** `parse_payload("SSLContextSpec,com.example.Net,Net,open,Net.java:9,UnsafeProtocol,expecting one of TLSv1.2, TLSv1.3 but found SSLv3")` is called
- **THEN** the event SHALL have `message=expecting one of TLSv1.2, TLSv1.3 but found SSLv3` with its comma, `code=""`, `event=""`, `shape_ok=True`
- **AND** `envelope_malformed` SHALL NOT be incremented for it

#### Scenario: A short payload is kept whole and counted

- **WHEN** `parse_payload("SSLContextSpec,com.example.Net,Net")` is called
- **THEN** the event SHALL have `spec=SSLContextSpec`, `message=SSLContextSpec,com.example.Net,Net`, `shape_ok=False`
- **AND** `read_logcat` SHALL count it under `shape_bad`

## MODIFIED Requirements

### Requirement: Step Bundle Places Every Logcat Stream on the Step Timeline (FR11, FR13)

`analysis/step_bundle.py` SHALL return one `StepBundle` per step: the `StepRow` plus `violations[]` (`RVSEC`), `monitored_ops[]` (`RVSEC-COV`) and `diagnostics[]` (the `RV_LOGCAT_DIAGNOSTICS` tags, via `rv_coverage`'s diagnostic parser) placed by the same heartbeat rule `clock_logcat_join` uses (INV-CAN-18), plus the per-state `UICOV` payload joined by `state_key` through `state_coverage_join.py` (intra-run only). It SHALL report the heartbeat⇄step discrepancy as a count — on cmp162, 15,701 heartbeats for 15,702 steps over 60 runs — and SHALL treat a run with no heartbeat as `UNALIGNED`, never repaired. It is intra-`aperv` by construction: `ape` and `droidbot` emit no NDJSON. The `violations[]` of a bundle SHALL be `ViolationEvent`s produced by `violations.parse_payload`, and `clock_logcat_join` SHALL decompose its `RVSEC` payloads through the same function, so the `code`, `event` and `shape_ok` of an event are the same on the step timeline, in the run join and in the event frame; a bundle SHALL carry the run's `LogcatDiagnostics` counters (`shape_bad`, `envelope_malformed`, `envelope_truncated`) beside its heartbeat gap.

#### Scenario: RVSEC-COV lines reach the bundle
- **WHEN** a run's logcat carries heartbeats and `RVSEC-COV` lines between heartbeat 7 and heartbeat 8
- **THEN** those lines SHALL appear in step 7's `monitored_ops[]` with their signatures intact
- **AND** `clock_logcat_join`'s `RunJoin` output for the same run SHALL be unchanged

#### Scenario: Heartbeat gap is a number
- **WHEN** a run has 262 steps and 261 heartbeats
- **THEN** the bundle report SHALL state `heartbeat_gap=1` and name the step without one
- **AND** that step's events SHALL be attributed to the previous heartbeat with a flag, not dropped

#### Scenario: UICOV joins totally by state key within a run
- **WHEN** the run's teardown dump carries `UICOV state=<key>` lines
- **THEN** every `STATE.key` in the trace SHALL find at most one row and every UICOV row SHALL find its key (measured 3801/3801 on 120 cmp162 runs)
- **AND** the joined `discovered/interacted/byType` SHALL be flagged cumulative-per-run, never per-visit

#### Scenario: One payload parser on the step timeline and in the run join
- **WHEN** a run's logcat carries, between heartbeat 3 and heartbeat 4, the `RVSEC` payload `MessageDigestSpec,okio.ByteString,ByteString,digest$okio,ByteString.kt:12,UnsafeAlgorithm,v=1 code=MESSAGEDIGEST-ALG-01 ev=update obj=MessageDigest val='MD2' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384' msg='expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found MD2'`
- **THEN** step 3's `violations[]` SHALL hold one `ViolationEvent` with `code=MESSAGEDIGEST-ALG-01`, `event=update`, `shape_ok=True`
- **AND** `clock_logcat_join.join_run` SHALL report the same event at step 3 with `violation_type=UnsafeAlgorithm` and the full envelope as `message`
- **AND** the bundle's diagnostics SHALL read `envelope_malformed=0, envelope_truncated=0`
