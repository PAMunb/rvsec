# Proposal: Unify GESDA + GATOR + REACH into Single GATOR Client

**GitHub Issue**: #27
**Track**: Full SDD
**Date**: 2026-02-20

## Why

The gh26 experiment batch shows very low static analysis success rates because three separate Java tools (GESDA, GATOR, REACH) each initialize Soot independently — 3 redundant Soot startups and up to 3 call graph constructions per APK. Combined with critical misconfigurations (`cg all-reachable` inflating call graphs 10-100x, no process-level timeouts, no JVM memory flags), analysis that should take 2-5 minutes per APK takes 30-60+ minutes or hangs indefinitely. This blocks the entire gh26 experiment campaign.

## What Changes

- **BREAKING**: Replace three separate static analysis tools (GESDA, GATOR, REACH) with a single unified GATOR client (`RvsecUnifiedClient`) that produces one JSON output file instead of three separate `.gesda`/`.wtg`/`.reach` files
- **BREAKING**: Replace three Python parsers (`GesdaParser`, `GatorParser`, `ReachParser`) with a single `UnifiedParser` that reads the unified JSON
- **BREAKING**: Replace three-tool pipeline in `StaticAnalyzer` with a single `_run_unified()` invocation
- **BREAKING**: Change `StaticAnalysisResult` from three file paths (`gesda_file`, `gator_file`, `reach_file`) to a single `unified_file` path
- Remove `cg all-reachable` from call graph construction (safe — FlowDroid callback discovery + CHA provides complete JCA reachability without forcing every method as entry point)
- Use JGraphT Dijkstra with caching for reachability computation instead of independent BFS traversals
- Extract `inputType` and `entries` from GATOR's decoded layout XMLs (these GESDA-exclusive fields are not available via GATOR's internal APIs)
- Drop unused fields: `layoutFileName`, `field`, `registeredInFile`, `possiblePath`, `allPathsToMop` (see `plan.md` Section 4 for field-by-field usage analysis)
- Update `rv-platform` `StaticAnalysisComponent` file copy extensions
- Add `EXTENSION_UNIFIED` constant to `rv-android-core`

## Capabilities

### New Capabilities

None. The unified tool produces the same `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph) consumed by all downstream modules. The change is architectural — consolidating three tools into one — not a new capability.

### Modified Capabilities

- `analysis`: FR04 (GATOR), FR05 (GESDA), and FR06 (REACH) are unified into a single tool invocation. INV-ANA-01 (GESDA-before-REACH ordering) no longer applies — there is one tool, not a pipeline. INV-ANA-02 (SignatureNormalizer) and INV-ANA-03 (code_package filtering) still apply but to UnifiedParser instead of three separate parsers. INV-ANA-06 (graceful degradation) applies per-section within the unified JSON. INV-ANA-11 (caching) applies to a single output file instead of three. StaticAnalysisResult data contract changes from three file paths to one.

## Impact

### Modules Affected

| Module | Change Type | Scope |
|--------|-------------|-------|
| **rv-static-analysis** | Major | New parser, rewritten analyzer, updated config, deleted parsers |
| **rv-android-core** | Minor | New constant (`EXTENSION_UNIFIED`) |
| **rv-platform** | Minor | Updated file copy extensions in `StaticAnalysisComponent` |

### External (Java — RVSEC_HOME)

| Component | Change Type | Scope |
|-----------|-------------|-------|
| **rvsec-gator/client** | Major | New `RvsecUnifiedClient.java`, updated `pom.xml` with JGraphT + shade plugin |

### Dependencies and Risks

- **Soot version**: GATOR uses Soot 3.3.0 (OSU fork). Dependencies (`rvsec-mop-extractor`, `rvsec-apk`) must exclude their Soot transitive deps to avoid conflicts.
- **GATOR timeout**: GATOR's fixpoint solver can hang on complex APKs. Mitigated by process-level timeout (600s) via `Command.timeout` and GATOR's `--timeout` flag.
- **Reachability differences**: Removing `all-reachable` may produce slightly different reachability results. `directly_reaches_mop` flags are CG-construction-independent and will be preserved. Differences in `reaches_mop` must be documented and validated against `cryptoapp.apk` baseline.

### Related FRs/NFRs

- **FR04**: GATOR WTG analysis — unified into single tool
- **FR05**: GESDA widget extraction — unified into single tool
- **FR06**: REACH reachability — unified into single tool
- **NFR01**: Performance — ~3x speedup from eliminating redundant Soot initializations
