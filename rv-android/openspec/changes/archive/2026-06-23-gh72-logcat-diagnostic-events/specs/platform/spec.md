# Delta Spec: Platform — Diagnostic Events CSV and Capture Flag Wiring

## Purpose

The platform domain (`rv-platform`) runs tasks and materializes results. `result_processor.py` writes
the per-task CSVs (`coverage.csv`, `errors.csv`, `summary.csv`), and `components/logcat.py`
(`LogcatComponent`) starts logcat capture. On resume, the repository is rebuilt from the captured
logcat via `_reconstruct_repository_from_logcat` → `parse_logcat_file` (the gh58 path).

This delta adds a dedicated `app_events.csv` writer for diagnostic events and threads the
`RV_LOGCAT_DIAGNOSTICS` flag from configuration into capture. The new CSV stores one row per diagnostic
event with a `stack_head` summary; the full multi-line trace stays in the `.logcat` (decision D3),
avoiding CSV escaping/volume problems. The existing CSV schemas are left untouched so that downstream
consolidation scripts and the paired Wilcoxon analysis keep working unchanged. Because diagnostic events
are reconstructed from the logcat on resume (the parser runs inside `parse_logcat_file`), `app_events.csv`
survives resumed tasks just like `errors.csv`.

The flag is consumed here: `LogcatComponent` passes `tags = default_tags + diagnostic_tags` to
`LogcatManager.start_capture` (which already accepts a `tags` parameter) only when diagnostics are
enabled; otherwise it passes nothing and the baseline command is emitted.

## Data Contracts

### Input
- `logcat_diagnostics: bool` — from `PlatformConfig` (sourced from the experiment CLI / `RV_LOGCAT_DIAGNOSTICS`).
- `LogcatRepository.get_diagnostic_events()` — parsed events for the task (in-memory or reconstructed).

### Output
- `app_events.csv` — header
  `apk,rep,timeout,tool,time,category,exception_class,method,source,message,process,pid,fatal,n_frames,stack_head`;
  one row per diagnostic event.

### Side-Effects
- **[Filesystem]**: writes `app_events.csv` under the results directory alongside the existing CSVs.

### Error
- Per-task write failures SHALL be logged at WARNING and skipped without aborting the run (mirrors
  `_write_task_error_data`).

## Invariants

- **INV-PLT-19**: The headers and column order of `coverage.csv`, `errors.csv`, and `summary.csv` MUST
  remain byte-identical to baseline; the diagnostic feature MUST NOT add columns to them.
- **INV-PLT-20**: Diagnostic events MUST survive the resume reconstruction path — a task whose repository
  is rebuilt from its `.logcat` MUST still produce its `app_events.csv` rows.
- **INV-PLT-21**: WHEN `logcat_diagnostics` is `false`, `LogcatComponent` MUST start capture with the
  baseline tag set (no diagnostic tags passed).

## ADDED Requirements

### Requirement: Diagnostic Events CSV Generation (FR14)

`result_processor` SHALL generate a per-run `app_events.csv` containing one row per diagnostic event,
using `LogcatRepository.get_diagnostic_events()`, with the column set
`apk,rep,timeout,tool,time,category,exception_class,method,source,message,process,pid,fatal,n_frames,stack_head`.
The full multi-line stack trace SHALL NOT be written to the CSV (it remains in the `.logcat`). The
existing `coverage.csv`/`errors.csv`/`summary.csv` writers and schemas SHALL remain unchanged.

#### Scenario: One row per diagnostic event with stack_head only
- **WHEN** a task's repository holds one crash event for `br.unb.cic.cryptoapp`
- **THEN** `app_events.csv` contains one row with `category=crash`,
  `exception_class=java.lang.NullPointerException`, `process=br.unb.cic.cryptoapp`, `fatal=true`,
  and a non-empty `stack_head`
- **AND** the row contains no multi-line trace (the full block stays in the `.logcat`)

#### Scenario: Existing CSV schemas unchanged
- **WHEN** the run completes with diagnostics enabled
- **THEN** the headers of `coverage.csv`, `errors.csv`, and `summary.csv` are byte-identical to baseline

#### Scenario: app_events survives resume reconstruction
- **WHEN** a task is processed via `_reconstruct_repository_from_logcat` (resume) and its `.logcat`
  contains a crash block
- **THEN** the reconstructed repository yields the crash event and `app_events.csv` includes its row

### Requirement: Capture Flag Threading to LogcatComponent (FR07, FR08)

The platform SHALL thread the `RV_LOGCAT_DIAGNOSTICS` setting from `PlatformConfig` into
`LogcatComponent`, which SHALL pass the augmented tag set to `LogcatManager.start_capture` only when
diagnostics are enabled. When disabled, capture SHALL use the baseline tags.

#### Scenario: Enabled flag augments capture
- **WHEN** `PlatformConfig.logcat_diagnostics` is `true`
- **THEN** `LogcatComponent` calls `start_capture(tags=default_tags + ["AndroidRuntime:E","art:E","dalvikvm:E","ActivityManager:W"])`

#### Scenario: Disabled flag uses baseline capture
- **WHEN** `PlatformConfig.logcat_diagnostics` is `false` (default)
- **THEN** `LogcatComponent` starts capture without passing diagnostic tags (baseline command emitted)
