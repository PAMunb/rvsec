<!-- Subagent dispatch plan. The main session orchestrates and dispatches; each subagent edits only the files of its group.
     - Group 0 (main) runs first: it freezes the baseline jars and the baseline documents that group 6 compares against.
     - Groups 1, 2, 3 and 4 are independent and run in parallel, one subagent each, after Group 0:
         Group 1 (A+B) owns ReachabilityEngine, getEntryPoints/collectCallbacks/complementWithCallbacks in RvsecAnalysisClient,
                       XMLParser/DefaultXMLParser, FragmentViewFlow.FRAGMENT_BASES, FragmentHostResolver, and their tests;
         Group 2 (C)   owns the new reach/EmptySiteEdges.java and its test (it does NOT edit RvsecAnalysisClient);
         Group 3 (paths, Java) owns reach/TargetDistances.java, a new reach/DistancePaths.java, json/JsonSchema.java,
                       json/JsonReportWriter.java and their tests (it does NOT edit RvsecAnalysisClient);
         Group 4 (Python) owns rv-android-core util/analysis_document.py, rv-static-analysis (config.py, __main__.py,
                       compact.py, _JK) and their tests.
       Groups 1 and 3 do not touch the same lines of RvsecAnalysisClient: Group 1 edits only getEntryPoints,
       complementWithCallbacks (deleted) and collectCallbacks (new); the wiring that Groups 2 and 3 need there is Group 5.
     - Group 5 (main) wires EmptySiteEdges and the path pass into RvsecAnalysisClient.run(), builds the reactor with tests on,
       and runs pytest and parity. Needs 1-4.
     - Group 6 (main) runs the end-to-end measurements. The GATOR runs inside it go in parallel, the sum of -Xmx of
       concurrent JVMs ≤ 80 GB.
     - Group 7 (docs, one subagent, .md files only) runs in parallel with Group 6.
     - Group 8 (lint, verify, review, commit) runs after Groups 6 and 7: tests before review.
     - Critical path: 0 -> {1,2,3} -> 5 -> 6 -> 8.
     - Every subagent prompt MUST forbid git commands that change state (stash, checkout, switch, restore, reset, branch,
       rebase, clean, commit); only diff/status/log/show/grep are allowed. Work happens in the worktree
       /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/paths (branch wip/gator-paths).
     - Java subagents do not run Maven: a module built outside the reactor breaks main.basedir; the build is task 5.3.
     - Outputs of groups 0 and 6 go to rv-android/experimento-gtpaths/, never to /tmp. The replication package
       (rvsec-study03-replication-package/data/raw/) is read-only input. -->

## 0. Baseline (main session)

- [x] 0.1 Copy `rv-android/lib/gator/rvsec-analysis-client.jar` and `rvsec-gator.jar` of the worktree to `rv-android/experimento-gtpaths/baseline/` before any build, and record their sha256 in `baseline/SHA256`.
- [x] 0.2 (APK set changed by the author on 2026-10-19: `app.maskan.chat_90` and `com.kin.easynotes_14`, about 30 min each in Soot/SPARK, replaced by `com.vrem.wifianalyzer_71` and `systems.sieber.droid_scep_7`; see design, Testing Strategy.) With the baseline jars, run `rv-static-analysis analyze` with `--full-output` on `apks_examples/cryptoapp.apk` and on the five corpus APKs of the design's end-to-end row (`org.fedorahosted.freeotp_48`, `org.cry.otp_31`, `app.maskan.chat_90`, `com.kin.easynotes_14`, `net.gaast.giggity_769`, from `rvsec-study03-replication-package/data/raw/e6-corpus/`). Write the outputs under `baseline/`, in parallel within the heap budget, and record each run's wall time and the GATOR log.
- [x] 0.3 From `data/e03igg_analysis/out/rp_guidance/r_direct_full.csv`, write `experimento-gtpaths/targets63.csv`: the 63 rows with `reachable = False` and `executed = True`. Mark the ones in the five APKs of 0.2; these are the cases group 6 checks.

## 1. A + B: callbacks as seeds, framework-created component entry points (subagent A — rvsec-gator, Java)

- [x] 1.1 `RvsecAnalysisClient`: extract `collectCallbacks(GUIAnalysisOutput)` from `complementWithCallbacks`. It returns the activity lifecycle handlers, the GUI event handlers (`collectEventHandlers`) and the Service/Receiver/Provider lifecycle methods, with no side effect. Delete `complementWithCallbacks` (P3, design D7).
- [x] 1.2 `reach/ReachabilityEngine.run()`: seed `multiSourceBfs` with `getEntryPoints(output) ∪ collectCallbacks(output)`, and remove the call to the deleted complement. Update the class Javadoc's five steps to describe the pipeline as it now is (P4: current state only).
- [x] 1.3 `sootandroid/.../xml/XMLParser` + `DefaultXMLParser`: add `getApplicationClassName()`, read from `<application android:name>` with `Helper.getClassName(…, appPkg)`, `null` when the attribute is absent (design D9).
- [x] 1.4 `sootandroid/.../gui/FragmentViewFlow`: make `FRAGMENT_BASES` public. `client/.../fragment/FragmentHostResolver`: delete its private copy and read `FragmentViewFlow.FRAGMENT_BASES`.
- [x] 1.5 `RvsecAnalysisClient.getEntryPoints`: add the Application class's lifecycle methods (`onCreate`, `onTerminate`, `onConfigurationChanged`, `onLowMemory`, `onTrimMemory`, `attachBaseContext`) and its public/protected methods, logging a warning when it is absent from the Scene. Add the public/protected methods of every app class with a superclass in `FragmentViewFlow.FRAGMENT_BASES` (design D8). Add `doWork`/`startWork` of every app subclass of `androidx.work.ListenableWorker`. Add the public methods of every app subclass of `RecyclerView$Adapter`/`RecyclerView$ViewHolder`, both `androidx.recyclerview.widget` and `android.support.v7.widget`. Declare those base names as constants beside the fragment set. The method needs the app-class map; pass it in and update its callers.
- [x] 1.6 Tests: in `ReachabilityBfsTest`, a synthetic graph where a method two calls below a callback seed is reachable. New `ReachabilityEngineCallbackSeedTest`: on a synthetic graph, the `reachesTarget`/`directlyReachesTarget` sets with seeding equal what the deleted complement produced (design D7). Also add a manifest test for `getApplicationClassName()` with a relative name (`.App`), an absolute name, and no attribute, and an entry-point test in the Scene idiom of `CallSiteMatchPolicyTest`: Application, Fragment, ListenableWorker (only `doWork`/`startWork` taken), Adapter and ViewHolder subclasses; a ViewModel subclass not taken.
- [x] 1.7 Report the files changed and the callers updated (grep `complementWithCallbacks`, `getEntryPoints(`, `FRAGMENT_BASES`: zero dangling references).

## 2. C: empty-site edges (subagent B — rvsec-gator, Java)

- [x] 2.1 New `client/.../clients/reach/EmptySiteEdges.java` with `public static int addTo(CallGraph cg, Map<SootClass, List<SootMethod>> appClasses)`, per the requirement "Empty-Site Edges in the Reachability Call Graph" and design D10:
  - for every concrete app method whose body is retrievable, each `Stmt` with an `InstanceInvokeExpr` and no `cg.edgesOutOf(stmt)` gets edges;
  - a special invoke goes to its resolved method, if it is a concrete app method;
  - a virtual or interface invoke goes to `FastHierarchy.resolveConcreteDispatch` over the declared receiver type (if it is a concrete app class) and each concrete app subtype, keeping app callees only;
  - add each edge with the kind that matches the invoke;
  - log one line with sites, empty sites, edges added, bodies skipped and the largest fan-out.

  The class Javadoc explains why SPARK leaves these sites empty (framework/reflection/DI receivers), in the style of `LambdaEdges`.
- [x] 2.2 New `EmptySiteEdgesTest` in the Scene idiom of `LambdaEdgesTest`, one test per scenario of the requirement: a call on `this`, a call through a field, a special invoke, interface fan-out to app implementers only (no library callee), a resolved site left untouched, a static invoke left untouched, an abstract-only hierarchy giving no edge, and a body that cannot be retrieved being skipped and counted.
- [x] 2.3 Report the files changed. The call from `RvsecAnalysisClient.run()` is task 5.1.

## 3. Distance paths, Java (subagent C — rvsec-gator, Java)

- [x] 3.1 `reach/TargetDistances.compute`: build the callee → callers map as lists sorted by the signature function, once (design D4). Keep `reverseBfs` FIFO. Existing `TargetDistancesTest` expectations must hold unchanged.
- [x] 3.2 New `reach/DistancePaths.java`: an immutable holder with `methods()` (sorted signatures) and `steps()` (`int[3]` sorted by `(i, v)`).
- [x] 3.3 `TargetDistances.paths(BiPredicate<V, int[]> written)` (design D3): for each target index named by a written pair, repeat the reverse search recording the first-discovering callee of each visited vertex. From each written pair's method, follow the predecessors to the target and collect the steps `(i, v, n)` with their vertex objects. After the last target, sort the vertices by signature, renumber, and return a `DistancePaths`. Hold one target's predecessor map at a time.
- [x] 3.4 `json/JsonSchema.Keys`: add `PATH_METHODS = "pathMethods"` and `DISTANCE_PATHS = "distancePaths"`, with the comment style of the neighbouring keys. Update `JsonSchemaKeysTest`.
- [x] 3.5 `json/JsonReportWriter`: take a nullable `DistancePaths`. When it is non-null, write `pathMethods` and then `distancePaths` right after `reachability`, in both writes. When it is null, write nothing, so the document is unchanged (INV-ANA-90).
- [x] 3.6 New `TargetDistancesPathsTest` (string vertices):
  - the spec's two-call handler example;
  - a chain through a library vertex;
  - a tie at equal length resolved by signature, stable over 10 runs with shuffled insertion order;
  - compact predicate: no step only on a reduced pair's chain, kept chains complete;
  - `d = 0` gives no step;
  - every step lies on a written chain (INV-ANA-91, -92, -93).
- [x] 3.7 New `DistancePathsEmissionTest` beside `DistanceKeysEmissionTest`: members absent with null paths; present, in order, right after `reachability` with paths; values as given.
- [x] 3.8 Report the files changed. The client parameter and the call of `paths(...)` are task 5.2.

## 4. Readers, option and converter (subagent D — Python: rv-android-core, rv-static-analysis)

- [x] 4.1 `modules/rv-android-core/src/rv_android_core/util/analysis_document.py`: add `PATH_METHODS_KEY`/`DISTANCE_PATHS_KEY`. In `read_analysis_document`, skip both top-level members with `_skip_value` under every `PairPolicy`. Update the module docstring's account of what is dropped (INV-ANA-97).
- [x] 4.2 `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`: add `PATH_METHODS` and `DISTANCE_PATHS` to `_JK` with the Java values (INV-ANA-32).
- [x] 4.3 `config.py`: add `distance_paths: bool = Field(default=False, …)`; `get_tool_command` appends `-clientParam distancePaths=true` only when it is `True`. `__main__.py`: add `--distance-paths` to `analyze` and `batch`, beside `--full-output`.
- [x] 4.4 `compact.py`: refuse an input carrying `distancePaths` with `CompactRefused`, a message naming the input and saying that GATOR writes a compact document with paths when `distancePaths=true`, and no output file left behind (design D6). The reader drops the member, so detect it in the same pass the converter already uses to detect `distancePairs`.
- [x] 4.5 Tests:
  - `analysis_document`: both policies drop the two members; a truncated document ending inside `distancePaths` keeps the members before it;
  - parser: `StaticAnalysisData` equal with and without the members (the cryptoapp fixture with members inserted); the parsed copy lacks them;
  - config/CLI: the parameter appears only with `--distance-paths`, on both subcommands;
  - converter: exit 1, message, no output file.
- [x] 4.6 New `modules/rv-static-analysis/src/rv_static_analysis/path_query.py` (requirement "Path Query Subcommand", design D12). Its own ijson event pass keeps `distanceTargets`, `pathMethods`, `distancePaths` and the `targetDistances` of the requested method, and skips everything else. Index the steps by `(i, v)`. For each pair `[i, d]` (or only `--target`), follow `d` steps and print the header and the indented chain. Refuse with exit 1 and one stderr line when there is no `distancePaths`, the method is unknown, the target is not among the method's pairs, or a chain breaks. Wire `path DOC METHOD [--target I]` in `__main__.py`.
- [x] 4.7 New `tests/test_path_query.py`: a small fixture with paths, covering every pair, `--target`, a method with no pair (exit 0, no output), each refusal, and a fixture with a missing step (broken chain → exit 1).
- [x] 4.8 Run `/rv-doc-code modules/rv-static-analysis/src/rv_static_analysis/path_query.py`.
- [x] 4.9 Run `/rv-test-run rv-android-core` and `/rv-test-run rv-static-analysis` (pytest with `--import-mode=importlib -o "addopts="`).

## 5. Wiring and integration build (main session — after 1, 2, 3, 4)

- [x] 5.1 `RvsecAnalysisClient.run()`: call `EmptySiteEdges.addTo(Scene.v().getCallGraph(), appClasses)` right after `LambdaEdges.addTo`, in its own try/catch that logs and continues. Update the step comment.
- [x] 5.2 `RvsecAnalysisClient`: add `distancePaths()`, modelled on `fullOutput()`. When it is true, compute `distances.paths(written)` with the mode's predicate (every pair in full mode; membership in `TargetDistances.compact(pairs(m))` in compact mode) before the pre-WTG write, in its own try/catch (a failure costs only the paths). Pass the result to `JsonReportWriter`, and log one INFO line with the number of methods and steps.
- [x] 5.3 Build from the rvsec reactor root with JDK 21 in the prefix and tests on: `mvn -o install -DskipMopAgent -pl rvsec/rvsec-android/rvsec-gator/client -am` (no `-DskipTests`; a log line `Tests are skipped.` fails this task). Then run `mvn -o verify -DskipITs=false -pl rvsec/rvsec-android/rvsec-gator/client`. Record test counts and the sha256 of the jars the build wrote to `rv-android/lib/gator/` of the worktree.
- [x] 5.5 `EmptySiteEdges.addTo` returns the `List<Edge>` it added (update `EmptySiteEdgesTest`). In `RvsecAnalysisClient.run()`, keep that list and remove each edge from `Scene.v().getCallGraph()` after `computeDistances`, before the path pass (which reads the callers map `TargetDistances` kept), `analyzeFragments` and the WTG, logging the count. Rebuild with tests on, as in 5.3, and record the new jar hashes.
- [x] 5.6 Fixes from the code review of 8.3 (author's decision, 2026-10-19):
  - `TargetDistances.releaseCallers()` drops the callers map, called in `run()` after the path pass, so the map is not held through the WTG with paths off; `paths` throws `IllegalStateException` afterwards (test in `TargetDistancesPathsTest`);
  - `EmptySiteEdges.addTo(cg, appClasses, added)` appends each edge to a caller-owned list as it enters the graph, so edges added before a mid-pass failure are still removed before the WTG;
  - `DefaultXMLParser.readApplicationClassName` treats an empty `android:name` as absent (test in `ApplicationClassNameTest`);
  - `modules/rv-static-analysis/pyproject.toml` declares `ijson>=3.3.0`, which `path_query.py` imports; `uv lock --offline` re-locks it.
  - the cryptoapp reference fixture, which the parity gates (`tests/parity/test_baseline_freshness.py`, `test_reachability_parity.py`) compare against the deployed jar: `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` regenerated in full mode with the review jar (client `434e8614…`) by the gate script's command (`./gator … -clientParam mopDir=<jca> -clientParam fullOutput=true`) and byte-copied to `modules/aperv-tool/tests/fixtures/cryptoapp.apk.json`; `baselines/MANIFEST.json` (date, jar sha, `reachable` 61, `reaches_target` 39) and the aperv-tool fixture README updated; the pinned counts in the parser and reader tests moved (`reachable` 55 → 61, methods carrying `targetDistances` 38 → 39). Against the old fixture only the intended growth differs: 6 methods become reachable (callback seeding, INV-ANA-94) and `MessageDigestUtil.unreachableHash` reaches a target; `directlyReachesTarget`, `distanceTargets`, `windows` and `transitions` are unchanged. Afterwards rv-static-analysis 266, rv-android-core 1148, aperv-tool 712 passed / 74 skipped, `tests/parity` 184 passed / 26 skipped.

  Rebuild with tests on as in 5.3, run the ITs, and record the new jar hashes. The output does not change, so no GATOR run is repeated.
- [x] 5.4 Run `tests/parity/test_json_keys.py` and `tests/parity/test_distance_pair_constants.py`, and `/rv-test-run aperv-tool` (derive tests unchanged in result).

## 6. End-to-end measurements (main session — after 5)

- [x] 6.1 With the new jar, analyse the six APKs of 0.2 in three configurations: full; compact (default); compact with `--distance-paths`. Add full with `--distance-paths` on `cryptoapp.apk` and `org.cry.otp_31` only. Run them in parallel within the heap budget, and record wall time and document size for each.
- [x] 6.2 Defect checks against `targets63.csv` and the baseline:
  - for each of the 63 cases in the five APKs, report `reachable` and `reachesTarget` before and after, and which of A, B or C changed it;
  - the scenarios of the delta (cry.otp `HOTP.hmac_sha1`, maskan `initDatabaseEncryption`, freeotp `onNewIntent`/`addToken`, easynotes `encryptNote`) hold, or the report says which do not and why.
- [x] 6.3 Effect sizes per APK, baseline against new full mode:
  - `reachable` and `reachesTarget` counts;
  - pairs written;
  - `distanceTargets` (must be equal, INV-ANA-96);
  - `directlyReachesTarget` (must be equal);
  - EmptySiteEdges' log line: sites, empty sites, edges, largest fan-out, plus the 10 sites with the most callees and their declared types. This is the input of the author's decision on a fan-out bound (design, Open Questions); no bound is implemented here.

  Then repeat the comparison with C disabled in a test build (or by computing from the logs), to show that A and B change only `reachable` (design D7).
- [x] 6.4 Path checks:
  - INV-ANA-90: compact with paths and compact without paths differ only by the two members;
  - INV-ANA-91 and INV-ANA-93, with a script that rebuilds every written pair's chain from the steps;
  - INV-ANA-92: run `org.cry.otp_31` twice with paths and compare the bytes;
  - for every app→app step, check against the bytecode (androguard, scripts from `data/e03igg_analysis/out/rp_guidance/gator_cg_investigation/`) that `v`'s body invokes `n`, or that the step is a lambda edge or an empty-site edge.
- [x] 6.4b Run `rv-static-analysis path` on the `org.cry.otp_31` document with paths for `Home$1.onClick` (the spec scenario), and for three other methods with pairs at `d ≥ 3`. The printed chains must match the steps checked in 6.4.
- [x] 6.5 The converter refuses the full document with paths of 6.1, with exit 1 and no output. Converting the full document without paths gives GATOR's compact document byte for byte (INV-ANA-87), or equal with node ids compared by content.
- [x] 6.7 With the 5.5 jar, rerun the full configuration on the six APKs. `windows` must equal the baseline's, and `transitions` must equal it as a set (order follows identity hashing). `reachable`, `reachesTarget`, pairs and paths must equal the 6.1 full documents. The client time must be back near the baseline's. Add the numbers to `RELATORIO.md`.
- [x] 6.6 Write `experimento-gtpaths/RELATORIO.md` with every number of 6.1–6.5 and the answers group 6 gives to the design's Open Questions (largest fan-out; path cost). Jars, documents and logs stay out of git (`experimento-gtpaths/.gitignore`).

## 7. Documentation (subagent E — `.md` files only; parallel with 6)

- [x] 7.1 `rvsec/rvsec-android/rvsec-gator/CLAUDE.md`:
  - Key components: `EmptySiteEdges`, `DistancePaths`;
  - JSON contract: the `distancePaths` parameter and the two members;
  - Distances: callers in signature order, the second pass;
  - Gotchas: the empty-site edges and what they do not repair (library dispatch);
  - Build & invocation: add `distancePaths` to the params.
- [x] 7.2 `modules/rv-static-analysis/CLAUDE.md` and `modules/rv-static-analysis/docs/architecture.md`: `distance_paths`, `--distance-paths`, the converter's refusal, the `path` subcommand and `path_query.py`. `modules/rv-android-core/CLAUDE.md`: the reader drops the path members.
- [x] 7.3 Record for the archive step what the sync must change by hand in `openspec/specs/analysis/spec.md`, outside the requirements:
  - the Purpose paragraph that lists the entry points ("Entry points include all four Android component types");
  - the Data Contracts output lines (add `pathMethods` and `distancePaths`).

## 8. Verification and closing (main session)

- [x] 8.1 Run `/rv-qa-lint-fix rv-static-analysis` and `/rv-qa-lint-fix rv-android-core`.
- [x] 8.2 Run `/rv-verify rv-static-analysis` and `/rv-verify rv-android-core`.
- [x] 8.3 Invoke `/rv-code-reviewer` via the Skill tool on the change's diff (Java and Python).
- [x] 8.4 Run `openspec validate gh-tbd-gator-distance-paths --strict`.
- [x] 8.5 Commit by path (`git commit -- <paths>`) on `wip/gator-paths`, with no issue reference and no co-author trailer, when the author asks for it.
