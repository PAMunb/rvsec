# Design: Logcat Diagnostic Events (crashes, VerifyError, ANR)

## Context

Logcat capture is wired to `adb logcat -v threadtime -s RVSEC:V RVSEC-COV:V`
(`rv-android-core/util/android/logcat_manager.py`). The `-s` flag silences all other tags at the
source, so crashes, class-load `VerifyError`s, and ANRs never reach the captured `.logcat`. Empirically,
across the 2,028 `cmp_*` logcats only `RVSEC`/`RVSEC-COV` appear; the `--------- beginning of crash`
separator shows in 8.8% of runs with its content filtered away. The result is an invisible confounder:
an instrumented APK that dies early looks like a low-coverage tool result.

This change makes those failures observable behind an opt-in flag, with a hard non-regression
constraint (G1): with the flag off, the adb command, the `.logcat`, and every existing CSV schema must
be byte-identical to baseline — every experiment depends on that baseline (memory:
`feedback_never_change_experiment_config`). The authoritative Phase 0 ideation, with the full decision
record (D1–D9), blast-radius investigation, and acceptance criteria (G1–G7), is
`docs/20260621_plano_logcat_tags_expandidas.md`. Relevant requirements: FR07–FR11, FR12–FR14, FR33–FR37;
NFRs for non-regression and performance.

## Architecture

```
                 RV_LOGCAT_DIAGNOSTICS (env)
                          │
   rv-experiment CLI (Click envvar=) ──► ExperimentConfig ──► PlatformConfig
                                                                  │ logcat_diagnostics
                                                                  ▼
 rv-platform: LogcatComponent ──tags=default+diagnostic──► rv-android-core: LogcatManager
                                                                  │  adb logcat -s ... (+diag tags)
                                                                  ▼
                                                            <task>.logcat  (device → file)
                                                                  │
        ┌─────────────────────────────────────────────────────────┴───────────────┐
        ▼ (live, background thread)                                                 ▼ (offline / resume)
 rv-coverage: CoverageTracker._process_line                       rv-coverage: parse_logcat_file
        │  parse_logcat_line(line)  ── RVSEC/COV ──► register_rv_error/method_call │
        │  diag_parser.feed_line(line) ─ crash/verify/anr ─► register_diagnostic_event
        └───────────────────────────────────┬───────────────────────────────────┘
                                             ▼
                       rv-android-core: LogcatRepository
                         classes / errors / unique_errors      (metrics — untouched)
                         diagnostic_events                      (isolated, new)
                                             │
                                             ▼
                 rv-platform: result_processor → app_events.csv (stack_head; full trace stays in .logcat)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `LogcatManager.start_capture` (core) | Emit adb command; add diagnostic tags when enabled | `tags: List[str]` | adb process → `.logcat` |
| `RvDiagnosticEvent` (core `domain/log.py`) | Validated model for a diagnostic event | parsed fields | dataclass/`to_dict` |
| `LogcatRepository.{register,get}_diagnostic_event(s)` (core `domain/coverage.py`) | Isolated event collection | `RvDiagnosticEvent` | list of dicts |
| `DiagnosticEventParser` (rv-coverage) | Stateful multi-line assembly by `(tag,pid,tid)` | `line: str` | `Optional[RvDiagnosticEvent]` |
| `parse_logcat_file` / `CoverageTracker` (rv-coverage) | Drive both parsers; register results | `.logcat` lines | populated repository |
| `result_processor._generate_app_events_csv` (rv-platform) | Write `app_events.csv` | repository events | CSV file |
| `LogcatComponent` (rv-platform) | Thread the flag into capture | `PlatformConfig` | `start_capture(tags=...)` |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|--------------------------|---------------|------|
| core: Opt-in capture (INV-CORE-37/38) | `logcat_manager.py` `start_capture`, `constants.ENV_LOGCAT_DIAGNOSTICS` | `test_logcat_manager_diagnostics` |
| core: `RvDiagnosticEvent` model | `domain/log.py` | `test_rv_diagnostic_event` |
| core: isolated collection (INV-CORE-39) | `domain/coverage.py` `register/get_diagnostic_event(s)` | `test_repository_diagnostics_isolation` |
| analysis: stateful parser (INV-ANA-46/47/48) | `parser/log/diagnostic_parser.py` (new); `logcat_parser.py` unchanged | `test_diagnostic_parser` |
| analysis: tracker + file integration | `analysis/coverage/tracker.py`, `logcat_parser.parse_logcat_file` | `test_tracker_diagnostics`, `test_parse_file_diagnostics` |
| platform: `app_events.csv` (INV-PLT-19/20) | `result_processor.py` `_generate_app_events_csv` | `test_app_events_csv`, `test_app_events_resume` |
| platform: flag threading (INV-PLT-21) | `components/logcat.py`, `PlatformConfig` | `test_logcat_component_flag` |
| G1 non-regression | golden re-parse of `cmp_*` logcats | `test_rvsec_cov_golden` |
| G7 E2E | `examples/cryptoapp` option-menu NPE | manual/E2E run |

## Goals / Non-Goals

**Goals:**
- Capture and structure crashes (`AndroidRuntime:E`), class-load `VerifyError` (`art`/`dalvikvm:E`), and
  ANR (`ActivityManager:W`) behind an opt-in flag, off by default.
- Zero change to the RVSEC/COV hot path, coverage/MOP metrics, and existing CSV schemas.
- Survive the resume reconstruction path (gh58).

**Non-Goals:**
- Native tombstones / SIGSEGV (`DEBUG:F`/`libc:F`) — out of v1 (D8); instrumentation is DEX/Java and the
  dataset has 0 ARM-translation-only APKs. Reopened only by the data trigger in the plan §8.1.
- Live `--pid` filtering (D6) — attribution is by the crash block (`Process:`/`ANR in`).
- Turning the flag on in baseline experiment compose (D9) — opt-in per campaign, user decision.
- Refactoring `parse_logcat_line` to a union return type (option A) — rejected by blast-radius (D1).

## Decisions

**D1 — Separate stateful parser over a union return type** (formal record: ADR-001,
`modules/rv-coverage/docs/adr/ADR-001-separate-stateful-diagnostic-parser.md`). `parse_logcat_line`
stays a pure 2-tuple function. A new `DiagnosticEventParser` holds the multi-line state. *Alternative (A):* change the return
to `Optional[RvLogEvent]` (a union base class). Rejected: A touches 6 production call-sites + 7 test
asserts and breaks the public API (`rv_coverage/__init__.py`); B is additive (0 churn on the hot path).
The RVSEC/COV path (1 line → 1 record) is orthogonal to diagnostics (multi-line, stateful).
> Explicitly rejected: turning `parse_logcat_line` into a 3-tuple `(error, coverage, diagnostic)` — that
> is option A in disguise and contradicts D1.

**D2 — Unified `RvDiagnosticEvent` with a `category` enum** over three separate models
(`RvCrashLog`/`RvVerifyErrorLog`/`RvAnrLog`). Adding a category is an enum value, not a class (P1).

**D3 — `stack_head` in CSV, full trace in the `.logcat`.** Avoids CSV escaping/volume; the `.logcat`
remains the source of truth and `original_msg` carries the full block in memory / on reconstruction.

**D4 — Isolated `diagnostic_events` collection.** Metric calculation reads only `self.classes` /
`self.errors`; a separate collection cannot perturb coverage/MOP/`total_errors` (confirmed in code).

**D5 — Opt-in flag `RV_LOGCAT_DIAGNOSTICS`**, default off, plumbed via the existing `RV_*` Click
`envvar=` pattern. The `tags` parameter already exists on `LogcatManager.start_capture`.

**D6 — Attribution by block** (`Process: <pkg>` / `ANR in <pkg>`). The capture component has no package
name at capture start, and `adb logcat --pid` is impractical mid-stream.

## API Design

### `DiagnosticEventParser` (rv-coverage, `parser/log/diagnostic_parser.py`)

```python
class DiagnosticEventParser:
    """Assemble multi-line diagnostic events from logcat lines, grouped by (tag, pid, tid)."""

    def feed_line(self, line: str) -> Optional[RvDiagnosticEvent]:
        """Pre: a raw threadtime line.
        Returns a completed event when the current line closes the buffered block
        (key change or non-continuation), else None. Non-matching lines are skipped."""

    def flush(self) -> Optional[RvDiagnosticEvent]:
        """Post: emit any still-buffered event at end of input; idempotent thereafter."""
```

### `RvDiagnosticEvent` (core, `domain/log.py`)

```python
@validated_model(["category", "class_full_name", "method", "message"])
class RvDiagnosticEvent(BaseValidatedModel):
    category: str            # "crash" | "verify_error" | "anr"
    class_full_name: str
    method: str
    message: str
    source: str = ""
    process: str = ""
    pid: str = ""
    tid: str = ""
    fatal: bool = False
    stack_head: str = ""
    n_frames: int = 0
    original_msg: str = ""
    time_occurred: datetime = Field(default_factory=datetime.now)
    time_since_task_start: int = 0
```

### `LogcatRepository` (core, `domain/coverage.py`)

```python
def register_diagnostic_event(self, event: RvDiagnosticEvent) -> None: ...
def get_diagnostic_events(self) -> List[Dict[str, Any]]:  # sorted by time_since_task_start
```

### Capture (core, `logcat_manager.py`) and flag (platform)

`start_capture(output_file, tags=None, ...)` already accepts `tags`. `LogcatComponent` computes
`tags = default_tags + DIAGNOSTIC_TAGS if cfg.logcat_diagnostics else None` where
`DIAGNOSTIC_TAGS = ["AndroidRuntime:E", "art:E", "dalvikvm:E", "ActivityManager:W"]`.

## Data Flow

1. Flag flows env → CLI → `ExperimentConfig` → `PlatformConfig` → `LogcatComponent`.
2. `LogcatComponent` starts capture with baseline or augmented tags; device writes `.logcat`.
3. Live: `CoverageTracker` feeds each line to `parse_logcat_line` (RVSEC/COV) and to a
   `DiagnosticEventParser` (diagnostics); completed events are registered.
4. Offline/resume: `parse_logcat_file` does the same over the file, so reconstruction repopulates events.
5. `result_processor` writes `app_events.csv` from `get_diagnostic_events()`; other CSVs unchanged.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Unparseable diagnostic content | `DiagnosticEventParser` | log WARNING, skip (no event) | none needed |
| Non-threadtime line (separators) | parser regex | skip silently | none needed |
| Per-task CSV write failure | `result_processor` | log WARNING, skip task row | continue run |
| Missing `.logcat` on resume | reconstruction path | existing gh58 handling | task has no events |

## Risks / Trade-offs

- [Capture change alters experiment baseline] → opt-in flag default off; INV-CORE-37 byte-identical gate; G1.
- [State in parser bugs the hot path] → option B keeps `parse_logcat_line` untouched; RVSEC/COV golden test.
- [Diagnostics pollute metrics] → isolated collection; INV-CORE-39 / INV-ANA-48 / INV-PLT-19.
- [`art`/`dalvikvm` emit at W not E] → validate priority in the E2E run; widen to `art:W` if observed.
- [Volume in long runs] → named error-priority tags only, no `*:E` catch-all.
- [False positive `isAndroidRuntime()` substring] → match the parsed tag field, not the line (INV-ANA-47).

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | `DiagnosticEventParser` multi-line/flush/categories/false-positive | fixtures (canonical formats) | ~10 |
| Unit | `RvDiagnosticEvent`, repository isolation, `start_capture` tag set | direct, mock | ~8 |
| Unit | `app_events.csv` rows + schema-unchanged for other CSVs | tmp dir, mock repo | ~5 |
| Integration | flag threading end-to-end (config → component → command) | wired config | ~3 |
| Integration | resume reconstruction repopulates events | reconstruct from fixture logcat | ~2 |
| Golden | RVSEC/COV byte-identical re-parse of a `cmp_*` logcat | diff vs baseline | ~1 |
| E2E | cryptoapp option-menu NPE captured | run with flag on | manual |

## Open Questions

- Exact priority of `art`/`dalvikvm` verification logs (E vs W) on the target AVD — resolved empirically
  in the E2E run (AC7.3); widen the tag if needed.
- Whether the live `CoverageTracker` should `flush()` on a quiescence timeout or only at stop — default:
  flush at stop and on key change; revisit if a final crash is observed truncated.
