# Group 5 — E3: honest transport

Tracked checkboxes: `tasks.md` §5. Wave 1; disjoint from Groups 1/2/3/4/6/7; Group 9 (E6) depends on it. Soft dependency: task 5.8 (consumer matrix) cites Group 1's definitions — write it last.

## Subagent brief

Read `design.md` D-3 and D-8, and the four deltas `analysis` (INV-ANA-08/62/63), `core` (INV-CORE-25/41/56/57), `platform` (INV-PLT-19/30), `campaign-analysis` (INV-CAN-04/25/26), plus the collector part of `instrumentation` (`Requirement: Violation Line Emission by the Collector`). Count, never drop; sentinels, never fabricated values; one `unique_msg` constructor. P3: delete the four other constructors, do not wrap them. Property tests are the deliverable of the parser work.

## Files

Java (git root `…/workspace-rv/rvsec`):
| file | lines | edit |
|---|---|---|
| `rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` | 56 | `:36-40` build the line with `escape(getExpecting().trim())`; the existing `escapeSpecialCharacters :42-49` is dead (call commented `:38`) — replace it by an `escape` that maps `\n`→`\\n` and leaves commas; `null` expecting → `v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''`; new `ErrorCollectorTest` |
| `rvsec/rvsec-logger-csv/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` | 92 | `escape() :84-91` — align with the logcat rule (same newline handling); header `:14` unchanged |
| `rv-monitor/rv-monitor-rt/src/main/java/com/runtimeverification/rvmonitor/java/rt/ViolationRecorder.java` | 141 | `makeRelevantList :87-105`: a frame whose `fileName == null` and whose class is a monitoring-runtime class is excluded (today fail-open per frame; `getLineOfCode :53-60` returns `relevantStack.get(0)`); new `ViolationRecorderTest` |
| `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java` | 146 | no edit in this group (identity is Group 9); note `toString :143` renders `expecting %s` — envelope `msg` must not start with `expecting` |

Python (`rv-android/`):
| file | lines | edit |
|---|---|---|
| `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` | 466 | `_parse_error_message :285-372`: keep Format 2 by structure (`len(parts) >= 6`, rejoin `parts[6:]`); parse the envelope of field 7 into `code, event, obj, val, exp, msg` (regex over `key=value` / `key='…'` with `\'` escape); unclosed final quote → `truncated=True`; sentinels `error_type=UNSPECIFIED`, `source=UNSPECIFIED:0`, `code/event=UNSPECIFIED`; Format-1 (`endswith("went into an error state.") :306`) whose regex `:386` fails → count `format1_regex_failed`, return `None` (today falls into the comma path and scrambles); `parse_logcat_file :202-203` re-raises after logging the line number; `ParserDiagnostics` (13 counters: `lines_not_threadtime`, `lines_other_tag`, `format1_regex_failed`, `format2_short`, `format3_unresolved`, `unrecognised`, `continuation_lines`, `truncated_envelopes`, `sentinel_error_type`, `sentinel_source`, `sentinel_code`, `sentinel_event`, `envelope_forbidden_chars`) attached to `LogcatRepository.parser_diagnostics`; discard points to cover: `:268-270`, `:235-248`, `:306-316`, `:321-350`, `:355-368`, `:371-372`, `_normalize_frame :87-95` (warning only, keep) |
| `modules/rv-coverage/tests/parser/log/test_logcat_parser.py` | 762 | property tests: comma inside `exp`; `\'`; `\n` (line split → second half `continuation_lines`); `:::` inside a value → `envelope_forbidden_chars`, record kept; 4068-byte cut → `truncated`; sentinels; Format-1 no fall-through; counters sum = lines read |
| `modules/rv-android-core/src/rv_android_core/domain/log.py` | 468 | `RvErrorLog` gains `code, event, obj, val, exp, msg: str | None`, `truncated: bool`; `unique_msg :113` → seven parts `class:::method:::spec:::error_type:::code:::event:::message` (sentinel `UNSPECIFIED`); identity `:181-187` unchanged in form (it is `unique_msg`); `RvDiagnosticEvent :269-271` untouched |
| `modules/rv-android-core/tests/domain/test_log.py` | 398 | update |
| `modules/rv-platform/src/rv_platform/components/result_processor.py` | 1145 | writer `:558-576` header → `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg`; rows `:638-652`; delete fallbacks `:631,:999,:1038`; `:654-655` and `:1046-1047` count and log as error (never a WARNING that hides the task's rows); `:333-338` count |
| `modules/rv-platform/tests/components/test_result_processor.py` | 1569 | header test; failure counted test; also the `Diagnostic Events CSV Generation` scenario now expects the 13-column `errors.csv` |
| `modules/aperv-tool/src/aperv_tool/analysis/violations.py` | 320 | `ERRORS_CSV_HEADER :63-75` → 13 columns; `read_errors_csv :239-297` seven parts (`:253-254` → `parts[3]`, `parts[4]`, `parts[5]`), else `unique_msg_unparsed`; `parse_payload :140-160` envelope → `code/event/obj/val/exp/msg`, `shape_ok=False` + `envelope_truncated`/`envelope_malformed`; `ViolationEvent` fields |
| `modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py` | 655 | `_parse_payload :454-460` → call `violations.parse_payload` (one parser); `read_tagged_lines :364-379` count skipped lines |
| `modules/aperv-tool/tests/test_violations.py` | 125 | +4 tests (13-col accepted; 11-col `ValueError` naming expected header; 5-part `unique_msg` unparsed; truncated envelope) |
| `scripts/regenerate_results/regenerate_container.py` | 346 | `:244` builds `unique_msg` → import `RvErrorLog` and use it (or delete the local composition) |
| `scripts/rv_oracle_common.py` | 174 | `:73-81` reads `parts[3]`/`parts[4]` — require seven parts, name the parts |
| `data/gh104/consumer_matrix.md` | new | see task 5.8 — includes the readers the first inventory missed: `rv_android_core/domain/coverage.py:397,575,627` (`unique_errors`), `execution_status.py:87`, `scripts/derive_l3b_oracle.py`, `scripts/derive_l3c_oracle.py`, `scripts/regenerate_results/verify.py`, `scripts/jca557_*.py`, `experimento-gov/scripts/violations_detail.py` and `experimento-comp162-ajc/scripts/mop_diff.py` (parse the `RVSEC :` logcat line), the frozen `audit/20260808_validacao_jca_android/**/*.py`, and the tests under `rv-platform`, `rv-coverage`, `rv-android-core`, `aperv-tool` that build `unique_msg` fixtures; closed by an `rg`-backed check |

## Grammar to implement (design D-3)

`v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'` — commas allowed in values; `\n` and `:::` forbidden (count if seen); `'` escaped `\'`; unclosed final quote = truncated; `val` capped at 512 by the producer; logcat payload bound 4068 bytes (API 30).

## Commands

```bash
uv run pytest --import-mode=importlib -o "addopts=" modules/rv-coverage/tests -q        # baseline today: 266 passed
uv run pytest --import-mode=importlib -o "addopts=" modules/aperv-tool/tests -q         # baseline today: 704 passed, 22 skipped
uv run pytest --import-mode=importlib -o "addopts=" modules/rv-platform/tests -q
uv run pytest --import-mode=importlib -o "addopts=" modules/rv-android-core/tests -q
grep -rn "':::'\|\":::\"" modules/ scripts/ --include=*.py | grep -v tests   # after 5.4/5.7: only log.py composes; violations.py / rv_oracle_common.py read
cd ../rvsec/rvsec-android/rvsec-logger-logcat && mvn -q test; cd ../../../rv-monitor/rv-monitor-rt && mvn -q test
```

## Acceptance

- Every counter named above exists and the sum of records + counted lines equals lines read on the parser fixtures.
- Sentinels appear exactly where a value used to be fabricated; the same `[helper] ::: …` line yields the same count in `rv-coverage` and `aperv_tool` (both count it, neither invents a record).
- `errors.csv` header is the 13-column string; `ERRORS_CSV_HEADER` equal to it; cmp162 fixtures (11 columns) are **not** modified — they are read by Group 1's own frozen 11-column reader, never by this module's `read_errors_csv` once the header is 13 columns; `test_errors_csv_of_the_campaign` therefore moves to a 13-column synthetic fixture.
- `grep` gate: one `unique_msg` constructor.
- Consumer matrix written with a verdict per consumer, and the `rg`-backed inventory check (`rg -l "errors.csv|unique_msg|ERRORS_CSV_HEADER|read_errors_csv|RVSEC :"` over `modules/ scripts/ experimento-*/ audit/`, `.venv`/`backup/` excluded) has no hit without a row.
