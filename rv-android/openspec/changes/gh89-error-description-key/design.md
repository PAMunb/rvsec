# Design — gh89-error-description-key

## Context

The proposal establishes the defect: `ErrorDescription`'s regex cannot parse method names
containing `$`, `-` or spaces, and its fallback copies the whole stack frame into both the
class and the method field, so a source position enters the `(apk, class, method, spec)` key
and one misuse is counted once per line. It affects 58 of 567 campaign keys and 52 of 166
unit-test keys on the frozen 2026-07-06 dataset.

The design has to satisfy two constraints that pull in different directions.

**The fix cannot live in one place.** The corrupted records reach the article's dataset by two
disjoint routes. The campaign route is `instrumented APK → logcat → rv-coverage LogcatParser →
errors.csv`. The unit-test route is `instrumented test run → rvsec-logger-csv → summary.csv →
rvsec-dataset`, which never touches Python at all. A Python-only fix leaves 31% of the
unit-test baseline broken; a Java-only fix leaves every already-instrumented APK broken, and
re-instrumenting a campaign costs far more than parsing defensively. Both sides are in scope,
and the design's main job is to make sure they agree.

**Agreement must be structural, not aspirational.** Two implementations of "parse a stack
frame" in two languages will drift unless they implement the same algorithm against the same
corpus. This design therefore specifies one algorithm — suffix-strip then last-dot split — and
one shared corner-case corpus drawn from the real data, used verbatim by both test suites.

Relevant requirements: FR11 (Logcat Capture and Parsing), FR13 (Specification Violation
Detection), FR14 (Result Generation), NFR03 (correctness of recorded measurements).

## Architecture

```
  ┌───────────────────────── device / JVM ─────────────────────────┐
  │  woven monitor → ErrorCollector.addError(ErrorDescription)     │
  │                        │                                       │
  │            ErrorDescription.createErrorSummary()   ← FIX 1     │
  │              (suffix-strip + last-dot split)                   │
  │                        │                                       │
  │        ErrorSummary.toString() = spec,class,className,          │
  │                                  method,location,error          │
  └────────┬───────────────────────────────────┬───────────────────┘
           │ Log.v("RVSEC", …)                 │ CSV (rvsec-logger-csv)
           ▼                                   ▼
   rv-coverage LogcatParser              rvsec-dataset unittests
   _parse_error_message (Format 2)       (consumes the Java output
     normalize_frame()  ← FIX 2           directly — Python never runs)
           │
           ▼
   RvErrorLog(class_full_name, method, source, …)   ← FIX 3 (source kept)
           │
           ▼
   LogcatRepository → ResultProcessorComponent → errors.csv (+ source column)
```

FIX 2 is not redundant with FIX 1: it is the only protection for APKs instrumented before
FIX 1 ships. FIX 1 is not redundant with FIX 2: it is the only protection for the unit-test
route.

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ErrorDescription.createErrorSummary()` (Java, `rvsec-core`) | Split a `StackTraceElement` string into class, method, location | `location: String` | `ErrorSummary` |
| `logcat_parser._normalize_frame()` (new, `rv-coverage`) | Recover `(class, method, source)` from a frame-form value; no-op on well-formed values | `value: str` | `tuple[str, str, str] \| None` |
| `logcat_parser._parse_error_message()` | Bind JCA Format 2 fields, applying normalization | `message: str` | `RvErrorLog \| None` |
| `RvErrorLog.to_dict()` (`rv-android-core`) | Serialize a violation, now including `source` | — | `dict` |
| `ResultProcessorComponent._generate_errors_csv/_write_task_error_data` (`rv-platform`) | Write `errors.csv` with the `source` column | `List[Task]` | CSV file |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| analysis: Frame-Form Normalization (FR11, FR13) | `logcat_parser._normalize_frame()` + Format 2 branch of `_parse_error_message()` | `test_logcat_parser.py::test_normalize_frame_*` (corpus-driven) |
| INV-ANA-50 (no position in class/method) | `_normalize_frame()` applied before `RvErrorLog` construction | `test_no_frame_form_in_output` over the full corpus |
| INV-ANA-51 (idempotent, no-op on well-formed) | Suffix guard returns `None` when no trailing group | `test_normalize_is_idempotent`, `test_wellformed_passthrough_byte_identical` |
| INV-ANA-52 (suffix-anchored guard) | Regex `\(([^()]+:\d+)\)$` — no prefix constraint | `test_backtick_name_with_nested_parens` |
| INV-ANA-46 (amended golden baseline) | Re-frozen golden fixture | `test_rvsec_golden_output` |
| core: RvErrorLog Preserves Source (FR13, FR14) | `RvErrorLog.to_dict()`; `result_processor` header + row | `test_log.py::test_to_dict_includes_source`; `test_result_processor.py::test_errors_csv_header` |
| INV-CORE-40 (source outside identity) | `unique_msg`, `__eq__`, `__hash__` unchanged | `test_source_does_not_affect_identity` |
| INV-CORE-41 (event granularity documented) | Docstring on `RvErrorLog.unique_msg` | Reviewed, not asserted (documentation invariant) |
| INV-CORE-42 (no position in either field) | Guaranteed by INV-ANA-50 upstream | `test_no_frame_form_in_output` |
| Java root cause (issue #89) | `ErrorDescription.createErrorSummary()` | `ErrorDescriptionTest` (new, JUnit 4) |
| Java hashCode/equals contract | `ErrorDescription.hashCode()` | `ErrorDescriptionTest::hashCodeMatchesEquals` |

## Goals / Non-Goals

**Goals:**
- No `class`/`method` value produced by either route contains a source position.
- The Java and the Python side implement the *same* algorithm and are tested against the *same*
  corpus of real values.
- Line information is preserved in its own field rather than discarded.
- The Java `hashCode`/`equals` contract holds.
- The line-granular in-JVM dedup is a recorded decision rather than an accident.

**Non-Goals:**
- Repairing the frozen 2026-07-06 result CSVs (owned by `fix-rv-key-granularity` in
  `ase-journal`).
- Changing `unique_msg` or any deduplicated count. Every count that exists today must be
  unchanged for well-formed data.
- Re-instrumenting existing APKs.
- Recovering a method *signature*. `StackTraceElement` carries none; method-name granularity is
  the instrument's unit of analysis, not a limitation introduced here.

## Decisions

### D1: Suffix-strip + last-dot split, not a smarter regex

The current Java code tries to describe a valid method name with a character class. That is the
defect: every time a language adds a mangling scheme (`$` for Kotlin internals and lambdas, `-`
for inline classes, `$$robo$$` for Robolectric shadows, spaces for backtick test names), the
character class is wrong again and fails *silently* into a fallback that produces garbage.

The algorithm here inverts the problem. It does not describe what a method name looks like; it
describes the one thing a stack frame reliably ends with — `(<file>:<line>)` — strips it, and
splits the remainder at its last dot, because the class part is a dotted path and the method
part never contains a dot. Nothing about the method name needs to be predicted.

*Alternative considered*: widen the character class to `[\w$\- ]+`. Rejected — it is the same
design that already failed twice, and it still needs a `$$`/space/nested-paren audit every time a
new toolchain appears.

### D2: The guard tests the trailing group only, and requires a line number

The guard is `\(([^()]+:\d+)\)$` — a parenthesised group at the very end, containing no nested
parentheses and ending in `:<digits>`.

Two properties matter. The **prefix is unconstrained**, because two real backtick test names in
the corpus contain a nested parenthesis pair inside the method name itself
(`V2-header files (3xx format) are still decryptable…`); a guard requiring a dotted path before
the parenthesis matches only about half of the real malformed values. And the group **must end
in `:<digits>`**, which is what distinguishes a stack-frame position from an ordinary trailing
parenthesis, so a well-formed name can never be truncated by accident.

*Alternative considered*: strip any trailing `(...)`. Rejected — it cannot tell a source position
from a parenthesis that belongs to the name.

### D3: Normalize only Format 2

Format 1 (generic spec) and Format 3 (FSM) already split structurally — Format 1 with a greedy
`(.*)\.(.*)\((.*):(.*)\)` that handles `$`, `-` and spaces correctly, Format 3 by truncating at
the first `(`. Only Format 2 receives pre-split fields from the Java `ErrorSummary` and can
therefore inherit the fallback's output. Applying normalization to all three would be defensive
coding against a state that cannot occur (P1).

### D4: `ErrorSummary` keeps `location` in `equals`/`hashCode` — documented, not changed

In-JVM deduplication stays line-granular. Two consequences make this the right choice: it is what
bounds logcat volume for a hot violated method, and now that `source` is preserved end to end,
emitting one record per line is what makes that field carry information. Coarsening to the
analysis key inside the monitor would discard the line data the rest of this change is preserving,
and the coarsening the analysis actually needs already happens downstream, at
`drop_duplicates` time.

The decision is recorded in a class comment on `ErrorSummary` (P4: state the current rule and its
reason, not the history).

### D5: `hashCode` drops `expecting`

`ErrorDescription.equals` delegates to `ErrorSummary.equals`, which does not consider
`expecting`; `hashCode` hashes it. Equal objects can therefore land in different buckets, which is
a broken contract regardless of measured impact (2 keys on the current data). `expecting` is
removed from `hashCode` so that both consider exactly the fields of the summary.

### D6: `source` is added to `errors.csv` after `method`

Position is chosen so the CSV reads as `spec, class, method, source, message` — identity fields
first, then evidence. All known consumers (`rvsec-dataset` `unittests/report.py`,
`unittests/classify.py`, the `ase-journal` scripts) address columns by name, so an added column
is tolerated; this is verified as a task, not assumed.

## API Design

### Python — `_normalize_frame(value: str) -> Optional[Tuple[str, str, str]]`

```python
_FRAME_SUFFIX = re.compile(r"\(([^()]+:\d+)\)$")

def _normalize_frame(value: str) -> Optional[Tuple[str, str, str]]:
    """Recover (class, method, source) from a stack-frame string.

    Returns None when `value` is not in frame form, which is the signal to keep
    the caller's fields untouched.
    """
```

- **Precondition**: none; `value` may be any string, including the empty string.
- **Postcondition**: returns `None` unless `value` ends with `(<file>:<line>)` **and** the
  remainder contains at least one dot. On success returns
  `(remainder_before_last_dot, remainder_after_last_dot, group_contents)`.
- **Idempotence**: for any `v`, if `_normalize_frame(v)` returns `(c, m, s)`, then
  `_normalize_frame(c)` and `_normalize_frame(m)` both return `None`.
- **Errors**: none raised. A value that ends with a position group but has no dot in the
  remainder returns `None` and logs a warning — a frame that shape cannot come from a real
  `StackTraceElement`, and silently mangling it would be worse than leaving it.

Caller (Format 2 branch of `_parse_error_message`): attempt normalization on `parts[3]` (method);
if that returns `None`, attempt it on `parts[1]` (class). On success, bind class, method and
source from the result and log at debug level. On failure, bind the fields exactly as today.

### Java — `ErrorDescription.createErrorSummary()`

```java
private static final Pattern FRAME_SUFFIX = Pattern.compile("\\(([^()]+:\\d+)\\)$");
```

Same two steps, same guard, same fallback semantics: when the suffix does not match or the
remainder has no dot, `clazz`, `method` and `loc` keep the current fallback values, so behavior
for genuinely unparseable input is unchanged.

### Pydantic — `RvErrorLog`

No field is added or removed; `source` already exists. Only `to_dict()` changes:

```python
{
    "spec": ..., "error_type": ..., "class_full_name": ..., "method": ...,
    "source": self.source,          # added
    "message": ..., "time_occurred": ..., "time_since_task_start": ..., "unique_msg": ...,
}
```

`unique_msg`, `__eq__` and `__hash__` are untouched (INV-CORE-25 holds, INV-CORE-40 requires it).

## Data Flow

1. The woven monitor reports a violation with `location` = one `StackTraceElement` string.
2. `ErrorDescription.createErrorSummary()` splits it (FIX 1). `ErrorCollector` deduplicates on
   the full summary including `location`, then emits
   `spec,class,className,method,location,error,expecting` — to logcat on device, to CSV in the
   unit-test harness.
3. `LogcatParser._parse_error_message()` splits the comma-separated message and, for values still
   in frame form (older jars), normalizes them (FIX 2), binding `source` from the recovered group.
4. `RvErrorLog` carries `class_full_name`, `method`, `source`; `unique_msg` is computed from the
   corrected class and method.
5. `LogcatRepository` deduplicates on `unique_msg` (unchanged); `ResultProcessorComponent` writes
   `errors.csv` with the added `source` column (FIX 3).
6. Downstream, `(apk, class, method, spec)` now identifies one misuse regardless of how many lines
   it occurred at.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Value ends with a position group but the remainder has no dot | `_normalize_frame` / Java equivalent | Return `None` / keep fallback; log a warning | Record is kept unnormalized rather than mangled; the warning names the value |
| Message matches no known format | `_parse_error_message` | Unchanged: warning + `None` | No record registered (existing behavior) |
| `parts[4]` missing (short JCA message) | `_parse_error_message` | Unchanged: the `len(parts) >= 6` guard already prevents it | — |
| Downstream consumer breaks on the new CSV column | `rvsec-dataset` / analysis scripts | Verified before landing (task 4.1) | Column is appended by name, not position; a positional reader would be fixed there |

## Risks / Trade-offs

- **[Golden-fixture drift]** The RVSEC golden output baseline changes for frame-form lines, which
  INV-ANA-46 currently forbids → the invariant is amended in the analysis delta to permit exactly
  that diff, and the re-freeze is a task with an explicit diff review, not a silent regeneration.
- **[Two implementations of one algorithm]** Java and Python can drift → the same corner-case
  corpus is used by both test suites and is committed as a shared fixture list; adding a case to
  one suite without the other is a review-visible omission.
- **[CSV contract change]** A downstream reader could address columns positionally → verified
  against `rvsec-dataset` and the `ase-journal` scripts before the change lands.
- **[Java module has no test source tree]** `rvsec-core` has only `src/main` → a `src/test` tree
  and a JUnit 4 dependency are added; the reactor already manages `junit 4.13.2` and
  `surefire 3.5.6`, and `rvsec/pom.xml` defaults `skipTests` to `false`, so tests run in a normal
  build.
- **[No effect on published results]** This change alone does not correct any number already in
  the article → that is by design; the article's repair is `fix-rv-key-granularity`, and this
  change is what stops the defect from recurring in future campaigns.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Python) | `_normalize_frame` over the real corner-case corpus; idempotence; well-formed pass-through | pytest, no I/O | ~12 tests |
| Unit (Python) | Format 2 end-to-end through `parse_logcat_line`; `source` binding; no-frame-form invariant | pytest with synthetic logcat lines built from real values | ~5 tests |
| Unit (Python) | `RvErrorLog.to_dict()` includes `source`; `source` does not affect identity or `unique_errors` | pytest | ~4 tests |
| Unit (Java) | `ErrorDescription` over the identical corpus; `<init>`/`<clinit>`; well-formed pass-through; `hashCode`/`equals` contract | JUnit 4 in new `rvsec-core/src/test` | ~12 tests |
| Integration (Python) | `errors.csv` header and rows carry `source`; golden RVSEC fixture re-frozen with a reviewed diff | pytest over `result_processor` and the fixture | ~3 tests |

The corpus, taken verbatim from the 2026-07-06 data: `okio.ByteString.digest$okio(ByteString.kt:83)`,
`okio.ByteString.digest$jvm(ByteString.kt:…)`, `io.ktor.util.DigestImpl.plusAssign-impl(CryptoJvm.kt:51)`,
`io.matthewnelson.kmp.tor.runtime.FileID$Companion.createFID$lambda$0(FileID.kt:57)`,
`android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:350)`,
a backtick test name with spaces, a backtick test name with nested parentheses,
`com.example.Crypto.<init>(Crypto.java:15)`, `<clinit>`, and the well-formed pair
`(okhttp3.internal.platform.Platform, newSSLContext)`.

## Open Questions

- Does any consumer of the per-run `errors.csv` outside `rvsec-dataset` and the `ase-journal`
  scripts read it positionally? Resolved by the census in task 4.1 before the schema change lands.
- Should the Java fix ship as part of a `rvsec` release, or is a local `mvn install` sufficient for
  the next campaign? Affects sequencing only, not this design; decided at implementation time with
  the owner.
