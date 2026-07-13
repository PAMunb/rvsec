## Purpose

The rv-agent's monitored-operation (MOP) guidance is today entirely static: it derives MOP relevance from GATOR reachability flags (`reachable → reaches_target → directly_reaches_target` on `MethodCoverageData`, `rv-android-core/domain/coverage.py:62-69`), consumed via `rvagent_visitor.py:243`. Static reachability over-approximates — a path may exist that the running app never triggers (the "30% curse") — so the agent cannot tell which of its actions actually executed a monitored operation. There is no runtime signal in the agent (`grep RVSEC` in `rv-agent` returns 0).

This delta adds a runtime signal that closes the static→dynamic loop. The agent reads the app's logcat incrementally, per exploration step, and reuses the existing lower-layer parsers (`parse_logcat_line` for RVSEC/RVSEC-COV, `DiagnosticEventParser` for crash/VerifyError/ANR from #72) to detect three kinds of runtime events: coverage of a method that statically `directly_reaches_target` (runtime-confirmed MOP progress), a monitor violation (RVSEC — the project's terminal goal, JCA misuse), and a diagnostic event (crash/VerifyError/ANR). The signal is fed back into exploration progress/reward.

Two facts constrain the design and are part of the requirement. First, the logcat file already exists at the tool boundary as `task.result.logcat_file`, written by the platform's `LogcatComponent` before the tool runs; the agent must consume the file **as a path** (injected by the `rvagent-tool` adapter into a flat config field), never by reaching into rv-platform components or its logcat stream, and never by modifying rvsec-core. Second, both RVSEC and RVSEC-COV deduplicate **per process** (`CoverageSourceEmitter.java:47-57`; `ErrorCollector.java:36-42`): each signature/violation is logged once per app process and re-logged after a process restart, and events arrive in lifecycle-tied bursts. The runtime signal is therefore a **novelty-per-episode** signal — good for "did this action reach something new?" — and explicitly NOT reliable for fine action→event attribution or frequency-proportional reward.

## Data Contracts

### Input
- `logcat_feed_path: str | None` — path to the logcat file being written (source: `rvagent-tool` maps `task.result.logcat_file`; None in standalone without a feed). The `rv_agent` core receives only this path and stays ignorant of rv-platform.
- logcat lines (RVSEC / RVSEC-COV / diagnostic tags) — read incrementally from `logcat_feed_path`, parsed by `parse_logcat_line` and `DiagnosticEventParser.feed_line` (rv-coverage).
- `directly_reaches_target: bool` per method signature — from the `StaticAnalysisData` the agent already loads; cross-referenced with new RVSEC-COV signatures.

### Output
- `runtime_events` (per step) — the set of new coverage signatures, new violations, and diagnostic events observed since the previous step, consumed by the reward/progress logic.

### Side-Effects
- **[Device]** (standalone only): the agent may start its own `LogcatManager` with `clear_buffer=False`; it MUST stop that process at teardown.

### Error
- No new exceptions. A missing/empty `logcat_feed_path` means "no feed"; the agent runs exactly as today.

## Invariants

- **INV-AGT-60**: The `rv_agent` core MUST consume the feed only as a file path; it MUST NOT import rv-platform types nor read rv-platform component objects/streams. The platform→tool boundary is one-directional (a path passed through `RVAgentConfig`).
- **INV-AGT-61**: The runtime feed MUST be used as a novelty-per-episode signal only; the implementation MUST NOT claim per-action attribution or frequency-proportional reward from it, because RVSEC/RVSEC-COV deduplicate per process.
- **INV-AGT-62**: When running under the platform, the agent MUST NOT start a second `adb logcat` capture and MUST NOT clear the shared logcat buffer; it reads the existing `logcat_feed_path`. In standalone mode a self-started `LogcatManager` MUST use `clear_buffer=False`.
- **INV-AGT-63**: rvsec-core MUST NOT be modified by this change. The `ErrorDescription` `equals/hashCode` contract bug found during investigation is documented only.
- **INV-AGT-64**: Each reward-bearing runtime event (a covered reaching-method signature, a monitor violation) MUST be rewarded at most once per episode, enforced by a reader-side seen-set keyed on a stable signature. The implementation MUST NOT rely on device-side deduplication for one-shot behavior, because a process restart re-logs every signature and the `ErrorDescription` `equals/hashCode` bug re-logs some violations — either of which would otherwise re-reward the same event and trap the agent on one screen.

## ADDED Requirements

### Requirement: Runtime Logcat Feed Source (FR30)

The agent SHALL obtain runtime events by reading the app's logcat file incrementally, one read per exploration step, from a path supplied as `logcat_feed_path`. Under the platform this path is `task.result.logcat_file`, injected by the `rvagent-tool` adapter; the `rv_agent` core SHALL receive only the path (INV-AGT-60). It SHALL reuse `parse_logcat_line` and `DiagnosticEventParser.feed_line` (rv-coverage) and SHALL NOT instantiate the full `CoverageTracker` (no background thread). When under the platform, it SHALL NOT start a second `adb logcat` nor clear the buffer (INV-AGT-62).

#### Scenario: Platform mode reads the injected path
- **WHEN** `logcat_feed_path` is set to `task.result.logcat_file` and the app emits new RVSEC-COV lines after an action
- **THEN** the agent SHALL read the new lines at the end of that step
- **AND** it SHALL NOT start its own `adb logcat` process

#### Scenario: Standalone fallback with own capture
- **WHEN** the agent runs standalone and a feed is wanted
- **THEN** it SHALL start its own `LogcatManager` with `clear_buffer=False`
- **AND** it SHALL stop that process at teardown

#### Scenario: No feed configured
- **WHEN** `logcat_feed_path` is None and no standalone capture is started
- **THEN** the agent SHALL run exactly as today (no runtime signal), with no error

### Requirement: Runtime-Confirmed MOP Progress Signal (FR27, FR30)

The agent SHALL cross-reference each newly observed RVSEC-COV signature against the static `directly_reaches_target` flag it already loads, and SHALL treat a new directly-reaching signature as runtime-confirmed MOP progress — a stronger signal than the static `callback_signature` proxy of change #78. A newly observed RVSEC line (monitor violation) SHALL be recognized as the terminal exploration goal. The signal SHALL be treated as novelty-per-episode (INV-AGT-61).

#### Scenario: New directly-reaching coverage is confirmed progress
- **WHEN** an RVSEC-COV line appears for a method whose static flag is `directly_reaches_target=True` and that signature was not seen this episode
- **THEN** the step SHALL be marked as runtime-confirmed MOP progress

#### Scenario: Monitor violation recognized
- **WHEN** an RVSEC violation line appears (e.g. `MessageDigestSpec ... UnsafeAlgorithm ... found MD5`)
- **THEN** the agent SHALL recognize it as a monitor violation event (terminal goal)

#### Scenario: Repeated coverage within a process is not new
- **WHEN** a method already observed this process emits RVSEC-COV again (or after a process restart re-logs it)
- **THEN** it SHALL NOT be counted as new progress (dedup by signature on the reader side)

### Requirement: Crash Annotation for Hash-Jump Attribution (FR29, FR30)

In v1, diagnostic events are NOT reward inputs. When diagnostic capture is enabled (platform run with `RV_LOGCAT_DIAGNOSTICS=true`), the agent SHALL recognize crash events assembled by `DiagnosticEventParser` and use them for a single purpose: to attribute a subsequent structural-hash jump to a process restart rather than to a newly discovered screen. VerifyError and ANR events are parsed by the reused `DiagnosticEventParser` but are NOT consumed by v1 (their use as health/avoidance signals is deferred to a follow-up). When the flag is off, the logcat contains no diagnostic tags and this requirement is inert.

#### Scenario: Crash annotates a hash jump (not a reward)
- **WHEN** a FATAL crash block appears in the feed and the next dump has a different structural hash
- **THEN** the agent SHALL attribute the hash change to the crash/restart rather than to a newly discovered screen
- **AND** the crash SHALL NOT contribute to the reward

#### Scenario: VerifyError/ANR not consumed in v1
- **WHEN** a VerifyError or ANR event appears in the feed
- **THEN** it SHALL NOT enter the reward and SHALL NOT annotate the graph in v1 (deferred to a follow-up)

#### Scenario: Diagnostics flag off
- **WHEN** the platform runs with `RV_LOGCAT_DIAGNOSTICS` unset
- **THEN** the feed contains only RVSEC/RVSEC-COV
- **AND** the diagnostic-event path SHALL be inert with no error

### Requirement: Reward Scope (FR27)

The v1 reward mapping SHALL be: (a) every runtime-confirmed reaching method — a covered signature flagged `reaches_target` OR `directly_reaches_target` by static analysis — rewarded once per episode as novelty; and (b) every monitor violation (RVSEC line) rewarded with the maximum weight, once per episode. Diagnostic events SHALL NOT contribute to the reward in v1 (crash is used only for hash-jump attribution). Both reward sources are one-shot per episode via the reader-side seen-set (INV-AGT-64) and treated as novelty-per-episode (INV-AGT-61).

The maximum violation weight SHALL be strictly greater than any single coverage reward but of the same order of magnitude, so a violation is the clear priority target without saturating the value function and trapping the agent. Because a violation is rewarded once and then the plateau detector — now fed the MOP-progress signal by change #78 — sees no further MOP progress on that screen and drives the escape (tarpit / stochastic phase), max-weight is safe against getting stuck. An optional per-revisit decay of the violation reward MAY be added as a tuning fallback if empirical runs show lingering.

#### Scenario: All confirmed reaches rewarded as novelty
- **WHEN** a covered method flagged `reaches_target` (or `directly_reaches_target`) appears for the first time this episode
- **THEN** it SHALL contribute a novelty reward
- **AND** a subsequent re-observation of the same signature (including after a process restart) SHALL contribute nothing (INV-AGT-64)

#### Scenario: Violation rewarded at maximum weight, once
- **WHEN** a monitor violation (RVSEC line) is observed for the first time this episode
- **THEN** it SHALL contribute the maximum reward, greater than any single coverage reward but of the same order of magnitude
- **AND** a re-logged identical violation (restart or the `ErrorDescription` re-log) SHALL contribute nothing

#### Scenario: Max-weight violation does not trap the agent
- **WHEN** a violation has been rewarded on a screen and no further MOP progress occurs there
- **THEN** the plateau detector (fed the MOP-progress signal per #78) SHALL increment and trigger the configured escape
- **AND** the agent SHALL leave the screen rather than loop back to a spent reward
