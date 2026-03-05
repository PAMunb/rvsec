package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for MopScorer — scores actions based on MOP reachability from static analysis.
 */
class MopScorerTest {

    private final MopScorer scorer = new MopScorer(500, 300);
    private final DynamicStateGraph graph = new DynamicStateGraph();
    private final ScreenState screen = new ScreenState(
            Collections.<ScreenItem>emptyList(), "TestActivity");

    @Test
    void testReturnsZeroWhenStaticMapIsNull() {
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroWhenStaticMapNotLoaded() {
        // StaticMap with null path is not loaded
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsDirectScoreWhenHasDirectMop() throws Exception {
        String actionSig = "click@100,200";
        File tempFile = createStaticMapJson(actionSig, true, false);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(staticMap.isLoaded());

            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            assertEquals(500, scorer.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testReturnsTransitiveScoreWhenHasMopButNotDirect() throws Exception {
        String actionSig = "click@100,200";
        File tempFile = createStaticMapJson(actionSig, false, true);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(staticMap.isLoaded());

            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            assertEquals(300, scorer.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testReturnsZeroWhenActionNotInMop() throws Exception {
        // Create a static map with a different action signature
        File tempFile = createStaticMapJson("click@999,999", true, true);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(staticMap.isLoaded());

            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            assertEquals(0, scorer.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testCustomConstructorValues() throws Exception {
        MopScorer custom = new MopScorer(1000, 600);
        String actionSig = "click@50,60";
        File tempFile = createStaticMapJson(actionSig, true, false);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            Action action = new Action(Action.Type.CLICK, 50, 60, "algorithm", "Button");
            assertEquals(1000, custom.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    // --- Helper ---

    /**
     * Creates a temporary JSON file with static analysis data for a single action signature.
     */
    private File createStaticMapJson(String actionSig, boolean directMop, boolean transitiveMop)
            throws Exception {
        File tempFile = Files.createTempFile("static_map_test", ".json").toFile();
        String json = "{"
                + "\"reachability\": {"
                + "\"directly_reaches_mop\": {\"" + actionSig + "\": " + directMop + "},"
                + "\"reaches_mop\": {\"" + actionSig + "\": " + transitiveMop + "}"
                + "},"
                + "\"windows\": {},"
                + "\"transitions\": {}"
                + "}";
        try (FileWriter writer = new FileWriter(tempFile)) {
            writer.write(json);
        }
        return tempFile;
    }
}
