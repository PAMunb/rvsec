# CLAUDE.md - rv-monitor-generator

Guidance for Claude Code working in the rv-monitor-generator module. See `rv-android/CLAUDE.md` for workspace-wide setup (uv sync, pytest, env vars, spec sets).

## Purpose
Drives JavaMOP + RV-Monitor to turn MOP specs (`.mop`) into monitoring artifacts (AspectJ aspects + Java monitor classes) that rv-instrumentation weaves into APKs.

| Component | Responsibility |
|---|---|
| `RuntimeVerificationGenerator` | Orchestrates the JavaMOP → RV-Monitor pipeline. |
| `RVGeneratorConfig` | Pydantic config with priority-based path resolution. |
| `ConfigurationError` | Raised on config validation failure. |

## Monitor Generation Pipeline
1. Validate config (tool binaries, dirs, MOP files present).
2. Prepare/reset output dir.
3. Execute JavaMOP (`-merge`): emits `.aj` + `.rvm`; when `emit_descriptor` is on, also emits `MultiSpec_*MonitorAspect.json`.
   - **Workaround:** JavaMOP's `-d` does not move `.rvm` files to the output dir, so the generator moves them manually (`utils.move_files_by_extension(EXTENSION_RVM, mop_specs_dir, output_dir)`).
4. Copy custom `.aj` aspects from `aspects_dir`.
5. Execute RV-Monitor (`-merge`): `.rvm` → `.java` monitor classes; clean up `.rvm`.
6. Return success/failure.

### emit_descriptor seam
`RVGeneratorConfig.emit_descriptor` (default on) appends the patched-JavaMOP flag `--emit-descriptor`, writing a `MultiSpec_*MonitorAspect.json` descriptor alongside each aspect. This descriptor is consumed by the **dexlib2 instrumentation variant**. `get_generation_summary()` reports its count under `descriptors` (0 when the flag is off).

## Configuration Priority
1. Individual tool paths (highest): `javamop_bin`, `rvmonitor_bin`, `mop_specs_dir`, `aspects_dir`.
2. Explicit `rvsec_root` (standard layout discovery).
3. `RVSEC_HOME` env var.
4. Otherwise → `ConfigurationError`.

Standard layout tool paths under `$RVSEC_HOME`:
- `javamop/bin/javamop`
- `rv-monitor/bin/rv-monitor`
- `rvsec/rvsec-mop/src/main/resources/{jca,generic,aspect}/`

## Generated Artifacts
| Artifact | Purpose |
|---|---|
| `MultiSpec_*.aj`, `*MonitorAspect.aj` | Pointcuts + advice; consumed by rv-instrumentation. |
| `*.java` | Monitor classes implementing verification logic; compiled into instrumented APKs. |
| `MultiSpec_*MonitorAspect.json` | Descriptor consumed by the dexlib2 instrumentation variant (see emit_descriptor seam). |
| `logging.aj`, `coverage.aj` | Custom aspects copied from `aspects_dir`. |

## Known Issues
- **JavaMOP `-d` bug:** does not relocate `.rvm` files — handled by the step-3 move workaround above.
- **Tool help exit codes:** JavaMOP/RV-Monitor may return non-zero on `-h`; config validation checks for any stdout/stderr output rather than the exit code.

## Dependencies
- `rv-android-core` (ErrorHandler, LoggingManager, Command utilities), `pydantic`.
- External: JavaMOP, RV-Monitor, AspectJ.

## Tests
`tests/` holds `test_config_and_cli.py`, `test_main_cli.py`, `test_emit_descriptor.py`, `test_runtime_verification_generator.py`, `test_runtime_verification_generator_complete.py`. Integration tests marked `@pytest.mark.slow` need a real RVSEC install and skip if absent.
