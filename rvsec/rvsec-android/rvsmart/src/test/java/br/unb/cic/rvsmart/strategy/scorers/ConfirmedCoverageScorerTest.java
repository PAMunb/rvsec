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
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class ConfirmedCoverageScorerTest {

    private ConfirmedCoverageScorer scorer;
    private DynamicStateGraph graph;
    private ScreenState screen;
    private StaticMap staticMap;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        scorer = new ConfirmedCoverageScorer(350);
        graph = new DynamicStateGraph();
        screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        staticMap = new StaticMap(null);
    }

    @Test
    void testReturnsZeroWithNoConfirmedHashes() {
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsConfirmedBaseForConfirmedScreen() {
        Set<String> methods = new HashSet<>();
        methods.add("javax.crypto.Cipher.getInstance");

        scorer.addConfirmed(screen.getHash(), methods);

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(350, scorer.score(action, screen, graph, staticMap));
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

        scorer.addConfirmed(screen.getHash(), methods1);
        scorer.addConfirmed(screen.getHash(), methods2);

        assertTrue(scorer.hasConfirmed(screen.getHash()));
        // Still confirms (both methods now tracked for the hash)
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(350, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testAddConfirmedIgnoresNullOrEmptyMethods() {
        scorer.addConfirmed(screen.getHash(), null);
        scorer.addConfirmed(screen.getHash(), Collections.emptySet());
        assertFalse(scorer.hasConfirmed(screen.getHash()));
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
        // otherScreen has a different hash — should score 0
        assertEquals(0, scorer.score(action, otherScreen, graph, staticMap));
    }
}
