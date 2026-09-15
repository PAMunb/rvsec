# Design: rv-agent runtime MOP/coverage/diagnostic signal

## Context

See `proposal.md` (GitHub Issue #79; FR27 reward, FR30 MOP-guided navigation). The agent's MOP guidance is purely static (GATOR `directly_reaches_target`, consumed at `rvagent_visitor.py:243`); there is no runtime signal (`grep RVSEC` in `rv-agent` = 0). This design adds an incremental, per-step read of the app's logcat, reusing lower-layer parsers, and cross-references runtime coverage with the static flags the agent already holds. It is constrained by two investigated facts: the logcat file is already at the tool boundary (`task.result.logcat_file`), and RVSEC/RVSEC-COV deduplicate per process — so the signal is novelty-per-episode, not attribution. The change touches no rv-platform runtime path and no rvsec-core.

## Architecture

```
rv-platform LogcatComponent ──writes──► task.result.logcat_file  (RVSEC / RVSEC-COV [/ diagnostics if flag])
        │ (path only, via Task)                     │
        ▼                                            │ incremental read per step
 rvagent-tool adapter: logcat_feed_path ─────────────┤
        │ (flat str into RVAgentConfig)              ▼
        ▼                             rv-coverage: parse_logcat_line + DiagnosticEventParser
 rv_agent core (learn_node ~:677) ◄──── new events (cov / violation / diagnostic)
        │  cross-ref new COV signature × StaticAnalysisData.directly_reaches_target
        ▼
 reward / progress  (scope = OPEN DECISION)
```

Standalone: no platform, no `task.result.logcat_file` → agent optionally starts its own `LogcatManager` (`clear_buffer=False`) writing a path it then reads, or runs with no feed.

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `rvagent-tool` config mapping | Inject `task.result.logcat_file` → `RVAgentConfig.logcat_feed_path` | `Task` | flat `str \| None` |
| `RVAgentConfig.logcat_feed_path` (new field) | Carry the path into the core | `str \| None` | — |
| runtime-feed reader (new, rv-agent) | Incremental per-step read; reuse rv-coverage parsers; dedup by signature | `logcat_feed_path`, file offset | new events |
| static cross-ref | Map new COV signature → `directly_reaches_target` | `StaticAnalysisData` (already loaded) | confirmed-progress bool |
| reward hook (`learn_node` ~:677) | Turn events into reward/progress (all confirmed reaches + max-weight violations, one-shot) | events | reward |
| standalone `LogcatManager` (rv-android-core, reused) | Own capture, `clear_buffer=False` | device serial | logcat file |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Runtime Logcat Feed Source | `logcat_feed_path` field + per-step incremental read; reuse `parse_logcat_line`/`DiagnosticEventParser`; no `CoverageTracker` | `test_platform_reads_injected_path`, `test_standalone_own_capture`, `test_no_feed_no_error` |
| INV-AGT-60 (path only, no platform types) | Core imports no rv-platform; adapter does the mapping | `test_core_has_no_platform_import` |
| INV-AGT-61 (novelty only) | Reader dedups by signature; reward keyed on novelty | `test_repeated_coverage_not_new` |
| INV-AGT-62 (no 2nd capture / no clear under platform) | Platform path only reads; standalone uses `clear_buffer=False` | `test_platform_no_second_logcat`, `test_standalone_clear_buffer_false` |
| INV-AGT-63 (rvsec-core untouched) | No edits under `rvsec/`; bug documented | grep/review gate |
| Runtime-Confirmed MOP Progress | Cross-ref new COV × `directly_reaches_target`; recognize RVSEC violation | `test_new_directly_reaching_is_progress`, `test_violation_recognized` |
| Diagnostic Events | `DiagnosticEventParser.feed_line`; crash→hash-jump attribution | `test_crash_attributes_hash_jump`, `test_diagnostics_flag_off_inert` |
| Reward Scope (resolved) | All confirmed reaches (one-shot) + RVSEC violations (max weight, one-shot); diagnostics not in reward | `test_reward_all_reaches`, `test_reward_violation_max_once`, `test_violation_no_retrap` |
| INV-AGT-64 (reader-side one-shot) | Episode-local seen-set keyed on stable signature | `test_restart_does_not_rereward` |

## Goals / Non-Goals

**Goals:**
- Runtime-confirmed MOP progress + violation recognition, reusing existing parsers, with zero rv-platform coupling and zero rvsec-core change.
- Per-step incremental read (no background thread), bounding attribution to "since my last action."
- Work identically enough in platform mode (injected path) and standalone (own capture), behind one config seam.
- One-shot novelty reward (all confirmed reaches + max-weight violations) that cannot trap the agent on a spent screen.

**Non-Goals:**
- Fine action→event attribution or frequency-proportional reward (impossible under per-process dedup — INV-AGT-61).
- Diagnostics (crash/VerifyError/ANR) as reward inputs — deferred to v2; v1 keeps only crash-as-hash-jump-annotation.
- Fixing the `ErrorDescription` equals/hashCode bug (rvsec-core is out of scope — INV-AGT-63).
- Using the full `CoverageTracker` (over-heavy for a per-step novelty read).
- Any platform→tool feedback channel (vetoed).

## Decisions

- **Consume the file as a path, not the platform's tracker (D1).** The logcat file is already `task.result.logcat_file` at the tool boundary; the adapter injects it as a flat string. Alternative — tap the platform's `LogcatManager`/`CoverageTracker` object or stream — is rejected: it inverts the `AbstractTool` black-box contract, couples the agent loop to a platform component's lifecycle, and only works under the platform. A file path is plain domain data already on `Task`.
- **Per-step incremental read, not CoverageTracker (D2).** The agent acts in discrete steps; reading new bytes at the end of each step (in `learn_node` ~:677) is simpler (no thread/RLock), and the read window naturally scopes events to the last action. Reusing `parse_logcat_line`/`DiagnosticEventParser` avoids duplicating the RVSEC regex (P1/P3).
- **Novelty-per-episode semantics, made explicit (D3).** RVSEC/RVSEC-COV dedup per process (verified in rvsec-core and real logcats; process restarts re-log, events burst on lifecycle). So the signal is reward-for-novelty, not attribution. The spec encodes this as INV-AGT-61 to prevent future misuse.
- **New dependency rv-agent → rv-coverage (D4).** Needed to reuse the parsers; no cycle (rv-coverage depends only on rv-android-core). Alternative — reimplement parsing in rv-agent — violates P1/P3.
- **Reward scope RESOLVED (D5).** v1 reward = (a) all runtime-confirmed reaches (`reaches_target` ∪ `directly_reaches_target`) as one-shot novelty — a denser gradient toward MOPs than directly-only, which also reduces premature plateau; + (b) RVSEC violations at maximum weight (greater than any single coverage reward but same order of magnitude, not saturating), one-shot. Diagnostics are NOT reward inputs in v1; only crash-as-hash-jump-annotation is kept. The one-shot guarantee is enforced by a **reader-side seen-set** (INV-AGT-64), NOT by device-side dedup — because process restarts and the `ErrorDescription` `equals/hashCode` bug re-log events; without the reader guard, max-weight violations would re-reward and trap the agent (the exact stuck-on-a-screen risk raised in review). Max-weight is safe because the reward is one-shot and, once spent, change #78's plateau signal (S1) sees no further MOP progress on that screen and ejects the agent (tarpit / stochastic phase). An optional per-revisit decay is left as a tuning fallback, not implemented by default. Rationale for the alternatives rejected: directly-only coverage gives a sparser signal (single jackpot at the MOP call site) and more plateau risk; diagnostics-as-reward depends on `RV_LOGCAT_DIAGNOSTICS` (off by default), so tying reward to it would make the policy inconsistent across runs — deferred to v2.

## API Design

### `RVAgentConfig.logcat_feed_path: str | None`
New optional field. Set by `rvagent-tool` from `task.result.logcat_file`; None when absent. The core never inspects a `Task`.

### runtime-feed reader: `read_new_events(path: str, offset: int) -> (events, new_offset)`
Precondition: `path` exists (created-if-missing tolerated, as the platform writes it before the tool). Reads bytes from `offset`, feeds complete lines to `parse_logcat_line` and `DiagnosticEventParser.feed_line`, dedups coverage/violation by signature against an episode-local seen-set, returns new events and the advanced offset. No thread; called once per step.

### cross-ref: `is_confirmed_mop_progress(signature, static_data) -> bool`
Returns True when `signature` is newly covered this episode and `static_data` flags it `directly_reaches_target`.

## Data Flow

Per step: execute action → at step end, `read_new_events(logcat_feed_path, offset)` → classify events (new confirmed-reaching coverage / violation / crash) → dedup by reader-side seen-set → feed the reward hook (all confirmed reaches one-shot + max-weight violation one-shot) and the plateau signal → advance offset. Crash events annotate the subsequent hash jump so the WTG logic does not treat a restart as a new screen; crash does not contribute to reward.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `logcat_feed_path` missing/empty | Standalone without capture; path not yet written | Treat as "no feed" | Run as today, no signal |
| Partial last line | Reading a file being appended | Buffer the incomplete tail; parse on next read | No data loss |
| Dangling standalone `adb logcat` | Agent crash before teardown | Teardown stops the process (INV-RVA-05 point) | Process cleanup on teardown |

## Risks / Trade-offs

- [Per-process dedup limits the signal to novelty] → Encoded as INV-AGT-61; reward policy must not assume frequency/attribution.
- [Diagnostics require `RV_LOGCAT_DIAGNOSTICS=true`] → Documented precondition; with the flag off the diagnostic path is inert (no error), only RVSEC/COV are used.
- [File read latency / buffering] → Same latency the platform's own tracker sees; acceptable for a novelty signal. Partial-line buffering avoids corruption.
- [New rv-coverage dependency] → No cycle; smallest reuse surface (`parse_logcat_line` + `DiagnosticEventParser`), not the whole tracker.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | incremental read + dedup; cross-ref confirmed progress; violation recognition; crash→hash-jump attribution; diagnostics-off inert; no-feed no-op | Synthetic logcat files (real lines from `results/`), static-data fixture | ~9 tests |
| Integration | rvagent-tool injects `logcat_feed_path` from `task.result.logcat_file`; core has no rv-platform import; standalone `clear_buffer=False` + teardown | Tool adapter + config; import-graph assertion | ~3 tests |
| E2E | live feed with an instrumented APK (may require `RV_LOGCAT_DIAGNOSTICS=true`) | rv-experiment run | manual/1 |

## Open Questions

- **Reward scope (v1)** — RESOLVED (see D5): all runtime-confirmed reaches (one-shot novelty) + RVSEC violations (max weight, one-shot); diagnostics deferred to v2 (only crash-annotation in v1). No blocking open questions remain.
- **Tuning (non-blocking)** — the exact numeric weights and whether to enable the optional per-revisit violation decay are empirical tuning left to implementation/experimentation, within the invariants above (violation > single coverage reward, same order of magnitude, one-shot).
