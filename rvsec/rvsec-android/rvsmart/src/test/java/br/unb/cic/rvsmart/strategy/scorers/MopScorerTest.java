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
 * Tests for MopScorer — scores actions based on activity-level MOP reachability.
 * Uses the JsonArray format from RvsecAnalysisClient (gh27).
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
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsDirectScoreWhenActivityHasDirectMop() throws Exception {
        File tempFile = createReachabilityJson("com.example.TestActivity", true, false);
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
    void testReturnsTransitiveScoreWhenActivityHasMopButNotDirect() throws Exception {
        File tempFile = createReachabilityJson("com.example.TestActivity", false, true);
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
    void testReturnsZeroWhenActivityNotInMop() throws Exception {
        File tempFile = createReachabilityJson("com.example.OtherActivity", true, true);
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
        File tempFile = createReachabilityJson("com.example.TestActivity", true, false);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            Action action = new Action(Action.Type.CLICK, 50, 60, "algorithm", "Button");
            assertEquals(1000, custom.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testEndToEndWithJsonArrayFormat() throws Exception {
        // Verifies the full chain: JSON parsing -> MopScorer returns non-zero
        File tempFile = createReachabilityJson(
                "com.example.app.CryptoActivity", true, true);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(staticMap.isLoaded());

            ScreenState cryptoScreen = new ScreenState(
                    Collections.<ScreenItem>emptyList(), "CryptoActivity");
            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            int score = scorer.score(action, cryptoScreen, graph, staticMap);
            assertTrue(score > 0, "MopScorer should return non-zero for activity with directMop");
            assertEquals(500, score);
        } finally {
            tempFile.delete();
        }
    }

    // --- Helper ---

    private File createReachabilityJson(String className, boolean directMop, boolean transitiveMop)
            throws Exception {
        File tempFile = Files.createTempFile("mop_scorer_test", ".json").toFile();
        String json = "{"
                + "\"reachability\":[{"
                + "\"className\":\"" + className + "\","
                + "\"isActivity\":true,"
                + "\"methods\":[{"
                + "\"name\":\"doEncrypt\","
                + "\"signature\":\"<" + className + ": void doEncrypt()>\","
                + "\"reachable\":true,"
                + "\"reachesMop\":" + transitiveMop + ","
                + "\"directlyReachesMop\":" + directMop
                + "}]"
                + "}],"
                + "\"windows\":[],"
                + "\"transitions\":[]"
                + "}";
        try (FileWriter writer = new FileWriter(tempFile)) {
            writer.write(json);
        }
        return tempFile;
    }
}
