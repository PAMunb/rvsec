# CLAUDE.md - rv-instrumentation-ajc

AspectJ-based APK instrumentation variant (legacy dex2jar→ajc→d8 pipeline). One
of two interchangeable variants — the other is `rv-instrumentation-dexlib2`.
`AjcInstrumentation` implements the `Instrumenter` ABC defined in
`rv-instrumentation-core` (which also owns the shared `InstrumentationResults` /
`InstrumentationError` types); the parent `rv-instrumentation` re-exports the
public API and dispatches via `get_instrumenter("ajc", config)`.

**Package**: `rv_instrumentation_ajc` · **Engine**: `AjcInstrumentation`

## Instrumentation Pipeline

```
Original APK
    |
    v
[1.  Decompilation] ---------> DEX to JAR (dex2jar)
    |
    v
[1b. Strip desugared shims] -> Remove R8 desugar synthetic classes that break weaving
    |
    v
[1c. Quarantine classes] ---> Move VerifyError-prone library classes to side-jar
    |                          (gh50 §16/§19/§22; skipped if --no-quarantine)
    v
[2.  Monitor Integration] ---> Inject AspectJ + Java monitors from rv-monitor-generator
    |
    v
[2b. Pre-ajc frame compute] -> Run rv-frame-computer to fix stack maps before weaving
    |
    v
[3.  AspectJ Weaving] -------> Integrate monitoring pointcuts with application bytecode
    |
    v
[4.  Recompute frames] ------> Re-run rv-frame-computer post-weaving
    |
    v
[4b. Restore quarantined] ---> Re-include the side-jar contents (gh50; pairs with 1c)
    |
    v
[5.  Dependency Integration] -> Merge rv-monitor-rt, aspectjrt, rvsec-core libraries
    |
    v
[6.  Recompilation] ---------> JAR to DEX (Android d8 compiler)
    |
    v
[7.  APK Signing] -----------> Sign for deployment (jarsigner / apksigner + keystore)
    |
    v
Instrumented APK
```

### Quarantine (gh50, stages 1c + 4b)

Library classes the AspectJ weaver or `d8` reject (e.g. heavily-desugared
Compose/Kotlin coroutine classes producing `VerifyError`) are moved to a side-jar
before weaving and restored afterwards. Enabled by default; driven by
`assets/weaving_excludes.yaml` glob patterns and implemented by
`__quarantine_problematic_classes()` / `__restore_quarantined_classes()` in
`ajc_instrumentation.py`. `--no-quarantine` bypasses both, weaving those classes
inline — empirical use only, to compare recovery rate vs MOP visibility loss.
dexlib2 has no quarantine equivalent.

#### The anti-quarantine guard, and why this module holds a different scope key

Quarantine protects app code from its own glob patterns with a guard keyed on
`app.code_package` (`ajc_instrumentation.py:854-885`): a file whose path starts
with the key's directory form is never quarantined, however broadly a pattern
matches. On a corpus built with `assembleDebug` that guard is **inert**, and
silently so — the declared applicationId is `org.fossify.calendar.debug` while
the classes compile under `org/fossify/calendar/`, so the prefix
`org/fossify/calendar/debug/` matches no file and the skip branch is never
taken. The code says so out loud since gh111 and logs a warning naming the
condition; it does not repair it by electing a different key, which would put a
second, invisible package policy in the pipeline.

That is why **`strip_build_type_suffix` is deliberately not propagated here**
(INV-EXP-36). Neutralizing the key would make the guard live in exactly the apps
where it is inert today, which changes what gets woven — a change on the
instrumentation path, decided on instrumentation evidence, not a side effect of
a repair to the analysis denominator. The pipeline therefore holds two answers
for `code_package`, by consumer: the analysis path may neutralize, this module
receives the declared id. `instrument_apks()` constructs its `App`s at `:193`
and `:199` with `package_detector` alone, and that arity is the exclusion.

The exclusion is **asymmetric, and the asymmetry is not covered by the reason
above**: this module is excluded from the suffix policy but not from
`package_detector`, which it does forward (`:193`, `:199`). A run with
`--package-detector` already elects a code package here, so the guard activation
cited as the reason for the exclusion already happens today under that flag.
Recorded, not repaired — repairing the ajc instrumenter is out of scope by
researcher decision.

## Configuration

`AjcInstrumentationConfig` (`config.py`) resolves paths by priority:

1. Individual explicit paths (highest)
2. Explicit `rvsec_root` parameter
3. `RVSEC_HOME` environment variable
4. Working-directory defaults

**Required fields**: `monitor_output_dir` (generated `*.aj`/`*.java`),
`android_jar_path`, `android_platforms_dir`, `dex2jar_home`, `keystore_file`
(defaults to the keystore bundled in the parent `rv-instrumentation/assets/`,
shared with dexlib2 — INV-INS-39). Default target platform is `android-29`.

## Dependencies

**Module**: `rv-android-core` (app model, ErrorHandler, LoggingManager, utils),
`rv-instrumentation-core` (ABC + shared types), `pydantic`.

### External tools

| Tool | Purpose | Configuration |
|------|---------|---------------|
| dex2jar | DEX → JAR | `dex2jar_home` |
| ajc (AspectJ) | Monitor weaving | System PATH |
| d8 | JAR → DEX | Android SDK (`ANDROID_HOME`) |
| jarsigner | APK signing | Java (`JAVA_HOME`) |
| Maven | Dependency resolution | System PATH |
| zip | APK manipulation | System PATH |

### Required libraries (resolved via Maven)

`rv-monitor-rt.jar`, `rvsec-core.jar`, `rvsec-logger-logcat.jar`, `aspectjrt.jar`.

## Verification

After instrumentation the module confirms the APK actually changed by comparing
file hashes against the original; matching hashes are treated as a failed
instrumentation.

## Error Handling

`InstrumentationError` (defined in `-core`) carries the failing pipeline phase.
Failed batch runs are written to `instrument_errors.json`:

```json
{
  "app_name.apk": {
    "code": -1,
    "tool": "dex2jar",
    "message": "Tool execution failed",
    "phase": "decompilation"
  }
}
```

## Tests

```bash
uv run pytest modules/rv-instrumentation-ajc/tests/ -v
```

`tests/`: `test_ajc_instrumentation.py`, `test_cli.py`, `test_config.py`,
`conftest.py` (shared fixtures).
