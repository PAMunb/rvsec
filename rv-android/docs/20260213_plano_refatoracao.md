# Refactoring Plan: Remove Over-Built Infrastructure from rv-android-core

**Date**: 2026-02-13
**Author**: Pedro Henrique Teixeira Costa (with Claude Code assistance)
**Status**: Active — backlog populated (Issues #3-#7)

## 1. Motivation

During the system's development, the foundation module `rv-android-core` was designed with infrastructure capabilities that anticipated a larger scale of usage than what actually materialized. The EventBus was built with asynchronous processing, priority queues, and 4 worker threads — but the system only uses synchronous publishing. The ErrorHandler was designed with 30+ type-specific handlers each meant to implement distinct recovery strategies — but every single handler performs the same action: log the error and return True. The PerformanceMonitor was built to collect and aggregate runtime metrics — but no code ever reads the collected data.

This is not unusual in research software that evolves iteratively. Early architectural decisions were made when the system's needs were unclear, and the infrastructure was designed with flexibility in mind. Now that the system has stabilized and the actual usage patterns are clear, the speculative infrastructure has become dead weight — code that must be understood, maintained, and navigated without providing any functional value.

The goal of this refactoring plan is to remove the dead infrastructure, making the codebase match what the system actually does. This aligns directly with Principle 1 (Simplicity): "the right amount of complexity is the minimum needed for the current task."

## 2. How This Plan Was Produced

Two external LLM analyses (Gemini and Qwen, stored in `docs/analise_gemini.md` and `docs/analise_qwen.md`) provided an initial list of refactoring suggestions. These analyses identified several categories of potential improvements: EventBus coupling, Singleton abuse, component over-engineering, configuration duplication, CLI complexity, state management, and more.

We performed an independent, evidence-based audit of the actual codebase to validate each suggestion. The audit measured concrete usage metrics: how many times each EventType is published, how many exception types are actually raised, whether PerformanceMonitor data is ever consumed, and so on. The results showed that the LLM analyses were largely wrong about *what* the problems are — they cited inflated numbers and proposed solutions that would add complexity (DI containers, state management services, error categorization frameworks). However, the user's intuition that the system has unnecessary complexity was correct. The problem is more specific: **over-built infrastructure in rv-android-core that was designed for anticipated needs that never materialized**.

The following table summarizes the audit results that ground this plan:

| Component | Designed For | Actual Usage | Dead % |
|-----------|-------------|--------------|--------|
| EventBus async processing (4 worker threads, priority queue) | Asynchronous event handling | Zero async events in production code | 100% |
| EventBus priority system (5 event + 4 handler priority levels) | Prioritized processing | All subscribers use default priority | 100% |
| EventType enum (31 types) | Comprehensive lifecycle tracking | 7 types actually published | 77% |
| Exception hierarchy (49 types) | Granular error handling per type | ~19 types actually raised | 61% |
| ErrorHandler type-specific handlers (30+ registered) | Distinct recovery strategies per error | All handlers do identical log+return | ~90% |
| PerformanceMonitor | Metrics collection and analysis | Collects data, but no code reads it | 100% |
| EventHistoryManager | Event history queries and filtering | Never queried by any module | 100% |
| Circuit Breaker (CommandCircuitBreaker) | Command execution protection | Never instantiated in production | 100% |

**Estimated dead infrastructure**: ~1,500 lines of code and 4 dormant worker threads across `rv-android-core`.

## 3. What We Rejected (and Why)

Several suggestions from the LLM analyses were rejected because they would add complexity rather than reduce it, or because the problem they address does not exist in the actual codebase. Documenting these rejections is important so that future analyses do not re-propose them.

**Singleton to Dependency Injection migration** — Both analyses recommended replacing the Singleton pattern (EventBus, ErrorHandler, LoggingManager, PerformanceMonitor) with constructor-based Dependency Injection. In a multi-tenant web application or a library consumed by many different clients, this would be sound advice. But RV-Android is a single-context research tool: there is one experiment running at a time, one event bus, one logger. DI would add constructor plumbing across dozens of classes (passing `event_bus=`, `error_handler=`, `logger=` through every constructor chain) without providing any real benefit. The singletons are well-understood, thread-safe, and consistent. The actual number of `get_instance()` calls (253 total, dominated by 140 LoggingManager calls) is modest for a 73K-line codebase. This is standard Python practice, not an anti-pattern in this context.

**ExecutionSessionComponent consolidation** — Gemini proposed consolidating the 5 execution components in rv-platform into a single `ExecutionSessionComponent`. The audit showed that the TaskExecutor is 483 lines — a reasonable size for an orchestrator managing a 3-phase execution workflow with emulator lifecycle, logcat capture, coverage tracking, and tool execution. The 5 components have 168-354 lines each, with clearly distinct responsibilities. Consolidating them would not reduce total code — it would just move it into a larger class, reducing cohesion without reducing complexity.

**Configuration hierarchy refactoring** — Both analyses suggested unifying configuration classes to reduce field duplication. The audit found no actual duplication: each module owns its schema (PlatformConfig, ExperimentConfig, ToolConfig), and the composition between them is correct. ExperimentConfig creates a PlatformConfig when delegating to the platform — this is proper layering, not duplication.

**rv-screen-parser module split** — Gemini proposed splitting the module into XML parsing and visual analysis. The audit confirmed the module is already well-split internally: 5,539 lines of XML/Visitor code and 4,989 lines of OpenCV/Tesseract code in separate packages. Creating a new top-level module would add pyproject.toml overhead, a new `__init__.py`, and cross-module import management without functional benefit.

**Error categorization framework** — Qwen proposed adding error categories (transient, permanent, critical) with recovery strategies (retry with exponential backoff, circuit breakers, graceful degradation). This would add a sophisticated error management framework to a system where the actual recovery strategy is universally "log and continue." The framework would be dead infrastructure from the day it was committed.

**CLI simplification, state management service, centralized temp resource management, centralized system operations** — All rejected on the basis that they address problems the audit did not find. The CLI serves a research audience effectively. Temporary resources are managed with 1,201 context manager uses across the codebase. State management is straightforward for the single-context execution model. System operations are not significantly duplicated between modules.

## 4. Refactoring Backlog: 5 Issues

All five issues follow the **Quick Path** track from `docs/WORKFLOW.md` (Section 8). The rationale for Quick Path is clear: every issue removes code without introducing new behavior, requires no design decisions about alternatives, and has an obvious mechanical plan. Per the WORKFLOW.md decision guide: "Does it remove/refactor without adding new documented behavior? → Quick Path."

Each issue will use the **Refactoring** issue template from `.github/ISSUE_TEMPLATE/refactoring.yml`, with the track field overridden to "Quick Path" (the template defaults to FF SDD, which is not appropriate for pure cleanup).

The Quick Path workflow for each issue has three phases:

```
Phase 1: Analyze  →  Phase 2: Fix  →  Phase 3: Verify
```

- **Phase 1 (Analyze)**: Create `openspec/changes/2026-02-DD-GH<N>-<short-name>/plan.md` with file inventory and acceptance criteria. Skills: `/rv-analyze-dead-code`, `/rv-analyze-module`, or direct code reading.
- **Phase 2 (Fix)**: Implement the removal using `/rv-cleanup` orchestrator. Back up removed files to `backup/` per P3 (No Backward Compatibility). For issues touching 20+ files, use subagent orchestration (WORKFLOW.md Section 5).
- **Phase 3 (Verify)**: Run `/rv-verify` (tests + lint). Grep for zero dangling references. Confirm acceptance criteria from `plan.md`. Archive the change directory to `openspec/archive/`.

Cross-referencing convention: the change directory name includes the issue number (`GH<N>`), `plan.md` header includes `GitHub Issue: #N`, commits use `refs #N` during work and `closes #N` in the final commit.

---

### Issue 1: Remove Circuit Breaker (smallest, isolated)

**Template**: Refactoring
**Track**: Quick Path
**Priority**: Medium
**Affected Domains**: Core (rv-android-core)
**Related NFRs**: NFR01 (Maintainability)
**Estimated LOC reduction**: ~200 lines

**Description**: The `CommandCircuitBreaker` class in `rv-android-core/src/rv_android_core/commands/circuit_breaker.py` implements a complete circuit breaker pattern (~200 lines) with open/closed/half-open states, failure thresholds, and recovery timers. However, the circuit breaker is never instantiated in any production code path. It was built anticipating that command execution (ADB, shell commands) might benefit from automatic failure detection and request suppression — but the system evolved to handle command failures through simpler mechanisms (try/except with logging). The associated `CircuitBreakerOpenError` exception and its ErrorHandler registration are also dead code.

**Tasks**:
1. Back up `commands/circuit_breaker.py` to `backup/`
2. Delete the `circuit_breaker.py` file
3. Remove `CircuitBreakerOpenError` from `exceptions.py`
4. Remove circuit breaker handler registration from ErrorHandler
5. Update `commands/__init__.py` exports
6. Delete circuit breaker tests
7. Grep for zero remaining references

**Acceptance Criteria**:
- `grep -r "CircuitBreaker" modules/` returns zero results
- `grep -r "circuit_breaker" modules/` returns zero results (excluding backup/)
- All tests pass (`poetry run pytest`)

---

### Issue 2: Remove PerformanceMonitor

**Template**: Refactoring
**Track**: Quick Path
**Priority**: Medium
**Affected Domains**: Core (rv-android-core), Platform (rv-platform), Tools (rv-uiautomator)
**Related NFRs**: NFR01 (Maintainability)
**Estimated LOC reduction**: ~300-400 lines

**Description**: The `PerformanceMonitor` singleton collects runtime metrics through `measure_time()` context managers and `record_metric()` calls spread across 6 files. However, no production code ever reads the collected data — `get_metrics()` and `get_statistics()` are defined but never called outside of tests. The performance CSV output in rv-platform uses `TaskResult.performance` data (populated by the task execution timing code), not the PerformanceMonitor. This means the monitor has been silently accumulating metrics into memory throughout every experiment run with zero consumption.

The `measure_time()` calls in TaskExecutor and UIAutomator adapter create context managers that record timing data into the monitor's internal dictionary, but since nothing queries that dictionary, the only effect is minor memory allocation and Python overhead for entering/exiting the context managers.

**Tasks**:
1. Back up `util/performance/` directory to `backup/`
2. Remove `PerformanceMonitor` class and related utilities from rv-android-core
3. Remove `PerformanceMonitor.get_instance()` calls from rv-platform's `executor.py`
4. Remove `measure_time()` and `record_metric()` calls from rv-platform and rv-uiautomator
5. Verify performance CSV still generates correctly (it uses TaskResult, not PerformanceMonitor)
6. Update `__init__.py` exports in rv-android-core
7. Delete PerformanceMonitor tests
8. Grep for zero remaining references

**Acceptance Criteria**:
- `grep -r "PerformanceMonitor" modules/` returns zero results (excluding backup/)
- `grep -r "measure_time\|record_metric" modules/` returns zero results from PerformanceMonitor usage (there may be other unrelated uses of `measure_time`)
- Performance CSV still generates in experiment results
- All tests pass

---

### Issue 3: Remove dead EventBus infrastructure

**Template**: Refactoring
**Track**: Quick Path
**Priority**: High
**Affected Domains**: Core (rv-android-core)
**Related NFRs**: NFR01 (Maintainability), NFR05 (Performance)
**Estimated LOC reduction**: ~400-500 lines

**Description**: The EventBus in `rv-android-core/src/rv_android_core/event/bus.py` (531 lines) implements a sophisticated event system with features that the codebase does not use. The async subsystem allocates 4 worker threads at startup and manages a `PriorityQueue` for asynchronous event processing, but all 71 publish operations in the codebase use synchronous mode. The priority system defines 5 event priority levels and 4 handler priority levels, but all subscribers use defaults. The `EventHistoryManager` stores and indexes every event for later querying, but no production code calls `get_history()` or `get_statistics()`. There is also a leftover debug `print()` statement on line 222.

Additionally, the `EventType` enum defines 31 event types, but the audit found that only 7 are actually published anywhere in the codebase: `TASK_CREATED`, `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED`, `COVERAGE_UPDATED`, `COVERAGE_TRACKING_STARTED`, and `MOP_ERROR_DETECTED`. The remaining 24 types were defined for anticipated lifecycle events (experiment phases, workflow transitions, configuration changes) that were never wired into the system.

After this refactoring, the EventBus should be a simple synchronous publish/subscribe mechanism: a dictionary mapping event types to callback lists, with `publish()` iterating the callbacks and `subscribe()`/`unsubscribe()` managing the lists. The channel concept (DEFAULT, LIFECYCLE, ANALYSIS, ERROR) should be evaluated during implementation — if all active publishers use DEFAULT, channels can be removed too.

**Tasks**:
1. Remove async processing: delete `PriorityQueue`, worker threads, `publish_async()`, `publish_with_callback()`
2. Remove priority system: delete `EventPriority` constants, `HandlerPriority` enum, priority-based handler sorting
3. Remove `EventHistoryManager` class and all history tracking methods
4. Remove the debug `print()` on line 222
5. Remove 24 unused `EventType` values, keeping only the 7 that are published
6. Evaluate channel usage: if only DEFAULT is used in practice, remove channel support
7. Simplify remaining EventBus to a clean synchronous pub/sub (~150-200 lines)
8. Update all subscribers/publishers across modules to match the simplified API
9. Update `event/__init__.py` exports
10. Delete related tests for removed functionality, update remaining tests
11. Grep for zero dangling references to removed types/methods

**Acceptance Criteria**:
- EventBus is a synchronous pub/sub with no worker threads, no priority queue, no history tracking
- `EventType` enum has 7 values (or close, if implementation reveals additional active types)
- `grep -r "publish_async\|publish_with_callback\|EventHistoryManager\|EventPriority\|HandlerPriority" modules/` returns zero results
- All tests pass
- No debug print statements remain in bus.py

---

### Issue 4: Remove dead exception types and collapse ErrorHandler

**Template**: Refactoring
**Track**: Quick Path
**Priority**: High
**Affected Domains**: Core (rv-android-core)
**Related NFRs**: NFR01 (Maintainability)
**Estimated LOC reduction**: ~500-700 lines

**Description**: The exception hierarchy in `rv-android-core/src/rv_android_core/util/error/exceptions.py` defines 49 custom exception types organized in an inheritance tree rooted at `RVAndroidError`. The audit found that only ~19 of these types are actually raised anywhere in the codebase. The remaining ~30 types were defined for anticipated error scenarios that the code handles through simpler means (catching base types, or through general `try/except Exception` blocks).

Separately, the `ErrorHandler` in `rv-android-core/src/rv_android_core/util/error/error_handler.py` registers 30+ type-specific handlers through `_register_builtin_handlers()`. A critical finding from the audit is that **every single handler has identical behavior**: log the error with context information and return True. None of the handlers implement distinct recovery logic, retry strategies, or fallback paths. This means the elaborate handler registration system provides no value beyond what a single generic handler would provide.

This issue involves two coordinated tasks: (a) removing the ~30 dead exception types, and (b) collapsing the ErrorHandler from 30+ identical handlers to a minimal set. During the Analyze phase, a precise audit must verify which exception types are imported, raised, or caught across all modules — some types might be used in `except` clauses even if they are never raised, and those should be kept.

**Tasks**:
1. Audit every exception type: search for `raise TypeName`, `except TypeName`, and `import TypeName` across all modules
2. Remove exception types with zero raise/except/import references
3. Collapse ErrorHandler: replace 30+ identical handlers with 2-3 base-type handlers (or a single generic handler)
4. Remove unused handler registration from `_register_builtin_handlers()`
5. Update `__init__.py` exports to match the reduced set
6. Update imports across modules that referenced removed types
7. Grep for zero dangling references

**Acceptance Criteria**:
- Exception hierarchy has ~19 types (exact count determined during Analyze phase)
- ErrorHandler has 2-3 handlers maximum
- `poetry run pytest` passes
- `grep -r "RemovedTypeName" modules/` returns zero for each removed type

---

### Issue 5: TaskExecutor component lookup improvement

**Template**: Refactoring
**Track**: Quick Path
**Priority**: Low
**Affected Domains**: Platform (rv-platform)
**Related NFRs**: NFR01 (Maintainability)
**Estimated LOC reduction**: ~0 (code clarity improvement, not removal)

**Description**: The `TaskExecutor._execute_coordinated_components()` method in `rv-platform/src/rv_platform/execution/executor.py` identifies its 5 registered components by matching strings against their `name` property:

```python
for component in self.components:
    if "StaticAnalysis" in component.name:
        static_component = component
    elif "Coverage" in component.name:
        coverage_component = component
    elif "Emulator" in component.name:
        emulator_component = component
    elif "Logcat" in component.name:
        logcat_component = component
    elif "ToolExecution" in component.name:
        tool_component = component
```

This works reliably (component names are set deterministically in their `__init__` methods), but it is fragile in principle: renaming a component class or changing its `self.name` string would silently break the lookup without any type-checking error. Replacing this with a type-based lookup using `isinstance()` or a `{type: instance}` dictionary provides compile-time safety and makes the dependency on specific component types explicit rather than implicit through string conventions.

This is a low-priority improvement. The current code works and has not caused bugs. It is included in the backlog because it was independently identified by both LLM analyses and is a genuine (if minor) code clarity improvement.

**Tasks**:
1. Replace the string-matching loop with type-based component lookup
2. Update `_execute_coordinated_components()` to access components by type
3. Run tests to verify no behavior change

**Acceptance Criteria**:
- Zero string-based component identification (`"StaticAnalysis" in component.name` pattern removed)
- Component lookup uses Python types (isinstance or dict keyed by type)
- All tests pass with no behavior change

---

## 5. Execution Order

The issues are independent and can be executed in any order without merge conflicts. The recommended sequence is:

1. **Issue 1** (Circuit Breaker) — Smallest scope, isolated within `commands/`. Takes ~30 minutes. Good warm-up to establish the cleanup pattern.
2. **Issue 2** (PerformanceMonitor) — Cross-module but straightforward. Touches rv-android-core, rv-platform, rv-uiautomator.
3. **Issue 3** (EventBus) — Largest scope within rv-android-core. Requires the most careful work because the EventBus is used (even if lightly) across multiple modules.
4. **Issue 4** (Exceptions + ErrorHandler) — Needs the most thorough audit phase to determine exactly which types are safe to remove. Best done after the EventBus cleanup, since some exception types might be referenced by the EventBus infrastructure being removed in Issue 3.
5. **Issue 5** (TaskExecutor) — rv-platform, completely independent from rv-android-core changes. Can be done at any point.

Each issue is an independent commit (or PR, if the team prefers per-issue PRs). Each follows the Quick Path workflow with its own change directory in `openspec/changes/`.

## 6. Expected Impact

When all five issues are complete:

- **~1,400-1,800 lines of dead code removed** from the codebase
- **4 dormant worker threads eliminated** (EventBus async subsystem)
- **EventBus reduced from ~531 lines to ~150-200 lines** — a simple, understandable synchronous pub/sub
- **24 dead EventType values removed** (77% reduction in the enum)
- **~30 dead exception types removed** (61% reduction in the hierarchy)
- **ErrorHandler simplified from 30+ identical handlers to 2-3**
- **2 entire subsystems deleted** (PerformanceMonitor, CircuitBreaker)
- **Component lookup in TaskExecutor** uses Python types instead of string matching

The result is a codebase where the infrastructure matches actual usage — no speculative capabilities, no dead abstractions, no complexity that does not serve a real purpose.
