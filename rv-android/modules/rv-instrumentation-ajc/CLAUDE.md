# CLAUDE.md - rv-instrumentation-ajc

AspectJ-based APK instrumentation variant (dex2jar→ajc→d8 pipeline). One
of two interchangeable variants — the other is `rv-instrumentation-dexlib2`.
`AjcInstrumentation` implements the `Instrumenter` ABC defined in
`rv-instrumentation-core` (which also owns the shared `InstrumentationResults` /
`InstrumentationError` types); the parent `rv-instrumentation` re-exports the
public API and dispatches via `get_instrumenter("ajc", config)`.

**Package**: `rv_instrumentation_ajc` · **Engine**: `AjcInstrumentation`
(`src/rv_instrumentation_ajc/ajc_instrumentation.py`) · **Config**:
`AjcInstrumentationConfig` (`src/rv_instrumentation_ajc/config.py`) · **CLI**:
`src/rv_instrumentation_ajc/__main__.py`

## Entry Points

```bash
# From project root; subcommands: instrument (--apk) | batch (--apks-dir)
uv run rv-instrumentation-ajc instrument --apk /data/apks/cryptoapp.apk --output /tmp/instrumented
uv run rv-instrumentation-ajc batch --apks-dir /data/apks --output /tmp/instrumented --summary
# other flags: --rvsec-root --monitor-dir --android-jar --android-platforms-dir --keystore
#              --keystore-password --working-dir --tmp-dir --dex2jar-home --no-quarantine
#              --force --verbose --dry-run
```

```python
from rv_instrumentation_ajc import AjcInstrumentation, AjcInstrumentationConfig
results = AjcInstrumentation(config).instrument_apks(apks_dir, results_dir, apk_paths=apk_list)
```

In production rv-experiment builds the config (`get_rv_instrumentation_config`,
with `instrumented_dir=<output_dir>/instrumented_apks`, `enable_quarantine`,
`package_detector`) and calls through the parent factory with `apk_paths`.

## Instrumentation Pipeline

```
Original APK
    |
    v
[1.  Decompilation] ---------> DEX to JAR (dex2jar), extracted as loose .class files
    |
    v
[1b. Strip desugared shims] -> Delete pre-desugared j$.* classes (d8 refuses to merge them)
    |
    v
[1c. Quarantine classes] ---> Move VerifyError-prone library classes to a side dir
    |                          (gh50 §16/§19/§22; skipped if --no-quarantine)
    v
[2.  Monitor Integration] ---> Copy AspectJ + Java monitors from rv-monitor-generator
    |
    v
[2b. Pre-ajc frame compute] -> Run rv-frame-computer to fix stack maps before weaving
    |
    v
[3.  AspectJ Weaving] -------> ajc -proceedOnError over the class tree
    |
    v
[4.  Recompute frames] ------> Re-run rv-frame-computer post-weaving
    |
    v
[4b. Restore quarantined] ---> Re-include the side-dir contents (pairs with 1c)
    |
    v
[5.  Dependency Integration] -> Merge rv-monitor-rt, rvsec-core, rvsec-logger-logcat, aspectjrt classes
    |
    v
[6.  Recompilation] ---------> JAR to DEX (d8 --release --min-api 26), zip -u into a copy of the APK
    |
    v
[6b. Align] -----------------> zipalign -f -P 16 4 (before signing)
    |
    v
[7.  APK Signing] -----------> apksigner sign (keystore) + apksigner verify
    |
    v
Instrumented APK  (<config.instrumented_dir>/<apk name>)
```

`d8 --lib` gets the `android.jar` of the APK's `targetSdkVersion` when that
platform is installed, else the highest `android-*` under
`android_platforms_dir`; `config.android_jar_path` (default `android-29`) is
the last resort.

### Quarantine (gh50, stages 1c + 4b)

Library classes the AspectJ weaver or `d8` reject (e.g. heavily-desugared
Compose/Kotlin coroutine classes producing `VerifyError`) are moved to a side
directory (`<tmp_dir>_quarantine/`) before weaving and restored afterwards.
Enabled by default; driven by `assets/weaving_excludes.yaml` glob patterns and
implemented by `__quarantine_problematic_classes()` / `__restore_quarantined_classes()` in
`ajc_instrumentation.py`. `--no-quarantine` bypasses both, weaving those classes
inline — empirical use only, to compare recovery rate vs MOP visibility loss.
dexlib2 has no quarantine equivalent.

#### The anti-quarantine guard, and why this module holds a different scope key

Quarantine protects app code from its own glob patterns with a guard keyed on
`app.code_package` (`ajc_instrumentation.py:854-904`): a file whose path starts
with the key's directory form is never quarantined, however broadly a pattern
matches. On an APK built with `assembleDebug` that guard is **inert**, and
silently so — the declared applicationId is `com.example.app.debug` while
the classes compile under `com/example/app/`, so the prefix
`com/example/app/debug/` matches no file and the skip branch is never
taken. The code logs a warning naming the condition ("App-code quarantine
guard is inert"); it does not repair it by electing a different key, which
would put a second, invisible package policy in the pipeline.

That is why **`strip_build_type_suffix` is deliberately not propagated here**
(INV-EXP-36). Neutralizing the key would make the guard live in exactly the apps
where it is inert today, which changes what gets woven — a change on the
instrumentation path, decided on instrumentation evidence, not a side effect of
a repair to the analysis denominator. The pipeline therefore holds two answers
for `code_package`, by consumer: the analysis path may neutralize, this module
receives the declared id. `instrument_apks()` constructs its `App`s at `:193`
and `:198` with `package_detector` alone, and that arity is the exclusion.

The exclusion is **asymmetric, and the asymmetry is not covered by the reason
above**: this module is excluded from the suffix policy but not from
`package_detector`, which it does forward (`:193`, `:198`). A run with
rv-experiment's `--package-detector` already elects a code package here, so the
guard activation cited as the reason for the exclusion already happens today
under that flag. Recorded, not repaired — repairing the ajc instrumenter is out
of scope by researcher decision.

## Configuration

`AjcInstrumentationConfig` (`config.py`) resolves paths by priority:

1. Individual explicit paths (highest; all of `monitor_output_dir`,
   `android_jar_path`, `keystore_file`, `instrumented_dir`, `dex2jar_home` set)
2. Explicit `rvsec_root` parameter (`working_dir` = `<rvsec_root>/rv-android`)
3. `RVSEC_HOME` environment variable (same layout)
4. Current working directory

Defaults below `working_dir`: `mop_out/` (monitors), `out/` (instrumented),
`tmp/`, `lib_tmp/`, `rvm_tmp/`, `lib/dex2jar/`. `android_platforms_dir`
defaults to `$ANDROID_HOME/platforms` (`ConfigurationError` when `ANDROID_HOME`
is unset and SDK paths are not explicit). `keystore_file` defaults to the
keystore bundled in the parent `rv-instrumentation/assets/` (INV-INS-39),
`keystore_password` to `password`, `keystore_alias` to `server`. Construction
validates eagerly: the directories exist, `android.jar` and the keystore are
files, and `monitor_output_dir` holds at least one `*.aj` and one `*.java`.

`prepare_instrumentation` needs `config.rvsec_root` or `RVSEC_HOME` to resolve
the runtime jars (`_resolve_runtime_libs` from `-core`, into `lib_tmp_dir`).
This module reads no other environment variable; `package_detector` and
`enable_quarantine` arrive by value from the caller (INV-EXP-34).

## Dependencies

**Module**: `rv-android-core` (`App`, `Command`, `ErrorHandler`, `LoggingManager`,
utils), `rv-instrumentation-core` (ABC + shared types), `pyyaml` (quarantine
patterns).

### External tools

| Tool | Purpose | Resolution |
|------|---------|------------|
| dex2jar (`d2j-dex2jar.sh`, `d2j-asm-verify.sh`) | DEX → JAR | `dex2jar_home` |
| ajc (AspectJ) | Monitor weaving | `PATH` |
| `java` + `rv-frame-computer.jar` | Stack-map recompute | `rv-android/lib/frame-computer/` (built by the rvsec Maven reactor); **missing jar → warning and both frame passes skipped** |
| d8, zipalign, apksigner | DEX, alignment, signing | `PATH` (Android build-tools) |
| zip | Replace DEX entries in the APK copy | `PATH` |
| mvn | Runtime-jar resolution | `PATH` |

### Required libraries (resolved via Maven)

`rv-monitor-rt.jar`, `rvsec-core.jar`, `rvsec-logger-logcat.jar`, `aspectjrt.jar`.

## Error Handling

`InstrumentationError` (defined in `-core`) carries the failing pipeline phase,
taken from the innermost `@ErrorHandler.handle_errors(phase=...)` the exception
crossed (e.g. `aspect_weaving`, `apk_signing`, `zipalign`; a dex2jar failure
reports `single_apk_instrumentation` because decompilation has no phase of its
own). When any APK fails, `instrument_errors.json` is written under
`results_dir` (nothing is written on a clean batch):

```json
{
  "app_name.apk": {
    "code": 1,
    "tool": "ajc",
    "message": "<stderr of the failing tool>",
    "phase": "aspect_weaving"
  }
}
```

`utils.execute_command` treats any stderr output as failure unless called with
`skip_stderr=True`; ajc, d8, the frame computer and apksigner use it (they
print warnings on success), dex2jar's `asm-verify`, `zip` and `zipalign` do not.

## Gotchas

- **The unchanged-APK check does not fail the APK.** `check_if_instrumented`
  compares the SHA-256 of the original and of `config.instrumented_dir/<apk>`
  and raises `CommandException` when they match, but its
  `@ErrorHandler.handle_errors` decorator has no `reraise=True`, so the
  exception is logged and swallowed and the APK is counted in `success_count`.
  The same holds for `prepare_instrumentation`: a missing `RVSEC_HOME` or a
  Maven failure is logged, `instrument_apks` continues without runtime jars,
  and its `setup_error` branch is never reached.
- **Existing outputs are skipped.** `instrument()` returns early when
  `<results_dir>/<apk>` already exists unless `force_instrumentation=True`
  (CLI `--force`); the skipped APK still counts as a success.
- **Keep `results_dir` and `config.instrumented_dir` equal.** The signed APK and
  the hash check use `config.instrumented_dir`; `results_dir` is used for the
  skip check and `instrument_errors.json`. The CLI and rv-experiment set both
  to the same directory.
- No weaver counters: `weave_counts` stays empty and `variant` is `"ajc"` by the
  `-core` validator default. Coverage comes from `Coverage.aj`, not dexlib2's
  `CoverageWeaver`.

## Tests

```bash
uv run pytest modules/rv-instrumentation-ajc/tests/ \
    --import-mode=importlib -o "addopts=" -v
```

`tests/`: `test_ajc_instrumentation.py`, `test_cli.py`, `test_config.py`,
`conftest.py` (shared fixtures). All external tools are mocked.
