# Deep Analysis: Source-Sink + Widget-Method Mapping for RV-Agent

**Date**: 2026-02-24
**Author**: Pedro Henrique Teixeira Costa
**Status**: Research / Brainstorming
**Related**: gh27 (unified static analysis), rv-agent exploration strategy (gh26)

## Context

RV-Agent currently uses boolean MOP flags (`reaches_mop`, `directly_reaches_mop`) from static analysis to prioritize UI actions during exploration. After gh27 (unified static analysis), the JGraphT call graph and MOP resolution infrastructure exist in the Java client but only boolean flags are exported. Two proposed analyses could dramatically improve agent decision-making:

1. **Source-sink analysis**: Map which interactive widgets (sources) can trigger which MOP methods (sinks)
2. **Widget -> method + params**: Full call chain from handler to MOP sink, with statically-determined parameter values

This document analyzes how these would benefit rv-agent. This is a research/brainstorming exercise to evaluate the value proposition — not an implementation plan.

### Important Architectural Constraint: No Runtime MOP Feedback

RV-Agent does **NOT** have access to real-time MOP method coverage during execution. The coverage data flow is:

- **CoverageTracker** (rv-platform, background thread): Monitors logcat RVSEC-COV lines in real-time, but does **NOT** feed back to the agent loop
- **LogcatRepository** (rv-coverage): Parses logcat post-execution to compute actual method/MOP coverage for reports
- **RV-Agent's CoverageMetrics**: Tracks `mop_methods_reached` based on **static callback signatures** — what the agent BELIEVES it triggered based on UI interactions + static analysis metadata, not runtime confirmation

This means:
- The agent knows "I clicked a button whose handler statically reaches Cipher.getInstance" (UI-level tracking + static metadata)
- The agent does NOT know "Cipher.getInstance was actually executed at runtime" (requires logcat parsing unavailable during execution)
- Benefits in this document that reference "coverage-directed targeting" operate on **inferred coverage** (static metadata + UI interaction history), not on confirmed runtime coverage. This is explicitly noted where applicable.

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
    │   ├── reaches_mop: bool
    │   └── directly_reaches_mop: bool
    └── Used by: RVAgentVisitor (MOP enrichment), TransitionManager (path planning)
```

### 1.2 MOP Enrichment at Parse Time (RVAgentVisitor)

When the agent parses the current screen's UI hierarchy, `RVAgentVisitor._enrich_action_with_mop()` performs:

1. Finds the static Widget matching the runtime UI element (by resource-id, text, or hint)
2. Looks up widget.events (callbacks) — gets handler signature
3. Resolves handler signature to `StaticAnalysisData.classes.methods`
4. Copies boolean flags (`reaches_mop`, `directly_reaches_mop`) to the ItemAction
5. Adds `[M]` or `[DM]` markers to action.text for LLM visibility

Result: each `ItemAction` has:
- `reaches_mop: bool` / `directly_reaches_mop: bool`
- `widget_id: str` (static widget ID)
- `callback_signature: str` (handler method)
- `text` with `[M]`/`[DM]` markers

### 1.3 How MOP Data Influences Decisions

| Component | How it uses MOP data | Score impact |
|---|---|---|
| **MopScorer** | `directly_reaches_mop` -> +300, `reaches_mop` -> +150 | Highest single scorer |
| **WtgScorer** | Checks if action leads to unvisited screen | +250 for WTG-guided transition |
| **ScreenProcessor** | Adds MOP bonus to LLM action ordering | +100 (DM), +50 (M) |
| **TransitionManager** | `_calculate_target_priority()` checks widget events for MOP | +50 direct, +25 transitive |
| **Path planning** | `plan_path_to_mop_activity()` BFS to high MOP-density activities | Navigation targeting |

### 1.4 Widget Information Available Today

```python
# What the agent knows about each widget/action:
widget_id: str                    # Static widget ID from GATOR
reaches_mop: bool                 # Boolean: transitively reaches MOP
directly_reaches_mop: bool        # Boolean: directly calls MOP
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

### B1: MOP-Specific Targeting (Differentiated Scoring)

**Scenario** (using cryptoapp as example):

```
MainActivity has 3 buttons leading to activities:
  - "Cipher" button -> CipherActivity -> {Cipher.getInstance, Cipher.init, Cipher.doFinal}
  - "Digest" button -> MessageDigestActivity -> {MessageDigest.getInstance, MessageDigest.digest}
  - "Mac" button -> MacActivity -> {Mac.getInstance, Mac.init, Mac.doFinal}

TODAY: Agent returns to MainActivity. All 3 buttons score +300 (directMOP).
       Agent has clicked "Cipher" 5 times. "Mac" 0 times.
       Visit count deprioritizes Cipher, but scoring is still binary.
       Agent has no basis to understand that Mac reaches DIFFERENT MOP targets.

WITH SOURCE-SINK: Agent knows which SPECIFIC MOP methods each button reaches.
       MopScorer differentiates: "Cipher" button -> 3 MOP methods, "Mac" button -> 3 DIFFERENT MOP methods.
       Combined with visit counts: "Cipher" methods have been triggered (inferred from clicks).
       "Mac" methods have NEVER been triggered -> prioritize Mac button.
```

**How it transforms the agent**: Instead of treating all directMOP actions equally (+300), the agent can differentiate based on WHICH MOP methods each widget reaches. Combined with the existing UI-level tracking (visit counts per element), this creates a more informed heuristic: "I've clicked the Cipher button multiple times (its MOP targets are likely covered), but the Mac button's MOP targets are distinct and untested."

**Important caveat**: The agent does not have runtime confirmation that MOP methods were actually executed. The "coverage" here is INFERRED: "I clicked widget X which statically reaches MOP methods {A, B, C}, so A/B/C are probably covered." This is an approximation — the actual call might have failed at runtime (exception, wrong input, etc.) — but it's still far more informative than the current binary flag.

**Integration points**:
- **MopScorer**: Instead of binary +300/+150, score based on: (1) how many distinct MOP methods this widget reaches, (2) how many of those MOP methods are ALSO reachable from already-tested widgets (inferred coverage). A widget reaching 3 MOP methods that no other tested widget reaches scores higher than one reaching methods already "covered" by previous interactions.
- **NavigationGuidance**: "Navigate to MacActivity for {Mac.getInstance, Mac.init, Mac.doFinal} (untested MOP targets)"
- **TransitionManager.plan_path_to_mop_activity()**: Plan path to activity with MOP methods not yet targeted by previous interactions, not just "high MOP density".

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

Both reach the EXACT SAME set of MOP methods (possibly even the same code path,
or two different paths to the same library method).

After exploring Activity A (agent clicked Button_encrypt multiple times):
  Agent recognizes: Activity B's MOP target set is IDENTICAL to Activity A's.
  Deprioritizes Activity B in exploration queue — testing it would be redundant.
```

**How it transforms the agent**: Without source-sink, two buttons in different activities both score +300 (directMOP) and the agent has no way to know they reach the same MOP targets. With source-sink, the agent can compute "MOP target equivalence" between widgets — if two widgets across different screens reach the exact same MOP method set, testing one makes the other redundant.

This detection is purely static (comparing MOP target sets from source-sink data) — it does NOT require runtime coverage confirmation. The agent simply knows: "Button_encrypt in Activity A and Button_quick_encrypt in Activity B both reach {Cipher.getInstance, Cipher.init, Cipher.doFinal}. Once I've tested one, the other is a duplicate."

**Integration points**:
- **SuccessorTracker**: When evaluating candidate next-states, compute "MOP novelty score" = count of MOP methods reachable from that state that are NOT also reachable from already-tested widgets. States with zero novelty are deprioritized.
- **WtgScorer**: In addition to "is this screen unvisited?", add "does this screen have untested MOP targets?" — a visited screen with MOP targets not yet tested from any other widget is more valuable than an unvisited screen whose MOP targets are already covered by other tested paths.

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
    4. Cipher chain likely executes successfully. 3 MOP methods inferred as triggered.
  Next: checks which MOP target sets remain untested.
        MessageDigest targets never triggered from any widget -> navigate to DigestActivity.

  -> Effective MOP coverage gain: fast, directed, efficient
  (Note: "covered" = inferred from UI interactions + static metadata, not runtime-confirmed)
```

### Impact Matrix: All Agent Components

| Component | Current Behavior | With Source-Sink + Params |
|---|---|---|
| **MopScorer** | Binary: +300 (DM) or +150 (M) | Differentiated: f(distinct MOP methods reachable, untested target novelty) |
| **WtgScorer** | +250 for unvisited screen | +bonus for screens with uncovered MOP targets |
| **ScreenProcessor** | "[DM] CLICK button" | "[DM:Cipher.init,doFinal] CLICK (needs: key, data)" |
| **NavigationGuidance** | "Navigate to high-MOP screen" | "Navigate to MacActivity for {Mac.init} (uncovered)" |
| **TransitionManager** | Path to MOP-density activity | Path to specific uncovered MOP target |
| **Input generation** | Random / LLM-guessed values | MOP-context-aware: algorithm names, key sizes |
| **Form deferral** | Defer button until ALL inputs filled | Defer until REQUIRED inputs filled (source-sink) |
| **Exploration strategy** | DFS with MOP priority heuristic | MOP-target-aware DFS with novelty scoring |
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

Conservative estimate with source-sink + params:
- MOP coverage: 20-30% (1.5-2x improvement)
- Method coverage: 18-22% (modest improvement — most methods aren't MOP-related)
- Test efficiency: 2-3x fewer wasted cycles (meaningful inputs, action ordering, deduplication)

**Important caveat**: These estimates assume the inferred coverage model (static metadata + UI interaction tracking) is a reasonable approximation of actual runtime coverage. The agent cannot confirm actual MOP method execution — it infers coverage from "I clicked widgets that statically reach these MOP methods." If a future change adds a runtime feedback channel (e.g., CoverageTracker -> agent callback), the estimates above would improve further because the agent would know the actual coverage state.

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

**3. MopScorer enhancement**: Replace binary scoring with MOP-target-aware:

```python
def score(action, inferred_coverage):
    # inferred_coverage = MOP methods already targeted by previously-tested widgets
    # (from UI interaction history + static source-sink data, NOT runtime confirmation)
    novel_mop = action.mop_targets - inferred_coverage.targeted_mop_methods
    return len(novel_mop) * MOP_SCORE_PER_NOVEL_TARGET
```

**4. Input strategy**: MOP-context-aware value generation for algorithm names, key sizes, etc.

**5. Prompt enrichment**: Semantic action descriptions with call chain summaries for LLM.

### 6.3 Risk Assessment

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

**C2: MOP-target-aware exploration via static analysis + UI interaction history**

Using static widget-MOP mappings cross-referenced with UI interaction history to infer which MOP targets have been exercised and redirect exploration toward untested targets. This is a novel feedback mechanism:
- Android testing tools (Monkey, DroidBot, APE) are either coverage-unaware (Monkey) or structurally-aware only (DroidBot/APE use code coverage but not spec-specific MOP awareness)
- No existing tool uses MOP-spec-specific target sets to guide widget interaction decisions
- The feedback loop is: static analysis (which widget reaches which MOP methods) + UI interaction tracking (which widgets have been tested) -> infer which MOP targets remain untested -> prioritize widgets targeting novel MOP methods
- **Future enhancement**: If a runtime feedback channel is added (CoverageTracker -> agent), this loop would use confirmed MOP coverage instead of inferred coverage, making targeting even more precise

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

### Step 1: Spike on cryptoapp (Low effort, high learning)
Extend `RvsecAnalysisClient` (from gh27) to output source-sink paths for cryptoapp. Validate:
- Expected: 4-5 distinct source-sink paths (buttons -> JCA methods)
- Expected parameters: "AES", "SHA-256", "HmacSHA256", "RSA" as string constants
- Measure: how many params are statically extractable vs. dynamic

### Step 2: Design rv-agent integration (gh28/gh29)
Full OpenSpec change: how source-sink + params data flows from analysis JSON through StaticAnalysisData into MopScorer, NavigationGuidance, LLM prompts, and input generation.

### Step 3: Prototype integration
Implement the rv-agent changes (scoring, prompts, input generation) using the enriched static analysis data.

### Step 4: Evaluate runtime feedback channel (optional, high impact)
Currently rv-agent infers MOP coverage from UI interactions + static metadata. Adding a callback from `CoverageTracker` (rv-platform) to the agent would provide REAL coverage data during execution, transforming inferred targeting into confirmed targeting. This would be a separate change but would multiply the value of source-sink analysis.

### Step 5: Controlled experiment
Run same 19-APK experiment as gh26 validation, comparing:
- Baseline: gh27 agent (boolean MOP flags)
- Treatment: gh28/29 agent (source-sink + params)
- Metrics: MOP coverage %, method coverage %, time-to-coverage, violation detection rate
