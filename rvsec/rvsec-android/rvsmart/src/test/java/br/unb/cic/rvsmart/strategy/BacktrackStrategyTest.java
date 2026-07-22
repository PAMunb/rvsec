package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.graph.NavigationMap;
import br.unb.cic.rvsmart.graph.StructuralGraph;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for BacktrackStrategy — two-stage backtracking plan builder.
 */
class BacktrackStrategyTest {

    private NavigationMap navigationMap;
    private StructuralGraph structuralGraph;
    private BacktrackStrategy strategy;

    @BeforeEach
    void setUp() {
        navigationMap = new NavigationMap();
        structuralGraph = new StructuralGraph();
        strategy = new BacktrackStrategy(navigationMap, structuralGraph);
    }

    @Test
    void testPlanBacktrack_ReturnsBACKMarkerAsFirstStep() {
        List<String> plan = strategy.planBacktrack("structA", "structB");
        assertNotNull(plan);
        assertFalse(plan.isEmpty());
        assertEquals(BacktrackStrategy.BACK_MARKER, plan.get(0),
                "planBacktrack must return BACK as the first (and only) element");
    }

    @Test
    void testPlanReplay_ReturnsPathFromNavigationMap() {
        navigationMap.record("structA", "click_btn", "structB");
        navigationMap.record("structB", "click_next", "structC");

        List<String> replay = strategy.planReplay("structA", "structC");
        assertNotNull(replay);
        assertEquals(2, replay.size());
        assertEquals("click_btn", replay.get(0));
        assertEquals("click_next", replay.get(1));
    }

    @Test
    void testCanReach_FalseWhenNoPath() {
        // Nothing recorded — no path exists
        assertFalse(strategy.canReach("structA", "structB"));
    }

    @Test
    void testCanReach_TrueWhenPathExists() {
        navigationMap.record("structA", "action1", "structB");
        assertTrue(strategy.canReach("structA", "structB"));
    }

    @Test
    void testReplayCount_IncrementsOnNonEmptyReplay() {
        assertEquals(0, strategy.getReplayCount());

        // No path — count stays 0
        strategy.planReplay("structA", "structZ");
        assertEquals(0, strategy.getReplayCount());

        // Path exists — count increments
        navigationMap.record("structA", "click", "structB");
        strategy.planReplay("structA", "structB");
        assertEquals(1, strategy.getReplayCount());

        strategy.planReplay("structA", "structB");
        assertEquals(2, strategy.getReplayCount());
    }
}
