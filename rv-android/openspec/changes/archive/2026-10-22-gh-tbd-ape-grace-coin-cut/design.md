## Context

This change implements Pedro's decisions of 21/10/2026 (`docs/20261021_plano_base_igual_ape.md` §3.2,
§3.3 and §3.5, outside git) that fall on the rv-android side. The `ape` repository half (the base cell
equal to APE, the WebView prune fix, the seeds and the new-state capture default of the jar) is a
separate change in that repository. The mini-experiment that follows runs the `rvandroid:0.9.6` image
with frozen copies of three files bind-mounted from this worktree: `aperv-tool`'s `tool.py`, its
`derive_mop_artifact.py` and the `rv-tools` `ape/tool.py`.

Current state, read at `88d6e153`:

- `APERV_TEARDOWN_GRACE_S = 45` is defined in `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:102`,
  and `modules/aperv-tool/src/aperv_tool/analysis/liveness.py:96` holds a second copy,
  `TEARDOWN_GRACE_S = 45`.
- `modules/rv-tools/src/rv_tools/builtin/ape/tool.py` builds the `adb shell` command with
  `timeout = budget` and runs it through `AbstractTool._execute_and_check_command`, which raises on a
  non-zero exit (`rv_android_core/tools/abstract_tool.py:239`).
- `modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py` fills `click` for the
  `CALLBACK_PARAMS` methods in `_handler_events`, its only caller being `_index_reachability`
  (line 571).

## Architecture

```
rv-android-core/constants.py  TOOL_TEARDOWN_GRACE_S = 45
        │                │                         │
        ▼                ▼                         ▼
rv-tools ape/tool.py   aperv-tool aperv/tool.py   aperv-tool analysis/liveness.py
 (command timeout,      (command timeout,          (C2 floor of the
  completion floor)      completion floor)          campaign analysis)

aperv-tool derive_mop_artifact.py ── _handler_events: View onClick/onLongClick + Compose invoke only
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `rv_android_core.constants.TOOL_TEARDOWN_GRACE_S` | The one grace value | — | `int` (45) |
| `APETool.execute_tool_specific_logic` | Pushes the properties, runs APE, judges completion by elapsed time | `Task`, `App` | `None` or raises |
| `APETool._push_ape_properties` | Writes and pushes the three capture lines | device serial, trace path | `/data/local/tmp/ape.properties` |
| `ApeRVTool._build_main_command` / completion floor | Reads the shared grace | budget | `Command`, floor |
| `liveness.floor_for` | C2 floor from the shared grace | budget | `int` |
| `derive_mop_artifact._handler_events` | Classifies a signature as handler events | Soot signature | event tuple |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-TOOL-27 | `APETool._build_ape_shell_command` reads `TOOL_TEARDOWN_GRACE_S`; `ApeRVTool` and `liveness` import it | `rv-tools/tests/builtin/test_ape_tool.py` (timeout 345), `aperv-tool/tests/test_aperv_tool.py`, `test_liveness.py` |
| INV-TOOL-28 | `APETool.execute_tool_specific_logic` uses `Command.invoke` plus the elapsed-time floor | `test_ape_tool.py`: exit 1 at full budget passes; early return raises; floor + 1 passes |
| INV-TOOL-29 | `APETool._push_ape_properties` | `test_ape_tool.py`: push order and exact content; failed push raises |
| INV-DRV-11 | `_handler_events`, `HANDLER_METHOD_PATTERN` | `aperv-tool/tests/test_derive_mop_artifact.py` (callback classes not listed, merge class keeps the View record, cryptoapp has 2 handler keys) |
| INV-APV-69 | `TraceReader` maps `dec.fz` → `StepRow.fuzz_events` (`analysis/trace_ndjson.py`) | `aperv-tool/tests/test_trace_ndjson.py` (in order, `[]`, absent, non-array) |

## Goals / Non-Goals

**Goals:**
- Same host grace and completion rule for `ape` and `aperv`, from one constant.
- New-state capture instead of per-step capture in the `ape` arm.
- No handler record for the library-dispatched app callbacks.

**Non-Goals:**
- Any change to the wire format, `FORMAT_VERSION`, the cache key, k or the distance cut.
- Any change to the dexlib2 stamp or to the corpus.
- `experimento-comp162/scripts/admissibility.py`. It is the frozen rule of a finished campaign and
  keeps its own 45; `test_liveness.py` loads it from disk, by design, to compare it with the package.
- The jar (the `ape` repository change).

## Decisions

**D1. The constant lives in `rv-android-core/constants.py` as `TOOL_TEARDOWN_GRACE_S`.** `aperv-tool`
declares no workspace dependency except `rv-android-core`, so a constant in `rv-tools` would not be
reachable from it. The name drops the `APERV_` prefix because two tools now read it. It is not an
`ENV_*` name, so `scripts/check_env_vars_drift.py` does not apply. `APERV_TEARDOWN_GRACE_S` and
`liveness.TEARDOWN_GRACE_S` are deleted and their readers import the core name (P3). The explanatory
comment, which says the value is a hypothesis about censored teardown, moves with it.

**D2. The `ape` tool skips `_execute_and_check_command` and calls `Command.invoke` directly.** That
helper exists to raise on a non-zero exit, which is exactly the check the rule removes. The tool
records `time.monotonic()` before the command and compares the elapsed time with
`timeout − TOOL_TEARDOWN_GRACE_S` after it returns, as `ApeRVTool` does. `RVCommandTimeoutError` still
reaches `AbstractTool.execute()`, which converts it (INV-TOOL-06). The alternative, a flag on the
shared helper, adds a parameter that only one caller would use.

**D3. The properties file is written by the tool, not shipped beside the jar.** Three fixed lines
written through a temporary file and `adb push` match how `aperv` pushes its own `ape.properties`.
A file shipped beside the jar would need its own resolution path. There is no cleanup: the emulator
of each task runs with `-read-only -no-snapshot-save`.

**D4. The callback cut removes `CALLBACK_PARAMS` and the callback names from
`HANDLER_METHOD_PATTERN`.** `onClick` stays in the pattern for the View form. The dialog
`onClick(android.content.DialogInterface,int)` then falls through to "not a handler" because its
parameters are not `android.view.View`. Nothing else in the derivation serves the callbacks. Docstrings
and the comment above `CALLBACK_PARAMS` are rewritten to the current behaviour.

**D6. `dec.fz` is read like `dec.ret`.** The `ape` change `gh-tbd-base-equals-ape` adds the optional member under trace version 2. The reader freezes it into a tuple and keeps `None` for absence, because absence (no fuzzing) and `[]` (fuzzing that queued nothing) are different facts (INV-APV-49). No version bump: an older trace simply has no `fz`.

**D5. No `FORMAT_VERSION` or cache-key change.** The jar parses format 2 only, and Pedro decided not to
add the generator to the cache key. A reused results directory therefore keeps stale artifacts, which
the aperv spec records. The mini-experiment uses a new results directory.

## API Design

### `APETool._push_ape_properties(self, trace_file_path: str) -> None`
Writes `APE_PROPERTIES_CONTENT` (a module constant holding the three lines, each ending in `\n`) to a
temporary file and pushes it to `/data/local/tmp/ape.properties` on `self.config["device_serial"]`
(timeout 60 s). The temporary file is removed in all cases. Raises `RVToolExecutionError` on a failed
push.

### `APETool.execute_tool_specific_logic(self, task, app) -> None`
Postcondition: it returns normally only when APE ran for at least `timeout − TOOL_TEARDOWN_GRACE_S`
seconds. Raises `RVToolExecutionError` on an early return or a failed push, and lets
`RVCommandTimeoutError`/`RVToolTimeoutError` propagate.

## Data Flow

1. Resolve the jar and push it.
2. Push `ape.properties`.
3. Start the clock.
4. Run `adb shell … --running-minutes N --ape <strategy>` with timeout `budget + 45`, stdout and
   stderr going to the trace.
5. When the command returns, compare the elapsed time with the floor.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `RVToolExecutionError` (push) | `adb push` of the properties fails | raise before APE starts | rv-platform ERROR, resumed |
| `RVToolExecutionError` (early return) | elapsed < budget − 45 | raise with elapsed and budget | rv-platform ERROR, resumed |
| `RVCommandTimeoutError` | host timeout at budget + 45 | propagate | `AbstractTool.execute()` → `RVToolTimeoutError`, normal end |

## Risks / Trade-offs

- [The `ape` arm stops being comparable with the 200 MOP misuses of e03igg/e03igg4] → Accepted by
  Pedro. The next comparison reruns the `ape` arm.
- [45 s is a hypothesis about teardown, not a measurement] → The value is unchanged and shared. Its
  comment says so.
- [A reused results directory keeps artifacts that still list the callback classes] → Recorded in the
  aperv spec. The mini-experiment uses a new directory.
- [A class that declares a callback and a View handler stays listed (9/3109 classes, 8 APKs, e7
  corpus)] → Recorded in the aperv spec as a known limit. Fixing it would need a format change.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | `ape` timeout, completion floor, exit-code independence, properties push | mock `Command.invoke` and `time.monotonic` | ~6 |
| Unit | `aperv` and `liveness` read the core constant | existing tests with the import switched | ~3 edits |
| Unit | `_handler_events` and the handler table without callbacks | existing derive tests rewritten | ~4 |
| Smoke | derive of the cryptoapp fixture, and one `ape` command built with a fake device | pytest | 1–2 |

## Open Questions

None. Every point was decided by Pedro on 21/10.
