# analysis Delta Specification — Honest Parsing of Logcat Violation Lines

## Purpose

`LogcatParser` (`modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`) is the only place where a violation reported by a woven monitor becomes an `RvErrorLog`. Every downstream count of the thesis — `total_errors`, `unique_errors`, the `errors.csv` a campaign consolidates, the per-event attribution `campaign-analysis` performs — is computed over what this parser returns. Whatever it drops is invisible everywhere; whatever it fabricates looks like data everywhere. This delta makes both impossible to miss: the parser recognises the message envelope the `jca_android` monitors emit, marks the fields it could not read with named sentinels, counts every line it does not turn into a record, and treats an unclosed quote as what it is — a record logcat cut in half.

The producer is the logcat `ErrorCollector` (`rvsec/rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java:36-40`): it writes `ErrorSummary.toString()` followed by `,` and the expecting text, so a violation line is **seven comma-separated fields** — `spec,classQualifiedName,className,methodName,location,errorType,expecting`. Nothing in that path escapes anything, and logcat truncates any payload longer than `LOGGER_ENTRY_MAX_PAYLOAD` (4068 bytes) silently. The parser has always recognised this shape by structure (`len(parts) >= 6`, fields 6 onwards rejoined with `,`), and it keeps doing so: commas inside a message are legal and 27 % of the recorded messages carry one. What changes is the content of the seventh field. In a JCA-family report it is now a versioned envelope, `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'`, whose values are single-quoted with `'` escaped as `\'`, and whose producer contract forbids `\n` and `:::` inside a value — `\n` because logcat splits the line on it, `:::` because it is the separator of `unique_msg`. The parser exposes the envelope's keys as plain optional fields on `RvErrorLog` (`code`, `event`, `obj`, `val`, `exp`, `msg`, plus `truncated`) rather than a typed sub-object: the domain object already carries the six legacy fields, one more level of nesting would be indirection with a single consumer, and `core` composes `unique_msg` from these fields — the parser does not build `unique_msg` and never did.

The three families of loss this delta closes were measured on the recorded corpus. First, silence: ten points between the producer and `errors.csv` drop or rewrite a line without a counter, and the `except Exception` around the file loop returns a partial repository as if it were complete. Second, fabrication: a Format-3 record receives `Unknown Source:1` as its location and a six-field line receives `No additional message` — values that read as measurements and are not. Third, scrambling: a Format-1 line (`… went into an error state.`) whose regex fails falls through into the comma path, and when its prefix bears five commas the parser emits a JCA record whose `spec` is the first fragment of a generic class name. The `generic` and `generic_new` sets are a written non-goal of the change (none of their 145 `.mop` files passes through `ErrorCollector`), so `[helper] ::: ` lines stay unparsed — but they stay **counted**, which is the whole point.

## Data Contracts

### Input

- `line: str` — one raw threadtime logcat line, fed by `parse_logcat_file` (offline / resume) and by `CoverageTracker` (live) in file order (source: `task.result.logcat_file`).
- `message: str` — the text after the `RVSEC` tag of one line; seven comma-separated fields when written by the logcat `ErrorCollector`, one of the two `went into an error state.` shapes when written by a generic monitor (source: `_parse_logcat_line`).

### Output

- `RvErrorLog` — the six legacy fields (`spec`, `error_type`, `class_full_name`, `method`, `source`, `message`) plus the envelope fields `code: str`, `event: str`, `obj: str`, `val: str`, `exp: str`, `msg: str` and the flag `truncated: bool`. `code` and `event` hold the sentinel `UNSPECIFIED` when the message is not an envelope; `obj`/`val`/`exp`/`msg` hold `""` then. `unique_msg` is a computed field owned by `core` (INV-CORE-25/41) and is not assigned by the parser (destination: `LogcatRepository.register_rv_error`, `CoverageTracker`, `result_processor`).
- `ParserDiagnostics` — a counter object carried by the returned `LogcatRepository` as `parser_diagnostics` and shared by the live `CoverageTracker`, with exactly these integer counters: `lines_not_threadtime`, `lines_other_tag`, `format1_regex_failed`, `format2_short`, `format3_unresolved`, `unrecognised`, `continuation_lines`, `truncated_envelopes`, `sentinel_error_type`, `sentinel_source`, `sentinel_code`, `sentinel_event`, `envelope_forbidden_chars` (destination: `result_processor`, offline analysis scripts, tests).

### Side-Effects

- **[Logging]**: every counted discard is logged at WARNING with the line number and the counter name; a re-raised file-level exception is logged at ERROR with the line number before propagating. No filesystem or device access beyond reading the logcat.

### Error

- Any exception raised while iterating the file inside `parse_logcat_file` — after being logged with the 1-based line number at which it occurred, it is re-raised to the caller. A partially populated repository MUST NOT be returned in its place: a caller that receives a repository is entitled to read its counts as the counts of the whole file.

## Invariants

- **INV-ANA-08** (restated, replacing the entry of the same number): The `LogcatParser` MUST support three error message formats and MUST recognise each by structure, in this order: Format 1, the generic format with source location (`class.method(file:line) ::: Spec went into an error state.`), selected by the suffix `went into an error state.` and parsed by its regex — a line that carries the suffix but fails the regex MUST be counted under `format1_regex_failed` and dropped, never re-tried as Format 2; Format 2, the JCA format written by the logcat `ErrorCollector` as seven comma-separated fields `spec,classQualifiedName,className,methodName,location,errorType,expecting`, recognised when `len(message.split(",")) >= 6`, with fields 6 onwards rejoined with `,` into `message` (commas inside a message are legal); Format 3, the FSM format (`class.method():::Spec went into an error state.`), recognised by `:::`. When the Format-2 message is an envelope `v=1 code=… ev=… obj=… val='…' exp='…' msg='…'`, the parser MUST expose its keys as `code`, `event`, `obj`, `val`, `exp`, `msg` on `RvErrorLog`, unescaping `\'` to `'`. Fabricated values MUST NOT be emitted: an empty `errorType` becomes `error_type=UNSPECIFIED`, an empty or absent location becomes `source=UNSPECIFIED:0` (Format 3 no longer receives `Unknown Source:1`), a message that is not an envelope yields `code=UNSPECIFIED` and `event=UNSPECIFIED`, and each use of a sentinel is counted. A message matching no format MUST return `None`, be logged, and be counted under `unrecognised`.

- **INV-ANA-62**: No logcat line MUST be discarded silently. For every line `parse_logcat_file` or `CoverageTracker` reads that does not become an `RvErrorLog`, an `RvCoverageLog` or a diagnostic-block line, exactly one counter of `ParserDiagnostics` MUST be incremented — `lines_not_threadtime`, `lines_other_tag`, `format1_regex_failed`, `format2_short`, `format3_unresolved`, `unrecognised` or `continuation_lines` — and every value the parser substitutes for a value the producer did not supply MUST be counted under the matching `sentinel_*` counter. `parse_logcat_file` MUST NOT catch an exception raised while iterating the file and return the repository built so far; it MUST log the line number and re-raise. The sum of records registered plus lines counted MUST equal the number of lines read.

- **INV-ANA-63**: An envelope whose last quoted value is not closed MUST be treated as a truncated record: `truncated=True`, the record registered and counted under `truncated_envelopes`, and no field parsed from the unclosed value onwards (the fields before it are kept). Logcat cuts a payload at `LOGGER_ENTRY_MAX_PAYLOAD` (4068 bytes) without a marker and a `\n` inside a value ends the line at that byte, so an unclosed quote is the only evidence the parser has that the record it holds is not the record the monitor wrote. A value containing `:::` MUST be kept verbatim, the record registered, and `envelope_forbidden_chars` incremented — the producer contract, not the parser, forbids the character.

## MODIFIED Requirements

### Requirement: Specification Violation Detection (FR13)

The system MUST detect and record violations of MOP specifications (RV errors) reported via logcat during test execution. Violations are logged by the runtime monitors woven into the instrumented APK, using the `RVSEC` logcat tag. The `CoverageTracker` detects these violations in real-time and logs them immediately.

Three error message formats are supported by the `LogcatParser`, tried in this order and each recognised by structure (INV-ANA-08):

1. **Generic format with source location (Format 1)**: `class.method(file:line) ::: Spec went into an error state.` -- Selected by the suffix `went into an error state.` and parsed by the regex `(.*)\.(.*)\((.*):(.*)\) ::: (.*) went into an error state.`. Example: `com.example.IO.read(IO.java:42) ::: InputStream_ManipulateAfterClose went into an error state.` A line carrying the suffix whose regex fails MUST be counted under `format1_regex_failed` and dropped; it MUST NOT fall through into the comma split, because a generic class or method name bearing five commas would otherwise be scrambled into a JCA record whose `spec` is a fragment of that name.

2. **JCA format (Format 2)**: seven comma-separated fields `spec,classQualifiedName,className,methodName,location,errorType,expecting`, exactly as the logcat `ErrorCollector` writes `ErrorSummary.toString()` followed by `,` and the expecting text -- Recognised when `len(message.split(",")) >= 6`; fields 6 onwards are rejoined with `,` into `message`, since commas inside a message are legal. Field 3 (`className`) is redundant with field 2 and is not stored. Example: `CipherSpec,com.example.Crypto,Crypto,doEncrypt,Crypto.java:15,MISUSE,Using weak algorithm DES`. When `message` is a **v1 envelope** — `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'`, values single-quoted with `'` escaped as `\'` — the parser MUST fill `code`, `event`, `obj`, `val`, `exp`, `msg` on `RvErrorLog` (plain optional string fields; no sub-object) and MUST treat an unclosed final quote as truncation (INV-ANA-63). A `message` that is not an envelope (the legacy `unknown`, a free-text expecting, a pre-change corpus) MUST yield `code=UNSPECIFIED`, `event=UNSPECIFIED`, and empty `obj`/`val`/`exp`/`msg`, counting `sentinel_code` and `sentinel_event`; an envelope whose `code=` or `ev=` value is itself the literal `UNSPECIFIED` — the collector's `null` guard — MUST count under the same counters, since the value is a sentinel whoever wrote it. An empty field 6 MUST yield `error_type=UNSPECIFIED` (counting `sentinel_error_type`); an empty field 5 MUST yield `source=UNSPECIFIED:0` (counting `sentinel_source`); an empty seventh field MUST yield `message=""`, never `No additional message`. A message that carries between one and four commas, no `:::` and no Format-1 suffix MUST be counted under `format2_short` and dropped — the shape logcat leaves when it cuts a payload before its sixth comma.

3. **FSM format (Format 3)**: `class.method():::Spec went into an error state.` -- Recognised by `:::`; class and method are split at the last `.` before `(`. Example: `java.util.Iterator.next():::HasNext went into an error state.` The record's `source` MUST be the sentinel `UNSPECIFIED:0` (counting `sentinel_source`), never `Unknown Source:1`. A `:::` line whose left part has no `.` — the `[helper] ::: ` lines of `generic_new`, a written non-goal of gh104 — MUST be counted under `format3_unresolved` and dropped.

A message matching none of the three MUST be logged, return `None` and be counted under `unrecognised`; a message that matches none of the three **and** immediately follows, from the same `(pid, tid)`, an `RVSEC` record flagged `truncated` MUST instead be counted under `continuation_lines` — it is the second half of a payload logcat split on a `\n` the producer contract forbids. Lines that do not match the threadtime format are counted under `lines_not_threadtime`; threadtime lines under a tag that is neither `RVSEC`, `RVSEC-COV` nor a diagnostic tag are counted under `lines_other_tag`. The counters live in a `ParserDiagnostics` object carried by the returned `LogcatRepository` and shared by the live `CoverageTracker`; no line is dropped without incrementing exactly one of them (INV-ANA-62). `parse_logcat_file` MUST NOT swallow an exception raised while iterating the file: it logs the 1-based line number and re-raises, so a caller never mistakes a partial repository for a complete one.

Each parsed error produces an `RvErrorLog` with `spec`, `error_type`, `class_full_name`, `method`, `source`, `message`, `code`, `event`, `obj`, `val`, `exp`, `msg` and `truncated`. The `LogcatRepository` stores all registered errors and provides deduplication via the `unique_msg` computed field, which `core` composes from the record's fields (INV-CORE-25/41); the parser MUST NOT assemble `unique_msg` itself.

In the ICST study, the top 4 violation classes (SSLContextSpec, MessageDigestSpec, CipherSpec, SecretKeySpecSpec) accounted for 78% of 230 unique violations. 33.91% originated from application code; the rest from external libraries. In the published dataset 72.93 % of the 97,018 records carry the literal `unknown` as their message; those records now surface as `code=UNSPECIFIED` with `sentinel_code` counted, rather than as a message that looks like text.

#### Scenario: JCA envelope parsing with commas inside a value

- **WHEN** a logcat line contains `RVSEC: TrustManagerFactorySpec,okhttp3.internal.tls.X,X,get,X.java:12,UnsafeAlgorithm,v=1 code=TMF-ALG-01 ev=g3 obj=TrustManagerFactory val='X509' exp='PKIX,SunX509' msg='expecting one of PKIX,SunX509 but found X509'`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `spec=TrustManagerFactorySpec`, `class_full_name=okhttp3.internal.tls.X`, `method=get`, `source=X.java:12`, `error_type=UnsafeAlgorithm`
- **AND** `code=TMF-ALG-01`, `event=g3`, `obj=TrustManagerFactory`, `val=X509`, `exp=PKIX,SunX509`, `msg=expecting one of PKIX,SunX509 but found X509`, `truncated=False`
- **AND** `message` MUST be the whole envelope from `v=1` to the closing `'`, the commas inside `exp` and `msg` preserved
- **AND** no `sentinel_*` counter MUST be incremented

#### Scenario: Unclosed quote is a truncated record

- **WHEN** a logcat line contains `RVSEC: CipherSpec,com.example.Crypto,Crypto,doEncrypt,Crypto.java:15,UnsafeAlgorithm,v=1 code=CIPHER-ALG-02 ev=c1 obj=Cipher val='AES/ECB/PKCS5Padding' exp='AES/GCM/NoPadding,AES/CBC/PKCS7Pad` and no closing `'` follows before end of line
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `truncated=True`, `code=CIPHER-ALG-02`, `event=c1`, `obj=Cipher`, `val=AES/ECB/PKCS5Padding`
- **AND** `exp` and `msg` MUST be `""` — the unclosed value MUST NOT be parsed as a valid value
- **AND** the record MUST be registered and `truncated_envelopes` MUST be incremented by 1

#### Scenario: Legacy `unknown` message receives sentinels, not text

- **WHEN** a logcat line contains `RVSEC: MessageDigestSpec,com.example.Hash,Hash,digest,Hash.java:40,UnsafeAlgorithm,unknown`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `message=unknown`, `code=UNSPECIFIED`, `event=UNSPECIFIED`, `obj=""`, `val=""`, `exp=""`, `msg=""`, `truncated=False`
- **AND** `sentinel_code` and `sentinel_event` MUST each be incremented by 1
- **AND** `error_type=UnsafeAlgorithm` and `source=Hash.java:40` MUST be kept as written, with `sentinel_error_type` and `sentinel_source` unchanged

#### Scenario: Format-1 line with a comma-bearing prefix and a failing regex is counted, not scrambled

- **WHEN** a logcat line contains `RVSEC: com.example.Svc.call(a,b,c,d,e,f) ::: HasNext went into an error state.` — the suffix selects Format 1, the parenthesised group carries no `file:line` colon so the regex fails, and the prefix bears five commas
- **THEN** `parse_logcat_line()` MUST return `(None, None)`
- **AND** `format1_regex_failed` MUST be incremented by 1
- **AND** no `RvErrorLog` with `spec=com.example.Svc.call(a` MUST be produced

#### Scenario: Property test over the characters the envelope grammar constrains

- **WHEN** a property test generates envelopes whose `val`, `exp` and `msg` values contain, in any combination, `,`, an escaped `\'`, and `:::`, and whose total payload is optionally cut at 4068 bytes or split at a `\n` inserted inside a value, and writes each as one or two `RVSEC` threadtime lines
- **THEN** for every uncut, unsplit envelope the parsed `val`/`exp`/`msg` MUST equal the generated values byte-for-byte after unescaping, and every `,` inside a value MUST survive
- **AND** every payload cut at 4068 bytes inside a quoted value MUST yield `truncated=True` and increment `truncated_envelopes` by exactly 1
- **AND** every payload split at a `\n` MUST yield one record with `truncated=True` for the first line and increment `continuation_lines` by 1 for the second line, and MUST NOT yield a second `RvErrorLog`
- **AND** every value containing `:::` MUST be kept verbatim on the record and increment `envelope_forbidden_chars` by 1
- **AND** for the whole generated file, records registered plus counted lines MUST equal lines read (INV-ANA-62)

#### Scenario: Empty fields receive sentinels

- **WHEN** a logcat line contains `RVSEC: SecretKeySpecSpec,com.example.K,K,make,,,`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `error_type=UNSPECIFIED`, `source=UNSPECIFIED:0`, `message=""`, `code=UNSPECIFIED`, `event=UNSPECIFIED`
- **AND** `sentinel_error_type`, `sentinel_source`, `sentinel_code` and `sentinel_event` MUST each be incremented by 1
- **AND** the string `No additional message` MUST NOT appear in any field

#### Scenario: FSM error format parsing

- **WHEN** a logcat line contains `RVSEC: java.util.Iterator.next():::HasNext went into an error state.`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `spec=HasNext`, `class_full_name=java.util.Iterator`, `method=next`, `source=UNSPECIFIED:0`
- **AND** `sentinel_source` MUST be incremented by 1

#### Scenario: Generic error format parsing

- **WHEN** a logcat line contains `RVSEC: com.example.IO.read(IO.java:42) ::: InputStream_ManipulateAfterClose went into an error state.`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `spec=InputStream_ManipulateAfterClose`, `class_full_name=com.example.IO`, `method=read`, `source=IO.java`

#### Scenario: `generic_new` helper lines are counted, not parsed

- **WHEN** a logcat line contains `RVSEC: [helper] ::: Iterator_HasNext went into an error state.`
- **THEN** `parse_logcat_line()` MUST return `(None, None)`
- **AND** `format3_unresolved` MUST be incremented by 1

#### Scenario: MOP error detection and registration

- **WHEN** CoverageTracker processes a logcat line that yields an RvErrorLog
- **THEN** the error MUST be registered in LogcatRepository via register_rv_error()
- **AND** a log entry MUST be emitted with spec, error_type, class_full_name, method, message, code, event and time_since_task_start

#### Scenario: Malformed error message handling

- **WHEN** a logcat line contains `RVSEC: some malformed message that does not match any format`
- **THEN** _parse_error_message() MUST log a warning
- **AND** MUST return None (not a malformed RvErrorLog)
- **AND** `unrecognised` MUST be incremented by 1
- **AND** CoverageTracker MUST NOT register any error

#### Scenario: A file-level exception is re-raised with the line number

- **WHEN** `parse_logcat_file(path, static_data)` reads a file whose line 1,203 raises `UnicodeDecodeError` inside the loop
- **THEN** the exception MUST be logged at ERROR naming line 1203 and re-raised to the caller
- **AND** no `LogcatRepository` MUST be returned for that call

#### Scenario: Logcat timestamp to datetime conversion with year handling

- **WHEN** a logcat line has date `12-31` and is parsed in January of the following year
- **THEN** _convert_to_datetime() MUST attribute the log to the previous year
- **AND** all other months MUST use the current year
