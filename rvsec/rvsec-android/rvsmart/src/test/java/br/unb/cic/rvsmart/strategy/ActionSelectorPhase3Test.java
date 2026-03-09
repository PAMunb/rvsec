package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.PhaseController.Phase;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ActionSelector Phase 3 (stochastic exploration).
 *
 * Phase 3 uses the unified priority queue (all widgets + BACK + RESTART) with stochastic
 * probability boosted to 0.5 (PHASE3_STOCHASTIC_PROBABILITY), escaping local optima.
 */
class ActionSelectorPhase3Test {

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
     * Phase 3 never returns null (INV-RSM-12) — RESTART is always in the unified queue.
     */
    @Test
    void testPhase3NeverReturnsNull() {
        ActionSelector selector = new ActionSelector(config);
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "MainActivity");

        Action selected = selector.selectAction(Phase.PHASE_3, screen, screen.getStructHash(),
                contentGraph, null, null, null, staticMap);

        assertNotNull(selected, "selectAction must never return null in Phase 3 (INV-RSM-12)");
        assertEquals(Phase.PHASE_3, selector.getLastSelectedPhase(),
                "lastSelectedPhase must be PHASE_3");
    }

    /**
     * Phase 3 with no widget candidates (null bounds in test environment) returns
     * RESTART — the guaranteed fallback when BACK is excluded on root screens.
     */
    @Test
    void testPhase3ReturnsRestartOnRootScreenWithNoWidgets() {
        // No SuccessorTracker → root screen → BACK excluded
        ActionSelector selector = new ActionSelector(config);
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "RootActivity");

        // Run multiple times to exercise stochastic path (seed=42 ensures determinism)
        for (int i = 0; i < 10; i++) {
            Action selected = selector.selectAction(Phase.PHASE_3, screen, screen.getStructHash(),
                    contentGraph, null, null, null, staticMap);
            assertNotNull(selected);
            assertEquals(Action.Type.RESTART, selected.getType(),
                    "Phase 3 on root screen with no widgets must return RESTART");
        }
    }
}
