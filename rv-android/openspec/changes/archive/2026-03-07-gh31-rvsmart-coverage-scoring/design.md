## Context

After gh30 fixes rvsmart's critical bugs (hash redesign, saturation, scroll, MopScorer, UI captures, action selection gaps) and speed bottlenecks (throttle, restart cost, adaptive wait, state caching, cycle profiling), the agent will have a functional foundation with ~10 evt/s throughput. This change adds the exploration intelligence needed to consistently outperform APE and FastBot: element-level coverage tracking, plateau detection, improved scoring parameters, WTG-based scoring with multi-hop guidance, and context-aware text input.

> **Dropped**: The Java-side `PackageDetector` was superseded by `--code-package` from rv-android's `App.code_package` (gh30). OOA detection uses manifest package directly. A Java-side diagnostic detector is unnecessary — the researcher already knows the code_package from the Python side.

All changes are in the rvsmart Java codebase (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`). The Python plugin (`modules/rvsmart-tool/`) is not modified.

**Proposal**: `openspec/changes/gh31-rvsmart-coverage-scoring/proposal.md`
**Delta spec**: `openspec/changes/gh31-rvsmart-coverage-scoring/specs/tools/spec.md`
**Pre-plan**: `docs/20260306_rvsmart_refactoring.md` (Phase 1 + Phase 2 + Phase 3)
**PRD references**: FR18 (Tool Registration), NFR01 (Performance), NFR03 (Extensibility)

## Architecture

The new components integrate into the existing rvsmart architecture through the `AgentLoop` orchestrator. No new external dependencies are introduced — all components are pure Java classes with no third-party libraries.

```
AgentLoop (orchestrator)
  |
  +-- UiCapture (existing) -----> UICoverageTracker (NEW)
  |                                    |
  +-- ActionSelector (existing) <------+-- getCoverageGap()
  |     |
  |     +-- MopScorer (existing, fixed in gh30)
  |     +-- GradualDecayScorer (existing)
  |     +-- SystemElementFilter (existing, enhanced)
  |     +-- ComponentPriorityScorer (existing)
  |     +-- ConfirmedCoverageScorer (existing, decay added)
  |     +-- CoverageDensityScorer (existing, re-enabled)
  |     +-- WtgScorer (existing stub, implemented with multi-hop BFS)
  |     +-- InputValueGenerator (NEW)
  |     +-- softmax selection (replaces uniform random)
  |
  +-- PlateauDetector (NEW) ----> ActionSelector.stochasticProbability
  |
  +-- StuckDetector (existing, time-based + form exemption + dynamic threshold)
  |
  +-- LLM boundary check (NEW, hybrid mode only)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `core/UICoverageTracker.java` | Track UI elements per screen, record interactions, compute coverage gaps | `List<ScreenItem>`, screen hash, element ID | `float` coverage gap (0.0–1.0) |
| `strategy/PlateauDetector.java` | Detect exploration plateaus via sliding window | `boolean` isNewState, `boolean` hasNewMop | `boolean` isPlateauDetected |
| `strategy/InputValueGenerator.java` | Generate context-aware text input based on widget attributes | `ScreenItem` | `String` input value |
| `strategy/scorers/WtgScorer.java` | Score actions based on static analysis WTG transitions (multi-hop BFS) | `ScreenAction`, scoring context | `double` score (0, 50, 100, or 200) |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|------------------------|----------------|------|
| INV-RSM-20: Element tracking by hybrid ID | `UICoverageTracker.registerScreenElements()` | `UICoverageTrackerTest.testRegisterElements` |
| INV-RSM-21: Coverage gap computation | `UICoverageTracker.getCoverageGap()` | `UICoverageTrackerTest.testCoverageGap*` |
| INV-RSM-22: Sliding window of 10 iterations | `PlateauDetector.recordIteration()` | `PlateauDetectorTest.testWindowSize` |
| INV-RSM-23: Stochastic boost to 0.5 during plateau | `ActionSelector` plateau integration | `ActionSelectorTest.testPlateauBoost` |
| INV-RSM-24: Input value rotation | `InputValueGenerator.generateInput()` | `InputValueGeneratorTest.testRotation` |
| INV-RSM-25: WTG transition scoring (multi-hop) | `WtgScorer.score()` | `WtgScorerTest.testUnvisited*`, `testMultiHop*` |
| INV-RSM-27: System UI element filtering | `ActionSelector.generateCandidateActions()` | `ActionSelectorTest.testSystemUiFilter` |
| Scoring parameter tuning | `Config.java` defaults | `ConfigTest.testScoringDefaults` |
| Saturation thresholds | `ScreenNode.java` constants | `ScreenNodeTest.testSaturationThresholds` |
| Saturation-based proactive backtrack | `ActionSelector` tier-3 condition | `ActionSelectorTest.testSaturationBacktrack` |
| ConfirmedCoverageScorer decay | `ConfirmedCoverageScorer.score()` | `ConfirmedCoverageScorerTest.testDecay` |
| Form action exemption for stuck | `StuckDetector` action type check | `StuckDetectorTest.testFormExemption` |
| Dynamic stuck threshold | `StuckDetector` per-screen threshold | `StuckDetectorTest.testDynamicThreshold` |
| Time-based stuck detection | `StuckDetector` time threshold | `StuckDetectorTest.testTimeBased` |
| LLM boundary protection | `AgentLoop` LLM action validation | `AgentLoopTest.testLlmBoundaryReject` |
| Score breakdown in RVTRACK | `TraceWriter` score decomposition | `TraceWriterTest.testScoreBreakdown` |

## Goals / Non-Goals

**Goals:**
- Port rvagent's element-level coverage tracking to rvsmart with hybrid element IDs (resourceId-primary, coords-fallback)
- Enable coverage-driven exploration decisions through `CoverageDensityScorer` using real coverage data
- Fix scorer parameter problems identified by 5 LLM analyses (BACK score, saturation thresholds, backtrack trigger, uniform random, maxRetries, ConfirmedCoverageScorer overfitting)
- Implement WtgScorer with multi-hop BFS (depth 2-3) using the static analysis transitions section to guide exploration toward unvisited activities
- Replace hardcoded "test" with context-aware input to pass login screens and form validations
- Add element-level system UI filtering to reduce wasted actions
- Add plateau detection to escape local optima via adaptive stochastic boost
- Add form action exemption and dynamic stuck threshold to prevent premature backtracking during form filling
- Add score breakdown in RVTRACK for fast debugging and calibration

**Non-Goals:**
- Cross-run model persistence (Phase 5, deferred)
- Adaptive state abstraction / CEGAR (Phase 5, deferred)
- LLM-guided plateau recovery (Phase 5, deferred — plateau boost uses stochastic, not LLM)
- Coordinated multi-step action sequences for login flows (gh32, deferred — simplified version)
- Input fuzzing mode (gh32, deferred — opt-in feature)
- Deep link integration for unreachable activities (Phase 5, deferred)
- Changes to the rvsmart-tool Python plugin or RVSMART_METRICS JSON format
- Changes to the rv-platform, rv-experiment, or any other Python module

## Decisions

### D1: UICoverageTracker as a standalone class (not integrated into ScreenNode)

**Choice**: New `UICoverageTracker` class that AgentLoop manages.

**Alternative considered**: Adding element tracking directly to `ScreenNode` (which already has `executionCounts` and `widgetClasses`). Rejected because ScreenNode tracks action execution (by action signature) while UICoverageTracker tracks element identity (by element ID). These are conceptually different: one action signature can map to different elements across visits, and one element can be targeted by different action types. Keeping them separate follows P1 (simplicity — single responsibility).

### D2: Hybrid element IDs (resourceId-primary, coordinates-fallback)

**Choice**: Element ID format `"res:{resource_id}"` when resourceId is present and non-empty, otherwise `"coords:{centerX},{centerY}"`.

**Rationale**: Pure coordinate-based IDs (`coords:x,y`) have a collision problem: overlapping widgets (e.g., a Button containing an ImageView) share the same center coordinates, causing UICoverageTracker to undercount elements and misreport coverage gap. Using `resource_id` as primary ID avoids this for the majority of interactive elements that have resource IDs. The coords fallback handles the minority of elements without resource IDs. Shared resource_ids in lists (e.g., all items with `@id/item_title`) is a theoretical concern but rare for interactive elements (buttons, inputs) that the agent targets.

### D3: Softmax instead of Gumbel-max for stochastic selection

**Choice**: Softmax-weighted selection with temperature=50.

**Alternative considered**: Gumbel-max trick (MiniMax suggestion), which adds Gumbel noise to log-scores and takes the argmax. Mathematically equivalent to softmax sampling but implemented differently. Rejected because softmax is more widely understood, easier to debug (explicit probabilities), and the temperature parameter is more intuitive to tune. Performance difference is negligible for candidate lists of 10–50 actions.

### D4: Saturation-based proactive backtrack trigger (not score-based)

**Choice**: Trigger proactive backtrack when `screenNode.getSaturationRate() >= 0.8` instead of when best score falls below a fixed threshold.

**Rationale**: The original score-based threshold (50, then 150) is fragile — adding or removing scorers shifts the score range, requiring re-tuning. The rvagent Python uses saturation >= 0.8 as the backtrack trigger, which is self-calibrating: it depends only on how many actions have been tried on the current screen, not on scorer weights. Now that gh30 task 0.1 fixes `getSaturationRate()` to return correct values, the saturation-based approach is viable and more robust.

### D5: Time-based stuck detection as a secondary trigger (not replacement)

**Choice**: Add 30-second time threshold alongside existing iteration-based detection.

**Alternative considered**: Replacing iteration-based with time-based entirely. Rejected because iteration-based detection is reliable in pure_algorithm mode (fast, consistent iterations) and only fails in hybrid/multimode (variable iteration duration). Both triggers share the same recovery mechanism, so having both adds robustness without complexity.

### D6: WtgScorer multi-hop BFS (depth 3, diminishing boost)

**Choice**: BFS of depth 3 on the transitions graph with diminishing boost: +200 (1-hop to unvisited), +100 (2-hop), +50 (3-hop).

**Rationale**: 1-hop scoring (the original design) only guides the agent toward immediately adjacent activities. For apps with deep navigation hierarchies (Settings → Category → Detail), activities 2-3 hops deep are invisible to the scorer. BFS on a small WTG graph (typically <50 nodes) has negligible cost. The diminishing boost ensures that direct transitions are preferred while still providing guidance toward distant targets. WtgScorer applies ONLY to CLICK and LONG_CLICK actions on interactive widgets — for SCROLL, BACK, RESTART, and SET_TEXT actions, WtgScorer returns 0 (WTG transitions only describe widget-triggered navigation).

### D7: ConfirmedCoverageScorer decay with revisit count

**Choice**: Score = `150 / (1 + revisits)` instead of flat +150.

**Rationale**: The flat +150 boost for screens that already yielded MOP coverage, combined with MopScorer's activity-based boost, creates a positive feedback loop that keeps the agent on known-productive screens instead of exploring new ones. Adding a revisit-based decay preserves the "this screen has MOP" signal on first visits but diminishes it as the agent revisits, pushing toward exploration of new screens.

## API Design

### `UICoverageTracker`

```java
public class UICoverageTracker {
    // Register all interactive elements on a screen visit
    // Idempotent: re-registering known elements does not duplicate them
    // Element ID: "res:{resource_id}" when present, else "coords:{centerX},{centerY}"
    void registerScreenElements(String screenHash, List<ScreenItem> items);

    // Record an interaction with an element
    void recordInteraction(String screenHash, String elementId);

    // Get fraction of untested elements (0.0 = all tested, 1.0 = none tested)
    // Returns 1.0 for unknown screen hashes
    float getCoverageGap(String screenHash);

    // Get total registered elements across all screens
    int getTotalElements();

    // Get total interactions recorded
    int getTotalInteractions();
}
```

### `PlateauDetector`

```java
public class PlateauDetector {
    static final int WINDOW_SIZE = 10;

    // Record iteration outcome
    void recordIteration(boolean isNewState, boolean hasNewMopCoverage);

    // Check if plateau is currently detected
    boolean isPlateauDetected();

    // Get current window statistics (for RVTRACK logging)
    int getConsecutiveNoProgress();
}
```

### `InputValueGenerator`

```java
public class InputValueGenerator {
    // Generate context-appropriate input for a text field
    // Tracks used values per element to ensure rotation
    String generateInput(ScreenItem item);

    // Get the category detected for a widget (for logging/debugging)
    String getCategory(ScreenItem item);
}
```

### `WtgScorer` (existing class, implemented with multi-hop BFS)

```java
public class WtgScorer implements ActionScorer {
    // Returns: 200 (1-hop to unvisited), 100 (2-hop), 50 (3-hop), 0 (no match or no data)
    // Only scores CLICK and LONG_CLICK actions; returns 0 for SCROLL, BACK, RESTART, SET_TEXT
    double score(ScreenAction action, ScoringContext context);
}
```

## Data Flow

```
UiCapture.capture()
      |
      v
  List<ScreenItem>
      |
      +--------> UICoverageTracker.registerScreenElements(hash, items)
      |                |
      |                v
      |          elementsByScreen: Map<String, Set<String>>
      |          interactionCounts: Map<String, Integer>
      |
      +--------> ActionSelector.generateCandidateActions(items, context)
                       |
                       +-- filter: exclude packageName == "com.android.systemui"
                       +-- generate: CLICK, LONG_CLICK, SET_TEXT (via InputValueGenerator), SCROLL
                       |
                       v
                  List<ScoredAction>
                       |
                       +-- MopScorer (activity-based, fixed in gh30)
                       +-- GradualDecayScorer
                       +-- ComponentPriorityScorer
                       +-- ConfirmedCoverageScorer (with revisit decay)
                       +-- CoverageDensityScorer (reads UICoverageTracker.getCoverageGap)
                       +-- WtgScorer (multi-hop BFS, reads StaticMap.getTransitions)
                       +-- SystemElementFilter
                       |
                       v
                  Selection (softmax-weighted if stochastic, else top-scored)
                       |
                       +-- stochastic probability = 0.5 if PlateauDetector.isPlateauDetected()
                       +-- stochastic probability = 0.15 otherwise
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Unknown screen hash in getCoverageGap | UICoverageTracker | Return 1.0 (fully unexplored) | No error — defensive default |
| Null hint/resourceId in InputValueGenerator | Widget attributes | Fall back to Generic category | Use "test" as first generic value |
| StaticMap has no transitions data | No static analysis JSON | WtgScorer returns 0 for all actions | Graceful degradation |
| Softmax overflow (very high scores) | Extreme score values | Subtract max score before exp() | Standard numerical stability trick |
| BFS cycle in transitions graph | Malformed static analysis data | Track visited nodes in BFS | Skip already-visited nodes |

## Risks / Trade-offs

**[UICoverageTracker memory overhead]** → Cap tracked elements at 2000 per screen (same as UiCapture MAX_ITEMS). Use HashMap, not LinkedHashMap, since insertion order is not needed. Profile memory usage in long runs (1000+ iterations).

**[Softmax temperature sensitivity]** → Temperature=50 is a reasonable default for score ranges of 0–500. If calibration (gh9) reveals better values, the temperature is configurable via Config. No adaptive temperature — that would add complexity for uncertain benefit (P1).

**[WtgScorer depends on gh30 StaticMap fix]** → gh30 task 0.3 exposes both `getReachableMethods()` and `getTransitions()`. WtgScorer reads from the same `StaticMap` instance — API alignment is verified in integration tests.

**[InputValueGenerator category detection is heuristic]** → Pattern matching on hint/resource_id may misclassify some widgets. Mitigation: the Generic fallback ensures no field goes unfilled, and value rotation ensures diversity even with wrong categorization.

**[PlateauDetector window size is fixed at 10]** → In fast execution (~10 evt/s), 10 iterations = ~1 second, which may be too short. In slow execution (~2 evt/s), 10 iterations = ~5 seconds, which is reasonable. The window size is a constant, not configurable — changing it requires a code change. If calibration reveals a better value, it can be updated without architectural changes.

**[Saturation threshold increase]** → Raising from 2→4 (default) and 4→6 (multi-value) increases per-screen time. This is intentional — the current threshold of 2 causes premature backtracking. Combined with plateau detection, the agent will escape truly stuck screens while persisting longer on productive ones.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | UICoverageTracker element registration (hybrid IDs), coverage gap, idempotency | Direct method calls with mock ScreenItems | ~8 tests |
| Unit | PlateauDetector sliding window, plateau detection, clearance | Sequential recordIteration calls | ~5 tests |
| Unit | InputValueGenerator category detection, rotation, fallback | Mock ScreenItems with various hints/resource_ids | ~8 tests |
| Unit | WtgScorer with mock StaticMap data: 1-hop, 2-hop, 3-hop, no-data, action-type filter | Mock ScoringContext with transitions | ~8 tests |
| Unit | Softmax selection probability distribution | Verify score ordering affects selection probability | ~3 tests |
| Unit | System UI filtering, LLM boundary protection | Mock items and coordinates | ~4 tests |
| Unit | Scoring parameter defaults (BACK score, saturation thresholds, maxRetries) | Read Config defaults | ~3 tests |
| Unit | Saturation-based proactive backtrack trigger | Mock ScreenNode with various saturation rates | ~3 tests |
| Unit | ConfirmedCoverageScorer decay with revisit count | Score at revisit=0,1,5,10 | ~3 tests |
| Unit | Time-based stuck detection, form action exemption, dynamic threshold | Mock clock, verify 30s threshold, verify SET_TEXT exempt, verify per-screen threshold | ~6 tests |
| Unit | Score breakdown in RVTRACK trace output | Verify trace contains per-scorer decomposition | ~2 tests |
| Integration | Full AgentLoop iteration with UICoverageTracker + PlateauDetector | End-to-end iteration with mock device | ~3 tests |

**Total: ~56 new tests** (all JUnit 5, no external dependencies beyond mocking).

## Open Questions

None — all design decisions are resolved. Implementation can proceed once gh30 is complete.
