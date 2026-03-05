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

class WtgScorerTest {

    private WtgScorer scorer;
    private DynamicStateGraph graph;
    private ScreenState screen;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        scorer = new WtgScorer(400);
        graph = new DynamicStateGraph();
        screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
    }

    @Test
    void testReturnsZeroWhenStaticMapIsNull() {
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroWhenStaticMapNotLoaded() {
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroWhenWtgDataNotParsed() {
        // Current StaticMap does not expose WTG transition lookups yet
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.CLICK, 50, 60, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }
}
