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

class SaturationScorerTest {

    private SaturationScorer scorer;
    private DynamicStateGraph graph;
    private ScreenState screen;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        scorer = new SaturationScorer(20, 10);
        graph = new DynamicStateGraph();
        screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        staticMap = new StaticMap(null);
    }

    @Test
    void testReturnsZeroForUnvisitedScreen() {
        // No node in graph yet
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroWhenBelowThreshold() {
        // Visit the screen 5 times — below threshold of 20
        String hash = screen.getHash();
        for (int i = 0; i < 5; i++) {
            graph.recordVisit(hash, "TestActivity");
        }
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsPenaltyWhenAboveThreshold() {
        // Visit the screen 25 times — 5 above threshold of 20
        String hash = screen.getHash();
        for (int i = 0; i < 25; i++) {
            graph.recordVisit(hash, "TestActivity");
        }
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        // penalty = -(25 - 20) * 10 = -50
        assertEquals(-50, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroAtExactThreshold() {
        String hash = screen.getHash();
        for (int i = 0; i < 20; i++) {
            graph.recordVisit(hash, "TestActivity");
        }
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }
}
