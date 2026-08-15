# aperv Specification (delta)

## Purpose

This delta touches the two shipped analysis-time readers of `aperv_tool` — `analysis/trace_ndjson.py` and `analysis/clock_logcat_join.py` — so that the `campaign-analysis` capability can build on them without forking them. Two findings from the 2026-08-15 survey drive it. **F1:** the jar's `RUN_START` record carries thirteen members (`type, v, run_id, t0, seed, agent, preset, features, params, inert, corpus_basis, digest, props_digest, build{sha,time}` — `ape/src/main/java/.../runtime/RunSpecEcho.java:72-96`), and the reader's `RunStart` dataclass carries three (`run_id`, `t0_ms`, `params`, `trace_ndjson.py:106-122`). The ten dropped members are siblings of `params`, not entries inside it, so they are unrecoverable through the sanctioned path — and the spec designates that path as *the sole mechanism by which analysis code consumes a trace*. Through it a trace cannot say which jar or which arm produced it, which is the exact failure `RUN_START.build.sha` was created to end (`RunSpecEcho.java:31-34`), and `rvsec-calibracao/scripts/check_run_start.py:56-113` already re-parses `RUN_START` outside the package to get around it. **F2:** `FORMAT_VERSION = 1` is emitted as `v` (`RunSpecEcho.java:54,73`), justified in `ape`'s `run-spec` spec as "what makes a cross-campaign comparison fail loudly instead of quietly comparing incomparable fields", and no consumer references it. The gate exists on the wire and is inert at the consumer.

The third item is not a defect but a reuse point: the heartbeat placement rule in `clock_logcat_join` (violation → last `ApeRvHb` at or before it) is the right mechanism for every logcat stream, not only `RVSEC`; the module's regex deliberately refuses `RVSEC-COV`, and nothing places the diagnostic tags. `campaign-analysis`'s `step_bundle` needs the placement as a function of the tag; the violation-centric `RunJoin` and every scenario of the join requirement stay as they are.

## Invariants

- **INV-APV-61**: `RunStart` SHALL carry every top-level member of the `RUN_START` record the jar emits, with `build` as a nested `(sha, time)` value; a member absent on the wire SHALL be reported absent, never defaulted. No consumer in `aperv_tool` SHALL parse `RUN_START` other than through `TraceReader`.
- **INV-APV-62**: `TraceReader` SHALL check `RUN_START.v` against the format version it was written for; a mismatch SHALL be surfaced in `TraceDiagnostics` and SHALL raise `SchemaVersionMismatch` when the reader is opened in strict mode. A trace with no `RUN_START` reports the version as unknown (INV-APV-51 applies).
- **INV-APV-63**: The heartbeat placement rule SHALL exist once, in `clock_logcat_join.place_on_timeline(stamp, heartbeats)`, and SHALL be tag-agnostic; the tag admitted is a parameter of the line reader, not of the placement.

## MODIFIED Requirements

### Requirement: Native NDJSON Trace Reader (FR11, FR13, NFR03, NFR06)

The module SHALL provide `modules/aperv-tool/src/aperv_tool/analysis/trace_ndjson.py`, a read-only streaming reader of the NDJSON trace, and it SHALL be the sole mechanism by which analysis code in this module consumes a stage-4 trace. It follows the shape of its sibling `analysis/coverage_dump.py`: a pure offline component with a typed row model, never in the run path.

The reader SHALL stream the file — the trace is the largest artifact a run produces, and the reader must not require it in memory — and SHALL yield one typed row per `StepRecord`, having already:

- resolved the `act` and `st` integer references, and `out.target`, against the `ACT` / `STATE` dictionary records defined earlier in the same trace;
- materialized the fields the sink omits at their documented defaults, and left the tri-state fields absent (INV-APV-49);
- re-derived `activity_has_mop` on the step side from the record's `ACT` entry, and on the outcome side via `out.target` → `STATE.act` → `ACT.mop`, since the jar records that static per-activity fact once on the dictionary entry rather than on every step;
- expanded the run-relative `t` to epoch milliseconds via `RUN_START.t0` where an absolute clock is wanted, and reported the expansion as unavailable when `RUN_START` is absent (INV-APV-51);
- attached the step's `llm[]` sub-events, in occurrence order, and its `out` section to the same row — so that the three-way join by `step=` that the legacy format required ceases to exist for every consumer;
- carried each sub-event **whole**, including the `sys` / `user` / `resp` / `tool_calls` prompt and response dumps (INV-APV-58).

**`RunStart` carries the whole `RUN_START` record (INV-APV-61).** The jar echoes its resolved run specification into the first record so that a post-hoc audit can say which jar, which arm and which parameters produced a trace — `build.sha` exists because a stale jar once shipped, its MOP boost fired zero times across 147,153 evaluations, and nothing in 2,028 tasks' output said which jar had run. A reader that drops ten of those thirteen members reproduces that blindness one layer up. `RunStart` SHALL therefore expose `v`, `run_id`, `t0_ms`, `seed`, `agent`, `preset`, `features`, `params`, `inert`, `corpus_basis`, `digest`, `props_digest` and `build` (as a nested value with `sha` and `time`), each reported absent — `None` — when the wire record lacks it, never defaulted; `params` remains what the jar recorded verbatim (only non-default values plus active activation keys — absence means "at the jar default for this `build.sha`"). No consumer in `aperv_tool` SHALL parse `RUN_START` other than through this class; the workaround parser in `rvsec-calibracao/scripts/check_run_start.py` loses its reason to exist.

**The `v` schema gate is checked, not merely carried (INV-APV-62).** The reader SHALL compare `RUN_START.v` to the format version it implements (`FORMAT_VERSION = 1`); a mismatch SHALL be recorded in `TraceDiagnostics.schema_version_mismatch` and, when the reader is constructed with `strict=True`, SHALL raise `SchemaVersionMismatch` before any row is yielded — a cross-campaign comparison over incomparable fields fails loudly rather than quietly. The default is non-strict, so a survey over a mixed tree still yields rows and counts the mismatches. A trace whose capture began after `RUN_START` reports the version as unknown, and the reader does not infer it.

The reader SHALL additionally expose the run-level records as attributes beside the `RUN_START` header — `MOP_DATA`, `PIPELINE` and `LLM_ACK` — since a step-row iterator has no natural place for them and this module is the sole way to reach them. `RUN_END` SHALL NOT be exposed, and the asymmetry is deliberate rather than an omission: INV-APV-53 makes it write-only, and an accessor is the first step toward the `if not run_end: ...` that owner decision D5 refuses. The other three are load and assembly census, not a termination signal.

**Both clauses reverse an earlier reading of this requirement, and the reversal is recorded rather than quietly applied.** The first implementation surfaced neither, on the defensible ground that the dumps are the bulk of the record and nothing in this module read them. What that reasoning missed is that the jar writes them by default and the jar's own throughput gate (`event-sink` INV-SNK-13) prices their escaping, so the run pays their full cost either way — and that the analysis which did read them is real rather than hypothetical: `calibracao/decompose_nomatch.py` pairs each response with the call that produced it to decompose `no_match` causes, and that pairing was the gate of a change decision. It stays on the legacy format under INV-APV-55, so its successor over new traces has to get `resp` from here. The same argument applies to the census: `MOP_DATA.wtgEdges` and `PIPELINE.candidates` are the two quantities the jar-side change added — one because `transitions` had been misread as the frontier gate for months, the other because "the arm turned this off" and "this application's data could not support it" were otherwise the same evidence across 25 of 40 applications — and writing them into a trace no reader surfaces would reproduce that defect one layer up. If the dumps are ever judged too expensive, the lever is the jar's `llmPromptDump` flag, not a silent drop here.

The reader SHALL NOT convert between formats in either direction, SHALL NOT write to the trace, and SHALL NOT run on the collection path (INV-APV-48). A malformed record SHALL be skipped and counted rather than aborting the read (INV-APV-50): a trace truncated by a `SIGKILL` ends in a partial line by construction, and losing the whole run's analysis over its last line would be a worse failure than losing the line. `RUN_START` is not guaranteed to be line 1 — AOSP banner lines may precede it — so the reader SHALL take the first `{`-leading line as the candidate header.

**The `ape` change `rearch-04-step-ndjson-telemetry` is the authority for the wire format.** Its `event-sink` spec defines the `StepRecord` schema, the dictionary encoding, the omitted-default rules and the heartbeat payload; its `run-spec` spec defines the `RUN_START` echo; its design carries the legacy-field → new-schema mapping table. The format is defined jointly and cut once, and this reader conforms to it rather than restating it.

The golden fixture that exercises this requirement SHALL be `modules/aperv-tool/tests/fixtures/trace_ndjson_golden.ndjson`, a hand-written stage-4 trace containing, at minimum: a `RUN_START` with `t0` **and all thirteen members**; `ACT` entries with `mop:1` and `mop:0`; two `STATE` entries; a step whose `dec` carries no boost fields at all; a step carrying `patched:0`; a step carrying no `patched` member; a step with two `llm[]` entries in occurrence order; a step whose `out` resolves to a new state; a step closed with no `out` member; a step flushed with `out:{"resolved":false}`; a completed call carrying the `sys` / `user` / `resp` / `tool_calls` dumps beside one that carries none; a `MOP_DATA` record, a `PIPELINE` record whose `candidates` include disabled entries, and an `LLM_ACK`; a malformed line; and a truncated final line. A second fixture, `trace_ndjson_v2_header.ndjson`, SHALL carry `RUN_START` with `v: 2` and one step. Every scenario below names the fixture element that exercises it, so no rule is asserted against an input that cannot reach it.

#### Scenario: Reader yields a joined step row
- **WHEN** the reader runs over the golden fixture, whose step 42 carries a `dec` with no boost fields, two `llm[]` sub-events and an `out` closed at step 43
- **THEN** it SHALL yield exactly one row for step 42
- **AND** that row SHALL carry the activity and state resolved to their dictionary strings, not their integer IDs
- **AND** it SHALL carry `mop=0`, `mopf=0`, `wtg=0`, `cov=0`, `menu=0` and `form=0` as explicit zeros
- **AND** it SHALL carry both LLM sub-events in occurrence order and the outcome fields
- **AND** no second pass over the trace SHALL be required to join them

#### Scenario: Tri-state patched is not defaulted
- **WHEN** the reader runs over the fixture's step carrying `dec.patched:0` and the fixture's step carrying no `patched` member
- **THEN** the first row SHALL report `patched` as `0` and the second SHALL report it as absent
- **AND** the two SHALL be distinguishable in the row model, because absence means "no resolved target" and `0` means "natively clickable node"

#### Scenario: activity_has_mop re-derived on both sides
- **WHEN** the reader runs over a step whose `act` refers to an `ACT` entry with `mop:1` and whose `out.target` refers to a `STATE` whose `act` refers to an `ACT` entry with `mop:0`
- **THEN** the row SHALL report the step-side flag as true and the outcome-side flag as false
- **AND** neither value SHALL be read from the step record itself, which does not carry them

#### Scenario: Malformed record is skipped and counted
- **WHEN** the reader runs over the golden fixture, whose content includes one unparseable line and one truncated final line
- **THEN** the reader SHALL yield rows for every well-formed record in the file
- **AND** SHALL report exactly 2 skipped records in its diagnostics
- **AND** SHALL NOT raise

#### Scenario: Reference to an undefined dictionary ID is malformed
- **WHEN** a record references `st:99`, for which no `STATE` record appears earlier in the trace
- **THEN** that record SHALL be counted as malformed and skipped
- **AND** the reader SHALL NOT emit a row carrying a placeholder or empty state string

#### Scenario: Trace without RUN_START reports epoch as unavailable
- **WHEN** the reader runs over a trace whose capture began after `RUN_START` was written, so no `t0` is present
- **THEN** every row SHALL still carry its run-relative `t`
- **AND** the epoch expansion SHALL be reported as unavailable
- **AND** no base SHALL be inferred from the file's mtime or from the logcat
- **AND** the schema version SHALL be reported unknown, not assumed

#### Scenario: Prompt and response dumps reach the caller
- **WHEN** the reader runs over the fixture's step-42 completed call, which carries `sys`, `user`, `resp` and `tool_calls`
- **THEN** the sub-event SHALL carry all four, with the widget list's embedded newlines intact as the jar escaped them
- **AND** the abandoned attempt beside it, written without dumps, SHALL report them as absent rather than as empty strings — an empty string would claim the model was sent an empty prompt

#### Scenario: The run-level census is reachable and RUN_END is not
- **WHEN** the reader runs over a trace carrying `MOP_DATA`, `PIPELINE`, `LLM_ACK` and `RUN_END`
- **THEN** the first three SHALL be readable as reader attributes, so `wtgEdges` and the candidate census need no second parser
- **AND** the reader SHALL expose no `RUN_END` accessor at all (INV-APV-53)
- **AND** a trace carrying none of them SHALL report each as absent rather than as an empty record

#### Scenario: RunStart carries all thirteen members
- **WHEN** the reader runs over the golden fixture's `RUN_START`, which carries `v, run_id, t0, seed, agent, preset, features, params, inert, corpus_basis, digest, props_digest, build{sha,time}`
- **THEN** `reader.run_start` SHALL expose each of them, `build` as a nested value with `sha` and `time`
- **AND** on cmp162's 972 `aperv` traces every member SHALL be present, and the test over the fixture manifest SHALL assert it
- **AND** a `RUN_START` written without `inert` SHALL report `inert=None`, not `False`

#### Scenario: Schema version mismatch is loud in strict mode and counted otherwise
- **WHEN** the reader opens `trace_ndjson_v2_header.ndjson` with `strict=True`
- **THEN** it SHALL raise `SchemaVersionMismatch` naming `2` and `1` before yielding any row
- **AND** with `strict=False` it SHALL yield the row and report `schema_version_mismatch=1` in diagnostics

#### Scenario: Reader stays off the collection path
- **WHEN** the module's tests assert the import graph of `tools/aperv/tool.py`
- **THEN** `trace_ndjson` SHALL NOT be reachable from it
- **AND** no collection-path function SHALL reference `RUN_END` (INV-APV-53)

## ADDED Requirements

### Requirement: Heartbeat Placement Is One Tag-Agnostic Function (FR11, FR13, NFR03)

`clock_logcat_join.py` SHALL expose its placement rule as `place_on_timeline(stamp, heartbeats) -> (Phase, step | None, anchor)` — the violation belongs to the step of the last heartbeat at or before it; before the first heartbeat is `PRE_EXPLORATION`, after the last is `POST_EXPLORATION`, no heartbeat at all is `UNALIGNED` — and a line reader `read_tagged_lines(logcat_path, tag) -> list[(stamp, payload)]` whose admitted tag is a parameter (INV-APV-63). The join's own behaviour, output type `RunJoin` and every scenario of *Offline Clock-to-Violation Join* SHALL be unchanged: it calls the two with `tag="RVSEC"`. `campaign-analysis`'s `step_bundle` calls them with `RVSEC-COV` and with the diagnostic base tags. The heartbeat regex, the timestamp regex and the run-filename regex SHALL NOT be duplicated into any other module; the last one moves to `run_identity.py` and is imported here (`campaign-analysis` INV-CAN-01).

#### Scenario: The join is unchanged after the extraction
- **WHEN** the existing `test_clock_logcat_join.py` suite runs after the placement and line reader are extracted
- **THEN** every test SHALL pass without modification
- **AND** `join_run` SHALL produce byte-identical `RunJoin` values over the fixtures

#### Scenario: RVSEC-COV lines are placed by the same rule
- **WHEN** `read_tagged_lines(path, "RVSEC-COV")` and `place_on_timeline` run over a logcat with heartbeats
- **THEN** a coverage line between heartbeat 7 and heartbeat 8 SHALL be placed at step 7
- **AND** `read_tagged_lines(path, "RVSEC")` SHALL NOT admit that line, and vice versa

#### Scenario: Placement exists once
- **WHEN** the tests grep `aperv_tool/analysis/` for the phrase `last heartbeat at or before`
- **THEN** the implementing loop SHALL exist only in `clock_logcat_join.py`
- **AND** `step_bundle.py` SHALL import it
