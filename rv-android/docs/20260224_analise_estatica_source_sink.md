# Deep Analysis: Source-Sink + Widget-Method Mapping for RV-Agent

**Date**: 2026-02-24
**Author**: Pedro Henrique Teixeira Costa
**Status**: Research / Brainstorming
**Related**: gh27 (unified static analysis), rv-agent exploration strategy (gh26)

## Context

RV-Agent currently uses boolean MOP flags (`reaches_target`, `directly_reaches_target`) from static analysis to prioritize UI actions during exploration. After gh27 (unified static analysis), the JGraphT call graph and MOP resolution infrastructure exist in the Java client but only boolean flags are exported. Two proposed analyses could dramatically improve agent decision-making:

1. **Source-sink analysis**: Map which interactive widgets (sources) can trigger which MOP methods (sinks)
2. **Widget -> method + params**: Full call chain from handler to MOP sink, with statically-determined parameter values

This document analyzes how these would benefit rv-agent. This is a research/brainstorming exercise to evaluate the value proposition — not an implementation plan.

### Architectural Note: Runtime MOP Feedback Channel

Today, RV-Agent does **NOT** have access to real-time MOP method coverage during execution. The `CoverageTracker` (rv-platform) monitors logcat in a background thread and populates a `LogcatRepository` with confirmed method executions, but this data is not fed back to the agent loop. The agent only tracks UI-level interactions (visit counts per widget) and infers MOP coverage from static metadata.

However, as analyzed in **Section 6.3** of this document, injecting the `LogcatRepository` reference into the agent is **architecturally feasible** with minimal changes — it follows the same dependency injection pattern already used for `StaticAnalysisData`. When both static analysis data AND the coverage repository are present (always the case when running via rv-platform), the agent would have access to **confirmed** runtime MOP coverage, enabling true coverage-directed targeting.

Benefits B1-B8 in this document are written assuming this runtime feedback channel is available, since the analysis in Section 6.3 shows it is a straightforward extension. The standalone CLI mode (`rv-agent run`) would gracefully degrade to inferred coverage when the repository is not injected.

---

## 1. Current Architecture: How RV-Agent Uses Static Analysis Today

### 1.1 Data Flow: Static Analysis -> Agent Decision-Making

```
StaticAnalysisData (from GATOR/gh27)
├── wtg (WindowTransitionGraph)
│   ├── windows: List[Window]
│   │   └── transitions: List[{target, widget_id, event_type}]
│   └── Used by: TransitionManager, NavigationGuidance, WtgScorer
│
├── windows (Windows)
│   ├── windows: List[Window]
│   │   ├── id, activity
│   │   └── widgets: Dict[widget_id -> Widget]
│   │       └── events: List[{type, signature}]
│   └── Used by: RVAgentVisitor (widget matching)
│
└── classes (Classes)
    ├── methods: Dict[signature -> Method]
    │   ├── reachable: bool
    │   ├── reaches_target: bool
    │   └── directly_reaches_target: bool
    └── Used by: RVAgentVisitor (MOP enrichment), TransitionManager (path planning)
```

### 1.2 MOP Enrichment at Parse Time (RVAgentVisitor)

When the agent parses the current screen's UI hierarchy, `RVAgentVisitor._enrich_action_with_mop()` performs:

1. Finds the static Widget matching the runtime UI element (by resource-id, text, or hint)
2. Looks up widget.events (callbacks) — gets handler signature
3. Resolves handler signature to `StaticAnalysisData.classes.methods`
4. Copies boolean flags (`reaches_target`, `directly_reaches_target`) to the ItemAction
5. Adds `[M]` or `[DM]` markers to action.text for LLM visibility

Result: each `ItemAction` has:
- `reaches_target: bool` / `directly_reaches_target: bool`
- `widget_id: str` (static widget ID)
- `callback_signature: str` (handler method)
- `text` with `[M]`/`[DM]` markers

### 1.3 How MOP Data Influences Decisions

| Component | How it uses MOP data | Score impact |
|---|---|---|
| **MopScorer** | `directly_reaches_target` -> +300, `reaches_target` -> +150 | Highest single scorer |
| **WtgScorer** | Checks if action leads to unvisited screen | +250 for WTG-guided transition |
| **ScreenProcessor** | Adds MOP bonus to LLM action ordering | +100 (DM), +50 (M) |
| **TransitionManager** | `_calculate_target_priority()` checks widget events for MOP | +50 direct, +25 transitive |
| **Path planning** | `plan_path_to_mop_activity()` BFS to high MOP-density activities | Navigation targeting |

### 1.4 Widget Information Available Today

```python
# What the agent knows about each widget/action:
widget_id: str                    # Static widget ID from GATOR
reaches_target: bool                 # Boolean: transitively reaches MOP
directly_reaches_target: bool        # Boolean: directly calls MOP
callback_signature: str           # Handler method signature (e.g., "com.app.Handler.onClick")
event_type: str                   # "click", "input", "long_click"
text: str                         # Display text + [M]/[DM] markers
coordinates: Tuple[int, int]      # Device pixel coordinates
target_view: Dict                 # UI properties (class, resource_id, bounds)
```

### 1.5 What the Agent Does NOT Know

| Known | Unknown |
|---|---|
| "This button reaches MOP" (boolean) | **Which** specific MOP methods it reaches |
| Handler signature exists | **What** the handler actually does (call chain) |
| MOP methods exist in the app | **Which widget** triggers **which** MOP method |
| Coverage % at runtime | Which **uncovered** MOP method to target next |
| EditText exists with hint text | What **type of value** the input expects |
| Two buttons both score +300 | Whether they reach the **same or different** MOP methods |

---

## 2. The Five Problems with Binary MOP Flags

### P1: Equal Scoring of Unequal Actions

Two buttons both score +300 (directMOP) but one triggers `Cipher.getInstance` and the other `Mac.init`. The agent can't distinguish them — picks by position, test count, or random tiebreaker. This means the agent has no basis for prioritizing one crypto operation over another.

In practice: the agent might test `Cipher` operations 10 times while `Mac` operations remain untested, because the scorer treats all directMOP actions identically.

### P2: No Coverage-Directed Targeting

After covering `Cipher.getInstance` at runtime, the agent can't answer: "Which widget triggers the still-uncovered `Mac.init`?" It continues exploring all MOP-marked actions equally, often re-triggering already-covered operations.

The information needed to close this gap exists — runtime coverage tracking knows WHICH methods were covered, and static analysis knows WHICH widgets reach WHICH handlers — but the link between "widget X reaches MOP method Y specifically" doesn't exist. Only "widget X reaches SOME MOP method" is known.

### P3: Meaningless Input Generation

An EditText with hint "Enter algorithm" gets filled with "test" or "hello" (by LLM guess or random generation). `Cipher.getInstance("hello")` throws `NoSuchAlgorithmException` before reaching monitored code — the MOP specification never triggers because the call fails before the monitored method completes its protocol.

This is a wasted test cycle. The agent doesn't know that this specific EditText feeds into a crypto algorithm parameter, and that valid values are algorithm names like "AES", "DES", "RSA".

### P4: No Action Ordering Awareness

Without knowing data dependencies (EditText_key feeds into Cipher.init, EditText_data feeds into Cipher.doFinal), the agent might click "Encrypt" before filling inputs. This triggers a NullPointerException or error dialog, activating error recovery (gh18's VisualErrorDetector), consuming a test cycle.

The agent already has form-context deferral in MopScorer (defers MOP button click when untested inputs exist), but this is a heuristic — it doesn't know WHICH inputs are actually required by WHICH button's MOP chain. It defers for ALL inputs on the screen, even irrelevant ones.

### P5: Redundant Path Exploration

Two navigation paths reaching the same MOP methods (e.g., Settings -> Advanced -> Encrypt and Home -> Quick Encrypt both calling the same `Cipher.getInstance -> Cipher.init -> Cipher.doFinal` chain) are explored independently. The agent has no way to know they're equivalent from a MOP coverage perspective.

In the gh26 validation (19 APKs, 3 reps), redundant exploration was observed as a significant time sink — the agent revisits screens and re-triggers operations that are already fully covered, because it can't map actions to specific MOP targets.

---

## 3. Source-Sink Analysis: Benefits for RV-Agent

**Definition**: Sources = any interactive widget (Button, EditText, Spinner, CheckBox, etc.). Sinks = any MOP method (spec-set agnostic — works for JCA, generic/FSM, or any future spec set). The analysis traces which widget interactions can reach which specific MOP methods through the call graph.

### B1: Coverage-Directed MOP Targeting

**Scenario** (using cryptoapp as example):

```
MainActivity has 3 buttons leading to activities:
  - "Cipher" button -> CipherActivity -> {Cipher.getInstance, Cipher.init, Cipher.doFinal}
  - "Digest" button -> MessageDigestActivity -> {MessageDigest.getInstance, MessageDigest.digest}
  - "Mac" button -> MacActivity -> {Mac.getInstance, Mac.init, Mac.doFinal}

Runtime coverage after 30 seconds (from LogcatRepository):
  Cipher.getInstance CONFIRMED, Cipher.init CONFIRMED, Cipher.doFinal CONFIRMED

TODAY: Agent returns to MainActivity. All 3 buttons score +300 (directMOP).
       Agent might click "Cipher" again. Wastes time.

WITH SOURCE-SINK + RUNTIME FEEDBACK:
  Agent cross-references source-sink mapping with LogcatRepository:
  - "Cipher" button -> {Cipher.getInstance, Cipher.init, Cipher.doFinal} -> ALL CONFIRMED covered
  - "Mac" button -> {Mac.getInstance, Mac.init, Mac.doFinal} -> NONE confirmed covered
  Score: Cipher button = 0 (all targets covered), Mac button = 3 * SCORE_PER_TARGET
  -> Agent clicks Mac button. Directed, not random.
```

**How it transforms the agent**: The agent maintains a real-time "coverage gap" by cross-referencing two data sources:
1. **Source-sink mapping** (static): widget X reaches MOP methods {A, B, C}
2. **LogcatRepository** (runtime): methods {A} confirmed called, {B, C} not yet

This creates a true directed search — the agent always knows the most valuable next action for increasing MOP coverage, based on **confirmed** runtime data rather than heuristic inference.

**Graceful degradation**: Without the runtime feedback channel (standalone mode), the agent falls back to inferring coverage from UI interaction history + static metadata. Less precise but still better than binary MOP flags.

**Integration points**:
- **MopScorer**: Instead of binary +300/+150, score = f(count of UNCOVERED MOP methods reachable from this widget). Queries LogcatRepository for confirmed coverage. A widget whose MOP targets are ALL confirmed covered scores 0 — freeing exploration to focus elsewhere.
- **NavigationGuidance**: "Navigate to MacActivity to cover {Mac.getInstance, Mac.init, Mac.doFinal} (0/3 confirmed covered)"
- **TransitionManager.plan_path_to_mop_activity()**: Plan path to activity with the highest number of uncovered (confirmed) MOP targets, not just "high MOP density".

### B2: Data Dependency Awareness (Action Ordering)

**Scenario**:

```
Source-sink analysis on CipherActivity reveals:
  - EditText_key (source) -> flows to -> Cipher.init(param: key) (sink)
  - EditText_data (source) -> flows to -> Cipher.doFinal(param: data) (sink)
  - Button_encrypt -> triggers the chain: encrypt() -> Cipher.init(key) -> Cipher.doFinal(data)

The source-sink paths show that:
  1. EditText_key provides data consumed by Cipher.init
  2. EditText_data provides data consumed by Cipher.doFinal
  3. Both are required before Button_encrypt's chain can complete successfully
```

**How it transforms the agent**: The agent understands that Button_encrypt has DATA DEPENDENCIES on EditText_key and EditText_data. Instead of the current heuristic form-context deferral (which defers for ALL inputs on the screen), the agent knows PRECISELY which inputs are required by which button.

This is especially valuable on screens with mixed content — some inputs feeding into MOP chains, others being decorative or unrelated (e.g., a "notes" field that doesn't affect crypto operations). Today, the agent defers the MOP button until ALL inputs are filled. With source-sink, it defers only until the REQUIRED inputs are filled.

**Integration points**:
- **MopScorer**: Replace generic form-context deferral with source-sink-informed dependency check: "defer Button_encrypt only if EditText_key or EditText_data are unfilled"
- **LLM prompt enrichment**: "Button_encrypt requires: EditText_key (key for Cipher.init), EditText_data (data for Cipher.doFinal)"
- **Action ordering in algorithm mode**: Fill source widgets first, then click sink-triggering widgets

### B3: Deduplication / Redundancy Detection

**Scenario**:

```
Source-sink analysis across the app reveals:
  - Activity A, Button_encrypt -> {Cipher.getInstance, Cipher.init, Cipher.doFinal}
  - Activity B, Button_quick_encrypt -> {Cipher.getInstance, Cipher.init, Cipher.doFinal}

Both reach the EXACT SAME set of MOP methods.

After exploring Activity A, LogcatRepository confirms:
  Cipher.getInstance CALLED, Cipher.init CALLED, Cipher.doFinal CALLED

Agent cross-references: Activity B's MOP target set is FULLY COVERED (confirmed).
  Deprioritizes Activity B — exploring it would be redundant.
```

**How it transforms the agent**: Two complementary deduplication mechanisms:

1. **Static equivalence** (no runtime data needed): Two widgets reaching the exact same MOP target set are statically redundant. Once one is tested, the other is deprioritized regardless of runtime confirmation. This is purely a source-sink comparison.

2. **Runtime-confirmed deduplication** (with feedback channel): Even if two widgets have OVERLAPPING (not identical) MOP target sets, the agent can compute the incremental value of testing the second one. If Widget A reaches {Cipher.getInstance, Cipher.init} and Widget B reaches {Cipher.getInstance, Mac.init}, and runtime confirms Cipher.getInstance is covered, then Widget B's incremental value is only {Mac.init} — the Cipher.getInstance target is confirmed redundant.

**Integration points**:
- **SuccessorTracker**: Compute "MOP novelty score" = count of MOP methods reachable from this widget that are NOT yet confirmed covered in LogcatRepository. States with zero novelty are deprioritized.
- **WtgScorer**: In addition to "is this screen unvisited?", add "does this screen have uncovered MOP targets?" — a visited screen with uncovered MOP methods is more valuable than an unvisited screen with no MOP methods or only covered ones.

### B4: Widget-MOP Mapping for Enriched LLM Prompts

**Current prompt** (what the LLM sees today):

```
[12] [UNTESTED] [DM] CLICK "Encrypt" button
[13] [TESTED-1x] [M] CLICK "Settings" button
[14] [UNTESTED] INPUT "Algorithm" field
```

**Enhanced prompt** (with source-sink data):

```
[12] [UNTESTED] [DM:Cipher.getInstance,Cipher.init,Cipher.doFinal] CLICK "Encrypt" button
     Requires: [14] Algorithm field, [15] Key field
[13] [TESTED-1x] [M:Cipher.init via SettingsHelper] CLICK "Settings" button
[14] [UNTESTED] INPUT "Algorithm" field -> feeds into Cipher.getInstance(algorithm)
```

**How it transforms the agent**: The LLM receives semantic understanding of what each action does. Instead of treating `[DM]` as an opaque priority marker, the LLM knows that clicking "Encrypt" triggers a specific chain of crypto operations, and that certain inputs are prerequisites.

This is especially impactful in multimode (70% LLM / 30% algorithm), where the LLM's decision quality directly affects exploration efficiency. A semantically-informed LLM can make decisions that the algorithm scorer cannot — for example, recognizing that testing different algorithm values (AES, DES, RSA) via the Algorithm field would increase MOP coverage by triggering different code paths.

---

## 4. Widget -> Method + Params: Benefits for RV-Agent

**Definition**: For each widget event, export the full call chain from handler to MOP sink, with statically-determined parameter values (string constants, enum values, resource references).

### B5: Intelligent Input Generation

**Scenario** (using cryptoapp):

```
Full call chain analysis reveals:
  - EditText_algorithm -> CipherActivity.onEncryptClick() ->
    CipherHelper.encrypt(algorithm) -> Cipher.getInstance(algorithm)
    Parameter: "algorithm" is a String flowing from EditText to Cipher.getInstance(param1)

  - Spinner_mode has static entries: ["AES/CBC/PKCS5Padding", "AES/ECB/NoPadding"]
    Selected value flows to: Cipher.getInstance(transformation)

TODAY: Agent fills EditText_algorithm with "hello" or "test123".
       Cipher.getInstance("hello") throws NoSuchAlgorithmException.
       MOP spec never triggers. Wasted cycle.

WITH PARAMS: Agent knows this input feeds into Cipher.getInstance(algorithm).
       Types "AES" or "DES" — valid algorithm names.
       Cipher.getInstance("AES") succeeds. MOP spec triggers and monitors.
```

**How it transforms the agent**: Input generation becomes MOP-context-aware. The agent doesn't need to guess — it knows the semantic type of each input (algorithm name, key size, provider name, etc.) because it can trace the data flow from the input widget to the MOP method parameter.

For Spinners with static entries (extracted from XML by gh27), the agent can systematically enumerate all valid values rather than randomly selecting. Each value potentially exercises a different code path through the MOP specification.

**Integration points**:
- **New input strategy**: "MOP-aware input generation" — when an input widget is a source in a source-sink path to a MOP method, generate values appropriate for the parameter type at the sink
- **Spinner systematic testing**: For Spinners with entries, cycle through all values to maximize code path coverage
- **LLM prompt**: "This input feeds into Cipher.getInstance — provide a valid Java crypto algorithm name"
- **Combined with gh27's widget.inputType**: If `inputType=numberPassword` and the sink is `KeyGenerator.init(keySize)`, the agent knows to type numeric key sizes (128, 256, etc.)

### B6: Violation-Seeking Behavior

**Scenario**:

```
Full chain + params reveals:
  - Button_encrypt -> CipherHelper.encrypt() ->
    Cipher.getInstance("AES/ECB/NoPadding") [constant from source code]
  - The string "AES/ECB/NoPadding" is statically visible as a StringConstant

  Or alternatively:
  - Spinner has entries: ["AES/CBC/PKCS5Padding", "AES/ECB/NoPadding"]
  - Agent can see BOTH values and reason about which is more likely to trigger a violation

Agent reasoning: "ECB mode is known to be insecure for multi-block encryption.
The NoPadding option combined with ECB may trigger a MOP violation related to
insecure cipher mode. I should SELECT 'AES/ECB/NoPadding' to test the MOP spec."
```

**How it transforms the agent**: The agent evolves from a random explorer to a TARGETED TESTER. With knowledge of the actual parameter values at MOP call sites, it can deliberately choose inputs that stress MOP specifications. This is a qualitative leap — the agent is not just trying to reach MOP methods, but trying to trigger specific MOP VIOLATIONS.

This is particularly powerful for JCA specs, where violations are triggered by specific algorithm/mode/padding combinations:
- `Cipher.getInstance("DES")` — weak algorithm violation
- `Cipher.init(ENCRYPT_MODE, key)` with insufficient key size — weak key violation
- `MessageDigest.getInstance("MD5")` — weak hash violation
- `SecureRandom` without explicit seeding — predictable randomness violation

**Integration points**:
- **New decision mode**: "violation-seeking" — when the agent has parameter visibility, it can deliberately select inputs most likely to trigger MOP violations
- **LLM reasoning**: The LLM can be prompted with spec-specific knowledge: "The CipherUsesECBMode spec flags ECB as insecure. This Spinner offers ECB as an option. Select it to test violation detection."
- **Cross-reference with MOP spec rules**: If the `.mop` specification defines the violation condition (e.g., "after Cipher.getInstance(transformation): if transformation contains 'ECB' then flag violation"), the agent could match parameter values against known violation triggers

### B7: Test Recipe Generation

**Scenario**:

```
Screen analysis with full call chains for CipherActivity:

Widgets:
  - EditText_password (hint: "Password")
    -> flows to KeyGenerator.init(SecureRandom(password.getBytes()))
  - Spinner_algorithm (entries: ["AES", "DES", "3DES"])
    -> flows to Cipher.getInstance(algorithm)
  - Spinner_mode (entries: ["CBC", "ECB", "GCM"])
    -> flows to Cipher.getInstance(algorithm + "/" + mode + "/PKCS5Padding")
  - Button_encrypt
    -> triggers: KeyGenerator.init -> Cipher.getInstance -> Cipher.init -> Cipher.doFinal

Generated test recipes:
  Recipe 1: password="testKey", algorithm="AES", mode="CBC" -> Encrypt
  Recipe 2: password="testKey", algorithm="AES", mode="ECB" -> Encrypt  [violation candidate]
  Recipe 3: password="testKey", algorithm="DES", mode="CBC" -> Encrypt  [weak algo candidate]
  Recipe 4: password="testKey", algorithm="DES", mode="ECB" -> Encrypt  [double violation]
  ...

Agent systematically executes each recipe, tracking which MOP events trigger.
```

**How it transforms the agent**: Instead of trial-and-error exploration, the agent generates a complete "test plan" for each screen based on the combinatorial space of input values x MOP call sites. Each recipe is a targeted test case designed to exercise a specific combination of MOP parameters.

This is fundamentally different from the current approach where the agent:
1. Explores a screen (fills random inputs, clicks buttons)
2. Observes what happens (coverage logs, error detection)
3. Learns incrementally (visit counts, success rates)

With test recipes, the agent:
1. Analyzes the screen statically (call chains, parameters, valid values)
2. Generates targeted recipes (each designed to cover specific MOP targets)
3. Executes recipes systematically (ordered by expected coverage gain)
4. Moves on when all recipes are exhausted (no redundant exploration)

**Integration points**:
- **New "recipe generation" phase**: After parsing a screen, before choosing an action, generate recipes from source-sink + params data
- **Recipe prioritization**: Order recipes by: (1) number of uncovered MOP methods targeted, (2) violation potential, (3) parameter novelty
- **Recipe tracking**: Mark recipes as executed/skipped, integrate with coverage tracking
- **Spinner enumeration**: For each Spinner with static entries, generate one recipe per entry value

### B8: Call Chain for Post-Execution Analysis

When a MOP violation occurs at runtime (logged via RVSEC logcat), having the full static call chain enables:

1. **Violation attribution**: Map the runtime violation (stack trace) back to the specific widget interaction that triggered it — "this violation was caused by clicking Button_encrypt after selecting ECB mode from the Spinner"

2. **Call chain comparison**: Compare the static call chain (predicted) with the runtime stack trace (actual) to validate the static analysis accuracy and identify cases where dynamic dispatch diverged from the static prediction

3. **Reporting enrichment**: Generate richer experiment reports: instead of "Cipher violation detected at line 42", report "Cipher ECB mode violation triggered by user action: select 'ECB' in mode Spinner -> click Encrypt -> Cipher.getInstance('AES/ECB/NoPadding') -> violation at init()"

---

## 5. Combined Value: The "Testing Intelligence" Leap

Individually, each analysis improves specific aspects. Combined, they create something qualitatively different — a **testing intelligence** where the agent understands not just WHAT to click, but WHY, HOW, and WITH WHAT VALUES.

### Before vs. After Comparison

```
CURRENT (gh26/gh27 — boolean MOP flags):
  Agent on CipherActivity. Sees:
    [12] [UNTESTED] [DM] CLICK "Encrypt" button        (+300)
    [13] [UNTESTED] [DM] INPUT "Algorithm" field        (+300)
    [14] [UNTESTED] [M]  INPUT "Key" field              (+150)

  Agent action: Fills "Algorithm" with "asdf". Fills "Key" with "test".
  Clicks "Encrypt". Cipher.getInstance("asdf") throws exception.
  Error recovery activates. Wasted cycle.
  Next: tries again with different random text. Maybe succeeds after 3-4 attempts.

  -> Effective MOP coverage gain: slow, random, wasteful

WITH SOURCE-SINK + WIDGET->METHOD+PARAMS:
  Agent on CipherActivity. Sees:
    [12] [UNTESTED] CLICK "Encrypt" button
         -> triggers: Cipher.getInstance(algo), Cipher.init(key), Cipher.doFinal(data)
         -> requires: [13] Algorithm, [14] Key
    [13] [UNTESTED] INPUT "Algorithm" field
         -> feeds into: Cipher.getInstance(param1: algorithm name)
    [14] [UNTESTED] INPUT "Key" field
         -> feeds into: Cipher.init(param2: encryption key)

  Agent action:
    1. Fill "Algorithm" with "AES" (knows it's an algorithm name parameter)
    2. Fill "Key" with "secretkey123" (knows it's an encryption key)
    3. Click "Encrypt"
    4. Cipher chain executes. LogcatRepository confirms: 3 MOP methods covered.
  Next: queries LogcatRepository for coverage gaps.
        MessageDigest.getInstance NOT in confirmed coverage -> navigate to DigestActivity.

  -> Effective MOP coverage gain: fast, directed, efficient
  (Coverage confirmation via LogcatRepository — not inference, actual runtime data)
```

### Impact Matrix: All Agent Components

| Component | Current Behavior | With Source-Sink + Params |
|---|---|---|
| **MopScorer** | Binary: +300 (DM) or +150 (M) | Dynamic: f(uncovered MOP methods reachable, confirmed via LogcatRepository) |
| **WtgScorer** | +250 for unvisited screen | +bonus for screens with uncovered MOP targets |
| **ScreenProcessor** | "[DM] CLICK button" | "[DM:Cipher.init,doFinal] CLICK (needs: key, data)" |
| **NavigationGuidance** | "Navigate to high-MOP screen" | "Navigate to MacActivity for {Mac.init} (uncovered)" |
| **TransitionManager** | Path to MOP-density activity | Path to specific uncovered MOP target |
| **Input generation** | Random / LLM-guessed values | MOP-context-aware: algorithm names, key sizes |
| **Form deferral** | Defer button until ALL inputs filled | Defer until REQUIRED inputs filled (source-sink) |
| **Exploration strategy** | DFS with MOP priority heuristic | Coverage-gap-directed DFS with confirmed MOP novelty |
| **LLM prompts** | Boolean [M]/[DM] markers | Semantic descriptions with call chains + params |
| **Redundancy** | Re-explores same MOP paths | Detects MOP-equivalent paths, skips duplicates |
| **Test generation** | Trial and error | Systematic test recipes from parameter space |
| **Violation seeking** | Random (occasional hits) | Targeted: selects values likely to violate specs |

### Estimated Quantitative Impact

Based on gh26 validation data (19 APKs x 2 tools x 3 reps):
- Current MOP coverage: ~12-16% (RVAgent comparable to APE)
- Current method coverage: ~16-18%

Main coverage bottlenecks observed:
1. Agent can't differentiate between widgets that reach different MOP targets (-> B1)
2. Input values are meaningless for crypto operations (-> B5)
3. Agent re-explores paths to the same MOP targets without knowing they're equivalent (-> B3)
4. Premature button clicks trigger errors due to missing input dependencies (-> B2)

Conservative estimate with source-sink + params + runtime feedback:
- MOP coverage: 25-40% (2-3x improvement)
- Method coverage: 20-25% (modest improvement — most methods aren't MOP-related)
- Test efficiency: 2-4x fewer wasted cycles (meaningful inputs, action ordering, deduplication, confirmed coverage targeting)

The runtime feedback channel (Section 6.3) is critical for the higher end of these estimates. Without it, the agent infers coverage from UI interactions + static metadata, which is less precise but still a significant improvement over binary MOP flags.

---

## 6. Technical Feasibility Assessment

### 6.1 What Already Exists After gh27

The gh27 unified static analysis change provides the foundation infrastructure:

| Component | Status | Details |
|---|---|---|
| JGraphT call graph | Built | `DefaultDirectedGraph<SootMethod, DefaultEdge>` from Soot CHA |
| Reverse graph | Built | `EdgeReversedGraph` for backward traversal |
| Multi-source BFS | Built | Forward + backward BFS on JGraphT |
| MOP method resolution | Built | Class + method name matching, all overloads |
| Widget -> handler mapping | Built | `output.getAllEventsAndTheirHandlers(guiObject)` |
| Handler -> SootMethod | Built | Handler signature resolved to SootMethod via `Scene.v()` |
| Widget entries/inputType | Built | Extracted from decoded APK layout XMLs |
| Soot Scene | Available | Full Soot scene with all application classes and methods |

**Key insight**: The call graph, MOP resolution, and widget-handler mapping already exist in gh27. The proposed analyses are extensions of existing infrastructure, not new systems.

### 6.2 What Would Need to Be Built

#### Java Side (RvsecAnalysisClient extension)

**1. Source-sink path extraction**:
- BFS from each handler SootMethod, following call graph edges
- Stop when reaching a MOP method (already identified by gh27's MOP resolution)
- Record the path: [handler -> intermediate1 -> intermediate2 -> MOP_method]
- Complexity: O(handlers x (V + E)) — manageable for app-level graphs
- Already have: handler methods (from widget events), MOP methods (from resolution), call graph (JGraphT)
- Need: path recording BFS (instead of boolean-only BFS)

**2. Parameter value extraction at MOP call sites**:
- At each call site where a MOP method is invoked, inspect the arguments
- For `StringConstant` arguments (Soot intra-procedural): extract the string value directly
- For arguments flowing from widget inputs (inter-procedural): mark as "dynamic from widget X"
- Soot provides: `Stmt.getInvokeExpr().getArg(i)` to access each argument
- `StringConstant` is the simplest case — covers ~80% of crypto algorithm/provider parameters
- `IntConstant` covers key sizes (e.g., `KeyGenerator.init(256)`)
- More complex flows (concatenation, method returns) would require inter-procedural analysis

**3. JSON output extension**:
- New section `sourceSinkPaths` in analysis JSON:

```json
{
  "sourceSinkPaths": [
    {
      "sourceWidgetId": 2131165268,
      "sourceWidgetName": "button_encrypt",
      "sourceEventType": "click",
      "sinkMethod": "<javax.crypto.Cipher: javax.crypto.Cipher getInstance(java.lang.String)>",
      "callChain": [
        "<com.app.CipherActivity: void onEncryptClick(android.view.View)>",
        "<com.app.CipherHelper: byte[] encrypt(java.lang.String)>",
        "<javax.crypto.Cipher: javax.crypto.Cipher getInstance(java.lang.String)>"
      ],
      "sinkParams": {
        "0": {
          "type": "dynamic",
          "sourceWidgetId": 2131165270,
          "sourceWidgetName": "edittext_algorithm"
        }
      }
    },
    {
      "sourceWidgetId": 2131165270,
      "sourceWidgetName": "edittext_algorithm",
      "sourceEventType": "input",
      "sinkMethod": "<javax.crypto.Cipher: javax.crypto.Cipher getInstance(java.lang.String)>",
      "callChain": ["..."],
      "sinkParams": {
        "0": {
          "type": "input_value",
          "description": "algorithm name for Cipher.getInstance"
        }
      }
    }
  ]
}
```

#### Python Side (StaticAnalysisParser + rv-agent)

**1. Parse source-sink data**: Extend `StaticAnalysisData` with:

```python
@dataclass
class SourceSinkPath:
    source_widget_id: str
    source_widget_name: str
    source_event_type: str
    sink_method: str              # Full Soot signature of the MOP method
    call_chain: List[str]         # Ordered method signatures from handler to MOP
    sink_params: Dict[int, ParamInfo]  # Position -> value/source info

@dataclass
class ParamInfo:
    type: str                     # "constant", "dynamic", "input_value"
    value: Optional[str]          # For constants: the actual string value
    source_widget_id: Optional[str]  # For dynamic: which widget provides the value
```

**2. RVAgentVisitor enrichment**: Extend action enrichment to attach:
- `action.mop_targets: List[str]` — specific MOP methods this widget reaches
- `action.call_chains: List[SourceSinkPath]` — full path details
- `action.required_inputs: List[str]` — widget IDs that must be filled first

**3. MopScorer enhancement**: Replace binary scoring with coverage-gap-aware:

```python
def score(action, coverage_repository):
    if coverage_repository:
        # Runtime feedback available: use confirmed coverage from LogcatRepository
        covered = {sig for cls in coverage_repository.classes.values()
                   for sig, m in cls.methods.items() if m.called and m.reaches_target}
        uncovered_mop = action.mop_targets - covered
    else:
        # Standalone mode: fall back to UI interaction-based inference
        uncovered_mop = action.mop_targets - self.inferred_targeted_methods
    return len(uncovered_mop) * MOP_SCORE_PER_UNCOVERED_TARGET
```

**4. Input strategy**: MOP-context-aware value generation for algorithm names, key sizes, etc.

**5. Prompt enrichment**: Semantic action descriptions with call chain summaries for LLM.

### 6.3 Runtime Feedback Channel: LogcatRepository Injection

Today the agent has no access to confirmed runtime coverage. However, injecting this data is architecturally straightforward because the infrastructure already exists — it just isn't connected.

#### Current Data Flow (No Feedback)

```
TaskExecutor._execute_coordinated_components()
  → CoverageComponent creates CoverageTracker (with LogcatRepository)
  → CoverageComponent.start_tracking()        # Background thread starts
  → ToolExecutionComponent.execute()           # Runs RVAgentTool
    → RVAgentTool gets static_data from task
    → AgentFactory.create_agent(config, static_data)  ← NO coverage data
    → agent.run()                              # Agent runs WITHOUT runtime feedback
  → CoverageComponent.stop_tracking()          # Background thread stops
```

During the agent's execution, the `CoverageTracker` background thread is continuously populating the `LogcatRepository` with confirmed method executions parsed from logcat RVSEC-COV lines. This data is available in real-time — it's just not passed to the agent.

#### Proposed Data Flow (With Feedback)

```
TaskExecutor._execute_coordinated_components()
  → CoverageComponent creates CoverageTracker (with LogcatRepository)
  → CoverageComponent.start_tracking()
  → task.coverage_repository = coverage_tracker.repository  ← NEW: store reference
  → ToolExecutionComponent.execute()
    → RVAgentTool gets static_data AND coverage_repository from task
    → AgentFactory.create_agent(config, static_data, coverage_repository=repository)
    → agent.run()   # Agent can now query LogcatRepository during execution
  → CoverageComponent.stop_tracking()
```

#### Why This Works

**1. No circular dependency**: `LogcatRepository` is defined in `rv-android-core` (`rv_android_core.domain.coverage`), which is already a dependency of both `rv-agent` and `rv-coverage`. Passing a `LogcatRepository` reference to the agent introduces NO new module dependency.

**2. Same injection pattern**: `StaticAnalysisData` is already stored on the task object by `StaticAnalysisComponent` and read by `RVAgentTool`. The exact same pattern applies:

```python
# In CoverageComponent.start_tracking() — NEW
self.task.coverage_repository = self.coverage_tracker.repository

# In RVAgentTool.execute_tool_specific_logic() — NEW
coverage_repository = getattr(task, 'coverage_repository', None)

# In AgentFactory.create_agent() — EXTENDED
agent = AgentFactory.create_agent(
    config=agent_config,
    static_data=static_data,
    coverage_repository=coverage_repository  # NEW optional param
)
```

**3. AgentFactory already supports optional dependencies**: The factory method signature already uses `static_data: Optional[StaticAnalysisData] = None`. Adding `coverage_repository: Optional[LogcatRepository] = None` follows the same pattern. Components that receive it use it; components that don't get `None` degrade gracefully.

**4. Standalone mode degrades gracefully**: When running via `rv-agent run` (standalone CLI), no `CoverageComponent` exists, so `coverage_repository=None`. The agent falls back to inferring MOP coverage from UI interaction history + static metadata (the behavior described in the original version of this document). When running via rv-platform, both are always present.

#### What the Agent Would Query

The `LogcatRepository` provides exactly the data the agent needs:

```python
# Query: "Which MOP methods have been CONFIRMED executed at runtime?"
confirmed_mop_coverage = set()
for class_data in coverage_repository.classes.values():
    for signature, method in class_data.methods.items():
        if method.called and method.reaches_target:
            confirmed_mop_coverage.add(signature)

# Query: "What's the current MOP coverage percentage?"
metrics = coverage_repository.calculate_metrics()
# metrics.called_target_methods, metrics.total_target_methods, etc.

# Query: "Has this specific MOP method been executed?"
class_data = coverage_repository.get_class("javax.crypto.Cipher")
if class_data:
    method = class_data.methods.get("<javax.crypto.Cipher: ...getInstance...>")
    if method and method.called:
        # Confirmed: this MOP method was actually executed at runtime
```

#### Thread Safety

The `CoverageTracker` writes to `LogcatRepository` from a background thread while the agent reads from the main thread. Thread safety considerations:

- **Python's GIL** protects basic attribute reads (`method.called`, `method.call_count`). The worst case is a slightly stale read (missing the last 0.5-1s of updates), which is perfectly acceptable for heuristic scoring.
- **No structural mutations during reads**: The `LogcatRepository.classes` dict is populated during initialization from static analysis data. The background thread only UPDATES existing `MethodCoverageData` objects (sets `called=True`, increments `call_count`). It does NOT add/remove entries. This means the agent iterating over `classes.values()` will never encounter a concurrent structural modification.
- **Acceptable staleness**: The agent doesn't need microsecond-accurate data. Knowing "as of ~1 second ago, these MOP methods were confirmed called" is sufficient for action prioritization. The background thread updates every 0.5-1.0 seconds.

If more robust safety is desired, a simple `get_confirmed_mop_signatures() -> Set[str]` method with a `threading.Lock` could be added to `LogcatRepository`. But given the GIL protection and the read-only nature of the agent's queries, this is likely unnecessary.

#### The Dual Condition

The full value of source-sink analysis requires **both** data sources:

| static_data | coverage_repository | Agent capability |
|---|---|---|
| None | None | Standalone: UI-only exploration, no MOP awareness |
| Present | None | Current gh27: boolean MOP flags, inferred coverage |
| None | Present | Limited value: knows what methods were called but can't map them to widgets |
| **Present** | **Present** | **Full integration**: source-sink mapping + confirmed runtime coverage = coverage-directed targeting |

The "both present" condition is always satisfied when running via rv-platform (the production execution path). The standalone CLI mode is primarily for development/debugging and naturally has reduced capabilities.

### 6.4 Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| **CHA over-approximation** (false source-sink paths) | Medium | High | Filter: only app-level methods in chain, max depth limit, prune Android framework internals. Accept some false positives — runtime verification catches the rest. |
| **Dynamic dispatch** (callbacks registered at runtime) | Medium | Medium | Acceptable limitation — static analysis is always an approximation. Runtime behavior fills the gap. Document as known limitation. |
| **Data size explosion** (long call chains, many paths) | Medium | Medium | Only store paths to MOP sinks. Limit chain depth (e.g., max 10 methods). Compress shared prefixes. Top-K paths per widget. |
| **LLM context overload** (too much info per action) | Low-Medium | Medium | Summarize: show only MOP target names + required inputs. Full chains available but not in every prompt. Structured format, not prose. |
| **Intra-procedural constant limitation** (~20% params not extractable) | Low | High | Accept gracefully: mark as "dynamic" or "unknown". Even 80% constant extraction is a massive improvement over 0% today. |
| **Soot performance** for path extraction | Low | Low | BFS is O(V+E) per source. Total: O(handlers x (V+E)). For typical apps (100-500 handlers, 10K-50K edges), this is seconds, not minutes. |

---

## 7. Thesis Contribution Positioning

### 7.1 Novel Contributions

**C1: First integration of source-sink analysis with LLM-driven Android testing**

No prior work combines static data-flow analysis from widget interactions to monitored API methods with an LLM agent for runtime verification testing. Existing approaches:
- FlowDroid (Arzt et al., 2014): Source-sink for privacy leak detection — we adapt the concept for MOP-targeted testing
- CryptoGuard/CogniCrypt: Static-only crypto misuse detection — we combine static analysis with dynamic testing
- Neither uses source-sink to GUIDE a testing agent

**C2: Coverage-directed exploration via static-runtime feedback loop**

Using runtime coverage data (from LogcatRepository, fed back to the agent via dependency injection) cross-referenced with static widget-MOP mappings (from source-sink analysis) to dynamically redirect exploration in real-time. This is a novel feedback mechanism:
- Android testing tools (Monkey, DroidBot, APE) are either coverage-unaware (Monkey) or structurally-aware only (DroidBot/APE use code coverage but not spec-specific MOP coverage)
- No existing tool uses MOP-spec-specific coverage to guide widget interaction decisions
- The feedback loop is: static analysis (which widget reaches which MOP methods) + confirmed runtime coverage (which MOP methods actually executed, from LogcatRepository) -> compute coverage gaps -> prioritize widgets targeting uncovered MOP methods
- Graceful degradation: without the runtime channel (standalone mode), falls back to UI interaction-based inference

**C3: Semantic action understanding for LLM agents**

Enriching UI action descriptions with call chain semantics and parameter types gives the LLM agent qualitatively richer context than any existing approach. Current LLM-for-testing approaches (GPT-Droid, AXNav, etc.) use only UI tree information (element text, type, position). None provide call chain or parameter semantics.

**C4: Quantifiable improvement measurable against established baseline**

Direct A/B comparison with gh26 baseline (19 APKs, 3 reps, controlled experiment) would demonstrate the value of deeper static analysis in a reproducible setting. The experimental infrastructure already exists.

### 7.2 Related Work Positioning

| Work | What it does | How we differ |
|---|---|---|
| **FlowDroid** (Arzt et al.) | Source-sink for privacy leaks | We target MOP-monitored API methods, not privacy sources/sinks |
| **CryptoGuard** (Rahaman et al.) | Static-only crypto misuse detection | We combine static + dynamic (runtime verification) |
| **CogniCrypt** (Kruger et al.) | CrySL-based static misuse detection | We use MOP specs (more general) and add runtime testing |
| **APE** (Gu et al.) | Model-based exploration with abstraction | No static analysis, no spec-aware targeting |
| **Humanoid** (Li et al.) | DNN-guided exploration | UI-only context, no call chain semantics |
| **DroidBot** (Li et al.) | Depth-first exploration with instrumentation | General code coverage, not MOP-spec-specific |
| **GPT-Droid** (Liu et al.) | LLM-guided Android testing | UI tree only, no static analysis integration |

The unique position: **we are the first to combine source-sink static analysis with an LLM-driven agent for runtime verification testing of Android applications**. This is at the intersection of three research areas (program analysis, LLM agents, runtime verification) where no prior work exists.

### 7.3 DSR Cycle Alignment

In the DSR methodology (4 cycles):
- **Cycle 1** (MOP specs): Completed — 23 JCA specs from CrySL rules
- **Cycle 2** (Instrumentation + basic testing): Completed — rv-instrumentation + Monkey/DroidBot
- **Cycle 3** (LLM-driven testing): In progress — rv-agent with boolean MOP flags
- **Cycle 4** (Advanced static-dynamic integration): This would be cycle 4 — source-sink + params enabling coverage-directed, violation-seeking testing

Source-sink + widget-method+params would constitute the Cycle 4 artifact, demonstrating the full potential of integrating deep static analysis with LLM-driven runtime verification testing.

---

## 8. Recommended Next Steps

If this analysis is convincing, the path forward would be:

### Step 1: Runtime feedback channel (Small change, high leverage)
Inject `LogcatRepository` reference into rv-agent via the existing dependency injection pattern (Section 6.3). This is a small change (~20 lines across 3 files: `CoverageComponent`, `RVAgentTool`, `AgentFactory`) but enables all runtime-confirmed coverage features. Should be done BEFORE source-sink integration, since it's a prerequisite for the full coverage-directed targeting value.

Key files:
- `modules/rv-platform/src/rv_platform/components/coverage.py` — store repository on task
- `modules/rv-agent/src/rv_agent/tools/rvagent/tool.py` — read repository from task, pass to factory
- `modules/rv-agent/src/rv_agent/agent/agent_factory.py` — accept and distribute `coverage_repository`

### Step 2: Spike on cryptoapp (Low effort, high learning)
Extend `RvsecAnalysisClient` (from gh27) to output source-sink paths for cryptoapp. Validate:
- Expected: 4-5 distinct source-sink paths (buttons -> JCA methods)
- Expected parameters: "AES", "SHA-256", "HmacSHA256", "RSA" as string constants
- Measure: how many params are statically extractable vs. dynamic

### Step 3: Design rv-agent integration (gh28/gh29)
Full OpenSpec change: how source-sink + params data flows from analysis JSON through StaticAnalysisData into MopScorer, NavigationGuidance, LLM prompts, and input generation. Includes integration with LogcatRepository for confirmed coverage targeting.

### Step 4: Prototype integration
Implement the rv-agent changes (scoring, prompts, input generation) using the enriched static analysis data + runtime feedback.

### Step 5: Controlled experiment
Run same 19-APK experiment as gh26 validation, comparing:
- Baseline: gh27 agent (boolean MOP flags, no runtime feedback)
- Treatment A: gh27 agent + runtime feedback only (isolate feedback channel value)
- Treatment B: source-sink + params + runtime feedback (full integration)
- Metrics: MOP coverage %, method coverage %, time-to-coverage, violation detection rate
