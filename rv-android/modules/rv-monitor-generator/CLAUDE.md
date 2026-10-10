# CLAUDE.md - rv-monitor-generator

Guidance for Claude Code working in the rv-monitor-generator module. See `rv-android/CLAUDE.md` for workspace-wide setup (uv sync, pytest, env vars, spec sets).

## Purpose
Drives JavaMOP + RV-Monitor to turn MOP specs (`.mop`) into monitoring artifacts (AspectJ aspects + Java monitor classes, plus a JSON descriptor) that rv-instrumentation weaves into APKs. Pre-processing step 1 of `rv-experiment`; also usable standalone through the `rv-monitor-generator` CLI.

| Component | File | Responsibility |
|---|---|---|
| `RuntimeVerificationGenerator` | `src/rv_monitor_generator/runtime_verification_generator.py` | Orchestrates the JavaMOP → RV-Monitor pipeline; `generate_monitors(output_dir) -> bool`, `get_generation_summary(output_dir)`. |
| `RVGeneratorConfig` | `src/rv_monitor_generator/config.py` | Pydantic config; path resolution and eager validation in `model_post_init`. |
| `ConfigurationError` | `src/rv_monitor_generator/config.py` | Raised on config resolution/validation failure (subclass of `RVAndroidError`). |
| CLI | `src/rv_monitor_generator/__main__.py` | argparse, one subcommand: `generate`. |

## Monitor Generation Pipeline
`generate_monitors(output_dir)`:
1. `validate_output_directory()` (create + write probe), then `utils.reset_folder(output_dir)`.
2. `_execute_javamop`: `javamop -d <output_dir> -merge [--emit-descriptor] <mop_specs_dir>/*.mop` emits the merged `.aj` (+ `.json` descriptor) and one `.rvm` per spec.
   - **Workaround:** JavaMOP's `-d` does not move `.rvm` files to the output dir (it writes each beside its `.mop`), so the generator moves them manually (`utils.move_files_by_extension(EXTENSION_RVM, mop_specs_dir, output_dir)`). Without the move RV-Monitor finds no input.
   - Still inside this stage, every `.aj` in `aspects_dir` is copied into `output_dir`.
3. `_execute_rvmonitor`: `rv-monitor -d <output_dir> -merge <output_dir>/*.rvm` → `.java` monitor class; then the `.rvm` files are deleted.
4. Returns `True`, or `False` when any step raised (the exception goes to `ErrorHandler.handle_error` with a context dict).

"Success" means both commands exited 0 **and wrote nothing to stderr** (`rv_android_core.util.utils.execute_command` raises `CommandException` on either). The method does not check that a `.aj` or `.java` was produced — callers that need certainty inspect the directory.

On `False`, `rv-experiment`'s `PreProcessor._generate_monitors` logs `"Monitor generation failed"`, writes no `specification_set.txt` provenance marker, and pre-processing continues.

### emit_descriptor seam
`RVGeneratorConfig.emit_descriptor` (default `True`) appends the patched-JavaMOP flag `--emit-descriptor`, writing a `MultiSpec_*MonitorAspect.json` descriptor alongside each aspect. This descriptor is consumed by the **dexlib2 instrumentation variant**. `get_generation_summary()` reports its count under `descriptors` (0 when the flag is off). The CLI has no flag for it: standalone runs always emit the descriptor.

## Configuration Priority
1. Individual tool paths (highest): when `javamop_bin`, `rvmonitor_bin` and `mop_specs_dir` are all given, they are used as-is; `aspects_dir` defaults to `<parent of mop_specs_dir>/aspect`.
2. Explicit `rvsec_root` (standard layout discovery; fills only the fields left `None`).
3. `RVSEC_HOME` env var (`constants.ENV_RVSEC_HOME`).
4. Otherwise → `ConfigurationError`.

Standard layout under the RVSEC root (`_resolve_from_rvsec_root`):
- `javamop/bin/javamop` and `rv-monitor/bin/rv-monitor` — module-root wrapper scripts that run the release launchers under `target/release/`, so the rvsec reactor must have been built (`mvn install`) for them to work.
- `rvsec/rvsec-mop/src/main/resources/jca/` — the default `mop_specs_dir` when none is given.
- `rvsec/rvsec-mop/src/main/resources/aspect/` — the default `aspects_dir`.

Choosing a specification set (`jca`, `jca_android`, `generic`, `custom`) is **not** this module's job: `rv-experiment`'s `ExperimentConfig.get_monitored_operations_config()` resolves the set to a directory (`resolve_spec_set_dir`) and passes all four paths explicitly. Other directories under `resources/` (e.g. `generic_new`, `jca_android_bug_predicate`) are reachable only as an explicit `mop_specs_dir`.

Validation (`_validate_configuration`, at construction): binaries exist and are executable; `mop_specs_dir`/`aspects_dir` exist and are readable; `mop_specs_dir` holds at least one `.mop`; each tool answers `-h` within 10 s.

## Generated Artifacts
| Artifact | Purpose |
|---|---|
| `MultiSpec_1MonitorAspect.aj` | Merged pointcuts + advice; woven by the ajc variant. |
| `MultiSpec_1RuntimeMonitor.java` | Merged monitor class (package `mop`); compiled into instrumented APKs. |
| `MultiSpec_1MonitorAspect.json` | Descriptor consumed by the dexlib2 instrumentation variant (see emit_descriptor seam). |
| `Coverage.aj` | The only custom aspect in `aspects_dir`; copied verbatim; used by the ajc variant only. |

The `MultiSpec_<n>` name is assigned by JavaMOP's `-merge` only when there is more than one `.mop`; a set with a single `Foo.mop` produces `FooMonitorAspect.aj`/`.json`, which the dexlib2 variant's default `MultiSpec_*MonitorAspect.json` glob does not match.

## Entry Points
```bash
# From rv-android root; uses RVSEC_HOME for the tools and the aspect dir
uv run rv-monitor-generator generate \
  --specs-dir "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android" \
  --output out/monitors
```
Flags: `--rvsec-root`, `--javamop-bin`, `--rvmonitor-bin`, `--specs-dir`, `--aspects-dir`, `--output` (required), `--verbose/-v`, `--summary`. Exit 0 on success, 1 on failure.

```python
from rv_monitor_generator import RuntimeVerificationGenerator, RVGeneratorConfig
config = RVGeneratorConfig(mop_specs_dir=specs_dir)  # tools + aspects from RVSEC_HOME
ok = RuntimeVerificationGenerator(config).generate_monitors(output_dir)
```

## Known Issues
- **JavaMOP `-d` bug:** does not relocate `.rvm` files — handled by the move workaround above. The move takes *every* `.rvm` in `mop_specs_dir`, and needs that directory writable by JavaMOP although validation only checks readability.
- **Tool help exit codes:** JavaMOP/RV-Monitor may return non-zero on `-h`; config validation checks for any stdout/stderr output rather than the exit code. That also accepts the shell's error when a wrapper's release launcher has not been built, and the 10 s timeout can be missed by a cold JVM on a loaded machine (`ConfigurationError`).
- **`--summary` is broken:** `handle_generate_command` indexes `summary['aspectj_files']['count']`, but `get_generation_summary()` returns plain integers, so the CLI prints "Unexpected Error" and exits 1 after a successful generation. `tests/test_main_cli.py` mocks the summary with the nested shape and does not catch it.

## Dependencies
- `rv-android-core` (`Command`, `utils.execute_command` and the file helpers, `ErrorHandler`, `LoggingManager`, `BaseValidatedModel`, `constants`), `pydantic`.
- External: JavaMOP and RV-Monitor from the rvsec reactor (`$RVSEC_HOME/javamop`, `$RVSEC_HOME/rv-monitor`).
- Depended on by: `rv-experiment` (`config.py` builds `RVGeneratorConfig`; `PreProcessor` runs the generator).

## Tests
```bash
# From rv-android root
uv run pytest modules/rv-monitor-generator/tests/ --import-mode=importlib -o "addopts=" -v
```
`tests/` holds `test_config_and_cli.py`, `test_main_cli.py`, `test_emit_descriptor.py`, `test_runtime_verification_generator.py`, `test_runtime_verification_generator_complete.py`. `TestRuntimeVerificationGeneratorIntegration` (in `test_runtime_verification_generator.py`) needs a real RVSEC install and skips if absent; its `-h` probe test is marked `@pytest.mark.slow`, which CI deselects.
