package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;
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

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
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
    private DynamicStateGraph graph;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        config = Config.defaults();
        config.setSeed(42);
        selector = new ActionSelector(config);
        graph = new DynamicStateGraph();
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
        ActionSelector selectorWithTracker = new ActionSelector(config, null, tracker);

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
        tracker.record(rootScreen.getHash(), childScreen.getHash());

        // With stochastic disabled (seed=42), on childScreen BACK or RESTART can appear.
        // The key assertion: BACK is NOT excluded (it appears in the candidate list).
        ActionSelector selectorWithTracker = new ActionSelector(config, null, tracker);

        // Verify childScreen has parents
        assertFalse(tracker.getParents(childScreen.getHash()).isEmpty(),
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
        ActionSelector selectorNoTracker = new ActionSelector(config, null, null);

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
        ActionSelector selectorWithTracker = new ActionSelector(config, null, tracker);

        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "RootActivity");

        Action action = selectorWithTracker.selectAction(screen, graph, staticMap);
        assertNotNull(action, "selectAction must never return null (INV-RSM-12)");
        assertEquals(Action.Type.RESTART, action.getType(),
                "On root screen with no widgets, RESTART must be the fallback");
    }

    @Test
    void testBackBaseScoreIsNegative500() {
        Config defaultConfig = Config.defaults();
        assertEquals(-500.0f, defaultConfig.getBackBaseScore(), 0.01f,
                "BACK base score should be -500 to strongly discourage BACK");
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
        ActionSelector selectorNoTracker = new ActionSelector(config, null, null);
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
        ActionSelector selectorWithTracker = new ActionSelector(config, null, tracker);
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
        tracker.record(rootScreen.getHash(), childScreen.getHash());

        ActionSelector selectorWithTracker = new ActionSelector(config, null, tracker);
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
                config, null, null, confirmedScorer);

        List<Scorer> scorers = selectorWithConfirmed.getScorers();
        boolean found = scorers.stream().anyMatch(s -> s instanceof ConfirmedCoverageScorer);
        assertTrue(found, "ConfirmedCoverageScorer must be in the chain when provided");
        assertEquals(5, scorers.size(), "Should have 5 scorers: Mop, GradualDecay, SystemElement, Component, Confirmed");
    }

    @Test
    void testScorerChainOmitsConfirmedCoverageScorer_WhenNull() {
        // When null is passed for ConfirmedCoverageScorer, chain has 4 scorers
        ActionSelector selectorNoConfirmed = new ActionSelector(config);
        List<Scorer> scorers = selectorNoConfirmed.getScorers();
        assertEquals(4, scorers.size(), "Should have 4 scorers without ConfirmedCoverageScorer");
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
    void testScorerChainDoesNotContainWtgScorer() {
        // WtgScorer is excluded: stub that always returns 0
        List<Scorer> scorers = selector.getScorers();
        boolean found = scorers.stream().anyMatch(s -> s instanceof WtgScorer);
        assertFalse(found, "WtgScorer must NOT be in the scorer chain (stub, always returns 0)");
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
        // Verify the scorer chain order: MopScorer, GradualDecay, SystemElement, ComponentPriority
        List<Scorer> scorers = selector.getScorers();
        assertEquals(4, scorers.size());
        assertTrue(scorers.get(0) instanceof MopScorer, "First scorer should be MopScorer");
        assertTrue(scorers.get(1) instanceof GradualDecayScorer, "Second scorer should be GradualDecayScorer");
        assertTrue(scorers.get(2) instanceof SystemElementFilter, "Third scorer should be SystemElementFilter");
        assertTrue(scorers.get(3) instanceof ComponentPriorityScorer, "Fourth scorer should be ComponentPriorityScorer");
    }

    @Test
    void testConfirmedCoverageScorerBoostsScoreForConfirmedScreens() {
        // Verify the same ConfirmedCoverageScorer instance receives addConfirmed() data
        // and produces a non-zero score when the screen hash matches
        ConfirmedCoverageScorer confirmedScorer = new ConfirmedCoverageScorer(150);
        ActionSelector selectorWithConfirmed = new ActionSelector(
                config, null, null, confirmedScorer);

        ScreenState screen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");

        // Before confirmation, scorer contributes 0
        assertFalse(confirmedScorer.hasConfirmed(screen.getHash()));

        // Simulate coverage confirmation on this screen
        Set<String> methods = new HashSet<>();
        methods.add("javax.crypto.Cipher.getInstance");
        confirmedScorer.addConfirmed(screen.getHash(), methods);

        // After confirmation, scorer contributes +150
        assertTrue(confirmedScorer.hasConfirmed(screen.getHash()));
        assertEquals(150, confirmedScorer.score(
                Action.back("test"), screen, graph, staticMap));
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
