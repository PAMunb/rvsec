# Delta Specification: Platform — Boot Precondition and Finalization Ownership

## Purpose

`rv-platform` executes one task at a time through `TaskExecutor`, which drives a set of duck-typed components across three coordinated phases. Phases 1 and 2 — static-analysis load and coverage-tracker initialization — run outside any emulator, because they need no device. Phase 3 runs inside `TaskExecutor._run_emulator_session()`, bracketed by the emulator context manager, and is where the device work happens: install the APK, start logcat capture, start coverage tracking, run the testing tool, finalize.

This delta touches two things in that phase: the precondition under which installation is attempted, and who owns finalization.

**The precondition.** `_run_emulator_session` installs the APK immediately after the context manager yields, and this is correct in itself — the contract of `start_emulator` says the device is ready. That contract is currently violated in `rv-android-core` (see the `core` delta), so the platform installs against devices that never completed boot. The platform's own obligation is narrower but real: state the precondition explicitly, so that a future regression in the layer below is a spec violation rather than an unstated assumption. This requirement's existing text already asserts the principle for installation itself — *"App installation is verified via `CommandResult.is_failure()`"* — and this delta extends the same discipline to the gate that precedes it.

There is also an inconsistency inside the platform layer, and it runs to three sites rather than two. The emulator is booted on a port read from `tool_config.parameters["device_port"]`, the APK is installed on a serial read from `tool_config.parameters["device_serial"]`, and logcat is captured from a serial `LogcatComponent` derives on its own, falling back to `task.config.device_id` — which `Platform._generate_tasks` in turn populates from `parameters["device_serial"]` with a literal `"emulator-5554"` fallback. Each site carries its own default, so a task that injects only one of the two keys boots one device, installs on another, and captures logcat from a third.

This is reachable from the CLI. The tool-specification DSL accepts arbitrary `@key=value` parameters, so `--tools "monkey@device_port=5558"` yields `{"device_port": 5558}` with no `device_serial`. Boot and install then target `emulator-5558` while logcat targets `emulator-5554`. The install case announces itself with a failure; the logcat case does not — it produces an empty capture, zero coverage, and, since this delta also makes that file the single reconstruction source for resume, a silently empty reconstruction.

**The finalization owner.** Coverage and logcat are finalized by two separate pieces of code today. One is inline at `execution/executor.py:440-448`, inside the `with`, so it runs with the emulator alive; it calls `coverage_component.stop_tracking()`, `coverage_component.process_results()`, then `logcat_component.stop_capture()`. The other is the components' own `cleanup()` methods, reached from `execute()`'s `except` at `:251-263` via `_cleanup_resources()` → `_cleanup_components()` — by which point the context manager's `finally` has already destroyed the emulator. Both do the same work; `CoverageComponent.cleanup()` and `LogcatComponent.cleanup()` contain nothing *but* that work.

Two readings of this were investigated and neither survived. The first held that an exception after installation *skips* finalization: false, the `cleanup()` path reaches it. The second held that the surviving problem was loss of the logcat tail on the failure path, where finalization runs after teardown. That does not hold either, and the reason is task state. `ResultProcessorComponent` processes only `TaskState.COMPLETED` (INV-PLT-10, `result_processor.py:212`), and `TaskStorage.get_completed_tasks()` is the same source `_skip_completed_tasks()` consumes. A task ending in `ERROR` therefore never enters any CSV **and** is never skipped on resume — it re-executes from scratch and writes a fresh logcat. The truncated tail of a failed task's logcat has no consumer.

What is actually at stake is the reverse. A `COMPLETED` task's `.logcat` file *is* the reconstruction source for resume (INV-PLT-15/16/18), and today it is closed in order, with the emulator alive, by the inline block. Moving finalization to `cleanup()` alone would push the success path to post-teardown and damage exactly that artifact. So the single owner must be positioned inside the `with`, in a `finally` covering its body — that placement is what guarantees the success path cannot drift, on either exit.

The owner calls the components' existing `cleanup()` methods rather than duplicating their bodies. This removes the duplicated implementation (P3) while keeping every component's `initialize/execute/cleanup` lifecycle intact — the contract is duck-typed by an explicitly recorded architectural decision, and `_cleanup_components` still invokes both across all five registered components, so **INV-PLT-06** (cleanup-always) continues to hold.

The second invocation is inert, by two different mechanisms that must both be checked. The two *stops* are guarded: `CoverageTracker.stop()` returns early on `is_running`, and `LogcatManager.stop_capture()` acts only when `logcat_process` is set and nulls it afterwards. `CoverageComponent.cleanup()` however also calls `process_results()`, which carries **no guard** — it re-reads the tracker's repository, recomputes `calculate_metrics()` and re-`update()`s `task.result.coverage_metrics`. It is inert because it is a pure function of a repository that can no longer change once the tracker has stopped, not because it declines to run. Any future change that makes `process_results()` depend on wall-clock time or mutate the repository breaks this property silently.

Both `cleanup()` methods also swallow their own exceptions, which is required here — a finalization error inside a `finally` on the failure path would otherwise replace the original exception, reintroducing precisely the diagnostic corruption this change exists to remove.

The order is inverted to logcat-then-coverage, and the tree asserts the opposite in more places than the first survey found. Six were identified initially — the comment at `executor.py:435`, `docs/architecture/rv-platform.md:262` and `:888`, `docs/architecture/subsystem-rv-experiment.md:279` and `:816`, and the main platform spec — and a second sweep with wider patterns found further sites in the same two architecture documents plus four in `modules/rv-platform/docs/architecture.md` (the AD-2 rationale, a scenario summary asserting "cleanup in reverse", a sequence diagram and a data-flow diagram). Two of them justify the order as finalizing "metrics against a complete log", which is precisely backwards, since it is the coverage tracker that reads and the logcat producer that writes. Every one of them is corrected with its reason rather than merely reordered or deleted; the count is deliberately not restated as a fixed number here, because the first attempt to fix "the five" missed six.

The two are decoupled by the filesystem: `adb logcat` writes the file, and `CoverageTracker` opens that same file by path with an independent handle (`tracker.py:293`), so stopping the producer cannot EOF or otherwise disturb the consumer. Stopping the producer first freezes the file, which is what makes the tracker's final drain (see the `analysis` delta) deterministic. The two corrections are only meaningful together.

## Data Contracts

### Input

- `tool_config.parameters["device_port"]: int` — emulator port for this task (source: `ExecutionController`; default `5554`).
- `tool_config.parameters["device_serial"]: str` — ADB serial for this task (source: `ExecutionController`; default `"emulator-5554"`).
- `task.config.skip_installation: bool` — when `True`, installation is bypassed.

### Output

- `task.result.coverage_metrics: dict` — written by `CoverageComponent.process_results()` from the tracker's in-memory repository.
- `task.result.logcat_file: str` — path to the captured logcat, persisted in `tasks.json` and re-read on resume for `COMPLETED` tasks.
- `task.result.error_message: str` — for failed tasks, now carrying the originating exception's own identity rather than a relabelled one.

### Side-Effects

- **[Device]**: emulator boot and teardown, APK installation, logcat capture — all bracketed by the context manager.
- **[File System]**: the `.logcat` file is closed by `stop_capture()`; for `COMPLETED` tasks this file is the resume reconstruction source.

### Error

- `TaskExecutionError` — installation failed, or the tool component reported failure. It MUST reach `execute()`'s handler with its own type.
- `EmulatorError` — the emulator failed to start. Reserved for genuine startup failures only.

## Invariants

- **INV-PLT-27**: `TaskExecutor._run_emulator_session()` MUST NOT attempt APK installation unless the emulator context manager yielded after a boot completion that was positively observed. The platform relies on `EmulatorManager.start_emulator` to enforce this (core INV-CORE-44); the obligation is recorded here so that a device which never completed boot receiving an install attempt is a specification violation, not merely an implementation defect.

- **INV-PLT-28**: Within a single task, **every component that addresses the device MUST address the same one**. The emulator port used to boot, the device serial used to install, and the device serial used to capture logcat MUST all come from a single resolution over `tool_config.parameters`, such that a task supplying only `device_port` or only `device_serial` cannot boot one device and install or capture on another. Independent per-call defaults are prohibited, anywhere.

  Three sites derive this today and each has its own fallback: `EmulatorComponent` (`components/emulator.py`), `LogcatComponent` (`components/logcat.py`, falling back to `task.config.device_id`) and `Platform._generate_tasks` (`platform.py`, falling back to a literal `"emulator-5554"` when populating `TaskConfiguration.device_id`). The divergence is reachable from the CLI, not hypothetical: the tool-specification DSL accepts arbitrary `@key=value` parameters, so `--tools "monkey@device_port=5558"` produces `{"device_port": 5558}` with no `device_serial`, and the platform then boots and installs on `emulator-5558` while capturing logcat from `emulator-5554`.

  Logcat is the load-bearing case rather than an afterthought. A wrong-device capture raises nothing: it yields an empty `.logcat`, coverage of zero, and — because INV-PLT-29 makes that file the single reconstruction source for resume (INV-PLT-15/16/18) — a silently empty reconstruction. That is the same class of silent failure this change exists to remove.

- **INV-PLT-29**: Coverage and logcat finalization MUST have exactly one firing point, located in a `finally` covering the body of the emulator `with` block in `_run_emulator_session()`, so that it executes with the emulator still alive on both the success and the failure path. The inline block at `executor.py:440-448` MUST be deleted rather than retained alongside it (P3).

- **INV-PLT-30**: That firing point MUST invoke the components' own `cleanup(context)` methods rather than reimplementing their bodies. `CoverageComponent.cleanup()` and `LogcatComponent.cleanup()` MUST continue to exist and MUST continue to be invoked by `_cleanup_components()`, preserving INV-PLT-06 and the uniform duck-typed `initialize/execute/cleanup` contract across all five components registered by `Platform` (StaticAnalysis, Emulator, Logcat, Coverage, ToolExecution — the set `_cleanup_components()` iterates). Finalization MUST therefore be idempotent, and MUST NOT raise: an exception escaping the `finally` would replace the exception that caused the failure.

- **INV-PLT-31**: The finalization order MUST be logcat first, then coverage. `LogcatManager.stop_capture()` terminates the `adb logcat` producer; `CoverageTracker.stop()` terminates the consumer, which reads the same file through an independent handle. Stopping the producer first freezes the file so the consumer's final drain (analysis INV-ANA-53) observes a complete input.

  Every documented statement of the opposite order MUST be corrected to this one together with its reason, not merely deleted. At the time of writing there are five: the comment at `executor.py:435`, `docs/architecture/rv-platform.md:262` and `:888`, and `docs/architecture/subsystem-rv-experiment.md:279` and `:816`. Leaving any of them standing would reproduce the situation this invariant exists to end — a documented ordering rule with no reason attached, which the next reader has to re-derive.

## MODIFIED Requirements

These two notes are deliberately outside the requirement bodies: `openspec archive` copies a requirement body verbatim into `openspec/specs/platform/spec.md`, and a note about what this delta changed has no place in a permanent spec (P4). Prose here, above the first requirement header, is not synced.

The **Android Emulator Management** block below carries the requirement in full, including the five scenarios that already existed, so nothing is lost at archive time. Two edits in it are unrelated to the boot gate and are called out here rather than left to be discovered in a diff: the original read *"**future** parallel execution requires isolated emulator instances"*, which is no longer future — the composes run 8 to 16 containers today; and the "APK Installation Failure" scenario's trigger moves from `EmulatorManager.install_app()` *returning `False`* to it *reporting failure*, because C6 leaves the carrier open (design Open Question 2) and the scenario must not prejudge it.

The **Component-Based Task Execution** block below likewise carries its requirement in full, including the six scenarios that already existed. It is modified for two reasons the rest of this delta creates. First, its narrative and its "Successful Three-Phase Execution" scenario both assert the finalization order this change inverts — and because no other MODIFIED block in this delta touches this requirement, archiving without it would leave `openspec/specs/platform/spec.md` asserting *coverage before logcat* while `executor.py` does the opposite, which is exactly the documented-rule-with-no-reason situation INV-PLT-31 exists to end. Second, `LogcatComponent`'s device resolution belongs to this requirement rather than to "Android Emulator Management", so the scenario enforcing INV-PLT-28 across all three sites is added here.

### Requirement: Android Emulator Management (FR07, NFR04, NFR07)

The platform MUST manage the full lifecycle of Android emulator instances during task execution. This includes starting the emulator with a named AVD, allocating a unique device port, installing the APK under test, and stopping the emulator after task completion. Emulator management is encapsulated in `EmulatorComponent`, which operates within the Phase 3 context manager in `TaskExecutor._run_emulator_session()`.

Dynamic port allocation is necessary because the ICST study runs multiple tool configurations across 188 applications, and parallel execution requires isolated emulator instances. Each task can specify a unique `device_port` (default 5554) and `device_serial` (default `emulator-5554`) via `tool_config.parameters`, enabling multiple concurrent emulator sessions without port conflicts. Both values MUST resolve to the same device within a task: the port used to boot and the serial used to install MUST NOT be derived independently, because a task supplying only one of the two keys would otherwise boot one device and install on another.

The emulator is started using the `EmulatorManager.start_emulator()` context manager, which ensures proper cleanup on both normal and exceptional exits. **APK installation MUST be attempted only after boot completion has been positively observed** — that is, only after the device reported `sys.boot_completed == "1"`. Installation is then verified via `CommandResult.is_failure()`; if installation fails, `EmulatorError` is raised and the task transitions to `ERROR` state, carrying the reason reported by ADB.

A failure occurring inside the emulator session — installation, logcat, coverage, or tool execution — MUST reach `TaskExecutor.execute()` with its own exception type. It MUST NOT be relabelled as a failure to start the emulator.

#### Scenario: Successful Emulator Startup and APK Installation

- **WHEN** a task is being executed with `apk_name="cryptoapp.apk"` and `no_window=True`
- **THEN** `EmulatorComponent.start_emulator("RVSec")` MUST start the emulator in headless mode on the default port 5554
- **AND** the context manager MUST NOT yield until the device reported `sys.boot_completed == "1"`
- **AND** `EmulatorComponent.install_app()` MUST install the APK on the emulator

#### Scenario: APK Installation Failure

- **WHEN** `EmulatorComponent.install_app()` is called and `EmulatorManager.install_app()` reports failure
- **THEN** the component MUST raise `EmulatorError` with message containing the app name
- **AND** the message MUST carry the reason reported by ADB, such as `INSTALL_FAILED_INSUFFICIENT_STORAGE`
- **AND** the error MUST be handled by `ErrorHandler` with task context
- **AND** the method MUST return `False`

#### Scenario: Installation is not attempted against a device that did not boot

- **WHEN** the boot wait exhausts its budget for the device on port 5554
- **THEN** `TimeoutError` MUST propagate out of `EmulatorManager.start_emulator` as the cause of an `EmulatorError`
- **AND** `EmulatorComponent.install_app()` MUST NOT be called
- **AND** the task's `error_message` MUST NOT contain `"Failed to install application"`

#### Scenario: Session failure keeps its own identity

- **WHEN** `_run_emulator_session()` raises `TaskExecutionError("Failed to install application", task_id)` inside the `with` block
- **THEN** `TaskExecutor.execute()` MUST record an `error_message` of that type
- **AND** the stored `error_message` MUST NOT read `"Failed to start emulator RVSec caused by TaskExecutionError: ..."`

#### Scenario: Dynamic Port Allocation for Parallel Execution

- **WHEN** a task has `tool_config.parameters = {"device_port": 5558, "device_serial": "emulator-5558"}`
- **THEN** `EmulatorComponent.start_emulator()` MUST pass port `5558` to `EmulatorManager.start_emulator()`
- **AND** `EmulatorComponent.install_app()` MUST pass `device_serial="emulator-5558"` to `EmulatorManager.install_app()`

#### Scenario: Partially injected device parameters resolve consistently

- **WHEN** a task has `tool_config.parameters = {"device_port": 5558}` and no `device_serial` key
- **THEN** the serial used for installation MUST be `"emulator-5558"`, derived from the port actually booted
- **AND** it MUST NOT fall back independently to `"emulator-5554"`

#### Scenario: Skip Installation When Configured

- **WHEN** `task.config.skip_installation` is `True`
- **THEN** `EmulatorComponent.install_app()` MUST return `True` without calling `EmulatorManager.install_app()`
- **AND** a skip log message MUST be emitted

#### Scenario: Logcat Buffer Clearing

- **WHEN** `EmulatorComponent.clean_logcat()` is called
- **THEN** the component MUST call `EmulatorManager.clear_logcat()` to reset the logcat buffer
- **AND** if clearing fails, the error MUST be logged as a warning (non-critical)

### Requirement: Component-Based Task Execution (FR09, NFR02)

The platform MUST execute tasks through a component-based architecture where each component handles a specific concern (static analysis, emulator, logcat, coverage, tool execution). Components implement the `ITaskComponent` interface with `initialize(context)`, `execute(context)`, and `cleanup(context)` methods. The `TaskExecutor` coordinates component execution in three phases.

This design exists because task execution involves multiple orthogonal concerns that interact in specific ways. Static analysis data must be loaded before the coverage tracker can classify methods. The coverage tracker must be initialized before the emulator session begins. Inside the emulator session, logcat capture must start before coverage tracking, and coverage tracking must start before tool execution. After tool execution the order reverses for a stated reason: `adb logcat` is the producer writing the file and `CoverageTracker` is the consumer reading that same file through an independent handle, so **logcat MUST stop before coverage stops** — freezing the file is what lets the consumer's final drain observe a complete input. Startup ordering is enforced by `TaskExecutor._execute_coordinated_components()`; finalization ordering is enforced at the single firing point required by INV-PLT-29.

Every component that addresses the device MUST obtain its port and serial from the one resolution required by INV-PLT-28. A component MUST NOT carry its own fallback for a missing `device_port` or `device_serial` key.

Components are identified by string matching on their `name` property (`"StaticAnalysis"`, `"Coverage"`, `"Emulator"`, `"Logcat"`, `"ToolExecution"`). The executor iterates registered components and assigns them to the appropriate phase based on name containment.

The executor logs lifecycle transitions: task started, task completed, task failed, and tool started (for accurate timing coordination).

#### Scenario: Successful Three-Phase Execution

- **WHEN** a task is executed with all five components registered (StaticAnalysis, Emulator, Logcat, Coverage, ToolExecution)
- **THEN** Phase 1 MUST execute `StaticAnalysisComponent.execute()` outside the emulator session
- **AND** Phase 2 MUST execute `CoverageComponent.execute()` outside the emulator session
- **AND** Phase 3 MUST start the emulator via `EmulatorComponent.start_emulator("RVSec")`
- **AND** inside the emulator session, the execution order MUST be: install app -> start logcat -> start coverage -> mark tool execution start -> execute tool -> stop logcat -> stop coverage and process coverage results
- **AND** the task state MUST transition from `RUNNING` to `COMPLETED`

#### Scenario: Logcat captures the device that was booted

- **WHEN** a task has `tool_config.parameters = {"device_port": 5558}` and no `device_serial` key — the form the tool DSL produces for `--tools "monkey@device_port=5558"`
- **THEN** `LogcatComponent` MUST capture from `"emulator-5558"`
- **AND** it MUST NOT fall back to `task.config.device_id` or to a literal `"emulator-5554"`
- **AND** `TaskConfiguration.device_id`, populated by `Platform._generate_tasks`, MUST resolve to that same serial

#### Scenario: Component Execution Failure

- **WHEN** `StaticAnalysisComponent.execute()` or `CoverageComponent.execute()` returns `False` and raises `TaskExecutionError`
- **THEN** the executor MUST catch the exception and update task state to `ERROR`
- **AND** `_cleanup_resources()` MUST be called to clean up all registered components

#### Scenario: Missing Emulator or Tool Component

- **WHEN** the executor has no `EmulatorComponent` or no `ToolExecutionComponent` registered
- **THEN** Phase 3 (emulator session) MUST be skipped
- **AND** a warning MUST be logged: "Missing emulator or tool component - skipping emulator session"

#### Scenario: Task Without App Instance

- **WHEN** `TaskExecutor.execute()` is called and `task.app` is `None`
- **THEN** the method MUST return `False` immediately without executing any components
- **AND** the task state MUST be set to `ERROR` with message "Task has no app instance set"

#### Scenario: Cleanup After Exception

- **WHEN** an exception occurs during component execution
- **THEN** `_cleanup_resources()` MUST call `cleanup(context)` on all registered components
- **AND** if a component's `cleanup()` raises an exception, the error MUST be logged as a warning but MUST NOT prevent cleanup of remaining components
- **AND** post-execution hooks MUST still be called with `success=False`

#### Scenario: Pre/Post Execution Hooks

- **WHEN** hooks have been registered via `add_pre_execution_hook()` and `add_post_execution_hook()`
- **THEN** pre-execution hooks MUST be called before task state transitions to `RUNNING`
- **AND** post-execution hooks MUST be called after execution completes, with `(task, True)` on success or `(task, False)` on failure


## ADDED Requirements

### Requirement: Single-Owner Coverage and Logcat Finalization (FR09, NFR04)

Coverage and logcat finalization MUST happen at exactly one point in the task lifecycle, and that point MUST be inside the emulator session, so it executes while the device is still alive regardless of how the session ends.

The firing point MUST be a `finally` covering the body of the `with` block in `_run_emulator_session()`. The inline sequence currently at `executor.py:440-448` MUST be deleted; retaining it beside the new owner would leave two implementations of the same work (P3).

The owner MUST call `logcat_component.cleanup(context)` and then `coverage_component.cleanup(context)`, in that order. It MUST NOT reimplement their bodies. Both components keep their `cleanup()` methods and both are still invoked by `_cleanup_components()`, so INV-PLT-06 holds and the duck-typed lifecycle contract stays uniform across the five registered components; the repeat invocation is inert because both underlying stops are guarded, and because `process_results()` — which is not guarded — recomputes from a repository that a stopped tracker can no longer change.

The order matters for a stated reason. `adb logcat` is the producer, writing to a file; `CoverageTracker` is the consumer, reading that same file through an independent handle. Stopping the producer first freezes the file, so the consumer's final drain sees a complete input. Stopping the consumer first leaves the producer appending lines that the consumer will never read — lines that are present in the file but absent from the in-memory repository, which is what `process_results()` reads.

Finalization MUST NOT raise. Both `cleanup()` methods already catch their own exceptions and log a warning; that behavior is required here, because an exception escaping a `finally` on the failure path would replace the exception being propagated and destroy the failure's diagnosis.

#### Scenario: Success path finalizes with the emulator alive

- **WHEN** a task completes normally and control reaches the end of the `with` block
- **THEN** `logcat_component.cleanup(context)` MUST be called, then `coverage_component.cleanup(context)`
- **AND** both MUST execute before `EmulatorManager` issues `adb emu kill`
- **AND** `task.result.coverage_metrics` MUST be populated

#### Scenario: Failure path finalizes with the emulator alive

- **WHEN** `tool_component.execute(context)` returns `False` and `TaskExecutionError` is raised inside the `with` block
- **THEN** the `finally` MUST call both `cleanup()` methods before the exception leaves the `with`
- **AND** they MUST execute before the context manager's teardown kills the emulator
- **AND** the `TaskExecutionError` MUST continue to propagate unchanged

#### Scenario: Finalization does not mask the original failure

- **WHEN** an exception is propagating out of the `with` body and `coverage_component.cleanup(context)` encounters an internal error
- **THEN** that internal error MUST be logged as a warning
- **AND** the exception reaching `TaskExecutor.execute()` MUST still be the original one

#### Scenario: Repeat invocation from _cleanup_components is inert

- **WHEN** `_cleanup_components(context)` invokes `cleanup()` on both components after the emulator session already finalized them
- **THEN** `CoverageTracker.stop()` MUST return immediately because `is_running` is `False`
- **AND** `LogcatManager.stop_capture()` MUST take no action because `logcat_process` is `None`
- **AND** `CoverageComponent.process_results()` MAY run a second time, since it carries no guard
- **AND** `task.result.coverage_metrics` MUST hold the same values after the second invocation as after the first

#### Scenario: Only one implementation of finalization exists

- **WHEN** `execution/executor.py` is inspected after this change
- **THEN** it MUST contain no direct calls to `stop_tracking()`, `process_results()`, or `stop_capture()`
- **AND** the only path to those methods MUST be through the components' `cleanup()`
