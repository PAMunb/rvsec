GitHub Issue: none (created without an issue, at the author's request on 2026-10-19)

## Why

On 2026-10-19 the mini-experiment session measured GATOR's reachability against the RVSEC-COV lines of the 1,467 `e03igg` tasks (`data/e03igg_analysis/out/rp_guidance/RESULTS.md`, sections K, M and N). Of the 495 direct targets (app methods that call the JCA) in 81 APKs, GATOR marks 279 as not `reachable`, and 63 of those 279 ran on the device, in 29 APKs. 10 of the 63 are primary misuse sites. 63 is a lower bound, because an unreachable target that no task ran cannot be checked this way. The investigation of the same day (`data/e03igg_analysis/out/rp_guidance/gator_cg_investigation/`, androguard caller trees and the full `.apk.json` of the replication package) traced the 63 to three defects in `rvsec-gator`:

- **A — the callback complement does not propagate.** `RvsecAnalysisClient.complementWithCallbacks` adds widget handlers, lifecycle handlers and service/receiver/provider callbacks to the reachable set after the forward search has finished, and never searches from them. In `org.cry.otp_31`, `Home$1.onClick` is `reachable` and `reachesTarget`, while `HOTP.gen`, `HOTP.generateOTP` and `HOTP.hmac_sha1` (a misuse site) on the same call-graph path are not `reachable`.
- **B — two framework-created component kinds are not entry points.** `getEntryPoints` takes activities and manifest services, receivers and providers. It has no `Application` subclass and no `Fragment`. In `app.maskan.chat_90`, `MaskanApplication.onCreate` has its call-graph edge to `initDatabaseEncryption` (distance 1), and both methods come out not `reachable`.
- **C — the call graph loses edges.** SPARK resolves a virtual call through the points-to set of its receiver. An object that the Android framework, reflection or a dependency-injection container creates has no allocation site SPARK follows, so a call on `this` of an activity, or on a field of an injected object, gets no edge. In `org.fedorahosted.freeotp_48`, `Activity.onNewIntent` and `Activity.onClick` do `invoke-virtual this.addToken(…)`. Neither edge is in the graph: `onNewIntent` is `reachable` with `reachesTarget: false`, and `addToken` is not `reachable`. Meanwhile `addToken → Token.parse`, an `invoke-static`, is in the graph at distance 1. In `com.kin.easynotes_14`, `NoteUseCase.encryptNote` calls `this.encryptionHelper.encrypt(…)` through a Hilt-injected field, and the edge is missing (`encryptNote` has `reachesTarget: false`). `LambdaEdges` (INV-ANA-77) already repairs the same mechanism for the receiver captured by a lambda wrapper.

A and B together explain 22 of the 63, including 4 of the 10 misuse sites. In those cases the call graph already holds a path from a handler or lifecycle method, and only the `reachable` flag is wrong. C explains the other 41, including 6 misuse sites. For those the bytecode roots are DI factories (22), library-invoked function objects (`Runnable`, Rx, `Function`, `Comparator`, 18), coroutines (13), Compose lambdas (7), ViewModels (4) and adapters (3), counted by a name and hierarchy heuristic; a target can have several. `reachable` is not read by the APE-RV jar or by the `aperv-tool` derive. It is the coverage denominator (FR12). C changes the distances and `reachesTarget`, which the derive does read.

Separately, the analyser is also used as a product of its own, outside the campaigns. In that use the question a reader asks of a distance is "through which calls?". GATOR computes that path in each distance search and discards it. Keeping it costs one predecessor per method visited, and the compact document (the default since gh125) is small enough to carry it: the compact `targetDistances` of `com.kin.easynotes_14` hold 9,094 pairs in about 0.1 MB.

## What Changes

The author's decisions of 2026-10-19:

- **Distance paths, on request.** A new client parameter `distancePaths=true` makes GATOR write the call path behind every `targetDistances` pair it writes. The paths go in two new top-level members, a table of the methods that occur on a path (app and library) and a list of `[i, v, n]` steps meaning "on the way to target `i`, method `v` calls method `n`". A reader follows the steps from a method to the target. Without the parameter the document is exactly the one GATOR writes today, in both output modes. The distance searches visit callers in signature order, so the path chosen among equally short ones is the same on every run. In compact mode the steps kept are those on the paths of the pairs kept. `rv-static-analysis` exposes the parameter (`distance_paths`, `--distance-paths`), its offline `compact` converter refuses a document that carries paths (GATOR writes the compact document with paths directly), and the streaming reader drops both members as it drops `targetDistances`.
- **A: the reachability search starts from the callbacks.** The callbacks that `complementWithCallbacks` collects become seeds of the forward search, so the methods they call are `reachable` too.
- **B: framework-created components are entry points.** These contribute entry points to the reachability search:
  - the `Application` subclass named in the manifest;
  - every app subclass of `android.app.Fragment`, `android.support.v4.app.Fragment` or `androidx.fragment.app.Fragment`;
  - the `doWork`/`startWork` of every app subclass of `androidx.work.ListenableWorker`;
  - the public methods of every app subclass of `androidx.recyclerview.widget.RecyclerView$Adapter`, `androidx.recyclerview.widget.RecyclerView$ViewHolder` or their `android.support.v7.widget` counterparts.

  `ViewModel` is not an entry point. A ViewModel runs only when a screen asks for it, and with C the screen's call reaches it.
- **A query subcommand.** `rv-static-analysis path <doc> <method> [--target i]` streams a document with paths and prints, for one method, the readable chain to each of its targets, or to the one requested. It refuses a document without `distancePaths`.
- **C: an edge at every call site SPARK left without one.** Before the reachability search, at each instance-invoke site of an app method where the call graph holds no edge, the client adds an edge to each concrete app method the call can dispatch to by the statically named method and the app subtypes of its receiver type. Sites SPARK resolved are not touched, and library callees are not added. The edges serve the reachability search, the distances and the paths only: the client removes them before the fragment windows and the WTG, so `windows` and `transitions` are what they are today.

**BREAKING (for coverage and the derive input):** A and B enlarge the `reachable` set, the coverage denominator. C enlarges `reachable`, `reachesTarget` and `targetDistances`. It leaves `directlyReachesTarget` and `distanceTargets` as they are, because it adds no edge to a library method and every target is a library method. A document produced after this change is not comparable with an earlier one on any of those fields, and a MOP artifact derived from it differs. No campaign may mix documents across the change.

**Not in this change:** library-invoked callbacks in the derive's `handlers` table and the instrumentation stamp that would name them. Those belong to the `dexlib2` and `aperv` sessions and wait for the stamp A/B of 2026-10-19 (`experimento-stampcb`). This change also leaves out the GATOR listener on `#OptionsMenu` menu-item widgets (it waits for that A/B), models of library dispatch (coroutines, koin/Hilt registries, executors, `Collections.sort`), the path's continuation inside library code for `boundary` targets (a path ends at the app target, as the distance does), `ViewModel` as an entry point, re-analysing or converting the corpus, the Docker image, the APE-RV jar and the replication package.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `analysis`: entry points of the reachability search (B), the place of the callback complement in it (A), a new requirement for empty-site edges in the call graph (C), a new requirement for distance paths with their output contract, its interaction with compact output and the offline converter, and the streaming reader dropping the path members.

## Impact

- **`rvsec-gator`** (Java, `rvsec/rvsec-android/rvsec-gator`): `RvsecAnalysisClient` (`getEntryPoints`, `complementWithCallbacks`, the client parameter, the reachability writer), `reach/ReachabilityEngine`, a new `reach/EmptySiteEdges`, `reach/TargetDistances` (sorted callers, predecessors, path steps), `json/JsonSchema.Keys`, and `XMLParser`/`DefaultXMLParser` (the manifest's `<application android:name>`). FR04, FR06, FR12.
- **`rv-static-analysis`**: `config.py` (`distance_paths`), the CLI, `_JK`, `compact.py` (refuses an input with paths), and a new `path_query.py` behind the `path` subcommand. NFR05, NFR08.
- **`rv-android-core`**: `util/analysis_document.py` drops the path members under both pair policies. `StaticAnalysisData` is unchanged, and so is the derive's input apart from the fields C moves.
- **`aperv-tool`**: no code change. Artifacts derived from post-change documents differ through C.
- **`rv-coverage` and every coverage report**: the denominator grows through A and B.
- **Cost (NFR04)**: C adds one call-graph scan of the app's invoke sites. Paths add one sorted callers list per callee and one predecessor per visited method per search, and nothing when `distancePaths` is off.
- **Running campaigns**: none affected. The change lives in the `wip/gator-paths` worktree, and `rv-android/lib/gator/` is replaced only when the jar is installed.
