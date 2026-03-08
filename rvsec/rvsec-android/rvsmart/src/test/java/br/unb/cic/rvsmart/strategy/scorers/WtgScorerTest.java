package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

class WtgScorerTest {

    private WtgScorer scorer;
    private DynamicStateGraph graph;
    private ScreenState screen;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        scorer = new WtgScorer();
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
    void testReturnsZeroForScrollAction() {
        // SCROLL actions should not receive WTG boost
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.SCROLL, 50, 60, "down", "algorithm", "ListView");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroForBackAction() {
        StaticMap staticMap = new StaticMap(null);
        Action action = Action.back("algorithm");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroForRestartAction() {
        StaticMap staticMap = new StaticMap(null);
        Action action = Action.restart("algorithm");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroForSetTextAction() {
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.SET_TEXT, 50, 60, "text", "algorithm", "EditText");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroWhenActivityIsNull() {
        // Screen with null activity
        ScreenState nullActivityScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), null);
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, nullActivityScreen, graph, staticMap));
    }

    @Test
    void testReturnsZeroWhenActivityIsEmpty() {
        ScreenState emptyActivityScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "");
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, emptyActivityScreen, graph, staticMap));
    }

    // --- BFS logic tests (using bfsBoost directly) ---

    @Test
    void testBfsBoostReturnsZeroWithNoTransitions() {
        // StaticMap not loaded returns empty transitions
        StaticMap staticMap = new StaticMap(null);
        assertEquals(0, scorer.bfsBoost("MainActivity", graph, staticMap));
    }

    @Test
    void testBfsBoostReturnsZeroWhenAllTargetsVisited() {
        // Even if transitions exist, if all targets are visited, boost is 0.
        // This test uses StaticMap(null) which is not loaded, so getTransitions
        // returns empty. A more complete test would need a loaded StaticMap.
        StaticMap staticMap = new StaticMap(null);
        graph.getOrCreate("hash1", "TargetActivity");
        graph.recordVisit("hash1", "TargetActivity");
        assertEquals(0, scorer.bfsBoost("MainActivity", graph, staticMap));
    }

    @Test
    void testWtgScorerReturnsNonZeroWithLoadedJsonArray() throws Exception {
        // End-to-end: JsonArray transitions -> WtgScorer returns boost
        File tempFile = createTransitionsJson();
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(staticMap.isLoaded());

            ScreenState mainScreen = new ScreenState(
                    Collections.<ScreenItem>emptyList(), "MainActivity");
            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            int score = scorer.score(action, mainScreen, graph, staticMap);
            assertEquals(200, score, "1-hop unvisited activity should give +200 boost");
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testWtgScorerReturnsZeroForVisitedTarget() throws Exception {
        File tempFile = createTransitionsJson();
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());

            // Mark target as visited
            graph.getOrCreate("hash1", "SettingsActivity");
            graph.recordVisit("hash1", "SettingsActivity");

            ScreenState mainScreen = new ScreenState(
                    Collections.<ScreenItem>emptyList(), "MainActivity");
            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            int score = scorer.score(action, mainScreen, graph, staticMap);
            assertEquals(0, score, "Visited target should give 0 boost");
        } finally {
            tempFile.delete();
        }
    }

    // --- Helper ---

    private File createTransitionsJson() throws Exception {
        File tempFile = Files.createTempFile("wtg_scorer_test", ".json").toFile();
        String json = "{"
                + "\"reachability\":[],"
                + "\"windows\":["
                + "{\"id\":1,\"name\":\"com.example.app.MainActivity\",\"type\":\"ACTIVITY\",\"isMain\":true,\"widgets\":[]},"
                + "{\"id\":2,\"name\":\"com.example.app.SettingsActivity\",\"type\":\"ACTIVITY\",\"isMain\":false,\"widgets\":[]}"
                + "],"
                + "\"transitions\":["
                + "{\"sourceId\":1,\"targetId\":2,\"events\":[{\"type\":\"implicit_launch_event\"}]}"
                + "]"
                + "}";
        try (FileWriter writer = new FileWriter(tempFile)) {
            writer.write(json);
        }
        return tempFile;
    }
}
