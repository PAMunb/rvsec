# G8 — Real E2E across both entry points (Phase 5 evidence)

Executed 2026-06-17 on the real stack. APK `apks_examples/cryptoapp.apk`, tool `ape`,
`--specification-set jca --instrumentation-variant dexlib2 --repetitions 2 --timeout 60`.
Emulator lifecycle owned by rv-platform throughout; interruption was a SIGINT to the
rv-experiment **process** only (PID, not the emulator) — the framework then logged
"Shutting down emulator RVSec (emulator-5554) ... has been killed" itself.

## 5b.1 — rv-experiment `--name` implicit resume + forced skip-static (cases 1/4/6)

- Run 1 did Phase 1 (monitors + dexlib2 instrument + GATOR static analysis), booted
  RVSec, ran rep1 (task `92f6aaad`) to COMPLETED, started rep2; SIGINT mid-rep2.
  Persisted: `tasks.json` (rep1 COMPLETED), `cryptoapp.apk/cryptoapp.apk__1__60__ape.logcat`
  + co-located `cryptoapp.apk.json` (70 KB).
- Run 2 (identical command) → implicit resume: logged "Skipping monitor generation /
  APK instrumentation / static analysis", "Resume: skipped 1 already-completed tasks
  (1 remaining)", reused the persisted JSON (no new GATOR). Ran rep2, consolidated both.
- **Result:** the RESUMED rep1 reconstructed coverage from the persisted JSON via
  `dirname(logcat)`: `Reconstructed 10 MOP violations ... (with per-method coverage)`.

| rep | cov_method | cov_class | mop_errors_total | mop_errors_unique |
|-----|-----------|-----------|------------------|-------------------|
| 1 (resumed) | 15.09 | 25.0 | 10 | 5 |
| 2 (fresh)   | 16.04 | 37.5 | 8  | 8 |

Pre-gh65 the resumed rep1 row would be `cov_method=0` (the zeroing bug). Now non-zero.

## 5b.2 — rv-platform standalone auto-resume (cases 1/4)

`rv-platform run --tools ape --apks-dir results/e2e_resume/instrumented_apks
--results-dir results/e2e_resume --repetitions 2 --timeout 60`: auto-detected
`tasks.json`, "Resume: skipped 2 already-completed tasks (0 remaining)", reconstructed
both with per-method coverage, regenerated `summary.csv`. **Byte-identical** to 5b.3.

## 5b.3 — Consolidation-only `--process-results` (case 5 — the path that zeroed T=300)

`rv-platform run --process-results results/e2e_resume`: "Found 2 tasks", both
reconstructed from disk (`from_dict` → `results_dir=""`), both rows non-zeroed.
Required fixing a pre-existing CLI bug in `_process_results_standalone` (passed the
directory to `TaskStorage` instead of `<dir>/tasks.json` and never called `load()`,
so it always found zero tasks). Locked by
`test_process_results_standalone_consolidates_from_disk`.

## 5b.4 — Canary + no-GATOR-on-resume

- **G6 canary: 100% PASS** — 2/2 tasks with `cov_method > 0` in the consolidated
  `summary.csv`; total MOP errors 18.
- **No GATOR re-run** in any resume path: 0 "Soot started" / "Starting static analysis"
  across run 2, `--process-results`, and rv-platform auto-resume logs (skip-static honored).
- Cross-entry-point consistency: 5b.2 and 5b.3 summaries identical.

All G8 cases PASS. The fix is validated on the real stack across both entry points.
