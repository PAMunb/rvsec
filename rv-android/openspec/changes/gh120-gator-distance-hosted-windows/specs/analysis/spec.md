## Purpose

The static analysis exists to tell the explorer, before it acts, which parts of the app lead to a monitored operation. Until this change, GATOR answered one question per method — "does this method reach a target?" — and attached widgets only to activities, menus and the dialogs it allocates itself. In Study 03 (E6) that answer saturated: 41 % of handlers reach some target, so the flag does not separate a widget one call away from a monitored operation from a widget eight calls away. The attachment was also too narrow: 17.0 % of clicks landed on a resource id GATOR never emitted, and in 53 % of those the owner was app code GATOR did not model — fragments, DialogFragments, adapters and binding layouts.

This change adds three things to the `.apk.json`, all computed from state that exists before the window transition graph (WTG) is built:

1. **Distance per target.** For each direct caller `c` of a monitored operation in the app (the set C), and for each app method `b` that hands control to library code which reaches a monitored operation without returning to the app (the boundary set B), a reverse breadth-first search over the call graph records, for every app method `m`, the number of call edges from `m` to the target, up to `DIST_MAX = 10`. The artefact carries the targets as an ordered list, each with its kind, and, per app method, the pairs `[i, d]` for the targets within reach. A consumer can then rank widgets by how close their handlers are to a not-yet-exercised target instead of reading a saturated boolean.
2. **Lambda wrapper edges.** A D8/desugar lambda wrapper (`X$$ExternalSyntheticLambdaN`) or a single-call function object forwards to one body, but SPARK may give the captured receiver no points-to set, leaving the wrapper without an edge to that body. The call graph used for reachability and distance gains these edges, so the wrapper carries its own flags and distance.
3. **Fragment and hosted windows.** Fragment views, dialog bodies, DialogFragment views, adapter rows and binding layouts are emitted as windows named `Host#Owner`, where `Host` is the activity the user sees them on. Every consumer already folds a `Host#…` window into the host's bucket, so these widgets join the host activity without a new key shape.

The placement rule is load-bearing. In September 2026, 29 of the 89 APKs with an app direct caller hit the analysis time cap and 44 of 163 artefacts have no `complete` sentinel; almost all of that time is spent in the WTG. Anything that does not depend on the WTG is therefore computed and written in the pre-WTG artefact, so a WTG timeout costs transitions and nothing else.

The section also corrects a claim about Soot package exclusions: they never reached Soot, and this change removes them rather than making them effective (see the MODIFIED requirement).

## Data Contracts

### Input
- `Scene.v().getCallGraph()` — the SPARK call graph after the client's lambda edges are added (source: GATOR/Soot 4.7.1)
- `ReachabilityIndex` — the reachability result, including the `directlyReachesTarget` set restricted to app methods, which is C (source: `ReachabilityEngine`)
- `GUIAnalysisOutput` — the solved flow graph (view trees, inflate results, listener registrations), complete before the pre-WTG write (source: `GUIAnalysis`)
- Layout and navigation resources decoded by apktool (`res/layout`, `res/navigation`) (source: `Configs.resourceLocation`)

### Output
- `distanceTargets: list[{signature: str, kind: "direct" | "boundary"}]` — top-level key in the `.apk.json`: the members of C (`direct`) sorted by signature, followed by the members of B that are not in C (`boundary`) sorted by signature, so index `i` is stable for a given artefact (destination: `aperv-tool` derive, offline analyses)
- `reachability[].methods[].targetDistances: list[[int, int]]` — pairs `[i, d]`, `i` an index into `distanceTargets`, `1 ≤ d ≤ 10` for a method that is not itself `c`, and `[i, 0]` for `c` itself; sorted by `i`; the key is omitted when the list would be empty (destination: same)
- `windows[]` entries of type `FRAGMENT` — name `Host#Fragment` (fully qualified class names), `isMain: false`, `widgets[]` with the same fields as an activity window (destination: `StaticAnalysisParser`, `aperv-tool` derive)
- `windows[]` entries of type `HOSTED` — name `Host#Owner`, where `Owner` is the class holding the inflating code (dialog, DialogFragment, adapter, binding owner); same fields (destination: same)

### Side-Effects
- **Soot call graph**: lambda wrapper edges are added to `Scene.v().getCallGraph()` before the reachability BFS; they stay for the rest of the run, so the WTG with `cgDelegation=true` sees them too
- **Flow graph**: value-flow edges from a fragment's `onCreateView` return value to its `onViewCreated` `view` parameter and to `getView()`/`requireView()` results, and ViewBinding `findChildViewById` op nodes, are added before the solver runs

### Error
- A failure inside the fragment pass, the hosted-window pass or the distance pass is caught, logged with `[RvsecAnalysisClient]`, and costs only that section; the rest of the artefact is written (no new exception type)

## Invariants

- **INV-ANA-73**: Each distance search MUST be seeded by exactly one app method: a member of C (the app methods in the `directlyReachesTarget` set) or of B. Library methods MUST NOT seed it. `d(t, t) = 0`, `d ≤ DIST_MAX = 10`, and a method absent from a target's search has no pair for that target.
- **INV-ANA-74**: Every method carrying a non-empty `targetDistances` MUST carry `reachesTarget` or `directlyReachesTarget` `true`: the distance search runs on the same call graph as the reachability search and its seeds are a subset of that search's seeds.
- **INV-ANA-75**: `distanceTargets`, every `targetDistances` list, and every `FRAGMENT` and `HOSTED` window MUST be present in the pre-WTG artefact, with the same content as in the final artefact of the same run.
- **INV-ANA-76**: `FRAGMENT` and `HOSTED` windows MUST be named `Host#Owner` and MUST NOT be typed `DIALOG`; their ids MUST be disjoint from WTG node ids, from the client's fallback ids, and from each other.
- **INV-ANA-77**: The call graph used for `reachesTarget` and for distances MUST contain an edge from each method of a D8/desugar lambda class to each app method its body invokes, and from a single-invoke implementation of a directly implemented single-abstract-method interface to the app method it invokes.
- **INV-ANA-78**: `StaticAnalysisParser._map_window_type` MUST map `FRAGMENT` and `HOSTED` explicitly; neither may fall through to `ACTIVITY`, so `Host#Owner` windows are never counted as activities.
- **INV-ANA-79**: When an APK has no fragment, no hosted view, no binding layout and no lambda wrapper, the `.apk.json` content MUST equal the content produced without this change, apart from the `distanceTargets` and `targetDistances` keys and from widget records that repeat another record of the same window in every field, which appear once (Requirement: Repeated Widget Records Are Emitted Once). Window and widget node ids are compared by content, not by value, because GATOR's ids depend on identity-hash iteration.

## ADDED Requirements

### Requirement: Per-Target Call-Graph Distance (FR06)

The client SHALL compute, after the reachability search and before the pre-WTG write, one reverse breadth-first search per direct caller `c ∈ C` over the call graph with self-loops dropped (the graph the reachability search walks, lambda edges included). The search SHALL stop at depth `DIST_MAX = 10` and SHALL record the depth at which it first visits each app method. C SHALL be the app methods in the `directlyReachesTarget` set, sorted by signature, and SHALL be written as `distanceTargets`; each app method's pairs SHALL be written as `targetDistances` inside its `reachability[].methods[]` entry. The keys SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

The reachability search keeps its library seeds, so `reachesTarget` keeps its meaning. The distance is seeded by app methods only, because a distance to a library direct caller says nothing a consumer can act on in the app (INV-ANA-73). C entries carry `kind: "direct"`.

The graph is the whole call graph, not the subgraph induced by app methods. Both were measured on 2026-10-07 on 10 APKs against the E6 traces and gave the same answers on every measure (true-handler rank, click lift, no-bind lift); the whole graph keeps INV-ANA-74, and on `com.password.monitor_102` it finds 102 app methods within 10 calls of a target where the app subgraph finds 6, because app callbacks invoked from library code are paths the app subgraph cuts.

#### Scenario: A handler two calls away from a direct caller
- **WHEN** the app has `A.onClick` → `A.save` → `Crypto.encrypt`, and `Crypto.encrypt` calls `javax.crypto.Cipher.doFinal`, a target
- **THEN** `distanceTargets` MUST contain `<Crypto: byte[] encrypt(byte[])>` at some index `i`
- **AND** `A.onClick` MUST carry `[i, 2]`, `A.save` `[i, 1]` and `Crypto.encrypt` `[i, 0]`

#### Scenario: Library direct callers do not seed the distance
- **WHEN** an app method `Net.connect` calls `okhttp3.OkHttpClient.newCall`, a library method that reaches a target only through library code, and no app method calls a target directly
- **THEN** `distanceTargets` MUST hold exactly `{"signature": "<…Net: void connect()>", "kind": "boundary"}`
- **AND** no library method MUST appear in `distanceTargets`
- **AND** `Net.connect`'s `reachesTarget` MUST be `true`, as before this change

#### Scenario: Distance beyond the cap
- **WHEN** an app method reaches `c` only through a call chain of 11 edges
- **THEN** that method MUST NOT carry a pair for `c`
- **AND** its `reachesTarget` MUST still be `true`

#### Scenario: Distance survives a WTG timeout
- **WHEN** the analysis of `org.quantumbadger.redreader_117.apk` is killed by the 1,800 s timeout while `WTGBuilder` runs
- **THEN** the partial `.apk.json` MUST contain `distanceTargets` and every `targetDistances` list
- **AND** it MUST NOT contain the `complete` sentinel (INV-ANA-31)

### Requirement: Boundary Targets (FR06)

The client SHALL compute B, the app methods with a call-graph edge to a library method from which a target is reachable through library methods only (a target itself is excluded, because an edge to a target makes the caller a member of C), and SHALL append the members of B not in C to `distanceTargets` with `kind: "boundary"`, each seeding its own distance search. B exists so that an APK whose monitored operations are all invoked inside libraries still gives the explorer a distance to steer by. Measured on 2026-10-07 on the 12 APKs whose distance pass finished, |B| had median 6 (0 to 531) and covered a median 0.4 % of app methods; the largest in count, `eu.faircode.email_2322`, holds 531 of 17,250 (3.1 %). Constructors and static initializers are not filtered out of B: a consumer that wants only interaction code can skip `boundary` entries.

#### Scenario: A boundary method is a target of its own
- **WHEN** `Sync.run` calls `com.google.crypto.tink.Aead.encrypt`, whose library body reaches `javax.crypto.Cipher.doFinal`, and `Sync.run` does not call a target directly
- **THEN** `distanceTargets` MUST contain `{"signature": "<…Sync: void run()>", "kind": "boundary"}` at some index `j`
- **AND** a handler that calls `Sync.run` MUST carry `[j, 1]`

### Requirement: Lambda Wrapper Edges in the Reachability Call Graph (FR06)

Before the reachability search, the client SHALL add to `Scene.v().getCallGraph()` an edge from every method of a D8/desugar lambda class (class name containing `$$ExternalSyntheticLambda` or `$$Lambda`) to each app method its body invokes, and from every app method that implements the single abstract method of a directly implemented interface, whose body holds exactly one invoke naming an app method, to that method. SPARK gives the receiver captured by such a wrapper no points-to set, so without these edges a wrapper registered as a listener carries `reachesTarget: false` even when its body reaches a target, and the derive falls back to a per-class guess (see the `aperv` delta).

#### Scenario: A D8 wrapper reaches through its own body
- **WHEN** `MainActivity$$ExternalSyntheticLambda0.onClick(View)` invokes `MainActivity.lambda$onCreate$0(View)`, which calls a direct caller `c`
- **THEN** the wrapper MUST carry `reachesTarget: true`
- **AND** it MUST carry `[i, 2]` for `c` when `lambda$onCreate$0` carries `[i, 1]`

#### Scenario: A sibling lambda does not lend its flag
- **WHEN** `MainActivity$$ExternalSyntheticLambda1.onClick(View)` invokes `MainActivity.lambda$onCreate$1(View)`, which reaches no target, while `lambda$onCreate$0` does
- **THEN** `MainActivity$$ExternalSyntheticLambda1.onClick` MUST carry `reachesTarget: false`
- **AND** it MUST NOT carry `targetDistances`

### Requirement: Fragment Windows (FR04, FR06)

The client SHALL build a host → fragments map from the app's own code and resources: `<fragment>` and `FragmentContainerView` elements in a host's layouts, `FragmentTransaction.add`/`replace` calls in the host, Navigation graphs referenced by the host's layouts, and fragments handed to a pager adapter the host creates. A host that is a base class SHALL be mapped to each manifest activity that extends it. For each (host, fragment) pair, the client SHALL emit a window named `Host#Fragment` of type `FRAGMENT`, whose widgets are the views reaching the value `onCreateView` returns (including ViewBinding `Binding.inflate(...).getRoot()`), or, when none is found, the results of the `inflate` calls inside `onCreateView`. Widgets and listeners SHALL be collected by the same walk as activity widgets, so the window carries the same fields.

Fragments created by reflection, by a `FragmentFactory` or Hilt, or by a Navigation graph built in code are not mapped, and a fragment built with `Fragment(R.layout.x)` and no `onCreateView` has no window.

#### Scenario: A fragment added by a transaction
- **WHEN** `MainActivity.onCreate` calls `getSupportFragmentManager().beginTransaction().replace(R.id.container, new SettingsFragment())` and `SettingsFragment.onCreateView` inflates a layout with a button `save` whose listener `SettingsFragment$1.onClick` is set in `onViewCreated`
- **THEN** `windows[]` MUST contain a window named `com.example.MainActivity#com.example.SettingsFragment` of type `FRAGMENT`
- **AND** its widgets MUST contain `save` with the listener `<com.example.SettingsFragment$1: void onClick(android.view.View)>`

#### Scenario: Fragment windows when the WTG does not finish
- **WHEN** the same APK is analyzed with `--skip-wtg`
- **THEN** the pre-WTG artefact MUST contain the same `FRAGMENT` window with the same widgets (INV-ANA-75)

#### Scenario: Nothing existing is lost
- **WHEN** `systems.sieber.droid_scep_7.apk` is analyzed with and without this change
- **THEN** every window, widget and listener of the artefact without the change MUST be present, by content, in the artefact with it

### Requirement: Fragment View Flow and ViewBinding in the Flow Graph (FR04, FR06)

Before the solver runs, the flow graph SHALL connect a fragment's `onCreateView` return value to the `view` parameter of its `onViewCreated(View, Bundle)` and to the result of `getView()`/`requireView()` called on a fragment of that class, and SHALL model `androidx.viewbinding.ViewBindings.findChildViewById(View, int)` as a `findViewById` on its first argument. The framework makes both connections at run time; without the edges, listeners set through `view.findViewById(id)` in `onViewCreated` or through a ViewBinding field are registered on views the solver cannot see. The edges are per class, not per instance.

#### Scenario: A listener set through ViewBinding in an activity
- **WHEN** an activity calls `ActivityMainBinding.inflate(getLayoutInflater())`, `setContentView(binding.getRoot())` and `binding.ok.setOnClickListener(l)`, where the generated binding resolves `ok` through `ViewBindings.findChildViewById(root, R.id.ok)`
- **THEN** the activity's window MUST contain the widget `ok` with listener `l`

#### Scenario: A listener set on the view passed to onViewCreated
- **WHEN** `ListFragment.onViewCreated(View view, Bundle b)` calls `view.findViewById(R.id.add).setOnClickListener(l)` and `onCreateView` returns the inflated `R.layout.list`
- **THEN** the `Host#ListFragment` window MUST contain the widget `add` with listener `l`

### Requirement: Hosted Windows for Dialogs, Binding Layouts and Adapter Rows (FR04, FR06)

The client SHALL emit, as windows of type `HOSTED` named `HostActivity#OwnerClass`, the view trees GATOR builds outside an activity's own content view and outside the `FRAGMENT` windows: dialog bodies, DialogFragment views, adapter rows and binding layouts. The host SHALL be the activity the owner's inflating code is reachable from; an owner reachable from more than 20 activities is a shared helper and SHALL NOT be emitted. A view tree already emitted in a `FRAGMENT` window for the same (host, owner) SHALL NOT be emitted again. The windows are produced from solver state alone, so they appear in the pre-WTG artefact (INV-ANA-75).

#### Scenario: A DialogFragment shown from an activity
- **WHEN** `MainActivity` shows `DeleteDialog extends DialogFragment`, whose `onCreateView` inflates a layout with a button `confirm` and listener `DeleteDialog$1.onClick`
- **THEN** `windows[]` MUST contain `com.example.MainActivity#com.example.DeleteDialog` of type `HOSTED` with the widget `confirm`
- **AND** no window of type `DIALOG` MUST carry that name

#### Scenario: An adapter row
- **WHEN** `ItemAdapter.onCreateViewHolder` inflates `R.layout.item_row` with a button `star`, and `ItemAdapter` is created only in `ListActivity`
- **THEN** `windows[]` MUST contain `com.example.ListActivity#com.example.ItemAdapter` of type `HOSTED` with the widget `star`

### Requirement: Repeated Owned Windows Are Emitted Once (FR04)

After the `FRAGMENT` and `HOSTED` windows are built and before the XML attributes are added, the client SHALL keep, for each host, one `FRAGMENT` or `HOSTED` window per distinct widget list, the first in emission order, and drop the others. Fragments that share a base class reach the same view objects through the per-class fragment view flow, so each subclass window can carry the same tree; every consumer folds `Host#Owner` windows into the host's bucket, so the copies add size and change nothing a consumer reads. On `github.paroj.dsub2000_217`, 58 of 61 fragment windows held one 124-widget tree, which took the listeners from 54 to 28,238 and the artefact from 1.8 MB to 11 MB; with one window per tree, 6 `FRAGMENT` windows, 2,610 listeners and 2.9 MB remain, and the derive flags the same 11 widgets. `ACTIVITY`, `DIALOG` and menu windows are never dropped.

#### Scenario: Fragments sharing a base class and a tree
- **WHEN** `MainActivity` hosts `AlbumFragment`, `ArtistFragment` and `SongFragment`, all extending `ListBaseFragment`, and the three windows `MainActivity#AlbumFragment`, `MainActivity#ArtistFragment` and `MainActivity#SongFragment` carry the same 124-widget list
- **THEN** `windows[]` MUST contain exactly one of them, the one emitted first
- **AND** a `MainActivity#SettingsFragment` window with a different widget list MUST stay
- **AND** a window `OtherActivity#AlbumFragment` with the same widget list MUST stay, because its host differs

### Requirement: Repeated Widget Records Are Emitted Once (FR04)

After the XML attributes are added and the programmatic spinner items are merged, the client SHALL keep, in every window of every type, the first of the widget records that are equal in every field (`id`, `idName`, `type`, texts, `entries`, `listeners` and the other attributes) and drop the others. A layout reached from several view roots of one window yields one record per root, and two such records say nothing the first one does not, so dropping them loses no content. On `org.hwyl.sexytopo_93`, the leg form of `LegDialogs` is built by three methods (`addStation`, `addSplay`, `editLeg`), so each of its 13 hosted windows listed the 39-id tree three times: 2,642 widget records and 3,071 listeners before, 2,118 records and 2,109 listeners after, with the same 2,118 distinct records. On `com.etesync.syncadapter_20700`: 920 → 731 records, none distinct lost. The `ACTIVITY` windows of the September producer also hold a few such copies (3 to 12 per APK on the APKs measured); they are dropped too. Records of one id that differ in any field, for instance one annotated by `enrichFromXml` and one not (D7), all stay.

#### Scenario: One dialog layout built by three methods
- **WHEN** a hosted window `TableActivity#LegDialogs` receives the widget tree of `R.layout.leg_form` from three view roots, and the three `editDistance` records carry the same type, texts and five listeners
- **THEN** the window MUST contain one `editDistance` record
- **AND** the distinct content of `windows[]` MUST be the same as before the drop

#### Scenario: Records of one id that differ are kept
- **WHEN** a window holds two `editDistance` records whose `text` differs
- **THEN** both records MUST stay

### Requirement: Spinner Items from Array Resources (FR04)

The programmatic spinner extractor SHALL take a spinner's items from an array resource when the adapter bound by `setAdapter` was created by `ArrayAdapter.createFromResource(ctx, R.array.X, layout)`, or when the items passed to the `ArrayAdapter` constructor or to `addAll` come from `Resources.getStringArray(R.array.X)` or `Resources.getTextArray(R.array.X)`. The array id SHALL be resolved to its items through the decoded resources: the id to the array name by the app's resource id map, the name to its `<item>` values by the same parser that resolves `android:entries="@array/X"` (with `@string/` references resolved). The items SHALL be appended to the widget's `entries` after any XML entries, as the other programmatic items are. An id that is not an app array leaves `entries` unchanged. A resource id, the `findViewById` argument included, is either an int constant or a read of a static field of the app's `R$<type>` class (an app whose `R` fields are not final); the field SHALL be resolved by its type and name through the app's resource id map. The `findViewById` argument SHALL be resolved at the `findViewById` statement, and the items SHALL be those of the adapter that reaches `setAdapter`, identified by the statement that created it, because the compiler reuses one register for several ids and one local for several adapters. A spinner bound in several places SHALL carry each item once. These items are static resources, while a spinner filled from runtime data has no items for a static analysis to read; without this, a spinner filled from a resource array carried an empty `entries` list.

#### Scenario: A spinner filled with createFromResource
- **WHEN** `ProfileSetup` calls `ArrayAdapter.createFromResource(getApplicationContext(), R.array.TimeIntervals, R.layout.spinner_layout)` and passes the adapter to `setAdapter` on `findViewById(R.id.totpTimeIntervalSpinner)`, and `res/values/arrays.xml` declares `<string-array name="TimeIntervals"><item>30 Seconds</item><item>60 Seconds</item></string-array>`
- **THEN** the widget `totpTimeIntervalSpinner` in the `ProfileSetup` window MUST carry `entries == ["30 Seconds", "60 Seconds"]`

#### Scenario: One register for the spinner id and the array id
- **WHEN** `Home` assigns `$i0 = <org.cry.otp.R$id: int totpSHATypeSpinner>`, calls `findViewById($i0)`, then assigns `$i0 = <org.cry.otp.R$array: int SHATypes>`, calls `createFromResource(this, $i0, …)` and `setAdapter` on the spinner
- **THEN** the widget `totpSHATypeSpinner` MUST carry `entries == ["SHA-1", "SHA-256", "SHA-512"]`
- **AND** no items MUST be keyed by the id of `SHATypes`

#### Scenario: An array read through getStringArray
- **WHEN** an activity builds `new ArrayAdapter<>(this, layout, getResources().getStringArray(R.array.Modes))` and binds it to a spinner obtained by `findViewById(R.id.mode)`
- **THEN** the widget `mode` MUST carry the items of `Modes` as `entries`

### Requirement: The Parser Recognizes Fragment and Hosted Windows (FR04)

`StaticAnalysisParser._map_window_type` (`modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`) SHALL map `FRAGMENT` to `WindowType.FRAGMENT` and `HOSTED` to `WindowType.HOSTED`, a member added to `WindowType` in `rv-android-core` (`domain/window.py`). An unknown type falls back to `ACTIVITY` today, which would make every `HOSTED` window look like an activity to any consumer that filters by type (INV-ANA-78).

#### Scenario: Hosted windows are not activities
- **WHEN** an artefact holds one `ACTIVITY` window `com.example.MainActivity` and one `HOSTED` window `com.example.MainActivity#com.example.ItemAdapter`
- **THEN** the parsed `Windows` MUST hold one window of type `ACTIVITY` and one of type `HOSTED`
- **AND** `Windows` filtered to `WindowType.ACTIVITY` MUST hold one window

## MODIFIED Requirements

### Requirement: Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)

The system MUST run a single GATOR analysis client to produce a single JSON output file containing four data sections written in priority order: (1) method reachability relative to a `TargetMethodSource` (coverage denominator), (2) window and widget inventory with event listeners, **populated regardless of WTG completion status (INV-ANA-20)**, (3) window transition graph, and (4) non-Activity component data (Services, BroadcastReceivers, ContentProviders) with intent-filters/authorities and target reachability. The JSON output MUST end with a sentinel `"complete": true` as the last top-level field on successful completion (INV-ANA-31).

The partial-write path (`wtg == null`) MUST emit a populated `windows[]` section using the same `extractWindows` helper as the full-write path, supplying `Collections.emptyMap()` for `windowNodeIds` and `null` for the WTG handle (INV-ANA-20). The catch-all loop over `wtg.getNodes()` (which adds fragment/context-menu windows not enumerated by `output.getActivities()`/`getDialogs()`/`getOptionsMenu()`) is guarded by `if (wtg != null)`; its absence in the partial path is the only widget-data difference between the two paths.

The analysis tool is a GATOR client (`RvsecAnalysisClient`) that implements the `GUIAnalysisClient` interface. Following decomposition, `RvsecAnalysisClient` is an orchestrator (~200 LOC) that wires four single-responsibility components plus a streaming enricher: `TargetResolver` (loads from a `TargetMethodSource` and resolves into Soot `Scene`), `ReachabilityEngine` (builds JGraphT call graph, runs multi-source BFS, complements with bytecode scan), `ReachabilityIndex` (encapsulated lookup ADT), `ReachabilityEnricher` (per-node visitor that annotates each window/transition/component/method on the fly using `ReachabilityIndex`, called by the writer during the section walk — NOT a batch materializer), and `JsonReportWriter` (incremental walker that emits each section to the output stream and flushes immediately, invoking `ReachabilityEnricher` callbacks per node to obtain the annotated values; `flush()` per section preserves partial recovery on timeout). The `JsonReportWriter` MUST NOT itself call any `ReachabilityIndex` lookup method (INV-ANA-30); all flag decisions go through the injected `ReachabilityEnricher` callback interface, which is purely a delegate — the writer holds no direct reference to the index.

GATOR initializes Soot once with defensive configuration (INV-ANA-16), builds its constraint graph and fixpoint analysis, and then invokes the client's `run(GUIAnalysisOutput output)` method. Inside this method, the orchestrator writes each JSON section incrementally with explicit flush, so that a timeout or crash after any section produces a parseable partial file (no sentinel emitted — `complete` is absent or implicitly `false`). The writer MUST NOT buffer all sections into memory before serialization — this would defeat the partial-recovery guarantee when timeout is the dominant failure mode (~30-50% of large sweeps per gh57 ground truth). Each section is enriched and emitted in one stream, then flushed before the next section is computed.

The `Flowgraph.processApplicationClasses()` method MUST handle individual method failures gracefully (INV-ANA-17). When `retrieveActiveBody()` or `createOpNode()` throws an exception for a specific method, the Flowgraph MUST skip that method and continue processing remaining methods. The resulting Flowgraph may be incomplete (missing OpNodes, widgets, or listeners for skipped methods), but the GUIAnalysis pipeline MUST complete and the `RvsecAnalysisClient` MUST produce JSON output. Reachability data (computed from `Scene.v().getCallGraph()` via BFS) is NOT affected by Flowgraph incompleteness — it depends on the Soot call graph, not on the Flowgraph.

The GATOR MUST use Soot 4.7.1 (`org.soot-oss:soot`, INV-ANA-18) with defensive configuration (INV-ANA-16). The `ClassHierarchy.typeNode()` bug (soot-oss/soot#1071) is not fixed in Soot 4.7.1, but the improved Dexpler in 4.x reduces crash frequency. The defensive options (disabling `jb.sils`/`jb.dae`) further reduce the crash surface. GATOR passes no package exclusion to Soot: bodies of `kotlin.*`, `kotlinx.*` and `androidx.*` are loaded like any other library body. Soot 4.7.1 reads its exclusion list only when the `Scene` is constructed (`Scene.determineExcludedPackages`), and GATOR constructs the `Scene` in `PrerunEntrypoint.run()` before `soot.Main.main(args)` parses its arguments, so an `-exclude` argument never had an effect. Applying the exclusions before the `Scene` exists was measured on 2026-10-07 and rejected: it shrinks the call graph (droid_scep 80,025 vertices / 282,789 edges to 67,518 / 238,046) without changing any distance or flag measured on the test APKs, and GATOR's own passes then fail on excluded classes they still need (`androidx.compose.ui.tooling.PreviewActivity` is a manifest activity whose body the flow graph retrieves). GATOR keeps passing `-no-bodies-for-excluded`, which is not inert: it acts on the packages Soot excludes by default (`java.*`, `javax.*`, `sun.*`, …), and without it the call graph of `net.gaast.giggity_769` grows from 11,247 vertices / 23,698 edges to 11,286 / 24,472.

Crash recovery is bounded by phase: failures inside `Flowgraph.processApplicationClasses()` are method-local (skip method, continue — INV-ANA-17) and the analysis pipeline completes. Failures inside Soot's call-graph construction phase (e.g., SPARK `InternalTypingException`) are NOT recoverable at the Flowgraph level — the JVM exits with a non-zero code and no JSON is produced. This boundary is load-bearing: it prevents the silent emission of a "complete-looking" report built on a corrupt call graph. Together, these recovery rules form a layered defense — prevention (defensive Soot config), method-local skip (Flowgraph try-catch), and hard halt (call-graph phase) — each at a distinct layer with non-overlapping responsibility.

When comparing analysis output against a baseline (e.g., gh57 commit `b2e04a26`), tolerances reflect Soot 4.7.1 non-determinism: for set-based reachability comparisons the contract is **strict equality** (BFS is deterministic over a fixed call graph and target set); for cardinality metrics derived from Flowgraph skips (window/transition/widget counts) a ±10% tolerance is permitted to absorb crash-frequency variation across Soot runs. `directlyReachesTarget` MUST be a strict superset or equal to the baseline `directlyReachesMop` set (BUG-INV-ANA-19: the bytecode-scan complement can only add direct callers SPARK missed, never remove them).

The execution order inside `run()`:

1. **Loads target methods via `TargetMethodSource` and resolves into Soot `Scene`**. The source is constructed from CLI input: `--mop-dir <dir>` yields a `MopSpecsTargetSource` wrapping `JavamopFacade.listUsedMethods(mopDir, false)`; `--targets-file <path>` yields a `SignatureFileTargetSource` parsing a text file of Soot signatures (one per line, `#` comments, blank lines tolerated). The two CLI flags are mutually exclusive (INV-ANA-33). The `TargetResolver` calls `source.load()` to produce a `Set<TargetMethod>`, then resolves each to one or more `SootMethod` instances per the source's matching policy: LENIENT (class+name only) for `MopSpecsTargetSource` because AspectJ wildcards in `.mop` specs leave the full signature semantically undefined; STRICT (full Soot signature) for `SignatureFileTargetSource` because the user controls precision. Wildcard parameter lists in a targets-file entry (`(..)` or `(*)`) resolve LENIENT for that entry only.

2. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. Entry points include: Activity lifecycle handlers and public/protected methods (via `output.getActivities()`), Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`) and public/protected methods (via `XMLParser.getServices()`), BroadcastReceiver lifecycle method (`onReceive`) and public/protected methods (via `XMLParser.getReceivers()`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`) and public/protected methods (via `XMLParser.getProviders()`). For each application method, the `ReachabilityEngine` computes: `reachable` (reachable from entry points), `reachesTarget` (has path to a resolved target method — renamed from `reachesMop`), and `directlyReachesTarget` (directly invokes a resolved target method — renamed from `directlyReachesMop`). The `ReachabilityIndex` materializes these as `Set<String>` for O(1) lookup. This section is written and flushed first.

3. **Extracts windows and widgets** using GATOR's internal APIs (`getActivities()`, `getActivityRoots()`, `getDialogs()`, `getDialogRoots()`, `getOptionsMenu()`, `PropertyManager`). GATOR's interprocedural analysis provides the widget inventory (IDs, names, types, text, hint, listeners) including dynamically-registered listeners. Widget XML attributes not available via GATOR APIs — `inputType`, `entries` (from `android:entries="@array/X"`), and the four attributes `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` — are extracted by `enrichFromXml()` from the decoded layout XML files at `Configs.resourceLocation`. The `windows[]` section is written in both the partial-JSON path (after reachability, with `wtg=null`) and the full-JSON path (after WTG completion, with the WTG handle for numeric ID assignment and catch-all enumeration).

4. **Extracts the Window Transition Graph** using GATOR's `WTGBuilder` and `WTGAnalysisOutput`, producing window IDs, transition edges with event types, widget IDs, and handler signatures. WTG construction MUST use `Scene.v().getCallGraph()` (the SPARK CG already built by Soot) as the single source of virtual-dispatch resolution when the `cgDelegation` client parameter is `true`; `AndroidCallGraph.v()` MUST NOT be populated by `FlowgraphRebuilder.buildCallGraph()` in this mode (INV-ANA-21). The legacy `AndroidCallGraph` rebuild via `FlowgraphRebuilder.buildCallGraph()` MUST be preserved behind `cgDelegation=false` (default after the M3 paridade-gate decision in `docs/20260515_diagnostico_paridade_cgdelegation.md`), where rollback is bit-for-bit. Edges to library classes quarantined by SPARK's `IGNORED_CLASSES` are recovered via a WTG-level bytecode-scan complement (INV-ANA-22). WTG construction is skipped entirely when the `skipWtg` client parameter is `true` (see the `skipWtg` ADDED requirement), in which case `transitions[]` is emitted as an empty array.

5. **Extracts non-Activity components** (Services, BroadcastReceivers, ContentProviders) from `XMLParser.getServices()`, `XMLParser.getReceivers()`, and `XMLParser.getProviders()`, enriched with intent-filters from `IntentFilterManager`, `android:exported` attribute, and target reachability cross-referenced with the reachability BFS results. This section is written and flushed last.

6. **Emits sentinel `"complete": true`** as the final top-level field, after all sections are flushed. Parser uses this to distinguish a successful run from a truncated one (INV-ANA-31).

The `complementWithCallbacks()` method, which propagates target reachability flags for lifecycle and event handlers, MUST also include Service, Receiver, and Provider lifecycle methods in its callback set, so they receive flag propagation via the call graph.

Each entry in `reachability[]` MUST include `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null` when the method belongs to no component) and `isMain` (boolean) fields. The legacy `isActivity` and `isMainActivity` fields are removed (no shim — P3). The `StaticAnalysisParser` (Python) MUST parse the new fields into the `Clazz` domain model as `component_type: str | None` and `is_main: bool`. The `null` handler exists because `getSootClassUnsafe` may return `null` for methods declared on synthetic or excluded classes; the producer emits `componentType=null` rather than dropping the entry, preserving the reachability set cardinality.

All JSON keys MUST be emitted via constants in `presto.android.gui.clients.json.JsonSchema.Keys` (Java) and consumed via `_JK = SimpleNamespace(...)` in `rv_static_analysis.parser.static.static_analysis_parser` (Python). The two constant sets MUST be value-equal (INV-ANA-32) — verified by `tests/parity/json_keys.py`.

The analysis JSON output is parsed by `StaticAnalysisParser` into the `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph, Components, `complete: bool`). Downstream consumers (rv-coverage, rv-platform, rv-experiment, aperv-tool, scripts) receive renamed Pydantic fields per the `core` spec delta. rv-agent (deprecated) is not a live consumer; sweep regenerates JSONs and breaks rv-agent's stale reader by design.

The reachability section defines the **method universe** — the total set of reachable methods that serves as the denominator for all coverage percentage calculations. Without reachability data, the system can count absolute method calls but cannot compute coverage percentages.

The reachability section also provides target prioritization data consumed by agents. The agent's action ranker assigns score boosts to actions whose handler method has `directly_reaches_target=true` or `reaches_target=true` (consumer side details outside this spec).

The call graph is built using SPARK (`-cgAlgorithm spark`) with `all-reachable:true`, which performs full points-to analysis to resolve virtual calls based on types effectively instantiated in the program. SPARK is the operational default. Other algorithms — CHA, RTA, VTA — remain available. JCA framework classes appear as call targets whenever any application method invokes them — they do not need to be entry points.

**Module**: rv-static-analysis (launcher + parser — modified for `--targets-file`, `_JK`, sentinel check), rvsec-gator (analysis client — decomposed + renamed + sentinel-emitting)
**Key components**: `Main.java` (Soot config), `Flowgraph.java` (error handling), `RvsecAnalysisClient` (orchestrator, ~200 LOC post-decomp), `TargetMethod`, `TargetMethodSource`, `MopSpecsTargetSource`, `SignatureFileTargetSource`, `TargetResolver`, `ReachabilityEngine`, `ReachabilityIndex`, `ReachabilityEnricher` (visitor callback, no `ReportModel` materialization), `JsonReportWriter` (streaming walker with `flush()` per section), `JsonSchema.Keys`, `JsonSchemaKeysDump` (reflection-based parity dumper), `JimpleDefUtils`, `XMLParser`, `DefaultXMLParser`, `IntentFilterManager`, `StaticAnalysisParser` (consumes `_JK` + sentinel; builds `window_methods_index` for `WindowTransition.target_reaches_target`), `Clazz`.

#### Scenario: Successful static analysis with valid APK using --mop-dir

- **WHEN** `StaticAnalyzer._run_analysis()` is called with a valid APK path, the analysis client JAR exists at `lib/gator/rvsec-analysis-client.jar`, and the user passed `--mop-dir <dir>` on the CLI
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <analysis_client_jar> --out <output_file> -client RvsecAnalysisClient -clientParam mopDir=<mop_dir> --timeout <timeout> -cgAlgorithm spark`
- **AND** the producer MUST instantiate `MopSpecsTargetSource(Path(mopDir))` and `TargetResolver` MUST resolve targets LENIENT (class+name)
- **AND** the resulting `.json` file MUST end with `"complete": true` as the final top-level field
- **AND** the resulting `.json` file MUST be parseable by `StaticAnalysisParser` into a `StaticAnalysisData` with `complete == True`
- **AND** all JSON keys present in the output MUST match values declared in `JsonSchema.Keys`

#### Scenario: Successful static analysis using --targets-file

- **WHEN** the user invokes `rv-static-analysis --targets-file demo.txt <apk>` and `demo.txt` contains lines such as `<javax.crypto.Cipher: void init(int,java.security.Key)>` and `# comment` and blank lines
- **THEN** the CLI MUST accept the invocation (mutex group permits exactly one of `--mop-dir` or `--targets-file`, INV-ANA-33)
- **AND** GATOR MUST be invoked with `-clientParam targetsFile=<path>` instead of `mopDir=...`
- **AND** the producer MUST instantiate `SignatureFileTargetSource(Path(targetsFile))` and `TargetResolver` MUST resolve targets STRICT (full signature) for non-wildcard entries
- **AND** entries containing `(..)` or `(*)` MUST resolve LENIENT for that entry only
- **AND** the output JSON MUST follow the same schema as the `--mop-dir` path (same keys, sentinel last)

#### Scenario: CLI mutex rejects passing both --mop-dir and --targets-file

- **WHEN** the user invokes `rv-static-analysis --mop-dir /m --targets-file /t <apk>`
- **THEN** the argparse mutex group MUST emit an error to stderr explaining `--mop-dir` and `--targets-file` are mutually exclusive
- **AND** the process MUST exit with a non-zero return code before launching GATOR

#### Scenario: CLI rejects passing neither --mop-dir nor --targets-file

- **WHEN** the user invokes `rv-static-analysis <apk>` without specifying any target source
- **THEN** the argparse mutex group MUST emit an error indicating one of `--mop-dir` or `--targets-file` is required
- **AND** the process MUST exit with a non-zero return code

#### Scenario: --targets-file with malformed signature line

- **WHEN** the targets-file contains a line that is not blank, not a `#` comment, and is not a valid Soot signature (e.g., `Cipher.init` without angle brackets)
- **THEN** `SignatureFileTargetSource.load()` MUST raise `IllegalArgumentException` with the offending line number and content
- **AND** the GATOR process MUST exit with a non-zero code before producing any JSON

#### Scenario: MopSpecsTargetSource preserves baseline byte-for-byte

- **WHEN** GATOR analyzes `cryptoapp.apk` with `--mop-dir cryptoapp.mop` using the decomposed pipeline (`TargetResolver` + `ReachabilityEngine`)
- **THEN** the resulting `set(method.signature for method in data.methods if method.reaches_target)` MUST be equal to the same set computed from the gh57 baseline at commit `b2e04a26` (`reaches_mop` semantically — set comparison transparent to rename)
- **AND** the resulting `set(method.signature for method in data.methods if method.directly_reaches_target)` MUST be equal to the corresponding baseline set
- **AND** `cryptoapp.apk` MUST report exactly 16 target methods (INV-ANA-35)

#### Scenario: WTG timeout still produces populated windows[] in partial JSON

- **WHEN** GATOR analyzes an APK whose WTG construction exceeds the external sweep timeout (e.g. `ac.mdiq.podcini.X_256.apk` from the original-APK corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs/`), and the Java process is killed via SIGTERM during `WTGBuilder.build()`
- **THEN** the JSON file written before the kill MUST contain a fully-populated `windows[]` section with all activities, dialogs, options-menu skeletons, and their widgets (including listeners, text, hint, inputType, entries) extracted from `GUIAnalysisOutput`
- **AND** the JSON `transitions[]` MUST be `[]` (empty array, not missing)
- **AND** the JSON `windows[].widgets[]` MUST NOT contain the catch-all WTG-only entries (fragments, context menus that depend on `wtg.getNodes()` enumeration) — these are skipped because `wtg == null` (INV-ANA-20)
- **AND** numeric `windows[].id` values MUST come from the `fallbackId` sequence (starting at `100000`) or from `dialog.id`/`menu.id` fallbacks, since `windowNodeIds` is an empty map in the partial-write path

#### Scenario: WTG built using legacy call graph (cgDelegation=false, default post-M3)

- **WHEN** `RvsecAnalysisClient.run()` is invoked with default client parameters (`cgDelegation` defaults to `false` per `docs/20260515_diagnostico_paridade_cgdelegation.md`)
- **AND** `WTGBuilder.build(output)` is called and reaches `FlowgraphRebuilder.buildCallGraph()`
- **THEN** `FlowgraphRebuilder.buildCallGraph()` MUST take the legacy points-to + CHA-fallback code path (`buildCallGraphLegacy` — `hier.virtualDispatch()` + `hier.getConcreteSubtypes()`)
- **AND** `AndroidCallGraph.v()` MUST be populated as before the change
- **AND** the output `transitions[]` MUST match exactly the pre-change baseline for the same APK on this code path (rollback is bit-for-bit on the WTG section)

#### Scenario: WTG built using SPARK call graph (cgDelegation=true, opt-in)

- **WHEN** `RvsecAnalysisClient.run()` is invoked with `-clientParam cgDelegation=true`
- **AND** `WTGBuilder.build(output)` is called and reaches `FlowgraphRebuilder.buildCallGraph()`
- **THEN** `FlowgraphRebuilder.buildCallGraph()` MUST consult `Scene.v().getCallGraph()` to resolve virtual-dispatch targets for each `InvokeExpr` site
- **AND** `AndroidCallGraph.v()` MUST NOT be populated via the legacy CHA-style loop (INV-ANA-21)
- **AND** for `InvokeExpr` sites whose declared callee class is in `IGNORED_CLASSES` (SPARK quarantine — `java.*`, `javax.*`, `sun.*`, `android.*`, `androidx.*`, `dalvik.*`), edges MUST be recovered via the WTG-level bytecode-scan complement (INV-ANA-22)

#### Scenario: Hybrid-framework apps lose transitions in cgDelegation=true mode

This scenario documents a known limitation of the opt-in SPARK delegation path until a follow-up change ports the CHA fallback at application-class scope for zero-edge invoke sites.

- **GIVEN** an APK whose UI listener dispatch is routed through synthetic lambdas (`$$ExternalSyntheticLambda*`) declared in application packages, instantiated through native bridges (React Native, Flutter, Capacitor)
- **WHEN** the analyzer runs with `-clientParam cgDelegation=true`
- **THEN** the WTG MAY fail to create WTGNodes for the entry activities (the SPARK call graph lacks the edges that signal "this activity is live")
- **AND** the resulting `transitions[]` section MAY be empty for those apps
- **AND** the activities WILL appear in `windows[]` with fallback IDs (≥100000)
- **AND** consumers MUST treat an empty `transitions[]` paired with fallback-IDed windows as an analyzer limitation, not a "no transitions exist" assertion (reference: `docs/20260515_diagnostico_paridade_cgdelegation.md`)

This limitation does NOT apply to `cgDelegation=false` (the default), which uses the legacy CHA fallback over application-class subtypes and captures these lambdas.

#### Scenario: GATOR crashes during call graph construction

- **WHEN** Soot's call-graph builder throws an `InternalTypingException` during call graph construction for a method in a Kotlin class
- **THEN** the GATOR process MUST terminate with a non-zero exit code
- **AND** no `.json` output file MUST exist (the crash occurs before `RvsecAnalysisClient.run()` is invoked)
- **AND** the `StaticAnalyzer` wrapper MUST log the failure as `StaticAnalysisException`
- **AND** the `StaticAnalysisResult.analysis_file` MUST point to the expected output path (which does not exist)

#### Scenario: Timeout during JSON write produces truncated file without sentinel

- **WHEN** GATOR is killed by external timeout enforcement mid-way through `JsonReportWriter.write` (e.g., after `windows[]` is flushed but before `transitions[]` is complete)
- **THEN** the partial JSON file on disk MUST NOT contain the `"complete": true` sentinel
- **AND** `StaticAnalysisParser` MUST parse what is available via `_recover_truncated_json` (load-bearing recovery)
- **AND** `StaticAnalysisData.complete` MUST be `False` (Pydantic default for absent key)
- **AND** downstream gates requiring completeness MUST exclude this sample

#### Scenario: Flowgraph skips method with failing body (Scenario B recovery)

- **WHEN** `Flowgraph.processApplicationClasses()` calls `currentMethod.retrieveActiveBody()` and Soot throws an exception for a specific method
- **THEN** the exception MUST be caught by the try-catch around `retrieveActiveBody()` (INV-ANA-17)
- **AND** a log MUST be emitted via `Logger.warn()` with the skipped method's signature and exception message
- **AND** the loop MUST continue to the next method via `continue`
- **AND** the Flowgraph MUST complete with partial data
- **AND** the `RvsecAnalysisClient.run()` MUST execute and produce a JSON file (with sentinel if no further failure)

#### Scenario: Flowgraph skips statement with failing OpNode creation

- **WHEN** `Flowgraph.processApplicationClasses()` calls `createOpNode(currentStmt)` and the method throws an exception for a specific statement
- **THEN** the exception MUST be caught by the existing catch block (INV-ANA-17)
- **AND** a log MUST be emitted via `Logger.warn()`
- **AND** the loop MUST continue to the next statement via `continue`

#### Scenario: Kotlin stdlib exclusion impact on reachability

- **WHEN** GATOR analyzes `systems.sieber.droid_scep_7.apk`, a Kotlin APK
- **THEN** the Soot arguments built by `presto.android.Main` MUST NOT contain `-exclude`
- **AND** `Scene.v().isExcluded(Scene.v().getSootClass("kotlin.Unit"))` MUST be `false`
- **AND** the call graph MUST contain the bodies of `kotlin.*` methods reached from application code (80,025 vertices and 282,789 edges on this APK)

#### Scenario: Analysis output comparison after decomposition (refactor-only)

- **WHEN** the decomposed pipeline analyzes `cryptoapp.apk` with `--mop-dir cryptoapp.mop` and the output is compared against the saved characterization fixture captured immediately before C1c on the same Soot 4.7.1 + same baseline commit
- **THEN** window count MUST match exactly (±0)
- **AND** transition count MUST match exactly (±0)
- **AND** total method count MUST match exactly (±0)
- **AND** `set(reaches_target signatures)` post-decomposition MUST equal the pre-decomposition `set(reaches_mop signatures)` (set-equivalence, transparent to field rename and to JSON byte-order)
- **AND** `set(directly_reaches_target signatures)` post-decomposition MUST equal the pre-decomposition `set(directly_reaches_mop signatures)` (the decomposition is a refactor — no new direct edges introduced)

#### Scenario: Analysis output comparison against gh57 baseline across Soot runs

- **WHEN** the post-rename pipeline analyzes `cryptoapp.apk` and is compared against the gh57 baseline at commit `b2e04a26`, potentially across distinct Soot 4.7.1 invocations
- **THEN** `set(reaches_target signatures)` MUST equal `set(reaches_mop signatures)` from the baseline (strict equality — BFS is deterministic over the same call graph and target set)
- **AND** `set(directly_reaches_target signatures)` MUST equal the baseline `set(directly_reaches_mop signatures)` (the bytecode-scan complement is deterministic)
- **AND** window / transition / widget counts MAY differ by up to ±10% to absorb Soot 4.7.1 non-determinism from Flowgraph skips on borderline-broken methods
- **AND** the GESDA widget parity subset MUST match exactly (this subset is hand-curated and skip-free)

#### Scenario: directlyReachesTarget detects literal library invocations omitted by SPARK (BUG-INV-ANA-19)

- **WHEN** an application method's bytecode contains a literal `invoke-*` whose target's `(declaringClass.getName(), methodRef.name())` matches a resolved target from `ReachabilityIndex.reachesTargetSignatures()`
- **AND** Soot's SPARK call graph does NOT contain that target as a vertex
- **THEN** `findDirectTargetCallersByBytecodeScan` (renamed from `findDirectMopCallersByBytecodeScan`) MUST detect the invocation by walking the method's `Body.getUnits()`, casting each to `Stmt`, and inspecting `InvokeExpr.getMethodRef()` against the precomputed `Set<String>` of `"className#methodName"` keys
- **AND** the detection MUST be independent of the call graph
- **AND** the matched method MUST be unioned into `directTargetSet` after `findDirectTargetCallers` completes
- **AND** the output JSON MUST report `directlyReachesTarget=true` for that method
- **AND** the implementation MUST log scan statistics

#### Scenario: Bytecode-scan resilience on corrupted method bodies

- **WHEN** the bytecode scanner attempts `method.retrieveActiveBody()` and Soot raises a `RuntimeException` or `OutOfMemoryError` on a single application method
- **THEN** the scanner MUST catch the throwable, emit a WARN log, and `continue` to the next method
- **AND** the body-retrieval skip MUST be counted in the `bodies_skipped` log statistic
- **AND** the scanner MUST NOT abort the analysis

#### Scenario: Bytecode-scan scope is limited to application classes

- **WHEN** the bytecode scanner runs as part of the `ReachabilityEngine`
- **THEN** it MUST iterate only the `appClasses` map produced by `extractClasses` (filtered by `code_package`)
- **AND** it MUST NOT iterate every class in `Scene.v().getClasses()`
- **AND** the union with `directTargetSet` MUST never report a library class as a direct target caller

#### Scenario: JsonReportWriter purity — no runtime ReachabilityIndex lookup

- **WHEN** the post-decomposition `JsonReportWriter.write(ReportModel, Path)` is invoked
- **THEN** the writer MUST NOT hold any reference to `ReachabilityIndex` (verified by absence of import and absence of constructor parameter)
- **AND** every flag in the emitted JSON (`reachesTarget`, `directlyReachesTarget`, future `handlerReachesTarget`, etc.) MUST be read directly from the `ReportModel` fields populated upstream by `ReachabilityEnricher` (INV-ANA-30)

#### Scenario: JsonSchema.Keys ↔ _JK parity

- **WHEN** the parity test `tests/parity/json_keys.py` runs in CI
- **THEN** it MUST execute a small Java helper (`JsonSchemaKeysDump`) via subprocess that uses reflection (`Arrays.stream(JsonSchema.Keys.class.getDeclaredFields()).filter(Modifier::isStatic).map(f -> f.get(null))`) and prints the values one-per-line
- **AND** it MUST import `_JK` from Python and collect `set(_JK.__dict__.values())`
- **AND** the two sets MUST be equal (INV-ANA-32)
- **AND** the test MUST fail with a diff listing keys only in Java vs only in Python if they diverge
- **AND** the test MUST NOT rely on text-level regex against the `.java` source (fragile to Javadoc, multi-line concatenation, comments)

#### Scenario: MatchPolicy has no CLI flag

- **WHEN** any caller inspects the `rv-static-analysis` `argparse.ArgumentParser`
- **THEN** there MUST be no argument named `--match-mode`, `--matching`, `--lenient`, `--strict`, or any equivalent that would override policy at the CLI level (INV-ANA-36)
- **AND** the assertion is verified by `tests/cli/test_no_match_mode_flag.py` walking `parser._actions` for forbidden option strings

#### Scenario: G_no_legacy_mop CI gate finds zero legacy references

- **WHEN** the CI gate `tests/parity/no_legacy_mop.py` runs `git grep -nE "reachesMop|directlyReachesMop|mopMethods|handlerReachesMop|handlerDirectlyReachesMop|reaches_mop|directly_reaches_mop|handler_reaches_mop|handler_directly_reaches_mop|target_reaches_mop|cov_reaches_mop|\\bMopMethod\\b|loadMopSignatures|resolveMopInScene|findDirectMopCallersByBytecodeScan"` across `rvsec-gator/`, `modules/` (excluding `modules/rv-agent/` — deprecated per CLAUDE.md), and `scripts/`
- **THEN** the only matches MUST be inside the documented exclusion set: `MopSpecsTargetSource.java`, the CLI flag literal `--mop-dir`, the config attribute name `mop_dir`, published CSVs under `results/` and `experimento-*/`, archived OpenSpec deltas under `openspec/changes/archive/`, and historical commit messages
- **AND** zero matches MUST appear in any other location
- **AND** on any extra match the gate MUST exit non-zero with the file:line of each unexpected hit (INV-ANA-37)

#### Scenario: JsonReportWriter contains no inline string literals for JSON keys

- **WHEN** the audit `tests/parity/no_json_literals.py` parses `JsonReportWriter.java` and counts string literals that match the pattern `"[a-z][a-zA-Z0-9]*"` outside of `JsonSchema.Keys.*` references
- **THEN** the count MUST be zero
- **AND** the test MUST fail with the offending line numbers if any inline literal is found

#### Scenario: JimpleDefUtils replaces duplicated helpers in MenuExtractor and SpinnerItemExtractor

- **WHEN** the post-extraction GATOR jar is inspected
- **THEN** `presto.android.util.JimpleDefUtils` MUST exist with public static methods `definitionRhs(Unit, Local)`, `resolveInt(Value)`, `resolveStr(Value)`
- **AND** `MenuExtractor.java` and `SpinnerItemExtractor.java` MUST contain zero private duplicates of those helpers (grep within those two files yields zero hits for `private.*definitionRhs|private.*resolveInt|private.*resolveStr`)
- **AND** `MenuExtractor` and `SpinnerItemExtractor` MUST invoke the helpers via `JimpleDefUtils.*` qualified calls

