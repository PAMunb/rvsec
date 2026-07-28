# Analysis — delta for gh89-error-description-key

## Purpose

The analysis domain turns raw logcat text into the structured violation records every
downstream count is computed from. `LogcatParser` (`modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`)
reads each `RVSEC`-tagged line and produces an `RvErrorLog` naming the class and the method
where a specification was violated. Those two fields, together with the APK name and the
specification name, form the `(apk, class, method, spec)` key that identifies a *unique
misuse* — the unit of analysis for the thesis and for the ICST/journal studies.

This delta closes a path by which a **source position** enters that key. The JCA message
format (Format 2) is a comma-separated line produced by the Java monitor
(`ErrorSummary.toString()` = `spec,class,className,method,location,error`), and the parser
binds `parts[1]` and `parts[3]` to class and method verbatim. When the Java side fails to
split a stack frame — which it does for every method name containing `$`, `-` or a space —
both fields carry the whole frame, `pkg.Class.method(File.ext:NN)` included. The parser has
no defense and copies the corruption into the record, so the line number silently becomes
part of the identity of the misuse and one misuse is counted once per line it occurs at.

The parser must be defensive here even though the defect originates upstream, for a reason
that is specific to how RV-Android is deployed: **an APK is instrumented once and replayed
many times**. Every APK already instrumented with the current monitor jar keeps emitting the
corrupted form no matter what the Java does afterwards, and re-instrumenting an entire
campaign is far more expensive than normalizing at parse time. The normalization is therefore
not a duplicate of the upstream repair — it is the only thing that protects data produced from
existing artifacts.

Normalization is defined so that it can never damage a well-formed record: it fires only when
a value *ends with* a `(<file>:<line>)` group, and a value that does not is returned
byte-identical. The suffix anchor matters. Two real Kotlin backtick test names in the observed
corpus contain nested parentheses inside the method name itself
(`V2-header files (3xx format) are still decryptable…`), so a guard anchored on the shape of
the prefix — for instance requiring a dotted fully-qualified path before the parenthesis —
matches only about half of the real malformed values. The prefix must be unconstrained and only
the trailing group tested.

## Data Contracts

### Input
- `message: str` — the message portion of an `RVSEC`-tagged logcat line, produced by the
  instrumented APK's `ErrorCollector` (`spec,class,className,method,location,error[,expecting]`
  for the JCA format).

### Output
- `RvErrorLog.class_full_name: str` — fully-qualified class name, never containing a source
  position; consumed by `CoverageTracker`, `LogcatRepository`, and `errors.csv`.
- `RvErrorLog.method: str` — bare method name, never containing a source position; may contain
  `$`, `-`, spaces and angle brackets (`<init>`, `<clinit>`).
- `RvErrorLog.source: str` — the source location recovered from the frame (`File.ext:NN`) or
  the value the emitter supplied; never part of the uniqueness key.

### Side-Effects
- **[Logging]**: when a frame-form value is normalized, the parser emits a debug-level log
  recording the original and the corrected pair, so a campaign run against APKs instrumented
  with the old jar is auditable after the fact.

### Error
- None added. Values that match no known format continue to produce a warning and `None`, as
  today.

## Invariants

- **INV-ANA-50**: `parse_logcat_line` MUST NOT return an `RvErrorLog` whose `class_full_name`
  or `method` ends with a `(<file>:<line>)` group. Any such value present in the emitted
  message MUST be normalized before the record is constructed.
- **INV-ANA-51**: Normalization MUST be idempotent and MUST be a no-op on well-formed values:
  for any value `v` that does not end with a `(<file>:<line>)` group, `normalize(v) == v`
  byte-for-byte, and for any value at all, `normalize(normalize(v)) == normalize(v)`.
- **INV-ANA-52**: The normalization guard MUST be anchored on the trailing group only. It MUST
  NOT constrain the prefix, because real method names in the corpus contain spaces and nested
  parentheses. Verified by the corner-case corpus, which includes
  `…CryptoMigrationV2CompatibilityTest.V2-header files (3xx format) are still decryptable after reading a V1-header file(CryptoMigrationV2CompatibilityTest.kt:131)`.
- **INV-ANA-46** (amended): `parse_logcat_line` MUST retain its signature
  `Tuple[Optional[RvErrorLog], Optional[RvCoverageLog]]` and its existing behavior for
  RVSEC/RVSEC-COV lines, with one stated exception: RVSEC lines whose `class`/`method` fields
  are in frame form now yield normalized values. The golden output MUST be byte-identical to
  baseline for every line that does not carry a frame-form value; for the lines that do, the
  golden baseline is re-frozen as part of this change and the diff MUST be confined to the
  `class_full_name`, `method` and `source` fields of those lines.

## ADDED Requirements

### Requirement: Frame-Form Normalization of Violation Class and Method (FR11, FR13)

The `LogcatParser` MUST normalize violation records whose `class` or `method` field carries a
whole stack frame instead of a class name and a method name. A value is in **frame form** when
it ends with a parenthesised group of the shape `(<file>:<line>)`. When a value is in frame
form, the parser MUST strip that trailing group and split the remainder at its **last** dot,
binding the part before the dot to `class_full_name` and the part after it to `method`, and
MUST bind the stripped group's contents to `source`.

The guard MUST test the trailing group only and MUST place no constraint on what precedes it.
Method names in the observed corpus contain `$` (Kotlin internal mangling, lambdas, Robolectric
shadows), `-` (Kotlin inline-class mangling), spaces (Kotlin backtick test names) and nested
parenthesis pairs; a guard that constrains the prefix silently fails on roughly half of them.

Normalization MUST be idempotent and MUST leave well-formed values byte-identical, so that
running the parser over output from a corrected monitor produces exactly the same records as
running it over output from an uncorrected one. The parser MUST apply normalization to the JCA
comma-separated format (Format 2), which is the only format whose class and method fields
originate from the Java `ErrorSummary` and can therefore arrive in frame form.

This requirement exists because APKs are instrumented once and replayed across many runs: an
APK already instrumented with an uncorrected monitor jar keeps emitting frame-form values
regardless of any upstream fix, and normalizing at parse time is the only protection for data
produced from those existing artifacts.

#### Scenario: Kotlin `$`-mangled internal method in frame form

- **WHEN** an `RVSEC` line carries the JCA format with `class` and `method` both equal to
  `okio.ByteString.digest$okio(ByteString.kt:83)`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with
  `class_full_name` = `okio.ByteString`
- **AND** `method` = `digest$okio`
- **AND** `source` = `ByteString.kt:83`
- **AND** neither `class_full_name` nor `method` MUST contain a parenthesis

#### Scenario: Two adjacent source lines collapse to one unique key

- **WHEN** two `RVSEC` lines from the same APK carry
  `okio.ByteString.digest$okio(ByteString.kt:83)` and
  `okio.ByteString.digest$okio(ByteString.kt:84)` under spec `MessageDigestSpec`
- **THEN** both MUST yield `class_full_name` = `okio.ByteString` and `method` = `digest$okio`
- **AND** the two records MUST agree on the `(class_full_name, method, spec)` triple, so that
  the `(apk, class, method, spec)` key counts them as one unique misuse
- **AND** their `source` values MUST differ (`ByteString.kt:83` and `ByteString.kt:84`)

#### Scenario: Kotlin inline-class hyphen mangling

- **WHEN** the frame-form value is `io.ktor.util.DigestImpl.plusAssign-impl(CryptoJvm.kt:51)`
- **THEN** `class_full_name` MUST be `io.ktor.util.DigestImpl` and `method` MUST be
  `plusAssign-impl`

#### Scenario: Robolectric shadow with double `$$`

- **WHEN** the frame-form value is
  `android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:350)`
- **THEN** `class_full_name` MUST be `android.os.SystemProperties`
- **AND** `method` MUST be `$$robo$$android_os_SystemProperties$digestOf`

#### Scenario: Lambda with `$` in both class and method

- **WHEN** the frame-form value is
  `io.matthewnelson.kmp.tor.runtime.FileID$Companion.createFID$lambda$0(FileID.kt:57)`
- **THEN** `class_full_name` MUST be `io.matthewnelson.kmp.tor.runtime.FileID$Companion`
- **AND** `method` MUST be `createFID$lambda$0`

#### Scenario: Backtick test name containing spaces and nested parentheses

- **WHEN** the frame-form value is
  `dev.leonlatsch.photok.CryptoMigrationV2CompatibilityTest.V2-header files (3xx format) are still decryptable after reading a V1-header file(CryptoMigrationV2CompatibilityTest.kt:131)`
- **THEN** `class_full_name` MUST be `dev.leonlatsch.photok.CryptoMigrationV2CompatibilityTest`
- **AND** `method` MUST be
  `V2-header files (3xx format) are still decryptable after reading a V1-header file`
- **AND** `source` MUST be `CryptoMigrationV2CompatibilityTest.kt:131`

#### Scenario: Constructor and static initializer

- **WHEN** the frame-form value is `com.example.Crypto.<init>(Crypto.java:15)`
- **THEN** `class_full_name` MUST be `com.example.Crypto` and `method` MUST be `<init>`
- **AND** the same MUST hold for `<clinit>`

#### Scenario: Well-formed record passes through untouched

- **WHEN** an `RVSEC` line carries `class` = `okhttp3.internal.platform.Platform` and
  `method` = `newSSLContext`, neither in frame form
- **THEN** `class_full_name` MUST be `okhttp3.internal.platform.Platform` byte-identical
- **AND** `method` MUST be `newSSLContext` byte-identical
- **AND** no normalization log entry MUST be emitted

#### Scenario: Normalization is idempotent

- **WHEN** the normalization is applied twice to
  `okio.ByteString.digest$okio(ByteString.kt:83)`
- **THEN** the second application MUST return exactly what the first returned
