package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class ConfirmedCoverageScorerTest {

    private ConfirmedCoverageScorer scorer;
    private ContentGraph graph;
    private ScreenState screen;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        scorer = new ConfirmedCoverageScorer(150);
        graph = new ContentGraph();
        screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        staticMap = new StaticMap(null);
    }

    @Test
    void testReturnsZeroWithNoConfirmedHashes() {
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsFullScoreOnFirstVisit() {
        // visitCount=0 (not in graph) → revisits=0 → score = 150/(1+0) = 150
        Set<String> methods = new HashSet<>();
        methods.add("javax.crypto.Cipher.getInstance");
        scorer.addConfirmed(screen.getContentHash(), methods);

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(150, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testDecayAtRevisit1() {
        // visitCount=2 → revisits=1 → score = 150/(1+1) = 75
        Set<String> methods = new HashSet<>();
        methods.add("javax.crypto.Cipher.getInstance");
        scorer.addConfirmed(screen.getContentHash(), methods);

        graph.getOrCreate(screen.getContentHash(), "TestActivity");
        graph.recordVisit(screen.getContentHash(), "TestActivity");
        graph.recordVisit(screen.getContentHash(), "TestActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(75, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testDecayAtRevisit5() {
        // visitCount=6 → revisits=5 → score = 150/(1+5) = 25
        Set<String> methods = new HashSet<>();
        methods.add("javax.crypto.Cipher.getInstance");
        scorer.addConfirmed(screen.getContentHash(), methods);

        graph.getOrCreate(screen.getContentHash(), "TestActivity");
        for (int i = 0; i < 6; i++) {
            graph.recordVisit(screen.getContentHash(), "TestActivity");
        }

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(25, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testHasConfirmedReturnsFalseWhenEmpty() {
        assertFalse(scorer.hasConfirmed("unknown_hash"));
    }

    @Test
    void testHasConfirmedReturnsTrueAfterAddConfirmed() {
        Set<String> methods = new HashSet<>();
        methods.add("javax.crypto.Cipher.init");
        scorer.addConfirmed("some_hash", methods);
        assertTrue(scorer.hasConfirmed("some_hash"));
    }

    @Test
    void testAddConfirmedAccumulatesMethods() {
        Set<String> methods1 = new HashSet<>();
        methods1.add("method.A");
        Set<String> methods2 = new HashSet<>();
        methods2.add("method.B");

        scorer.addConfirmed(screen.getContentHash(), methods1);
        scorer.addConfirmed(screen.getContentHash(), methods2);

        assertTrue(scorer.hasConfirmed(screen.getContentHash()));
    }

    @Test
    void testAddConfirmedIgnoresNullOrEmptyMethods() {
        scorer.addConfirmed(screen.getContentHash(), null);
        scorer.addConfirmed(screen.getContentHash(), Collections.emptySet());
        assertFalse(scorer.hasConfirmed(screen.getContentHash()));
    }

    @Test
    void testDifferentHashesAreIndependent() {
        Set<String> methods = new HashSet<>();
        methods.add("method.X");
        scorer.addConfirmed("hash_A", methods);

        ScreenState otherScreen = new ScreenState(
                Collections.singletonList(
                        new ScreenItem("android.widget.Button", "id/btn", "X", null, null,
                                "com.example", true, false, false, true, false, false, -1)),
                "OtherActivity");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, otherScreen, graph, staticMap));
    }
}
