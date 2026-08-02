# Delta Specification: Analysis — Coverage Tracker Final Drain

## Purpose

`CoverageTracker` (`modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py`) is the live half of RV-Android's coverage measurement. While a testing tool exercises the app, the tracker runs a background daemon thread that tails the logcat file the platform is capturing, parses each line for the `RVSEC-COV` (method call) and `RVSEC` (violation) tags, and registers what it finds in a `LogcatRepository`. When the task ends, `CoverageComponent.process_results()` calls `repository.calculate_metrics()` and writes the result into `task.result.coverage_metrics`.

The critical detail is that `process_results()` reads the **in-memory repository**, not the file (`components/coverage.py:280-283`). Whatever the tracker thread failed to read is simply absent from the metrics — there is no second pass over the file on the live path.

The tracker's thread does not perform that second pass either. Its structure is:

```
open(self.logcat_file)            # tracker.py:293 — by path, its own handle
drain existing lines              # tracker.py:297-298
seek(0, SEEK_END)                 # tracker.py:301
while not self._stop_event.is_set():     # tracker.py:304
    readlines(); process; sleep(0.5 or 1.0)
finally:                          # tracker.py:330-342
    is_running = False; flush_diagnostics(); close()
```

`stop()` sets `_stop_event` and joins with a five-second timeout. The thread wakes from its sleep, re-evaluates the `while` condition, and exits — **without a final `readlines()`**. The `finally` flushes buffered diagnostic events and closes the handle, but never reads. Every line appended to the file after the thread's last read is therefore lost to the live repository, permanently.

This is not merely an accuracy nuisance; it puts two documented paths out of agreement. On resume, a `COMPLETED` task is reloaded from `tasks.json` with `repository=None`, and `ResultProcessorComponent._reconstruct_repository_from_logcat()` re-parses the **entire** logcat file to rebuild it. The reconstruction therefore sees lines the live tracker never did. **INV-PLT-18** requires the two to agree within a rounding tolerance of 0.01 for every coverage and error field — so the missing drain is a latent violation of that invariant, present by construction rather than by accident.

The size of the gap is **not measured**. It is bounded by the tail loop's sleep interval (0.5 s when lines are flowing, 1.0 s when idle) plus however long `process_results()` takes before logcat is stopped. It is recorded here as an unmeasured quantity, not as a claim about magnitude.

Closing the gap requires two things that only work together. The drain itself belongs here: `stop()` must consume the remainder of the file before the handle closes. But a drain is only deterministic if the file has stopped growing — otherwise it reads "whatever happened to be there", and lines written afterwards are lost exactly as before. That is why the platform delta inverts the finalization order to stop the `adb logcat` producer before stopping this consumer. The two are decoupled by the filesystem — the tracker holds its own handle obtained by path, so killing the producer cannot EOF it or raise in it — which is precisely what makes stopping the producer first safe.

## Data Contracts

### Input

- `logcat_file: str` — path to the file written by `LogcatManager`; opened by the tracker with its own handle, independent of the producer's.
- `_stop_event: threading.Event` — set by `stop()` to signal thread termination.

### Output

- `repository: LogcatRepository` — populated in place; the sole source for `CoverageComponent.process_results()`.

### Side-Effects

- **[File System]**: read-only tailing of the logcat file; the handle is closed in the thread's `finally`.
- **[Thread]**: the daemon thread terminates after the drain completes, within the five-second join budget.

### Error

- Read errors during the final drain MUST be caught and logged; they MUST NOT propagate out of `stop()`, which is invoked from a `finally` on the platform side where a raised exception would replace the exception being propagated.

## Invariants

- **INV-ANA-53**: `CoverageTracker.stop()` MUST NOT allow the tracking thread to close its file handle without first reading the remainder of the file from the current position to end-of-file and processing those lines into the repository. After `stop()` returns, the repository MUST reflect every line present in the logcat file at the moment the file stopped being written. The drain MUST run under `_reader_lock`, consistently with INV-ANA-05, and MUST complete within the existing five-second join budget; if it does not, the thread MUST still terminate and the truncation MUST be logged as a warning rather than silently accepted.

- **INV-ANA-54**: The drain MUST be bounded and MUST NOT reprocess already-consumed lines. It reads forward from the handle's current position only, so a line registered during the tail loop MUST NOT be registered a second time by the drain — coverage counts unique method signatures, and duplicate registration of a violation would inflate `total_errors`.

- **INV-ANA-55**: `stop()` MUST remain safe to call when the tracker is already stopped. The existing `if not self.is_running: return` guard MUST be preserved, because the platform now reaches finalization from a single owner while `_cleanup_components()` still invokes `cleanup()` afterwards (platform INV-PLT-30), so a second call is expected on every task.

## ADDED Requirements

### Requirement: Coverage Tracker Final Drain (FR12, NFR06)

`CoverageTracker.stop()` MUST guarantee that the tracking thread consumes the remainder of the logcat file before terminating. Terminating on the stop signal alone leaves any lines written since the thread's last read permanently absent from the repository, and the repository is the only input `CoverageComponent.process_results()` has.

The drain MUST read forward from the handle's current position to end-of-file and process those lines through the same path the tail loop uses, so parsing, timing arithmetic, and diagnostic-event handling are identical. It MUST run before the existing `flush_diagnostics()` call, so that any diagnostic event completed by the drained lines is emitted rather than discarded.

The drain MUST be resilient. A read error MUST be caught and logged as a warning; `stop()` MUST NOT raise, because the platform now invokes it from a `finally` where a raised exception would replace the exception being propagated.

This requirement is only fully effective when the logcat producer has already been stopped, which the platform guarantees by finalizing logcat before coverage (platform INV-PLT-31). Without that ordering the drain still reads whatever is present at the moment it runs, but the file may continue to grow afterwards.

#### Scenario: Lines written after the last tail iteration are recovered

- **WHEN** the tail loop completes an iteration, three `RVSEC-COV` lines are appended to the file, and `stop()` is then called
- **THEN** all three lines MUST be present in the repository after `stop()` returns
- **AND** `repository.calculate_metrics()` MUST count the methods they name

#### Scenario: Live metrics match re-parsing the same file

- **WHEN** the `adb logcat` producer is stopped, then `stop()` is called on the tracker, for a task that ends `COMPLETED`
- **THEN** `repository.calculate_metrics().to_dict()` MUST equal the metrics obtained by parsing the same logcat file from the beginning with `parse_logcat_file`, for every coverage and error field, within a tolerance of `0.01`
- **AND** this MUST hold for the round trip required by platform INV-PLT-18

#### Scenario: Drain does not double-count

- **WHEN** a violation line was already processed by the tail loop before `stop()` was called
- **THEN** the drain MUST NOT register it again
- **AND** `total_errors` MUST be identical to its value immediately before `stop()` was called, plus only the errors found in genuinely unread lines

#### Scenario: Drain completes before diagnostics are flushed

- **WHEN** the unread tail contains the final line of a diagnostic event whose earlier lines were already buffered
- **THEN** the drain MUST process that line before `flush_diagnostics()` runs
- **AND** the completed diagnostic event MUST be emitted

#### Scenario: Read failure during drain does not propagate

- **WHEN** reading the remainder of the file raises `OSError`
- **THEN** `stop()` MUST NOT raise
- **AND** the condition MUST be logged as a warning naming the logcat file
- **AND** the thread MUST still terminate and the handle MUST still be closed

#### Scenario: Stopping an already-stopped tracker remains inert

- **WHEN** `stop()` is called on a tracker whose `is_running` is already `False`
- **THEN** it MUST return immediately without attempting a drain
- **AND** the repository MUST be unchanged
