# CLAUDE.md - rvsec-gator

## Purpose

Static-analysis engine of RVSEC (a fork of **GATOR** on **Soot 4.7.1**). Runs
`presto.android.Main` over one APK and, via `RvsecAnalysisClient`, emits **one JSON per
APK** with five sections: `reachability` (coverage denominator, per-method target
distances), `distanceTargets`, `windows`/widgets, WTG `transitions`, and manifest
`components`. It **unified and replaced** the former GESDA,
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
| `sootandroid/` | 180 | GATOR fork; main `presto.android.Main`; fat jar `rvsec-gator.jar` |
| `client/` | 28 (main) | `presto.android.gui.clients`; fat jar **`rvsec-analysis-client.jar`** |

## Key components (real paths)

- `client/.../clients/RvsecAnalysisClient.java` — orchestrator (~2250 LOC; also holds the
  `writeReachability/Windows/Transitions/ComponentsSection` static writers, `prepareWindows`,
  `dropRepeatedOwnedWindows`, `dropRepeatedWidgets`), and the reachability seeds:
  `getEntryPoints(output, appClasses)` (activities; manifest services, receivers, providers;
  the manifest's `Application` subclass; app subclasses of the `FragmentViewFlow` bases —
  fragments, `ListenableWorker` (`doWork`/`startWork` only), RecyclerView `Adapter`/`ViewHolder`;
  INV-ANA-95) and `collectCallbacks(output)` (lifecycle, GUI event and component callbacks),
  which seed the forward search together (INV-ANA-94).
- `client/.../clients/target/{TargetResolver,MopSpecsTargetSource,SignatureFileTargetSource}.java`
- `client/.../clients/reach/{ReachabilityEngine,ReachabilityIndex,ReachabilityEnricher}.java`,
  `reach/LambdaEdges.java` (D8 lambda wrapper → body and single-invoke SAM edges added to the
  Scene call graph before reachability, INV-ANA-77), `reach/EmptySiteEdges.java` (edges at the
  instance-invoke sites of app methods SPARK left with no edge, to app callees only, added right
  after the lambda edges, INV-ANA-96), `reach/TargetDistances.java` (one reverse
  BFS per target, depth ≤ `DIST_MAX` = 10, INV-ANA-73; `compact()` and
  `COMPACT_WEIGHED_MAX`/`COMPACT_K` = 3/3, the per-method reduction of compact output,
  INV-ANA-85; `paths()` and `keptByCompact()`, the second pass behind the distance paths),
  `reach/DistancePaths.java` (the `pathMethods` table and `distancePaths` steps a run writes)
- `client/.../clients/fragment/{FragmentHostResolver,FragmentWindows}.java` — host → fragment
  map (layout tags, transactions, Navigation XML, pagers) and `FRAGMENT` windows
- `client/.../clients/hosted/{HostedWindowExtractor,HostResolver,NavGraphUses,BindingListenerRecovery}.java`
  — `HOSTED` windows (dialogs, DialogFragment, DataBinding, adapters, bottom sheets), at most
  `MAX_HOSTS` = 20 hosts per owner
- `client/.../clients/json/{JsonReportWriter,JsonSchema (nested .Keys),JsonSchemaKeysDump}.java`
- `client/.../clients/{MenuExtractor,SpinnerItemExtractor}.java` (+ legacy `wtg/model/*`, `wtg/writer/Writer.java`)
- `sootandroid/.../presto/android/Main.java` (Soot config), `Configs.java` (client params),
  `gui/Flowgraph.java`, `gui/wtg/WTGBuilder.java`, `gui/flowgraph/{FlowgraphRebuilder,AndroidCallGraph}.java`
  (cgDelegation), `xml/XMLParser.java` (`getApplicationClassName()` = `<application android:name>`), `gui/util/JimpleDefUtils.java`,
  `gui/FragmentViewFlow.java` (`onCreateView` → `onViewCreated(view)`/`getView()`; also the
  public `FRAGMENT_BASES`, `LISTENABLE_WORKER` and `RECYCLER_VIEW_BASES` the client's
  `FragmentHostResolver` and entry points read),
  `gui/LibraryInflateModel.java` (DataBinding, `AppCompatActivity(int)`, builder
  `setView(int)`); the ViewBinding op node (`ViewBindings.findChildViewById`) lives in
  `Flowgraph.createOpNode`.

## JSON contract

Keys centralized in `JsonSchema.Keys` == Python `_JK` (INV-ANA-32); target fields renamed
**MOP -> Target** (`reachesTarget`, `directlyReachesTarget`). Sentinel `"complete": true`
written **last**, then `fos.getFD().sync()`; absence => parser marks sample incomplete.
**Actual write order (JsonReportWriter, D14 2026-05-29): `components -> reachability ->
windows -> transitions -> complete`** — components is promoted first (manifest-derived,
cheap) so a WTG/transitions timeout cannot drop the windows->activity lookup. (Note: the
class Javadoc + `RvsecAnalysisClient` header still describe the older
`reachability -> windows -> transitions -> components` "priority" order — stale comment.)

**Output modes (INV-ANA-85, INV-ANA-86).** `RvsecAnalysisClient.fullOutput()` reads the
client parameter `fullOutput`; `true` (case-insensitive) selects **full** output, anything
else or its absence selects **compact**, the default. `JsonReportWriter` holds one mode,
so the pre-WTG write and the final write of a run always agree.
- **Full**: two-space indent, every `targetDistances` pair up to `DIST_MAX`, no marker —
  the form of the documents already published (E6 corpus included), reproduced byte for
  byte up to `transitions`; `transitions` holds the same edges, in the order the WTG's
  identity-hash iteration gives this jar (INV-ANA-86).
- **Compact**: no whitespace; each method's `targetDistances` reduced by
  `TargetDistances.compact` (see Distances below); and a top-level marker
  `"distancePairs":{"weighedMax":3,"k":3}` written right after the scope members
  (`package`, `mainActivity`, `codePackage`, `codePackageSource`, `class_defs_under_key`)
  and before `distanceTargets`, even when the distance pass failed and `distanceTargets`
  is absent — it describes how the document was written, not what the pass found. A
  streaming reader learns the document's kind before the first pair.

Why compact is the default: the E6 corpus documents took 24.62 GB for 163 APKs in full
form and take 1.02 GB compact (sdmse 9.3 GB → 55 MB). The only pair consumer, the
`aperv-tool` MOP derive, keeps exactly the pairs compact output writes, and
`StaticAnalysisParser` drops the pairs anyway (INV-ANA-80), so either mode yields the same
`StaticAnalysisData` and the same `*.mop.json` apart from its `source.digest`, the sha256
of the input file (INV-ANA-89). Offline scripts that
count pairs beyond the reduction need a full document; the marker says which one they
hold. A full document already on disk is converted with `rv-static-analysis compact`
(byte-identical to GATOR's compact output, INV-ANA-87) instead of re-running GATOR.

**Distance paths (INV-ANA-90..93).** `RvsecAnalysisClient.distancePaths()` reads the client
parameter `distancePaths`; `true` (case-insensitive) adds two top-level members, written by
`JsonReportWriter` right after `reachability`, in both writes and in both output modes:
- `pathMethods`: the sorted signatures of every method on some path, app and library;
- `distancePaths`: steps `[i, v, n]` sorted by `(i, v)`, at most one per `(i, v)` — "on the
  way to `distanceTargets[i]`, method `pathMethods[v]` calls method `pathMethods[n]`, one call
  closer". Following `n` from a method `d` times reaches the target of its pair `[i, d]`.

The steps cover exactly the chains of the pairs the mode writes (every pair in full output,
the pairs `compact()` keeps in compact output), so a step may pass through a method whose own
pair for `i` was reduced away. A path ends at the app target, never inside library code.
Without the parameter the document is the one written without it, member for member, so
the compact default and the converter's byte identity hold for every campaign document. The
paths exist for the analyser's stand-alone use: no campaign reader reads them
(`read_analysis_document` drops both members), `rv-static-analysis path` prints one method's
chains, and `rv-static-analysis compact` refuses a document that carries them (reducing a
full document's steps would be a second reduction; run GATOR in compact mode with the
parameter instead). The pass runs before the pre-WTG write, logs
`[RvsecAnalysisClient] Distance paths: N methods, S steps (t ms)`, and a failure costs only
the two members.

### Distances and owned windows

- `distanceTargets` (top level) lists the targets of the distance pass as
  `{signature, kind}`: `kind` `"direct"` = app methods with `directlyReachesTarget` (C), then
  `"boundary"` = app methods with an edge to a library method that reaches a target through
  library code only (B \ C). Each method entry may carry `targetDistances` = `[[index, d], …]`
  with `d ≤ 10`, sorted by index; the key is omitted when the method has no pair, and
  `distanceTargets` is omitted only when the pass failed.
- Each search visits a method's callers in signature order (sorted once in `compute`, kept
  on the instance until `run()` releases them after the path pass, so the WTG runs
  without them), with a first-in first-out queue. The order changes no distance; it
  fixes which of several equally short paths a search reaches first, so the distance paths
  are the same on every run over the same graph (INV-ANA-92). `paths()` is a second pass:
  it repeats the search of each target named by a written pair, recording the callee each
  method was first visited from, and holds one target's search at a time. Recording
  predecessors in the first pass would hold one entry per visited method per target,
  library methods included, for the whole run, and compact output cannot know which pairs
  survive before every target's search is done.
- Full output writes every pair the searches recorded. Compact output keeps per method the
  pairs at `d ≤ COMPACT_WEIGHED_MAX` (3) plus the `COMPACT_K` (3) nearest by `(d, i)`,
  still sorted by index (INV-ANA-85); `distanceTargets` is written whole in both modes,
  because it is the index space. The numbers are the derive's (`aperv-tool`
  `DIST_WEIGHED_MAX`/`DIST_K`: the jar weighs a pair only up to `d = 3`, `activityDist`
  keeps the 3 nearest), which makes the reduction exact for it: a dropped pair has 3
  targets ahead of it in its own method. Because the nearest pair always survives, a method
  carries `targetDistances` in compact output exactly when it does in full output. The
  three declarations (Java, the `rv-static-analysis` converter, `aperv-tool`) are pinned
  equal by `../rv-android/tests/parity/test_distance_pair_constants.py` (INV-ANA-88); the
  marker keys live in `JsonSchema.Keys` and `_JK`.
- Window types: `ACTIVITY`, `DIALOG`, `OPTIONSMENU`, `FRAGMENT` (`Host#Fragment`) and
  `HOSTED` (`Host#Owner`). Owned windows are numbered from `FIRST_OWNED_WINDOW_ID` = 900000;
  a `HOSTED` window whose name equals a `FRAGMENT` window is dropped (one window per (host,
  owner)), and `dropRepeatedOwnedWindows` keeps one owned window per host for each distinct
  widget list.
- `dropRepeatedWidgets` (last step of `prepareWindows`, every window type) keeps one widget
  record among records equal in every field.
- Reachability, distances, `FRAGMENT` and `HOSTED` windows depend only on the solver and the
  call graph, so they are all in the pre-WTG write (INV-ANA-75).

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
(default, M3 gate 2026-05-15)**; `skipWtg=false`; `fullOutput=false` (compact output;
`true` writes the full document, see JSON contract); `distancePaths=false` (`true` adds
`pathMethods`/`distancePaths`, see JSON contract); `--timeout=600`.

## References

Canonical spec: `../rv-android/openspec/specs/analysis/spec.md` (invariants **INV-ANA-\***,
71 refs). **Defer to it — do not duplicate.** Consumer contract: `../rv-android/modules/rv-static-analysis/CLAUDE.md`.

## Gotchas

- **Overloads do not exist for this analysis. Never reason about targets by full
  signature.** MOP-sourced targets are always built `MatchPolicy.LENIENT`
  (`client/.../target/MopSpecsTargetSource.java:38`), and `TargetResolver.resolveInScene`
  under LENIENT compares **only `(className, methodName)`** and then `break`s
  (`commons/.../target/TargetResolver.java:52-66`) — `params` and `signature` are never
  read, so every overload of a targeted `(class, method)` becomes a seed. This is by
  design, not an oversight: pointcuts carry wildcards, and at runtime `rv-monitor`
  identifies the offending frame from a `StackTraceElement`, which has **no descriptor** —
  `ViolationRecorder.getLineOfCode()` yields `Class.method(File:line)`, which
  `rvsec-core`'s `ErrorDescription.createErrorSummary` parses back into
  `(class, method, loc)`. The `(apk, class, method, spec)` key every downstream analysis
  uses is method-name-granular at both ends. A full signature cannot be honoured end to
  end, so nothing in the pipeline tries.
- **`Loaded N MOP signatures` is NOT the target count.** N is
  `HashSet<TargetMethod>.size()` and `TargetMethod.equals/hashCode` **do** include `params`
  and `signature`, so N counts signature-distinct rows while the analysis seeds on
  `(class, method)` pairs. Measured over the 23 specs: `jca` prints **120** and seeds
  **68**; `jca_android` prints **119** and seeds **67**. Adding an overload of an
  already-targeted method raises N by one and adds **zero** seeds. Any gate, diff or
  regression check over the target set must count distinct `(class, method)` — comparing N
  will fire, or fail to fire, for the wrong reason.
- **Partial JSON on WTG timeout:** two-write strategy overwrites the pre-WTG file; no
  sentinel => `complete=false`, parser recovers. Windows absent from the WTG get a
  `fallbackId >= 100000`.
- **Hard halt** if SPARK call-graph construction fails: emits **no JSON** by design.
- `directlyReachesTarget` is a bytecode-scan complement and a **superset** of SPARK-only
  `reachesTarget`.
- **No `-exclude` package list reaches Soot.** Soot 4.7.1 reads its exclusion list only when
  the `Scene` is constructed, which `PrerunEntrypoint.run()` does before Soot parses its
  arguments. `-no-bodies-for-excluded` is passed and does act, on Soot's default exclusions
  (`java.*`, `javax.*`, `sun.*`, …).
- **Lambda edges change `reachesTarget`.** A D8 wrapper (`X$$ExternalSyntheticLambdaN`)
  whose body reaches a target is now `reachesTarget: true` itself; an artefact produced
  before INV-ANA-77 lists such wrappers with `false`, and the derive trusts a listed
  wrapper's own flag (INV-DRV-09), so never derive from an artefact older than this
  producer.
- **Reachability is seeded by the callbacks, not complemented with them.** Activity
  lifecycle handlers, GUI event handlers and Service/Receiver/Provider lifecycle methods
  are seeds of the forward search with the entry points, so a method only a handler calls
  is `reachable`; their target flags come from the searches like any method's. With the
  `Application`, fragment, worker and RecyclerView entry points, this makes the `reachable`
  set (the coverage denominator) of a document from this producer larger than one from an
  older producer: never compare the two on `reachable`.
- **Empty-site edges (`EmptySiteEdges`, log `[EmptySiteEdges] added …`).** SPARK resolves
  `x.m()` from the objects `x` may point to, learnt from allocation sites. `this` of an
  activity, fragment, application or service, a ViewModel from a provider, and an injected
  field point to nothing, because the framework, reflection or a DI container creates them,
  so SPARK leaves the site with no edge. At every instance-invoke site of an app method
  still without an edge after `LambdaEdges`, the pass adds an edge to the method a special
  invoke resolves to, or, for a virtual or interface invoke, to the method
  `FastHierarchy.resolveConcreteDispatch` yields on each concrete app class that the class
  the invoke names admits (itself included). Only app callees, only empty sites: a site
  SPARK resolved keeps exactly its edges, and no edge enters library code, so
  `directlyReachesTarget` and `distanceTargets` do not move while `reachable`,
  `reachesTarget` and `targetDistances` grow. It is the class-hierarchy answer, so a dead
  site also gets edges and an interface invoke fans out to every app implementer; the
  counter line and up to 10 `[EmptySiteEdges] fan-out n at …` lines (largest first) show
  the width per run. No fan-out bound is applied. The edges serve reachability, the
  distances and the paths only: after the distances, `RvsecAnalysisClient.run()` removes
  them from the call graph before `analyzeFragments` and the WTG (log `Empty-site edges
  removed before the WTG: N`), so `windows` and `transitions` stay as SPARK and
  `LambdaEdges` make them even with `cgDelegation=true`.
- **What the empty-site edges do not repair: library dispatch.** A call that leaves the
  app and comes back through library code stays lost when SPARK gave the library its own
  empty site: coroutine resumption (`kotlinx.coroutines`), RxJava operators, an executor
  running a `Runnable`, `Collections.sort` calling a `Comparator`, and koin/Hilt registries handing out objects from `java.util` maps whose bodies Soot does
  not load. The pass only fills sites inside app methods; the edge from the library's own
  call site to the app callback is not modelled.
- **Compose UI is not modelled** (no view tree for GATOR to read); it does not break the run.
- **WTG cost can grow where fragment listeners appear for the first time**
  (`com.iyps_158`: 106 s → 1,031 s, WTG stage 3 `CloseWindowEdgeBuilder`); the pre-WTG
  artefact keeps every new section if the time cap hits.
- **Stale internal READMEs** (`client/README.md` describes an old all-in-one client;
  `sootandroid/TestMain` targets the upstream author's paths and is excluded) — trust the
  spec + code, not the in-tree READMEs.
