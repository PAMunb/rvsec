# E6 — the collector line reaches the `errors.csv` columns (task 9.3)

Task 9.2 put `code` and `event` inside `ErrorSummary`'s identity. That decides how many lines a
device run *emits*; it decides nothing about whether those two values survive the trip from the
logcat line into the columns and the `unique_msg` parts that the analysis layer reads. This file
records the check that they do, and what the check is made of.

## The fixture is a transcript, not an authored string

`collector_lines.logcat` beside this file holds three lines produced by
`br.unb.cic.mop.eh.ErrorCollector.buildLine` — the logcat collector of
`rvsec/rvsec-android/rvsec-logger-logcat`, compiled against the `rvsec-core` of task 9.2 and
driven directly. `addError` was not called: its only other statement is `android.util.Log.v`,
whose body in the stub jar that module compiles against is `throw new RuntimeException("Stub!")`,
so the line text is only reachable where the device is not. That is why `buildLine` is
package-private and why the recorder ran inside the collector's own package.

The three lines are one call site — `com.example.vault.Hash.digest(Hash.java:40)` — reporting
`MessageDigestSpec` / `InvalidSequenceOfMethodCalls` three times:

| line | `code` | `ev` | why it is there |
|---|---|---|---|
| 1 | `MESSAGEDIGEST-ORDER-00` | `update` | the first of two causes at one site |
| 2 | `MESSAGEDIGEST-ORDER-00` | `reset` | the second — identical in every other field |
| 3 | — | — | a pre-envelope message, for the sentinel |

Lines 1 and 2 differ in exactly one token. Under the five-field identity they were **one**
record, and which of the two survived the collector's `HashSet` was arrival order; the code is
identical on both, which is the measured form of design D-5's claim that `code` alone would
refine nothing.

## Both ends are pinned, because a transcript can go stale in silence

A recorded fixture that nobody re-records keeps passing while its producer moves on, and the
test that reads it then measures a format nothing emits any more. So the transcript is asserted
from both sides:

- **Java** — `ErrorCollectorTest.buildLineReproducesTheRecordedFixtureLineByteForByte` builds the
  two envelope lines through the live `buildLine` and compares them to the recorded text. A
  change to the line format fails in the module that owns the format.
- **Python** — two tests read the same file, one per module, split that way because each asserts
  the code its own module owns and `aperv-tool` does not depend on `rv-coverage`:
  - `modules/rv-coverage/tests/parser/log/test_gh104_collector_transport.py` — the line through
    `parse_logcat_line` into `RvErrorLog`: both keys recovered from the envelope, `unique_msg` of
    seven parts with the keys in positions 5 and 6, the sentinel twice on the legacy line, and
    the two events not deduplicating (`len({update, reset}) == 2`).
  - `modules/aperv-tool/tests/test_gh104_collector_transport.py` — the same lines through
    `read_logcat`, out to a thirteen-column `errors.csv` written as `rv-platform` writes it, and
    back through `read_errors_csv`: the `code`/`event` columns carry the values, the round trip
    reports `unique_msg_unparsed == 0` and `unique_msg_disagrees == 0`, and the two rows at the
    one site hold two distinct `unique_msg`.

The last of those is the one worth naming. The columns and the `unique_msg` parts are two copies
of the same attribution written by one producer from one object, so a disagreement between them
is not a reconciliation problem to be resolved by preferring one — it means the writer and the
domain key have forked, which is exactly the failure the seven-part key exists to surface.

## The line format did not change, and that is deliberate

`ErrorSummary.toString()` still emits six comma-separated fields, and the collector still appends
the escaped message as the seventh. The two new values are already on the line, inside the
envelope; emitting them again would widen a positional record that every downstream parser splits
by count, for no information gained. Two tests hold that: `ErrorCollectorTest`'s
`buildLineKeepsTheSixSummaryFieldsAheadOfTheSeventh` (7 fields on the line) and
`ErrorDescriptionTest`'s `theReportedLineStillCarriesSixSummaryFields` (6 from the summary).

The identity era both halves belong to is declared in `../identity_discontinuity.md`.
