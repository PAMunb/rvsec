# Static Analysis Client — Implementation Plan

**Date**: 2026-02-20
**Track**: Full SDD (Explore → Propose → Specs → Design → Tasks → Implement → Verify → Archive)
**Prerequisite analysis**: `docs/20260220_analise_estatica_ferramentas.md` (root cause), `docs/20260220_analise_estatica_pre_plano.md` (feasibility)

---

## 1. Context and Motivation

### Problem

The gh26 experiments show very low static analysis success rates. Three separate Java tools (GESDA, GATOR, REACH) each initialize Soot/FlowDroid independently — 3 redundant Soot startups per APK, totaling 3 separate call graph constructions. Combined with critical misconfigurations (`cg all-reachable`, no process timeouts, no JVM memory flags), analysis that should take 2-5 minutes per APK instead takes 30-60+ minutes or hangs indefinitely.

### Root Causes (from `analise_estatica_ferramentas.md`)

| ID | Severity | Tool | Issue |
|----|----------|------|-------|
| R1 | CRITICAL | REACH | `all-reachable` inflates call graph 10-100x |
| R2 | CRITICAL | REACH | `--timeout` doesn't control CG construction |
| G1 | CRITICAL | GESDA | Dead `cg all-reachable` configuration |
| A1 | CRITICAL | GATOR | Timeout not passed from rv-android |
| P1 | CRITICAL | ALL | No process-level timeout (Command.timeout=None) |
| G2 | HIGH | GESDA | Recursive methods without cycle detection (4 methods) |
| R3 | HIGH | REACH | O(M*E + M*K) BFS traversals over massive graph |
| R4 | HIGH | REACH | Hardcoded SootReachabilityStrategy (no caching) |

### Decision

Skip incremental quick fixes (Phase 1 from `plano_analise_estatica.md`). Go directly to a **single GATOR-based analysis client** that performs all static analysis (windows, widgets, reachability) in one Soot initialization, producing a single JSON output file.

Rationale: The quick fixes address symptoms but maintain the fundamental 3x redundancy. A single analysis client eliminates the root cause and simplifies the architecture per P1 (Simplicity).

---

## 2. Architecture

### Before (3 separate runs)

```
GESDA (Soot init #1, call graph never used) → .gesda JSON
GATOR (Soot init #2, fixpoint + WTG)        → .wtg JSON
REACH (Soot init #3, call graph + BFS)       → .reach CSV
```

Total: 3 Soot initializations, 3 class loading passes, up to 2 call graph constructions.

### After (1 analysis client run)

```
GATOR + RvsecAnalysisClient (Soot init #1) → analysis .json
```

Total: 1 Soot initialization, 1 class loading pass, 1 call graph (GATOR's default CG via SPARK).

### Key Benefits

- **1 Soot init instead of 3** — eliminates ~66% of startup overhead
- **1 call graph instead of 3** — the dominant cost
- **Single JSON output** — simpler pipeline, simpler parsing
- **No `all-reachable`** — GATOR's default CG is fast and sufficient (see Section 3)
- **Interprocedural widget data** — GATOR's interprocedural analysis covers dynamically-registered listeners that intra-procedural pattern matching misses

---

## 3. Critical Decision: `all-reachable` and Call Graph Strategy

### The Problem

Both GESDA and REACH configure Soot with `cg all-reachable`, which forces Soot to treat **every concrete method in every loaded class** as a call graph entry point. For a typical APK, this means:
- Without `all-reachable`: 50-200 entry points (Android lifecycle callbacks) → CG with 10K-50K edges → built in seconds
- With `all-reachable`: 50K-200K entry points (every method in every class, including framework and libraries) → CG with 100K-1M+ edges → built in 5-60+ minutes

### Analysis: Will JCA Methods Be Missing Without `all-reachable`?

The concern: if we don't make "all methods reachable", JCA classes (Cipher, MessageDigest, KeyGenerator, etc.) might not appear in the call graph, breaking MOP reachability detection.

**Answer: This concern is unfounded.** Here's why:

1. **JCA classes are framework classes** (`javax.crypto.Cipher`, `java.security.MessageDigest`, etc.). They exist in the Android SDK's `android.jar` / `rt.jar`. Soot loads them as phantom references. They appear as **call targets** in the call graph — any app method calling `Cipher.getInstance()` creates a CG edge `appMethod → Cipher.getInstance()`.

2. **CHA (Class Hierarchy Analysis) call graph** resolves ALL virtual calls based on the class hierarchy. If app code calls `cipher.init()`, CHA creates edges to every concrete implementation of `Cipher.init()` in the hierarchy. CHA doesn't need entry points — it resolves every call site in every loaded class.

3. **SPARK with FlowDroid callback discovery** starts from Android lifecycle callbacks (onCreate, onClick, etc.) and transitively discovers all reachable methods. Any app method calling JCA APIs is reachable from these callbacks. The only methods that would be "missing" are truly dead code — unreachable from any Android entry point — which are irrelevant for runtime monitoring anyway.

4. **What `all-reachable` actually adds** is edges from framework-internal methods that are never called by app code. REACH then wastes time performing BFS over these irrelevant edges. The 10-100x performance cost provides zero benefit for MOP reachability detection.

### Decision: Use GATOR's Default Call Graph

Inside the GATOR analysis client:

- `Scene.v().getCallGraph()` provides the call graph built during GATOR's analysis phase
- GATOR runs Soot in whole-program mode (`-w`) without `all-reachable`
- The resulting CG contains all edges reachable from Soot's detected entry points
- Supplemented by GATOR's `AndroidCallGraph.v()` for GUI-specific reachability
- This is sufficient for all reachability queries: `reachable`, `reaches_mop`, `directly_reaches_mop`

### Fallback (if CG is insufficient)

If testing reveals missing reachability for specific APKs, the analysis client can optionally enable CHA mode via the GATOR `-withCHA` flag, which adds `cg.cha enabled:true`. CHA is conservative (every call site resolved to all possible targets) and fast (no points-to analysis needed). This provides a complete call graph without the `all-reachable` performance cost.

---

## 4. Field Retention Decisions

Based on comprehensive field-by-field usage analysis tracing every field from static analysis output through all consumers in rv-agent, rv-coverage, rv-screen-parser, and rv-platform.

### Mandatory Fields (system breaks without these)

| Field | Source | Critical Consumers |
|-------|--------|--------------------|
| `Method.signature` | REACH | TransitionManager, RVAgentVisitor, AbstractScreenVisitor, repository_initializer |
| `Method.reachable` | REACH | repository_initializer → CoverageAnalyzer (denominator) |
| `Method.reaches_mop` | REACH | MopScorer (+150), TransitionManager (+50), visitors ([M] marker), strategies |
| `Method.directly_reaches_mop` | REACH | MopScorer (+300), visitors ([DM] marker) |
| `Method.name`, `Method.params`, `Method.class_name` | REACH | repository_initializer → MethodCoverageData |
| `Clazz.name`, `Clazz.is_activity`, `Clazz.is_main_activity` | REACH | repository_initializer, Classes.get_main_activity() |
| `Window.id` | GATOR | WTG edges, TransitionManager.find_window_id_for_activity |
| `Window.name`, `Window.activity` | GESDA/GATOR | TransitionManager activity matching (3 strategies) |
| `Window.widgets` | GESDA/GATOR | AbstractScreenVisitor.find_matching_widget, TransitionManager._find_widget_globally |
| `Widget.widget_id` | GESDA/GATOR | Key in Window.widgets, action.widget_id assignment |
| `Widget.name` | GESDA/GATOR | Window.get_widget_by_name, RVAgentVisitor._find_widget_globally |
| `Widget.events` | GESDA/GATOR | AbstractScreenVisitor._update_action_mop_related_info (type+signature matching) |
| `WidgetEvent.event_type` | GESDA/GATOR | Matches action.event for MOP enrichment |
| `WidgetEvent.signature` | GESDA/GATOR | Lookup in Classes.methods for reaches_mop check |
| `WTG.transitions` | GATOR | TransitionManager.get_unvisited_targets |

### Important Fields (degrades accuracy without these)

| Field | Source | Consumer |
|-------|--------|----------|
| `Widget.text` | GESDA | AbstractScreenVisitor.find_matching_widget (text-based fallback matching) |
| `Widget.hint` | GESDA | RVAgentVisitor.find_matching_widget (hint-based fallback matching) |

### Kept But No Current Production Consumer

| Field | Decision | Rationale |
|-------|----------|-----------|
| `Widget.input_type` | **KEEP** | User explicitly requested; may be useful for LLM prompts |
| `Widget.entries` | **KEEP** | User explicitly requested; Spinner entries for LLM prompts |

### Dropped Fields (JSON output schema — Python model fields unchanged)

These fields are NOT included in the new analysis JSON output. The corresponding fields in the Python domain model (`Widget`, `Window`, `Clazz`, etc. in `rv_android_core/domain/`) remain with their default values — this is a non-goal per design.md ("Not changing the `StaticAnalysisData` domain model").

| Field | Reason |
|-------|--------|
| `Widget.field` | Only cosmetic use in `_with_field()` descriptive text |
| `Widget.layout_file` / `Window.layout_file` | No production consumer |
| `Widget.registeredInFile` | No production consumer |
| `WidgetEvent.clazz`, `WidgetEvent.method` | Only `signature` is used for MOP lookup |
| `Window.class_name` | Redundant with `Window.activity` |
| `Window.fields`, `Clazz.fields` | Never populated by any parser |
| `Widget.widget_type` | Only set during parsing, never read downstream |
| `Widget.resource_id`, `Widget.class_name`, `Widget.handlers` | Never set by any parser |
| `Widget.reaches_mop`, `Widget.directly_reaches_mop` | Never set (MOP resolved at Method level via events→signature) |
| `REACH.possiblePath`, `REACH.allPathsToMop` | Debug-only, not consumed by rv-agent |

---

## 5. Analysis JSON Schema

Single output file replacing `.gesda` + `.wtg` + `.reach`:

```json
{
  "package": "com.example.app",
  "mainActivity": "com.example.MainActivity",
  "windows": [
    {
      "id": 1,
      "name": "com.example.MainActivity",
      "type": "ACTIVITY",
      "isMain": true,
      "widgets": [
        {
          "id": 2131165267,
          "idName": "edittext_username",
          "type": "android.widget.EditText",
          "text": "",
          "hint": "Enter username",
          "inputType": "text",
          "entries": [],
          "listeners": [
            {
              "eventType": "click",
              "handler": "<com.example.MainActivity: void onClick(android.view.View)>"
            }
          ]
        }
      ]
    }
  ],
  "transitions": [
    {
      "sourceId": 1,
      "targetId": 2,
      "events": [
        {
          "type": "click",
          "handler": "<com.example.MainActivity: void onLoginClick(android.view.View)>",
          "widgetId": 2131165268,
          "widgetClass": "android.widget.Button",
          "widgetName": "button_login"
        }
      ]
    }
  ],
  "reachability": [
    {
      "className": "com.example.MainActivity",
      "isActivity": true,
      "isMainActivity": true,
      "methods": [
        {
          "name": "onCreate",
          "signature": "<com.example.MainActivity: void onCreate(android.os.Bundle)>",
          "reachable": true,
          "reachesMop": true,
          "directlyReachesMop": false
        }
      ]
    }
  ]
}
```

### Schema Design Notes

- `windows` replaces GESDA output. Each window has a `widgets` array with `inputType` and `entries`.
- `transitions` replaces GATOR WTG output. Same structure. Window IDs in transitions reference windows in the `windows` array.
- `reachability` replaces REACH CSV output. JSON array of class objects with nested method arrays.
- Dropped from REACH: `possiblePath`, `allPathsToMop` (debug-only, not consumed by rv-agent).
- Dropped from GESDA: `layoutFileName`, `field`, `registeredInFile` (see Section 4).

---

## 6. Java Implementation: `RvsecAnalysisClient`

### Location

`$RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/RvsecAnalysisClient.java`

### Class Structure

```java
public class RvsecAnalysisClient implements GUIAnalysisClient {
    @Override
    public void run(GUIAnalysisOutput output) {
        // 1. Read parameters from Configs.clientParams
        String mopDir = getClientParam("mopDir");

        // 2. Build WTG (reuse RvsecWtgClient logic)
        WTGBuilder wtgBuilder = new WTGBuilder();
        wtgBuilder.build(output);
        WTGAnalysisOutput wtgAO = new WTGAnalysisOutput(output, wtgBuilder);
        WTG wtg = wtgAO.getWTG();

        // 3. Extract windows + widgets (replaces GESDA)
        List<AnalysisWindow> windows = extractWindows(output);

        // 4. Extract WTG transitions
        TransitionData transitions = extractTransitions(wtg);

        // 5. Run reachability analysis (replaces REACH)
        ReachabilityData reachability = runReachability(mopDir);

        // 6. Build analysis result and save as JSON
        AnalysisResult result = new AnalysisResult(...);
        saveResult(result);
    }
}
```

### Window/Widget Extraction (replaces GESDA)

Uses GATOR's internal APIs which are richer than GESDA's intra-procedural pattern matching:

| GESDA Field | GATOR API Source |
|-------------|-----------------|
| `window.name` | `output.getActivities()` → `SootClass.getName()` |
| `window.type` | `getActivities()` = ACTIVITY, `getDialogs()` = DIALOG, `getOptionsMenu()` = OPTIONSMENU |
| `window.isMain` | `output.getMainActivity()` |
| `window.widgets[]` | `output.getActivityRoots(activity)` + recursive `getChildren()` — complete widget tree |
| `widget.id` | `NNode.idNode.getIdValue()` |
| `widget.idName` | `NNode.idNode.getIdName()` |
| `widget.type` | `NObjectNode.getClassType().getName()` |
| `widget.text` | `PropertyManager.v().getTextsOrTitlesOfView(node)` |
| `widget.hint` | `PropertyManager.v().getHintOfView(node)` |
| `widget.listeners` | `output.getAllEventsAndTheirHandlers(guiObject)` — ALL listeners, not just transition-causing |

### `inputType` and `entries` Extraction

These two fields are GESDA-exclusive (GATOR doesn't expose them). The analysis client extracts them from decoded layout XMLs:

1. GATOR already decodes APK resources with apktool (`lib/gator/gator` calls `decode_res_from_apk()`). Decoded XML files are available at `Configs.resourceLocation`.
2. For each activity, find its layout file via `setContentView(R.layout.X)` pattern in Soot method bodies.
3. Parse the decoded layout XML (`Configs.resourceLocation/layout/{name}.xml`) using standard Java DOM parser.
4. Extract `android:inputType` attribute (apktool decodes to string names like `"textPassword"`, no integer mapping needed).
5. Extract `android:entries` attribute, resolve `@array/...` reference by parsing `res/values/arrays.xml`.
6. Match XML widgets to GATOR widgets by comparing `idName` from XML with `idNode.getIdName()` from GATOR nodes.

### Reachability Analysis (replaces REACH)

Implemented directly inside the analysis client using Soot's Scene (already loaded by GATOR) + JGraphT:

```java
private ReachabilityData runReachability(String mopDir) {
    // 1. Load MOP method signatures from .mop spec files
    //    MopFacade returns (className, methodName) pairs — NO parameter types.
    //    This is by design: MOP monitors instrument ALL overloads of a method.
    Set<MopMethod> mopSignatures = loadMopSignatures(mopDir);

    // 2. Resolve MOP signatures to SootMethods in the call graph.
    //    Match by class+method name ONLY (same as MopFacade):
    //      sootMethod.getDeclaringClass().getName().equals(mopClassName)
    //        && sootMethod.getName().equals(mopMethodName)
    //    ALL overloads of a MOP method become seeds — e.g., both
    //    Cipher.init(int, Key) and Cipher.init(int, Key, AlgorithmParameterSpec)
    //    are included if any Cipher.init variant appears in a MOP spec.
    Set<SootMethod> mopMethods = resolveMopInScene(mopSignatures);

    // 3. Get entry points from activity classes (public/protected methods)
    Set<SootMethod> entryPoints = getEntryPoints();

    // 4. Build JGraphT directed graph from Soot call graph
    CallGraph cg = Scene.v().getCallGraph();
    DefaultDirectedGraph<SootMethod, DefaultEdge> graph = buildJGraph(cg);

    // 5. Multi-source BFS — O(V+E) total, boolean flags only
    //    a) reachable: BFS forward from ALL entry points simultaneously
    Set<SootMethod> reachableSet = multiSourceBfs(graph, entryPoints);
    //    b) reachesMop: BFS on REVERSE graph from ALL MOP methods (all overloads)
    EdgeReversedGraph<SootMethod, DefaultEdge> reversed = new EdgeReversedGraph<>(graph);
    Set<SootMethod> reachesMopSet = multiSourceBfs(reversed, mopMethods);
    //    c) directlyReachesMop: scan outgoing edges, check if target is MOP
    Set<SootMethod> directMopSet = findDirectMopCallers(graph, mopMethods);

    // 6. Complement with lifecycle and listener callback reachability
}
```

Key differences from current REACH:
- **No `all-reachable`**: Uses GATOR's default CG (see Section 3)
- **JGraphT instead of SootReachabilityStrategy**: Multi-source BFS O(V+E) instead of thousands of independent BFS traversals (fixes R3, R4)
- **GATOR-based entry points**: Uses `getAllEventsAndTheirHandlers()` + `getLifecycleHandlers()` for automatic discovery of Android lifecycle and event handlers
- **No GESDA dependency**: REACH currently reads GESDA output for activity/lifecycle info. The analysis client has this directly from GATOR

### Parameter Passing

Uses GATOR's existing `-clientParam` mechanism (`Configs.clientParams`) and the `-jre` parameter for rt.jar:

```bash
python gator a -p app.apk \
  --client-jar rvsec-analysis-client.jar \
  --out result.json \
  -client RvsecAnalysisClient \
  -clientParam mopDir=/path/to/jca/specs \
  --jre /path/to/jre/lib/rt.jar \
  --timeout 600
```

The client reads `mopDir` from `Configs.clientParams`. Output path from `Configs.pathoutfilename`.

### rt.jar Requirement (Spike Q6)

**Problem**: Without `rt.jar` in Soot's classpath, JCA framework classes (`javax.crypto.Cipher`, `java.security.MessageDigest`, etc.) are loaded as **phantom references** with no active body. Soot can resolve static calls like `MessageDigest.getInstance()` (the call site in app code is sufficient), but **cannot resolve instance method calls** like `md.update()` and `md.digest()` because virtual dispatch requires the class hierarchy from the active body. This breaks `reachesMop` and `directlyReachesMop` for all JCA instance methods — a critical correctness issue.

**Current tools**: REACH and GESDA both pass `rt.jar` explicitly via `set_soot_classpath()` + `set_prepend_classpath(true)`. GATOR's `Main.java` accepts `-jre` (L59-60) and includes it in `computeClasspath()` (L180), but the Python launcher **never passes** this parameter.

**Solution**: Add `--jre` parameter to the GATOR launcher (Spike Q6, Task 0.6). The launcher will forward it as `-jre <path>` to `Main.java`. GATOR's existing classpath computation (`Configs.android + ":" + Configs.jre + depJars`) will then include `rt.jar`, enabling Soot to load JCA classes with active bodies.

**Fallback**: If GATOR's Soot 3.3.0 has issues with `rt.jar`, test with `android-platforms` from the Sable/FlowDroid team (enhanced `android.jar` with stubs, cloned at `/home/pedro/desenvolvimento/aplicativos/android/platforms-sable`).

### Maven Dependencies

Add to `rvsec-gator-client/pom.xml`:

```xml
<!-- JGraphT for efficient reachability (multi-source BFS) -->
<dependency>
    <groupId>org.jgrapht</groupId>
    <artifactId>jgrapht-core</artifactId>
    <version>1.5.1</version>
</dependency>

<!-- MOP spec parser (exclude BOTH Soot groupIds to avoid version conflict with GATOR's Soot 3.3.0) -->
<dependency>
    <groupId>br.unb.cic</groupId>
    <artifactId>rvsec-mop-extractor</artifactId>
    <exclusions>
        <exclusion><groupId>ca.mcgill.sable</groupId><artifactId>soot</artifactId></exclusion>
        <exclusion><groupId>org.soot-oss</groupId><artifactId>soot</artifactId></exclusion>
    </exclusions>
</dependency>

<!-- APK metadata reader (exclude FlowDroid/Soot) -->
<dependency>
    <groupId>br.unb.cic</groupId>
    <artifactId>rvsec-apk</artifactId>
    <exclusions>
        <exclusion><groupId>de.fraunhofer.sit.sse.flowdroid</groupId><artifactId>*</artifactId></exclusion>
    </exclusions>
</dependency>
```

Build as fat JAR using `maven-assembly-plugin` (same pattern as `rvsec-reachability`) to bundle JGraphT + mop-extractor + apk-reader into a single `rvsec-analysis-client.jar`. This avoids classpath complexity at invocation time.

### Soot Version Consideration

GATOR uses Soot 3.3.0 (OSU fork), while REACH uses FlowDroid's Soot ~4.3.0. The analysis client runs inside GATOR, so it uses Soot 3.3.0. Core Soot APIs (`Scene.v()`, `CallGraph`, `SootClass`, `SootMethod`) are stable across versions. The `rvsec-mop-extractor` and `rvsec-apk` dependencies exclude their Soot transitive deps to avoid conflicts.

---

## 7. Python Implementation

### 7.1 Rewrite: `StaticAnalysisParser`

**Path**: `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`

Parses the static analysis JSON into domain objects (Classes, Windows, WindowTransitionGraph).

```python
class StaticAnalysisParser:
    """Parses the static analysis JSON into StaticAnalysisData.

    Uses LoggingManager directly for logging. Reads JSON sections
    (reachability, windows, transitions) and creates domain objects.
    """

    def parse_file(self, file_path, package) -> StaticAnalysisData:
        """Parse analysis JSON into StaticAnalysisData."""
        # Read JSON, handle missing file (return empty StaticAnalysisData)
        # Call _parse_classes(), _parse_windows(), _parse_transitions()
        # Return StaticAnalysisData(classes, windows, wtg)
```

Internal methods:
- `_parse_classes(data, package) -> Classes`: Iterates `data["reachability"]`, applies SignatureNormalizer as safety net (INV-ANA-02 — should be no-op since Java client already writes `$` notation via `SootClass.getName()`), filters by code_package (INV-ANA-03 — uses `App.code_package` from `PackageDetector`, NOT manifest package), creates Clazz and Method objects.
- `_parse_windows(data, package, classes) -> Windows`: Iterates `data["windows"]`, processes widgets and listeners into Widget and WidgetEvent objects. Reuses listener-to-event mapping from current GesdaParser.
- `_parse_transitions(data, windows) -> WindowTransitionGraph`: Iterates `data["transitions"]`, resolves source/target windows by ID, creates WTG graph.

Error handling (INV-ANA-06): Each section parsed in try/except. On failure, returns empty domain objects for that section.

### Normalization Strategy (D7 — normalize at the source)

**Problem history**: During legacy result regeneration (`rvsec-regerar-resultados/docs/NOVO/06_normalizacao_inner_classes.md`), inner class notation mismatches between Soot (`.`) and AspectJ (`$`) caused catastrophic issues: 10M+ warnings for 2 APKs, 50% performance degradation, unusable logs. The root cause was that GESDA and GATOR used Soot APIs that sometimes returned Java source notation (`.`) instead of JVM notation (`$`). A `SignatureNormalizer` was implemented to convert `.` → `$` at parse time with a heuristic.

**Design in gh27**: The new `RvsecAnalysisClient` eliminates the root cause by consistently using `SootClass.getName()` and `SootMethod.getSignature()` for all names in the JSON output. These APIs return JVM `$` notation. The Python `SignatureNormalizer` remains applied (INV-ANA-02) as defense-in-depth:

| Layer | Responsibility | Expected behavior |
|-------|---------------|-------------------|
| Java (`RvsecAnalysisClient`) | Write class names using `SootClass.getName()` — canonical `$` notation | Primary normalization — prevents the problem at the source |
| Python (`SignatureNormalizer`) | Apply `.` → `$` heuristic on all parsed names (INV-ANA-02) | Safety net — should be no-op. If it changes anything, log a WARNING (indicates Java client bug) |
| Python (`StaticAnalysisParser`) | Filter classes by `App.code_package` from `PackageDetector` (INV-ANA-03) | Correct package filtering — handles 27.5% APKs with manifest ≠ code package |

**Known limitation — Package.Class where Package == Class** (e.g., `com.hwloc.lstopo.ZoomView.ZoomView`): This is an AspectJ bug, not a Soot bug. Soot correctly writes `ZoomView.ZoomView` (package separator). AspectJ incorrectly logs `ZoomView$ZoomView` (treats as inner class). The `SignatureNormalizer` heuristic cannot distinguish this case. Impact: 2 APKs in dataset excluded (see `rvsec-regerar-resultados/docs/NOVO/06_normalizacao_inner_classes.md`, Section 9.1 — Opção A). This does NOT affect gh27 because the issue is in Coverage.aj runtime logs, not in static analysis JSON output.

### Package Detection Strategy (code_package vs manifest package)

The `package` parameter in `parse_file()` must be `App.code_package` (detected by `PackageDetector` in rv-android-core), NOT `App.package_name` (from AndroidManifest.xml). The distinction matters for ~27.5% of APKs where manifest ≠ implementation package (game engines, forks, wrappers — see `rvsec-regerar-resultados/docs/NOVO/07_pacotes.md`).

Package filtering happens in Python, not Java. Soot's `Scene.v().getApplicationClasses()` uses its own heuristics for class loading that may not match `code_package`. The Python parser is the correct layer because it has access to `PackageDetector` results.

### 7.2 `StaticAnalyzer` Changes

**Path**: `modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py`

Remove `_run_gesda()`, `_run_gator()`, `_run_reachability()`. Replace with single `_run_analysis()`:

```python
def _run_analysis(self) -> None:
    """Execute the static analysis tool."""
    cmd_args = self.config.get_tool_command(
        'analysis', self.app.path, self.analysis_file,
        mop_dir=self.config.mop_dir
    )
    analysis_cmd = Command(
        cmd_args[0], cmd_args[1:],
        timeout=self.config.analysis_timeout
    )
    self._execute_command("ANALYSIS", self.analysis_file, analysis_cmd)
```

`StaticAnalysisResult` changes:
- Remove `gesda_file`, `gator_file`, `reach_file`
- Add `analysis_file: str` and `timed_out: bool`

`get_static_data()` changes:
- Use StaticAnalysisParser instead of three separate parsers

### 7.3 `RVStaticAnalysisConfig` Changes

**Path**: `modules/rv-static-analysis/src/rv_static_analysis/config.py`

Remove: `gesda_jar`, `gator_dir`, `reach_jar` path resolution.

Add:
```python
analysis_client_jar: Optional[str] = Field(default=None, description="Path to analysis client JAR")
jvm_memory: str = Field(default="8g", description="JVM max heap for analysis tool")
analysis_timeout: float = Field(default=600.0, description="Timeout in seconds")
```

`get_tool_command('analysis', ...)`:
```python
return [
    'python', components['gator_python'], 'a',
    '-p', apk_path,
    '--client-jar', self.analysis_client_jar,
    '--out', output_file,
    '-client', 'RvsecAnalysisClient',
    '-clientParam', f'mopDir={mop_dir}',
    '--jre', self.rt_jar,
    '--timeout', str(int(self.analysis_timeout))
]
```

Note: `rt_jar` field already exists in config (L65-68, resolved from `RV_RT_JAR` env or sdkman default). The `--jre` parameter is added to the GATOR launcher in Spike Q6 (Task 0.6) — it forwards to GATOR's `Main.java -jre` which populates `Configs.jre` used in `computeClasspath()`.

### 7.4 `StaticAnalysisParser` Caller Updates

Update `read_static_analysis_files()` and any callers that used the old multi-parser API to use `StaticAnalysisParser.parse_file()` with `.json` extension.

### 7.5 rv-platform `StaticAnalysisComponent` Changes

**Path**: `modules/rv-platform/src/rv_platform/components/static_analysis.py`

Update `copy_static_analysis_files()`: change extensions list from `[EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH]` to `[EXTENSION_METHODS, EXTENSION_STATIC_ANALYSIS]`.

### 7.6 Constants

**Path**: `modules/rv-android-core/src/rv_android_core/constants.py`

Add: `EXTENSION_STATIC_ANALYSIS = ".json"`. Remove: `EXTENSION_GESDA`, `EXTENSION_GATOR`, `EXTENSION_REACH` (old constants — all consumers migrated by this change).

### 7.7 Files to Delete (P3)

Backup to `backup/` then delete:
- `parser/static/gesda_parser.py`
- `parser/static/gator_parser.py`
- `parser/static/reach_parser.py`
- `tests/parser/test_gesda_parser.py`
- `tests/parser/test_gator_parser.py`
- `tests/parser/test_reach_parser.py`

Grep all modules for dangling imports of deleted parsers.

---

## 8. SDD Workflow

This change follows the Full SDD track per `docs/WORKFLOW.md`:

### Phase 1: Explore (DONE)
- `docs/20260220_analise_estatica_ferramentas.md` — root cause analysis of 3 tools
- `docs/20260220_analise_estatica_pre_plano.md` — consolidation feasibility
- Sequential thinking: `all-reachable` safety analysis, CHA strategy
- Field-by-field usage matrix across all consumer modules

### Phase 2: Propose
- Create `openspec/changes/gh27-unified-static-analysis/proposal.md`
- Summary: Consolidate GESDA + GATOR + REACH into single GATOR analysis client
- Scope: Java (analysis client), Python (static analysis parser, config, analyzer)

### Phase 3: Specs (delta spec)
- Create `openspec/changes/gh27-unified-static-analysis/specs.md`
- Update analysis domain spec invariants:
  - INV-ANA-01: Remove GESDA-before-REACH ordering (single tool, no dependencies)
  - INV-ANA-02: Keep SignatureNormalizer requirement, update to reference StaticAnalysisParser
  - INV-ANA-03: Keep code_package requirement, update to reference StaticAnalysisParser
  - INV-ANA-06: Update graceful degradation to reference per-section JSON parsing
  - INV-ANA-11: Update from "three output files" to "one analysis JSON"
- Update FR04 (GATOR), FR05 (GESDA), FR06 (REACH) → single FR

### Phase 4: Design
- Create `openspec/changes/gh27-unified-static-analysis/design.md`
- This plan document serves as the design input

### Phase 5: Tasks
- Create `openspec/changes/gh27-unified-static-analysis/tasks.md`
- Task groups (see Section 9)

### Phase 6: Implement
- Execute tasks per Section 9

### Phase 7: Verify
- `/rv-verify` on affected modules
- `/opsx:verify` against change artifacts

### Phase 8: Archive
- `/opsx:archive` with spec sync

---

## 9. Implementation Tasks

### Task Group 0: Verification Spike (Pre-Implementation)

Answer the 6 Open Questions (Q1-Q6) before coding to prevent wasted effort. Verifies: PropertyManager hint API, CG population inside GATOR client, `-clientParam` propagation, apktool `@array` handling, rvsec-mop-extractor Soot API surface, rt.jar required for JCA instance methods.

### Task Group 1: Java — RvsecAnalysisClient Core + Reachability (Coverage Denominator)

**Files**: `RvsecAnalysisClient.java` (new), `pom.xml` (update)

Reachability comes first because it defines the method universe — the denominator for all coverage calculations. The JSON output writes this section first with flush, so timeout preserves the most critical data (D5).

1. Create `RvsecAnalysisClient.java` in GATOR client module
2. Add JGraphT, rvsec-mop-extractor, rvsec-apk dependencies with Soot exclusions
3. Implement MOP loading: `loadMopSignatures()` → `resolveMopInScene()` (all overloads)
4. Implement `getEntryPoints()`: public/protected methods of activity classes
5. Implement `buildJGraph()`: convert Soot CallGraph to JGraphT DirectedGraph
6. Implement reachability computation: `reachable`, `reachesMop`, `directlyReachesMop` via multi-source BFS (D2)
7. Implement `complementWithLifecycleCallbacks()` and `complementWithListenerCallbacks()`
8. Write `reachability` JSON section and flush
9. Test: verify reachability data against current REACH output for `cryptoapp.apk`

### Task Group 2: Java — Windows and WTG Extraction

**Files**: `RvsecAnalysisClient.java`

1. Implement `extractWindows()` using GATOR's internal APIs (getActivities, getActivityRoots, PropertyManager)
2. Port WTG extraction from `RvsecWtgClient.run()` into `extractTransitions()`
3. Write `windows` section (flush), then `transitions` section (flush + close)
4. Test: analysis client produces window + transition data matching current GESDA + GATOR output for `cryptoapp.apk`

### Task Group 3: Java — inputType and entries Extraction

**Files**: `RvsecAnalysisClient.java`

1. Implement layout file resolution: find `setContentView(R.layout.X)` in Soot method bodies, resolve to layout filename
2. Implement decoded XML parsing: read `Configs.resourceLocation/layout/{name}.xml` with DOM parser
3. Extract `android:inputType` attribute (string from apktool-decoded XML)
4. Extract `android:entries` attribute, resolve `@array/...` from `res/values/arrays.xml`
5. Match XML data to GATOR widget nodes by `idName`
6. Test: verify `inputType` and `entries` match current GESDA output for `cryptoapp.apk`

### Task Group 4: Java — Build, Deploy, and Tests

1. Build analysis client fat JAR: `cd $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client && mvn clean install -DskipTests` (assembly creates JAR, resources-plugin copies to `rv-android/lib/analysis-client/`)
2. Verify JAR runs correctly via GATOR launcher command (`teste.sh`)
3. Normalization validation (D7): code review + cryptoapp.apk output verification
4. JUnit 4 unit tests (no Soot): MOP signature loading, BFS on synthetic JGraphT graph, JSON output structure, XML inputType parsing
5. JUnit 4 integration tests (Soot + GATOR): full run on `cryptoapp.apk` with assertions, baseline comparison with tolerances
6. Run: `mvn test -DskipTests=false` (unit), `mvn verify -DskipTests=false -DskipITs=false` (integration)

### Task Group 5: Python — Constants and StaticAnalysisParser

**Files**: `constants.py`, `static_analysis_parser.py` (rewrite)

1. Add `EXTENSION_STATIC_ANALYSIS = ".json"` to constants
2. Rewrite `StaticAnalysisParser` — standalone class that parses the JSON into StaticAnalysisData
3. Implement `_parse_classes()` from `reachability` section
4. Implement `_parse_windows()` from `windows` section
5. Implement `_parse_transitions()` from `transitions` section
6. Ensure SignatureNormalizer applied to all class names and signatures (INV-ANA-02)
7. Ensure code_package filtering applied (INV-ANA-03)
8. Unit tests: parsing well-formed JSON, empty JSON, missing sections, missing file

### Task Group 6: Python — Config, StaticAnalyzer, CLI, and rv-experiment Config

**Files**: `config.py`, `static_analysis.py`, `__main__.py` (rv-static-analysis), `rv-experiment/config.py`

1. Update `RVStaticAnalysisConfig`: remove old tool paths, add `analysis_client_jar`, `jvm_memory`, `analysis_timeout`
2. Update `get_tool_command()` for analysis tool
3. Update `StaticAnalyzer`: replace 3-tool pipeline with single `_run_analysis()`
4. Update `StaticAnalysisResult`: `analysis_file`, `timed_out`
5. Handle `RVCommandTimeoutError` in `_execute_command()`
6. Update `get_static_data()` to use StaticAnalysisParser
7. Update `rv-static-analysis/__main__.py`: replace CLI args (`--gesda-jar`, `--gator-dir`, `--reach-jar` → `--analysis-client-jar`), tool choices, config mapping, result display, help text
8. Update `rv-experiment/config.py` `get_static_analysis_config()`: provide `analysis_client_jar`, `jvm_memory`, `analysis_timeout`
9. Unit tests: config validation, command generation, timeout handling

### Task Group 7: Python — Parser Cleanup and Platform

**Files**: `static_analysis_parser.py`, `static_analysis.py` (rv-platform)

1. Verify `StaticAnalysisParser.parse_file()` is compatible with all callers
2. Update `read_static_analysis_files()` for `.json` extension
3. Update rv-platform `StaticAnalysisComponent.copy_static_analysis_files()` extensions
4. Delete old parsers and `base_parser.py` (backup to `backup/` first per P3)
5. Delete old parser tests
6. Grep all modules for dangling imports, clean up

### Task Group 8: Tests

1. Create `tests/resources/cryptoapp.apk.json` test resource from real analysis output
2. Create `test_static_analysis_parser.py` with comprehensive tests
3. Update `test_static_analysis_parser.py` for single-parser flow
4. Update `test_static_analysis.py` for single-tool pipeline
5. Update `test_config.py` for new configuration fields
6. Update `conftest.py` fixtures

### Task Group 9: Documentation and Specs

1. Update `openspec/specs/analysis/spec.md` per Phase 3 above
2. Update `modules/rv-static-analysis/CLAUDE.md`
3. Update `modules/rv-android-core/CLAUDE.md` if constants changed

### Task Group 10: E2E Validation (Final Gate)

Full rv-experiment run exercising the entire pipeline: pre-processing → execution → post-processing. Includes data compatibility verification (Coverage.aj signature format match, MOP flag consistency, MOP error correlation) and APK-specific validation (inner class normalization, package mismatch, batch run on 5 diverse APKs).

---

## 10. Reference APK: cryptoapp

All spikes, unit tests, integration tests, and baseline comparisons use `cryptoapp.apk` — a custom app built by our team specifically for this type of validation. Having full control over the source code means we know exactly what the analysis output should contain.

**Source code**: `examples/cryptoapp/` (Android project, Gradle 7.6.4)
**Pre-built APK**: `apks_examples/cryptoapp.apk`
**Package**: `br.unb.cic.cryptoapp`

### Structure

| Class | Type | JCA Calls | Widgets/Events |
|-------|------|-----------|----------------|
| `MainActivity` | ACTIVITY (main) | — | 3 Buttons (XML onClick: `showScreenMessageDigest`, `showScreenCipher`, `showGenerated`), OptionsMenu with `OnMenuItemClickListener` + `onOptionsItemSelected` |
| `CipherActivity` | ACTIVITY | `Cipher.getInstance()`, `cipher.init()`, `cipher.doFinal()`, `KeyGenerator.getInstance()` | EditText, Button (programmatic `setOnClickListener`), TextView |
| `MessageDigestActivity` | ACTIVITY | `MessageDigest.getInstance()`, `md.update()`, `md.digest()` | Spinner (with `entries` array), EditText, Button, TextView |
| `CryptographyActivity` | ACTIVITY | `Cipher`, `MessageDigest`, `Mac`, `KeyPairGenerator` (multiple algorithms) | — |

### Expected Analysis Output

| Section | Expected |
|---------|----------|
| **Windows** | 4 activities: MainActivity (main), CipherActivity, MessageDigestActivity, CryptographyActivity |
| **Transitions** | MainActivity → CipherActivity (button + menu), MainActivity → MessageDigestActivity (button + menu), MainActivity → CryptographyActivity (button) |
| **Reachability** | `unreachableEncrypt()` and `unreachableHash()` should be NOT reachable from lifecycle callbacks. JCA static methods (`getInstance()`) should always appear. JCA instance methods (`update()`, `digest()`, `init()`, `doFinal()`) depend on rt.jar (Spike Q6) |
| **Widgets** | Spinner with `entries` from `arrays.xml`, EditText with `inputType`, programmatic + XML onClick listeners |

### Why cryptoapp

- **Controlled source**: we wrote it, we know every class/method/widget
- **JCA coverage**: exercises Cipher, MessageDigest, Mac, KeyPairGenerator with multiple algorithms
- **Unreachable methods**: `CipherUtil.unreachableEncrypt()` and `MessageDigestUtil.unreachableHash()` are never called — validates reachability analysis
- **Widget diversity**: XML onClick, programmatic `setOnClickListener`, `OnMenuItemClickListener`, Spinner entries — validates window/widget extraction
- **WTG transitions**: clear Activity→Activity navigation via buttons and menus — validates transition extraction
- **Fast analysis**: small app (~10 classes), analysis should complete in seconds — ideal for iterative spike testing

---

## 11. Verification Strategy

### Unit Verification

1. **StaticAnalysisParser**: parse well-formed JSON → correct `StaticAnalysisData` (classes, windows, wtg match expected values)
2. **Config**: `get_tool_command('analysis', ...)` produces correct command with all parameters
3. **StaticAnalyzer**: `_run_analysis()` dispatches single Command with timeout; handles timeout and errors correctly
4. **Old parser deletion**: no dangling imports across all modules

### Integration Verification

1. **Baseline capture**: Run current 3-tool pipeline on `cryptoapp.apk`, save outputs
2. **Analysis client output**: Run analysis client on `cryptoapp.apk`, save analysis JSON
3. **Compare**:
   - Windows: count, names, widget counts, widget IDs, text, hint, inputType, entries, listeners
   - Transitions: count, source/target IDs, event types, handler signatures
   - Reachability: class count, method count, reachable flags, reaches_mop flags, directly_reaches_mop flags
4. **Accepted differences**: Minor reachability differences due to different CG construction (no `all-reachable`). Document differences. Verify `directly_reaches_mop` is preserved (direct edges are CG-construction-independent).

### Batch Verification

1. Run analysis pipeline on 5 diverse APKs from gh26 batch
2. Measure total execution time vs 3-tool baseline
3. Expected: ~1/3 of pre-fix time per APK
4. Verify no crashes, clean timeout handling for problematic APKs

### End-to-End Verification

1. Run full rv-experiment with analysis tool on `cryptoapp.apk`
2. Verify: static analysis completes, rv-agent receives correct `StaticAnalysisData`, MOP scoring works, WTG navigation works, coverage tracking works

---

## 12. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| GATOR's CG missing non-GUI reachable methods | Some methods incorrectly marked as unreachable | Supplement with CHA if needed (via `-withCHA` flag) |
| GATOR's widget tree missing some GESDA widgets | Reduced widget matching accuracy | GATOR's interprocedural analysis is actually MORE complete for event-triggered widgets |
| Soot version conflict (GATOR 3.3.0 vs rvsec-mop-extractor) | Build failure or runtime ClassNotFoundException | Exclude Soot from all transitive deps; test at build time |
| MopFacade dependency on JavaMOP creates transitive conflicts | Build failure | Fallback: simpler regex-based `.mop` file parser |
| GATOR fixpoint solver timeout on complex APKs | Analysis tool hangs | Process-level timeout (600s) via Command.timeout + GATOR's `--timeout` flag |
| Combined inputType flags in decoded XML (e.g., `"textPassword\|textVisiblePassword"`) | Incorrect inputType parsing | Handle pipe-separated flags, take first value |

---

## 13. Critical Files Reference

### Java (RVSEC_HOME) — New/Modified

| File | Action |
|------|--------|
| `rvsec-gator/client/.../RvsecAnalysisClient.java` | **NEW** — analysis client |
| `rvsec-gator/client/pom.xml` | **MODIFY** — add JGraphT, mop-extractor, apk-reader deps + assembly plugin |
| `rvsec-gator/client/src/test/java/.../` | **NEW** — 6 JUnit test files (4 unit + 2 integration) |
| `rvsec-gator/client/src/test/resources/` | **NEW** — test fixtures (.mop files, layout XML, baseline JSON) |
| `rvsec-gator/client/.../RvsecWtgClient.java` | **REFERENCE then DELETE** (Task 7.8f) — port WTG logic, then backup + delete |
| `rvsec-android/pom.xml` (parent) | **MODIFY** — comment out rvsec-gesda, rvsec-reachability modules (Task 7.8e) |
| `rvsec-reachability/.../JGraphReachabilityStrategy.java` | Reference only (port reachability logic) |
| `rvsec-reachability/.../ReachabilityAnalysis.java` | Reference only (port complement logic) |
| `rvsec-reachability/.../MopFacade.java` | Reference only (port MOP loading) |
| `rvsec-gesda/.../XmlParser.java` | Reference only (port inputType/entries extraction) |
| `rvsec-gesda/.../SootAnalyze.java` | Reference only (port setContentView pattern) |

### Python (rv-android) — New/Modified

| File | Action |
|------|--------|
| `rv-android-core/.../constants.py` | **MODIFY** — add EXTENSION_STATIC_ANALYSIS, remove old extension constants |
| `rv-static-analysis/.../parser/static/static_analysis_parser.py` | **REWRITE** — analysis JSON parser |
| `rv-static-analysis/tests/.../test_static_analysis_parser.py` | **NEW** — comprehensive parser unit tests |
| `rv-static-analysis/tests/resources/cryptoapp.apk.json` | **NEW** — test fixture from real analysis output |
| `rv-static-analysis/.../analysis/static/static_analysis.py` | **MODIFY** — single tool pipeline |
| `rv-static-analysis/.../config.py` | **MODIFY** — analysis tool config |
| `rv-static-analysis/.../__main__.py` | **MODIFY** — CLI args, tool choices, result display (473 lines) |
| `rv-static-analysis/.../parser/static/base_parser.py` | **DELETE** — dead code after removing 3 child parsers |
| `rv-static-analysis/CLAUDE.md` | **MODIFY** — reflect analysis tool architecture (Task 9.1) |
| `rv-experiment/.../config.py` | **MODIFY** — `get_static_analysis_config()` must provide new fields |
| `rv-experiment/.../constants.py` | **MODIFY** — remove old extension re-exports, add EXTENSION_STATIC_ANALYSIS (Task 7.6a) |
| `rv-platform/.../components/static_analysis.py` | **MODIFY** — update file extensions |
| `rv-android-core/CLAUDE.md` | **MODIFY** — add EXTENSION_STATIC_ANALYSIS to constants section (Task 9.2) |
| `rv-agent-validation/.../experiment/runner.py` | **MODIFY** — replace 3-file parse with `parse_file()` |
| `rv-agent-validation/.../experiment/config.py` | **MODIFY** — replace 3-file glob with `.json` |
| `rv-agent-validation/.../preprocessing/instrumentation.py` | **MODIFY** — replace 14+ refs to 3-file pattern |
| `rv-agent-validation/CLAUDE.md` | **MODIFY** — remove 3-file references (Task 7.9g) |

### Python (rv-android) — Tests to Update

| File | Action |
|------|--------|
| `rv-agent/tests/unit/test_transition_manager.py` | **MODIFY** — use `parse_file()` + JSON fixture |
| `rv-agent/tests/unit/test_navigation_guidance.py` | **MODIFY** — use `parse_file()` + JSON fixture |
| `rv-agent/tests/unit/test_rvagent_visitor.py` | **MODIFY** — use `parse_file()` + JSON fixture |
| `rv-agent/tests/online/test_static_analysis.py` | **MODIFY** — check `.json` instead of `.reach/.wtg/.gesda` |
| `rv-agent/tests/fixtures/static_analysis/cryptoapp/cryptoapp.apk.json` | **NEW** — unified JSON fixture |
| `rv-agent/tests/fixtures/static_analysis/cryptoapp/cryptoapp.apk.{reach,wtg,gesda}` | **DELETE** — old fixtures (P3) |
| `rv-agent-validation/tests/test_navigation_guidance.py` | **MODIFY** — use `parse_file()` |
| `rv-agent-validation/tests/calibration/test_preprocess.py` | **MODIFY** — create/verify `.json` instead of 3 files |

### Python (rv-android) — Delete (backup to `backup/` first)

| File | Reason |
|------|--------|
| `rv-static-analysis/.../parser/static/gesda_parser.py` | Deleted (P3) |
| `rv-static-analysis/.../parser/static/gator_parser.py` | Deleted (P3) |
| `rv-static-analysis/.../parser/static/reach_parser.py` | Deleted (P3) |
| `rv-static-analysis/tests/.../test_gesda_parser.py` | Tests for deleted parser |
| `rv-static-analysis/tests/.../test_gator_parser.py` | Tests for deleted parser |
| `rv-static-analysis/tests/.../test_reach_parser.py` | Tests for deleted parser |

### Lib Deployment

| File | Action |
|------|--------|
| `rv-android/lib/analysis-client/rvsec-analysis-client.jar` | **NEW** — fat JAR from maven-assembly |
| `rv-android/lib/gator/teste.sh` | **MODIFY** — update client name, jar path, add `-clientParam` (Task 4.4) |
| `rv-android/lib/gator/rvsec-gator-client.jar` | **DELETE** — superseded by analysis-client (Task 7.8c) |
| `rv-android/lib/gator/.gitignore` | **MODIFY** — remove old JAR entry (Task 7.8c) |
| `rv-android/lib/gator/scripts/` | **DELETE** — standalone dev scripts, never referenced (Task 7.8d) |
| `rv-android/lib/gesda/` | **DELETE** — entire directory, superseded by analysis client (Task 7.8a) |
| `rv-android/lib/reach/` | **DELETE** — entire directory, superseded by analysis client (Task 7.8b) |

---

## 14. Build Commands

```bash
source /etc/profile

# Build analysis client fat JAR and copy to rv-android/lib/analysis-client/
# maven-resources-plugin copies the JAR during the install phase
cd $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client
mvn clean install -DskipTests

# Run static analysis on test APK
# --jre is REQUIRED for JCA instance method resolution (Spike Q6)
cd $RVSEC_HOME/rv-android
python lib/gator/gator a \
  -p apks_examples/cryptoapp.apk \
  --client-jar lib/analysis-client/rvsec-analysis-client.jar \
  --out /tmp/cryptoapp.json \
  -client RvsecAnalysisClient \
  -clientParam mopDir=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca \
  --jre $JAVA_HOME/jre/lib/rt.jar \
  --timeout 600
```
