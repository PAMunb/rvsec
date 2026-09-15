# Proposal: rv-agent runtime MOP/coverage/diagnostic signal

GitHub Issue: #79

## Why

The rv-agent's monitored-operation (MOP) guidance is today **entirely static**: it comes from GATOR reachability flags (`reachable → reaches_target → directly_reaches_target` on `MethodCoverageData`, `rv-android-core/domain/coverage.py:62-69`), consumed via `rvagent_visitor.py:243`. There is **no** runtime signal — `grep RVSEC` in `rv-agent` returns 0. Static reachability **over-approximates** (the "30% curse": a path exists, but at runtime the action may never trigger the monitored operation), so the agent explores blind to what actually executed. This change closes the static→dynamic loop by feeding runtime coverage, violation, and diagnostic events back into exploration, reusing lower-layer infrastructure that already exists — without touching rv-platform or rvsec-core.

## What Changes

- **Runtime feed source.** The agent reads the logcat file incrementally. Under the platform the path is already at the tool boundary as `task.result.logcat_file` (`TaskResult`, written by `LogcatComponent` **before** the tool runs); the `rvagent-tool` adapter (which already maps `Task → RVAgentConfig`) injects it as a flat field (`logcat_feed_path: str | None`), so the `rv_agent` core receives only a path and stays ignorant of the platform. In **standalone** mode the agent spawns its own `LogcatManager` with `clear_buffer=False` (avoiding an `adb logcat -c` that would wipe the shared buffer), or runs without the feed.
- **Reused parsers (new dependency rv-agent → rv-coverage, no cycle).** `parse_logcat_line` (RVSEC/RVSEC-COV) and `DiagnosticEventParser.feed_line` (crash/VerifyError/ANR from #72). It does **not** use the full `CoverageTracker` (background thread + RLock + metric computation): the agent operates in discrete steps and reads new lines at the end of each action (in `learn_node`, ~`:677`), which also bounds attribution to the "since my last action" window.
- **Signal use.** Cross-reference each new RVSEC-COV signature against the static `directly_reaches_target` flag the agent already loads → **runtime-confirmed** MOP progress (versus the static `callback_signature` proxy of #78/S1). An RVSEC line (monitor violation) is the project's terminal goal (JCA misuse). The #72 diagnostic events (crash = a bug plus a restart that explains a hash jump; VerifyError = broken instrumentation; ANR = an action to avoid) become exploration signals — **precondition**: the platform runs with `RV_LOGCAT_DIAGNOSTICS=true` (default off; RVSEC/COV are always in the file, diagnostics are not).
- **Semantics (investigated in rvsec-core and real logcats).** RVSEC-COV deduplicates 1× per signature **per process** (`CoverageSourceEmitter.java:47-57`); RVSEC 1× per `(spec,type,class,method,location)` per process (`ErrorCollector.java:36-42`). Consequence: the feed is a **novelty-per-episode** signal, **not** fine action→event attribution nor a frequency-proportional reward (process restarts re-log everything; events arrive in lifecycle-tied bursts). An `equals/hashCode` contract bug in `ErrorDescription` found during the investigation is **documented only** — it will not be fixed here (rvsec-core is not touched; a fix would change historical experiment metrics).

No **BREAKING** changes: with no feed path and no diagnostics flag, agent behavior is unchanged.

## Reward Scope (resolved)

The v1 reward scope, initially left open, is resolved (see `design.md` D5 and the `agent` delta "Requirement: Reward Scope"):
- (a) **All runtime-confirmed reaches** (`reaches_target` ∪ `directly_reaches_target`), one-shot novelty — a denser gradient toward MOPs than directly-only.
- (b) **RVSEC violations at maximum weight** (greater than any single coverage reward, same order of magnitude, non-saturating), one-shot.
- (c) **Diagnostics deferred to v2** — not reward inputs in v1; only crash-as-hash-jump-annotation is kept.
- (d) One-shot is enforced by a **reader-side seen-set** (INV-AGT-64), and max-weight is safe against getting stuck because change #78's plateau signal ejects the agent once the reward is spent.

Numeric weights and an optional per-revisit violation decay are non-blocking tuning left to implementation.

## Capabilities

### New Capabilities
<!-- None. This change modifies the existing agent capability; it introduces no new spec domain. -->

### Modified Capabilities
- `agent`: exploration/reward requirements gain a runtime signal source. MOP-guided navigation and reward (FR27, FR30) currently derive MOP relevance purely from static reachability; this change adds a runtime-confirmed MOP-progress signal, monitor-violation recognition, and optional diagnostic-event awareness, fed by an incremental per-step read of the logcat file. The signal's semantics (novelty-per-episode, not attribution) are part of the requirement.

## Impact

- **Modules**: `rv-agent` (primary — `learn_node`, reward, config field `logcat_feed_path`, standalone `LogcatManager` fallback); `rvagent-tool` (injects `logcat_feed_path` from `task.result.logcat_file`); `rv-coverage` (reused `parse_logcat_line` / `DiagnosticEventParser`); `rv-android-core` (`LogcatManager` reused in standalone).
- **Dependencies**: adds `rv-coverage` to `rv-agent`'s dependencies (no cycle — rv-coverage depends only on rv-android-core).
- **Requirements**: `agent` domain — FR27 (reward), FR30 (WTG/MOP-guided navigation). Relates to #72 (diagnostic events) and #77 (rv-agent revival). See `docs/PRD.md`.
- **Architectural constraints (non-negotiable)**: never tap the rv-platform logcat stream or its component objects (platform→tool feedback is vetoed); never modify rvsec-core. Reuse only lower layers (`rv-android-core` `LogcatManager`; `rv-coverage` parsers).
- **Cross-references**: independent of #78 (state identification); #78's static `callback_signature` proxy is the static counterpart to this change's runtime confirmation.
