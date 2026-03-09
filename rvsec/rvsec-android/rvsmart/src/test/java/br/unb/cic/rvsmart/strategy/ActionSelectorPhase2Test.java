package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.core.UICoverageTracker;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.graph.NavigationMap;
import br.unb.cic.rvsmart.graph.StructuralGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.PhaseController.Phase;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ActionSelector Phase 2 (coverage-guided exploration).
 *
 * Phase 2 targets UI coverage gaps. When a reachable cluster with coverage gap >
 * uiCoverageThreshold exists in NavigationMap, the selector navigates toward it.
 * If no such target exists or no path is found, Phase 2 falls back to Phase 1.
 */
class ActionSelectorPhase2Test {

    private Config config;
    private ContentGraph contentGraph;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        config = Config.defaults();
        config.setSeed(42);
        contentGraph = new ContentGraph();
        staticMap = new StaticMap(null);
    }

    /**
     * Phase 2 with null uiCoverageTracker falls back to Phase 1 behavior.
     * Result must be non-null (INV-RSM-12).
     */
    @Test
    void testPhase2FallsBackToPhase1_WhenNullTracker() {
        ActionSelector selector = new ActionSelector(config);
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "MainActivity");

        NavigationMap nav = new NavigationMap();
        StructuralGraph structGraph = new StructuralGraph();
        structGraph.register(screen.getStructHash(), screen.getContentHash());

        Action selected = selector.selectAction(Phase.PHASE_2, screen, screen.getStructHash(),
                contentGraph, structGraph, nav, null /* null tracker */, staticMap);

        assertNotNull(selected, "selectAction must never return null (INV-RSM-12)");
        // null tracker → falls back to Phase 1 → empty candidates → Phase 3 stochastic
        assertNotNull(selector.getLastSelectedPhase());
    }

    /**
     * Phase 2 navigates toward a reachable high-gap cluster via NavigationMap.
     * When a target cluster is found and a path exists, the selected action comes
     * from the first step on that path (reconstructed from the signature).
     */
    @Test
    void testPhase2NavigatesToHighGapCluster_WhenPathExists() {
        ActionSelector selector = new ActionSelector(config);

        // Current screen
        ScreenState currentScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "MainActivity");
        String currentStruct = currentScreen.getStructHash();

        // Target screen in a different structural cluster
        ScreenState targetScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TargetActivity");
        String targetStruct = targetScreen.getStructHash();

        // Register both in structural graph (different clusters since different activities)
        StructuralGraph structGraph = new StructuralGraph();
        structGraph.register(currentStruct, currentScreen.getContentHash());
        structGraph.register(targetStruct, targetScreen.getContentHash());

        // Add content nodes so the target has untested actions
        contentGraph.getOrCreate(currentScreen.getContentHash(), "MainActivity");
        contentGraph.getOrCreate(targetScreen.getContentHash(), "TargetActivity");

        // Wire a NavigationMap path: currentStruct → targetStruct via "click@540,960"
        NavigationMap nav = new NavigationMap();
        nav.record(currentStruct, "click@540,960", targetStruct);

        // UICoverageTracker with high gap on target screen (1.0 = fully unexplored)
        // Default ui_coverage_threshold = 0.8, so 1.0 > 0.8 → target qualifies
        UICoverageTracker tracker = new UICoverageTracker();
        // No interactions recorded on targetScreen → getCoverageGap returns 1.0

        // Verify path exists before calling selectAction
        assertTrue(nav.hasPath(currentStruct, targetStruct),
                "NavigationMap must have path from current to target");

        Action selected = selector.selectAction(Phase.PHASE_2, currentScreen, currentStruct,
                contentGraph, structGraph, nav, tracker, staticMap);

        assertNotNull(selected, "selectAction must never return null (INV-RSM-12)");
        assertEquals(Phase.PHASE_2, selector.getLastSelectedPhase(),
                "Phase 2 should be selected when a high-gap cluster is reachable");
        // The action should correspond to the first step "click@540,960"
        assertEquals(Action.Type.CLICK, selected.getType(),
                "First nav step (click@540,960) should produce a CLICK action");
    }
}
