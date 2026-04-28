# rv-instrumentation-dexlib2 (Python wrapper)

Thin Python wrapper that invokes the DEX-native weaver Java CLI
(`rvsec-instrumentation-dexlib2/cli/target/instr-cli.jar`, built by
the Maven aggregator at `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`).

Exposes the same `instrument_apks(apks_dir, results_dir) →
InstrumentationResults` contract as the legacy `rv-instrumentation`
module so `rv-experiment` can dispatch to either variant (`ajc` or
`dexlib2`) via a single config flag.

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

## Contract with the Java CLI

The Python wrapper writes its configuration into environment
variables and command-line flags consumed by `instr-cli`. The Java
side emits a JSON summary (`InstrumentationResults`-shaped) that the
Python wrapper parses and returns as-is. Variant tag is always
`"dexlib2"`.
