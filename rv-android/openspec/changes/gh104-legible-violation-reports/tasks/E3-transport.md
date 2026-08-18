# Group 5 — E3: honest transport

Tracked checkboxes: `tasks.md` §5. Wave 1; disjoint from Groups 1/2/3/4/6/7; Group 9 (E6) depends on it. Order inside the group: 5.4 (`log.py` with defaults) before 5.3; 5.6 and 5.7 in **one** commit (`read_logcat`'s new return shape breaks `step_bundle.py:286` otherwise). The collectors live in `rvsec-android/rvsec-logger-logcat` and `rvsec-logger-csv`, not in `rvsec-core`. `rg` is not installed — use `grep -rE`. Soft dependency: task 5.9 (consumer matrix) cites Group 1's definitions — write it last. Environment: prefix EVERY Java/Maven command line (the two `mvn -q test` runs, in `rvsec-android/rvsec-logger-logcat` and `rv-monitor/rv-monitor-rt`) with `export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH` (shell state does not persist between tool calls; the default JDK is 25); pytest always with `--import-mode=importlib -o "addopts="`; no monitor generation in this group, and no `mvn install` — the reactor install is the orchestrator's, between waves. Git: one repository (rv-android is a subdirectory of `…/rvsec`); every `git status`/`git diff` carries a pathspec (`git status --short -- <paths>`; `git diff --cached --stat -- <paths>`); commits are made by the orchestrator, after this group's summary, with explicit pathspecs — this group does not commit, and never `git add -A`/`git commit -a`; the `rv-monitor/rv-monitor-rt` edit (`ViolationRecorder.java`) is committed separately from Group 3's `rv-monitor/rv-monitor` edits (same tree, different submodules).

## Subagent brief

Read `design.md` D-3 and D-8, and the four deltas `analysis` (INV-ANA-08/62/63), `core` (INV-CORE-25/41/56/57), `platform` (INV-PLT-19/32), `campaign-analysis` (INV-CAN-04/25/26), plus the collector part of `instrumentation` (`Requirement: Violation Line Emission by the Collector`). Count, never drop; sentinels, never fabricated values; one `unique_msg` constructor. P3: delete the four other constructors, do not wrap them. Property tests are the deliverable of the parser work.

## Files

Java (git root `…/workspace-rv/rvsec`):
| file | lines | edit |
|---|---|---|
| `rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` | 56 | `:36-40` build the line with `escape(getExpecting().trim())`; the existing `escapeSpecialCharacters :42-49` is dead (call commented `:38`) — replace it by an `escape` that maps `\n`→`\\n` and leaves commas; `null` expecting → `v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''`; new `ErrorCollectorTest` |
| `rvsec/rvsec-logger-csv/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` | 92 | `escape() :84-91` — align with the logcat rule (same newline handling); header `:14` unchanged |
| `rv-monitor/rv-monitor-rt/src/main/java/com/runtimeverification/rvmonitor/java/rt/ViolationRecorder.java` | 141 | `makeRelevantList :87-105`: a frame whose `fileName == null` and whose class is a monitoring-runtime class is excluded (today fail-open per frame; `getLineOfCode :53-60` returns `relevantStack.get(0)`); new `ViolationRecorderTest` |
| `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java` | 146 | no edit in this group (identity is Group 9); note `toString :143` renders `expecting %s`, so consumers of `toString()` see `expecting` twice on a `msg='expecting one of … but found …'` envelope — the logcat collector emits `getErrorSummary()+","+getExpecting()` (`ErrorCollector.java:38`) and `errors.csv` carries the envelope as written, so this is a `toString()`-only artefact and not a rule on `msg` |

Python (`rv-android/`):
| file | lines | edit |
|---|---|---|
| `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` | 466 | `_parse_error_message :285-372`: keep Format 2 by structure (`len(parts) >= 6`, rejoin `parts[6:]`); parse the envelope of field 7 into `code, event, obj, val, exp, msg` (regex over `key=value` / `key='…'` with `\'` escape and `\\n`→newline restored; `ParserDiagnostics` on `LogcatRepository.parser_diagnostics` and shared with `CoverageTracker` on the live path); unclosed final quote → `truncated=True`; sentinels `error_type=UNSPECIFIED`, `source=UNSPECIFIED:0`, `code/event=UNSPECIFIED`; Format-1 (`endswith("went into an error state.") :306`) whose regex `:386` fails → count `format1_regex_failed`, return `None` (today falls into the comma path and scrambles); `parse_logcat_file :202-203` re-raises after logging the line number; `ParserDiagnostics` (13 counters: `lines_not_threadtime`, `lines_other_tag`, `format1_regex_failed`, `format2_short`, `format3_unresolved`, `unrecognised`, `continuation_lines`, `truncated_envelopes`, `sentinel_error_type`, `sentinel_source`, `sentinel_code`, `sentinel_event`, `envelope_forbidden_chars`) attached to `LogcatRepository.parser_diagnostics`; discard points to cover: `:268-270`, `:235-248`, `:306-316`, `:321-350`, `:355-368`, `:371-372`, `_normalize_frame :87-95` (warning only, keep) |
| `modules/rv-coverage/tests/parser/log/test_logcat_parser.py` | 762 | property tests: comma inside `exp`; `\'`; `\n` (line split → second half `continuation_lines`); `:::` inside a value → `envelope_forbidden_chars`, record kept; 4068-byte cut → `truncated`; sentinels; Format-1 no fall-through; counters sum = lines read |
| `modules/rv-android-core/src/rv_android_core/domain/log.py` | 468 | `RvErrorLog` gains `code, event, obj, val, exp, msg: str` (defaults `code`/`event` = `UNSPECIFIED`, others `""`, per specs/core and specs/analysis — the defaults keep `logcat_parser.py:309-316,341-350,366-368` working until 5.3), `truncated: bool = False`; `unique_msg :113` → seven parts `class:::method:::spec:::error_type:::code:::event:::message` (sentinel `UNSPECIFIED`); identity `:181-187` unchanged in form (it is `unique_msg`); `RvDiagnosticEvent :269-271` untouched |
| `modules/rv-android-core/tests/domain/test_log.py` | 398 | update |
| `modules/rv-platform/src/rv_platform/components/result_processor.py` | 1145 | writer `:558-576` header → `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg`; rows `:638-652`; delete fallbacks `:631,:999,:1038`; `:654-655` and `:1046-1047` count and log as error (never a WARNING that hides the task's rows); `:333-338` count |
| `modules/rv-platform/tests/components/test_result_processor.py` | 1569 | header test; failure counted test; also the `Diagnostic Events CSV Generation` scenario now expects the 13-column `errors.csv` |
| `modules/aperv-tool/src/aperv_tool/analysis/violations.py` | 320 | `ERRORS_CSV_HEADER :63-75` → 13 columns; `read_errors_csv :215-297` returns `(rows, CsvDiagnostics)` with seven parts (`:253-254` → `parts[3]`, `parts[4]`, `parts[5]`), else `unique_msg_unparsed`; `unique_msg_disagrees` when the parts disagree with the row's own columns (specs/campaign-analysis); `parse_payload :140-160` envelope → `code/event/obj/val/exp/msg`, `shape_ok=False` + `envelope_truncated`/`envelope_malformed`; `ViolationEvent` fields |
| `modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py` | 655 | `_parse_payload :454-461` deleted → call `violations.parse_payload` (one parser); `read_tagged_lines :364-379` count skipped lines |
| `modules/aperv-tool/src/aperv_tool/analysis/step_bundle.py` | — | task 5.7: `:286` already calls `violations.read_logcat` (so it already goes through `parse_payload`); adapt it to the `(events, LogcatDiagnostics)` return of 5.6 in the same commit and carry the counters onto the bundle (`BundleDiagnostics :106` has none today; INV-CAN-04, INV-CAN-25/26) so a step whose lines were discarded is not read as a step that had none |
| `modules/aperv-tool/tests/test_step_bundle.py` | 422 (existing, 12 tests) | task 5.7: +2 — envelope fields present on a bundled violation; counters non-`None` on a bundle built from a stream carrying a discarded line |
| `modules/aperv-tool/tests/test_violations.py` | 125 | +4 tests (13-col accepted; 11-col `ValueError` naming expected header; 5-part `unique_msg` unparsed + `unique_msg_disagrees`; truncated envelope) |
| `scripts/regenerate_results/regenerate_container.py` | 346 | `:244` builds `unique_msg` → import `RvErrorLog` and use it (or delete the local composition) |
| `scripts/rv_oracle_common.py` | 174 | `:73-81` reads `parts[3]`/`parts[4]` — require seven parts, name the parts |
| `data/gh104/consumer_matrix.md` | new | see task 5.9 — includes the readers the first inventory missed: `rv_android_core/domain/coverage.py:397,575,627` (`unique_errors`), `execution_status.py:87`, `scripts/derive_l3b_oracle.py`, `scripts/derive_l3c_oracle.py`, `scripts/regenerate_results/verify.py`, `scripts/jca557_*.py`, `experimento-gov/scripts/violations_detail.py` and `experimento-comp162-ajc/scripts/mop_diff.py` (parse the `RVSEC :` logcat line), the frozen `audit/20260808_validacao_jca_android/**/*.py`, and the tests under `rv-platform`, `rv-coverage`, `rv-android-core`, `aperv-tool` that build `unique_msg` fixtures; closed by a `grep -rE`-backed check |

## Task 5.4 — `log.py` first, and the grep gate's two permitted composers

`RvErrorLog` gains the six envelope fields with defaults and `unique_msg` becomes the seven-part string (table above). The grep gate `tests/parity/test_gh104_unique_msg_built_once.py` searches the f-string fragment `:::{` over `modules/ scripts/` (non-test) and permits exactly **two** composers: `RvErrorLog.unique_msg` (`log.py:113`, the seven-part violation identity) and **`RvDiagnosticEvent.unique_msg`** (`log.py:266-270`, the 4-field diagnostic variant `category:::class:::method:::message`, untouched by this group). Everything else that composes `:::{` — `result_processor.py:631,999,1038`, `regenerate_container.py:244` — is deleted (5.5, 5.8) and the gate fails on any third composer.

## Grammar to implement (design D-3)

`v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'` — commas allowed in values; `\n` and `:::` forbidden (count if seen); `'` escaped `\'`; unclosed final quote = truncated; `val` capped at 512 by the producer; logcat payload bound 4068 bytes (API 30).

## Commands

```bash
uv run pytest --import-mode=importlib -o "addopts=" modules/rv-coverage/tests -q        # baseline today: 266 passed
uv run pytest --import-mode=importlib -o "addopts=" modules/aperv-tool/tests -q         # baseline today: 704 passed, 22 skipped
uv run pytest --import-mode=importlib -o "addopts=" modules/rv-platform/tests -q
uv run pytest --import-mode=importlib -o "addopts=" modules/rv-android-core/tests -q
grep -rn ':::{' modules/ scripts/ --include=*.py | grep -v tests   # after 5.4/5.8: only log.py composes — RvErrorLog.unique_msg (:113) and RvDiagnosticEvent.unique_msg (:266-270) — (the f-string fragment `:::{` is what result_processor.py:631,999,1038 and regenerate_container.py:244 contain; a grep for the bare ':::' misses them); violations.py / rv_oracle_common.py only read
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH; cd ../rvsec/rvsec-android/rvsec-logger-logcat && mvn -q test
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH; cd ../rvsec/rv-monitor/rv-monitor-rt && mvn -q test
# 5.10
/rv-qa-lint-fix rv-coverage
/rv-test-run modules/rv-coverage
/rv-test-run modules/rv-android-core
/rv-test-run modules/rv-platform
/rv-test-run modules/aperv-tool   # covers test_violations.py and the new test_step_bundle.py tests of task 5.7
```

## Acceptance

- Every counter named above exists and the sum of records + counted lines equals lines read on the parser fixtures.
- Sentinels appear exactly where a value used to be fabricated; the same `[helper] ::: …` line yields the same count in `rv-coverage` and `aperv_tool` (both count it, neither invents a record).
- `errors.csv` header is the 13-column string; `ERRORS_CSV_HEADER` equal to it; cmp162 fixtures (11 columns) are **not** modified — they are read by Group 1's own frozen 11-column reader, never by this module's `read_errors_csv` once the header is 13 columns; `test_errors_csv_of_the_campaign` therefore moves to a 13-column synthetic fixture.
- `grep` gate: one `unique_msg` constructor for violations (`RvErrorLog.unique_msg`), with `RvDiagnosticEvent.unique_msg` as the only other permitted `:::{` composer.
- Consumer matrix written with a verdict per consumer, and the grep-backed inventory check (`grep -rlE "errors\.csv|unique_msg|ERRORS_CSV_HEADER|read_errors_csv|RVSEC\s*:"` over `modules/ scripts/ experimento-*/ audit/`, `.venv`/`backup/` excluded — `RVSEC\s*:` because `violations_detail.py`, `mop_diff.py`, `consolidate_gov.py` write `RVSEC   :`/`RVSEC\s+:`; also catches `scripts/consolida_comparacao_aperv.py`, `experimento-20260721/scripts/consolidate_compare.py`, `aperv_tool/analysis/loader.py`, `tests/domain/test_log.py`; `execution_status.py` is a root-level untracked script, not `domain/`; `regenerate_container.py:246` writes a 10-column layout) has no hit without a row.
