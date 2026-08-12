# CLAUDE.md - rv-static-analysis

Guidance for Claude Code working in the rv-static-analysis module. See `rv-android/CLAUDE.md` for workspace-wide setup (uv sync, pytest, env vars, spec sets).

## Purpose
Runs unified GATOR static analysis on APKs and parses the single JSON output into `StaticAnalysisData` domain objects (reachability, windows, transitions, components). Feeds navigation guidance and MOP prioritization in rv-agent, and the coverage denominator in rv-coverage.

- `StaticAnalyzer` (`analysis/static/static_analysis.py`) — orchestrates one GATOR invocation, produces `StaticAnalysisData`.
- `RVStaticAnalysisConfig` (`config.py`) — Pydantic config.
- Parser (`parser/static/static_analysis_parser.py`) — `parse_file()` / `StaticAnalysisParser`.

Authoritative JSON contract (schema + field semantics) lives with the producer: `rvsec/rvsec-android/rvsec-gator/CLAUDE.md` and `rv-android/openspec/specs/analysis/spec.md`. Section invariants (priority ordering, graceful degradation) are specified in `analysis/spec.md` — do not restate them here.

## Config resolution
Priority: (1) explicit params → (2) `rvsec_root` standard layout → (3) `RVSEC_HOME` → (4) cwd parent.
Key fields: `rvsec_root`, `lib_dir`, `gator_dir`, `analysis_client_jar`, `android_jar`, `mop_dir`, `output_dir`, `jvm_memory` (default `8g`), `cg_algorithm` (`spark|cha|rta|vta`, default `spark`), `skip_wtg` (default `False`).
`get_tool_command()` builds the GATOR command; standard layout expects `rv-android/lib/gator/{gator,rvsec-analysis-client.jar}` and `rvsec/rvsec-mop/src/main/resources/jca/`.

**`sys.executable` launcher:** `get_tool_command()` invokes the GATOR launcher with `sys.executable`, not literal `"python"` — avoids failures on systems without `/usr/bin/python` (clean Debian/Ubuntu, containers lacking `python-is-python3`).

## Parser semantics
Parses four sections — `reachability`, `windows`, `transitions`, `components` — each independently via order-independent key lookup, plus a trailing `complete` flag (incomplete/truncated samples set it `False`). A missing/corrupt section (e.g. timeout killed GATOR mid-write) yields empty domain objects rather than a failure. The authoritative on-disk write order lives with the producer (`rvsec/rvsec-android/rvsec-gator/CLAUDE.md`).

- **The artefact carries its own scope — parsing takes no package key (gh102).** GATOR was invoked with `-clientParam codePackage=<key>` and dropped everything outside that key before writing, so `reachability` *is* the application's whole method universe: every entry is loaded, unfiltered, and that set is the coverage denominator (INV-ANA-59). `windows`, by contrast, is **not** scoped by the producer — framework and library activities (`androidx.activity.ComponentActivity`, `com.canhub.cropper.CropImageActivity`) appear there and would inflate the activity denominator — so an `ACTIVITY` window is admitted exactly when its class is present in `reachability` (INV-ANA-60), a test the artefact answers on its own and therefore cannot disagree with the producer. `DIALOG`, `OPTIONSMENU` and other types are admitted unconditionally, because they can be system-provided overlays triggered by app code. No consumption-path function accepts a key (INV-ANA-61): the signatures are `parse_file(path)` and `read_static_analysis_files(results_dir, apk)`. Re-asking the scoping question here could only contradict the producer, and on an app built with `applicationIdSuffix` it emptied the universe outright.
- **Choosing the scope is a production-path concern.** `RVStaticAnalysisConfig.get_tool_command(code_package=…)` emits the `-clientParam`, and `analyze()` records `code_package` / `code_package_source` on its own `StaticAnalysisResult`. The key is the applicationId the APK declares unless the run enabled `PackageDetector` (`--package-detector` / `RV_PACKAGE_DETECTOR`), which elects the implementation package instead — what a corpus of Godot games needs (manifest `ir.hsn6.trans`, classes under `org.godotengine.godot`). It is never recovered from a stored JSON: GATOR writes the manifest package into the artefact's `package` member whatever key filtered it, so the run must record its own key (INV-ANA-58).
- **SignatureNormalizer** normalizes inner-class notation (`.` → `$`). GATOR already writes `$` via `SootClass.getName()`, so this is a safety-net no-op on well-formed output.
- **Method granularity is `(class, method)`. Overloads are not distinguished anywhere, and no analysis should assume they are.** GATOR seeds reachability from MOP targets under `MatchPolicy.LENIENT`, which matches on class name + method name only and ignores parameter types entirely (`TargetResolver.resolveInScene`); every overload of a targeted method becomes a seed. The runtime side agrees by construction — `rv-monitor` locates a violation from a `StackTraceElement` (`Class.method(File:line)`), which carries no parameter descriptor, and `rvsec-core` parses it back into `(class, method, loc)`. So the `(apk, class, method, spec)` key that joins static analysis, coverage and violations is method-name-granular at both ends. Do not build a comparison, a gate or a denominator that keys on a full signature: it cannot be honoured end to end, which is why the pipeline never tries.
- **`Loaded N MOP signatures` in the GATOR log is not a target count.** N counts signature-distinct rows, so it is inflated by overloads: `jca` prints 120 while seeding 68 distinct `(class, method)` targets; `jca_android` prints 119 and seeds 67. Use it to confirm *which spec set* was loaded, never to detect *whether the target set changed* — collapse to distinct `(class, method)` for that.

## CLI flags
- `--cg-algorithm` (default `spark`) — call-graph algorithm.
- `--analysis-timeout <s>` (gh55) — per-APK GATOR timeout; **required for standalone runs** (see caveat).
- `--skip-wtg` (gh57) — appends `-clientParam skipWtg=true`; GATOR emits reachability + `windows[]` and returns without building the WTG (`transitions[]` empty). For known-slow APKs where WTG construction is guaranteed to time out.
- `--package-detector` / `--no-package-detector` (gh98) — which package scopes app-owned classes. Default: the declared applicationId, passed to GATOR as `-clientParam codePackage=` verbatim. Honors `RV_PACKAGE_DETECTOR` under flag > env > default; an unparseable value exits nonzero before any APK is opened.

### Standalone env-var caveat (gh55)
`__main__` is argparse-based, not Click, so it does **not** honor `RV_SA_TIMEOUT` / `RV_JVM_MEMORY` when run directly (`uv run rv-static-analysis ...`). Those env vars only bridge through rv-experiment (gh55 §9 Click `envvar=`). For standalone runs use `--analysis-timeout` (added precisely to close this gap). Architectural fix tracked in `openspec/changes/gh-tbd-env-vars-architecture/`.

`RV_PACKAGE_DETECTOR` is the exception, and deliberately so (gh98 D4): this command resolves it itself, because a standalone invocation is a run rather than a step inside one, and an operator who exported the variable in a shell or a container should get the same behaviour whichever command they invoke. It is read through the `ENV_PACKAGE_DETECTOR` constant and parsed by the same helper `rv-experiment` uses, so the two CLIs cannot drift on what a given string means.

## Integration seams
- **rv-android-core:** `App`, `StaticAnalysisData`/`Classes`/`Windows`/`WindowTransitionGraph`/`Components`, `SignatureNormalizer`, `EXTENSION_STATIC_ANALYSIS`, base analyzer/error/logging infra.
- **rv-experiment:** `PreProcessor` calls `analyze()` in pre-processing, where `app.code_package` is the production key.
- **rv-platform:** runs no analysis — it only re-loads stored artefacts. `StaticAnalysisComponent` and `ResultProcessor` both call `read_static_analysis_files(results_dir, apk)`, passing no key.
- **rv-agent:** WTG → `TransitionManager`/`NavigationGuidance`; MOP flags → `RVAgentVisitor` action prioritization.
- **rv-coverage:** `Classes.methods` is the coverage denominator; `reachable` flag splits reachable vs unreachable.

## Error handling
- `StaticAnalysisException` — execution failures, **including the defensive post-condition** raised when GATOR returns but no output JSON exists at the expected path (catches a swallowed `CommandNotFoundError` / unreachable launcher, preventing silent zero-coverage downstream).
- `ConfigurationError` — invalid config.
- Parser returns empty sections for missing/malformed data; timeout produces partial JSON that the parser recovers.
