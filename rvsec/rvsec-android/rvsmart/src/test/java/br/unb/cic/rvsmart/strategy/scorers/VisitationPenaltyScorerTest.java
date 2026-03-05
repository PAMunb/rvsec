package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

class VisitationPenaltyScorerTest {

    private VisitationPenaltyScorer scorer;
    private DynamicStateGraph graph;
    private ScreenState screen;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        scorer = new VisitationPenaltyScorer(15);
        graph = new DynamicStateGraph();
        screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        staticMap = new StaticMap(null);
    }

    @Test
    void testReturnsZeroForUnvisitedScreen() {
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroForUnexecutedAction() {
        // Screen node exists but action was never executed
        graph.recordVisit(screen.getHash(), "TestActivity");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsPenaltyProportionalToVisits() {
        String hash = screen.getHash();
        graph.getOrCreate(hash, "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        String sig = action.signature();

        // Record 3 executions of this action
        graph.recordAction(hash, sig, "Button");
        graph.recordAction(hash, sig, "Button");
        graph.recordAction(hash, sig, "Button");

        // Expected: -(3 * 15) = -45
        assertEquals(-45, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testPenaltyScalesWithExecutionCount() {
        String hash = screen.getHash();
        graph.getOrCreate(hash, "TestActivity");

        Action action = new Action(Action.Type.CLICK, 200, 300, "algorithm", "TextView");
        String sig = action.signature();

        graph.recordAction(hash, sig, "TextView");
        graph.recordAction(hash, sig, "TextView");

        // Expected: -(2 * 15) = -30
        assertEquals(-30, scorer.score(action, screen, graph, staticMap));
    }
}
