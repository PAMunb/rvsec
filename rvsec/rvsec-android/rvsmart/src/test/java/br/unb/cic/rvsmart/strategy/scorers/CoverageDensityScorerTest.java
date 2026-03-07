package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.core.UICoverageTracker;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

class CoverageDensityScorerTest {

    private UICoverageTracker tracker;
    private DynamicStateGraph graph;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        tracker = new UICoverageTracker();
        graph = new DynamicStateGraph();
    }

    @Test
    void testReturnsFullWeightForUnknownScreen() {
        // Unknown screen hash -> coverageGap = 1.0 -> score = weight
        CoverageDensityScorer scorer = new CoverageDensityScorer(100, tracker);
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "Unknown");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(100, scorer.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroWhenAllElementsInteracted() {
        // All elements interacted -> coverageGap = 0.0 -> score = 0
        CoverageDensityScorer scorer = new CoverageDensityScorer(100, tracker);

        ScreenItem item = new ScreenItem("Button", "pkg:id/btn1", null, null, null,
                "com.example", true, false, false, true, false, false, 0);
        ScreenState screen = new ScreenState(Collections.singletonList(item), "TestActivity");

        tracker.registerScreenElements(screen.getHash(), screen.getItems());
        tracker.recordInteraction(screen.getHash(), "res:pkg:id/btn1");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, null));
    }

    @Test
    void testReturnsHalfWeightWhenHalfInteracted() {
        // 1 of 2 elements interacted -> coverageGap = 0.5 -> score = 50
        CoverageDensityScorer scorer = new CoverageDensityScorer(100, tracker);

        ScreenItem item1 = new ScreenItem("Button", "pkg:id/btn1", null, null, null,
                "com.example", true, false, false, true, false, false, 0);
        ScreenItem item2 = new ScreenItem("Button", "pkg:id/btn2", null, null, null,
                "com.example", true, false, false, true, false, false, 0);
        ScreenState screen = new ScreenState(Arrays.asList(item1, item2), "TestActivity");

        tracker.registerScreenElements(screen.getHash(), screen.getItems());
        tracker.recordInteraction(screen.getHash(), "res:pkg:id/btn1");

        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(50, scorer.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroWhenTrackerIsNull() {
        // Null tracker -> graceful degradation
        CoverageDensityScorer scorer = new CoverageDensityScorer(100, null);
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, null));
    }

    @Test
    void testLegacyConstructorReturnsZero() {
        // Legacy constructor (no tracker) -> returns 0 always
        CoverageDensityScorer scorer = new CoverageDensityScorer(100);
        ScreenState screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, null));
    }
}
