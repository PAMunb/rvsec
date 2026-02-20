# Unified Static Analysis Tool — Implementation Plan

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

Skip incremental quick fixes (Phase 1 from `plano_analise_estatica.md`). Go directly to a **unified GATOR client** that replaces all three tools with a single Soot initialization, producing a single unified JSON output file.

Rationale: The quick fixes address symptoms but maintain the fundamental 3x redundancy. The unified approach eliminates root cause and simplifies the architecture per P1 (Simplicity).

---

## 2. Architecture

### Before (3 separate runs)

```
GESDA (Soot init #1, call graph never used) → .gesda JSON
GATOR (Soot init #2, fixpoint + WTG)        → .wtg JSON
REACH (Soot init #3, call graph + BFS)       → .reach CSV
```

Total: 3 Soot initializations, 3 class loading passes, up to 2 call graph constructions.

### After (1 unified run)

```
GATOR + RvsecUnifiedClient (Soot init #1) → unified .json
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

Inside the unified GATOR client:

- `Scene.v().getCallGraph()` provides the call graph built during GATOR's analysis phase
- GATOR runs Soot in whole-program mode (`-w`) without `all-reachable`
- The resulting CG contains all edges reachable from Soot's detected entry points
- Supplemented by GATOR's `AndroidCallGraph.v()` for GUI-specific reachability
- This is sufficient for all reachability queries: `reachable`, `reaches_mop`, `directly_reaches_mop`

### Fallback (if CG is insufficient)

If testing reveals missing reachability for specific APKs, the unified client can optionally enable CHA mode via the GATOR `-withCHA` flag, which adds `cg.cha enabled:true`. CHA is conservative (every call site resolved to all possible targets) and fast (no points-to analysis needed). This provides a complete call graph without the `all-reachable` performance cost.

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

### Dropped Fields (P3: no backward compatibility)

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

## 5. Unified JSON Schema

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

## 6. Java Implementation: `RvsecUnifiedClient`

### Location

`$RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/RvsecUnifiedClient.java`

### Class Structure

```java
public class RvsecUnifiedClient implements GUIAnalysisClient {
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
        List<UnifiedWindow> windows = extractWindows(output);

        // 4. Extract WTG transitions
        TransitionData transitions = extractTransitions(wtg);

        // 5. Run reachability analysis (replaces REACH)
        ReachabilityData reachability = runReachability(mopDir);

        // 6. Build unified result and save as JSON
        UnifiedResult result = new UnifiedResult(...);
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

These two fields are GESDA-exclusive (GATOR doesn't expose them). The unified client extracts them from decoded layout XMLs:

1. GATOR already decodes APK resources with apktool (`lib/gator/gator` calls `decode_res_from_apk()`). Decoded XML files are available at `Configs.resourceLocation`.
2. For each activity, find its layout file via `setContentView(R.layout.X)` pattern in Soot method bodies.
3. Parse the decoded layout XML (`Configs.resourceLocation/layout/{name}.xml`) using standard Java DOM parser.
4. Extract `android:inputType` attribute (apktool decodes to string names like `"textPassword"`, no integer mapping needed).
5. Extract `android:entries` attribute, resolve `@array/...` reference by parsing `res/values/arrays.xml`.
6. Match XML widgets to GATOR widgets by comparing `idName` from XML with `idNode.getIdName()` from GATOR nodes.

### Reachability Analysis (replaces REACH)

Implemented directly inside the unified client using Soot's Scene (already loaded by GATOR) + JGraphT:

```java
private ReachabilityData runReachability(String mopDir) {
    // 1. Load MOP method signatures from .mop spec files
    Set<SootMethod> mopMethods = loadMopMethods(mopDir);

    // 2. Get entry points from activity classes (public/protected methods)
    Set<SootMethod> entryPoints = getEntryPoints();

    // 3. Build JGraphT graph from Soot call graph
    CallGraph cg = Scene.v().getCallGraph();
    Graph<SootMethod, DefaultEdge> graph = buildJGraph(cg);
    DijkstraShortestPath<SootMethod, DefaultEdge> dijkstra =
        new DijkstraShortestPath<>(graph);

    // 4. For each app class and method, compute:
    //    - reachable: has path from any entry point
    //    - reachesMop: has path to any MOP method
    //    - directlyReachesMop: has direct edge to MOP method
    // 5. Complement with lifecycle and listener callback reachability
}
```

Key differences from current REACH:
- **No `all-reachable`**: Uses GATOR's default CG (see Section 3)
- **JGraphT instead of SootReachabilityStrategy**: Cached Dijkstra instead of thousands of independent BFS traversals (fixes R3, R4)
- **GATOR-based entry points**: Uses `getAllEventsAndTheirHandlers()` + `getLifecycleHandlers()` for automatic discovery of Android lifecycle and event handlers
- **No GESDA dependency**: REACH currently reads GESDA output for activity/lifecycle info. The unified client has this directly from GATOR

### Parameter Passing

Uses GATOR's existing `-clientParam` mechanism (`Configs.clientParams`):

```bash
python gator a -p app.apk \
  --client-jar rvsec-unified-client.jar \
  --out result.json \
  -client RvsecUnifiedClient \
  -clientParam mopDir=/path/to/jca/specs \
  --timeout 600
```

The client reads `mopDir` from `Configs.clientParams`. Output path from `Configs.pathoutfilename`.

### Maven Dependencies

Add to `rvsec-gator-client/pom.xml`:

```xml
<!-- JGraphT for efficient reachability (Dijkstra with caching) -->
<dependency>
    <groupId>org.jgrapht</groupId>
    <artifactId>jgrapht-core</artifactId>
    <version>1.5.1</version>
</dependency>

<!-- MOP spec parser (exclude Soot to avoid version conflict with GATOR's Soot 3.3.0) -->
<dependency>
    <groupId>br.unb.cic</groupId>
    <artifactId>rvsec-mop-extractor</artifactId>
    <exclusions>
        <exclusion><groupId>ca.mcgill.sable</groupId><artifactId>soot</artifactId></exclusion>
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

Build as fat JAR using `maven-shade-plugin` to bundle JGraphT + mop-extractor + apk-reader into a single `rvsec-unified-client.jar`. This avoids classpath complexity at invocation time.

### Soot Version Consideration

GATOR uses Soot 3.3.0 (OSU fork), while REACH uses FlowDroid's Soot ~4.3.0. The unified client runs inside GATOR, so it uses Soot 3.3.0. Core Soot APIs (`Scene.v()`, `CallGraph`, `SootClass`, `SootMethod`) are stable across versions. The `rvsec-mop-extractor` and `rvsec-apk` dependencies exclude their Soot transitive deps to avoid conflicts.

---

## 7. Python Implementation

### 7.1 New File: `UnifiedParser`

**Path**: `modules/rv-static-analysis/src/rv_static_analysis/parser/static/unified_parser.py`

Replaces the three separate parsers (GesdaParser, GatorParser, ReachParser) with a single parser that reads the unified JSON.

```python
class UnifiedParser(BaseStaticAnalysisParser):
    """Parser for the unified static analysis JSON output."""

    def parse_file(self, file_path, package) -> StaticAnalysisData:
        """Parse unified JSON into StaticAnalysisData."""
        # Read JSON, handle missing file (return empty StaticAnalysisData)
        # Call _parse_classes(), _parse_windows(), _parse_transitions()
        # Return StaticAnalysisData(classes, windows, wtg)
```

Internal methods:
- `_parse_classes(data, package) -> Classes`: Iterates `data["reachability"]`, normalizes class names via SignatureNormalizer, filters by code_package (INV-ANA-03), creates Clazz and Method objects.
- `_parse_windows(data, package, classes) -> Windows`: Iterates `data["windows"]`, processes widgets and listeners into Widget and WidgetEvent objects. Reuses listener-to-event mapping from current GesdaParser.
- `_parse_transitions(data, windows) -> WindowTransitionGraph`: Iterates `data["transitions"]`, resolves source/target windows by ID, creates WTG graph.

Error handling (INV-ANA-06): Each section parsed in try/except. On failure, returns empty domain objects for that section.

### 7.2 `StaticAnalyzer` Changes

**Path**: `modules/rv-static-analysis/src/rv_static_analysis/analysis/static/static_analysis.py`

Remove `_run_gesda()`, `_run_gator()`, `_run_reachability()`. Replace with single `_run_unified()`:

```python
def _run_unified(self) -> None:
    """Execute the unified static analysis tool."""
    cmd_args = self.config.get_tool_command(
        'unified', self.app.path, self.unified_file,
        mop_dir=self.config.mop_dir
    )
    unified_cmd = Command(
        cmd_args[0], cmd_args[1:],
        timeout=self.config.unified_timeout
    )
    self._execute_command("UNIFIED", self.unified_file, unified_cmd)
```

`StaticAnalysisResult` changes:
- Remove `gesda_file`, `gator_file`, `reach_file`
- Add `unified_file: str` and `timed_out: bool`

`get_static_data()` changes:
- Use UnifiedParser instead of three separate parsers

### 7.3 `RVStaticAnalysisConfig` Changes

**Path**: `modules/rv-static-analysis/src/rv_static_analysis/config.py`

Remove: `gesda_jar`, `gator_dir`, `reach_jar` path resolution.

Add:
```python
unified_jar: Optional[str] = Field(default=None, description="Path to unified client JAR")
jvm_memory: str = Field(default="8g", description="JVM max heap for unified tool")
unified_timeout: float = Field(default=600.0, description="Timeout in seconds")
```

`get_tool_command('unified', ...)`:
```python
return [
    'python', components['gator_python'], 'a',
    '-p', apk_path,
    '--client-jar', self.unified_jar,
    '--out', output_file,
    '-client', 'RvsecUnifiedClient',
    '-clientParam', f'mopDir={mop_dir}',
    '--timeout', str(int(self.unified_timeout))
]
```

### 7.4 `StaticAnalysisParser` Changes

**Path**: `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py`

Replace three parser instances with UnifiedParser. Add `parse_unified()` method. Update `read_static_analysis_files()` to use `.json` extension.

### 7.5 rv-platform `StaticAnalysisComponent` Changes

**Path**: `modules/rv-platform/src/rv_platform/components/static_analysis.py`

Update `copy_static_analysis_files()`: change extensions list from `[EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH]` to `[EXTENSION_METHODS, EXTENSION_UNIFIED]`.

### 7.6 Constants

**Path**: `modules/rv-android-core/src/rv_android_core/constants.py`

Add: `EXTENSION_UNIFIED = ".json"`

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
- Create `openspec/changes/gh-unified-static-analysis/proposal.md`
- Summary: Unify GESDA + GATOR + REACH into single GATOR client
- Scope: Java (unified client), Python (unified parser, config, analyzer)

### Phase 3: Specs (delta spec)
- Create `openspec/changes/gh-unified-static-analysis/specs.md`
- Update analysis domain spec invariants:
  - INV-ANA-01: Remove GESDA-before-REACH ordering (single tool, no dependencies)
  - INV-ANA-02: Keep SignatureNormalizer requirement, update to reference UnifiedParser
  - INV-ANA-03: Keep code_package requirement, update to reference UnifiedParser
  - INV-ANA-06: Update graceful degradation to reference per-section JSON parsing
  - INV-ANA-11: Update from "three output files" to "one unified JSON"
- Update FR04 (GATOR), FR05 (GESDA), FR06 (REACH) → unified FR

### Phase 4: Design
- Create `openspec/changes/gh-unified-static-analysis/design.md`
- This plan document serves as the design input

### Phase 5: Tasks
- Create `openspec/changes/gh-unified-static-analysis/tasks.md`
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

### Task Group 1: Java — RvsecUnifiedClient Core (WTG + Windows)

**Files**: `RvsecUnifiedClient.java` (new), `pom.xml` (update)

1. Create `RvsecUnifiedClient.java` in GATOR client module
2. Port WTG extraction from `RvsecWtgClient.run()` into `extractTransitions()`
3. Implement `extractWindows()` using GATOR's internal APIs (getActivities, getActivityRoots, PropertyManager)
4. Implement JSON serialization for windows + transitions sections
5. Update `pom.xml` with maven-shade-plugin for fat JAR
6. Test: unified client produces window + transition data matching current GESDA + GATOR output for `cryptoapp.apk`

### Task Group 2: Java — inputType and entries Extraction

**Files**: `RvsecUnifiedClient.java`

1. Implement layout file resolution: find `setContentView(R.layout.X)` in Soot method bodies, resolve to layout filename
2. Implement decoded XML parsing: read `Configs.resourceLocation/layout/{name}.xml` with DOM parser
3. Extract `android:inputType` attribute (string from apktool-decoded XML)
4. Extract `android:entries` attribute, resolve `@array/...` from `res/values/arrays.xml`
5. Match XML data to GATOR widget nodes by `idName`
6. Test: verify `inputType` and `entries` match current GESDA output for `cryptoapp.apk`

### Task Group 3: Java — Reachability Analysis

**Files**: `RvsecUnifiedClient.java`, `pom.xml`

1. Add JGraphT, rvsec-mop-extractor, rvsec-apk dependencies with Soot exclusions
2. Implement `loadMopMethods()`: load MOP spec signatures using JavamopFacade
3. Implement `getEntryPoints()`: public/protected methods of activity classes
4. Implement `buildJGraph()`: convert Soot CallGraph to JGraphT DirectedGraph
5. Implement reachability computation: `reachable`, `reachesMop`, `directlyReachesMop`
6. Implement `complementWithLifecycleCallbacks()` and `complementWithListenerCallbacks()`
7. Test: verify reachability data matches current REACH output for `cryptoapp.apk` (minor differences expected — document and justify)

### Task Group 4: Java — Build and Deploy

1. Build unified client JAR: `mvn package` with shade plugin
2. Copy `rvsec-unified-client.jar` to `rv-android/lib/unified/`
3. Verify JAR runs correctly via GATOR launcher command

### Task Group 5: Python — Constants and UnifiedParser

**Files**: `constants.py`, `unified_parser.py` (new)

1. Add `EXTENSION_UNIFIED = ".json"` to constants
2. Create `UnifiedParser` class extending BaseStaticAnalysisParser
3. Implement `_parse_classes()` from `reachability` section
4. Implement `_parse_windows()` from `windows` section
5. Implement `_parse_transitions()` from `transitions` section
6. Ensure SignatureNormalizer applied to all class names and signatures (INV-ANA-02)
7. Ensure code_package filtering applied (INV-ANA-03)
8. Unit tests: parsing well-formed JSON, empty JSON, missing sections, missing file

### Task Group 6: Python — Config and StaticAnalyzer

**Files**: `config.py`, `static_analysis.py`

1. Update `RVStaticAnalysisConfig`: remove old tool paths, add `unified_jar`, `jvm_memory`, `unified_timeout`
2. Update `get_tool_command()` for unified tool
3. Update `StaticAnalyzer`: replace 3-tool pipeline with single `_run_unified()`
4. Update `StaticAnalysisResult`: `unified_file`, `timed_out`
5. Handle `RVCommandTimeoutError` in `_execute_command()`
6. Update `get_static_data()` to use UnifiedParser
7. Unit tests: config validation, command generation, timeout handling

### Task Group 7: Python — StaticAnalysisParser and Platform

**Files**: `static_analysis_parser.py`, `static_analysis.py` (rv-platform)

1. Update `StaticAnalysisParser` facade to use UnifiedParser
2. Update `read_static_analysis_files()` for `.json` extension
3. Update rv-platform `StaticAnalysisComponent.copy_static_analysis_files()` extensions
4. Delete old parsers (backup to `backup/` first per P3)
5. Delete old parser tests
6. Grep all modules for dangling imports, clean up

### Task Group 8: Test Resources and Integration

1. Create `tests/resources/cryptoapp.apk.json` test resource from real unified output
2. Create `test_unified_parser.py` with comprehensive tests
3. Update `test_static_analysis_parser.py` for unified flow
4. Update `test_static_analysis.py` for single-tool pipeline
5. Update `test_config.py` for new configuration fields
6. Update `conftest.py` fixtures

### Task Group 9: Spec Updates and Documentation

1. Update `openspec/specs/analysis/spec.md` per Phase 3 above
2. Update `modules/rv-static-analysis/CLAUDE.md`
3. Update `modules/rv-android-core/CLAUDE.md` if constants changed

---

## 10. Verification Strategy

### Unit Verification

1. **Unified parser**: parse well-formed JSON → correct `StaticAnalysisData` (classes, windows, wtg match expected values)
2. **Config**: `get_tool_command('unified', ...)` produces correct command with all parameters
3. **StaticAnalyzer**: `_run_unified()` dispatches single Command with timeout; handles timeout and errors correctly
4. **Old parser deletion**: no dangling imports across all modules

### Integration Verification

1. **Baseline capture**: Run current 3-tool pipeline on `cryptoapp.apk`, save outputs
2. **Unified tool output**: Run unified client on `cryptoapp.apk`, save unified JSON
3. **Compare**:
   - Windows: count, names, widget counts, widget IDs, text, hint, inputType, entries, listeners
   - Transitions: count, source/target IDs, event types, handler signatures
   - Reachability: class count, method count, reachable flags, reaches_mop flags, directly_reaches_mop flags
4. **Accepted differences**: Minor reachability differences due to different CG construction (no `all-reachable`). Document differences. Verify `directly_reaches_mop` is preserved (direct edges are CG-construction-independent).

### Batch Verification

1. Run unified pipeline on 5 diverse APKs from gh26 batch
2. Measure total execution time vs 3-tool baseline
3. Expected: ~1/3 of pre-fix time per APK
4. Verify no crashes, clean timeout handling for problematic APKs

### End-to-End Verification

1. Run full rv-experiment with unified tool on `cryptoapp.apk`
2. Verify: static analysis completes, rv-agent receives correct `StaticAnalysisData`, MOP scoring works, WTG navigation works, coverage tracking works

---

## 11. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| GATOR's CG missing non-GUI reachable methods | Some methods incorrectly marked as unreachable | Supplement with CHA if needed (via `-withCHA` flag) |
| GATOR's widget tree missing some GESDA widgets | Reduced widget matching accuracy | GATOR's interprocedural analysis is actually MORE complete for event-triggered widgets |
| Soot version conflict (GATOR 3.3.0 vs rvsec-mop-extractor) | Build failure or runtime ClassNotFoundException | Exclude Soot from all transitive deps; test at build time |
| MopFacade dependency on JavaMOP creates transitive conflicts | Build failure | Fallback: simpler regex-based `.mop` file parser |
| GATOR fixpoint solver timeout on complex APKs | Unified tool hangs | Process-level timeout (600s) via Command.timeout + GATOR's `--timeout` flag |
| Combined inputType flags in decoded XML (e.g., `"textPassword\|textVisiblePassword"`) | Incorrect inputType parsing | Handle pipe-separated flags, take first value |

---

## 12. Critical Files Reference

### Java (RVSEC_HOME) — New/Modified

| File | Action |
|------|--------|
| `rvsec-gator/client/.../RvsecUnifiedClient.java` | **NEW** — unified client |
| `rvsec-gator/client/pom.xml` | **MODIFY** — add JGraphT, mop-extractor, apk-reader deps + shade plugin |
| `rvsec-gator/client/.../RvsecWtgClient.java` | Reference only (port WTG logic) |
| `rvsec-reachability/.../JGraphReachabilityStrategy.java` | Reference only (port reachability logic) |
| `rvsec-reachability/.../ReachabilityAnalysis.java` | Reference only (port complement logic) |
| `rvsec-reachability/.../MopFacade.java` | Reference only (port MOP loading) |
| `rvsec-gesda/.../XmlParser.java` | Reference only (port inputType/entries extraction) |
| `rvsec-gesda/.../SootAnalyze.java` | Reference only (port setContentView pattern) |

### Python (rv-android) — New/Modified

| File | Action |
|------|--------|
| `rv-android-core/.../constants.py` | **MODIFY** — add EXTENSION_UNIFIED |
| `rv-static-analysis/.../parser/static/unified_parser.py` | **NEW** — unified JSON parser |
| `rv-static-analysis/.../analysis/static/static_analysis.py` | **MODIFY** — single tool pipeline |
| `rv-static-analysis/.../config.py` | **MODIFY** — unified tool config |
| `rv-static-analysis/.../parser/static/static_analysis_parser.py` | **MODIFY** — delegate to UnifiedParser |
| `rv-platform/.../components/static_analysis.py` | **MODIFY** — update file extensions |

### Python (rv-android) — Delete (backup to `backup/` first)

| File | Reason |
|------|--------|
| `rv-static-analysis/.../parser/static/gesda_parser.py` | Replaced by UnifiedParser |
| `rv-static-analysis/.../parser/static/gator_parser.py` | Replaced by UnifiedParser |
| `rv-static-analysis/.../parser/static/reach_parser.py` | Replaced by UnifiedParser |
| `rv-static-analysis/tests/.../test_gesda_parser.py` | Tests for deleted parser |
| `rv-static-analysis/tests/.../test_gator_parser.py` | Tests for deleted parser |
| `rv-static-analysis/tests/.../test_reach_parser.py` | Tests for deleted parser |

### Lib Deployment

| File | Action |
|------|--------|
| `rv-android/lib/unified/rvsec-unified-client.jar` | **NEW** — fat JAR from maven-shade |
| `rv-android/lib/gesda/rvsec-gesda.jar` | Keep until verified, then remove |
| `rv-android/lib/reach/rvsec-reach.jar` | Keep until verified, then remove |

---

## 13. Build Commands

```bash
source /etc/profile

# Build unified client fat JAR
cd $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator/client
mvn package -DskipTests
cp target/rvsec-unified-client.jar $RVSEC_HOME/rv-android/lib/unified/

# Run unified analysis on test APK
cd $RVSEC_HOME/rv-android
python lib/gator/gator a \
  -p apks_examples/cryptoapp.apk \
  --client-jar lib/unified/rvsec-unified-client.jar \
  --out /tmp/cryptoapp.json \
  -client RvsecUnifiedClient \
  -clientParam mopDir=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca \
  --timeout 600
```
