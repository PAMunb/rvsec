# Proposal: gh98-manifest-package-default

GitHub Issue: #98

## Why

`App.code_package` runs `PackageDetector` unconditionally (`domain/app.py:119-132`), so rv-android has no way to answer with the package the APK itself declares. Which package keys the class filter of a static analysis is a property of the study being run, not of the tool, and rv-android runs many studies — that decision belongs to the user, explicitly, on every dataset.

The cost of it being implicit is on record. The 30-APK re-analysis of #91 needed a key that was neither the detector's election nor the raw applicationId, and no interface offered one: the change had to bypass `rv-static-analysis analyze` and drive GATOR from a dedicated script, *"because its only source for that parameter is `App.code_package`, the property backed by `PackageDetector`"*.

## What Changes

- **BREAKING** — `App.code_package` returns `App.package_name` (the applicationId declared in the manifest, verbatim) by default. `PackageDetector` runs only when the user enables it. Every consumer of the property changes result on any APK where the two values differ.
- No rule is applied on top of the manifest value. Suffix stripping, prefix repair and similar normalisations are properties of a particular corpus, not of the tool, and stay with whoever curates that corpus.
- `App` gains a constructor parameter carrying the choice. `domain/app.py` reads no environment variable: the value arrives already resolved.
- `ENV_PACKAGE_DETECTOR = "RV_PACKAGE_DETECTOR"` joins the `ENV_*` registry and is read **at the entry points only** — `rv-experiment` and the standalone `rv-static-analysis` command — beside the negatable CLI flag `--package-detector` / `--no-package-detector`, with precedence CLI > env > default (INV-EXP-32) at each. Every layer in between (`rv-platform`, `rv-instrumentation-*`, `rv-android-core`) receives the resolved boolean by value: `rv-experiment` carries it into `PlatformConfig`, and `App` takes it as a constructor argument. The L1 canonical-reader set is not extended and `domain/app.py` reads nothing — `docs/WORKFLOW.md` §14 and `docs/adr/0001-env-var-pattern.md` are followed, not amended.
- The run records which key it used and where that key came from (`manifest` | `detector`). No code path infers a key from an analysis JSON it did not produce: the GATOR JSON stores the manifest package, not the key that filtered it, so an artefact cannot report its own filter key and the tool must not guess one.
- `PackageDetector` itself is unchanged. Its heuristics, its result type and its logging keep their current behaviour under the flag.

### Explicitly out of scope

- **Removing `PackageDetector`.** It stays, and stays justified for the game-engine and library-namespace cases documented in `core/spec.md:597`.
- **The class-membership semantics of the filter.** The parser matches by substring (`static_analysis_parser.py:359`, INV-ANA-03) while GATOR's client matches by prefix. That divergence is real and independent; changing the key and the semantics together would make any measured difference unattributable.
- **Re-analysing any existing corpus.** Which stored JSON belongs to which key is data management, not tool behaviour.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `core`: `App.code_package` changes its source and gains the selector parameter — INV-CORE-18 is rewritten; `App.package_name` is untouched.
- `analysis`: the provenance of the filtering key changes — INV-ANA-03 is rewritten, INV-ANA-14 (the seven-strategy priority order) is restated as holding only in detector mode, and the Godot scenario becomes a detector-mode scenario.
- `experiment`: a new CLI flag and its `RV_PACKAGE_DETECTOR` counterpart enter the L5 surface under the existing CLI > env > default contract.

## Impact

- **Modules**: `rv-android-core` (`domain/app.py`, `constants.py`), `rv-experiment` (env read, CLI flag, propagation into `App`), `rv-static-analysis` (receives the resolved value; `__main__.py:326,404` construct `App` directly). `rv-platform` (`platform.py:232`, `components/static_analysis.py:136`, `result_processor.py:269`) and `rv-instrumentation-ajc` (`ajc_instrumentation.py:192,849`) consume the property and inherit the new default.
- **Requirements**: FR04, FR05, FR06 — the static analyses keep their contracts; what changes is which package scopes their parsed output. NFR05 (Configurability) gains the flag under the documented env-var pattern; NFR06 (Observability) gains the key-provenance record.
- **Lint and tests**: `scripts/check_env_vars_drift.py` must stay at 0 violations, which requires the constant plus its `README.md` and `.env.example` entries. `test_constants_registry.py` and `tests/lint/test_env_vars_drift.py` are the gates. Docker needs no edit — `validate_env_vars.sh` reads the registry at runtime.
- **Cross-module interface**: `App` is constructed at eight call sites across five modules (`util/utils.py:309`, `pre_processor.py:342,461,477`, `ajc_instrumentation.py:192`, `platform.py:232`, `rv-static-analysis/__main__.py:326,404`), plus the `scripts/` tree; each must pass the resolved choice or accept the default explicitly.
