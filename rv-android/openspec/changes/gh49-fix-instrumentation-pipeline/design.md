## Context

The instrumentation pipeline has a critical error masking bug (GitHub Issue: #49) where `@ErrorHandler.handle_errors(reraise=False)` decorators silently absorb exceptions, reporting 82% false success in batch instrumentation. Additionally, downstream phases (static analysis, execution) lack filtering by prior phase results, wasting compute and polluting experiment data.

This change touches 3 modules (rv-android-core, rv-instrumentation, rv-experiment) with ~36 lines of production code across 3 files. The design is straightforward — no new abstractions, no architectural changes, no new dependencies.

References: FR02, FR15, NFR04, NFR08.

## Architecture

```
ErrorHandler decorator (rv-android-core)
    │ annotates _error_phase on exception when reraise=True
    ▼
rvandroid.py pipeline (rv-instrumentation)
    │ 5 decorators with reraise=True
    │ loop except reads _error_phase via getattr()
    │ instrument_errors.json populated correctly
    ▼
PreProcessor (rv-experiment)
    │ _get_target_apks_for_analysis(): filters SA by instrumented_apks/ presence
    │ get_instrumented_apks(): filters execution by .apk.json presence
    ▼
ExecutionController → rv-platform (unchanged)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ErrorHandler.handle_errors` wrapper | Annotate `_error_phase` before re-raise | Exception + phase string | Annotated exception |
| `RVInstrumentation.instrument_apks` loop | Catch propagated exceptions, record with phase | CommandException/Exception with `_error_phase` | `InstrumentationResults` with accurate errors |
| `PreProcessor._get_target_apks_for_analysis` | Filter original APKs by instrumentation success | `config.get_apk_list()` + `instrumented_apks/` directory | Filtered list of original APK paths |
| `PreProcessor.get_instrumented_apks` | Filter instrumented APKs by SA data presence | `instrumented_apks/*.apk` + `*.apk.json` check | Filtered list of `App` objects |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|------------------------|----------------|------|
| INV-CORE-08: _error_phase annotation | `error_handler.py:455,459` — annotate before raise | `test_error_phase_annotation_reraise` |
| Core: inner phase preserved | `error_handler.py:455` — `not hasattr` guard | `test_nested_decorators_inner_phase_wins` |
| INS: reraise=True on 5 decorators | `rvandroid.py:416,712,747,824,1048` | `test_sign_apk_failure_propagates` |
| INS: phase in InstrumentationError | `rvandroid.py:277,305` — `getattr(ex, '_error_phase')` | `test_error_model_has_correct_phase` |
| INS: batch mixed results | `rvandroid.py:261-318` — existing except blocks | `test_batch_mixed_results_accurate_counts` |
| INV-EXP-15: SA filters by instrumentation | `pre_processor.py:_get_target_apks_for_analysis()` | `test_sa_only_for_instrumented_apks` |
| INV-EXP-16: execution filters by SA | `pre_processor.py:get_instrumented_apks()` | `test_execution_only_with_sa_data` |

## Goals / Non-Goals

**Goals:**
- Exceptions from pipeline phases propagate with accurate phase info to `instrument_errors.json`
- `success_count` reflects only physically instrumented APKs
- Static analysis skips APKs that failed instrumentation
- Execution skips APKs without static analysis data

**Non-Goals:**
- Fixing the root causes of instrumentation failures (AspectJ + protobuf, d8 desugar, etc.) — separate investigation
- Changing `instrument_apks()` loop behavior (must continue after per-APK failures)
- Modifying rv-platform's StaticAnalysisComponent behavior
- Adding retry logic for failed pipeline phases

## Decisions

### D1: Annotate exception object vs. wrap in new exception type

**Choice**: Annotate with `_error_phase` attribute on the existing exception.

**Alternative**: Wrap in `InstrumentationError(phase=..., cause=original)`.

**Rationale**: Wrapping changes the exception type, which would break the loop's `except CommandException` block — it would need to unwrap or catch a different type. Annotation preserves the original type and is invisible to code that doesn't use `getattr`. Minimal invasion, zero risk of breaking existing except handlers.

### D2: Filter by file presence vs. pass results between phases

**Choice**: File presence check (`os.path.exists(apk_json_path)`).

**Alternative**: Pass `InstrumentationResults` from `_instrument_apks()` to `_run_static_analysis()` and store successful APK names.

**Rationale**: File presence is self-describing and works across sessions (resume, `--skip-*` flags, Docker). No new state to pass between methods. The `instrumented_apks/` directory is already the contract between phases — making it the single source of truth simplifies reasoning.

### D3: Always filter by .json presence vs. conditional on SA flag

**Choice**: Always check for `.apk.json` regardless of flags.

**Alternative**: Only filter when `static_analysis=True`.

**Rationale**: If `.json` doesn't exist, coverage is 0% regardless of how we got there. Executing an APK without SA data is always wasteful. The file check is cheap (`os.path.exists`), works correctly in all scenarios, and requires no flag tracking.

## API Design

### `ErrorHandler.handle_errors` wrapper (modified)

```python
# Before each `raise` in the decorator wrapper:
if phase and not hasattr(e, '_error_phase'):
    e._error_phase = phase
raise
```

**Precondition**: `reraise=True` in decorator parameters.
**Postcondition**: Exception has `_error_phase` attribute set to the innermost phase.
**Error behavior**: No new errors — annotation is side-effect-free.

### `PreProcessor._get_target_apks_for_analysis() -> List[str]` (modified)

```python
def _get_target_apks_for_analysis(self) -> List[str]:
    instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
    instrumented_names = {f for f in os.listdir(instrumented_dir)
                         if f.endswith(EXTENSION_APK)} if os.path.exists(instrumented_dir) else set()

    result = []
    for apk_path in self.config.get_apk_list():
        apk_name = os.path.basename(apk_path)
        if apk_name in instrumented_names:
            result.append(apk_path)
        else:
            self.logger.info(f"Skipping static analysis for {apk_name}: not instrumented")
    return result
```

**Precondition**: `instrumented_apks/` directory may or may not exist.
**Postcondition**: Returns only original APK paths for APKs with instrumented versions.

### `PreProcessor.get_instrumented_apks() -> List[App]` (modified)

Filter added after scanning `.apk` files:

```python
# For each .apk in instrumented_dir:
sa_json = app_path + constants.EXTENSION_STATIC_ANALYSIS  # ".json"
if not os.path.exists(sa_json):
    self.logger.warning(f"Excluding {file} from execution: no static analysis data")
    continue
```

**Precondition**: `instrumented_apks/` directory exists with `.apk` files.
**Postcondition**: Returns only `App` objects for APKs with corresponding `.json`.
**Fallback**: If NO APKs pass the filter, falls back to original APKs (existing behavior preserved).

## Data Flow

```
config.get_apk_list()          # ALL original APK paths
        │
        ▼
instrument_apks()              # M2+M3: reraise=True on pipeline methods
        │
        ├── Success: APK written to instrumented_apks/
        └── Failure: entry in InstrumentationResults.errors with _error_phase
                     instrument_errors.json written at end of batch
        │
        ▼
_get_target_apks_for_analysis() # M4: scan instrumented_apks/, return originals
        │
        ▼
StaticAnalyzer.analyze()        # GATOR on original APK
        │
        ├── Success: .apk.json written to instrumented_apks/
        └── Failure: no .json, log warning
        │
        ▼
get_instrumented_apks()         # M5: scan .apk with .json check
        │
        ▼
ExecutionController             # Only APKs with instrumentation + SA
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `CommandException` from jarsigner | `__sign_apk()` | Propagate via `reraise=True` through decorator chain | Batch loop catches, records in `InstrumentationResults.errors`, continues to next APK |
| `CommandException` from d8 | `__create_apk()` (d8 called inside) | Same propagation chain | Same as above |
| `CommandException` from ajc | `__weave_monitors()` | Same propagation chain | Same as above |
| Missing instrumented APK | `_get_target_apks_for_analysis()` | Skip and log info | Continue with other APKs |
| Missing .apk.json | `get_instrumented_apks()` | Skip and log warning | Continue with other APKs; fall back to originals if none pass |

## Risks / Trade-offs

- **[Risk: Existing tests assume reraise=False]** → Run full test suite after change. Tests that mock pipeline methods and expect `None` return on failure will need updating. Mitigation: grep for mocks of the 5 affected methods.
- **[Risk: --skip-static with no pre-existing .json excludes all APKs]** → This is correct behavior (executing without SA data is wasteful), but may surprise users. Mitigation: warning log message explains the exclusion and suggests running with `--static-analysis`.
- **[Trade-off: _error_phase uses private attribute convention]** → The `_` prefix signals this is internal to the error handling system. Alternative (public attribute on CommandException) would require changing the exception class in rv-android-core. The private attribute approach has zero impact on existing code.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | `_error_phase` annotation in decorator | Nested decorated functions, verify `_error_phase` on caught exception | 3 tests |
| Unit | `reraise=True` propagation in rvandroid.py | Mock `__sign_apk` to raise, verify exception reaches loop | 2 tests |
| Unit | `InstrumentationError.phase` accuracy | Simulate failures at different phases, check `.phase` field | 2 tests |
| Unit | `_get_target_apks_for_analysis()` filtering | Create tmp dir with subset of APKs, verify filter | 2 tests |
| Unit | `get_instrumented_apks()` SA filtering | Create tmp dir with .apk and selective .json, verify filter | 3 tests |
| E2E | Full pipeline with mixed APKs | `rv-experiment run` with cryptoapp + known-failing APK | 1 manual test |

**Total**: ~12 unit tests + 1 manual E2E

## Open Questions

None — design is fully resolved from the diagnostic analysis in the plan.
