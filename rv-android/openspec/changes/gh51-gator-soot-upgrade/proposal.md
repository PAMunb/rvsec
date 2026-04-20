## Why

GitHub Issue: #51

GATOR static analysis succeeds on only 97/352 instrumented APKs (27.6%). The root cause is a `InternalTypingException` in Soot 3.3.0's `ClassHierarchy.typeNode()` when processing Kotlin bytecode (issue soot-oss/soot#1071, open since 2018). The crash is compounded by GATOR configuring Soot with zero defensive options and re-throwing exceptions fatally instead of continuing with partial data. Empirical validation with CryptoAnalysis 5.0.1 (Soot 4.6.0) confirms that the upgrade path eliminates the crash.

## What Changes

- **GATOR Soot configuration**: Add defensive options to `Main.java` — disable `jb.sils` and `jb.dae` sub-phases (documented workaround for typing crashes, soot#1641/#1975), exclude `kotlin.*`/`kotlinx.*`/`androidx.compose.*` from body loading, enable `no_bodies_for_excluded`, `ignore_resolution_errors`, and `throw_analysis_dalvik`
- **GATOR error handling**: Protect two crash points in `Flowgraph.java` — wrap unguarded `retrieveActiveBody()` at line 274 in try-catch, and replace fatal `throw RuntimeException` at line 343 with `continue`
- **Soot version upgrade**: Unify GATOR from `ca.mcgill.sable:soot:3.3.0` (discontinued 2019) to `org.soot-oss:soot:4.7.1` (latest stable, Feb 2026), aligning with the parent pom's `org.soot-oss` group
- **Deprecated module removal**: Remove `rvsec-methods-extractor` and `rvsec-taint` from `rvsec-android/pom.xml` and move directories to `backup/` before upgrade to reduce compilation surface
- **Soot exclusion in FIX 1**: Add `-exclude androidx.compose.` alongside `kotlin.*`/`kotlinx.*` to cover the dominant failure category (Kotlin+Compose APKs are ~71% of crashes)
- **CHA description update**: The call graph strategy description is updated to reflect the actual operational state — CHA with `-withCHA` flag is always used (was described as optional in the spec, but the execution command always includes it)
- **Fat JAR rebuild**: Remove Soot exclusion from `rvsec-gator/client/pom.xml` dependency exclusions in `rvsec-mop-extractor` (lines 43-51; no more groupId conflict) and rebuild `rvsec-analysis-client.jar`

## Capabilities

### New Capabilities

(none — this change improves robustness of existing capabilities)

### Modified Capabilities

- `analysis`: The GATOR analysis client's Soot configuration, error handling, and Soot version change. The `StaticAnalysisParser` (Python side) is unmodified — it already handles partial JSON gracefully (INV-ANA-06). The change affects the Java side only (rvsec-gator), improving the rate at which JSON files are produced.

## Impact

**Java modules affected (RVSEC)**:
- `rvsec-gator` (Main.java, Flowgraph.java, all pom.xml files) — primary target
- `rvsec/pom.xml` — parent `soot.version` property
- `rvsec-apk` — FlowDroid 2.10.0 transitively pulls Soot ~4.3.0; Maven mediation resolves to 4.7.1

**Python modules affected (rv-android)**: None directly. The `StaticAnalyzer` wrapper and `StaticAnalysisParser` are unchanged. More APKs will produce JSON, increasing downstream data availability for rv-coverage and rv-agent.

**Related FRs**: FR04 (reachability), FR05 (WTG), FR06 (GUI elements) — all benefit from higher SA success rate.

**Risk**: Soot API breaks in `Configs.java` (Options setters), `EpiccBasedIntentAnalysis.java` (`soot.dexpler.Util`). FlowDroid 2.10.0 compatibility with Soot 4.7.1 needs runtime validation (compile ≠ runtime — `NoSuchMethodError` possible). Guava version conflict (GATOR uses 27.1-jre, parent uses 19.0).
