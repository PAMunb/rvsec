# gh104 — consumer matrix: who reads the violation record, and what gh104 does to them

Two things change shape in this campaign and both are read in many places. The **message**
becomes a versioned envelope in the seventh comma field of an `RVSEC` line
(`v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='…' exp='…' msg='…'`), and
`unique_msg` grows from five `:::` parts to seven
(`class:::method:::spec:::error_type:::code:::event:::message`), which takes `errors.csv`
from eleven columns to thirteen (`code` and `event` after `source`).

Neither change is backward compatible and neither is meant to be (P3 of `CLAUDE.md`): a
shim would leave two identities in the tree and no way to tell which produced a number.
What this file provides instead is the list of everything that reads the record, with a
verdict per reader — **migrated** (it was changed in this campaign), **frozen-with-reason**
(it reads a corpus of the previous era and must go on reading it as that era wrote it), or
**unaffected** (it names the artefact without reading its violation fields) — plus, in the
second half, the four tasks of this change that edit runtime code the **frozen `jca` set
executes unchanged**, so that a later `jca` replay is read against the right runtime.

The closure check is a grep, run from `rv-android/`:

```bash
grep -rlE "errors\.csv|unique_msg|ERRORS_CSV_HEADER|read_errors_csv|RVSEC\s*:" \
  modules/ scripts/ experimento-*/ audit/ \
  | grep -vE '\.venv|/backup/|__pycache__|mypy_cache'
```

`RVSEC\s*:` is in the pattern because the shell scripts and the campaign consolidators
match the tag as `RVSEC   :` or `RVSEC\s+:` rather than reading `errors.csv` at all. Every
hit of that grep that is code has a row below; hits that are recorded data — a run's
`errors.csv`, a `results.json`, a manifest, a report — are listed once at the end as data,
not as readers.

## 1. Readers

### 1.1 The transport itself (migrated by this group)

| reader | what it reads | verdict | note |
|---|---|---|---|
| `modules/rvsec-logger-logcat/.../ErrorCollector.java` (`buildLine`, `escape`) | writes the line | migrated (5.1) | `\n` → `\\n`; `null` expecting → the sentinel envelope. It is the producer, so every row below inherits from it. |
| `rvsec/rvsec-logger-csv/.../ErrorCollector.java` (`escape`) | writes `output/summary.csv` | migrated (5.1) | same newline rule as the logcat collector, applied before the CSV quoting rather than after it. |
| `rv-monitor/rv-monitor-rt/.../ViolationRecorder.java` (`makeRelevantList`) | chooses the reported `location` | migrated (5.2) | a monitoring-runtime frame with `fileName == null` is excluded; `location` is part of the dedupe identity. |
| `modules/rv-coverage/.../parser/log/logcat_parser.py` | every `RVSEC`/`RVSEC-COV` line | migrated (5.3) | envelope parsed into `code/event/obj/val/exp/msg`; sentinels named; thirteen counters on `ParserDiagnostics`; Format-1 no longer falls through into the comma path. |
| `modules/rv-coverage/.../analysis/coverage/tracker.py:411` | the live line stream | migrated (5.3) | passes `self.repository.parser_diagnostics`, so the live and the offline path count on one object. |
| `modules/rv-android-core/.../domain/coverage.py` (`LogcatRepository`, `ParserDiagnostics`) | `unique_errors` at `:601,:688,:740` | migrated (5.3/5.4) | the set is keyed by `unique_msg`, so its cardinality changes era with the key; the counter object is defined here because the repository that carries it is. |
| `modules/rv-android-core/.../domain/log.py` (`RvErrorLog.unique_msg`) | composes the key | migrated (5.4) | the **only** violation-key constructor; `RvDiagnosticEvent.unique_msg` (four parts, a different record type) is the only other permitted `:::{` composer. Gated by `tests/parity/test_gh104_unique_msg_built_once.py`. |
| `modules/rv-platform/.../components/result_processor.py` | writes `errors.csv`, `results.json` | migrated (5.5) | thirteen columns; the three `unique_msg` fallbacks deleted; a write or extraction failure is an ERROR counted onto `TaskResult.write_errors`. |
| `modules/aperv-tool/.../analysis/violations.py` | `errors.csv`, `RVSEC` payloads | migrated (5.6) | `ERRORS_CSV_HEADER` is the 13-tuple and any other header raises; `unique_msg` read as exactly seven parts; `parse_payload` parses the envelope; `read_logcat` returns `(events, LogcatDiagnostics)`. |
| `modules/aperv-tool/.../analysis/clock_logcat_join.py` | `RVSEC` payloads, per step | migrated (5.6) | its private `_parse_payload` is deleted and it calls `violations.parse_payload`; `read_tagged_lines` returns a `TaggedLines` list carrying `skipped`. |
| `modules/aperv-tool/.../analysis/step_bundle.py:286` | the run's violations, per step | migrated (5.7) | adapted to the `(events, LogcatDiagnostics)` return and carries those counters on `BundleDiagnostics.violations`, so a step whose lines were discarded is not read as a step that had none. |
| `modules/aperv-tool/.../analysis/monitored_ops.py:136` | `RVSEC-COV` payloads | unaffected | it calls `read_tagged_lines` and indexes the result; `TaggedLines` is a `list` subclass precisely so this call site and its tests are untouched. |
| `modules/aperv-tool/.../analysis/loader.py:19-22` | names `errors.csv` in prose | unaffected | it declares that the event streams belong to the stream readers and that it neither reads nor counts them. |
| `scripts/regenerate_results/regenerate_container.py` | rebuilds a container's CSVs from logcats | migrated (5.8) | the local five-part composition is deleted and `unique_msg` is read from the record. It still writes its own **10-column** errors layout (no `source`, no `code`/`event`) — that layout is the historical one it exists to reproduce, and it is named here so nobody reads its file as an `errors.csv` of the current schema. |
| `scripts/rv_oracle_common.py` | `unique_msg` of an oracle row | migrated (5.8) | `unique_msg_parts()` requires exactly seven parts and names them; `error_type()` still reads part 3 (unchanged index), `message()` moves from part 4 to part 6, and `code()`/`event()` are added. A key of the five-part era yields `Unknown`/`""` rather than a part read under the wrong name. |
| `scripts/derive_l3b_oracle.py:126,130`, `scripts/derive_l3c_oracle.py:118,127` | `error_type(...)`, `message(...)` | migrated by dependency (5.8) | they call `rv_oracle_common`; their `error_type` is index-stable, their `message` is not, which is why the split is centralised in one helper rather than repeated at four call sites. |
| `execution_status.py:87` (repository root, untracked) | `error.unique_msg` | unaffected | it prints the key as an opaque string; it never splits it. |
| `experimento-gh104/scripts/gh104_gates.py:82-108` | the campaign's own `errors.csv` gate | already migrated (campaign, ahead of this group) | it declares **both** headers — `ERRORS_CSV_HEADER` (13 columns, byte-identical to the one task 5.5 writes and task 5.6 expects) and `ERRORS_CSV_HEADER_LEGACY` (11 columns) — so gate G3 can say *which* era a file belongs to instead of only that the header is wrong. G4 checks that every `unique_msg` has seven `:::` parts. |

### 1.2 Readers of a corpus of the previous era (frozen, with the reason)

| reader | what it reads | verdict | reason |
|---|---|---|---|
| `scripts/gh104_baseline.py` | comp162 (11 columns) and the article dataset (10 columns) | frozen-with-reason | it declares **its own** readers for both layouts rather than importing `read_errors_csv`, because that function's header is rewritten by task 5.6 and an import would resolve to whatever the header is on the day the script runs — the opposite of what a baseline is for (INV-CAN-25). Its `error_type` freeze item (`unique_msg.split(':::')[3]`, `data/gh104/definitions.md`) is index-stable across the two eras and needs no change; its `message` reading does not go through part 4. |
| `data/gh104/definitions.md` | the freeze-item registry the baseline enforces | frozen-with-reason | records the **instrument discontinuity**: the article dataset has no `source` column, so its site key is `(spec, class, method)` while comp162's is `(spec, class, method, source)`. gh104 adds no column to either corpus; it adds them to the layout written from now on. |
| `modules/aperv-tool/tests/fixtures/cmp162_manifest.json`, `build_cmp162_manifest.py` | the pinned cmp162 tree | frozen-with-reason | cmp162 is a fixture, not a corpus. Its `errors.csv` files stay 11-column and are **not** rewritten; `test_errors_csv_of_the_campaign` moved to a 13-column synthetic fixture in task 5.6, because the shared reader now rejects the 11-column layout by design. |
| `scripts/regenerate_results/verify.py:46` | counts `RVSEC\s*:` lines against `errors.csv` rows | frozen-with-reason | a line count, not a field read: it is unaffected by the envelope and by the column count, and it remains a valid 1:1 check across both eras. |
| `scripts/jca557_vs_paper.py:52`, `scripts/jca557_quarantine_impact.py:104` | the article's `exp01_jca_errors.csv` | frozen-with-reason | the published 10-column dataset. Nothing in gh104 rewrites it; the scripts read it by column name and never split `unique_msg`. |
| `scripts/gh91_compare_consolidation.py:85-86` | a consolidation of the previous schema | frozen-with-reason | it names the pre-`source` column list in a comment and drops `class`/`method`/`unique_msg` before comparing — the fields gh104 changes are exactly the ones it already excludes. |
| `audit/20260808_validacao_jca_android/**` (`gama_batcha_errors.py`, `gama_errors_batch{B,C,D}.py`, `juiz_build_csv.py`, `set/set_cons_hist.py` and their claim CSVs and reports) | the audit's own frozen evidence | frozen-with-reason | a closed audit. Its numbers are cited in the change's reasoning and must reproduce byte-for-byte; nothing in it is re-run against a post-gh104 corpus. |
| `experimento-comp162/**`, `experimento-comp162-ajc/**`, `experimento-gov/results_g2/**`, `experimento-rearch-aperv/**` recorded outputs | recorded runs | frozen-with-reason | data of the previous era; see §3. |

### 1.3 Readers that regex the free text of `message` (the reason this change exists)

| reader | what it matches | verdict | note |
|---|---|---|---|
| `experimento-gov/scripts/violations_detail.py:9,22` | `RVSEC   :` then the seven comma fields, and the free text of field 7 | frozen-with-reason | it documents the seven-field grammar and reads field 7 as prose. On a `jca_android` run field 7 is an envelope and its prose reading degrades to showing the envelope verbatim — legible, but no longer the sentence it was written against. It is a campaign-local reporting script over a recorded `gov` run and is not re-pointed at the successor set. |
| `experimento-gov/scripts/consolidate_gov.py:26-27` | `RVSEC\s+:` line counts and a type breakdown | frozen-with-reason | the breakdown keys off field 6 (`errorType`), which the envelope does not touch; the line count is era-independent. |
| `experimento-comp162-ajc/scripts/mop_diff.py:26,84` | the seven fields, with `detail` (field 7) deliberately **outside** the identity | frozen-with-reason | it already excludes the free text from the key it compares, which is exactly the property that makes it survive the message rewrite. |
| `scripts/consolida_comparacao_aperv.py:26`, `experimento-20260721/scripts/consolidate_compare.py:35`, `experimento-gh104/scripts/consolidate.py:56` | `\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$` — a line counter | unaffected | matches the first field only. `mop_total` counts lines and is era-independent. |
| `experimento-gh104/scripts/msg_diff.py:39-41` | the two eras' logcats, deliberately not their `errors.csv` | migrated (this campaign's instrument) | it states its own reason: `errors.csv` changes schema between the eras (11 → 13 columns, task 5.6), so the diff is taken on the logcat where both eras are directly comparable. |
| `scripts/drive_cryptoapp.py:35,89-94` | `RVSEC:` and a substring of the violation line | frozen-with-reason | a manual smoke driver whose expectations are substrings of the old message text. It will report no match on a `jca_android` build until its fragments are rewritten; it drives nothing that produces a published number. |
| `ase-journal/docs/20260806_owasp_cwe_mapping_gen.py:47-54` (`but found (.*?)`), `validator/oracles/cryptoapp-oracle.yaml` (six substrings driving `TraceComparator.java:596-598`), `.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py:35` | the free text of `message` | frozen-with-reason | outside the four roots the closure grep scans (they live in sibling trees and in the skills directory), named here because design D-8 names them. Each reads the pre-change sentence; each belongs to an artefact of the previous era or is a template. |

### 1.4 Tests that build `unique_msg` or `RVSEC :` fixtures

These are hits of the closure grep, and they are readers in the sense that matters: each
pins a shape, so each fails loudly if the shape moves without them. All were updated with
their module in this campaign except where noted.

| test | pinned shape | verdict |
|---|---|---|
| `modules/rv-android-core/tests/domain/test_log.py` | the key, `to_dict()` keys, the identity | migrated (5.4) — `TestSevenPartIdentity` added |
| `modules/rv-android-core/tests/domain/test_coverage.py`, `test_diagnostic_event.py` | `unique_errors`, the four-part diagnostic key | unaffected |
| `modules/rv-android-core/tests/util/android/test_logcat_manager.py` | `RVSEC :` line fixtures | unaffected — line transport, not fields |
| `modules/rv-coverage/tests/parser/log/test_logcat_parser.py` | the three formats, the counters, the envelope | migrated (5.3) — `TestEnvelopeAndDiagnostics`, `TestCounterArithmetic`, `TestEnvelopeProperties` added |
| `modules/rv-coverage/tests/parser/log/test_frame_form_normalization.py` | frame normalisation, FSM `source` | migrated (5.3) — the FSM `source` expectation moved from `Unknown Source:1` to `UNSPECIFIED:0` |
| `modules/rv-coverage/tests/parser/log/fixtures/frame_form_corpus.py`, `test_diagnostic_integration.py` | corpus values, diagnostic blocks | unaffected |
| `modules/rv-coverage/tests/analysis/coverage/test_tracker*.py`, `test_analyzer_branches.py` | `RVSEC :` fixtures through the live path | unaffected — they assert on records, not on counters |
| `modules/rv-platform/tests/components/test_result_processor.py` | the header, the rows, the failure path | migrated (5.5) |
| `modules/rv-platform/tests/components/test_logcat.py`, `tests/execution/test_resume.py` | `RVSEC :` fixtures | unaffected |
| `modules/aperv-tool/tests/test_violations.py` | the header, the envelope, the key | migrated (5.6) |
| `modules/aperv-tool/tests/test_step_bundle.py` | the step timeline | migrated (5.7) — two tests added |
| `modules/aperv-tool/tests/test_clock_logcat_join.py`, `test_clock_logcat_join_extraction.py`, `test_monitored_ops.py` | `read_tagged_lines` and its payloads | unaffected — the `TaggedLines` return keeps the list contract |
| `experimento-cal/tests/test_consolidate_verify.py:57` | a synthetic `RVSEC:` line with a four-field payload | frozen-with-reason — a line-count fixture of a closed calibration campaign |
| `tests/parity/test_gh104_unique_msg_built_once.py` | that exactly one composer exists | new (5.4) |

### 1.5 Documentation naming the schema

`modules/rv-platform/CLAUDE.md`, `modules/rv-platform/README.md`,
`modules/rv-platform/docs/architecture.md`, `modules/rv-android-core/docs/architecture.md`,
`modules/rv-experiment/docs/architecture.md`, `scripts/regenerate_results/README.md`,
`experimento-20260508/README.md`, `experimento-20260604/CLAUDE.md`,
`experimento-gh104/{README,CONTEXTO,PRONTIDAO}.md` and
`experimento-gh104/docs/gh104_mudancas_observaveis.md` all name `errors.csv` or its columns.
They are documentation, not readers: none is executed. The module docs are synchronised by
the documentation task of this change, not by this group.

## 2. Shared runtime the frozen `jca` executes

Four tasks of gh104 edit runtime code that the **frozen `jca` monitors execute unchanged**.
The frozen set's `.mop` files are not touched by any of them, but the code they call at
report time is, so a replay of `jca` after this change is not run against the runtime the
published dataset was produced with. Each row states the effect and the artefact that
evidences it.

| task | what changes in the shared runtime | effect on a `jca` run | evidencing artefact |
|---|---|---|---|
| 5.1 | logcat `ErrorCollector`: `\n` → `\\n` escaping; `null` expecting → the sentinel envelope | a `jca` message carrying a newline (none of the 19 message texts does today) becomes one logcat line instead of two; a `null` expecting — which the 21 three-argument `@fail` sites pass — renders `v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''` instead of the literal `null`. **The line text of every `@fail` report of `jca` changes** (`…,null` → `…,v=1 code=UNSPECIFIED …`). `unique_msg` and the `ErrorSummary` identity do not change: neither reads `expecting`. | the line-text diff over `data/gh104/traces`, taken before and after the collector change |
| 5.2 | `ViolationRecorder.makeRelevantList`: a monitoring-runtime frame whose `fileName` is `null` is excluded | `__LOC` — the `source` column, `getLineOfCode()` returning the first relevant frame — can move from a runtime frame to the application frame on stacks where the runtime frame carried no file name. That is a `source` change on those rows, and therefore a different `ErrorSummary` identity for them, since `location` is in its 5-tuple. The count of rows whose `source` moves is the measurement. | the `source` diff over the same harness traces |
| 3.7 | the generated dispatcher releases its lock on every exit (`try`/`finally` around the explicit `tryLock` form) | no report changes. A thread that raises inside a dispatcher no longer leaves the lock held, so a `jca` run that today stalls after an exception — the `NullPointerException` in `KeyPairGeneratorSpec.validate` of task 8.4 — keeps reporting after it. The consequence is **more** rows, none of them a new accusation. | task 3.8's regeneration diff |
| 9.2 | `ErrorSummary.equals`/`hashCode` gain `code` and `event` | on `jca` both are `UNSPECIFIED` on every row, because the frozen set writes no envelope, so the identity is unchanged in effect: the collector dedupes on exactly the same set as before. | the comp162 recount of task 9.x (E6) |

Rows 3.7 and 9.2 are written from the change's task descriptions: they belong to other
groups, and this file records their effect on a `jca` run rather than their implementation.

## 3. Hits that are data, not readers

Recorded outputs matched by the closure grep, listed once so the check closes: the
`errors.csv` and `results.json` files under `experimento-comp162/results_smoke/`,
`experimento-comp162-ajc/results_smoke/`, `experimento-gov/results_g2/` and
`experimento-rearch-aperv/results_smoke/`; the claim CSVs, reports and handoffs under
`audit/20260808_validacao_jca_android/`; `modules/aperv-tool/tests/fixtures/cmp162_manifest.json`;
`experimento-comp162-ajc/20260813_relatorio_fase_a.md`; `experimento-20260508/RELATORIO.md`
and `experimento-20260604/RELATORIO.md`; `experimento-gov/scripts/hourly_monitor.sh` (counts `RVSEC   :` lines as the campaign's
primary metric and reads no field of them) and `experimento-comp162-ajc/scripts/app_events.py`
(names the tag in a comment about what the capture filter admits); `experimento-gh104/docker-compose{,.smoke}.yml`;
`scripts/gh104_baseline.py`'s recorded outputs `data/gh104/baseline.json` and
`data/gh104/baseline.md`. None of them is executed against a post-gh104 corpus, and none is
rewritten by this change.
