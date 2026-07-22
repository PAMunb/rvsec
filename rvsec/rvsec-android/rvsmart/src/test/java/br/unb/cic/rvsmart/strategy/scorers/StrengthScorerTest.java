package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

class StrengthScorerTest {

    private ContentGraph graph;
    private ScreenState screen;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        graph = new ContentGraph();
        screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        staticMap = new StaticMap(null);
    }

    @Test
    void testWeightedSumOfSubScorers() {
        // Two fixed scorers: one always returns 10, another always returns 20
        Scorer fixed10 = (candidate, s, g, sm) -> 10;
        Scorer fixed20 = (candidate, s, g, sm) -> 20;

        StrengthScorer scorer = new StrengthScorer(
                Arrays.asList(fixed10, fixed20),
                Arrays.asList(3, 2));

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        // Expected: 3*10 + 2*20 = 30 + 40 = 70
        assertEquals(70, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testSingleScorer() {
        Scorer fixed50 = (candidate, s, g, sm) -> 50;
        StrengthScorer scorer = new StrengthScorer(
                Collections.singletonList(fixed50),
                Collections.singletonList(4));

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(200, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testMismatchedSizesThrowsException() {
        Scorer fixed10 = (candidate, s, g, sm) -> 10;
        assertThrows(IllegalArgumentException.class, () ->
                new StrengthScorer(
                        Collections.singletonList(fixed10),
                        Arrays.asList(1, 2)));
    }

    @Test
    void testNegativeWeightsWork() {
        Scorer fixed100 = (candidate, s, g, sm) -> 100;
        StrengthScorer scorer = new StrengthScorer(
                Collections.singletonList(fixed100),
                Collections.singletonList(-1));

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(-100, scorer.score(action, screen, graph, staticMap));
    }
}
