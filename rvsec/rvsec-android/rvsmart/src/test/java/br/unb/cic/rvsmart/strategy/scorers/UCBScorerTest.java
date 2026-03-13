package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for UCBScorer -- UCB exploration bonus: C * sqrt(ln(N_state) / N_action).
 * Uses ContentGraph directly (no mocking framework needed).
 */
class UCBScorerTest {

    private static final float C = 150.0f;
    private final UCBScorer scorer = new UCBScorer(C);
    private final ScreenState screen = new ScreenState(
            Collections.<ScreenItem>emptyList(), "TestActivity");

    @Test
    void neverVisitedAction_getsCappedMaxBonus() {
        // N_action=0, N_state=10 -> returns (int)(150 * sqrt(ln(10))) = 227
        ContentGraph graph = new ContentGraph();
        ContentNode node = graph.getOrCreate(screen.getContentHash(), "TestActivity");
        // Set visitCount to 10
        for (int i = 0; i < 10; i++) {
            node.incrementVisitCount();
        }

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        int expected = (int) (C * Math.sqrt(Math.log(10)));
        assertEquals(expected, scorer.score(action, screen, graph, null));
        assertEquals(227, expected); // Verify the known value
    }

    @Test
    void visitedAction_getsDecayingBonus() {
        // C=150, N_state=10, N_action=2 -> returns (int)(150 * sqrt(ln(10)/2)) = 160
        ContentGraph graph = new ContentGraph();
        ContentNode node = graph.getOrCreate(screen.getContentHash(), "TestActivity");
        for (int i = 0; i < 10; i++) {
            node.incrementVisitCount();
        }

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        // Execute twice
        node.recordAction(action.signature(), "Button");
        node.recordAction(action.signature(), "Button");

        int expected = (int) (C * Math.sqrt(Math.log(10) / 2));
        assertEquals(expected, scorer.score(action, screen, graph, null));
        assertEquals(160, expected); // Verify the known value
    }

    @Test
    void nullContentNode_returnsZero() {
        // graph returns null for the hash -> 0
        ContentGraph graph = new ContentGraph();
        // Do NOT create a node for this screen's content hash

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, null));
    }

    @Test
    void nStateZero_returnsZero() {
        // ContentNode with visitCount=0 -> 0
        ContentGraph graph = new ContentGraph();
        // getOrCreate creates the node but visitCount stays 0
        graph.getOrCreate(screen.getContentHash(), "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, null));
    }

    @Test
    void formulaCorrectnessWithKnownValues() {
        // C=150, N_state=100, N_action=5 -> (int)(150 * sqrt(ln(100)/5)) = 143
        ContentGraph graph = new ContentGraph();
        ContentNode node = graph.getOrCreate(screen.getContentHash(), "TestActivity");
        for (int i = 0; i < 100; i++) {
            node.incrementVisitCount();
        }

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        // Execute 5 times
        for (int i = 0; i < 5; i++) {
            node.recordAction(action.signature(), "Button");
        }

        int expected = (int) (C * Math.sqrt(Math.log(100) / 5));
        assertEquals(expected, scorer.score(action, screen, graph, null));
        assertEquals(143, expected); // Verify the known value
    }
}
