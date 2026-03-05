package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.graph.ScreenNode;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for GradualDecayScorer — exponential decay based on visit count.
 * Formula: visits >= minVisits -> 0; else base * (decayRate ^ visits).
 */
class GradualDecayScorerTest {

    // Default: base=200, decayRate=0.7, minVisits=5
    private final GradualDecayScorer scorer = new GradualDecayScorer(200, 0.7, 5);
    private final ScreenState screen = new ScreenState(
            Collections.<ScreenItem>emptyList(), "TestActivity");

    @Test
    void testFullBaseScoreForNeverVisitedAction() {
        DynamicStateGraph graph = new DynamicStateGraph();
        // Node exists but action never executed (visits=0)
        graph.getOrCreate(screen.getHash(), "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        // 200 * 0.7^0 = 200 * 1.0 = 200
        assertEquals(200, scorer.score(action, screen, graph, null));
    }

    @Test
    void testExponentialDecayVisits1() {
        DynamicStateGraph graph = new DynamicStateGraph();
        ScreenNode node = graph.getOrCreate(screen.getHash(), "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        // Execute once
        node.recordAction(action.signature(), "Button");

        // 200 * 0.7^1 = 140
        assertEquals(140, scorer.score(action, screen, graph, null));
    }

    @Test
    void testExponentialDecayVisits2() {
        DynamicStateGraph graph = new DynamicStateGraph();
        ScreenNode node = graph.getOrCreate(screen.getHash(), "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        // Execute twice
        node.recordAction(action.signature(), "Button");
        node.recordAction(action.signature(), "Button");

        // 200 * 0.7^2 = 200 * 0.49 = 98.0, truncated via (int) cast
        int expected = (int) (200 * Math.pow(0.7, 2));
        assertEquals(expected, scorer.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroWhenVisitsAtMinVisits() {
        DynamicStateGraph graph = new DynamicStateGraph();
        ScreenNode node = graph.getOrCreate(screen.getHash(), "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        // Execute 5 times (minVisits=5)
        for (int i = 0; i < 5; i++) {
            node.recordAction(action.signature(), "Button");
        }

        assertEquals(0, scorer.score(action, screen, graph, null));
    }

    @Test
    void testReturnsBaseWhenGraphNodeIsNull() {
        DynamicStateGraph graph = new DynamicStateGraph();
        // graph.get(hash) returns null for unvisited screens

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(200, scorer.score(action, screen, graph, null));
    }

    @Test
    void testScoreNeverGoesBelowZero() {
        // The decay formula (base * decayRate^visits) uses 0 < decayRate < 1,
        // so the result is always >= 0. Visits >= minVisits returns 0 explicitly.
        // Verify no negative scores across many visit counts.
        DynamicStateGraph graph = new DynamicStateGraph();
        ScreenNode node = graph.getOrCreate(screen.getHash(), "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        for (int i = 0; i < 100; i++) {
            int score = scorer.score(action, screen, graph, null);
            assertTrue(score >= 0,
                    "GradualDecayScorer must never return negative score, got " + score
                    + " at visit " + i);
            node.recordAction(action.signature(), "Button");
        }
    }

    @Test
    void testCustomConstructorValues() {
        GradualDecayScorer custom = new GradualDecayScorer(400, 0.5, 3);
        DynamicStateGraph graph = new DynamicStateGraph();
        ScreenNode node = graph.getOrCreate(screen.getHash(), "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        node.recordAction(action.signature(), "Button");

        // 400 * 0.5^1 = 200
        assertEquals(200, custom.score(action, screen, graph, null));

        // At minVisits=3
        node.recordAction(action.signature(), "Button");
        node.recordAction(action.signature(), "Button");
        assertEquals(0, custom.score(action, screen, graph, null));
    }
}
