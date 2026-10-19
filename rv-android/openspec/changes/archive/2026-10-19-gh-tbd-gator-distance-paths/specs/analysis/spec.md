## Purpose

GATOR's static-analysis document answers three questions about every app method:
- is it `reachable` from what the Android runtime enters (the coverage denominator, FR12)?
- does it reach a monitored target (`reachesTarget`, `directlyReachesTarget`)?
- how many calls away is each target (`targetDistances`, gh120)?

All three come from the SPARK call graph that Soot builds with `all-reachable:true`, extended by the lambda wrapper edges (INV-ANA-77). `reachable` comes from a forward breadth-first search seeded by the entry points. The two target flags and the distances come from reverse searches seeded by the targets.

On 2026-10-19 the analysis of the `e03igg` campaign compared the document with what ran on the device. Of the 495 app methods that call the JCA directly, in 81 APKs, 279 were marked not `reachable`, and 63 of those ran (RVSEC-COV), 10 of them misuse sites. Three defects explain the 63:

- **The callback complement does not propagate.** Widget handlers and lifecycle callbacks were added to the reachable set after the forward search had finished. A method a handler calls stayed unreachable unless an entry point also reached it. In `org.cry.otp_31`, `Home$1.onClick` was `reachable` and `HOTP.hmac_sha1`, two calls below it, was not.
- **Application and Fragment were not entry points.** The search was seeded by activities and manifest services, receivers and providers. In `app.maskan.chat_90`, `MaskanApplication.onCreate` calls `initDatabaseEncryption` and neither was `reachable`.
- **The call graph loses edges.** SPARK resolves `x.m()` through the objects `x` may point to, and learns those objects from allocation sites. The Android framework creates activities, fragments and the application object by reflection, and Hilt and koin hand objects out of `java.util` maps, whose bodies Soot does not load (`-no-bodies-for-excluded`). So `this` inside an activity, and a field holding an injected object, point to nothing, and a virtual call on them gets no edge. In `org.fedorahosted.freeotp_48`, `Activity.onNewIntent` calls `this.addToken(…)` and the graph has no such edge. Static calls and calls to private methods are resolved by name and keep their edges.

The first two defects affect only `reachable`, which the derive and the APE-RV jar do not read. The third affects `reachesTarget` and the distances too.

This delta repairs the three:
- The callbacks become seeds of the forward search.
- The `Application` subclass and every app `Fragment`, `ListenableWorker`, RecyclerView `Adapter` and `ViewHolder` subclass contribute entry points.
- Every instance-invoke site in an app method that SPARK left without an edge receives an edge to each concrete app method the call can dispatch to. Dispatch is resolved from the statically named method over the class the invoke instruction names and its app subtypes, which is the same remedy `LambdaEdges` applies to lambda receivers.

Sites SPARK resolved keep exactly their edges, and no edge into library code is added. So `directlyReachesTarget` (every target is a library method) and `distanceTargets` do not move. `reachable`, `reachesTarget` and `targetDistances` grow.

It also adds **distance paths**, for the analyser's use as a stand-alone tool. A distance says how far a target is but not through which calls. With the client parameter `distancePaths=true`, GATOR writes, for every pair it writes, the call path its search followed. The path is stored as steps `[i, v, n]` ("towards target `i`, method `v` calls method `n`") over a table `pathMethods` of the methods that occur on a path, library methods included. The paths cost nothing when the parameter is off. They are computed in a second pass over the targets, after the pairs to be written are known, so the first pass keeps its memory, and they are deterministic, because the searches visit callers in signature order. The campaign readers drop the two members while streaming. Neither `StaticAnalysisData` nor the MOP artifact changes because a document carries them. A subcommand, `rv-static-analysis path`, prints a method's chains in readable form.

## Data Contracts

### Input
- `-clientParam distancePaths=true|false` — GATOR client parameter; absent or any value other than `true` (case-insensitive) writes no path (source: `RVStaticAnalysisConfig.get_tool_command`, `modules/rv-static-analysis/src/rv_static_analysis/config.py`)
- `RVStaticAnalysisConfig.distance_paths: bool = False` and `--distance-paths` on the `analyze` and `batch` subcommands (source: the operator)
- `rv-static-analysis path DOC METHOD [--target I]` — a document written with `distancePaths=true`, a method's Soot signature, and optionally a target index (source: the operator)
- `AndroidManifest.xml` `<application android:name="…">` — the Application subclass, resolved against the manifest package as activity names are (source: the decoded APK, read by `DefaultXMLParser`)

### Output
- `pathMethods: list[str]` — top-level, only with `distancePaths=true`: the Soot signatures of the methods that occur in some step, app and library, sorted by signature; the index space of `distancePaths` (destination: stand-alone readers of the document)
- `distancePaths: list[[int, int, int]]` — top-level, only with `distancePaths=true`, written right after `reachability`: steps `[i, v, n]`, `i` an index into `distanceTargets`, `v` and `n` indices into `pathMethods`, sorted by `(i, v)`, at most one step per `(i, v)` (destination: same)
- `path` subcommand stdout — for each target of the method's written pairs, sorted by `i`: one header line `[i] d=<d> <target signature>` followed by the `d + 1` signatures of the chain from the method to the target, one per line, indented by two spaces (destination: the operator)
- `reachability[].methods[].reachable`, `reachesTarget`, `targetDistances` — as today, computed over the extended entry points and call graph (destination: `rv-static-analysis` parser, `aperv-tool` derive, coverage)

### Side-Effects
- **[Soot call graph]**: `EmptySiteEdges.addTo` adds edges to `Scene.v().getCallGraph()` before the reachability search, and the client removes the same edges after the distances and the distance paths, before the fragment windows and the WTG; the WTG never reads them, with `cgDelegation=true` either

### Error
- A failure inside `EmptySiteEdges.addTo` is logged and the analysis continues on the graph as it stands, as `LambdaEdges` failures are; a method whose body cannot be retrieved is skipped
- A failure of the path pass costs only `pathMethods` and `distancePaths`; the rest of the document is written
- `rv-static-analysis path` exits 1 with one stderr line when the document carries no `distancePaths`, when the method is not in the document, or when `--target` names a target the method has no written pair for
- `rv-static-analysis compact` exits 1 on an input carrying `distancePaths` (Requirement: Offline Conversion of a Full Document to the Compact Form)

## Invariants

- **INV-ANA-90**: For the same analysis state, the document written with `distancePaths=true` SHALL equal the one written without it apart from the members `pathMethods` and `distancePaths`, which only the former carries.
- **INV-ANA-91**: For every pair `[i, d]` written on a method `m`, the steps SHALL hold a chain `m = v_0 → v_1 → … → v_d = t_i`, where `t_i` is `distanceTargets[i]` and each `v_k → v_(k+1)` is one step `[i, v_k, v_(k+1)]` and an edge of the call graph the distance searches walk. A pair with `d = 0` needs no step.
- **INV-ANA-92**: Two runs over the same call graph and target list SHALL write the same `pathMethods` and `distancePaths`: each search visits a method's callers in signature order and its queue is first-in first-out.
- **INV-ANA-93**: Every step SHALL lie on the chain of at least one written pair. In compact mode the steps SHALL be the union of the chains of the pairs compact mode keeps (INV-ANA-85); in full mode, of every pair.
- **INV-ANA-94**: The reachable set SHALL contain every method the call graph reaches from an entry point or from a member of the callback set (activity lifecycle handlers, GUI event handlers, Service/Receiver/Provider lifecycle methods).
- **INV-ANA-95**: The entry points SHALL include:
  - the lifecycle and public/protected methods of the manifest's Application subclass, when the manifest names one present in the Scene;
  - the public/protected methods of every app class with `android.app.Fragment`, `android.support.v4.app.Fragment` or `androidx.fragment.app.Fragment` among its superclasses;
  - the `doWork` and `startWork` methods of every app class with `androidx.work.ListenableWorker` among its superclasses;
  - the public methods of every app class with `androidx.recyclerview.widget.RecyclerView$Adapter`, `androidx.recyclerview.widget.RecyclerView$ViewHolder` or their `android.support.v7.widget` counterparts among its superclasses.
- **INV-ANA-96**: After `EmptySiteEdges.addTo`, at every instance-invoke site of a concrete app method that held no outgoing call-graph edge after SPARK and `LambdaEdges`, the call graph SHALL hold an edge to each concrete app method obtained by dispatching the invoked method over the class the invoke instruction names and its app subtypes (the resolved method itself for a special invoke). A site that held an edge SHALL keep exactly its edges, and no edge to a library method SHALL be added. Those edges SHALL be in the call graph for the reachability search, the distances and the distance paths only: before the fragment windows and the WTG are built, the client SHALL remove every edge `EmptySiteEdges.addTo` added, so `windows` and `transitions` equal what the call graph without them gives.
- **INV-ANA-98**: For a method `m` and a target `i` it carries a written pair `[i, d]` for, `rv-static-analysis path` SHALL print exactly the `d + 1` methods of the chain INV-ANA-91 defines, from `m` to `t_i`, in order.
- **INV-ANA-97**: `read_analysis_document` SHALL drop `pathMethods` and `distancePaths` under every `PairPolicy`. The `StaticAnalysisData` parsed from a document and the `*.mop.json` derived from it SHALL be the same with and without those members.

## ADDED Requirements

### Requirement: Callbacks Seed the Reachability Search (FR04, FR06, FR12)

`ReachabilityEngine.run()` SHALL collect the callback set before the forward search. The set is the activity lifecycle handlers, the event handlers of every GUI object reachable from an activity root, and the Service, Receiver and Provider lifecycle methods. The engine SHALL seed `multiSourceBfs` with the entry points and that set together. The step that marked callbacks `reachable` after the search, and copied target flags onto them from their direct callees, SHALL be deleted (P3). Both of its effects come out of the searches themselves:
- a callback is a seed, so it is `reachable`;
- a callback with an edge to a target is found by `findDirectTargetCallers`, and one that reaches a target is found by the reverse search.

Seeding is what makes a method that only a handler calls `reachable`. A widget handler is invoked by the framework, not by any app code SPARK sees. Marking the handler alone left everything below it unreachable unless an entry point also reached it.

#### Scenario: A method two calls below a widget handler becomes reachable
- **WHEN** `org.cry.otp_31.apk` is analysed, where `Home$1.onClick(View)` is a widget handler GATOR resolves and the call graph holds `Home$1.onClick → HOTP.gen → HOTP.generateOTP → HOTP.hmac_sha1`
- **THEN** `HOTP.gen`, `HOTP.generateOTP` and `HOTP.hmac_sha1` SHALL carry `reachable: true`
- **AND** `Home$1.onClick` SHALL carry `reachable: true` and `reachesTarget: true`, as before this change

#### Scenario: The target flags of callbacks are unchanged by the seeding
- **WHEN** the same APK is analysed before and after the callback step is replaced by seeding, with the empty-site edges disabled in the test harness
- **THEN** every method's `reachesTarget` and `directlyReachesTarget` SHALL be equal in the two documents

### Requirement: Framework-Created Component Entry Points (FR04, FR12)

`XMLParser` SHALL expose `getApplicationClassName()`, the class named by `<application android:name>` resolved against the manifest package, or `null` when the attribute is absent. When the class is present in the Scene, `getEntryPoints` SHALL add its lifecycle methods (`onCreate`, `onTerminate`, `onConfigurationChanged`, `onLowMemory`, `onTrimMemory`, `attachBaseContext`) and its public and protected methods. A missing class SHALL be logged as a missing service class is.

`getEntryPoints` SHALL also add the public and protected methods of every app class with `android.app.Fragment`, `android.support.v4.app.Fragment` or `androidx.fragment.app.Fragment` among its superclasses. This applies to every such class, whether or not an activity is found to host it. The fragment base names SHALL be the set `FragmentViewFlow.FRAGMENT_BASES` (sootandroid) holds, made public and read by `FragmentHostResolver` and `getEntryPoints`, so the three users read one declaration instead of two copies.

`getEntryPoints` SHALL also add:
- the `doWork` and `startWork` methods of every app class with `androidx.work.ListenableWorker` among its superclasses. WorkManager calls them; `Worker`, `CoroutineWorker` and `RxWorker` are its subclasses;
- the public methods of every app class with `androidx.recyclerview.widget.RecyclerView$Adapter`, `androidx.recyclerview.widget.RecyclerView$ViewHolder` or their `android.support.v7.widget` counterparts among its superclasses. RecyclerView calls `onCreateViewHolder`, `onBindViewHolder`, `getItemCount` and the holder's methods while a list is on screen.

All four kinds are created or driven by the framework or a library, so nothing in the app's code calls their entry methods. Without them, the code an application object, a fragment, a worker or a list runs on its own is unreachable, even when the call graph holds every edge below it. `androidx.lifecycle.ViewModel` is deliberately not among them. A ViewModel runs only when a screen requests it, so its use is reached from that screen's call, which the empty-site edges restore, and taking its methods by hierarchy would also mark ViewModels no screen uses.

#### Scenario: The Application's onCreate is an entry point
- **WHEN** `app.maskan.chat_90.apk` is analysed, whose manifest names `app.maskan.chat.MaskanApplication` and whose `MaskanApplication.onCreate` calls `initDatabaseEncryption`
- **THEN** `MaskanApplication.onCreate` and `MaskanApplication.initDatabaseEncryption` SHALL carry `reachable: true`

#### Scenario: A manifest without an Application subclass
- **WHEN** the manifest's `<application>` element has no `android:name`
- **THEN** `getApplicationClassName()` SHALL return `null`
- **AND** the entry points SHALL be the ones the other component kinds give

#### Scenario: A worker's doWork is an entry point
- **WHEN** an app class `SyncWorker extends androidx.work.CoroutineWorker` declares `doWork(Continuation)`, which calls `HttpClientFactory.getClient`
- **THEN** `SyncWorker.doWork` and `HttpClientFactory.getClient` SHALL carry `reachable: true`

#### Scenario: An adapter's bind method is an entry point
- **WHEN** an app class `EntryAdapter extends androidx.recyclerview.widget.RecyclerView$Adapter` declares `public void onBindViewHolder(EntryHolder, int)`, which calls `EntryHolder.getOtp`
- **THEN** `EntryAdapter.onBindViewHolder` and `EntryHolder.getOtp` SHALL carry `reachable: true`

#### Scenario: A ViewModel's method is not an entry point by itself
- **WHEN** an app class `EditViewModel extends androidx.lifecycle.ViewModel` declares `public void saveNote()` and no entry point reaches it through the call graph
- **THEN** `EditViewModel.saveNote` SHALL carry `reachable: false`

#### Scenario: A fragment method is an entry point
- **WHEN** an app class `SettingsFragment extends androidx.preference.PreferenceFragmentCompat`, itself a subclass of `androidx.fragment.app.Fragment`, declares `public void onCreatePreferences(Bundle, String)`
- **THEN** `SettingsFragment.onCreatePreferences` SHALL be an entry point and SHALL carry `reachable: true`

### Requirement: Empty-Site Edges in the Reachability Call Graph (FR04, FR06)

Before the reachability search, and after the lambda wrapper edges, the client SHALL run `EmptySiteEdges.addTo(Scene.v().getCallGraph(), appClasses)` (`client/.../clients/reach/EmptySiteEdges.java`). For every concrete method of an app class whose body can be retrieved, and for every statement of it holding an instance invoke (virtual, interface or special) with no outgoing edge in the call graph, it SHALL add one edge from that statement to each callee below:

- for a special invoke, the method the reference resolves to, when it is a concrete app method;
- for a virtual or interface invoke, every concrete app method that dispatching the invoked method's sub-signature yields on the class the invoke instruction names, when that class is a concrete app class, and on each concrete app subclass or implementer of it.

Static invokes, sites that hold at least one edge, and callees in library classes SHALL be left alone. The pass SHALL log the number of instance-invoke sites, of empty sites, of edges added, and the largest number of callees added at one site.

SPARK leaves a site empty when the receiver's points-to set is empty. On Android that is the normal state of any object the framework, reflection or a DI container creates, because Soot sees no allocation for it:
- `this` of an activity, fragment, application or service;
- a ViewModel obtained from a provider;
- a field holding an injected dependency.

Resolving such a site by the class the invoke names is the class-hierarchy answer SPARK would have given if it had known nothing. Keeping it to app callees and to empty sites leaves every call SPARK resolved unchanged. It also leaves `directlyReachesTarget` and `distanceTargets` unchanged, because every target is a library method. A site that is truly dead also receives edges. That over-approximates `reachesTarget` and the distances, the same way the bytecode-scan complement over-approximates the direct set.

`addTo` SHALL return the edges it added. After the distances and, when requested, the distance paths are computed, the client SHALL remove those edges from the call graph, before the fragment windows and the WTG. With `cgDelegation=true` the WTG builds its transitions from the Soot call graph. Measured on 2026-10-19 with the edges left in place, the WTG ran up to 12 times longer (the client on `org.fedorahosted.freeotp_48` went from 40 s to 269 s, of which 3.8 s outside the WTG), and the transitions of `net.gaast.giggity_769` went from 431 to 1,622. Among the new transitions, some are real: a click that calls `ScheduleViewActivity.showItem` opens `ScheduleItemActivity`. Others are false: `EventDialog$ShareButton.onClick` only opens a share chooser, yet it gained a transition to `ScheduleItemActivity` through a wide interface dispatch. A WTG built on these edges needs its own evaluation, so this change keeps them out of it.

#### Scenario: A call on `this` inside an activity gets its edge
- **WHEN** `org.fedorahosted.freeotp_48.apk` is analysed, where `Activity.onNewIntent(Intent)` holds `invoke-virtual this.addToken(Uri, boolean)` and SPARK gives the site no edge
- **THEN** the call graph SHALL hold an edge from that site to `Activity.addToken(Uri, boolean)`
- **AND** `Activity.onNewIntent` SHALL carry `reachesTarget: true` and the pair `[i, 2]` for `Token.parse(Uri)` at index `i`
- **AND** `Activity.addToken` SHALL carry `reachable: true`

#### Scenario: A call through an injected field gets its edge
- **WHEN** `com.kin.easynotes_14.apk` is analysed, where `NoteUseCase.encryptNote` loads `this.encryptionHelper` and invokes `EncryptionHelper.encrypt(String)`
- **THEN** `NoteUseCase.encryptNote` SHALL carry `reachesTarget: true` and the pair `[j, 1]` for `EncryptionHelper.encrypt` at index `j`

#### Scenario: A resolved site is not touched
- **WHEN** a site holds the SPARK edge `A.run → B.work` and `B` has an app subclass `C` overriding `work`
- **THEN** the pass SHALL add no edge from that site, and `A.run → C.work` SHALL be absent unless SPARK produced it

#### Scenario: An interface call fans out to the app implementers
- **WHEN** an empty site invokes `Repo.load()` on the interface `Repo`, implemented by the app classes `DbRepo` and `NetRepo`, and by the library class `androidx.room.RoomRepo`
- **THEN** the pass SHALL add edges to `DbRepo.load` and `NetRepo.load`
- **AND** it SHALL NOT add an edge to `androidx.room.RoomRepo.load`

#### Scenario: The WTG is built without the empty-site edges
- **WHEN** `net.gaast.giggity_769.apk` is analysed with `cgDelegation=true`, and `EmptySiteEdges.addTo` adds 761 edges
- **THEN** `reachable`, `reachesTarget` and `targetDistances` SHALL be computed with those edges
- **AND** `windows` and `transitions` SHALL equal those of the same analysis without the edges, transitions compared as a set (their order follows identity hashing)

### Requirement: Distance Paths (FR06, NFR05, NFR08)

`RvsecAnalysisClient` SHALL read the client parameter `distancePaths` as it reads `fullOutput`. When it is `true` (case-insensitive), the client SHALL write `pathMethods` and `distancePaths` right after `reachability`, in both writes of a run (pre-WTG and final) and in both output modes. Otherwise it SHALL write neither. The member names SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

The paths SHALL be computed by `TargetDistances` in a second pass, after the distances. The pass first determines, for every app method, the pairs the output mode writes:
- every pair in full mode;
- the pairs `TargetDistances.compact` keeps in compact mode.

Then, for each target `i` that one of those pairs names, it repeats the reverse search from target `i` and records, for each method first visited from a callee, that callee. The pass SHALL then follow the recorded callees from each written pair's method down to the target, and SHALL emit each step `[i, v, n]` on those chains once.

`pathMethods` SHALL hold the signatures of the methods that appear in some step, sorted by signature. `distancePaths` SHALL hold the steps with `v` and `n` as indices into it, sorted by `(i, v)`.

The second pass is what keeps the cost of the first unchanged. Compact mode's rank rule needs every target's pairs of a method before it can say which pair survives. Recording predecessors during the first pass would hold one entry per visited method per target for the whole run, library methods included. Repeating only the searches that some written pair needs holds one target's predecessors at a time.

A step says that the search found `n` one call closer to the target than `v`. It does not imply that `v` carries a written pair for `i`: in compact mode an intermediate method's own pair for `i` may be reduced away while a farther method's pair, kept by rank, still passes through it. Library methods appear only in `pathMethods` and in steps, never in `reachability`.

#### Scenario: The path of a handler two calls from a direct caller
- **WHEN** an app has `A.onClick → A.save → Crypto.encrypt`, `Crypto.encrypt` calls the target `javax.crypto.Cipher.doFinal`, `distanceTargets[i]` is `Crypto.encrypt`, and the analysis runs with `distancePaths=true`
- **THEN** `A.onClick` SHALL carry `[i, 2]`
- **AND** `distancePaths` SHALL hold `[i, p(A.onClick), p(A.save)]` and `[i, p(A.save), p(Crypto.encrypt)]`, where `p(x)` is the index of `x` in `pathMethods`

#### Scenario: A path through a library method
- **WHEN** an app method `UI.onClick` calls the library method `kotlinx.coroutines.BuildersKt.launch`, whose graph edges reach the app method `Repo.save`, which is `distanceTargets[j]`, and `UI.onClick` carries `[j, 2]`
- **THEN** `pathMethods` SHALL contain the signature of `kotlinx.coroutines.BuildersKt.launch`
- **AND** the chain from `UI.onClick` SHALL pass through it

#### Scenario: Equally short paths are chosen the same way on every run
- **WHEN** `M` reaches target `i` at distance 2 both through `A` and through `B`, with `A`'s signature sorting before `B`'s
- **THEN** every run over the same call graph SHALL write the step `[i, p(M), p(A)]`
- **AND** no run SHALL write `[i, p(M), p(B)]`

#### Scenario: Compact mode keeps the steps of the kept pairs only
- **WHEN** a method carries, in full mode, pairs at distances 1, 2, 3 and 6 for four targets, and the analysis runs in compact mode with `distancePaths=true`
- **THEN** the pair at distance 6 is not written (INV-ANA-85), and no step SHALL exist that lies only on its chain
- **AND** the chains of the three kept pairs SHALL be complete (INV-ANA-91)

#### Scenario: The parameter off leaves the document as it is
- **WHEN** the same APK is analysed with `distancePaths=true` and without the parameter
- **THEN** the two documents SHALL differ only by `pathMethods` and `distancePaths` (INV-ANA-90)

#### Scenario: `rv-static-analysis` passes the parameter
- **WHEN** `rv-static-analysis analyze app.apk --distance-paths` builds the GATOR command
- **THEN** the command SHALL contain `-clientParam distancePaths=true`
- **AND** without `--distance-paths` it SHALL contain no `distancePaths` parameter

### Requirement: Path Query Subcommand (FR06, NFR05)

`rv-static-analysis` SHALL provide the subcommand `path DOC METHOD [--target I]`, implemented in `modules/rv-static-analysis/src/rv_static_analysis/path_query.py`. It SHALL read `DOC` in one streaming pass of its own with `ijson` (C backend), because `read_analysis_document` drops the path members (INV-ANA-97). From that pass it SHALL keep:
- `distanceTargets`;
- `pathMethods`;
- `distancePaths`;
- the `targetDistances` of the one `reachability[].methods[]` entry whose `signature` equals `METHOD`.

For each pair `[i, d]` of that method, sorted by `i`, or for the one pair with `i = I` when `--target` is given, it SHALL follow the steps from `METHOD` to `distanceTargets[i]`. It SHALL print a header line `[i] d=<d> <target signature>`, then the chain's `d + 1` signatures, one per line, indented by two spaces (INV-ANA-98).

It SHALL exit 1 with one line on stderr naming the document and the reason when:
- the document carries no `distancePaths`;
- `METHOD` has no entry in `reachability`;
- `METHOD` carries no pair for the target `--target` names;
- a chain breaks (a step is missing, or a chain does not have `d` steps): the document does not satisfy INV-ANA-91.

A method with no pair at all exits 0 and prints nothing. It is a valid answer: the method reaches no target within `DIST_MAX`.

The subcommand exists because the steps are indices into a table and are not readable by eye. Reading them in its own pass keeps the campaign reader's contract unchanged. It holds the method table and the steps, which for a compact document are a few times the size of the pairs (about 0.1 MB for `com.kin.easynotes_14`).

#### Scenario: The chains of a handler
- **WHEN** `rv-static-analysis path cryotp.json "<org.cry.otp.Home$1: void onClick(android.view.View)>"` runs on a document of `org.cry.otp_31.apk` written with `distancePaths=true`, where `Home$1.onClick` carries `[k, 3]` for `HOTP.hmac_sha1`
- **THEN** it SHALL exit 0
- **AND** stdout SHALL contain the line `[k] d=3 <org.cry.otp.HOTP: byte[] hmac_sha1(byte[],byte[])>` followed by the four signatures `Home$1.onClick`, `HOTP.gen`, `HOTP.generateOTP`, `HOTP.hmac_sha1`, each indented by two spaces

#### Scenario: One target requested
- **WHEN** the same command runs with `--target k`
- **THEN** stdout SHALL hold only the block for target `k`

#### Scenario: A document without paths is refused
- **WHEN** the document was written without `distancePaths=true`
- **THEN** the subcommand SHALL exit 1 with a message naming the document and saying that it carries no `distancePaths`

#### Scenario: An unknown method is refused
- **WHEN** `METHOD` names no method in `reachability`
- **THEN** the subcommand SHALL exit 1 with a message naming the method

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

2. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. Entry points include: Activity lifecycle handlers and public/protected methods (via `output.getActivities()`), Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`) and public/protected methods (via `XMLParser.getServices()`), BroadcastReceiver lifecycle method (`onReceive`) and public/protected methods (via `XMLParser.getReceivers()`), ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`) and public/protected methods (via `XMLParser.getProviders()`), the `Application` subclass named by the manifest's `<application android:name>` (lifecycle methods and public/protected methods, via `XMLParser.getApplicationClassName()`), and the public/protected methods of every app subclass of `android.app.Fragment`, `android.support.v4.app.Fragment` or `androidx.fragment.app.Fragment` and the `doWork`/`startWork` of every app `ListenableWorker` subclass and the public methods of every app RecyclerView `Adapter` and `ViewHolder` subclass (Requirement: Framework-Created Component Entry Points). The callbacks the complement collects are seeds of the same forward search (Requirement: Callbacks Seed the Reachability Search). Before the search, the call graph receives the lambda wrapper edges (INV-ANA-77) and the empty-site edges (Requirement: Empty-Site Edges in the Reachability Call Graph). For each application method, the `ReachabilityEngine` computes: `reachable` (reachable from entry points), `reachesTarget` (has path to a resolved target method — renamed from `reachesMop`), and `directlyReachesTarget` (directly invokes a resolved target method — renamed from `directlyReachesMop`). The `ReachabilityIndex` materializes these as `Set<String>` for O(1) lookup. This section is written and flushed first.

3. **Extracts windows and widgets** using GATOR's internal APIs (`getActivities()`, `getActivityRoots()`, `getDialogs()`, `getDialogRoots()`, `getOptionsMenu()`, `PropertyManager`). GATOR's interprocedural analysis provides the widget inventory (IDs, names, types, text, hint, listeners) including dynamically-registered listeners. Widget XML attributes not available via GATOR APIs — `inputType`, `entries` (from `android:entries="@array/X"`), and the four attributes `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` — are extracted by `enrichFromXml()` from the decoded layout XML files at `Configs.resourceLocation`. The `windows[]` section is written in both the partial-JSON path (after reachability, with `wtg=null`) and the full-JSON path (after WTG completion, with the WTG handle for numeric ID assignment and catch-all enumeration).

4. **Extracts the Window Transition Graph** using GATOR's `WTGBuilder` and `WTGAnalysisOutput`, producing window IDs, transition edges with event types, widget IDs, and handler signatures. WTG construction MUST use `Scene.v().getCallGraph()` (the SPARK CG already built by Soot) as the single source of virtual-dispatch resolution when the `cgDelegation` client parameter is `true`; `AndroidCallGraph.v()` MUST NOT be populated by `FlowgraphRebuilder.buildCallGraph()` in this mode (INV-ANA-21). The legacy `AndroidCallGraph` rebuild via `FlowgraphRebuilder.buildCallGraph()` MUST be preserved behind `cgDelegation=false` (default after the M3 paridade-gate decision in `docs/20260515_diagnostico_paridade_cgdelegation.md`), where rollback is bit-for-bit. Edges to library classes quarantined by SPARK's `IGNORED_CLASSES` are recovered via a WTG-level bytecode-scan complement (INV-ANA-22). WTG construction is skipped entirely when the `skipWtg` client parameter is `true` (see the `skipWtg` ADDED requirement), in which case `transitions[]` is emitted as an empty array.

5. **Extracts non-Activity components** (Services, BroadcastReceivers, ContentProviders) from `XMLParser.getServices()`, `XMLParser.getReceivers()`, and `XMLParser.getProviders()`, enriched with intent-filters from `IntentFilterManager`, `android:exported` attribute, and target reachability cross-referenced with the reachability BFS results. This section is written and flushed last.

6. **Emits sentinel `"complete": true`** as the final top-level field, after all sections are flushed. Parser uses this to distinguish a successful run from a truncated one (INV-ANA-31).

The callback set — activity lifecycle handlers, the event handlers of every GUI object GATOR resolves, and Service, Receiver and Provider lifecycle methods — MUST seed the forward reachability search together with the entry points, so every method a callback reaches through the call graph is `reachable` (INV-ANA-94). The target flags of a callback come from the same searches as every other method's: a callback with an edge to a target is in the call-graph direct set, and a callback that reaches one is in the reverse search, so no step after the searches adds a flag.

Each entry in `reachability[]` MUST include `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null` when the method belongs to no component) and `isMain` (boolean) fields. The legacy `isActivity` and `isMainActivity` fields are removed (no shim — P3). The `StaticAnalysisParser` (Python) MUST parse the new fields into the `Clazz` domain model as `component_type: str | None` and `is_main: bool`. The `null` handler exists because `getSootClassUnsafe` may return `null` for methods declared on synthetic or excluded classes; the producer emits `componentType=null` rather than dropping the entry, preserving the reachability set cardinality.

All JSON keys MUST be emitted via constants in `presto.android.gui.clients.json.JsonSchema.Keys` (Java) and consumed via `_JK = SimpleNamespace(...)` in `rv_static_analysis.parser.static.static_analysis_parser` (Python). The two constant sets MUST be value-equal (INV-ANA-32) — verified by `tests/parity/json_keys.py`.

The analysis JSON output is parsed by `StaticAnalysisParser` into the `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph, Components, `complete: bool`). Downstream consumers (rv-coverage, rv-platform, rv-experiment, aperv-tool, scripts) receive renamed Pydantic fields per the `core` spec delta. rv-agent (deprecated) is not a live consumer; sweep regenerates JSONs and breaks rv-agent's stale reader by design.

The reachability section defines the **method universe** — the total set of reachable methods that serves as the denominator for all coverage percentage calculations. Without reachability data, the system can count absolute method calls but cannot compute coverage percentages.

The reachability section also provides target prioritization data consumed by agents. The agent's action ranker assigns score boosts to actions whose handler method has `directly_reaches_target=true` or `reaches_target=true` (consumer side details outside this spec).

The call graph is built using SPARK (`-cgAlgorithm spark`) with `all-reachable:true`, which performs full points-to analysis to resolve virtual calls based on types effectively instantiated in the program. A receiver whose object is created by the Android framework, by reflection or by a dependency-injection container has no allocation site SPARK follows, so SPARK leaves such a call site without an edge; the empty-site edges restore those calls among app methods (INV-ANA-96). SPARK is the operational default. Other algorithms — CHA, RTA, VTA — remain available. JCA framework classes appear as call targets whenever any application method invokes them — they do not need to be entry points.

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

### Requirement: Per-Target Call-Graph Distance (FR06)

The client SHALL compute, after the reachability search and before the pre-WTG write, one reverse breadth-first search per direct caller `c ∈ C` over the call graph with self-loops dropped (the graph the reachability search walks, lambda edges and empty-site edges included). Each search SHALL visit the callers of a method in the order of their signatures. The order changes no distance, since a breadth-first level does not depend on it; it fixes which of several equally short paths a search finds first, which the distance paths record (INV-ANA-92). The search SHALL stop at depth `DIST_MAX = 10` and SHALL record the depth at which it first visits each app method. C SHALL be the app methods in the `directlyReachesTarget` set, sorted by signature, and SHALL be written as `distanceTargets`; each app method's pairs SHALL be written as `targetDistances` inside its `reachability[].methods[]` entry. The keys SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

Which of a method's pairs are written depends on the output mode (Requirement: Compact and Full Output Modes of the Analysis Document). Full mode writes every pair the searches recorded. Compact mode, the default, writes the pairs at `d ≤ 3` and the 3 nearest by `(d, i)` (INV-ANA-85). The searches themselves do not depend on the mode.

The reachability search keeps its library seeds, so `reachesTarget` keeps its meaning. The distance is seeded by app methods only, because a distance to a library direct caller says nothing a consumer can act on in the app (INV-ANA-73). C entries carry `kind: "direct"`.

The graph is the whole call graph, not the subgraph induced by app methods. Both were measured on 2026-10-07 on 10 APKs against the E6 traces and gave the same answers on every measure (true-handler rank, click lift, no-bind lift); the whole graph keeps INV-ANA-74, and on `com.password.monitor_102` it finds 102 app methods within 10 calls of a target where the app subgraph finds 6, because app callbacks invoked from library code are paths the app subgraph cuts.

#### Scenario: A handler two calls away from a direct caller
- **WHEN** the app has `A.onClick` → `A.save` → `Crypto.encrypt`, and `Crypto.encrypt` calls `javax.crypto.Cipher.doFinal`, a target
- **THEN** `distanceTargets` MUST contain `<Crypto: byte[] encrypt(byte[])>` at some index `i`
- **AND** `A.onClick` MUST carry `[i, 2]`, `A.save` `[i, 1]` and `Crypto.encrypt` `[i, 0]`, in both output modes

#### Scenario: Library direct callers do not seed the distance
- **WHEN** an app method `Net.connect` calls `okhttp3.OkHttpClient.newCall`, a library method that reaches a target only through library code, and no app method calls a target directly
- **THEN** `distanceTargets` MUST hold exactly `{"signature": "<…Net: void connect()>", "kind": "boundary"}`
- **AND** no library method MUST appear in `distanceTargets`
- **AND** `Net.connect`'s `reachesTarget` MUST be `true`, as before this change

#### Scenario: Distance beyond the cap
- **WHEN** an app method reaches `c` only through a call chain of 11 edges
- **THEN** that method MUST NOT carry a pair for `c`
- **AND** its `reachesTarget` MUST still be `true`

#### Scenario: A distant pair is written only in full mode
- **WHEN** a method is 6 calls from target `i` and 1, 2 and 3 calls from three other targets
- **THEN** the full-mode document MUST carry `[i, 6]` on that method
- **AND** the compact-mode document MUST NOT carry it

#### Scenario: Distance survives a WTG timeout
- **WHEN** the analysis of `org.quantumbadger.redreader_117.apk` is killed by the 1,800 s timeout while `WTGBuilder` runs
- **THEN** the partial `.apk.json` MUST contain `distanceTargets` and every `targetDistances` list
- **AND** it MUST NOT contain the `complete` sentinel (INV-ANA-31)

### Requirement: Streaming Read of the Analysis Document (NFR02, NFR04)

`StaticAnalysisParser` (`modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`) SHALL read the analysis document with `ijson` (C backend) in one pass of JSON events, building each top-level member as a Python value except `distanceTargets`, the `targetDistances` member of every `reachability[].methods[]` entry, and the top-level `pathMethods` and `distancePaths` members, whose events SHALL be consumed and discarded without building a value (INV-ANA-80, INV-ANA-97). `read_analysis_document` drops `pathMethods` and `distancePaths` under both pair policies, so neither the parser, the parsed copy nor the `aperv-tool` derive ever holds a path. The section parsers (`_parse_classes`, `_parse_windows`, `_parse_transitions`, `_parse_components`) SHALL receive the same dict shape they receive today, so section independence and graceful degradation (INV-ANA-06) are unchanged.

A document that ends before its root object closes — the producer killed during its write, INV-ANA-31 — SHALL be recovered from the same pass: every top-level member read in full is kept, the member in progress and everything after it are dropped (INV-ANA-81). This is the behaviour `_recover_truncated_json` names, and the name stays. It is a superset of the bracket repair it replaces: that repair closed the root at the last `]` of the text, which failed whenever the last `]` closed a nested list rather than a top-level section.

#### Scenario: a gh120 document parses to the same model without its distances
- **WHEN** the parser reads `cryptoapp.apk.json` (fixture, 38 methods carrying `targetDistances`)
- **THEN** the returned `StaticAnalysisData` SHALL equal the one built from `json.loads` of the file by today's section parsers, class by class, method by method, window by window and transition by transition
- **AND** no `targetDistances` list SHALL have been materialised during the read

#### Scenario: a 2.16 GB document parses inside a campaign container
- **WHEN** the parser reads `org.wikipedia_50595.apk.json` (about 2.16 GB, 39,950 methods)
- **THEN** the process's peak resident memory SHALL stay below 3 GiB
- **AND** the model SHALL carry 39,950 methods and the document's windows and transitions

#### Scenario: a document truncated inside `transitions` keeps the earlier sections
- **WHEN** the file ends inside the 12th element of `transitions`, after `reachability` and `windows` were written in full
- **THEN** `classes` SHALL be populated as from the complete document, and `windows` as from the document without `transitions` (parsing `transitions` back-fills widgets into `windows`)
- **AND** `wtg` SHALL be empty and `complete` SHALL be `False`
- **AND** no exception SHALL reach the caller

#### Scenario: a document with no complete top-level array yields an empty model
- **WHEN** the file ends inside the first element of `reachability`
- **THEN** the parser SHALL return a `StaticAnalysisData` with empty `classes`, `windows` and `wtg`
- **AND** `complete` SHALL be `False`

#### Scenario: a document with distance paths parses to the model of the same document without them
- **WHEN** the parser reads a document GATOR wrote for `org.cry.otp_31.apk` with `distancePaths=true`, and the document of the same analysis without it
- **THEN** the two `StaticAnalysisData` SHALL be equal
- **AND** `<apk_name>.static.json` SHALL carry neither `pathMethods` nor `distancePaths`

### Requirement: Offline Conversion of a Full Document to the Compact Form (NFR04, NFR08)

`rv-static-analysis` SHALL provide the subcommand `compact INPUT OUTPUT`, implemented in `modules/rv-static-analysis/src/rv_static_analysis/compact.py`. It SHALL read `INPUT` with `read_analysis_document(INPUT, PairPolicy.reduce(COMPACT_WEIGHED_MAX, COMPACT_K))` from `rv_android_core.util.analysis_document`, sort each reduced `targetDistances` list by `i`, insert `distancePairs` where GATOR writes it, and write `OUTPUT` in Gson's compact form. Members, member order and values stay as read. Strings are escaped as Gson's `JsonWriter` escapes them with HTML-safe escaping off: `"` and `\` with a backslash, `\t`, `\b`, `\n`, `\r` and `\f` in short form, the other code points below U+0020 and U+2028/U+2029 as lowercase `\u00xx`/` `/` `, and every other character as itself in UTF-8. The output SHALL be the compact document GATOR writes for the same analysis (INV-ANA-87).

The converter exists because GATOR is expensive and the documents already exist. Re-analysing the E6 corpus to get compact documents would cost days of machine time, while the converter needs one streaming pass per document. It never holds the input's text or a dropped pair in memory. It does hold the reduced document, so its memory follows the sections the reduction leaves alone: on the E6 corpus the peak was 1.9 GiB of RSS for `org.fossify.calendar_20` (269 MB of output, almost all `windows`) and 674 MiB for the 9.34 GB `eu.darken.sdmse_10705000`.

The converter SHALL refuse, with exit status 1, one line on stderr naming the input and the reason, and no output file left behind:

- an input whose read reports truncation, because a truncated document is not the document GATOR wrote and its compact form would not be one either;
- an input that already carries `distancePairs`;
- an input that carries `distancePaths`, because the paths of a full document are not reduced here: a compact document with paths is written by GATOR itself, in compact mode with `distancePaths=true`;
- an input holding a number that is not an integer, because GATOR writes only integers and Gson's form of a non-integer is not reproduced;
- an `OUTPUT` that resolves to the same file as `INPUT`.

The output SHALL be written to a temporary file in the directory of `OUTPUT` and renamed onto it, so an interrupted conversion leaves either no file or the previous one.

#### Scenario: converting a gh120 document
- **WHEN** `rv-static-analysis compact org.wikipedia_50595.apk.json /tmp/w.json` runs on the 2.16 GB full document
- **THEN** it SHALL exit 0
- **AND** `/tmp/w.json` SHALL parse to the same top-level members as the input in the same order, plus `distancePairs` right before `distanceTargets`
- **AND** every `targetDistances` in `/tmp/w.json` SHALL equal the input's list reduced by INV-ANA-85

#### Scenario: the converter writes what GATOR writes
- **WHEN** GATOR analyses `cryptoapp.apk` once in full mode and once in compact mode, and the full document is converted
- **THEN** the converted document SHALL be byte-identical to GATOR's compact document whenever the two runs gave the same analysis state; otherwise the two SHALL be equal after window and widget node ids are compared by content (INV-ANA-79's rule, since GATOR's ids depend on identity-hash iteration)

#### Scenario: a truncated input is refused
- **WHEN** the input ends inside the `transitions` section
- **THEN** the converter SHALL exit 1 with a message naming the input and the truncation
- **AND** `OUTPUT` SHALL NOT exist afterwards

#### Scenario: a compact input is refused
- **WHEN** the input carries `distancePairs`
- **THEN** the converter SHALL exit 1 with a message saying the input is already compact

#### Scenario: the converter never overwrites its input
- **WHEN** `rv-static-analysis compact a.json a.json` runs
- **THEN** it SHALL exit 1 and `a.json` SHALL be byte-identical to its content before the call

#### Scenario: an input with distance paths is refused
- **WHEN** the input carries `distancePaths`
- **THEN** the converter SHALL exit 1 with a message naming the input and saying that a compact document with paths is written by GATOR with `distancePaths=true`
- **AND** `OUTPUT` SHALL NOT exist afterwards
