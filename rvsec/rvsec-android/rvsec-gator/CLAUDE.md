# CLAUDE.md - rvsec-gator

## Purpose

Static-analysis engine of RVSEC (a fork of **GATOR** on **Soot 4.7.1**). Runs
`presto.android.Main` over one APK and, via `RvsecAnalysisClient`, emits **one JSON per
APK** with four sections: `reachability` (coverage denominator), `windows`/widgets, WTG
`transitions`, and manifest `components`. It **unified and replaced** the former GESDA,
standalone REACH (reachability), and the WTG client into a single tool.

## Role in pipeline

Pre-processing static pass: computes the coverage denominator (reachable methods),
which application methods reach JCA targets, the widget inventory, and the WTG that
downstream dynamic exploration + prioritization consume. Fork lineage:
`limerick1718/Gator` -> `phtcosta/Gator` -> this in-tree fork.

## Relationships

- **Consumes (Java):** `rvsec-mop-extractor` (`JavamopFacade`, `MopMethod` — parse MOP
  specs into targets), `rvsec-apk` (APK metadata; FlowDroid/Soot excluded to avoid clash),
  FlowDroid `2.10.0`.
- **Consumed by (Python, sibling repo `../rv-android`):**
  `modules/rv-static-analysis` builds the launch command (`config.py`) and parses output
  via `StaticAnalysisParser` (`parser/static/static_analysis_parser.py`) into
  `StaticAnalysisData` (`rv-android-core/domain/static.py`) -> `rv-coverage` (denominator),
  `rv-agent`/`aperv` (WTG navigation + Target/MOP prioritization), `rv-platform`.

## Dependencies (versions)

Internal: `rvsec-gator-commons`, `rvsec-gator-sootandroid` (scope `provided` in client),
`rvsec-mop-extractor`, `rvsec-apk`. External: **Soot 4.7.1** (`org.soot-oss`, inherited
from a higher parent), **JGraphT 1.5.2** (multi-source BFS reachability), **Gson 2.10.1**,
Guava 27.1-jre, classindex 3.4, velocity 1.7, slf4j-simple 1.7.26, JUnit 4.12.

## Sub-reactor (`pom.xml`, `packaging=pom`, artifact `rvsec-gator-parent`)

| Module | Java files | Notes |
|---|---|---|
| `commons/` | 4 | Timer/Logger helpers |
| `sootandroid/` | 181 | GATOR fork; main `presto.android.Main`; fat jar `rvsec-gator.jar` |
| `client/` | 17 (main) | `presto.android.gui.clients`; fat jar **`rvsec-analysis-client.jar`** |

## Key components (real paths)

- `client/.../clients/RvsecAnalysisClient.java` — orchestrator (~1740 LOC; also holds the
  `writeReachability/Windows/Transitions/ComponentsSection` static writers).
- `client/.../clients/target/{TargetResolver,MopSpecsTargetSource,SignatureFileTargetSource}.java`
- `client/.../clients/reach/{ReachabilityEngine,ReachabilityIndex,ReachabilityEnricher}.java`
- `client/.../clients/json/{JsonReportWriter,JsonSchema (nested .Keys),JsonSchemaKeysDump}.java`
- `client/.../clients/{MenuExtractor,SpinnerItemExtractor}.java` (+ legacy `wtg/model/*`, `wtg/writer/Writer.java`)
- `sootandroid/.../presto/android/Main.java` (Soot config), `Configs.java` (client params),
  `gui/Flowgraph.java`, `gui/wtg/WTGBuilder.java`, `gui/flowgraph/{FlowgraphRebuilder,AndroidCallGraph}.java`
  (cgDelegation), `xml/XMLParser.java`, `gui/util/JimpleDefUtils.java`.

## JSON contract

Keys centralized in `JsonSchema.Keys` == Python `_JK` (INV-ANA-32); target fields renamed
**MOP -> Target** (`reachesTarget`, `directlyReachesTarget`). Sentinel `"complete": true`
written **last**, then `fos.getFD().sync()`; absence => parser marks sample incomplete.
**Actual write order (JsonReportWriter, D14 2026-05-29): `components -> reachability ->
windows -> transitions -> complete`** — components is promoted first (manifest-derived,
cheap) so a WTG/transitions timeout cannot drop the windows->activity lookup. (Note: the
class Javadoc + `RvsecAnalysisClient` header still describe the older
`reachability -> windows -> transitions -> components` "priority" order — stale comment.)

## Build & invocation

```
cd rvsec-gator && mvn package -DskipTests   # -> client/target/rvsec-analysis-client.jar (~62 MB)
```
Parent `maven-resources-plugin` copies the jar to `../rv-android/lib/gator/` on `install`.
Launched by the Python side:
```
python gator a -p <apk> --client-jar <jar> -client RvsecAnalysisClient \
  -clientParam mopDir=<dir> -cgAlgorithm spark --timeout <t>
```
Params (`Configs.getClientParamCode`): `mopDir` **XOR** `targetsFile` (INV-ANA-33; enforced
in Python and re-checked in-client); `cgAlgorithm=spark` (default); **`cgDelegation=false`
(default, M3 gate 2026-05-15)**; `skipWtg=false`; `--timeout=600`.

## References

Canonical spec: `../rv-android/openspec/specs/analysis/spec.md` (invariants **INV-ANA-\***,
71 refs). **Defer to it — do not duplicate.** Consumer contract: `../rv-android/modules/rv-static-analysis/CLAUDE.md`.

## Gotchas

- **Partial JSON on WTG timeout:** two-write strategy overwrites the pre-WTG file; no
  sentinel => `complete=false`, parser recovers. Windows absent from the WTG get a
  `fallbackId >= 100000`.
- **Hard halt** if SPARK call-graph construction fails: emits **no JSON** by design.
- `directlyReachesTarget` is a bytecode-scan complement and a **superset** of SPARK-only
  `reachesTarget`.
- Soot exclusions of `kotlin.*` / `kotlinx.*` / `androidx.compose.*` (analysis scoping).
- **Stale internal READMEs** (`client/README.md` describes an old all-in-one client;
  `sootandroid/TestMain` targets the upstream author's paths and is excluded) — trust the
  spec + code, not the in-tree READMEs.
