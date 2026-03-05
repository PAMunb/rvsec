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

class ComponentPriorityScorerTest {

    private ComponentPriorityScorer scorer;
    private DynamicStateGraph graph;
    private ScreenState screen;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        scorer = new ComponentPriorityScorer();
        graph = new DynamicStateGraph();
        screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        staticMap = new StaticMap(null);
    }

    @Test
    void testSetTextGetsHighestScore() {
        Action action = new Action(Action.Type.SET_TEXT, 100, 200, "test", "algorithm", "EditText");
        assertEquals(200, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testClickGetsMediumScore() {
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(100, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testLongClickGetsMediumScore() {
        Action action = new Action(Action.Type.LONG_CLICK, 100, 200, "algorithm", "Button");
        assertEquals(100, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testScrollGetsLowScore() {
        Action action = new Action(Action.Type.SCROLL, 100, 200, "algorithm", "RecyclerView");
        assertEquals(25, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testSwipeGetsLowScore() {
        Action action = new Action(Action.Type.SWIPE, 100, 200, "algorithm", "View");
        assertEquals(25, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testBackGetsZeroScore() {
        Action action = Action.back("algorithm");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testRestartGetsZeroScore() {
        Action action = Action.restart("algorithm");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }
}
