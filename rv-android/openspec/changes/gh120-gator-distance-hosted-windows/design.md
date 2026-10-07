## Context

The proposal (#120) fixes the producer of the static-analysis artefact, GATOR (`rvsec/rvsec-android/rvsec-gator`, Java, outside the uv workspace), so that the next corpus analysis carries what the explorer needs: a distance from each app method to each target, wrappers that carry their own flags, and the widgets of fragments, dialogs, binding layouts and adapter rows attached to the activity that shows them. The corpus analysis starts on the evening of 2026-10-07; this design is written the same day, after three prototypes and one measurement.

**Prototypes** (git worktrees of `rvsec` at base `4bd7b11a`, nothing committed):

| worktree | content | measured |
|---|---|---|
| `wip/gator-dist` | per-target reverse BFS, lambda edges, an exclusion switch, side-file export | 13 APKs × 2 exclusion modes, validated against the E6 traces |
| `wip/gator-frag` | fragment host map (F1), `Host#Fragment` windows (F2), fragment view flow, ViewBinding `findChildViewById` | 6 APKs: 0 windows/widgets/listeners lost; flagged widgets in the derived artefact 5 → 86 |
| `wip/gator-dlg` | library inflate model (DataBinding, `AppCompatActivity(L)`, builder `setView(int)`), hosted windows, host resolver, binding listener recovery | 11 APKs: 0 (id, host) pairs lost; 146 of 158 targeted absent ids recovered |

They are merged in `wip/gh120-int` (`frag` and `dist` applied cleanly; `dlg` needed two one-line resolutions in `RvsecAnalysisClient.java`); the merge compiles. The implementation starts from that worktree.

**Verdict of the distance experiment (2026-10-07)**, 10 APKs with full output under the campaign environment (`RV_STRIP_BUILD_TYPE_SUFFIX=true RV_PACKAGE_DETECTOR=false`), measures from `m18_distance_validation.py` (thesis folder):
- **Exclusions**: applied before the `Scene` exists, they shrink the call graph (droid_scep 80,025 / 282,789 → 67,518 / 238,046 vertices / edges) and change none of the measures on the 6 APKs where both modes finished; GATOR then crashes on `com.schwegelbin.openbible_46` (`RuntimeException: … androidx.compose.ui.tooling.PreviewActivity is at resolving level SIGNATURES`, the flow graph retrieves the body of a manifest activity) and on `org.quantumbadger.redreader_117`. Owner decision (2026-10-07): remove the inert options.
- **Whole graph vs app subgraph**: identical on every measure (true-handler rank, click lift, no-bind lift). The whole graph is kept (D2).
- **Lambda edges**: of the 12 usable true-handler events (2 APKs), the handler that fired has a finite distance in 3 with the edges and 1 without; on `redreader` 71 wrappers have a reaching body and a non-reaching wrapper without them. Kept (D3).
- **Click lift**: a click on a widget whose handler is within 3 calls of a not-yet-executed target is followed by a new target execution within 3 steps in 9.8 % of 61 clicks (3.6 % of 165 with lambda edges), against 0.2 % for the other ~2,700 clicks. Small counts, one direction.
- **Boundary set B**: on the 12 APKs whose distance pass finished, median 6 methods (0 to 531), median 0.4 % of app methods; the largest, `eu.faircode.email_2322`, holds 531 of 17,250 (3.1 %). Kept as a second target kind (D4).
- **Cost**: the whole distance pass (four graph variants, C and B) took at most 2.8 s per APK (`total_ms`).

## Architecture

```
GUIAnalysis (solver; Flowgraph + FragmentViewFlow + LibraryInflateModel + ViewBinding op node)
   │
   ▼
RvsecAnalysisClient.run
   ├─ LambdaEdges.addTo(Scene call graph)                 ← new, before reachability
   ├─ ReachabilityEngine → ReachabilityIndex (unchanged seeds)
   ├─ TargetDistances.compute(call graph, index)          ← new: C, B, [i,d]
   ├─ FragmentWindows.analyze / HostedWindowExtractor     ← from frag / dlg
   ├─ dropRepeatedOwnedWindows → enrichFromXml            ← new dedupe (D11), then XML attributes
   ├─ ReachabilityEnricher (+ distances)
   ├─ JsonReportWriter: PRE-WTG artefact (reachability + distances + windows incl. FRAGMENT/HOSTED)
   ├─ WTGBuilder (may time out)
   └─ JsonReportWriter: final artefact (+ transitions, complete)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `presto.android.Main.setupAndInvokeSootHelper` | Soot arguments; loses the three `-exclude`, keeps `-no-bodies-for-excluded` (D1) | CLI | Soot args |
| `clients.reach.LambdaEdges` (new, from `DistanceExporter`'s edge code) | Add wrapper → body and single-invoke SAM edges to `Scene.v().getCallGraph()` | Scene | edge count |
| `clients.reach.TargetDistances` (new, from `DistanceExporter`'s BFS) | C, B, one reverse BFS per target to depth 10 over the self-loop-free call graph | call graph, `ReachabilityIndex` | `targets: List<Target>`, `Map<SootMethod, int[][]>` |
| `clients.reach.ReachabilityEnricher` | Carries the distances (`distanceTargets()`, `targetDistances` per method) so the writer stays pure (INV-ANA-30); there is no `ReportModel` class | index, distances | enriched values |
| `RvsecAnalysisClient.dropRepeatedOwnedWindows` | One `FRAGMENT`/`HOSTED` window per host for each distinct widget list (D11) | windows | windows |
| `clients.json.JsonSchema.Keys` / `JsonReportWriter` | Keys `distanceTargets`, `targetDistances`, `kind`; emit in the pre-WTG write | model | JSON |
| `clients.fragment.FragmentHostResolver`, `FragmentWindows` | F1/F2 | solver, resources | `FRAGMENT` windows |
| `clients.hosted.HostedWindowExtractor`, `HostResolver`, `NavGraphUses`, `BindingListenerRecovery` | hosted windows | solver | `HOSTED` windows |
| `gui.FragmentViewFlow`, `gui.LibraryInflateModel`, `Flowgraph.createOpNode` hooks | flow-graph edges and op nodes before solving | Jimple | flow graph |
| `rv_static_analysis/parser/static/static_analysis_parser.py` (`_JK`, `_map_window_type`) | key parity; `FRAGMENT`/`HOSTED` mapping | JSON | domain |
| `rv_android_core/domain/window.py` (`WindowType.HOSTED`) | new enum member | — | — |
| `aperv_tool/tools/aperv/derive_mop_artifact.py` (`_index_reachability`) | exact-join index over every listed method (INV-DRV-09) | `reachability[]` | index |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Per-Target Call-Graph Distance; INV-ANA-73, -74 | `TargetDistances.compute`, `ReachabilityEnricher`, `JsonReportWriter` | `TargetDistancesTest` (synthetic graph: chain, cap at 10, library seed ignored, self 0); `JsonOutputTest` (keys present, omitted when empty) |
| Boundary Targets | `TargetDistances.boundary` | `TargetDistancesTest` (library-only path → B; edge to a target → C, not B) |
| Lambda Wrapper Edges; INV-ANA-77 | `LambdaEdges.addTo` | `LambdaEdgesTest` (wrapper → own body; sibling not linked; SAM single-invoke) |
| Fragment Windows; Fragment View Flow and ViewBinding | `FragmentWindows`, `FragmentHostResolver`, `FragmentViewFlow`, `Flowgraph` hook | acceptance runs (no unit harness for the solver exists); `RvsecAnalysisClientIT` when its APK fixture applies |
| Hosted Windows | `HostedWindowExtractor`, `HostResolver`, `LibraryInflateModel` | acceptance runs |
| INV-ANA-75 (pre-WTG) | call order in `RvsecAnalysisClient.run` | acceptance: `--skip-wtg` artefact contains the same keys/windows as the full one |
| INV-ANA-76 (names, ids) | id ranges; dedupe in `prepareWindows` | `JsonOutputTest`-style check on an acceptance artefact: ids unique, no `DIALOG` with `#` |
| Spinner Items from Array Resources | `SpinnerItemExtractor` (`createFromResource`, `getStringArray`/`getTextArray`), array-id map in `RvsecAnalysisClient` | `SpinnerItemExtractorTest` (synthetic Soot bodies); acceptance on `org.cry.otp_31` |
| Repeated Owned Windows Are Emitted Once | `RvsecAnalysisClient.dropRepeatedOwnedWindows` | `OwnedWindowsTest` (4); acceptance on `github.paroj.dsub2000_217` |
| Repeated Widget Records Are Emitted Once | `RvsecAnalysisClient.dropRepeatedWidgets` | `OwnedWindowsTest` (+2: equal records kept once, differing records kept); acceptance on `org.hwyl.sexytopo_93` and `com.etesync.syncadapter_20700` (distinct content unchanged) |
| INV-ANA-78 / Parser | `_map_window_type`, `WindowType.HOSTED` | `modules/rv-static-analysis/tests/…` parser test; `rv-android-core` enum test |
| INV-ANA-32 | `JsonSchema.Keys`, `_JK` | `JsonSchemaKeysTest`, the Python parity test |
| INV-ANA-79 | default path unchanged where nothing applies | acceptance: content comparison against September on `net.gaast.giggity_769` (no fragment, no binding) |
| MODIFIED Unified … (exclusions) | `Main.java` | grep test in `RvsecAnalysisClientIT` or a `Main` args unit test: no `-exclude` |
| aperv: Widget MOP Flag Derivation; INV-DRV-09 | `_index_reachability` | `modules/aperv-tool/tests/…derive…`: listed non-reaching wrapper stays `none`; absent wrapper still recovered |

## Goals / Non-Goals

**Goals:**
- the four new things in the artefact (distance, boundary, wrapper flags, fragment/hosted windows), all in the pre-WTG write;
- no existing window, widget or listener lost on the test APKs;
- a jar in `rv-android/lib/gator` before the corpus analysis of 2026-10-07 starts.

**Non-Goals:**
- the APE-RV side (reading distances, scoring, launcher order) — change in the `ape` repository;
- passing the distance through the derive to `*.mop.json` — same change, since the wire shape is decided by the consumer;
- the instrumenter handler stamp (#121);
- fragments from reflection, `FragmentFactory`/Hilt, code-built Navigation; fragment → fragment edges (F3) and seeds (F4); DataBinding `android:onClick="@{…}"`; `Dialog.setContentView(int)` on dialogs GATOR does not allocate;
- Compose (no view tree exists for GATOR to read).

## Decisions

**D1. Remove the exclusions instead of making them effective.** Effective exclusions crashed 2 of 13 APKs and changed no measure; making GATOR robust to classes at `SIGNATURES` level touches every pass that calls `retrieveActiveBody`. Removing the arguments keeps the graph every September artefact was built on. The `ExcludeMode` prototype is not ported. `-no-bodies-for-excluded` stays: it is not inert, because it acts on the packages Soot excludes by default (`java.*`, `javax.*`, `sun.*`, …); without it the call graph of `net.gaast.giggity_769` grows from 11,247 vertices / 23,698 edges to 11,286 / 24,472, which would move the September baseline for no measured gain.

**D2. Whole call graph, not the app subgraph.** Same answers on every measure; the whole graph keeps INV-ANA-74 (distance only where `reachesTarget`) and keeps app callbacks invoked from library code (password.monitor: 102 vs 6 methods within 10). Alternative rejected: computing both — doubles the artefact field for no measured gain.

**D3. Lambda edges go into the Scene call graph, before reachability.** The prototype added them to a private graph copy for the distance only. Putting them in the Scene makes `reachesTarget` and the distance agree, lets the derive drop the per-class guess for listed wrappers (aperv delta, owner decision 2026-10-07), and gives `cgDelegation=true` the same edges. Consequence: `reachesTarget` can turn `true` for wrappers and SAM implementations whose body reaches; this is the intended repair, measured in acceptance as a count. The edges also change `reachable`, the coverage denominator: a body reached only through its wrapper becomes reachable once the wrapper is. Measured against September on the final build: `com.afkanerd.deku_83`, `com.etesync.syncadapter_20700`, `com.kolktech.linxshare_22` and `github.paroj.dsub2000_217` unchanged; `com.flauschcode.broccoli_1040400` 271 → 272, `org.hwyl.sexytopo_93` 871 → 872, `com.iyps_158` 522 → 542, `net.gaast.giggity_769` +2; no method went from reachable to unreachable. The iyps increase was not split between the lambda edges and the fragment/ViewBinding models. A coverage comparison with September artefacts therefore compares two denominators.

**D4. B is a second kind of target in the same list.** One list with `kind` keeps one index space for `[i, d]` and lets a consumer ignore `boundary` entries. Alternative rejected: a separate `boundaryTargets` list with its own pair lists — two shapes for one concept.

**D5. Pairs live inside each method entry; methods with no pair carry no key.** The `.apk.json` is not sent to the device; size grows by the number of methods within 10 calls of a target (redreader: 113 rows over 9,333 app methods).

**D6. One window per (host, owner).** `frag` and `dlg` both emit fragment views. `FRAGMENT` wins: after both producers run, a `HOSTED` window whose name equals a `FRAGMENT` window's name is dropped. Both prototypes start window ids at 900000; hosted ids start after the last fragment id.

**D7. `enrichFromXml` keeps annotating the last widget record with a given id**, as in September. `dlg` found that an activity calling both `setContentView(L)` and `DataBindingUtil.setContentView(this, L)` gets two copies of the tree, and the consumer keeps the first, unannotated, copy. Annotating every copy was tried and rejected: it changed `text` on 21 widget records of `net.gaast.giggity_769` against September, because every copy of a shared id name took the text of the last layout declaring that id. Known limit kept: `com.github.cvzi.screenshottile_148` loses `contentDescription` on 4 widgets.

**D8. The side-file export (`RVSEC_DIST_DIR`) is not ported.** It existed for the experiment; the artefact carries the data now.

**D9. The derive's exact-join index holds every listed method** (INV-DRV-09), so a listed wrapper keeps its own `(false, false)`; the class recovery stays for absent wrappers. The rule assumes an artefact from this change's producer: a September artefact lists wrappers with `false` because the old call graph had no wrapper → body edge, so the new derive on it drops correct flags (`org.hwyl.sexytopo_93`: 20 flagged widgets with the old derive, 7 with the new one on the same artefact, 16 with the new derive on the new artefact). Owner decision (2026-10-07): no compatibility guard in the derive (P3); the corpus hand-off states that an APK without a new artefact is never derived from its September artefact.

**D10. Window and widget ids are compared by content in acceptance.** GATOR's node ids follow identity-hash iteration; loading new classes moved 141 ids on giggity in the prototype without changing content.

**D11. One `FRAGMENT`/`HOSTED` window per host for each distinct widget list** (`RvsecAnalysisClient.dropRepeatedOwnedWindows`, called in `prepareWindows` after both producers and before `enrichFromXml`; the first window in emission order is kept). Fragments that share a base class reach the same view objects through the per-class fragment view flow, so every subclass window can carry the same tree: on `github.paroj.dsub2000_217`, 58 of 61 fragment windows held one 124-widget tree, which took the listeners from 54 to 28,238 and the artefact from 1.8 MB to 11 MB. Every consumer folds `Host#Owner` windows into the host's bucket, so the copies added size and nothing else. With the dedupe (2026-10-07): 6 `FRAGMENT` windows, 2,610 listeners, 2.9 MB, and the same derive result (11 flagged widgets before and after).

**D13. Spinner items from array resources** (owner decision 2026-10-07). `SpinnerItemExtractor` gains two item sources: `$a = staticinvoke ArrayAdapter.createFromResource(ctx, id, layout)` binds the array `id` to the adapter local `$a`, and a `String[]`/`CharSequence[]` argument of `new ArrayAdapter(…)` or `addAll(…)` defined by `Resources.getStringArray(id)`/`getTextArray(id)` resolves to the array `id`. The id is resolved to items through a map the client builds once: array name → items from `parseArraysXml` (the parser `android:entries="@array/X"` already uses), and name → id from the app's `public.xml` (`XMLParser.getApplicationIdValue("array", name)`). The extractor receives that map as a function, so it stays testable without resources. Programmatic items are still appended after the XML entries (`unionProgrammaticSpinnerItems`). Evidence: the 5 spinners of `org.cry.otp_31` are all filled with `createFromResource` (`Home.java:145`, `ProfileSetup.java:422, 441, 459, 462, 478`) and get no `entries` today. Spinners filled from runtime data (accounts, folders, computed lists, as in `eu.faircode.email_2322`) stay empty: there is nothing static to read. The extractor still visits activity methods only.

Three fixes were needed for cry.otp to work, all in the same extractor:
- **Non-final `R` fields.** In that app the ids are not constants. They are static field reads (`$i0 = <org.cry.otp.R$array: int SHATypes>`), so every resource id, the `findViewById` one included, is resolved by (type, field name) through the app's resource id map when it is not an int constant.
- **The `findViewById` id is resolved at its own statement.** The compiler reuses the id register: `$i0` holds the spinner id for `findViewById` and is then overwritten with the array id before `setAdapter`. Resolving at `setAdapter` had keyed the items by the array id.
- **Items are keyed by the adapter's creation statement** (its reaching definition), not by the local. One local held several adapters in `ProfileSetup`, and every spinner there had received the union of all of them.

Items are also deduplicated per spinner, because the same spinner is bound in several methods (create and edit flows) to the same array. Result on cry.otp: 5 of 5 spinners carry their own items (3, 3, 3, 40, 2), and windows, widgets and the 255 transitions are equal by content.

At `setAdapter` the spinner takes the items of every creation statement that reaches the adapter local, so an adapter created in both branches of an if/else gives the spinner the items of both (`SpinnerItemExtractorTest.adapterCreatedInBothBranches`). Requiring a single reaching definition left such a spinner with no items, where the September producer, which keyed items by the local, gave the union.

**D14. Equal widget records are emitted once, in every window** (`RvsecAnalysisClient.dropRepeatedWidgets`, last step of `prepareWindows`, after `enrichFromXml` and `unionProgrammaticSpinnerItems`; owner decision 2026-10-07). A window whose owner builds the same layout from several methods gets one view root per method and one widget record per root: in `org.hwyl.sexytopo_93` each of the 13 `Host#LegDialogs` windows listed the 39-id leg form three times (2,642 records, 3,071 listeners; after: 2,118 and 2,109, the same 2,118 distinct records). Equality is `Map.equals` on the record (every value is a string, number, list or map), so records that differ in any field stay, including the annotated and unannotated copies of D7. The step covers every window type, `ACTIVITY` included: the September producer's activity windows hold 3 to 12 exact copies on the APKs measured, and they carry no content either. Consequence: a content comparison with September that counts multiplicity reports those copies as lost; comparisons are by distinct content. Alternative rejected: dropping only in `FRAGMENT`/`HOSTED` windows — it keeps copies that say nothing for the sake of a byte-level baseline that INV-ANA-79 already gives up (node ids move).

**D12. B keeps constructors and static initializers.** On `cryptoapp`, B holds activity constructors (`MainActivity.<init>` …): library initialization code that reaches a target through SPARK. Owner decision (2026-10-07): no `<init>`/`<clinit>` filter; `kind: "boundary"` lets a consumer ignore them.

## API Design

### `LambdaEdges.addTo(CallGraph cg, Map<SootClass, List<SootMethod>> appMethods) -> int`
Pre: SPARK call graph built. Post: for each lambda-class method and each single-invoke SAM implementation, a `new Edge(m, stmt, callee)` exists for every app callee its body invokes (the edge kind follows the invoke statement, not a fixed `VIRTUAL`); returns the number of edges added; edges already present are not duplicated. Errors: a body that cannot be retrieved is skipped and logged.

### `TargetDistances.compute(CallGraph cg, ReachabilityIndex idx, appClasses, targets) -> TargetDistances`
The BFS core works over a callee → callers map, so it is tested without Soot; the Soot entry builds that map from the call graph.
Pre: reachability computed. Post: `targets()` = C sorted, then B \ C sorted; `pairs(m)` sorted by target index, every `d ≤ 10`; library methods never appear as targets. Errors: none expected; the caller catches `RuntimeException`, logs, and writes the artefact without the two keys.

### Python
- `WindowType.HOSTED = 6`; `_map_window_type("HOSTED") -> WindowType.HOSTED`.
- `_JK.DISTANCE_TARGETS = "distanceTargets"`, `_JK.TARGET_DISTANCES = "targetDistances"`, `_JK.KIND = "kind"` (if `kind` is not already declared).
- `derive_mop_artifact._index_reachability(reachability)`: `by_signature` holds every method; `lambda_by_class` and `activity_classes` unchanged.

## Data Flow

APK → apktool resources + Soot (no exclusions) → flow graph with fragment/binding/inflate models → solver → lambda edges into the call graph → reachability → distances (C, B) → fragment and hosted windows → pre-WTG JSON (everything above) → WTG → final JSON (+ transitions, `complete`). Downstream: `rv-static-analysis` parser (types mapped), derive (flags; distance not yet propagated).

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `RuntimeException` in distance pass | `TargetDistances` | catch in client, log `[RvsecAnalysisClient]` | artefact without distance keys |
| `RuntimeException` in fragment/hosted pass | `FragmentWindows`, `HostedWindowExtractor` (constructor included: it indexes every app body through `HostResolver`) | catch around the pass in `prepareWindows`, log | artefact without those windows; reachability and the other windows are written |
| body retrieval failure | `LambdaEdges`, models | skip method, log (INV-ANA-17 pattern) | fewer edges |
| GATOR OOM / timeout | JVM, Python `Command` | unchanged | pre-WTG artefact carries every new section |

## Risks / Trade-offs

- **Listener over-attribution from abstract base activities** → `dlg` hosts an owner on every subclass (sexytopo listeners 137 → 3,071). Measured on 2026-10-07: in sexytopo, `LegDialogs` is opened from `SexyTopoActivity.onOptionsItemSelected`, the base of all 13 activities, and 12 of them carry the same 14-item options menu, so one hosted window per activity follows the code; the excess was the threefold repetition of the form inside each window, removed by D14 (3,071 → 2,109 listeners). The derive's collision rule keeps the strongest flag; `MAX_HOSTS = 20` bounds the worst case.
- **Wall time** → the fragment and hosted passes and the extra flow-graph edges cost time (password.monitor 204 → ~400 s under a shared machine, not isolated). The distance pass is ≤ 3 s. Acceptance records seconds per APK; the corpus run keeps the September time-cap policy.
- **WTG cost where listeners appear for the first time (accepted)** → `com.iyps_158`: 106 s in September, 1,031 s with this change. Run with each prototype on 2026-10-07: `dist` 126 s, `dlg` 107 s, `frag` 991 s, so the fragment view flow and ViewBinding model cause it. Thread samples put the time in WTG stage 3 (`CloseWindowEdgeBuilder`), one `ConstantAnalysis` per callback, hot in `QueryHelper.backwardReachableNodes`; the APK went from 0 to 741 listeners and from 9 to 153 transitions. It did not repeat on the other 14 APKs run that day, three of them with the same profile (ViewBinding, 0 listeners in September: pixiv 68 → 57 s, bibleverse 76 → 81 s, lnaddr2invoice 182 → 137 s); 15 of the 163 corpus APKs have that profile. An APK like iyps that reaches the cap keeps every new section in the pre-WTG artefact (INV-ANA-75) and loses only the WTG transitions. No change to the WTG in this change.
- **`reachesTarget` changes** (D3) → reported as counts per APK in acceptance; these are wrappers whose own body reaches.
- **Deadline** → tasks are grouped so that the GATOR jar can be handed to the corpus analysis before the Python/derive/spec groups finish; the derive change does not affect the artefact.
- **Heap** → faircode and bitbanana needed more than 12 g under 10 parallel JVMs in the experiment (September also needed a 32 g round for some APKs). On 2026-10-07 seven concurrent GATOR JVMs with 144 GB of summed `-Xmx` froze the 123 GB host. The hand-off keeps the September ladder within a summed budget of about 80 GB: 6 workers × 12 g, then 2 workers × 32 g for the APKs left without an artefact.
- **September artefacts and the new derive** → see D9; handled by a rule in the hand-off, not by code.
- **Hosted windows on a concrete base activity outside the manifest (known limit)** → `HostResolver.hostsOf` keeps a concrete app activity as its own host, while `FragmentHostResolver.launchedActivities` maps a base activity to its subclasses declared in the manifest. A `HOSTED` window opened from a concrete base activity that is not declared is named after a class that never runs, so the explorer never matches it. No content is lost against September (these windows are new). Measured after the corpus run: the `HOSTED` windows whose host is not in `components.activities`; a follow-up change aligns the two resolvers if the count matters.
- **A failure of the lambda-edge pass is only logged** → `LambdaEdges.addTo` runs inside a catch that prints `Lambda edges failed`; the artefact then lists wrappers with their SPARK flags, and the derive trusts them (INV-DRV-09) instead of falling back to the class recovery. None of the 14 APKs of 2026-10-07 hit it. After the corpus run, the logs are searched for that line; a follow-up change adds a marker to the artefact if any APK is affected.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | `TargetDistances`, `LambdaEdges`, key parity | synthetic Soot scenes / plain graphs, JUnit | ~10 |
| Unit (Python) | parser mapping, `WindowType.HOSTED`, `_JK` parity, derive index | pytest `--import-mode=importlib -o "addopts="` | ~6 |
| Acceptance (host) | planned: 9 test APKs + dsub2000, faircode, bitbanana, redreader + avnc, broccoli, screenshottile, sexytopo, keepalive, aelf, fosdem. Run on 2026-10-07 on small APKs chosen per feature: giggity, cry.otp, treehouses, dsub2000, sexytopo, keepalive, etesync (DataBinding), broccoli (DataBinding + Navigation), iyps (Navigation + ViewBinding), linxshare (Compose only), deku (mixed), pixiv, bibleverse, lnaddr2invoice (ViewBinding) | full GATOR under the campaign env; content comparison with September (no window, widget, (id, host) pair or listener lost on any of them); derive runs; distances equal to the prototype `DistanceExporter`'s `full_lambda` rows, re-run after the reboot (treehouses 153 pairs, cry.otp 13, giggity 1); dsub2000 `--skip-wtg` and a JVM killed inside the WTG carry the same new sections as the full artefact. Report: `docs/20261007_gh120_verificacao_final.md` | 14 APKs; faircode, bitbanana, redreader, openbible, fosdem not run |
| Build | reactor | `mvn clean install -DskipMopAgent -DskipTests -o` (JDK 21) in the main checkout after merge, then GATOR module tests | 1 |

## Open Questions

- None blocking. The corpus scope (163 APKs, owner decision 2026-10-07) and its time policy are outside rv-android and go in the hand-off file.
