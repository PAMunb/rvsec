# Implementation log — gh89-error-description-key

Records the measurements, censuses and reviewed diffs that individual tasks require to be
written down rather than merely performed. Everything here was produced by reading the frozen
2026-07-06 dataset read-only; that repository is not modified by this change.

## Task 1.1 — Corner-case census of the frozen dataset

Source: `ase-journal/dataset/results/errors.csv` (campaign) and `errors_unit_tests.csv`
(unit-test baseline), both read with `csv.DictReader` and scanned for values in the `class` or
`method` column matching `\(([^()]+:\d+)\)$`.

| File | Distinct frame-form values | Rows affected |
|---|---|---|
| `errors.csv` | 9 | 40 204 |
| `errors_unit_tests.csv` | 19 | 238 |
| union (distinct) | **28** | — |

`okio.ByteString.digest$okio(ByteString.kt:83)` is the only value present in both files.

A second scan looked for values containing a parenthesis but *not* matching the guard — the
shape that would silently pass through unnormalized. **Zero** such values exist in either file,
in either column. In particular the `(Unknown Source)` and `(Native Method)` frames a
`StackTraceElement` can also produce do not occur in the frozen data; the guard deliberately
leaves them alone because they carry no line number, and they are kept in the corpus as
pass-through cases so that boundary is asserted rather than assumed.

The complete distinct list, each with its expected `(class, method, source)` triple, is
committed as the shared corpus and is not duplicated here:

- Python: `modules/rv-coverage/tests/parser/log/fixtures/frame_form_corpus.py`
  (`FRAME_FORM_CASES`, 28 entries; `PASS_THROUGH_CASES`, 10 entries)
- Java: `rvsec/rvsec-core/src/test/resources/frame-form-corpus.txt` (same values, TSV)

Grouped by failure mode:

| Failure mode | Distinct values | Example |
|---|---|---|
| Kotlin `$`-mangled internals | 3 | `okio.ByteString.digest$okio(ByteString.kt:83)` |
| Kotlin lambda mangling `$lambda$N` | 4 | `…FileID$Companion.createFID$lambda$0(FileID.kt:57)` |
| Kotlin inline-class `-` mangling | 3 | `io.ktor.util.DigestImpl.plusAssign-impl(CryptoJvm.kt:51)` |
| Robolectric shadow `$$robo$$` | 6 | `android.os.SystemProperties.$$robo$$…digestOf(SystemProperties.java:318)` |
| Kotlin backtick test names (spaces) | 8 | `…CryptoEnginesTest.CBC engine decrypts V1-format files written by the 2xx app(CryptoEnginesTest.kt:135)` |
| Kotlin backtick test names (nested parens) | 2 | `…V2-header files (3xx format) are still decryptable after reading a V1-header file(…:131)` |

Two synthetic cases were added for JVM special method names (`<init>`, `<clinit>`), which the
regex the change replaces did handle and which must keep working.

The nested-parenthesis group is what forces the suffix anchor of design D2: a guard that
constrains the prefix to a dotted path fails on those 2 values and on all 8 space-bearing test
names — 10 of the 19 unit-test values, i.e. slightly more than half.

## Task 2.6 — Reviewed re-freeze of the RVSEC golden fixture

`fixtures/rvsec_cov_golden.logcat` carried no frame-form line, so the amended INV-ANA-46 was
unexercised. Two real okio frames (`ByteString.kt:83` and `:84`, the highest-volume pair in the
campaign data) were **appended** — appended, not inserted, so every pre-existing line keeps its
line number and the diff below is attributable line by line.

The diff was produced mechanically: the pre-change parser was recovered with
`git show HEAD:…/logcat_parser.py`, both versions were run over the same fixture, and every
field of every parsed record was dumped and compared.

- **Lines 1–7 (all pre-existing content): byte-identical.** Both RVSEC violations, all four
  RVSEC-COV entries and every non-matching line produce exactly the record they produced before.
- **Lines 8–9 (the appended frame-form lines): changed, and only in the permitted fields.**

  | Field | Before | After |
  |---|---|---|
  | `class_full_name` | `okio.ByteString.digest$okio(ByteString.kt:83)` | `okio.ByteString` |
  | `method` | `okio.ByteString.digest$okio(ByteString.kt:83)` | `digest$okio` |
  | `source` | `okio.ByteString.digest$okio(ByteString.kt:83)` | `ByteString.kt:83` |
  | `spec`, `error_type`, `message` | unchanged | unchanged |

  `unique_msg` also changes on these two lines. It is a *computed* field
  (`class:::method:::spec:::error_type:::message`), so it follows from the three fields above
  rather than being an independent edit — and its change is the point of the whole change: the
  two lines now share one key instead of being two misuses. 4 events, 3 unique errors.

No other field of any record differs. The re-freeze was not a silent regeneration; the golden
test now asserts the normalized values and the collapse explicitly.

## Task 4.1 — Census of `errors.csv` consumers (gate for the schema change)

The question the census had to answer: does anything read this file by column *position*? A
name-addressing reader tolerates an appended column; a positional one silently shifts.

**`rvsec-dataset`** — `src/rvsec_dataset/unittests/report.py` turned out to be a **writer**, not
a reader, of the campaign `errors.csv`. `EXP02_FIELDS` is the fieldname list of a
`csv.DictWriter` that emits `exp02_jca_errors_unit_tests.csv`; its input is the Java
`summary.csv` produced by `rvsec-logger-csv`, read with `csv.DictReader` and addressed by name
(`row.get("class")`, `row.get("method")`, …). `unittests/classify.py` likewise reads with
`csv.DictReader` and keys on `(apk, spec, class, method)` at line 147 — literally the
unique-misuse key, which is why the Java fix repairs the 31% unit-test inflation directly.

**`ase-journal`** — 56 Python files reference `errors.csv` or `errors_unit_tests.csv`:
210 `pandas.read_csv` calls, 38 `csv.DictReader`, 9 `csv.reader`. The `csv.reader` uses are the
only candidates for positional access, and all nine resolve their indices from the header first
(`header.index("apk")`, or `{name: i for i, name in enumerate(header)}` in
`repair_frame_keys.py`). A targeted scan for the positional idioms — literal `row[N]`,
`.iloc[:, N]`, `usecols=[N]`, `header=None` — found **zero** matches across the 56 files.

**Verdict: no positional reader exists. The schema change is safe to land.**

One divergence is worth stating rather than leaving to be discovered. The campaign
`errors.csv` now carries 11 columns; the unit-test `exp02_jca_errors_unit_tests.csv` that
`report.py` writes still carries 10, because `EXP02_FIELDS` has no `source`. The Java
`summary.csv` it reads *does* have a `location` column, so the data is available — adding the
column there is a one-line change in a third repository and is deliberately **not** made here,
since `rvsec-dataset` is outside this change's stated impact. Anyone unifying the two schemas
should start at `report.py:29` and `report.py:80`.

## Task 4.6 — Java build and test result

```
mvn -pl rvsec/rvsec-core -am test        (from the reactor root, after `source /etc/profile`)
Running br.unb.cic.mop.eh.ErrorDescriptionTest
Tests run: 9, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

`rvsec-core` had no `src/test` tree; one was created along with a `junit` + `surefire-junit4`
test-scoped dependency pair in its `pom.xml` (versions inherited from the reactor's
`dependencyManagement`). The 9 tests are the corpus sweep (split, no-position, pass-through,
idempotence), `<init>`/`<clinit>`, the nested-parenthesis backtick name, the two-adjacent-lines
case, the `hashCode`/`equals` contract, and the line-granular dedup decision.

## Task 5.1 — Cross-language parity (blocker check)

Two implementations of one algorithm agreeing on a shared list of *expected* values is an
argument, not a measurement, so parity was measured directly: both implementations were run
over the corpus file and their output diffed.

```
java -cp rvsec-core/target/classes DumpTriples.java frame-form-corpus.txt   > java_triples.tsv
python -c "_normalize_frame over the same file"                             > py_triples.tsv
diff java_triples.tsv py_triples.tsv
→ identical, 38/38 values
```

The comparison covers the fallback too. Where the guard misses, the Java keeps the value in all
three fields and the Python returns `None` so its caller does the same; the dump renders both
the same way, so a divergence in that path would also have shown up.

One intentional asymmetry, recorded so it is not mistaken for drift: the Python logs a warning
when a value ends in a position group but has no dot before it; the Java does not (it has no
logger). Both return the same triple.

Parity is also enforced permanently, not just at this moment:
`test_frame_form_normalization.py::TestCorpusParity` parses the Java corpus resource and asserts
it equals the Python list, skipping only when the sibling reactor is absent. A case added to one
side and forgotten on the other fails a test.

## Task 5.2 — Regression sweep over real campaign data

The corpus proves the corner cases; this proves the fix does not disturb anything else. Every
`.logcat` under `data/results/` was parsed twice — once by the pre-change parser recovered from
`HEAD`, once by the new one — and every record compared field by field.

```
logcat files swept                 : 1161
RVSEC-tagged lines                 : 6 836 709
violation records parsed           : 10 571
records changed by the fix         : 1 098
  of which were WELL-FORMED        : 0
records still carrying a position  : 0        (INV-ANA-50)
distinct (class, method, spec) keys: 156 → 154
well-formed keys before            : 145
  present after, with same count   : 145
```

Read together, those numbers say exactly what the change claims. Every one of the 1 098 altered
records was frame-form before; not one well-formed record moved. No `class` or `method` value
produced by the new parser matches `\(.*:\d+\)$`. And all 145 well-formed keys survive with
their counts *unchanged* — the only key movement is the intended collapse of frame-form keys,
156 → 154.

## Task 5.5 — Code review outcome

The review returned REQUEST CHANGES on two items. One was correct and is fixed; one is declined,
with the reason recorded here rather than left as a silent disagreement.

### Fixed — `ErrorDescription.hashCode` still violated the contract after removing `expecting`

D5's stated action was "remove `expecting`", and that is what was implemented first, keeping
`location`, `spec`, `type` and `summary` on the argument that the summary is derived from them.
**That argument is wrong**, because `createErrorSummary` is not injective:

| `location` | branch taken | resulting summary triple |
|---|---|---|
| `F:1` | guard misses → fallback | `(F:1, F:1, F:1)` |
| `F:1.F:1(F:1)` | guard hits → split | `(F:1, F:1, F:1)` |

`equals` compares the summary alone, so those two descriptions are equal — and hashing the raw
`location` gave them different hash codes. That is precisely the defect D5 exists to remove,
relocated from `expecting` to `location`.

`hashCode` is now `summary.hashCode()` and nothing else, which satisfies D5's stated *goal*
("both consider exactly the fields of the summary") without depending on any injectivity
argument. This goes marginally beyond D5's literal wording, which named only `expecting`.
`ErrorDescriptionTest.hashCodeMatchesEqualsWhenLocationsDifferButSummariesDoNot` pins the case.
Java suite: 10 tests, BUILD SUCCESS.

### Recorded — the `hashCode` fix narrows the emitted record set

Not a defect, but a real behavioral consequence that nothing in the diff stated. `ErrorCollector`
gates logcat emission on `HashSet.add`. Before, two descriptions equal by summary but differing
in `expecting` hashed differently, so **both** were emitted; now the second is dropped and which
one survives depends on arrival order. That is the correct behavior given what `equals` says, and
the proposal measured the real impact at 2 of 826 keys — but it is a narrowing of monitor output,
not a pure contract cleanup, and it is now stated in the `hashCode` Javadoc.

### Declined — binding `source` to `file:line` for the generic-spec format

The review is right that `source` means different things across the three formats: Format 2 now
yields `ByteString.kt:83`, while `_parse_generic_spec_error` parses a line number and then writes
only `Auth.java`, discarding it. In a column added specifically to carry line information that is
a genuine inconsistency.

It is not fixed here, for a reason that is structural rather than a matter of effort. The
golden fixture's line 6 is exactly such a record, and its `class`/`method` were never in frame
form — so changing its `source` would change the golden output for a line that carries no
frame-form value, which the amended **INV-ANA-46 in this change's own analysis delta explicitly
forbids**. Fixing it therefore requires amending an invariant this change is introducing, on
records that were never broken. That is a separate change with its own spec amendment, not a
review nit to absorb here.

Follow-up scope, if taken: `_parse_generic_spec_error`'s caller binds
`f"{file_name}:{line_number}"`, INV-ANA-46 gains a second stated exception, and the golden
baseline is re-frozen again. It also removes a produced-but-unread field (`line_number` currently
has no consumer).

### Applied from the suggestions

- `test_frame_form_normalization.py` now resolves the Java corpus via `$RVSEC_HOME` first, with
  the positional `parents[6]` walk as fallback — the review correctly noted that a bare
  positional walk plus `skipif` degrades into a silent skip if the tree depth ever changes.
- The unrelated Black reformat of `domain/components.py` was reverted; it did not belong to this
  change.

Not applied, as unrelated to gh89 and outside P1's "minimum complexity for the current task":
the unused `return_type` unpack in `_parse_coverage_message`, and unifying the module's mixed
`logging.getLogger(__name__)` / local-`logger` convention.
