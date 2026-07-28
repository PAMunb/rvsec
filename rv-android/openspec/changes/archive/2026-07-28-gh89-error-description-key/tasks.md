<!-- Group order is normative. Group 1 (shared corpus) must complete first: Groups 2, 3 and 4
     all consume it, and the whole point of the corpus is that the Java and the Python fix are
     tested against identical values. Groups 2 (Python normalization) and 4 (Java) are
     independent of each other and may run in parallel. Group 3 (source in the written schema)
     depends on Group 2 only for its test fixtures. Group 5 integrates and verifies.
     Critical path: 1 -> 2 -> 3 -> 5. This change touches ~12 files; subagent dispatch is
     optional and only worthwhile for running Groups 2 and 4 concurrently. -->

## 1. Shared corner-case corpus

- [x] 1.1 Extract the malformed values verbatim from the frozen dataset (`ase-journal/dataset/results/errors.csv` and `errors_unit_tests.csv`) — read-only, do not modify that repository — and record the complete distinct list plus the expected `(class, method, source)` triple for each in the change log
- [x] 1.2 Commit the corpus as a Python fixture list in `modules/rv-coverage/tests/parser/log/fixtures/frame_form_corpus.py`, covering at minimum: `okio.ByteString.digest$okio(ByteString.kt:83)`, `okio.ByteString.digest$jvm(...)`, `io.ktor.util.DigestImpl.plusAssign-impl(CryptoJvm.kt:51)`, `io.matthewnelson.kmp.tor.runtime.FileID$Companion.createFID$lambda$0(FileID.kt:57)`, `android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:350)`, a backtick test name with spaces, a backtick test name with a nested paren pair, `com.example.Crypto.<init>(Crypto.java:15)`, `<clinit>`, and the well-formed pair `(okhttp3.internal.platform.Platform, newSSLContext)` that must pass through untouched
- [x] 1.3 Mirror the same corpus as a Java constant in `rvsec/rvsec-core/src/test/resources/frame-form-corpus.txt` (one value + expected triple per line), so both suites read the same values and a case added to one but not the other is visible in review

## 2. Python normalization (`rv-coverage`)

- [x] 2.1 Implement `_normalize_frame(value) -> Optional[Tuple[str, str, str]]` in `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` per design D1/D2: guard `\(([^()]+:\d+)\)$` (suffix-anchored, unconstrained prefix, group must end in `:<digits>`), strip the group, split the remainder at its last dot; return `None` when the guard misses or the remainder has no dot, logging a warning in the latter case
- [x] 2.2 Apply it in the Format 2 (JCA comma-separated) branch of `_parse_error_message`: try `parts[3]` (method) first, then `parts[1]` (class); on success bind `class_full_name`, `method` and `source` from the result and emit a debug log naming the original value; on failure bind exactly as today. Do NOT touch Formats 1 and 3 (design D3)
- [x] 2.3 Add unit tests driven by the Group 1 corpus: one assertion per corner case, plus idempotence (`normalize(normalize(v)) == normalize(v)`), plus byte-identical pass-through for every well-formed value (INV-ANA-50, INV-ANA-51, INV-ANA-52)
- [x] 2.4 Add an end-to-end test through `parse_logcat_line` for a real `RVSEC` Format 2 line, asserting `source` is bound from the recovered group and that neither output field contains a parenthesis
- [x] 2.5 Add the two-adjacent-lines test: `ByteString.kt:83` and `:84` must produce the same `(class_full_name, method, spec)` triple and different `source` values
- [x] 2.6 Re-freeze the RVSEC golden fixture under `modules/rv-coverage/tests/parser/log/fixtures/`, reviewing the diff line by line: it MUST be confined to `class_full_name`, `method` and `source` on frame-form lines and MUST be empty everywhere else (amended INV-ANA-46). Record the diff summary in the change log
- [x] 2.7 Run `/rv-doc-code modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`
- [x] 2.8 Run `/rv-test-run rv-coverage`

## 3. Source location in the written schema (`rv-android-core`, `rv-platform`)

- [x] 3.1 Add `"source": self.source` to `RvErrorLog.to_dict()` in `modules/rv-android-core/src/rv_android_core/domain/log.py`, leaving `unique_msg`, `__eq__` and `__hash__` untouched (INV-CORE-40)
- [x] 3.2 Document on `unique_msg` that it counts at event granularity and is deliberately finer than the `(apk, class, method, spec)` unique-misuse key, with the reason (`error_type` separates sequence from constraint violations; `message` names the offending parameter) and the consequence (`unique_errors` / `mop_errors_unique` are not comparable to a unique-misuse count) — INV-CORE-41
- [x] 3.3 Add the `source` column to `errors.csv` in `modules/rv-platform/src/rv_platform/components/result_processor.py`: header becomes `apk,rep,timeout,tool,time,spec,class,method,source,message,unique_msg` (after `method`, design D6) and `_write_task_error_data` writes `error.get("source", "")`
- [x] 3.4 Add unit tests: `to_dict()` includes `source`; two records differing only in `source` are equal, hash equal, share one `unique_msg`, and register as `unique_errors == 1`; the CSV header matches exactly
- [x] 3.5 Run `/rv-test-run rv-android-core` and `/rv-test-run rv-platform`

## 4. Java root cause (`rvsec-core`, sibling repository)

- [x] 4.1 Census of `errors.csv` consumers before the schema change is relied on: confirm `rvsec-dataset` (`src/rvsec_dataset/unittests/report.py` `EXP02_FIELDS`, `unittests/classify.py`) and the `ase-journal` `data-analysis/` scripts address columns by name, not by position; record the census in the change log and flag any positional reader found (design open question 1)
- [x] 4.2 Replace the regex-only split in `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java` `createErrorSummary()` with the same two-step algorithm as the Python: suffix guard `\(([^()]+:\d+)\)$`, strip, split the remainder at its last dot. Keep the existing fallback semantics when the guard misses or the remainder has no dot
- [x] 4.3 Remove `expecting` from `ErrorDescription.hashCode()` so it considers exactly the fields `equals` does (design D5)
- [x] 4.4 Add a class comment on `ErrorSummary` recording that `location` participates in `equals`/`hashCode` deliberately — dedup is line-granular, which bounds logcat volume and keeps `source` meaningful per event; the coarsening to the analysis key happens downstream (design D4). State the rule and the reason, no history (P4)
- [x] 4.5 Create `rvsec/rvsec-core/src/test/java/br/unb/cic/mop/eh/ErrorDescriptionTest.java` (JUnit 4 — the reactor manages `junit 4.13.2` and `surefire 3.5.6`, and `rvsec/pom.xml` defaults `skipTests` to `false`), driven by the Group 1 corpus file: one case per malformed value, `<init>`/`<clinit>`, well-formed pass-through, and a `hashCode`/`equals` contract test
- [x] 4.6 Build and run the Java tests from the reactor root (`source /etc/profile` first; `main.basedir` only resolves from the root reactor): `mvn -pl rvsec/rvsec-core -am test`. Record the test count and result in the change log

## 5. Integration and verification

- [x] 5.1 Cross-check parity: every value in the Group 1 corpus produces the same `(class, method, source)` triple in the Python and the Java suite. Any divergence is a blocker, not a note
- [x] 5.2 Grep the produced artifacts for regressions: no `class` or `method` value in a freshly generated `errors.csv` matches `\(.*:[0-9]+\)$`, and every count that existed before is unchanged for well-formed data
- [x] 5.3 Run `/rv-qa-lint-fix rv-coverage` and `/rv-qa-lint-fix rv-android-core`
- [x] 5.4 Run `/rv-verify rv-coverage`, `/rv-verify rv-android-core`, `/rv-verify rv-platform`
- [x] 5.5 Invoke `/rv-code-reviewer` via the Skill tool for the full change (Python + Java)
- [x] 5.6a Add the missing `platform` delta spec: implementation revealed that `openspec/specs/platform/spec.md` pins the 10-column `errors.csv` header in three places (the output-file data contract, INV-PLT-19, and the "Errors CSV Format" scenario of "Result Generation (FR14)"), which design D6 changes. Without it, archiving would leave the platform spec asserting a header the code no longer produces
- [x] 5.6b At archive time, confirm the sync also updates the plain output-file line in `openspec/specs/platform/spec.md` (`errors.csv -- ... columns: apk, rep, ...`) — it sits outside any Requirement block, so `openspec archive` may not rewrite it automatically
- [x] 5.6 Run `/rv-docs-sync rv-coverage` if the module CLAUDE.md or architecture docs describe the parsing contract
- [x] 5.7 `/opsx:verify`, then `/opsx:archive` — sync the analysis and core deltas into `openspec/specs/`, close issue #89, and move the Kanban card to Done
