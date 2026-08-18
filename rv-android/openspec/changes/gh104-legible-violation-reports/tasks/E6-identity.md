# Group 9 — E6: identity

Tracked checkboxes: `tasks.md` §9. After Groups 5 (transport: `code`/`event` columns and parts) and 7 (envelope carries `ev=`). May overlap Group 8 (no `.mop` file here). Device-side consequence: instrumented APKs must be rebuilt for the identity change to take effect; the change lands after the E3 trial's final runs (design D-5).

## Subagent brief

Read `design.md` D-5, the `instrumentation` delta `Requirement: Dedupe Identity of a Violation Report` (INV-INS-126), the `core` delta (INV-CORE-57, era declaration). Measure first (9.1); if the discontinuity is zero, stop and report — do not land 9.2 (the group numbering is `tasks.md` §9: 9.1 measures, 9.2 lands).

## Files

- `scripts/gh104_identity_discontinuity.py` — over `experimento-comp162/results/*/*/errors.csv` (11 columns; use Group 1's reader): count distinct `(spec, error_type, class, method, source)` (today 6,344 with the `identity5` definition of Group 1 — recompute with the `ErrorSummary` five fields and record both), then with `event` added, where `event` is parsed from `message` if it is an envelope, else `UNSPECIFIED`. **Note**: comp162 was recorded before E1, so on that corpus every `event` is `UNSPECIFIED` and the discontinuity is zero *by construction*. The measurement that decides E6 is therefore on the first `jca_android` logcat produced by task 10.4 (device validation) or by the harness traces of Group 6 (JVM): recompute on `evidence/harness/**` outputs where each accusation carries `ev=`. State clearly which corpus the non-zero number comes from.
- `data/gh104/identity_discontinuity.md` — both numbers, definitions, corpus, era declaration.
- `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorSummary.java` (127 lines; `equals/hashCode :73-120`, `toString :124`) — add `code`, `event` fields; `ErrorDescription.java` (146; `createErrorSummary :216-233`) parses them from the envelope of `expecting` (`code=`, `ev=`), sentinel `UNSPECIFIED`; `toString` of `ErrorSummary` unchanged (the logcat line format is unchanged — the envelope already carries them).
- `rvsec/rvsec-core/src/test/java/br/unb/cic/mop/eh/ErrorDescriptionTest.java` (221; `hashCodeMatchesEquals :184-197` asserts `expecting` outside identity today) — rewrite for seven fields; message text still outside.
- Verification fixture: a recorded logcat with two envelopes at one site differing only in `ev=` → two rows in `errors.csv` (Group 5's writer) with distinct `unique_msg`.

## Acceptance

- `identity_discontinuity.md` states the corpus, both counts, non-zero delta; if zero, E6 is not integrated and design D-5 is re-opened (documented in `tasks.md` as blocked, not silently skipped).
- Java tests green; `lib/` jars rebuilt (`mvn -q install -DskipTests -DskipMopAgent=true` at the reactor root); `rv-coverage` and `aperv-tool` tests green.
- Era declared in `data/gh104/identity_discontinuity.md` and referenced by `data/gh104/baseline.md`.
