# Design: Emulator Boot Gating

**GitHub Issue**: #92

## Context

RV-Android runs every task by cold-booting an Android emulator inside a Docker container, installing the instrumented APK, running one testing tool against it for a fixed budget, and tearing the emulator down. The proposal establishes that the boot gate protecting that sequence does not work: phase 2 of `Android._wait_for_boot` returns success in milliseconds because a quoted shell string is delivered literally to the device (exit 127) and the resulting `CommandResult` is never inspected. 1,174 stored task records carry the consequence, across seven tools and seven months, most recently inside the live gh90 decisive run.

Three constraints shape every decision below, and none of them is negotiable.

**The emulator will never use GPU.** Headless with software rendering is the intended regime, not a gap. The AVD baked into `phtcosta/rvsec_android:0.9.3` carries `hw.gpu.enabled = no`, and the UI-automation timing constants in `modules/rv-uiautomator/src/rv_uiautomator/constants.py:4-6` are already calibrated for it. `EMU_GPU_MODE` and the `GPU_ACCELERATED` branch in `docker/android/scripts/start-emulator.sh` are dead code — that script is not `COPY`ed into the image (`docker/android/Dockerfile:88-94`) — and are deletion candidates under P3, not configuration to reactivate.

**No state may persist between tasks.** `-read-only`, `-no-cache` and `-no-snapshot-save` (`android.py:105-110`) are a requirement. Residue from one task — an installed APK, app data, ART cache, granted permissions — would contaminate the next task's coverage measurement and destroy experimental validity. `-read-only` additionally is what allows several containers to open the same `/data/RVSec.avd` concurrently.

**Cold boot on every task is the accepted, irreducible price of the second constraint.** Because nothing persists, `/data/RVSec.avd` stays permanently in a never-booted state, and every boot repeats zygote start, boot-image `dex2oat`, and the first package-manager scan in full. Warming the AVD at image build time is not merely undesirable but impossible: `docker build` does not expose `/dev/kvm`, so the boot would be pure software emulation. The only correct response to an irreducible cost is to size the budget for it, which is what C4 does.

These three are recorded in the ADR accompanying this change, because none of them was written down anywhere before and a previous attempt at this problem proposed GPU pinning, snapshot warming, and emulator reuse — all three long since decided against.

Relevant requirements: **FR07** (Android Emulator Management), **FR09** (Component-Based Task Execution), **NFR04** (resilience), **NFR06** (observability), **NFR07**.

## Architecture

```
                    ENV: RV_EMULATOR_BOOT_TIMEOUT / RV_ADB_CMD_TIMEOUT / RV_APK_INSTALL_TIMEOUT
                                    │  (read at point of use — L1 exception, gh55)
                                    ▼
┌─ rv-android-core ────────────────────────────────────────────────────────────┐
│                                                                              │
│  Android.start_emulator()                                                    │
│    └─ Android._wait_for_boot()          C1  phase 2 → Python poll + is_failure│
│         phase 1: getprop init.svc.bootanim   C3  explicit failure handling    │
│         phase 2: getprop sys.boot_completed  C1  accept only on b"1"          │
│                                                                              │
│  Android.install_apk()                  C4  timeout   C6  reason preserved    │
│                                                                              │
│  EmulatorManager.start_emulator()  @contextmanager                           │
│    try:                          ← outer: teardown covers BOTH blocks         │
│      ├─ try: register AVD → launch → wait   C5  register BEFORE launch        │
│      │  except: → EmulatorError             C2  covers startup ONLY           │
│      └─ yield                               C2  outside the relabelling except│
│    finally: kill_emulator()                 C5  reclaims the port on failure  │
│  EmulatorManager.install_app()          C6  carries the adb reason up         │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │  Android instance
                                    ▼
┌─ rv-platform ────────────────────────────────────────────────────────────────┐
│  EmulatorComponent          §6.3  port and serial from ONE resolution         │
│  TaskExecutor._run_emulator_session()                                        │
│    with start_emulator("RVSec") as android:                                  │
│        try:   install → logcat.start → coverage.start → tool.execute          │
│        finally:  logcat_component.cleanup()   §6.4  single owner, in order    │
│                  coverage_component.cleanup()                                 │
│    (inline block at :440-448 deleted)                                         │
│  _cleanup_components() still runs both — INV-PLT-06 holds, calls are inert    │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │  logcat file
                                    ▼
┌─ rv-coverage ────────────────────────────────────────────────────────────────┐
│  CoverageTracker.stop()     C8  final drain to EOF before closing the handle │
└──────────────────────────────────────────────────────────────────────────────┘

Out-of-band surfaces: constants.py (ENV_* registry) → validate_env_vars.sh (exit 64)
                                                    → check_env_vars_drift.py (lint)
                                                    → .env.example, README.md, composes
                      experimento-{20260706,20260604}/scripts/rv_status.py  C7  buckets (2 copies)
                      docs/architecture/rv-platform.md:262,:888            §6.4 order correction
                      docs/architecture/subsystem-rv-experiment.md:279,:816  §6.4 order correction
```

### Key Components

| Component | Responsibility | Input | Output |
|---|---|---|---|
| `Android._wait_for_boot` | Two-phase boot gate against one shared budget | `device_name: str`, `boot_timeout: Optional[int]` | `None`; raises `TimeoutError` |
| `Android.install_apk` | ADB install under a timeout, preserving the failure reason | `App`, `device_name: str` | `None`; raises `RuntimeError` / `RVCommandTimeoutError` |
| `EmulatorManager.start_emulator` | Brackets one emulator lifetime; startup errors labelled, session errors not | `avd_name`, `no_window`, `device_port` | yields `Android`; raises `EmulatorError` on startup only |
| `EmulatorManager.install_app` | Installs and carries the ADB reason upward | `App`, `device_serial: str` | raises with reason on failure |
| `EmulatorComponent` | Resolves one device identity for boot and install | `task.config.tool_config.parameters` | context manager, `bool` |
| `TaskExecutor._run_emulator_session` | Owns the single finalization point | components, context | `None` |
| `CoverageTracker.stop` | Terminates the tail thread after draining to EOF | `_stop_event` | `None` |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|---|---|---|
| INV-CORE-43 (never accept an unchecked `CommandResult`) | `util/android/android.py` — both boot loops, `install_apk`'s `adb root` | `test_boot_gate_rejects_failed_result`, plus a repo-wide grep task |
| INV-CORE-44 (accept only `b"1"`) | `android.py::_wait_for_boot` phase 2 | `test_phase2_requires_boot_completed_one` |
| INV-CORE-45 (no shell dependency in argv) | `android.py::_wait_for_boot` phase 2 argv | `test_boot_argv_has_no_quotes_or_shell_tokens` |
| INV-CORE-46 (one shared budget, distinguishable messages) | `android.py::_wait_for_boot` | `test_shared_budget_across_phases` |
| INV-CORE-47 (env resolution; invalid fails loudly) | `android.py::_resolve_timeout` helper | `test_env_default`, `test_env_valid`, `test_env_invalid_raises`, `test_arg_overrides_env` |
| INV-CORE-48 (every device `Command` has a timeout) | `android.py` — all `Command(...)` constructions | `test_install_command_has_timeout` |
| INV-CORE-49 (`yield` outside the relabelling `except`) | `util/android/emulator_manager.py::start_emulator` | `test_session_exception_keeps_type` |
| INV-CORE-50 (register AVD before launch) | `emulator_manager.py::start_emulator` | `test_failed_boot_triggers_kill` |
| INV-CORE-51 (ADB reason propagates) | `emulator_manager.py::install_app` | `test_install_failure_carries_reason` |
| INV-CORE-52 (post-kill delay only after a successful kill) | `android.py::kill_emulator` | `test_no_settle_delay_when_kill_fails` |
| C3 — phase 1 reports a broken ADB in seconds (scenario "Broken ADB is reported in seconds") | `android.py::_wait_for_boot` phase 1 | `test_phase1_failed_probe_logs_diagnostics` |
| INV-PLT-27 (install only after observed boot) | `execution/executor.py::_run_emulator_session` | `test_no_install_when_boot_times_out` |
| INV-PLT-28 (one device resolution) | `components/emulator.py` | `test_partial_device_params_resolve_consistently` |
| INV-PLT-29 (single firing point, inline block deleted) | `executor.py::_run_emulator_session` `finally` | `test_finalization_runs_before_teardown`, grep assertion |
| INV-PLT-30 (calls `cleanup()`, idempotent, non-raising) | `executor.py` `finally` | `test_second_cleanup_is_inert`, `test_cleanup_error_does_not_mask` |
| INV-PLT-31 (logcat → coverage order) | `executor.py` `finally`; the five doc/comment corrections | `test_finalization_order` |
| INV-ANA-53 (final drain) | `analysis/coverage/tracker.py::_track_coverage` `finally` | `test_drain_recovers_trailing_lines` |
| INV-ANA-54 (drain does not double-count) | same | `test_drain_does_not_double_count` |
| INV-ANA-55 (`stop()` stays idempotent) | `tracker.py::stop` | `test_stop_when_already_stopped` |
| C7 (mutually exclusive buckets) | `experimento-20260706/scripts/rv_status.py` **and** `experimento-20260604/scripts/rv_status.py` | `test_error_bucket_classification` |

## Goals / Non-Goals

**Goals**

- Make boot completion a condition that must be positively observed before any APK is installed.
- Size the boot budget for the environment that actually exists, and make it adjustable without a code change.
- Make failures name their own cause, so the next investigation starts from the right place.
- Leave exactly one implementation and one firing point for coverage/logcat finalization.
- Close the live-versus-resume divergence in coverage metrics (INV-PLT-18).
- Make boot failures visible in the monitoring bucket that claims to count them.

**Non-Goals**

- Reducing boot time by any means. Warm boot, snapshots, quickboot, emulator reuse, and removing `-read-only`/`-no-cache` are all rejected; see the ADR.
- Enabling GPU acceleration in any form.
- Tuning `hw.ramSize`, `hw.cpu.ncore`, or `disk.dataPartition.size`. The 800 MB `/data` partition is the most suspicious of the three and may be a direct cause of install failures, but deciding that requires C6 to land first and then measurement. Separate change.
- Fixing the pre-existing `rv-android-core ↔ rv-coverage` import cycle (`domain/task.py:682`).
- Deciding the fate of the dead `get_env_or_default` helper (`util/utils.py:424-473`, zero call sites, silently swallows `ValueError`). Not used here; its removal is a separate P3 cleanup.
- Adding in-process retry around boot. `TaskExecutor.execute()` has none today, and adding one would mask the very signal this change is trying to expose.

## Decisions

### D1 — Phase 2 polls from Python rather than fixing the quoting

The immediate defect is quoting, and a minimal fix would be to pass the shell loop as separate argv elements or to enable `shell=True`. Both are rejected. `shell=True` is explicitly avoided in `Command.invoke()` for injection safety and reliable process-tree cleanup, and reversing that for one call site would be a poor trade. Keeping a device-side loop, correctly quoted, would also keep the timeout semantics confused: the loop would block inside a single `Command` whose only bound is `cmd_timeout`, so the shared boot budget could only be enforced between invocations.

Polling `getprop sys.boot_completed` from Python removes the quoting problem by construction — there is nothing left to quote — and gives phase 2 the same shape as phase 1, which already works. The budget is then checked on every iteration.

### D2 — Environment variables, not a CLI flag or a config field

The alternative is threading the value through `ExperimentConfig` → `PlatformConfig` → `TaskConfiguration`, the route `no_window` takes. That means editing two modules to carry a value consumed in a third, at a point that reads no configuration at all today — plumbing across three module boundaries, against P1.

It is also prohibited in the direction of the CLI. `modules/rv-experiment/src/rv_experiment/__main__.py:296-303` carries an explicit in-code instruction: the per-flag `envvar=` pattern is a gh55 stopgap and *"do NOT expand this pattern to new flags."*

The established alternative already exists and is named: the "L1 cross-layer infra exception" from gh55, implemented in `util/validation/config.py:75-88` for `RV_PYDANTIC`. A boot budget fits that category exactly — its correct value depends on the host and the concurrency level, not on the semantics of the experiment. `RV_SA_TIMEOUT` (`rv_experiment/config.py:856-873`) is the precedent for an integer-valued timeout env var, justified in its own comment by the same reasoning applied to static analysis.

**Consequence for the drift lint.** `scripts/check_env_vars_drift.py` declares rv-experiment the only Python module allowed to read user-facing `RV_*` variables, with an `L1_INFRA_NAMES` frozenset of six names. `android.py` is already in `L1_ALLOWLIST_FILES`, and the read-form regexes match string literals only — so `os.getenv(ENV_EMULATOR_BOOT_TIMEOUT, ...)`, using the constant, passes silently. **Decision: extend `L1_INFRA_NAMES` with the three new names rather than rely on that gap.** Relying on a regex blind spot to pass a lint that documents the opposite rule is exactly the kind of silent inconsistency this change exists to remove.

### D3 — Keep `boot_timeout` as a parameter, defaulting to `None`

`_wait_for_boot(device_name, boot_timeout: Optional[int] = None)`, resolving from the environment when `None`. The alternative — dropping the parameter and reading the environment unconditionally — would force every test to patch `os.environ`, and `test_emulator_boot_retry.py` already injects through this parameter in five places. Keeping it preserves the injection point, keeps the default in exactly one place, and gives a clean three-level precedence: argument, then environment, then default.

### D4 — Register the AVD before launching, accepting a teardown cost

C5 requires `_active_emulators.add(avd_name)` to precede the launch, so a failed boot is reclaimed. The consequence is that the teardown `finally` now fires on paths where no emulator may exist, and `Android.kill_emulator` issues `adb emu kill` followed by an unconditional `time.sleep(10)` (`android.py:137-139`). That is a 10-second tax on every failed launch.

Alternatives considered: splitting `Android.start_emulator` into launch and wait so the manager can register between them (more precise, but changes a public method's shape and its only-caller contract for marginal gain); or making the sleep conditional on the kill having succeeded. **Decision: register before launch, and make the post-kill sleep conditional on a successful kill** — the sleep exists to let the port be released, which is meaningless when nothing was killed. That conditional is recorded as **INV-CORE-52** rather than left as an implementation detail, because it is an observable timing change on every task teardown and would otherwise be a task no spec asks for. The `adb emu kill` command also gains a timeout under INV-CORE-48, so it cannot hang.

### D5 — The finalization owner calls `cleanup()`, it does not reimplement it

Three shapes were considered.

*(a) Move the inline block's body into the `with`'s `finally`.* Rejected. The inline block has no `try/except`; in a `finally` on the failure path, an error inside it would replace the exception being propagated — reintroducing the diagnostic corruption C2 exists to remove. Making it safe means wrapping it in try/except-and-log, at which point it is a verbatim copy of `cleanup()`.

*(b) Delete the inline block and let `cleanup()` own it alone.* Rejected, and this is the one that looked most P1-aligned until the task states were checked. `ResultProcessorComponent` processes only `TaskState.COMPLETED` (INV-PLT-10), and `get_completed_tasks()` is also what `_skip_completed_tasks()` consumes — so an `ERROR` task never enters a CSV and is never skipped on resume; it re-executes from scratch. The failure path's post-teardown finalization is therefore harmless, while the **success** path's `.logcat` is the resume reconstruction source (INV-PLT-15/16/18). Option (b) would move the success path to post-teardown and damage precisely the artifact that matters.

*(c) Chosen.* The `finally` calls `logcat_component.cleanup(context)` then `coverage_component.cleanup(context)`. One implementation — the components' own — and one firing point, inside the `with`, so the success path can never drift to post-teardown. Both `cleanup()` methods survive, so INV-PLT-06 holds, `_cleanup_components()` keeps working unchanged, and the duck-typed `initialize/execute/cleanup` contract stays uniform across the five components the executor registers. That contract is duck-typed by a decision recorded in `docs/architecture/rv-platform.md:519-530`, which explicitly names drift as the accepted risk; removing lifecycle methods from two of those five would be that drift.

Idempotence, verified rather than assumed: `CoverageTracker.stop()` returns immediately when `is_running` is `False` (`tracker.py:265`), and `LogcatManager.stop_capture()` acts only when `logcat_process` is set, nulling it afterwards (`logcat_manager.py:246-250`). Both `cleanup()` methods already catch and log their own exceptions.

### D6 — Invert the finalization order, and correct the documents that assert otherwise

Five places in the tree assert the opposite order. `executor.py:435` says *"Stop order matters: coverage first, then logcat"*; `docs/architecture/rv-platform.md:888` says *"stop must precede logcat stop in the executor"*; `:262` restates it narratively. `docs/architecture/subsystem-rv-experiment.md:279` and `:816` go further and supply a reason — teardown *"unwinds coverage first, logcat last, so metrics finalize against a complete log"* — which is exactly inverted: coverage is the reader, logcat the writer, so stopping the reader first is what guarantees an *incomplete* log. No measurement in the repository decides the question.

The topology does decide it. `adb logcat` is the producer, writing to a file. `CoverageTracker` is the consumer, and it opens that same file **by path, with its own handle** (`tracker.py:293`) — not a pipe, not the device. Killing the producer therefore cannot EOF the consumer, break it, or raise inside it; the two are decoupled by the filesystem. That removes the only reason a consumer-first order could be safer, and leaves the standard pipeline-shutdown discipline: stop the producer, drain the consumer, stop the consumer.

Stopping the consumer first is actively wrong here, because the tracker's tail loop exits on `_stop_event` without a final read (`tracker.py:304`, `:330-342`). Lines the producer writes after that are in the file and absent from the repository, which is what `process_results()` reads (`coverage.py:280-283`).

### D7 — C8 and D6 ship together, or neither is meaningful

The reorder without the drain changes nothing: the tracker still exits without reading. The drain without the reorder closes only part of the window: it reads what is present at that instant while the producer keeps appending. Together they are deterministic — the file is frozen, then read to EOF. They are therefore one decision, and C8 brings `rv-coverage` into the change as a fifth module.

**The magnitude is unmeasured** and must stay labelled that way. The window is the tail loop's 0.5–1.0 s sleep plus the duration of `process_results()`. This is a structural violation of INV-PLT-18, not an observed corruption.

### D8 — C7 requires classification, not reordering

Verified against artifacts: `EmulatorError.__str__` embeds the cause's type, so a genuine phase-1 timeout is stored as `EmulatorError: Failed to start emulator RVSec caused by TimeoutError: emulator-5554 did not boot within 180s`. That matches `("timeout", r"time?out|timed out")`, evaluated first. The composite install message matches `("install/adb", ...)`, evaluated third. Both precede `("emulator/boot", ...)`. **No boot failure of either kind reaches `emulator/boot` today** — the bucket is empty by construction.

Simply moving `emulator/boot` to the front inverts the problem: a genuine tool timeout containing the word "emulator" would then land in the boot bucket. **Decision: classify on the most specific signal first** — match the two known boot signatures (`did not boot within`, `sys.boot_completed not set within`) and the composite install signature explicitly, before falling back to the current generic keyword buckets. New boot-failure messages introduced by C1–C4 must be added to that specific set rather than relying on keyword overlap.

### D9 — The 300 s default is provisional and ships with measurement

180 s was already exceeded 322 times by phase 1, with p50 182 s, p90 210 s, and three cases above 300 s (max 871 s). So 300 s is an improvement of unknown sufficiency, not a solved number. It ships together with the `elapsed` instrumentation already present at `android.py:223-224`.

**The distribution is collected by production observation, not by a validation run.** A dedicated contention run was considered and rejected on cost. The composite failure occurs in 0.86 % of recent tasks (128 of 14,939 since 2026-07), so an 8-container run of a handful of tasks would report zero failures about 93 % of the time with the bug completely untouched; by the rule of three, roughly 350 tasks are needed before an absence of failures is evidence at all. That is hours of wall clock to answer a question the change can answer for free afterwards.

What makes deferring safe is C4 itself. The budget is an environment variable read at the point of use, so a value that proves too low is corrected in a compose — no code change, no image rebuild, no redeploy. And C7 makes the signal visible: boot failures now land in the `emulator/boot` bucket, which is empty by construction today, so the first real run after this change surfaces them immediately instead of hiding them inside `timeout` and `install/adb`.

**Status at implementation time: DEFERRED TO PRODUCTION OBSERVATION.** No dedicated validation run was commissioned, and none should be added retroactively — the reasoning above is a cost decision, not an omission. The 300 s default ships provisional and stays provisional until the observation below supplies a distribution.

The procedure, for whoever runs the first real experiment after this change lands:

1. Read the `emulator/boot` bucket from `experimento-*/scripts/rv_status.py`. It is populated for the first time by C7 — before this change it was empty by construction, so any non-zero count is new information rather than a change in rate.
2. Read the boot `elapsed` values from the container logs. `Android._wait_for_boot` logs one line per task carrying the device serial and the measured time; that set of values, across a full run, is the distribution this change could not produce for itself.
3. If boot `TimeoutError`s appear, the gate is working and reporting honestly for the first time. **Raise `RV_EMULATOR_BOOT_TIMEOUT` in the compose — do not weaken the gate.** The variable is read at the point of use, so this needs no code change, no image rebuild and no redeploy.
4. If they do not appear, record the observed distribution and promote 300 s from provisional to measured, or lower it with evidence.

## API Design

### `Android._wait_for_boot(device_name: str = "emulator-5554", boot_timeout: Optional[int] = None) -> None`

**Preconditions**: the emulator process for `device_name` has been launched; ADB is reachable on the host.

**Behavior**: resolves `boot_timeout` as argument → `RV_EMULATOR_BOOT_TIMEOUT` → `300`. Takes one `start` timestamp. Phase 1 polls `getprop init.svc.bootanim` until `stdout.strip() == b"stopped"` with `is_failure()` false; a failed probe is logged with its combined output. Phase 2 polls `getprop sys.boot_completed` and terminates only when `is_failure()` is false **and** `stdout.strip() == b"1"`. Each iteration first checks the shared budget. `RVCommandTimeoutError` from any single probe is caught and the probe retried.

**Postconditions**: on return, the device reported `sys.boot_completed == "1"`. Total elapsed time is logged.

**Errors**: `TimeoutError` naming the phase and budget; `ValueError` if the environment variable is set but not an integer.

### `Android._resolve_timeout(env_name: str, default: int, override: Optional[int] = None) -> int`

Shared resolution helper, following the explicit `int(env_value)` style of `rv_experiment/config.py:865`. Returns `override` when not `None`; otherwise `int(os.getenv(env_name))` when set, letting `ValueError` propagate; otherwise `default`. The dead generic helper at `util/utils.py:424-473` is deliberately not used — it swallows `ValueError` and returns the default, which is the wrong behavior for a timeout.

### `EmulatorManager.start_emulator(...) -> Iterator[Android]`

Restructured by **nesting**, not by splitting into siblings. An outer `try` whose `finally` performs the existing teardown encloses everything. Inside it, an inner `try` wraps only the startup sequence — register the AVD, launch, wait for boot, disable animations — with the `except` that raises `EmulatorError`. The `yield self.android` sits after that inner block, inside the outer `try`, so it is covered by the teardown but not by the relabelling `except`.

The sibling arrangement is the trap. Writing `try/except` for startup followed by a separate `try: yield / finally: teardown` satisfies C2 and reads as the same refactor, but a startup failure raises `EmulatorError` out of the first block and the second block is never entered — so the teardown never runs, and the AVD that C5 registered before launch is never killed. That arrangement would make C5 produce the orphan it exists to prevent, and would make the INV-CORE-50 scenario unsatisfiable. INV-CORE-49 states the nesting requirement explicitly for this reason.

Note the current return annotation is `-> Android` while the method is a `@contextmanager`; it becomes `Iterator[Android]`.

### `EmulatorManager.install_app(app, with_permissions=True, device_serial=...) -> bool`

Whatever this method returns, it no longer discards the reason. The ADB text preserved by `Android.install_apk`'s `RuntimeError` must reach `EmulatorComponent.install_app`, which raises `EmulatorError` carrying it, so it lands in `task.result.error_message`.

The signature above shows today's shape, not a decision. The carrier is Open Question 2 and both branches are live: keep `-> bool` and attach the reason to a raised exception, or return a small result object carrying `ok` and `reason`. The spec fixes only the outcome — the reason reaches the task record — because the two mechanisms are indistinguishable from the spec's vantage point and the existing caller changes either way.

### `CoverageTracker.stop() -> None`

Unchanged signature and unchanged `if not self.is_running: return` guard. The thread's `finally` gains a drain: read forward from the handle's current position to EOF under `_reader_lock`, process those lines through the existing path, then `flush_diagnostics()` and close. Read errors are caught and logged; `stop()` does not raise.

## Data Flow

```
launch emulator (daemon)
   │
   ├─ register AVD in _active_emulators              C5 (before launch)
   │
   ├─ phase 1  getprop init.svc.bootanim ──▶ CommandResult ──▶ is_failure()? ──▶ b"stopped"?
   │                                              │ no                    │ no
   │                                              ▼                       ▼
   │                                         log + retry              sleep, retry
   │
   ├─ phase 2  getprop sys.boot_completed ──▶ CommandResult ──▶ is_failure()? ──▶ == b"1"?
   │                                                                             │ yes
   ▼                                                                             ▼
yield Android  ──▶  install (timeout, reason preserved)  ──▶  logcat.start  ──▶  coverage.start
                                                                                      │
                                                                                 tool.execute
                                                                                      │
                                                            finally: logcat.cleanup ──┘   (producer stops)
                                                                     coverage.cleanup     (drain to EOF,
                                                                                           then metrics)
                                                                          │
                                        context manager finally: kill_emulator (device dies last)
```

The essential property of the tail: the device is alive for every step above the last line.

## Error Handling

| Error | Source | Strategy | Recovery |
|---|---|---|---|
| `RVCommandTimeoutError` | a single ADB probe during boot | Caught inside both phase loops, logged as WARNING, probe retried | Retry until the shared budget expires |
| `TimeoutError` | either boot phase exhausting the shared budget | Propagates out of `_wait_for_boot` | Wrapped in `EmulatorError` by the startup `try`; task fails as a boot failure; no install attempted |
| `ValueError` | invalid integer in a timeout env var | Propagates uncaught | Operator fixes the environment; a typo must not silently become the default |
| `RuntimeError` | `adb install` non-zero exit | Reason preserved and carried upward | Task fails with the ADB reason in `error_message` |
| `RVCommandTimeoutError` | `adb install` exceeding its new timeout | Process tree killed by `Command`, then raised | Task fails; the emulator session is torn down normally |
| `TaskExecutionError` | install failure or tool-component failure inside the session | Propagates with its own type (C2) | `TaskExecutor.execute()` marks the task ERROR with the true message |
| `EmulatorError` | genuine startup failure only | Raised by the narrowed startup `try` | Teardown still runs; port reclaimed via C5 |
| Exception inside finalization | `cleanup()` of either component | Caught and logged as WARNING inside `cleanup()` | Never replaces the exception being propagated |
| `OSError` during the final drain | `CoverageTracker` thread `finally` | Caught, logged as WARNING naming the file | Thread still terminates, handle still closed |

## Risks / Trade-offs

- **[C1 converts hidden failures into visible boot timeouts]** → This is the intended outcome, but it will change failure counts in running experiments, and no contention run is commissioned to find out in advance (D9). Mitigated instead by three properties of the change itself: C4 makes the budget an env var, so a value that proves too low is corrected in a compose without a rebuild; the default rises to 300 s in the same change; and C7 makes boot failures land in a bucket that is empty today, so the first real run reports the problem rather than hiding it. If new `TimeoutError`s appear, the system is measuring boot honestly for the first time and the default needs raising, not the gate weakening.
- **[300 s may still be insufficient]** → Three historical timeouts exceeded it, and this change will not measure the real distribution before shipping. Mitigated by the `elapsed` instrumentation plus the env-var escape hatch, and by treating the value as explicitly provisional until production observation supplies the distribution (D9).
- **[C5 adds a 10 s teardown cost on failed launches]** → Mitigated by making the post-kill sleep conditional on a successful kill (D4).
- **[Deleting the inline finalization block changes success-path timing]** → The work is identical and now runs one step earlier relative to teardown, still inside the `with`. Covered by an explicit test that finalization precedes `adb emu kill`.
- **[Reordering finalization contradicts five documented statements]** → Handled explicitly: the comment at `executor.py:435`, `docs/architecture/rv-platform.md:262` and `:888`, and `docs/architecture/subsystem-rv-experiment.md:279` and `:816` are all corrected with the reason, rather than silently diverging (D6). The risk is that one is missed and the tree keeps asserting both orders at once, so the correction is a single task group with an explicit file list.
- **[Sixty-two existing tests sit in the blast radius, with brittle assertions]** → `test_android.py` asserts exact argv, exact log strings including `"(timeout=180s)"`, a 3-element `Command` `side_effect` list, and `patch("time.time", side_effect=range(20))`. Their failure is expected. Mitigated by rewriting the counted `time.time()` `side_effect` lists as a monotonic fake clock, so the tests stop encoding call counts and stop breaking on unrelated future edits.
- **[A new `RV_*` variable can kill every container]** → `validate_env_vars.sh` exits 64 for any `RV_*` not declared as an `ENV_*` constant. Mitigated by treating constants.py, `.env.example`, README.md, the composes, and the bats test as one atomic task group.
- **[`INSTALL_FAILED_INSUFFICIENT_STORAGE` may be an independent cause]** → The image AVD has `disk.dataPartition.size = 800M` against 6 GB on the host AVD. Recorded as an **untested hypothesis**; C6 is what lets the next occurrence distinguish it from the boot-gate cause in a single record. Not asserted as fact anywhere in this change.

## Testing Strategy

| Layer | What to test | How | Count |
|---|---|---|---|
| Unit — core | Boot gate acceptance and rejection, argv purity, shared budget, env resolution and precedence, install timeout, context-manager boundary, orphan reclamation, reason propagation | `Command` mocked; `MagicMock` results must set `is_failure.return_value` explicitly, since the default `MagicMock` is truthy; monotonic fake clock instead of counted `time.time` lists | ~20 |
| Unit — platform | Single firing point, order, idempotence of the second `cleanup()`, non-masking of the original exception, no install after boot timeout, consistent device resolution | Components mocked; assert call order and relative position against emulator teardown | ~10 |
| Unit — analysis | Drain recovers trailing lines, does not double-count, precedes `flush_diagnostics`, survives `OSError`, stays inert when already stopped | Real temp file, real thread, controlled appends | ~6 |
| Unit — monitoring | Bucket classification for both boot signatures and the composite install message | Table-driven over verbatim `error_message` strings taken from artifacts | ~6 |
| Lint / contract | `ENV_*` registry drift; Docker allow-list acceptance | `scripts/check_env_vars_drift.py`, `tests/lint/test_env_vars_drift.py`, `tests/integration/test_validate_env_vars.bats` | ~4 |
| Rewrite | `test_emulator_boot_retry.py` (5), `test_android.py` (10) | Rewritten against the new contract; stale gh50 phase-3 `side_effect` entries removed (P4) | 15 |
| E2E local | `rv-experiment run` over `apks_examples/cryptoapp.apk`: `tool_execution_start` no longer `null`, composite message gone | Single container | 1 run |
| Production observation | Boot `elapsed` values and the `emulator/boot` bucket, read from the first real experiment run after this change lands | No dedicated run: a 0.86 % failure rate needs ~350 tasks before absence is evidence (D9) | 0 runs |

All pytest invocations use the CI contract: `--import-mode=importlib -o "addopts="`.

## Open Questions

1. **`RV_APK_INSTALL_TIMEOUT` default — RESOLVED: 600 s.** There was no current value to preserve — `adb install` had no timeout at all — and no measured distribution of install durations exists. With no contention run commissioned (D9), the value is settled by judgement rather than measurement: the single install the E2E performs is a sanity check, not a distribution, and the `core` delta deliberately states the obligation without a number.

   **600 s, erring long deliberately.** The two failure modes are not symmetric. A value set too high only delays the detection of a hang that is already fatal to the task; a value set too low kills a healthy install and turns a slow host into a failed experiment — the same class of false failure this whole change exists to remove. On a cold-booted emulator under container contention, `adb install` covers the APK transfer plus the package manager's `dex2oat` of an instrumented APK, which is the slow part and scales with both APK size and host load. 600 s is twice the boot budget and far above any healthy install observed, while still bounding the case the timeout exists for: a hung install holds the emulator session open for the whole task, because it sits between boot and tool execution.

   The value is an environment variable read at the point of use, so a host that needs more raises it in its compose — no code change, no image rebuild. It is recorded in `.env.example`, `README.md`, `CLAUDE.md`, `.claude/project-info.md` and the two canonical composes.
2. **Carrier for the ADB reason (C6) — RESOLVED: the exception, not a result object.** `EmulatorManager.install_app` keeps `-> bool` for the success path and reports failure by letting the exception propagate rather than converting it to `False`. The `RuntimeError` that `Android.install_apk` raises already carries the ADB exit code and the `INSTALL_FAILED_*` text, so a result object would be a new type built to transport information that already has a carrier — and a raised exception cannot be dropped the way the returned `False` was, which is exactly how the reason was lost in all 1,174 records.

   The two hops above it follow from that. `EmulatorComponent.install_app` keeps the contract its spec scenario fixes — build an `EmulatorError` naming the app, hand it to `ErrorHandler`, return `False` — and additionally holds the composed message in `last_install_error`, because a boolean carries no text and the *executor* is the layer that turns a failed install into the task's `error_message`. `TaskExecutor._run_emulator_session` raises `TaskExecutionError` with that message, falling back to the old generic string only when no reason was recorded. The reason therefore reaches `task.result.error_message` without any layer changing its return type.
3. **Whether phase 1 should remain beyond this change.** Not open *within* gh92: the `core` delta mandates both phases, so phase 1 stays here. What is open is whether it survives afterwards — with phase 2 restored as a real gate, `init.svc.bootanim` under `-no-boot-anim` adds little. Keeping it now is the conservative choice and preserves the 322-occurrence historical signal; removing it is a P1 simplification to argue separately, once the real boot-time distribution exists.
4. **Scope of the INV-CORE-43 sweep — RESOLVED: bounded to `util/android/`, with the remainder recorded.** The grep found eleven `invoke()` call sites in that directory. Two were already checked (`install_apk`'s install result; `EmulatorManager.disable_animations`, via `is_success()`). Two are fixed here because this change's invariants cover them: the discarded `adb root` result, now inspected and logged at DEBUG — rejection is expected under `-read-only`, so a warning on every install would be noise — and `adb emu kill`, whose result INV-CORE-52 turns into the condition for the settling delay.

   The remaining seven are left to a separate P3 cleanup, because no invariant in this change governs them and widening the sweep would grow the blast radius of an already high-risk change: `simulate_reboot` (zero production callers), the signature-mismatch `uninstall_cmd` inside `install_apk` (its failure surfaces through the retry install, which *is* checked), `uninstall_apk`, `grant_permissions` (zero production callers — the only call site is commented out), the `readlink` in `install_apk` (a local command, not a device one), `EmulatorManager.clear_logcat` (returns `True` whenever nothing raised) and `LogcatManager`'s logcat clear. That cleanup pairs naturally with removing the two dead methods rather than fixing their result handling.
