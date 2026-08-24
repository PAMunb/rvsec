# rv-instrumentation-dexlib2 (Python wrapper)

Thin Python wrapper that invokes the DEX-native weaver Java CLI
(`rvsec-instrumentation-dexlib2/cli/target/instr-cli.jar`, built by
the Maven aggregator at `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`).

Exposes the `instrument_apks(apks_dir, results_dir) →
InstrumentationResults` contract of the `Instrumenter` ABC in
`rv-instrumentation-core`, so `rv-experiment` can dispatch to either
variant (`ajc` or `dexlib2`) via a single config flag
(`--instrumentation-variant` / `RV_INSTRUMENTATION_VARIANT`).

Spec-set agnostic — the underlying weaver handles JCA and Generic
specification sets identically.

## Layout

- `src/rv_instrumentation_dexlib2/config.py` — `DexlibInstrumentationConfig`
  Pydantic model (mirrors `RVInstrumentationConfig` shape).
- `src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` —
  `DexlibInstrumentation` class: `prepare_instrumentation`,
  `instrument`, `instrument_apks`. Shells out to the Java CLI via
  subprocess.
- `src/rv_instrumentation_dexlib2/errors.py` — module-specific
  exceptions: `MissingDescriptorError`, `DescriptorParseError`,
  `UnsupportedAspectConstructError`.
- `lib/instr-cli.jar` — fat jar auto-copied by the Maven build
  (design D9). Gitignored.
- `docs/architecture.md` — views, invariants, weaver counters.

## Contract with the Java CLI

The Python wrapper writes its configuration into environment
variables and command-line flags consumed by `instr-cli`. The Java
side emits a JSON summary (`InstrumentationResults`-shaped) carrying
per-APK weaver counters, which the Python wrapper parses into
`InstrumentationResults.weave_counts`. Variant tag is always
`"dexlib2"`.

Every run leaves the same artefacts under `results_dir`, whichever
path produced them (INV-INS-105):

- `instrument_results.json` — merged per-APK results and counters.
- `instrument_results.d/<apk>.json` and `.log` — one per APK when
  `apk_paths` is used (one JVM per APK); `instr-cli.log` for the
  batch path.
- `instrument_errors.json` — per-APK errors, `{}` when clean.

See `docs/architecture.md` for the counter reference.
