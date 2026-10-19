## Context

The proposal gives the evidence: 63 app methods that call the JCA ran on the device while GATOR marked them not `reachable`. They trace to three defects: A, the callback complement that does not propagate; B, the missing Application and Fragment entry points; and C, call sites SPARK leaves without an edge. The proposal also asks for distance paths, for the analyser's stand-alone use. The requirements cited are FR04, FR06, FR12, NFR04, NFR05 and NFR08.

Current state of the producer (`rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/`):

- `RvsecAnalysisClient.run()` adds the lambda edges (`LambdaEdges.addTo`, `:158`), runs `new ReachabilityEngine(…).run()`, then `computeDistances` (`TargetDistances.compute`, `:1552`), and writes the document through `json/JsonReportWriter` twice: pre-WTG and final.
- `reach/ReachabilityEngine.run()` builds the JGraphT view of `Scene.v().getCallGraph()`. It runs the forward search from `RvsecAnalysisClient.getEntryPoints(output)` (`:415`), then the direct set (call graph ∪ bytecode scan) and the reverse search. Last it calls `RvsecAnalysisClient.complementWithCallbacks` (`:885`), which adds the callbacks to `reachableSet` after the forward search and copies flags from their direct callees.
- `getEntryPoints` covers activities (lifecycle handlers plus public/protected methods) and manifest services, receivers and providers. `XMLParser`/`DefaultXMLParser` read activities, services, receivers and providers from the manifest (`DefaultXMLParser.java:346`), but not `<application android:name>`.
- `reach/TargetDistances.compute` builds a callee → callers map of `HashSet`s, so the order in which a search visits callers follows hash iteration. It runs one `reverseBfs` per target (`DIST_MAX = 10`), keeping a depth per app method. `compact(int[][])` applies INV-ANA-85.
- `JsonReportWriter.write` writes the scope members, `distancePairs` (compact), `distanceTargets`, `components`, `reachability` (through `RvsecAnalysisClient.writeReachabilitySection`, `:1691`), `windows`, `transitions` and the sentinel. Client parameters are read with `Configs.getClientParamCode("<name>=")`, as `skipWtg()` and `fullOutput()` do (`:300`, `:310`).
- `FragmentHostResolver` (`fragment/FragmentHostResolver.java:103`) and `sootandroid/.../gui/FragmentViewFlow.java:45` each hold a private copy of the same three fragment base names (`android.app.Fragment`, `android.support.v4.app.Fragment`, `androidx.fragment.app.Fragment`). The client depends on `sootandroid`, so the shared declaration goes there.

Consumer side:
- `modules/rv-android-core/src/rv_android_core/util/analysis_document.py` is the streaming reader. `PairPolicy.DROP` serves the parser; `PairPolicy.reduce` serves the derive and the converter.
- `modules/rv-static-analysis/src/rv_static_analysis/config.py` builds the GATOR command (`skip_wtg`, `full_output` at `:114–:123`, `:418–:422`).
- `compact.py` is the offline converter. `parser/static/static_analysis_parser.py` holds `_JK`.

## Architecture

```
Soot/SPARK call graph
   │  LambdaEdges.addTo            (INV-ANA-77, unchanged)
   │  EmptySiteEdges.addTo         (C, new: edges at sites SPARK left empty, app callees only)
   ▼
ReachabilityEngine.run()
   seeds = getEntryPoints(output)          (+ Application, + Fragment subclasses: B)
         ∪ collectCallbacks(output)        (A: callbacks are seeds; the post-search complement is gone)
   reachable   = forwardBfs(graph, seeds)
   direct      = CG direct callers ∪ bytecode scan            (unchanged)
   reachesTgt  = reverseBfs(graph, targets ∪ direct)          (unchanged)
   ▼
TargetDistances.compute(...)  callers sorted by signature; pass 1 = distances (unchanged values)
   ▼
[distancePaths=true]  TargetDistances.paths(written pairs)    pass 2, one target at a time
   ▼
JsonReportWriter: … reachability, [pathMethods, distancePaths], windows, transitions, complete
   │
   ├─ StaticAnalysisParser / parsed copy ─┐ read_analysis_document drops pathMethods
   ├─ aperv-tool derive ──────────────────┘ and distancePaths under every PairPolicy (INV-ANA-97)
   └─ rv-static-analysis compact: refuses an input carrying distancePaths
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `reach/EmptySiteEdges.addTo(CallGraph, Map<SootClass, List<SootMethod>>, List<Edge>)` (new) | Add edges at instance-invoke sites of app methods with no outgoing edge, to the concrete app callees by dispatch over the class the invoke names | call graph, app classes, caller-owned list | the edges added, in the list (and log counters) |
| `RvsecAnalysisClient.collectCallbacks(GUIAnalysisOutput)` | The callback set the complement used to build, as a set, with no side effect | GATOR output | `Set<SootMethod>` |
| `ReachabilityEngine.run()` | Seed the forward search with entry points ∪ callbacks; no post-search complement | as today | `ReachabilityIndex` |
| `RvsecAnalysisClient.getEntryPoints` | + Application lifecycle and public/protected methods, + Fragment subclasses' public/protected methods | GATOR output, app classes | `Set<SootMethod>` |
| `XMLParser.getApplicationClassName()` / `DefaultXMLParser` | Read `<application android:name>`, resolved like activity names | manifest | `String` or `null` |
| `FragmentViewFlow.FRAGMENT_BASES` (sootandroid, made public) | The one set of fragment base names, read by `FragmentHostResolver` (whose copy is deleted) and `getEntryPoints` | — | names |
| `TargetDistances.compute` | Callers in signature order (lists, not sets); distances as today | call graph, index, targets | `TargetDistances` |
| `TargetDistances.paths(Predicate written)` (new) | Pass 2: per target with a written pair, repeat the search with predecessors, emit the steps of the chains of written pairs | written-pair selection | `DistancePaths` (method table + steps) |
| `RvsecAnalysisClient.distancePaths()` | Read `-clientParam distancePaths=` | client params | `boolean` |
| `JsonReportWriter` | Write `pathMethods` and `distancePaths` after `reachability` when enabled, in both writes | `DistancePaths` | document |
| `JsonSchema.Keys.PATH_METHODS`, `DISTANCE_PATHS` + `_JK` | Member names on both sides (INV-ANA-32) | — | — |
| `analysis_document.read_analysis_document` | Skip the two path members under every policy | document | dict without them |
| `RVStaticAnalysisConfig.distance_paths` + `--distance-paths` | `-clientParam distancePaths=true` | CLI | GATOR command |
| `rv_static_analysis.compact` | Refuse an input carrying `distancePaths` | full document | exit 1 |
| `rv_static_analysis.path_query` (new) + `path` subcommand | Stream a document with paths and print one method's chains (D12) | document, method, optional target | stdout lines, exit status |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|-------------|---------------|------|
| Callbacks Seed the Reachability Search, INV-ANA-94 | `ReachabilityEngine.run`, `collectCallbacks`; `complementWithCallbacks` deleted | `ReachabilityBfsTest` (synthetic graph: a method two calls below a callback is reachable); `ReachabilityEngineCallbackSeedTest` (flags equal to the complement's output on a synthetic graph) |
| Framework-Created Component Entry Points, INV-ANA-95 | `getEntryPoints`, `XMLParser.getApplicationClassName`, `FragmentViewFlow.FRAGMENT_BASES` | `ApplicationNameParseTest` (manifest with and without `android:name`, relative and absolute names); `EntryPointsTest` (Scene idiom of `CallSiteMatchPolicyTest`: Application, Fragment, ListenableWorker, Adapter and ViewHolder subclasses; a ViewModel subclass not taken) |
| Path Query Subcommand, INV-ANA-98 | `rv_static_analysis.path_query`, `__main__.py` | `test_path_query.py`: chain printed for every pair and for `--target`; refusals; a broken chain detected; a method with no pair prints nothing |
| Empty-Site Edges, INV-ANA-96 | `EmptySiteEdges.addTo`, call in `RvsecAnalysisClient.run` after `LambdaEdges.addTo` | `EmptySiteEdgesTest` (Scene idiom of `LambdaEdgesTest`): `this` call, field receiver, special invoke, interface fan-out to app implementers only, resolved site untouched, static invoke untouched, library callee not added |
| Per-Target Call-Graph Distance (callers in signature order) | `TargetDistances.compute` | `TargetDistancesTest`: the existing expectations hold unchanged (distances do not depend on order) |
| Distance Paths, INV-ANA-90, -91, -92, -93 | `TargetDistances.paths`, `JsonReportWriter`, `distancePaths()` | `TargetDistancesPathsTest` (string vertices: chains of length `d`, tie by signature, compact keeps only kept pairs' chains, library vertex on a chain, `d = 0` has no step); `DistancePathsEmissionTest` (writer: members absent when off, present after `reachability` in both writes when on) |
| Keys parity (INV-ANA-32) | `JsonSchema.Keys` + `_JK` | existing `tests/parity/test_json_keys.py` |
| Streaming Read (INV-ANA-80, INV-ANA-97) | `analysis_document.py` | `test_analysis_document.py`: both policies drop the members; the parser's model is equal with and without them; the parsed copy lacks them |
| Offline Conversion (refusal) | `compact.py` | `test_compact_converter.py`: exit 1, message, no output file |
| `distance_paths` option | `config.py`, `__main__.py` | `test_config.py`: the parameter appears only when set |
| End to end | jar on six small APKs, before and after | group 7 of `tasks.md` |

## Goals / Non-Goals

**Goals:**
- Repair A, B and C so that the 63 measured cases are explained by the document, as far as the call graph allows.
- Give the stand-alone analyser a deterministic, verifiable call path for every written distance, at no cost when it is off.
- Keep every campaign reader's output a function of the fields the repairs change, and nothing else. The path members are invisible to them.

**Non-Goals:**
- Models of library dispatch: coroutine resumption, koin/Hilt registries, `Executor`, `Collections.sort`, RxJava. C repairs the edges among app methods; a call that leaves the app and comes back through library code without bodies stays lost.
- Library-invoked callbacks in the derive's `handlers` table, the instrumentation stamp, and GATOR's listener on `#OptionsMenu` menu items. The stamp A/B of 2026-10-19 decides those (`dexlib2` and `aperv` sessions).
- Reducing the paths of a full document offline.
- The path's continuation inside library code for `boundary` targets: a path ends at the app target, as the distance does (decided 2026-10-19).
- `ViewModel` as an entry point (D8).
- Re-analysing any corpus, or changing the Docker image, the APE-RV jar or the replication package.

## Decisions

**D1 — Paths in two top-level members, not inside the pairs.** `aperv-tool`'s `_read_pairs` keeps an entry only when it is a two-element list of integers. A third element in each pair would make every pair look like producer noise and the derive would drop all of them without an error. A per-method member would not cover library methods, which have no `reachability` entry. The members are a method table and a flat list of `[i, v, n]` steps, so a step costs three small integers and a method's signature is written once.
Alternatives:
- `[i, d, next]` pairs — breaks the derive, as above.
- the whole chain inline per pair — sums `d` per pair, with no sharing between pairs that run through the same methods.

**D2 — Steps, not chains.** A step is the predecessor that a breadth-first search records. The chains of all written pairs share their tails, and a list of steps stores each tail once. A reader rebuilds a chain by following `n` from the method until it reaches the target, `d` steps later (INV-ANA-91).

**D3 — A second pass, one target at a time.** The steps a compact document keeps depend on which pairs survive the rank rule, and that needs every target's search first. Recording predecessors in the first pass would hold one entry per visited method per target, library methods included, for the whole run. The second pass repeats only the searches of targets named by a written pair, holds one target's predecessors at a time, and emits that target's steps before moving on. The cost is at most a second distance pass, paid only with `distancePaths=true`.
Alternative: one pass with all predecessors kept — memory proportional to the full pair count plus library vertices, which on `eu.darken.sdmse_10705000` would be of the order of its 9.34 GB full document.

**D4 — Callers in signature order.** `compute` turns each callers set into a list sorted by signature once, when it builds the map. A breadth-first level does not depend on the order, so every distance and every pair stays as it is. What the order fixes is which equally short path the search reaches first, which the steps record (INV-ANA-92). Without it, two runs over the same graph could write different steps. Sorting costs one `O(E log E)` pass, the same in both passes.

**D5 — Paths off by default.** The campaigns read no path, and the readers would only skip them. With the parameter off, the document is the one the same jar writes (INV-ANA-90), so the compact default and the converter's byte identity (INV-ANA-87) keep holding for every document the campaigns produce.

**D6 — The converter refuses a document with paths.** Reducing a full document's steps to the chains of the kept pairs would need, per target, every step of that target in memory and a second walk over them. The converter would grow a second reduction for a use (stand-alone analysis) where GATOR can simply be run in compact mode with `distancePaths=true`. The refusal is one check and one message.
Alternative: a per-target closure inside the converter, kept for the case where only a full document with paths exists and GATOR cannot run again.

**D7 — Callbacks as seeds; the complement is deleted.** The flags that the complement copied onto callbacks are produced by the searches already:
- a callback with a call-graph edge to a target is a vertex with an edge to a target, so `findDirectTargetCallers` finds it;
- a callback that reaches a target is a vertex the reverse search reaches.

So the post-search step adds nothing to `reachesTarget` or `directlyReachesTarget`, and its only remaining effect, marking callbacks reachable, is what seeding does in full. It is deleted (P3). A test pins the flag equality on a synthetic graph before the deletion. The end-to-end check of group 7 compares the flags on six APKs with C disabled.

**D8 — Fragment entry points by hierarchy, every app subclass.** An entry point is a method the runtime may call. Whether GATOR finds the activity that hosts a fragment is a property of GATOR's resolution, not of the app, and the hosting map exists to build windows. Taking every app subclass of the three base classes is simple and does not inherit the host resolver's limits. Public and protected methods follow the rule already used for activities, which covers `onCreateView`, `onViewCreated`, `onResume` and the other lifecycle methods androidx declares public.

The same reasoning adds two kinds the author included on 2026-10-19:
- `ListenableWorker` subclasses, through `doWork` and `startWork` only. WorkManager calls those two, and a worker's other public methods are its own API, not entry points.
- RecyclerView `Adapter` and `ViewHolder` subclasses, through their public methods. RecyclerView calls them while a list is shown. The investigation found adapters among the roots of the 63, for example `EntryHolder.getOtp` in aegis.

Both exist in androidx and in the support library (`android.support.v7.widget.RecyclerView`). The names are matched as the fragment bases are, by superclass name.

`ViewModel` is left out. It runs only when a screen requests it, and C restores the screen's call into it. Taking ViewModels by hierarchy would also mark ones that no screen uses.

**D9 — Application by the manifest name, the lifecycle plus public/protected methods.** Only the class named in `<application android:name>` is instantiated by the runtime. Other subclasses of `android.app.Application` in the APK, typically in libraries, are not. The lifecycle names (`onCreate`, `onTerminate`, `onConfigurationChanged`, `onLowMemory`, `onTrimMemory`, `attachBaseContext`) are listed for the case where they are not public, matching how services list theirs.

**D10 — Empty-site edges: empty sites only, app callees only, dispatch over the class the invoke names.**
- *Empty sites only.* The pass never touches a site SPARK resolved, so no SPARK answer is widened.
- *App callees only.* Library callees would let the pass add edges into androidx or Kotlin code. That would move `directlyReachesTarget` and `distanceTargets` through the boundary set, and it would fan out without bound.
- *Dispatch over the named class.* Dispatch uses `FastHierarchy.resolveConcreteDispatch` from the class the invoke instruction names (`ref.declaringClass()`) and from each concrete app subtype. javac and kotlinc name the receiver expression's static type there; a shrinker that rebinds the member to a supertype only widens the fan-out, it never drops an edge. This is the class-hierarchy answer, restricted to what an app method can call. A special invoke goes to its resolved method.
- *Placement.* The pass runs after `LambdaEdges`, so a wrapper site `LambdaEdges` filled is no longer empty.
- *Kept out of the WTG.* `addTo` puts each edge it adds into a list the caller owns, so the edges added before a mid-pass failure are known too, and `run()` removes them from the call graph after the distances, before `analyzeFragments` and the WTG. The path pass runs after the removal and still sees them, through the callers map `TargetDistances` kept; `run()` then releases that map (`releaseCallers`), so it is not held through the WTG. The default WTG keeps its own call graph (INV-ANA-21), but with `cgDelegation=true` it reads the Soot graph. Group 6 measured that case with the edges left in: the WTG ran up to 12 times longer (freeotp client 40 s → 269 s, 3.8 s of it outside the WTG; wifianalyzer 29 s → 348 s), and giggity's transitions went from 431 to 1,622, real ones (clicks that call `showItem`) mixed with false ones (`EventDialog$ShareButton.onClick → ScheduleItemActivity`, through a 14-way `Runnable.run` dispatch). The author decided on 2026-10-19 that the WTG stays as it is; a WTG built on these edges is a change of its own.

Alternatives:
- generating a dummy main with allocations for components (the FlowDroid approach) — rebuilds the whole points-to solution, with a far larger effect and cost;
- full CHA for every app site — widens sites SPARK resolved precisely.

**D12 — `path` reads in a pass of its own.** `read_analysis_document` must keep dropping the path members (INV-ANA-97). So the subcommand runs its own ijson event pass. It keeps `distanceTargets`, `pathMethods`, `distancePaths`, and the one method entry it was asked about. Everything else it skips. It indexes the steps by `(i, v)` and follows them `d` times per pair, so a broken chain is detected instead of printed short. Its memory is the method table plus the steps, small in compact mode. In full mode with paths it is as large as the steps, which is the operator's choice.
The converter needs only to know that the members were there, so the reader reports it without keeping them: `read_analysis_document` takes a keyword-only `dropped_paths: set[str] | None = None` and adds to it the names of the path members it dropped. Its return value and its behaviour without the argument do not change, so the campaign readers are untouched.
Alternatives:
- a reader option in `analysis_document` that keeps the members — it widens a contract that two campaign readers depend on, for a tool that is not in the campaign path;
- `json.load` — not viable for the documents this tool targets.

**D11 — No switch for A, B or C.** They repair defects; a document with the defects is not a configuration anyone needs. A document produced before the change stays readable and is simply not comparable on the changed fields (the proposal's BREAKING note).

## API Design

### `EmptySiteEdges.addTo(CallGraph cg, Map<SootClass, List<SootMethod>> appClasses, List<Edge> added)`

- Preconditions: SPARK and `LambdaEdges.addTo` have run on `cg`; `appClasses` is the client's app-class map.
- Postconditions: INV-ANA-96 holds. `added` holds every edge added, each appended as it enters `cg`, and the caller removes them from `cg` before the fragment windows and the WTG. One log line gives instance-invoke sites, empty sites, edges added, bodies skipped and the largest fan-out at one site.
- Errors: a body that cannot be retrieved (`RuntimeException`) is skipped and counted; a failure of the whole pass is caught by the caller, logged, and the run continues on `cg` as it stands, with the edges already in `added` removed before the WTG like the others.

### `RvsecAnalysisClient.collectCallbacks(GUIAnalysisOutput output) -> Set<SootMethod>`

- Postcondition: the activity lifecycle handlers, the event handlers of every GUI object under every activity root, and the Service/Receiver/Provider lifecycle methods. No state is changed.

### `XMLParser.getApplicationClassName() -> String`

- Returns the fully qualified name from `<application android:name>`, resolved against the manifest package by `Helper.getClassName` as activity names are; `null` when the attribute is absent or empty (an empty name would make `getClassName` throw and abort the whole manifest read).

### `TargetDistances.paths(BiPredicate<V, int[]> written) -> DistancePaths<V>`

- Precondition: `compute` has run; `written.test(m, pair)` is true exactly for the pairs the output mode writes on `m`. Full mode passes every pair; compact mode tests membership in `compact(pairs(m))`.
- Postconditions: INV-ANA-91, -92 and -93 hold for the returned steps. `DistancePaths` exposes `methods()`, the sorted signatures, and `steps()`, the `int[3]` triples sorted by `(i, v)`.
- Cost: one reverse search per target named by a written pair; memory for one target's predecessors at a time plus the emitted steps.
- `releaseCallers()` drops the callers map, which only `paths` reads; afterwards `paths` throws `IllegalStateException`, and the targets, kinds and pairs stay readable.

### `RVStaticAnalysisConfig.distance_paths: bool = False`

- When `True`, `get_tool_command` appends `-clientParam distancePaths=true`. `analyze` and `batch` expose `--distance-paths`.

## Data Flow

1. Soot builds the SPARK graph. `LambdaEdges.addTo` and then `EmptySiteEdges.addTo` extend it.
2. `ReachabilityEngine.run` builds the JGraphT view. It searches forward from entry points ∪ callbacks, computes the direct set, and searches in reverse from targets ∪ direct. The index is published immutable.
3. `TargetDistances.compute` sorts callers, builds the target list and runs the distance searches, producing the same values as before for the same graph.
4. With `distancePaths=true`, `TargetDistances.paths` runs the second pass with the mode's written-pair predicate. It returns before the pre-WTG write, so a WTG timeout keeps the paths (as INV-ANA-75 keeps the distances).
5. `run()` removes the empty-site edges from the call graph, so the fragment windows and the WTG see the graph SPARK and `LambdaEdges` built.
6. `JsonReportWriter` writes `reachability`, then `pathMethods` and `distancePaths` when enabled, then `windows` and the rest. It does the same in the final write.
7. Campaign readers stream the document and skip the two members. Stand-alone readers follow the steps.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `RuntimeException` retrieving a body | `EmptySiteEdges` | skip the method, count it | none needed; its sites keep SPARK's edges |
| `RuntimeException` in the whole edge pass | `EmptySiteEdges.addTo` | caught in `run()`, logged, as for `LambdaEdges` | reachability runs on the graph as it stands; the edges already added are removed before the WTG |
| Application class absent from the Scene | `getEntryPoints` | log a warning, as for services | entry points from the other kinds |
| `RuntimeException` in the path pass | `TargetDistances.paths` | caught, logged | document written without `pathMethods`/`distancePaths` |
| Input carries `distancePaths` | `rv-static-analysis compact` | exit 1, one line on stderr naming the input | run GATOR in compact mode with `distancePaths=true` |

## Risks / Trade-offs

- [C over-approximates] Dead sites and wide interfaces receive edges, so `reachesTarget` and the distances can grow beyond what can run. → The pass logs the largest fan-out per run. Group 7 measures edges added, the growth of `reachesTarget` and of the pairs, and the fan-out on six APKs before the jar is installed. The numbers go into the change's report for the author to judge.
- [C and A/B make documents incomparable] Coverage denominators and derived artifacts move. → The BREAKING note. The campaigns of Study 03 keep their documents, and the jar in `rv-android/lib/gator/` is replaced only by an explicit install.
- [The path pass costs a second distance pass] → Paid only with `distancePaths=true`. Group 7 measures it.
- [Full mode with paths is large] One step per written pair's chain element. → Off by default. Its size is measured in group 7 on the six APKs, not extrapolated.
- [Fragment entry points by hierarchy include fragments no screen hosts] Such a fragment's methods become `reachable` without being reachable in practice. → Accepted (D8); the alternative inherits the host resolver's gaps.
- [A step through a reduced intermediate] In compact mode a chain can pass through a method whose own pair for that target was reduced away. → Stated in the requirement; the chain is still complete (INV-ANA-91).

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | `EmptySiteEdges` cases; callback seeding; entry points; manifest name; distances unchanged by order; path steps | Soot Scene idiom of `LambdaEdgesTest`/`CallSiteMatchPolicyTest`; string-vertex graphs for `TargetDistances` | ~25 |
| Unit (Python) | reader drops the members under both policies; config parameter; converter refusal; `path` subcommand output and refusals | pytest with small JSON fixtures | ~14 |
| Parity | `JsonSchema.Keys` ↔ `_JK` | existing `tests/parity/test_json_keys.py` | existing |
| End to end | jar before/after on `cryptoapp.apk` and five corpus APKs that analyse in 1–3 min (`org.fedorahosted.freeotp_48`, `org.cry.otp_31`, `net.gaast.giggity_769`, `com.vrem.wifianalyzer_71`, `systems.sieber.droid_scep_7`). `app.maskan.chat_90` and `com.kin.easynotes_14` were dropped by the author on 2026-10-19: each spends about 30 min in Soot and SPARK. Their scenarios stay covered by unit tests only; paths on and off; compact and full | GATOR runs in parallel within the heap budget; comparison scripts | 6 APKs × 3 configurations |

## Open Questions

The author settled four questions on 2026-10-19.

Decided after group 6:
- **Fan-out bound for C: none.** The author decided on 2026-10-19 that no cap is applied. Group 6 measured the largest fan-out per APK: 41 in `com.vrem.wifianalyzer_71`, at `kotlin.jvm.functions.Function1.invoke` sites; 14 (`Runnable.run`) in giggity; 12 (`View$OnClickListener.onClick`) in freeotp. At sites whose named type is an app class it is 1–8. `reachesTarget` grew from 1 to 53 in giggity and from 36 to 62 in freeotp (`experimento-gtpaths/RELATORIO.md` §4). With the edges kept out of the WTG they affect only `reachable`, `reachesTarget` and the distances, and a cap would drop real callees by an arbitrary count.

Decided:
- **Other framework-created kinds:** `ListenableWorker` (`doWork`/`startWork`) and RecyclerView `Adapter`/`ViewHolder` are entry points; `ViewModel` is not (D8).
- **Path tail inside the library:** not in this change; a path ends at the app target.
- **A query tool:** the `path` subcommand (D12).
