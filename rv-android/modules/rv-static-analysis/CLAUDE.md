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

- **`code_package` prefix filter:** only classes whose name starts with `code_package` are kept. Handles APKs where the manifest package differs from the implementation package (Godot: manifest `ir.hsn6.trans`, code `org.godotengine.godot`). rv-platform passes `app.code_package` (not `package_name`) for this reason.
- **SignatureNormalizer** normalizes inner-class notation (`.` → `$`). GATOR already writes `$` via `SootClass.getName()`, so this is a safety-net no-op on well-formed output.

## CLI flags
- `--cg-algorithm` (default `spark`) — call-graph algorithm.
- `--analysis-timeout <s>` (gh55) — per-APK GATOR timeout; **required for standalone runs** (see caveat).
- `--skip-wtg` (gh57) — appends `-clientParam skipWtg=true`; GATOR emits reachability + `windows[]` and returns without building the WTG (`transitions[]` empty). For known-slow APKs where WTG construction is guaranteed to time out.

### Standalone env-var caveat (gh55)
`__main__` is argparse-based, not Click, so it does **not** honor `RV_SA_TIMEOUT` / `RV_JVM_MEMORY` when run directly (`uv run rv-static-analysis ...`). Those env vars only bridge through rv-experiment (gh55 §9 Click `envvar=`). For standalone runs use `--analysis-timeout` (added precisely to close this gap). Architectural fix tracked in `openspec/changes/gh-tbd-env-vars-architecture/`.

## Integration seams
- **rv-android-core:** `App`, `StaticAnalysisData`/`Classes`/`Windows`/`WindowTransitionGraph`/`Components`, `SignatureNormalizer`, `EXTENSION_STATIC_ANALYSIS`, base analyzer/error/logging infra.
- **rv-platform:** `StaticAnalysisComponent` calls `analyze()` in pre-processing, passing `app.code_package`.
- **rv-agent:** WTG → `TransitionManager`/`NavigationGuidance`; MOP flags → `RVAgentVisitor` action prioritization.
- **rv-coverage:** `Classes.methods` is the coverage denominator; `reachable` flag splits reachable vs unreachable.

## Error handling
- `StaticAnalysisException` — execution failures, **including the defensive post-condition** raised when GATOR returns but no output JSON exists at the expected path (catches a swallowed `CommandNotFoundError` / unreachable launcher, preventing silent zero-coverage downstream).
- `ConfigurationError` — invalid config.
- Parser returns empty sections for missing/malformed data; timeout produces partial JSON that the parser recovers.
