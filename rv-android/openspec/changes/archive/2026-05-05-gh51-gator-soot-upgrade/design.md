## Context

GitHub Issue: #51 | Proposal: `proposal.md` | Pre-plan: `docs/20260419_gator.md`

GATOR static analysis succeeds on 27.6% of APKs (97/352). The crash occurs in Soot 3.3.0's `ClassHierarchy.typeNode()` when processing Kotlin bytecode. The dominant crash path is during CHA call graph construction (Scenario A), before the GATOR Flowgraph executes. A secondary path (Scenario B) occurs in `Flowgraph.processApplicationClasses()`.

The fix applies three complementary layers: defensive Soot configuration (FIX 1), graceful error handling (FIX 2), and Soot version upgrade (FIX 3). All changes are in the Java GATOR codebase (`rvsec/rvsec-android/rvsec-gator/`). No Python code changes.

**Constraint**: The `ClassHierarchy.typeNode()` bug (soot-oss/soot#1071) exists in ALL Soot versions (3.3.0 through 4.7.1). The 4.x Dexpler improvements reduce crash frequency but do not eliminate it. FIX 2 is the safety net for residual crashes.

## Architecture

```mermaid
flowchart TB
    subgraph "RVSEC Java (changes)"
        MAIN["Main.java<br/>FIX 1: Soot config"]
        FG["Flowgraph.java<br/>FIX 2: try-catch"]
        POM["pom.xml hierarchy<br/>FIX 3: Soot 4.7.1 (Feb 2026)"]
    end

    subgraph "RVSEC Java (unchanged)"
        RC["RvsecAnalysisClient.java"]
        GA["GUIAnalysis.java"]
    end

    subgraph "rv-android Python (unchanged)"
        SA["StaticAnalyzer"]
        SAP["StaticAnalysisParser"]
    end

    SA -->|"executes"| MAIN
    MAIN -->|"initializes Soot"| SOOT["Soot 4.7.1"]
    SOOT -->|"CHA phase"| CG["Call Graph"]
    CG -->|"wjtp.gui phase"| GA
    GA --> FG
    FG -->|"partial Flowgraph"| GA
    GA --> RC
    RC -->|"writes JSON"| JSON["analysis.json"]
    JSON -->|"parsed by"| SAP
```

### Key Components

| Component | Responsibility | Change |
|-----------|---------------|--------|
| `Main.java` (sootandroid) | Soot initialization and argument setup | FIX 1: defensive sootArgs + Options.v(). FIX 3: `-process-multiple-dex` → `-search-dex-in-archives` |
| `Flowgraph.java` (sootandroid) | GUI flowgraph construction from Jimple bodies | FIX 2: try-catch line 274, continue line 343, null-check `rcv_var` |
| `FlowgraphRebuilder.java` (sootandroid, `gui/wtg/flowgraph/`) | WTG flowgraph rebuild with virtual dispatch | FIX 2: null-check `rcv_var` at lines 133 and 967 |
| `IntentAnalysis.java` (sootandroid, `gui/wtg/intent/`) | Intent target resolution fixpoint | FIX 2: `HashSet<Pair> visited` to prevent infinite loop |
| `RvsecAnalysisClient.java` (client) | JSON output writer | FIX 2: write-first strategy (reachability before WTG), tolerate `wtg == null` |
| `rvsec/pom.xml` (artifactId=`rvsec-parent`) | Parent POM with `soot.version` property (line 38) | FIX 3: `4.4.1` → `4.7.1` |
| `rvsec-gator/pom.xml` + children | GATOR Soot dependency declaration | FIX 3: `ca.mcgill.sable:soot:3.3.0` → `${soot.version}` from parent |
| `rvsec-gator/client/pom.xml` | Fat JAR — Soot exclusions in `<dependencies>` (lines 43-51) | FIX 3: Remove both Soot exclusions (no more groupId conflict) |
| `Configs.java` (sootandroid) | Soot Options API calls | FIX 3: No changes needed — API preserved in 4.7.1 |
| `EpiccBasedIntentAnalysis.java` (sootandroid, `gui/clients/ata/`) | Intent analysis using `soot.dexpler.Util` | FIX 3: No changes needed — API preserved in 4.7.1 |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|--------------------------|---------------|------|
| INV-ANA-16 (defensive Soot options) | `Main.java:204-232` — sootArgs + Options.v() + `-search-dex-in-archives` (renamed from `-process-multiple-dex`) | Smoke test: 10 APKs that crash → verify JSON produced |
| INV-ANA-17 (Flowgraph graceful degradation) | `Flowgraph.java` (try-catch + null receiver), `FlowgraphRebuilder.java` (null receiver x2), `IntentAnalysis.java` (visited set) | Smoke test: APKs that crash in Flowgraph → verify partial JSON |
| INV-ANA-17b (Write-first JSON) | `RvsecAnalysisClient.java` — write reachability before WTG, rewrite if WTG completes | Smoke test: timeout APKs still produce JSON with reachability |
| INV-ANA-18 (Soot 4.7.1 unified) | 5 pom.xml files | `mvn clean compile` succeeds — zero API breaks |
| Scenario: CHA crash | No code change — crash is prevented by FIX 1 + FIX 3 | Smoke test: APKs that previously crashed |
| Scenario: Flowgraph skips method | `Flowgraph.java` try-catch + null-check | Smoke test: verify JSON has reachability data |
| Scenario: WTG timeout | `RvsecAnalysisClient.java` write-first | APK `dev.robin.flip_2_dnd_903`: timeout but JSON with reachability produced |
| Scenario: Kotlin exclusion impact | `Main.java` excludes | Compare reachability counts before/after for Java-pure APK |
| Scenario: Output equivalence | All fixes combined | `cryptoapp.apk` baseline: directlyReachesMop=21 (exact match), windows=5, transitions=35 |

## Goals / Non-Goals

**Goals:**
- Increase SA success rate from 27.6% to ≥50% (target: 50-70%)
- Unify Soot version across RVSEC (eliminate `ca.mcgill.sable` dependency)
- Produce partial analysis data when individual methods fail

**Non-Goals:**
- Fix the `ClassHierarchy.typeNode()` bug in Soot itself (upstream, unfixed since 2018)
- Modify the Python-side `StaticAnalyzer` or `StaticAnalysisParser`
- Implement Androguard fallback (separate future change if needed)
- Upgrade FlowDroid version (evaluate after Soot upgrade; only if `rvsec-apk` breaks)
- Modify `RvsecAnalysisClient.java` (unchanged — it already writes JSON incrementally)

## Decisions

### D1: Soot 4.7.1 (not 4.6.0, not SootUp)

**Choice**: `org.soot-oss:soot:4.7.1` (Feb 2026, latest stable)

**Alternatives considered**:
- **4.6.0** (validated empirically via CryptoAnalysis): Works, but 4.7.1 includes additional Dexpler fixes and a build fix over 4.7.0
- **SootUp 2.0**: Incompatible API, incomplete Android APK support, would require full GATOR rewrite. Not viable in thesis timeline
- **Patch ClassHierarchy.typeNode()**: Would require forking Soot, maintaining a custom build. Disproportionate effort for a workaround

**Rationale**: 4.7.1 is the closest to the empirically validated 4.6.0, with incremental improvements. The API core (`Scene.v()`, `SootClass`, `SootMethod`, etc.) is preserved from 3.x to 4.x.

### D2: Exclude `kotlin.*`/`kotlinx.*`/`androidx.compose.*` but NOT `android.*`/`androidx.*` (general)

**Choice**: Exclude Kotlin stdlib and Compose runtime from body loading; keep general Android framework bodies.

**Rationale**: GATOR needs general Android framework bodies to analyze widgets and listeners (`findViewById`, `setOnClickListener`, etc.). CryptoAnalysis/FlowDroid exclude `android.*` because they do taint analysis, not GUI analysis. For JCA specifications, excluding Kotlin stdlib has minimal impact (JCA APIs are in `javax.crypto.*`/`java.security.*`, called by app code). For generic specs (Iterator, Map), some reachability through Kotlin stdlib may be lost — acceptable trade-off.

The `androidx.compose.*` exclusion is critical: ~71% of crashing APKs are Kotlin+Compose, and Compose generates code in `androidx.compose.runtime.internal.*`, `androidx.compose.ui.*`, etc. These packages are NOT covered by `-exclude kotlin.`/`kotlinx.`. Compose widgets are not discoverable via traditional `findViewById`/XML layout analysis (they use a declarative Composition model), so excluding their bodies has minimal impact on GATOR's WTG construction.

### D3: FIX 2 scope — Flowgraph only, not RvsecAnalysisClient

**Choice**: Add try-catch in `Flowgraph.processApplicationClasses()` only. Do not modify `RvsecAnalysisClient.run()`.

**Rationale**: The `RvsecAnalysisClient` already writes JSON incrementally with flush between sections. If the Flowgraph completes (even partially), `RvsecAnalysisClient.run()` will produce JSON. Adding try-catch inside `RvsecAnalysisClient` would mask failures in the WTG construction pipeline, which is a different problem. Keep changes minimal (P1).

### D4: Deprecated modules removed before upgrade

**Choice**: Remove `rvsec-methods-extractor` and `rvsec-taint` from `rvsec-android/pom.xml` and move their directories to `backup/`.

**Rationale**: These modules have zero references from Python code (confirmed in pre-plan §7.1). Removing them entirely (P3: No Backward Compatibility) reduces the compilation surface — any API breaks in these modules are irrelevant. Only `rvsec-gator`, `rvsec-apk`, and `rvsec-frame-computer` need to compile. Directories are backed up (not deleted) in case of future reference.

### D5: Call Graph algorithm as parameter

**Choice**: Parameterize the call graph algorithm via `-cgAlgorithm` flag. Default: **`spark`**.

**Options and Soot mapping**:
- `cha`: `-p cg.cha enabled:true` (fastest, least precise — type-hierarchy only)
- `rta`: `-p cg.spark enabled:true -p cg.spark rta:true` (faster than full SPARK, considers only instantiated types)
- `vta`: `-p cg.spark enabled:true -p cg.spark vta:true` (considers only assigned types)
- `spark`: `-p cg.spark enabled:true` (full points-to analysis — slowest, most precise) — **default**

Note: RTA, VTA, and SPARK all use the SPARK framework internally. Only CHA is a separate implementation. See [Soot options docs](https://soot-oss.github.io/soot/docs/4.3.0/options/soot_options.html) and [issue #1828](https://github.com/soot-oss/soot/issues/1828) for details on SPARK sub-modes.

**Why SPARK as default** (revised choice; the previous version of this section recommended `cha`):

1. **Precision of `reachesMop`** — CHA over-approximates virtual dispatches by enumerating every override in the type hierarchy, regardless of whether a target type is actually instantiated at runtime. On Android codebases with deep inheritance and pervasive interfaces (especially Kotlin's `Function0..Function22` and lambda materialization), this inflates the set of methods that "reach MOP". SPARK's points-to analysis filters dispatches down to types effectively instantiated in the call graph, producing a `reachesMop` set closer to runtime reality.

2. **Quality of coverage metrics** — `cov_reaches_mop` uses the reachable-to-MOP set as denominator. A CHA-inflated denominator depresses the metric and makes apps look less covered than they actually are, undermining cross-app comparison. SPARK gives a tighter, semantically meaningful denominator.

3. **Quality of MOP-aware navigation** — `aperv:sata_mop` prioritizes UI widgets whose handlers reach MOP-monitored APIs. With CHA, more widgets are flagged as MOP-relevant than truly are; the tool wastes exploration budget on UI paths that never invoke crypto. With SPARK, the prioritized widget set is smaller and more accurate, focusing exploration on paths that genuinely matter for runtime verification.

4. **Crash concerns mitigated by gh51 fixes** — the earlier draft of this section argued "SPARK would trigger the same jimplification crashes". That argument was formulated against Soot 3.3.0 without defensive options. Soot 4.7.1 (FIX 3) plus the FIX 1 defensive options (`-p jb.sils enabled:false`, `-no-bodies-for-excluded`, Kotlin/Compose excludes) and FIX 2 graceful Flowgraph error handling resolve the dominant crash family. SPARK now completes on the same APKs CHA does, with the same robustness.

5. **Performance trade-off acceptable** — SPARK is typically 2–5× slower than CHA on large Android apps. Static analysis is offline and runs under a 30-minute per-APK budget (`RV_SA_TIMEOUT=1800`); the wall-clock cost is amortizable. The improvement in `reachesMop` quality drives better-targeted runtime exploration, recovering wall-clock at the runtime tool layer (less budget wasted on irrelevant widgets).

**Implementation**: Replace the boolean `-withCHA` flag with `-cgAlgorithm <cha|rta|vta|spark>` in `Main.java`. Pass from Python side via the GATOR script with `spark` as default. Keep backward compatibility: if `-withCHA` is passed, treat as `-cgAlgorithm cha` (so legacy invocations still resolve to a valid algorithm). Existing experiments that explicitly pinned CHA via `-withCHA` continue to work; new invocations get SPARK unless overridden.

### D6: Bytecode-scan complement to `findDirectMopCallers` (BUG-INV-ANA-19)

**Choice**: Add a statement-level scan over each application method's `Body.getUnits()` to detect literal `InvokeExpr` matches against MOP signatures, independent of the call graph. Union the result into `directMopSet` after `findDirectMopCallers` runs.

**Why**:

1. **CG-only detection is unsound for library-targeting MOP signatures** — `findDirectMopCallers` (RvsecAnalysisClient.java:406-421) iterates only vertices in the JGraphT graph, which is built from Soot's `CallGraph`. SPARK's default configuration omits library targets (`java.security.*`, `javax.crypto.*` are quarantined as IGNORED_CLASSES); the corresponding `Edge` objects are not produced, so even when an app method literally invokes `SecureRandom.nextInt`, neither the target vertex nor an outgoing edge to it exists. CG-only logic cannot find that caller.

2. **Asymmetry vs `reachesMopSet` is the observable bug** — `reachesMopSet` reaches the same method through `complementWithCallbacks` transitive completion (line 506-507): any callback whose target is in `reachesMopSet` is added to `reachesMopSet`. There is no analogous transitive completion for `directMopSet` (line 502 only adds direct CG-edge callbacks). The observable JSON inconsistency (`reachable=False, reachesMop=True, directlyReachesMop=False` for the same method) is the symptom of this asymmetry.

3. **Bytecode evidence is ground truth for "directly calls"** — the predicate `directlyReachesMop` semantically asks "does this method's bytecode contain a literal invocation of a MOP-monitored API?". The bytecode itself is authoritative. SPARK's call graph is an *over-approximation* of dispatches but a *under-approximation* of literal invocations (because it filters out library targets). For this specific predicate, bytecode scan is closer to the intended semantics than CG analysis.

4. **Match policy mirrors `resolveMopInScene`** — both consult MOP signatures by `(className, methodName)` ignoring parameter overloads. A precomputed `Set<String>` keyed `"className#methodName"` gives O(1) lookup per `InvokeExpr`. Helpers `buildMopKeys` and `matchesMopSignature` are package-private to enable unit testing without a Soot Scene.

5. **Resilience** — body retrieval is wrapped in try-catch (`RuntimeException`, `OutOfMemoryError`) with a WARN log and `continue`, mirroring the FIX 2 pattern in `Flowgraph.java`. A single corrupted method does not abort the whole pass.

6. **Scope = app classes only** — the scan iterates `appClasses` from `extractClasses` (already filtered by `code_package`), not every class in `Scene.v().getClasses()`. The caller universe matches the existing `extractClasses` semantics; we never report a library method as a "direct MOP caller".

**Why not "fix SPARK"**: Adding `java.security.*` to SPARK's reachable set would require modeling the full JCA implementation (Provider lookup, native crypto bindings, etc.), which is out of scope and would explode CG size on every APK. Bytecode scan is targeted, cheap (O(methods × statements) on app code only), and orthogonal to CG decisions.

**Empirical validation**: `com.myAllVideoBrowser_197.apk` `GeneratedProxyCreds$Companion::generateRandomString` flips from `directlyReachesMop=False` to `True`, matching Androguard's reachability witness. `cryptoapp.apk` baseline preserved at 22 (CG=22, bytecode=21, intersection=21) — bytecode scan adds zero spurious detections on a JCA-heavy benchmark, confirming the union semantics are conservative.

## Data Flow

No change to data flow. The existing pipeline is preserved:

```
APK → StaticAnalyzer (Python) → GATOR process (Java) → analysis.json → StaticAnalysisParser → StaticAnalysisData
```

The change affects the GATOR process internally (Soot configuration, error handling, Soot version). Input and output formats are unchanged.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `InternalTypingException` during CHA | `CHATransformer` via `retrieveActiveBody()` | FIX 1 (excludes, disabled sub-phases) + FIX 3 (Soot 4.7.1 Dexpler) reduce frequency | No recovery — GATOR process dies. SA fails for this APK |
| `InternalTypingException` in Flowgraph | `Flowgraph.processApplicationClasses()` line 274 | FIX 2: try-catch → log + continue | Partial Flowgraph; JSON produced with incomplete WTG |
| Exception in `createOpNode()` | `Flowgraph.processApplicationClasses()` line 343 | FIX 2: catch → log + continue (replaces throw) | Missing OpNode for that statement; loop continues |
| `NullPointerException` on `rcv_var.getType()` | `Flowgraph.java` and `FlowgraphRebuilder.java` — `jimpleUtil.receiver(ie)` returns null for excluded-package virtual calls | Null-check before `.getType()` | Skip virtual call dispatch for that statement |
| `IntentAnalysis` infinite loop | `IntentAnalysis.resolveStartActivityIntentContent()` — fixpoint loop re-adds pairs when `intentContent.get(allocNode)` is null | `HashSet<Pair> visited` prevents re-processing | Loop terminates; intent targets for affected nodes are incomplete |
| WTG timeout (external kill) | `WTGBuilder.build()` takes >timeout for complex APKs (18K+ vertices) | Write-first strategy: JSON with reachability written BEFORE WTG starts; rewritten with full data if WTG completes | Reachability always preserved; windows/transitions empty on timeout |
| API break during compilation | Soot 3.3.0 → 4.7.1 API changes | Fix compilation errors in `Configs.java`, `EpiccBasedIntentAnalysis.java` | **No breaks found** — all APIs preserved in 4.7.1 |
| `-process-multiple-dex` invalid option | Soot 4.x renamed the flag | Replace with `-search-dex-in-archives` | Compile-time discovery |
| FlowDroid 2.10.0 incompatibility | `rvsec-apk` transitively pulls Soot ~4.3.0 | Maven nearest-definition resolves to 4.7.1 | If compile or runtime broken: upgrade FlowDroid to 2.14.1 (validated with CryptoAnalysis) or 2.15.1 (latest) |

## Risks / Trade-offs

| Risk | Probability | Mitigation |
|------|-------------|------------|
| API breaks in `Configs.java` (`Options.v().set_*()`) | Low | Compile-and-fix; Options API mostly stable — `set_force_android_jar(String)` and `set_src_prec(int)` exist in Soot 4.x |
| API breaks in `EpiccBasedIntentAnalysis.java` (`soot.dexpler.Util`) | Medium-High | If `Util.splitParameters()` removed in 4.x, rewrite with standard string parsing |
| FlowDroid 2.10.0 + Soot 4.7.1 incompatibility in `rvsec-apk` | Medium | Test compilation AND runtime (compile ≠ runtime — `NoSuchMethodError` possible); if broken, upgrade FlowDroid to 2.14.1 or 2.15.1 |
| Soot 4.7.1 still crashes on some APKs (bug #1071 not fixed upstream) | Medium | FIX 2 catches Flowgraph crashes; CHA crashes remain fatal. Issues #2185/#2228 (Kotlin/Compose typing fix) merged in develop post-4.7.1 — consider 4.7.2/4.8.0 when released |
| Kotlin/Compose exclusion impact on WTG | Medium | DECIDED (D2): `-exclude androidx.compose.` added alongside `kotlin.`/`kotlinx.`. Trade-off: loses Compose widget bodies for GUI analysis — acceptable because Compose uses declarative model, not `findViewById` |
| Kotlin exclusion loses reachability for generic specs | Low (JCA) / Medium (generic) | Acceptable for JCA (thesis focus); document trade-off for generic |
| Regression in 97 APKs that currently work | Low | Baseline comparison: `cryptoapp.apk` directlyReachesMop must be exact |
| Guava version conflict | Medium | GATOR uses Guava 27.1-jre, parent pom uses 19.0. Verify `mvn dependency:tree -pl rvsec-gator`; align in parent pom if needed |

**Rollback plan**: Work in branch `gh51-gator-soot47`. FIX 1, FIX 2, FIX 3 in separate commits. If FIX 3 causes regressions, revert FIX 3 and keep FIX 1 + FIX 2. Preserve current `rvsec-analysis-client.jar` as backup before rebuild.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Compilation | All active Java modules compile | `mvn clean compile` on rvsec-gator, rvsec-apk, rvsec-frame-computer | 1 run |
| Dependencies | No Guava/SLF4J/transitive conflicts | `mvn dependency:tree -pl rvsec-gator` | 1 run |
| Runtime (FlowDroid) | FlowDroid 2.10.0 + Soot 4.7.1 has no `NoSuchMethodError` at runtime | Execute `rvsec-apk` on 1 APK | 1 APK |
| Isolation | FIX 1 alone (Soot 3.3.0 + defensive options) on 5 crashing APKs | Validate if FIX 3 is necessary | 5 APKs |
| Smoke (crash) | 10 APKs that previously crashed produce JSON | Run GATOR directly on each APK | 10 APKs |
| Smoke (regression) | 10 APKs that currently work still produce JSON | Run GATOR directly on each APK | 10 APKs |
| Baseline | `cryptoapp.apk` output matches baseline | Compare JSON field counts | 1 APK |
| Fat JAR (E2E) | `rvsec-analysis-client.jar` runs without classpath errors | Execute via `rv-experiment` on 10 APKs (not just 1) | 10 APKs |

**Smoke test APKs** (from JCA gh50 dataset — instrumented OK, SA failed — confirmed GATOR crashes):
1. `dev.robin.flip_2_dnd_903.apk`
2. `com.qq7te.totalrecall_8.apk`
3. `net.youapps.calcyou_10.apk`
4. `org.woheller69.ttsengine_31.apk`
5. `com.itsfrz.tictactoe_2.apk`
6. `com.github.girator.rebooter_14.apk`
7. `gizz.tapes.foss_63.apk`
8. `com.iyox.wormhole_5013.apk`
9. `org.librefit.app_10501.apk`
10. `io.github.dorumrr.happytaxes_10.apk`

Source: `APKS_JCA/errors/instrument_and_sa_errors.json` (32 total APKs with inst OK + SA failed)

**Success criteria**: ≥7/10 previously-failing APKs produce JSON AND ≤1 regression among the 10 regression APKs (10% threshold).

## Open Questions

1. ~~**FlowDroid version**~~: Resolved — if `rvsec-apk` fails to compile or has runtime errors with Soot 4.7.1, upgrade FlowDroid to 2.14.1 (validated with CryptoAnalysis) or 2.15.1 (latest stable, both confirmed on Maven Central). Covered by task 2.12.

## Resolved Decisions (from multi-LLM review 2026-04-20 + implementation findings)

- **`all-reachable:true`**: Keep enabled. Disabling it is a Python-side change (command builder), not Java-side. It would reduce the method universe for reachability, potentially affecting coverage metrics. If CHA crashes persist after FIX 1+3, this can be revisited as a Python-side quick win in a separate change.
- **`SootClass.getMethods()` Chain→List**: False alarm — `getMethods()` already returned `List<SootMethod>` in Soot 3.3.0. The code's `Lists.newArrayList()` is redundant but harmless. Risk removed from table.
- **Issue #1641 characterization**: The issue is about `jb.sils` interfering with `use-original-names`, not directly about typing crashes. However, disabling `jb.sils` IS a documented workaround for typing crashes (confirmed in #1641 and #1975). The INV-ANA-16 text has been corrected to reflect this nuance.
- **Compose coverage gap**: Added `-exclude androidx.compose.` to FIX 1 to cover the dominant failure category (~71% of crashing APKs are Kotlin+Compose). Trade-off: loses Compose widget bodies for GUI analysis — acceptable because Compose widgets are not discoverable via traditional `findViewById`/XML layout analysis anyway.
- **API breaks Soot 3.3.0→4.7.1**: ZERO breaks found in `Configs.java`, `EpiccBasedIntentAnalysis.java`, or any other file. Only rename was `-process-multiple-dex` → `-search-dex-in-archives`. Risks overestimated.
- **CHA vs SPARK** (revised after gh51 stabilization): The earlier review concluded CHA was correct on grounds of speed and shared crash surface with SPARK. That conclusion was reversed in D5: with Soot 4.7.1 + FIX 1+2+3 the crash argument no longer holds, and the precision argument (impact on `reachesMop` accuracy → coverage metrics → MOP-aware navigation quality) tips the trade-off toward SPARK as default. CHA remains available via `-cgAlgorithm cha` for experiments where speed dominates over precision. See Decision D5.
- **Write-first JSON**: Critical discovery — external timeout kills the Java process without triggering `catch`. Reachability must be written to disk BEFORE WTG starts so it survives the kill.
- **Null receivers in virtual dispatch**: Soot 4.7.1 with `-no-bodies-for-excluded` creates phantom method refs where `jimpleUtil.receiver()` returns null. This is expected behavior for excluded packages — null-check is the correct fix (not a bug).
