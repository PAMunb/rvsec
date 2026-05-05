## Why

GitHub Issue: #51

GATOR static analysis succeeds on only 97/352 instrumented APKs (27.6%). The root cause is a `InternalTypingException` in Soot 3.3.0's `ClassHierarchy.typeNode()` when processing Kotlin bytecode (issue soot-oss/soot#1071, open since 2018). The crash is compounded by GATOR configuring Soot with zero defensive options and re-throwing exceptions fatally instead of continuing with partial data. Empirical validation with CryptoAnalysis 5.0.1 (Soot 4.6.0) confirms that the upgrade path eliminates the crash.

## What Changes

- **GATOR Soot configuration**: Add defensive options to `Main.java` — disable `jb.sils` and `jb.dae` sub-phases (documented workaround for typing crashes, soot#1641/#1975), exclude `kotlin.*`/`kotlinx.*`/`androidx.compose.*` from body loading, enable `no_bodies_for_excluded`, `ignore_resolution_errors`, and `throw_analysis_dalvik`
- **GATOR error handling**: Protect crash/hang points across the GUI analysis pipeline — `Flowgraph.java` (try-catch + null receiver), `FlowgraphRebuilder.java` (null receiver x2), `IntentAnalysis.java` (visited set to prevent infinite loop), and `RvsecAnalysisClient.java` (write reachability JSON before WTG so external timeout preserves data)
- **Soot version upgrade**: Unify GATOR from `ca.mcgill.sable:soot:3.3.0` (discontinued 2019) to `org.soot-oss:soot:4.7.1` (latest stable, Feb 2026), aligning with the parent pom's `org.soot-oss` group. Replace `-process-multiple-dex` with `-search-dex-in-archives` (renamed in Soot 4.x)
- **Deprecated module removal**: Remove `rvsec-methods-extractor` and `rvsec-taint` from `rvsec-android/pom.xml` and move directories to `backup/` before upgrade to reduce compilation surface
- **Soot exclusion in FIX 1**: Add `-exclude androidx.compose.` alongside `kotlin.*`/`kotlinx.*` to cover the dominant failure category (Kotlin+Compose APKs are ~71% of crashes)
- **Call graph algorithm parameter**: Replace boolean `-withCHA` flag with `-cgAlgorithm <cha|rta|vta|spark>` parameter in `Main.java`, GATOR Python script, and `rv-static-analysis` config. **Default: `spark`** (full points-to analysis). RTA/VTA/SPARK use the SPARK framework internally with different precision levels; CHA remains available for experiments where speed dominates over precision. Default tightens `reachesMop` for accurate `cov_reaches_mop` metrics and focused MOP-aware navigation in `aperv:sata_mop`. Rationale in design.md D5
- **Fat JAR rebuild**: Remove Soot exclusion from `rvsec-gator/client/pom.xml` dependency exclusions in `rvsec-mop-extractor` (lines 43-51; no more groupId conflict) and rebuild `rvsec-analysis-client.jar`
- **BUG-INV-ANA-19 — `directlyReachesMop` bytecode-scan complement**: cross-validation against Androguard surfaced 2 FT cases on `directly_reaches_mop` where the bytecode literally invokes a MOP signature (`SecureRandom.<init>`, `SecureRandom.nextInt`) but GATOR reported `false`. Root cause: `findDirectMopCallers` (RvsecAnalysisClient.java:406-421) iterates only vertices in the JGraphT graph built from Soot's CallGraph, and SPARK omits library targets (`java.security.*`, `javax.crypto.*` are quarantined as IGNORED_CLASSES) so the MOP target never appears as an edge target. `reachesMopSet` recovers the same method through `complementWithCallbacks` transitive completion, producing the inconsistent `reachesMop=true, directlyReachesMop=false` pair. Fix adds a statement-level scan (`findDirectMopCallersByBytecodeScan`) over each app method's `Body.getUnits()` matching `InvokeExpr` against the MOP signature key set (`className#methodName`, mirroring `resolveMopInScene`). Independent of the call graph; resilient body retrieval (try-catch on `RuntimeException`/`OutOfMemoryError`, same pattern as Flowgraph.java FIX 2). Empirically validated: `com.myAllVideoBrowser_197.apk` `GeneratedProxyCreds$Companion::generateRandomString` now reports `directlyReachesMop=true`; cryptoapp baseline unchanged at 22 (CG=22, bytecode=21, intersection=21). Helper methods `buildMopKeys` and `matchesMopSignature` are package-private for unit testing without a Soot Scene.

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
