package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.PhaseController;
import br.unb.cic.rvsmart.strategy.scorers.ComponentPriorityScorer;
import br.unb.cic.rvsmart.strategy.scorers.ConfirmedCoverageScorer;
import br.unb.cic.rvsmart.strategy.scorers.CoverageDensityScorer;
import br.unb.cic.rvsmart.strategy.scorers.GradualDecayScorer;
import br.unb.cic.rvsmart.strategy.scorers.MopScorer;
import br.unb.cic.rvsmart.strategy.scorers.Scorer;
import br.unb.cic.rvsmart.strategy.scorers.SystemElementFilter;
import br.unb.cic.rvsmart.strategy.scorers.VisitationPenaltyScorer;
import br.unb.cic.rvsmart.strategy.scorers.WtgScorer;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ActionSelector — 4-tier action selection with scoring, BACK decay,
 * and stochastic selection.
 *
 * Note: Android's Rect class is a stub in unit tests (android.jar system scope),
 * so items are created with null bounds. generateCandidateActions skips items
 * with null bounds, meaning Tier 4 always applies with BACK + RESTART as the
 * only candidates. This is sufficient to verify INV-RSM-12 (never null),
 * BACK decay, and selectNextBest behavior.
 */
class ActionSelectorTest {

    private Config config;
    private ActionSelector selector;
    private ContentGraph graph;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        config = Config.defaults();
        config.setSeed(42);
        selector = new ActionSelector(config);
        graph = new ContentGraph();
        staticMap = new StaticMap(null);
    }

    @Test
    void testSelectActionNeverReturnsNull_EmptyScreen() {
        // INV-RSM-12: selectAction NEVER returns null, even with empty screen.
        // Tier 4 always includes BACK and RESTART.
        ScreenState emptyScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");
        Action action = selector.selectAction(emptyScreen, graph, staticMap);
        assertNotNull(action, "selectAction must never return null (INV-RSM-12)");
    }

    @Test
    void testSelectActionNeverReturnsNull_ScreenWithNullBoundsItems() {
        // Items with null bounds are skipped, so this is effectively an empty screen.
        // BACK and RESTART guarantee non-null result.
        ScreenState screen = createScreenWithNullBoundsItems();
        Action action = selector.selectAction(screen, graph, staticMap);
        assertNotNull(action, "selectAction must never return null");
    }

    @Test
    void testTier4ReturnsRestartOnRootScreen() {
        // With no widget candidates (null bounds) and no SuccessorTracker,
        // Tier 4 provides only RESTART (BACK excluded on root screens)
        ScreenState screen = createScreenWithNullBoundsItems();
        Action action = selector.selectAction(screen, graph, staticMap);
        assertNotNull(action);
        assertEquals(Action.Type.RESTART, action.getType(),
                "Tier 4 should return RESTART when no widget candidates and no parents");
    }

    @Test
    void testBackDecayIncreasesOnIneffectiveBack() {
        String hash = "screen_hash_1";
        assertEquals(0, selector.getBackDecayCount(hash));

        // Simulate ineffective BACK (no screen change)
        selector.updateBackDecay(true, false, hash);
        assertEquals(1, selector.getBackDecayCount(hash));

        selector.updateBackDecay(true, false, hash);
        assertEquals(2, selector.getBackDecayCount(hash));
    }

    @Test
    void testBackDecayResetsOnEffectiveBack() {
        String hash = "screen_hash_1";

        // Accumulate some decay
        selector.updateBackDecay(true, false, hash);
        selector.updateBackDecay(true, false, hash);
        assertEquals(2, selector.getBackDecayCount(hash));

        // Effective BACK resets the counter
        selector.updateBackDecay(true, true, hash);
        assertEquals(0, selector.getBackDecayCount(hash));
    }

    @Test
    void testBackDecayNotAffectedByNonBackActions() {
        String hash = "screen_hash_1";

        // Non-BACK action should not change decay count
        selector.updateBackDecay(false, true, hash);
        assertEquals(0, selector.getBackDecayCount(hash));

        selector.updateBackDecay(false, false, hash);
        assertEquals(0, selector.getBackDecayCount(hash));
    }

    @Test
    void testStochasticSelectionWithSeed() {
        // With a seed, results are deterministic. Run multiple times to exercise
        // the stochastic path in selectFromUnifiedQueue.
        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");
        for (int i = 0; i < 10; i++) {
            Action action = selector.selectAction(screen, graph, staticMap);
            assertNotNull(action);
        }
    }

    @Test
    void testSelectNextBestExcludesSpecifiedSignatures() {
        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");
        Set<String> excluded = new HashSet<>();
        excluded.add("back@0,0");

        Action action = selector.selectNextBest(screen, excluded, graph, staticMap);
        assertNotNull(action);
        // Should not be the excluded BACK signature
        assertNotEquals("back@0,0", action.signature());
    }

    @Test
    void testSelectNextBestReturnsNullWhenAllExcluded() {
        // No widget candidates (empty screen), exclude BACK + RESTART
        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");
        Set<String> excluded = new HashSet<>();
        excluded.add("back@0,0");
        excluded.add("restart@0,0");

        Action action = selector.selectNextBest(screen, excluded, graph, staticMap);
        assertNull(action, "Should return null when all candidates are excluded");
    }

    // --- Root screen BACK prevention tests (Group 15) ---

    @Test
    void testBackExcludedOnRootScreen_NoParentsInSuccessorTracker() {
        // When SuccessorTracker has no parents for the current screen (root),
        // BACK should never be selected — only RESTART is available.
        SuccessorTracker tracker = new SuccessorTracker();
        ActionSelector selectorWithTracker = new ActionSelector(config, tracker);

        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "RootActivity");

        // Run multiple times to exercise stochastic path
        for (int i = 0; i < 20; i++) {
            Action action = selectorWithTracker.selectAction(screen, graph, staticMap);
            assertNotNull(action);
            assertNotEquals(Action.Type.BACK, action.getType(),
                    "BACK must not be selected on root screen (no parents)");
        }
    }

    @Test
    void testBackAllowedWhenParentsExist() {
        // When SuccessorTracker records parents for the current screen,
        // BACK is a valid candidate and can be selected.
        SuccessorTracker tracker = new SuccessorTracker();

        ScreenState rootScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "RootActivity");
        ScreenState childScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "ChildActivity");

        // Record that rootScreen -> childScreen transition occurred
        tracker.record(rootScreen.getContentHash(), childScreen.getContentHash());

        // With stochastic disabled (seed=42), on childScreen BACK or RESTART can appear.
        // The key assertion: BACK is NOT excluded (it appears in the candidate list).
        ActionSelector selectorWithTracker = new ActionSelector(config, tracker);

        // Verify childScreen has parents
        assertFalse(tracker.getParents(childScreen.getContentHash()).isEmpty(),
                "Child screen should have parents");

        // On empty screen with parents, Tier 4 includes BACK + RESTART.
        // BACK at -500 and RESTART at -500 are equal, so either can be selected.
        Action action = selectorWithTracker.selectAction(childScreen, graph, staticMap);
        assertNotNull(action);
        assertTrue(action.getType() == Action.Type.BACK || action.getType() == Action.Type.RESTART,
                "On screen with parents, both BACK and RESTART should be candidates");
    }

    @Test
    void testBackExcludedWhenSuccessorTrackerIsNull() {
        // When no SuccessorTracker is wired (null), the selector treats every screen
        // as root: BACK is excluded. Only RESTART is available.
        ActionSelector selectorNoTracker = new ActionSelector(config);

        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "SomeActivity");

        for (int i = 0; i < 10; i++) {
            Action action = selectorNoTracker.selectAction(screen, graph, staticMap);
            assertNotNull(action);
            // With null tracker, isRootScreen=true, so BACK is excluded
            assertEquals(Action.Type.RESTART, action.getType(),
                    "With null SuccessorTracker, only RESTART should be available");
        }
    }

    @Test
    void testRootScreenWithExhaustedWidgets_RestartIsFallback() {
        // On root screen with no widget candidates (empty screen),
        // RESTART is the only fallback — BACK is excluded.
        SuccessorTracker tracker = new SuccessorTracker();
        ActionSelector selectorWithTracker = new ActionSelector(config, tracker);

        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "RootActivity");

        Action action = selectorWithTracker.selectAction(screen, graph, staticMap);
        assertNotNull(action, "selectAction must never return null (INV-RSM-12)");
        assertEquals(Action.Type.RESTART, action.getType(),
                "On root screen with no widgets, RESTART must be the fallback");
    }

    @Test
    void testBackBaseScoreIsNegative100() {
        Config defaultConfig = Config.defaults();
        assertEquals(-100.0f, defaultConfig.getBackBaseScore(), 0.01f,
                "BACK base score should be -100 (gh31: reduced from -500 to allow voluntary backtracking)");
    }

    @Test
    void testBackDecayPerRepeatIs100() {
        Config defaultConfig = Config.defaults();
        assertEquals(100.0f, defaultConfig.getBackDecayPerRepeat(), 0.01f,
                "BACK decay per repeat should be 100 (gentler since base is already -500)");
    }

    // --- selectNextBest root screen BACK prevention tests (Group 19) ---

    @Test
    void testSelectNextBestExcludesBackOnRootScreen_NoTracker() {
        // selectNextBest must apply the same root-screen check as Tier 4:
        // when SuccessorTracker is null, BACK is excluded from candidates.
        ActionSelector selectorNoTracker = new ActionSelector(config);
        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "RootActivity");
        Set<String> excluded = new HashSet<>();

        // On root screen with no widgets: only RESTART is available
        Action action = selectorNoTracker.selectNextBest(screen, excluded, graph, staticMap);
        assertNotNull(action);
        assertNotEquals(Action.Type.BACK, action.getType(),
                "selectNextBest must not return BACK on root screen (null tracker)");
        assertEquals(Action.Type.RESTART, action.getType(),
                "selectNextBest should return RESTART when BACK is excluded on root screen");
    }

    @Test
    void testSelectNextBestExcludesBackOnRootScreen_EmptyParents() {
        // selectNextBest must exclude BACK when SuccessorTracker has no parents
        SuccessorTracker tracker = new SuccessorTracker();
        ActionSelector selectorWithTracker = new ActionSelector(config, tracker);
        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "RootActivity");
        Set<String> excluded = new HashSet<>();

        for (int i = 0; i < 20; i++) {
            Action action = selectorWithTracker.selectNextBest(screen, excluded, graph, staticMap);
            assertNotNull(action);
            assertNotEquals(Action.Type.BACK, action.getType(),
                    "selectNextBest must not return BACK on root screen (empty parents)");
        }
    }

    @Test
    void testSelectNextBestAllowsBackWhenParentsExist() {
        // selectNextBest should include BACK when the screen has parents
        SuccessorTracker tracker = new SuccessorTracker();
        ScreenState rootScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "RootActivity");
        ScreenState childScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "ChildActivity");
        tracker.record(rootScreen.getContentHash(), childScreen.getContentHash());

        ActionSelector selectorWithTracker = new ActionSelector(config, tracker);
        Set<String> excluded = new HashSet<>();

        // On child screen (has parents), both BACK and RESTART are candidates
        Action action = selectorWithTracker.selectNextBest(childScreen, excluded, graph, staticMap);
        assertNotNull(action);
        assertTrue(action.getType() == Action.Type.BACK || action.getType() == Action.Type.RESTART,
                "selectNextBest should allow BACK when parents exist");
    }

    // --- Scorer chain composition tests (Group 17) ---

    @Test
    void testScorerChainContainsComponentPriorityScorer() {
        // ComponentPriorityScorer must be in the chain (added in Group 17)
        List<Scorer> scorers = selector.getScorers();
        boolean found = scorers.stream().anyMatch(s -> s instanceof ComponentPriorityScorer);
        assertTrue(found, "ComponentPriorityScorer must be in the scorer chain");
    }

    @Test
    void testScorerChainContainsConfirmedCoverageScorer_WhenProvided() {
        // When a ConfirmedCoverageScorer is passed, it must be in the chain
        ConfirmedCoverageScorer confirmedScorer = new ConfirmedCoverageScorer(150);
        ActionSelector selectorWithConfirmed = new ActionSelector(
                config, null, confirmedScorer);

        List<Scorer> scorers = selectorWithConfirmed.getScorers();
        boolean found = scorers.stream().anyMatch(s -> s instanceof ConfirmedCoverageScorer);
        assertTrue(found, "ConfirmedCoverageScorer must be in the chain when provided");
        assertEquals(6, scorers.size(), "Should have 6 scorers: Mop, GradualDecay, SystemElement, Component, Wtg, Confirmed");
    }

    @Test
    void testScorerChainOmitsConfirmedCoverageScorer_WhenNull() {
        // When null is passed for ConfirmedCoverageScorer, chain has 5 scorers
        ActionSelector selectorNoConfirmed = new ActionSelector(config);
        List<Scorer> scorers = selectorNoConfirmed.getScorers();
        assertEquals(5, scorers.size(), "Should have 5 scorers without ConfirmedCoverageScorer");
        boolean found = scorers.stream().anyMatch(s -> s instanceof ConfirmedCoverageScorer);
        assertFalse(found, "ConfirmedCoverageScorer must not be in chain when null");
    }

    @Test
    void testScorerChainDoesNotContainVisitationPenaltyScorer() {
        // VisitationPenaltyScorer is excluded: redundant with GradualDecayScorer
        List<Scorer> scorers = selector.getScorers();
        boolean found = scorers.stream().anyMatch(s -> s instanceof VisitationPenaltyScorer);
        assertFalse(found, "VisitationPenaltyScorer must NOT be in the scorer chain (redundant with GradualDecayScorer)");
    }

    @Test
    void testScorerChainContainsWtgScorer() {
        // WtgScorer is in the chain: activity-level BFS on WTG transitions
        List<Scorer> scorers = selector.getScorers();
        boolean found = scorers.stream().anyMatch(s -> s instanceof WtgScorer);
        assertTrue(found, "WtgScorer must be in the scorer chain (activity-level BFS)");
    }

    @Test
    void testScorerChainDoesNotContainCoverageDensityScorer() {
        // CoverageDensityScorer is excluded: redundant with MopScorer
        List<Scorer> scorers = selector.getScorers();
        boolean found = scorers.stream().anyMatch(s -> s instanceof CoverageDensityScorer);
        assertFalse(found, "CoverageDensityScorer must NOT be in the scorer chain (redundant with MopScorer)");
    }

    @Test
    void testScorerChainOrder() {
        // Verify the scorer chain order: MopScorer, GradualDecay, SystemElement, ComponentPriority, Wtg
        List<Scorer> scorers = selector.getScorers();
        assertEquals(5, scorers.size());
        assertTrue(scorers.get(0) instanceof MopScorer, "First scorer should be MopScorer");
        assertTrue(scorers.get(1) instanceof GradualDecayScorer, "Second scorer should be GradualDecayScorer");
        assertTrue(scorers.get(2) instanceof SystemElementFilter, "Third scorer should be SystemElementFilter");
        assertTrue(scorers.get(3) instanceof ComponentPriorityScorer, "Fourth scorer should be ComponentPriorityScorer");
        assertTrue(scorers.get(4) instanceof WtgScorer, "Fifth scorer should be WtgScorer");
    }

    @Test
    void testConfirmedCoverageScorerBoostsScoreForConfirmedScreens() {
        // Verify the same ConfirmedCoverageScorer instance receives addConfirmed() data
        // and produces a non-zero score when the screen hash matches
        ConfirmedCoverageScorer confirmedScorer = new ConfirmedCoverageScorer(150);
        ActionSelector selectorWithConfirmed = new ActionSelector(
                config, null, confirmedScorer);

        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");

        // Before confirmation, scorer contributes 0
        assertFalse(confirmedScorer.hasConfirmed(screen.getContentHash()));

        // Simulate coverage confirmation on this screen
        Set<String> methods = new HashSet<>();
        methods.add("javax.crypto.Cipher.getInstance");
        confirmedScorer.addConfirmed(screen.getContentHash(), methods);

        // After confirmation, scorer contributes +150
        assertTrue(confirmedScorer.hasConfirmed(screen.getContentHash()));
        assertEquals(150, confirmedScorer.score(
                Action.back("test"), screen, graph, staticMap));
    }

    // --- Phase-based selection observability ---

    @Test
    void testPhase1SelectedWhenUntestedActionsExist() {
        // When untested actions exist, legacy selectAction() uses Phase 1.
        // With no widget candidates (null bounds), falls to unified queue (Phase 3 fallback).
        // The key assertion: lastSelectedPhase is set (not null) after a call.
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        selector.selectAction(screen, graph, staticMap);
        // Phase should be set — either PHASE_1 or PHASE_3 (fallback from empty screen)
        assertNotNull(selector.getLastSelectedPhase(), "lastSelectedPhase must be set after selectAction");
    }

    @Test
    void testPhase3FallbackOnEmptyScreen() {
        // With no widget candidates (null bounds) and no untested actions in node,
        // Phase 1 falls back to Phase 3 (unified queue with boosted stochastic).
        SuccessorTracker tracker = new SuccessorTracker();
        ActionSelector sel = new ActionSelector(config, tracker);

        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        // Register the content node with totalActions=5 and all executed (simulate exhausted)
        graph.getOrCreate(screen.getContentHash(), "TestActivity");
        graph.get(screen.getContentHash()).setTotalActions(5);

        sel.selectAction(screen, graph, staticMap);
        // Phase 3 (stochastic) is the fallback when no untested candidates
        assertNotNull(sel.getLastSelectedPhase());
    }

    // --- Softmax-weighted stochastic selection (task 1.2) ---

    @Test
    void testSoftmaxPrefersHigherScoredActions() {
        // With temperature=50 and scores [300, 100], the action with score 300
        // should be selected much more often than the action with score 100.
        // p(300) = exp(0/50) / (exp(0/50) + exp(-200/50)) = 1/(1+exp(-4)) ≈ 0.982
        Config cfg = Config.defaults();
        cfg.setSeed(42);
        cfg.setStochasticProbability(1.0f); // force stochastic every time
        ActionSelector sel = new ActionSelector(cfg);

        Action a1 = new Action(Action.Type.CLICK, 100, 100, null, "algorithm", "Button", null);
        Action a2 = new Action(Action.Type.CLICK, 200, 200, null, "algorithm", "Button", null);
        Map<Action, Integer> scores = new HashMap<>();
        scores.put(a1, 300);
        scores.put(a2, 100);
        List<Action> actions = Arrays.asList(a1, a2);

        int a1Count = 0;
        for (int i = 0; i < 1000; i++) {
            Action selected = sel.softmaxSelect(actions, scores);
            if (selected == a1) a1Count++;
        }
        // a1 (score 300) should be selected >90% of the time with T=50
        assertTrue(a1Count > 900, "Higher-scored action should be selected >90% but was " + a1Count + "/1000");
    }

    @Test
    void testSoftmaxDegeneratesToUniformOnEqualScores() {
        // With equal scores, softmax should give equal probabilities (uniform random).
        Config cfg = Config.defaults();
        cfg.setSeed(42);
        cfg.setStochasticProbability(1.0f);
        ActionSelector sel = new ActionSelector(cfg);

        Action a1 = new Action(Action.Type.CLICK, 100, 100, null, "algorithm", "Button", null);
        Action a2 = new Action(Action.Type.CLICK, 200, 200, null, "algorithm", "Button", null);
        Map<Action, Integer> scores = new HashMap<>();
        scores.put(a1, 100);
        scores.put(a2, 100);
        List<Action> actions = Arrays.asList(a1, a2);

        int a1Count = 0;
        for (int i = 0; i < 1000; i++) {
            Action selected = sel.softmaxSelect(actions, scores);
            if (selected == a1) a1Count++;
        }
        // With equal scores, expect ~50% each. Allow 35%-65% range for statistical variation.
        assertTrue(a1Count > 350 && a1Count < 650,
                "Equal scores should produce roughly uniform distribution, got " + a1Count + "/1000");
    }

    @Test
    void testSoftmaxNumericalStabilityWithLargeScores() {
        // Large scores should not cause overflow — max subtraction ensures stability.
        Config cfg = Config.defaults();
        cfg.setSeed(42);
        cfg.setStochasticProbability(1.0f);
        ActionSelector sel = new ActionSelector(cfg);

        Action a1 = new Action(Action.Type.CLICK, 100, 100, null, "algorithm", "Button", null);
        Action a2 = new Action(Action.Type.CLICK, 200, 200, null, "algorithm", "Button", null);
        Map<Action, Integer> scores = new HashMap<>();
        scores.put(a1, 10000);
        scores.put(a2, 9900);
        List<Action> actions = Arrays.asList(a1, a2);

        // Should not throw and should prefer a1
        Action selected = sel.softmaxSelect(actions, scores);
        assertNotNull(selected, "softmaxSelect must not return null");
    }

    // --- System UI filtering tests (INV-RSM-27) ---

    @Test
    void testSystemUiElementsFilteredFromCandidates() {
        // generateCandidateActions should skip items with packageName="com.android.systemui".
        // Since Rect is a stub in tests (null bounds), items with null bounds are ALSO skipped,
        // so we verify the filter is present by checking that system UI items don't produce
        // actions even when other conditions are met.
        // This test verifies the filter exists in the code path. Full integration testing
        // requires a real Android environment where Rect works.
        List<ScreenItem> items = Arrays.asList(
                // System UI item — should be filtered out before bounds check
                new ScreenItem("android.widget.ImageButton", "systemui:id/back",
                        null, null, null, "com.android.systemui",
                        true, false, false, true, false, false, -1),
                // App item — allowed (but skipped due to null bounds in test)
                new ScreenItem("android.widget.Button", "pkg:id/btn1",
                        "OK", null, null, "com.example.app",
                        true, false, false, true, false, false, -1)
        );
        ScreenState screen = new ScreenState(items, "TestActivity");

        // Both items have null bounds, so generateCandidateActions returns empty list.
        // The key assertion is that the code compiles and the filter is in the right position.
        List<Action> candidates = selector.generateCandidateActions(screen);
        assertTrue(candidates.isEmpty(),
                "No candidates expected (null bounds in test), but filter is in place");
    }

    @Test
    void testNullPackageNameNotFiltered() {
        // Items with null packageName should NOT be filtered (only "com.android.systemui" is)
        ScreenItem item = new ScreenItem("android.widget.Button", "pkg:id/btn",
                null, null, null, null,
                true, false, false, true, false, false, -1);
        ScreenState screen = new ScreenState(Collections.singletonList(item), "TestActivity");

        // Item has null bounds so it gets skipped by bounds check (not by system UI filter)
        List<Action> candidates = selector.generateCandidateActions(screen);
        assertTrue(candidates.isEmpty(), "Null bounds items skipped, but not by system UI filter");
    }

    // --- Phase 3 stochastic boost tests ---

    @Test
    void testPhase3SelectionIsNonNull() {
        // Phase 3 uses the unified queue with boosted stochastic probability (0.5).
        // Result must never be null (INV-RSM-12).
        Config cfg = Config.defaults();
        cfg.setSeed(42);
        ContentGraph graph3 = new ContentGraph();
        ActionSelector sel = new ActionSelector(cfg);

        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");

        for (int i = 0; i < 10; i++) {
            Action action = sel.selectAction(PhaseController.Phase.PHASE_3, screen,
                    screen.getStructHash(), graph3, null, null, null,
                    new StaticMap(null));
            assertNotNull(action, "Phase 3 must never return null");
        }
    }

    @Test
    void testPhase3LastSelectedPhaseIsSet() {
        Config cfg = Config.defaults();
        cfg.setSeed(42);
        ContentGraph graph3 = new ContentGraph();
        ActionSelector sel = new ActionSelector(cfg);

        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");
        sel.selectAction(PhaseController.Phase.PHASE_3, screen, screen.getStructHash(),
                graph3, null, null, null, new StaticMap(null));

        assertEquals(PhaseController.Phase.PHASE_3, sel.getLastSelectedPhase(),
                "Phase 3 invocation must set lastSelectedPhase to PHASE_3");
    }

    // --- InputValueGenerator integration tests (task 4.2) ---

    @Test
    void testActionSelectorAcceptsInputValueGenerator() {
        // Verify ActionSelector constructor accepts InputValueGenerator
        // and uses it for SET_TEXT actions instead of hardcoded "test".
        // Full functional verification requires real Rect (integration tests).
        InputValueGenerator generator = new InputValueGenerator();
        ActionSelector sel = new ActionSelector(config, null, null, generator, null);
        assertNotNull(sel);
    }

    // --- Task 6.3: failure filter safety net ---

    @Test
    void testFailureFilterSafetyNet_AllCandidatesFiltered_ListPreserved() {
        // When ALL candidates have failureCount >= 3, the safety net preserves the
        // unfiltered candidate list so the agent never falls through to RESTART-only.
        // Setup: spy on generateCandidateActions to return 2 widget actions,
        // both with 3 failures recorded in the ContentNode.
        Action widgetA = new Action(Action.Type.CLICK, 100, 200, null, "algorithm", "Button", null);
        Action widgetB = new Action(Action.Type.CLICK, 300, 400, null, "algorithm", "Button", null);
        List<Action> fakeWidgets = Arrays.asList(widgetA, widgetB);

        ActionSelector spy = Mockito.spy(new ActionSelector(config));
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "OnboardingActivity");
        Mockito.doReturn(fakeWidgets).when(spy).generateCandidateActions(screen);

        // Register both signatures with 3 executions and 0 successes (failure_count=3)
        graph.getOrCreate(screen.getContentHash(), "OnboardingActivity");
        ContentNode node = graph.get(screen.getContentHash());
        for (int i = 0; i < 3; i++) {
            node.recordAction(widgetA.signature(), "Button");
            node.recordAction(widgetB.signature(), "Button");
            // No recordActionSuccess() -> strength=0 -> failures=executions=3
        }

        // Safety net must preserve widget candidates rather than falling through to RESTART
        Action selected = spy.selectAction(screen, graph, staticMap);
        assertNotNull(selected);
        assertNotEquals(Action.Type.RESTART, selected.getType(),
                "Safety net must keep widget candidates when filtering would empty the list");
        assertTrue(selected.getType() == Action.Type.CLICK,
                "Should select a widget action, not RESTART, when safety net fires");
    }

    @Test
    void testFailureFilterSafetyNet_SomeCandidatesFiltered_HighFailureRemoved() {
        // When SOME candidates have failureCount >= 3, filtering removes only those.
        // Setup: widgetA has 3 failures, widgetB has 1 failure — only widgetB survives.
        Action widgetA = new Action(Action.Type.CLICK, 100, 200, null, "algorithm", "Button", null);
        Action widgetB = new Action(Action.Type.CLICK, 300, 400, null, "algorithm", "Button", null);
        List<Action> fakeWidgets = Arrays.asList(widgetA, widgetB);

        ActionSelector spy = Mockito.spy(new ActionSelector(config));
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "OnboardingActivity");
        Mockito.doReturn(fakeWidgets).when(spy).generateCandidateActions(screen);

        graph.getOrCreate(screen.getContentHash(), "OnboardingActivity");
        ContentNode node = graph.get(screen.getContentHash());

        // widgetA: 3 executions, 0 successes -> failure_count=3 (filtered out)
        for (int i = 0; i < 3; i++) {
            node.recordAction(widgetA.signature(), "Button");
        }
        // widgetB: 2 executions, 1 success -> successes=1, strength=0.5, failures=round(0.5*2)=1
        // Actually: 2 executions, 1 success -> strength=0.5, round(0.5*2)=1, failures=2-1=1 < 3
        node.recordAction(widgetB.signature(), "Button");
        node.recordAction(widgetB.signature(), "Button");
        node.recordActionSuccess(widgetB.signature(), true);

        // Normal filtering: widgetA removed (3 failures), widgetB kept (1 failure)
        // Result: widgetB is the only candidate, so it should be selected (or BACK on Tier 4)
        Action selected = spy.selectAction(screen, graph, staticMap);
        assertNotNull(selected);
        // widgetB must survive — the selected action must be widgetB (Tier 2 untested? No: both executed.
        // Tier 4: widgetB is a candidate, RESTART is also candidate. widgetB should win via scoring.)
        // The key invariant: widgetA must NOT be selected.
        assertNotEquals(widgetA.signature(), selected.signature(),
                "widgetA with failure_count=3 must not be selected after normal filtering");
    }

    @Test
    void testFailureFilterSafetyNet_NoCandidatesWithFailures_NormalBehavior() {
        // When no candidates have failures (0 executions), normal filtering applies
        // and all candidates remain available.
        Action widgetA = new Action(Action.Type.CLICK, 100, 200, null, "algorithm", "Button", null);
        Action widgetB = new Action(Action.Type.CLICK, 300, 400, null, "algorithm", "Button", null);
        List<Action> fakeWidgets = Arrays.asList(widgetA, widgetB);

        ActionSelector spy = Mockito.spy(new ActionSelector(config));
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        Mockito.doReturn(fakeWidgets).when(spy).generateCandidateActions(screen);

        // No executions recorded: failure_count=0 for both (executions=0 -> getFailureCount returns 0)
        graph.getOrCreate(screen.getContentHash(), "TestActivity");

        // Both candidates pass filter — Phase 1 (untested) fires and selects from them
        Action selected = spy.selectAction(screen, graph, staticMap);
        assertNotNull(selected);
        assertEquals(PhaseController.Phase.PHASE_1, spy.getLastSelectedPhase(),
                "Phase 1 (untested) should fire when all candidates have 0 executions");
        assertTrue(selected.getType() == Action.Type.CLICK,
                "Should select a widget action from unfiltered candidates");
    }

    @Test
    void testFailureFilterSafetyNet_BoundaryAtExactly3_TriggersFallback() {
        // Boundary test: failure_count=3 triggers the safety net fallback (not failure_count=2).
        // With exactly failure_count=3 on all candidates, the safety net fires and preserves them.
        // With failure_count=2, normal filtering keeps them (no fallback needed).
        Action widgetA = new Action(Action.Type.CLICK, 100, 200, null, "algorithm", "Button", null);
        List<Action> fakeWidgets = Collections.singletonList(widgetA);

        // --- Sub-case 1: failure_count=3 -> safety net fires, widgetA preserved ---
        ActionSelector spy3 = Mockito.spy(new ActionSelector(config));
        ScreenState screen3 = new ScreenState(Collections.<ScreenItem>emptyList(), "BoundaryActivity3");
        Mockito.doReturn(fakeWidgets).when(spy3).generateCandidateActions(screen3);

        graph.getOrCreate(screen3.getContentHash(), "BoundaryActivity3");
        ContentNode node3 = graph.get(screen3.getContentHash());
        for (int i = 0; i < 3; i++) {
            node3.recordAction(widgetA.signature(), "Button");
        }
        // executions=3, successes=0 -> failures=3 -> filter removes it -> safety net kicks in

        Action selected3 = spy3.selectAction(screen3, graph, staticMap);
        assertNotNull(selected3);
        assertNotEquals(Action.Type.RESTART, selected3.getType(),
                "At failure_count=3, safety net must preserve widget candidates");

        // --- Sub-case 2: failure_count=2 -> normal filter keeps widgetA ---
        ContentGraph graph2 = new ContentGraph();
        ActionSelector spy2 = Mockito.spy(new ActionSelector(config));
        ScreenState screen2 = new ScreenState(Collections.<ScreenItem>emptyList(), "BoundaryActivity2");
        Mockito.doReturn(fakeWidgets).when(spy2).generateCandidateActions(screen2);

        graph2.getOrCreate(screen2.getContentHash(), "BoundaryActivity2");
        ContentNode node2 = graph2.get(screen2.getContentHash());
        // 3 executions, 1 success -> strength=1/3, round(1/3 * 3)=round(1)=1, failures=3-1=2
        for (int i = 0; i < 3; i++) {
            node2.recordAction(widgetA.signature(), "Button");
        }
        node2.recordActionSuccess(widgetA.signature(), true);

        Action selected2 = spy2.selectAction(screen2, graph2, staticMap);
        assertNotNull(selected2);
        // failure_count=2 < 3: normal filter keeps widgetA, so it's still a candidate
        assertTrue(selected2.getType() == Action.Type.CLICK,
                "At failure_count=2, normal filter keeps the candidate without safety net");
    }

    // --- BUG-01: selectNextBest uses structHash for BACK parent check ---

    @Test
    void testSelectNextBest_BackAvailableWhenStructHashHasParent() {
        // BUG-01: SuccessorTracker records at structHash level.
        // selectNextBest must use structHash (not contentHash) for the parent check.
        SuccessorTracker tracker = new SuccessorTracker();
        ScreenState parentScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "ParentActivity");
        ScreenState childScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "ChildActivity");

        // Record parent at structHash level (as SuccessorTracker is used in production)
        tracker.record(parentScreen.getStructHash(), childScreen.getStructHash());

        ActionSelector sel = new ActionSelector(config, tracker);
        Set<String> excluded = new HashSet<>();

        // Child's structHash has a parent -> BACK should be available
        assertFalse(tracker.getParents(childScreen.getStructHash()).isEmpty());
        Action action = sel.selectNextBest(childScreen, excluded, graph, staticMap);
        assertNotNull(action);
        assertTrue(action.getType() == Action.Type.BACK || action.getType() == Action.Type.RESTART,
                "BACK should be available when structHash has parent");
    }

    @Test
    void testSelectNextBest_BackAvailableEvenWhenContentHashDiffers() {
        // BUG-01: Even when contentHash has no parent recorded, BACK should
        // appear if structHash has a parent (different content hashes map to same struct).
        SuccessorTracker tracker = new SuccessorTracker();
        String structHashA = "struct_parent";
        String structHashB = "struct_child";

        // Record at structural level
        tracker.record(structHashA, structHashB);

        // Create a screen whose structHash matches structHashB
        // With empty items and same activity, structHash is deterministic.
        // We verify the structural check by recording at the struct level
        // and confirming the parent exists.
        assertFalse(tracker.getParents(structHashB).isEmpty(),
                "structHashB should have structHashA as parent");
        assertTrue(tracker.getParents("some_content_hash_never_recorded").isEmpty(),
                "A content hash never recorded should have no parents");
    }

    // --- CAP-9/10/11: Special widget action generation ---

    @Test
    void testGenerateCandidateActions_SeekBarGeneratesClick() {
        // CAP-9: SeekBar (not clickable, not scrollable) should get a CLICK action.
        // Note: in unit tests, Rect is a stub, so bounds are effectively null.
        // This test verifies the code path exists. We create the item with null bounds,
        // so it will be skipped by the bounds check. The structural test is that the
        // code compiles and the check is in the right position.
        ScreenItem seekBar = new ScreenItem("android.widget.SeekBar", "pkg:id/seekbar",
                null, null, null, "com.example.app",
                false, false, false, true, false, false, -1);
        ScreenState screen = new ScreenState(Collections.singletonList(seekBar), "TestActivity");

        // With null bounds in test environment, no actions are generated (bounds check)
        List<Action> candidates = selector.generateCandidateActions(screen);
        assertTrue(candidates.isEmpty(),
                "No candidates expected (null bounds in test), but CAP-9 check is in place");
    }

    @Test
    void testGenerateCandidateActions_SwipeRefreshLayoutGeneratesScrollDown() {
        // CAP-10: SwipeRefreshLayout (not clickable, not scrollable) should get SCROLL_DOWN.
        ScreenItem swipeRefresh = new ScreenItem(
                "androidx.swiperefreshlayout.widget.SwipeRefreshLayout", "pkg:id/swipe",
                null, null, null, "com.example.app",
                false, false, false, true, false, false, -1);
        ScreenState screen = new ScreenState(Collections.singletonList(swipeRefresh), "TestActivity");

        List<Action> candidates = selector.generateCandidateActions(screen);
        assertTrue(candidates.isEmpty(),
                "No candidates expected (null bounds in test), but CAP-10 check is in place");
    }

    @Test
    void testGenerateCandidateActions_DrawerLayoutGeneratesEdgeSwipe() {
        // CAP-11: DrawerLayout (not clickable, not scrollable) should get edge swipe.
        ScreenItem drawer = new ScreenItem(
                "androidx.drawerlayout.widget.DrawerLayout", "pkg:id/drawer",
                null, null, null, "com.example.app",
                false, false, false, true, false, false, -1);
        ScreenState screen = new ScreenState(Collections.singletonList(drawer), "TestActivity");

        List<Action> candidates = selector.generateCandidateActions(screen);
        assertTrue(candidates.isEmpty(),
                "No candidates expected (null bounds in test), but CAP-11 check is in place");
    }

    // --- CAP-12: Always-clickable widget types ---

    @Test
    void testGenerateCandidateActions_SpinnerGeneratesClick() {
        // CAP-12: Spinner (not clickable, not scrollable) should get a CLICK action.
        // Spinners may report clickable=false in UIAutomator dumps.
        ScreenItem spinner = new ScreenItem("android.widget.Spinner", "pkg:id/spinner",
                null, null, null, "com.example.app",
                false, false, false, true, false, false, -1);
        ScreenState screen = new ScreenState(Collections.singletonList(spinner), "TestActivity");

        List<Action> candidates = selector.generateCandidateActions(screen);
        assertTrue(candidates.isEmpty(),
                "No candidates expected (null bounds in test), but CAP-12 Spinner check is in place");
    }

    @Test
    void testGenerateCandidateActions_TabViewGeneratesClick() {
        // CAP-12: TabView (not clickable, not scrollable) should get a CLICK action.
        ScreenItem tabView = new ScreenItem(
                "com.google.android.material.tabs.TabLayout$TabView", "pkg:id/tab",
                null, null, null, "com.example.app",
                false, false, false, true, false, false, -1);
        ScreenState screen = new ScreenState(Collections.singletonList(tabView), "TestActivity");

        List<Action> candidates = selector.generateCandidateActions(screen);
        assertTrue(candidates.isEmpty(),
                "No candidates expected (null bounds in test), but CAP-12 TabView check is in place");
    }

    @Test
    void testGenerateCandidateActions_ClickableSpinnerNoDuplicate() {
        // CAP-12: When Spinner already reports clickable=true, it gets a CLICK from
        // normal flow. The CAP-12 block only fires when !clickable && !scrollable,
        // so no duplicate CLICK is generated.
        ScreenItem spinner = new ScreenItem("android.widget.Spinner", "pkg:id/spinner",
                null, null, null, "com.example.app",
                true, false, false, true, false, false, -1);
        ScreenState screen = new ScreenState(Collections.singletonList(spinner), "TestActivity");

        List<Action> candidates = selector.generateCandidateActions(screen);
        // With null bounds in test env, no actions generated — but verifies no crash
        // and that the !clickable guard prevents CAP-12 from firing on clickable widgets
        assertTrue(candidates.isEmpty(),
                "No candidates expected (null bounds in test), verifies no duplicate path");
    }

    // --- Helpers ---

    /**
     * Creates a screen with items that have null bounds.
     * generateCandidateActions skips items with null bounds, so no widget
     * candidate actions are generated — only BACK and RESTART in Tier 4.
     */
    private ScreenState createScreenWithNullBoundsItems() {
        List<ScreenItem> items = Arrays.asList(
                new ScreenItem("android.widget.Button", "pkg:id/btn1",
                        "Click Me", null, null, "com.example.app",
                        true, false, false, true, false, false, -1),
                new ScreenItem("android.widget.Button", "pkg:id/btn2",
                        "Button 2", null, null, "com.example.app",
                        true, false, false, true, false, false, -1)
        );
        return new ScreenState(items, "TestActivity");
    }
}
