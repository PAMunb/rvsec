# Fix the frame-form `class`/`method` corruption in RV violation records

GitHub Issue: #89

## Why

A violation record is supposed to name *where* a specification was violated: a class and a
method. For method names the JVM/ART can produce but the monitor's regex cannot parse, it
names neither — it copies the entire stack frame, source position included, into **both**
fields.

The regex lives in the Java monitor core,
`rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java:9`:

```java
static Pattern pattern = Pattern.compile("([\\w+\\.\\$]+)[.](\\<?\\w+\\>?)\\((.+)\\)");
String clazz = location; String method = location; String loc = location;  // fallback
if (matcher.matches()) { clazz = g1; method = g2; loc = g3; }
```

The asymmetry is one character class. The class group accepts `$`; the method group is
`\w+`, which accepts `[A-Za-z0-9_]` only — not `$`, not `-`, not space. Kotlin-mangled
internals (`digest$okio`), inline-class mangling (`plusAssign-impl`), lambdas
(`createFID$lambda$0`), Robolectric shadows (`$$robo$$…digestOf`) and Kotlin backtick test
names with spaces all fail the match, and the fallback before the `if` keeps the whole
`StackTraceElement` string in `clazz` and `method`.

Because the source position then rides *inside* those two fields, it silently joins the
`(apk, class, method, spec)` key every downstream analysis uses, and one misuse is counted
once per source line it occurs at. Measured on the frozen 2026-07-06 dataset: **58 of 567**
campaign keys (10.2%, 31 apps, collapsing to 7 distinct `(class, method)` pairs) and
**52 of 166** unit-test keys (31%). The bias is not noise — it concentrates in Kotlin library
code and Robolectric shadows. The entire Robolectric bucket of the unit-test baseline is the
single method `android.os.SystemProperties.$$robo$$…digestOf` counted across 6 source lines
in 14 apps: 34 keys where there should be 14.

Two further defects were confirmed in the same Java class while establishing the root cause:
`ErrorDescription.hashCode` hashes `expecting` while `equals` ignores it (a hashCode/equals
contract violation — negligible on the current data, 2 keys, but broken nonetheless), and
`ErrorSummary.equals`/`hashCode` include `location`, which makes the in-JVM deduplication
line-granular for every row, corrupted or not. The latter is an implicit decision nobody
recorded.

On the Python side the corruption is propagated without defense: `logcat_parser`
`_parse_error_message` Format 2 binds `parts[1]` → class and `parts[3]` → method exactly as
the Java emitted them. This must be fixed independently of the Java, because **APKs already
instrumented with the current jar keep emitting the corrupted form**, and conversely the
unit-test path (`rvsec-dataset`) consumes the Java CSV logger directly and never passes
through this parser. Neither fix alone covers both paths.

## What Changes

- **Java (`rvsec-core`, sibling repository)** — the method group of the `ErrorDescription`
  pattern accepts `$`, `-` and space, and the match is anchored on the trailing
  `(File.ext:NN)` suffix rather than on a restrictive name shape. `hashCode` and `equals` are
  brought into agreement. JUnit tests cover the real mangled-name corpus.
- **`ErrorSummary` line-granular dedup** — the `location` field in `equals`/`hashCode` is
  either removed or documented as intentional. This is a decision the design must settle;
  the invariant is that the choice is recorded, not implicit.
- **`rv-coverage`** — `_parse_error_message` normalizes frame-form `class`/`method` values
  defensively and idempotently: strip a trailing `(File.ext:NN)` group with a
  **suffix-anchored** guard and an unrestricted prefix, then split the remainder at its last
  dot. Well-formed values pass through byte-identical. The suffix anchor is not a stylistic
  choice — two real backtick test names in the corpus contain nested parentheses, and a guard
  anchored on a fully-qualified-path prefix matches only half the real malformed values.
- **`rv-android-core`** — `RvErrorLog.source` is preserved in `to_dict()` and therefore in
  the written `errors.csv`, kept **out** of the uniqueness key. Today it is parsed and then
  discarded, so line information is lost rather than merely excluded from the key.
  **BREAKING** for the `errors.csv` column set (one column added; all known consumers read by
  column name).
- **Tests** — both the Java and the Python fix are covered by the same corner-case corpus
  taken from the real dataset (`digest$okio`, `plusAssign-impl`, `$$robo$$…digestOf`,
  `createFID$lambda$0`, a backtick name with spaces, a backtick name with nested parentheses,
  `<init>`/`<clinit>`), plus a well-formed value that must pass through unchanged.

Explicitly **not** changing:

- `unique_msg` (`class:::method:::spec:::error_type:::message`) is correct. Within
  `(apk, class, method, spec, error_type)` only 2 of 826 keys carry more than one message, and
  in those the message distinguishes genuinely different misuses (`found MD5` vs
  `found SHA-1`). It is a deliberately finer granularity than the 4-part analysis key; the
  specs record that fact rather than alter the key.
- The frozen 2026-07-06 result CSVs. Repairing published sheets belongs to the
  `fix-rv-key-granularity` change in the `ase-journal` repository. This change fixes the
  producers so future runs are correct at the source.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `analysis`: violation-message parsing gains a normalization requirement — `parse_logcat_line`
  MUST NOT emit a `class_full_name` or `method` containing a source position, regardless of the
  form the instrumented APK emits (touches the "Specification Violation Detection" requirement
  and INV-ANA-46, whose byte-identical-baseline clause needs a stated exception for the
  malformed rows).
- `core`: the `RvErrorLog` written schema gains `source`, and the relationship between
  `unique_msg` (5-part, event granularity) and the 4-part analysis key is stated explicitly
  (touches INV-CORE-25 and the `RvErrorLog` data contract).
- `platform`: the `errors.csv` column set gains `source` after `method` (touches the
  "Result Generation (FR14)" requirement's "Errors CSV Format" scenario and INV-PLT-19, whose
  byte-identical-header clause must be narrowed to the diagnostic feature it was written for).

## Impact

**Modules**: `rv-coverage` (`parser/log/logcat_parser.py` — normalization), `rv-android-core`
(`domain/log.py` — `to_dict` schema), `rv-platform`
(`components/result_processor.py:545-650` — the `errors.csv` header and row writer, which
today emits `apk,rep,timeout,tool,time,spec,class,method,message,unique_msg`).

**Cross-repository**: `rvsec-core` (Java: `ErrorDescription`, `ErrorSummary`) in the sibling
`rvsec` reactor. The Java and Python fixes cover disjoint paths — the unit-test dataset path
never reaches the Python parser, and already-instrumented APKs never benefit from the Java fix
— so both land in this change.

**Downstream contract**: `rvsec-dataset` (`unittests/report.py` `EXP02_FIELDS`,
`unittests/classify.py`) and the `ase-journal` analysis scripts read these CSVs by column
name, so an added column is tolerated; this MUST be verified rather than assumed before the
schema change lands.

**Requirements**: FR11 (Logcat Capture and Parsing), FR13 (Specification Violation Detection),
FR14 (Result Generation), NFR03 (correctness of recorded measurements).
