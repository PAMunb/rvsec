package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.NavigationMap;
import br.unb.cic.rvsmart.graph.StructuralGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.PhaseController.Phase;
import br.unb.cic.rvsmart.strategy.scorers.ConfirmedCoverageScorer;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ActionSelector Phase 1 (DFS / broad exploration).
 *
 * Phase 1 returns untested actions from the current content state via the scoring chain.
 * When the current node is exhausted and no untested cluster is reachable via NavigationMap,
 * it falls back to Phase 3 (stochastic unified queue).
 */
class ActionSelectorPhase1Test {

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
     * Phase 1 returns an untested action when the content node has unexecuted actions.
     * Uses a Mockito spy to inject widget candidates (Rect is a stub in unit tests).
     */
    @Test
    void testPhase1ReturnsUntestedAction_WhenUntestedCandidatesExist() {
        ActionSelector selector = new ActionSelector(config);
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "MainActivity");

        // Inject a fake widget candidate via spy
        Action widget = new Action(Action.Type.CLICK, 100, 200, null, "algorithm", "Button", null);
        ActionSelector spy = Mockito.spy(selector);
        Mockito.doReturn(Collections.singletonList(widget))
                .when(spy).generateCandidateActions(screen);

        // Content node exists but has no execution records — widget is untested
        contentGraph.getOrCreate(screen.getContentHash(), "MainActivity");

        Action selected = spy.selectAction(Phase.PHASE_1, screen, screen.getStructHash(),
                contentGraph, null, null, null, staticMap);

        assertNotNull(selected);
        assertEquals(Action.Type.CLICK, selected.getType(),
                "Phase 1 should return the untested widget action");
        assertEquals(Phase.PHASE_1, spy.getLastSelectedPhase(),
                "lastSelectedPhase must reflect PHASE_1");
    }

    /**
     * Phase 1 falls back to Phase 3 when the content node is exhausted and
     * no NavigationMap path leads to an untested cluster.
     * Result must be non-null (INV-RSM-12) and phase must be set.
     */
    @Test
    void testPhase1FallsBackToPhase3_WhenExhaustedAndNoPath() {
        ActionSelector selector = new ActionSelector(config);
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "MainActivity");

        // Register the content node and mark all actions as executed (exhausted)
        contentGraph.getOrCreate(screen.getContentHash(), "MainActivity");
        contentGraph.get(screen.getContentHash()).setTotalActions(2);
        contentGraph.get(screen.getContentHash()).recordAction("click@100,200", "Button");
        contentGraph.get(screen.getContentHash()).recordAction("click@300,400", "Button");

        // Empty NavigationMap — no paths to any cluster
        NavigationMap emptyNav = new NavigationMap();
        StructuralGraph structGraph = new StructuralGraph();
        structGraph.register(screen.getStructHash(), screen.getContentHash());

        Action selected = selector.selectAction(Phase.PHASE_1, screen, screen.getStructHash(),
                contentGraph, structGraph, emptyNav, null, staticMap);

        assertNotNull(selected, "selectAction must never return null (INV-RSM-12)");
        // Phase falls back to PHASE_3 since no untested candidates and no nav path
        assertEquals(Phase.PHASE_3, selector.getLastSelectedPhase(),
                "Should fall back to PHASE_3 when exhausted and no nav path");
    }
}
