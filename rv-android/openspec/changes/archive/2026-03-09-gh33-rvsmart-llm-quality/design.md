## Context

RVSmart's LLM integration has correct infrastructure (HTTP client, circuit breaker, coordinate normalizer, 3-level parser) but two fundamental problems: the SGLang URL is unreachable from the emulator in the current deployment, and the prompt contains almost no useful context. This design covers the technical decisions for fixing both problems: making the URL configurable, introducing a `PromptContext`/`PromptVersion` abstraction, implementing the ARRIVAL_FIRST routing strategy, and wiring the rich V17 context data through AgentLoop.

Primary module: `rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/` (Java).
Secondary module: `rv-android/modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py` (Python).

Reference FRs: FR21 (LLM-driven exploration), FR28 (MOP-prioritized actions), FR31 (hybrid exploration modes), NFR06 (configurability).

## Architecture

```
AgentLoop.tryLlmAction()
  │
  ├─ outOfAppCount > 0 ? → skip LLM entirely (INV-RSM-LLM-02)
  │
  ├─ RoutingManager.shouldUseLlm(hash, prevHash, outOfAppCount)
  │     └─ ARRIVAL_FIRST: hash != prevHash → true (arrival)
  │                        hash == prevHash → random < phase2Prob
  │
  ├─ PromptContext.Builder
  │     ├─ base64Screenshot (ImageProcessor)
  │     ├─ uiElements (ScreenState)
  │     ├─ currentActivity
  │     ├─ navigationHint (computed from StaticMap)
  │     ├─ visitedActivities
  │     ├─ iterationNumber
  │     ├─ [V17] elementInteractionCounts ← UICoverageTracker
  │     ├─ [V17] directMopElements        ← StaticMap
  │     ├─ [V17] indirectMopElements      ← StaticMap
  │     ├─ [V17] elementScores            ← ActionSelector.getLastScoreBreakdown()
  │     └─ [V17] recentActions            ← AgentLoop ring buffer (last 5)
  │
  ├─ PromptBuilder.build(PromptVersion, PromptContext)
  │     ├─ V13 → dialog-aware system msg + simple user msg
  │     └─ V17 → MOP-aware system msg + enriched user msg
  │
  └─ SglangClient.chat(messages) → ToolCallParser → CoordinateNormalizer → Action
```

### Key Components

| Component | Responsibility | File |
|-----------|---------------|------|
| `PromptContext` | Value object holding all context fields for any prompt version | `llm/PromptContext.java` (new) |
| `PromptVersion` | Enum (V13, V17) determining template selection | `llm/PromptVersion.java` (new) or inner enum in Config |
| `PromptBuilder` | Assembles messages list given version + context | `llm/PromptBuilder.java` (modified) |
| `RoutingManager` | shouldUseLlm() with ARRIVAL_FIRST strategy | `core/RoutingManager.java` (modified) |
| `AgentLoop.tryLlmAction()` | Builds PromptContext, calls PromptBuilder, handles result | `core/AgentLoop.java` (modified) |
| `RVSmartTool.get_variants()` | Registers new/updated Python variants | `tools/rvsmart/tool.py` (modified) |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|------------------------|----------------|------|
| INV-RSM-LLM-02 (no LLM out-of-app) | `AgentLoop.tryLlmAction()`: early return if `outOfAppCount > 0` | `AgentLoopTest.testNoLlmWhenOutOfApp()` |
| INV-RSM-LLM-03 (PromptBuilder versioning) | `PromptBuilder` constructor + `build()` dispatch | `PromptBuilderTest.testV13Structure()`, `testV17Structure()` |
| INV-RSM-LLM-04 (graceful V17 degradation) | null-checks in `buildUserMessageV17()` | `PromptBuilderTest.testV17DegradationNullContext()` |
| INV-RSM-LLM-05 (ARRIVAL_FIRST arrival signal) | `RoutingManager.shouldUseLlm(hash, prevHash, ...)` | `RoutingManagerTest.testArrivalFirstFiresOnHashChange()` |
| INV-RSM-LLM-06 (phase-2 probability) | `RoutingManager.shouldUseLlmArrivalFirst()` | `RoutingManagerTest.testArrivalFirstPhase2Probabilistic()` |
| Prompt v13 port | `PromptBuilder.buildSystemMessageV13()`, `buildUserMessageV13()` | `PromptBuilderTest.testV13DialogInstructions()` |
| Prompt v17 test-status tags | `PromptBuilder.formatElementV17()` using `elementInteractionCounts` | `PromptBuilderTest.testV17TestStatusTags()` |
| Prompt v17 MOP markers | `PromptBuilder.formatElementV17()` using `directMopElements` | `PromptBuilderTest.testV17MopMarkers()` |
| Diagnostic logging | `Log.d("RVSMART-PROMPT", ...)` in `PromptBuilder.build()` | manual logcat inspection |
| Tool variants | `RVSmartTool.get_variants()` dict | `test_rvsmart_tool.py::test_arrival_first_v17_variant()` |

## Goals / Non-Goals

**Goals:**
- Make LLM calls actually reachable (URL fix)
- Make LLM prompt informative (v13 and v17 port)
- Add ARRIVAL_FIRST strategy to RoutingManager
- Wire rich context data to PromptBuilder for V17
- Guard LLM against out-of-app invocation
- Enable diagnostic observation (logging)
- Add `llm_only`, `arrival_first_v13`, `arrival_first_v17` variants

**Non-Goals:**
- Porting RVAgent v14, v15, v16 prompts (not needed; v13 and v17 are sufficient)
- Latency timeout tuning (requires measurement data from post-implementation testing)
- Calibrating `llm_new_screen_phase2_probability` (0.30 is a starting point; Optuna calibration is a separate effort)
- Changes to SglangClient, ImageProcessor, ToolCallParser, CoordinateNormalizer (correct as-is)

## Decisions

**Decision 1: PromptContext as plain value object, not builder pattern**

The context has ~12 fields across two versions. A Java builder pattern would add boilerplate for marginal benefit. The simpler design is a single `PromptContext` class with a static inner `Builder` used only in `AgentLoop.tryLlmAction()`. All V17-only fields are nullable and wrapped in null-checks inside `PromptBuilder`. This avoids creating two separate context classes (V13Context, V17Context) which would require casting or generics.

**Decision 2: PromptVersion as enum in `Config.java` vs separate file**

`PromptVersion` is a two-value enum (V13, V17) referenced only by `PromptBuilder` and `Config`. Placing it as a static nested enum inside `Config.java` keeps it close to the `llm_prompt_version` config field and avoids a trivial one-enum file. If more versions are added later, it can be extracted.

**Decision 3: ARRIVAL_FIRST tracks `previousScreenHash` in RoutingManager**

`AgentLoop` already tracks the current screen hash per iteration. The simplest way to implement ARRIVAL_FIRST is to pass both the current hash and the previous hash into `shouldUseLlm()`. Alternatively, `RoutingManager` could hold a `previousHash` field updated each call. The latter is cleaner (RoutingManager owns the comparison) and avoids changing the `shouldUseLlm()` call site extensively. `RoutingManager.shouldUseLlm(String currentHash, boolean isOutOfApp)` stores `currentHash` as `lastSeenHash` after each call, comparing on the next invocation.

**Decision 4: Navigation hint computed from StaticMap in AgentLoop, not PromptBuilder**

Computing "which activity has the most MOP operations and is reachable in fewest hops" requires StaticMap traversal. This belongs in `AgentLoop.tryLlmAction()` where StaticMap is already available, not in PromptBuilder (which should stay a pure formatter). The hint is a pre-computed String passed through PromptContext.

**Decision 5: Remove `hybrid` variant, don't alias it**

The `hybrid` variant had the wrong URL and PROBABILISTIC strategy at 5%. Keeping it as an alias to `arrival_first_v13` would be a backward-compatibility shim (P3: no shims). It is deleted. Users running `rvsmart:hybrid` will get a clear error rather than silently incorrect behavior.

**Decision 6: Ring buffer size = 5 actions**

RVAgent used last 5 actions. The 4B model has limited context capacity — 5 actions at ~20 tokens each adds ~100 tokens to a prompt already ~800-1000 tokens. This is acceptable. A configurable buffer size adds unnecessary complexity for a first implementation.

## API Design

### `PromptContext` (new Java class)

```java
public final class PromptContext {
    // Required for all versions
    public final String base64Screenshot;
    public final List<ScreenItem> uiElements;
    public final String currentActivity;
    public final String navigationHint;       // null if not available
    public final Set<String> visitedActivities;
    public final int iterationNumber;

    // V17-only (nullable — V17 degrades gracefully when absent)
    public final Map<String, Integer> elementInteractionCounts; // elementKey → count
    public final Set<String> directMopElements;                 // elementKey set
    public final Set<String> indirectMopElements;               // elementKey set
    public final Map<String, Integer> elementScores;            // elementKey → score
    public final List<Action> recentActions;                    // last N actions

    public static class Builder { /* fluent setters */ }
}
```

The `elementKey` is a stable string identifier for a UI element — the same key used by `UICoverageTracker`. This is typically a hash of `(className, text, bounds)` computed in `ScreenItem.getKey()`.

### `PromptBuilder.build(PromptVersion version, PromptContext ctx)`

```java
public List<SglangClient.Message> build(PromptVersion version, PromptContext ctx)
```

- **Precondition**: `version != null`, `ctx != null`, `ctx.base64Screenshot != null`
- **Postcondition**: returns a 2-element list `[systemMessage, userMessage]`
- **Error**: none — null/empty V17 fields produce V13-equivalent output for those sections (INV-RSM-LLM-04)
- **Side-effect**: logs full prompt to `Log.d("RVSMART-PROMPT", ...)` if `BuildConfig.DEBUG`

### `RoutingManager.shouldUseLlm(String currentHash, boolean isOutOfApp)`

```java
public boolean shouldUseLlm(String currentHash, boolean isOutOfApp)
```

- **Precondition**: `currentHash != null`
- **Postcondition**: returns false if `isOutOfApp`; otherwise delegates to mode/strategy logic
- **Side-effect**: in ARRIVAL_FIRST, updates `this.lastSeenHash = currentHash` after each call

## Data Flow

```
AgentLoop.runIteration()
  │
  ├── captureUI() → ScreenState (uiElements, hash, activity)
  ├── drainLogcat() → coverage events → UICoverageTracker updated
  │
  ├── tryLlmAction(screen, currentHash, activity, outOfAppCount, iteration):
  │     │
  │     ├── if outOfAppCount > 0: return null
  │     ├── routingManager.shouldUseLlm(currentHash, false)
  │     │     └── ARRIVAL_FIRST: compare currentHash with lastSeenHash
  │     │
  │     ├── PromptContext.Builder()
  │     │     .screenshot(imageProcessor.process(screenshotCapture.capture()))
  │     │     .uiElements(screen.items)
  │     │     .activity(activity)
  │     │     .navigationHint(computeNavigationHint(staticMap, activity))
  │     │     .visited(visitedActivities)
  │     │     .iteration(iteration)
  │     │     // V17 extras:
  │     │     .interactionCounts(uiCoverageTracker.getCountsForScreen(screen))
  │     │     .directMop(staticMap.getDirectMopElements(activity))
  │     │     .indirectMop(staticMap.getTransitiveMopElements(activity))
  │     │     .scores(actionSelector.getLastScoreBreakdown())
  │     │     .recentActions(recentActionsBuffer.snapshot())
  │     │     .build()
  │     │
  │     ├── promptBuilder.build(config.promptVersion, context)
  │     ├── sglangClient.chat(messages)
  │     ├── toolCallParser.parse(response)   → logs to RVSMART-LLM-RESP
  │     └── coordinateNormalizer.convert(parsed) → Action
  │
  └── (if null) actionSelector.selectAction(screen, graph, staticMap) → Action
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Connection refused / timeout | `SglangClient.chat()` | Catch `LlmException`, record failure | `routingManager.recordLlmFailure()` → falls back to algorithm |
| ToolCallParser returns null | No parseable action in response | Record failure, return null from `tryLlmAction` | Falls back to algorithm |
| Screenshot capture fails | `ScreenshotCapture.capture()` returns null | Record failure, return null | Falls back to algorithm |
| Circuit breaker open | `routingManager.shouldUseLlm()` returns false | Skip LLM | Algorithm handles iteration |
| Invalid PromptVersion | `PromptBuilder.build()` receives unknown version | `IllegalArgumentException` at construction | Surfaced at bootstrap, not during loop |

## Risks / Trade-offs

- **[Risk] V17 element key matching may not align with UICoverageTracker keys** → Use the same `ScreenItem.getKey()` method in both PromptBuilder and UICoverageTracker. Verify with a unit test that uses real ScreenItem fixtures.
- **[Risk] StaticMap MOP data is activity-level, not element-level** → The `[DM]`/`[M]` markers annotate elements whose *activity* reaches a MOP, not elements that individually trigger a MOP call. This is a simplification (same as RVAgent). The navigation hint provides the more specific element-level description when available.
- **[Risk] Qwen3-VL-4B may not benefit from V17 rich context** → The 4B model is smaller than models that clearly benefit from enriched prompts. The `arrival_first_v13` variant provides a V13 baseline for comparison. If V17 shows no improvement over V13 in coverage tests, the team can default to V13 permanently.
- **[Risk] ARRIVAL_FIRST phase-2 probability 0.30 is untested** → This is the initial value. Post-implementation testing on cryptoapp will reveal whether it's appropriate. Optuna calibration should be run after the first stable version.
- **[Risk] `hybrid` variant removal breaks existing experiment configs** → Any saved experiment configuration referencing `rvsmart:hybrid` will fail at tool resolution. This is intentional (P3). Users must update to `rvsmart:arrival_first_v13`.

## Testing Strategy

| Layer | What | How | Files |
|-------|------|-----|-------|
| Unit | PromptBuilder V13 message structure | Fixed ScreenItems, assert output strings | `PromptBuilderTest.java` |
| Unit | PromptBuilder V17 test-status tags, MOP markers, scores | Mock interaction counts + StaticMap sets | `PromptBuilderTest.java` |
| Unit | PromptBuilder V17 graceful degradation | null context fields | `PromptBuilderTest.java` |
| Unit | RoutingManager ARRIVAL_FIRST arrival signal | hash change → true | `RoutingManagerTest.java` |
| Unit | RoutingManager ARRIVAL_FIRST phase-2 | same hash, seeded random | `RoutingManagerTest.java` |
| Unit | RoutingManager out-of-app guard | outOfAppCount > 0 → false | `RoutingManagerTest.java` |
| Unit | tool.py variant registry | assert new variants, assert hybrid absent | `test_rvsmart_tool.py` |
| Integration | LLM_ONLY connectivity on cryptoapp | `rv-experiment run --tools rvsmart:llm_only --timeout 60` | manual / CI |
| Integration | arrival_first_v17 coverage vs pure_algorithm | side-by-side 5-min runs on cryptoapp | manual |

## Open Questions

1. **Does `ScreenItem.getKey()` exist, or does UICoverageTracker use a different identifier?** Need to verify the element key contract before wiring V17 context. If keys differ, a mapping step is needed in `AgentLoop.tryLlmAction()`.
2. **StaticMap API for MOP element sets** — does `StaticMap` currently expose a method to get element-level MOP reachability, or only activity-level? If activity-level only, the `[DM]`/`[M]` markers will annotate *all* elements on a MOP-reachable screen, not specific ones.
3. **`llm_multimode_strategy` config param** — confirm the Java `Config.java` already has a `llm_multimode_strategy` field or needs it added. If it exists (as `MultiModeStrategy` enum), just extend the enum.
