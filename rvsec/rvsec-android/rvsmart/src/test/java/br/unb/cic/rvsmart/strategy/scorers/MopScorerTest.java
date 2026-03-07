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
 *
 * MopScorer uses screen.getActivity() to check if any method on that activity
 * reaches a monitored operation. The JSON keys are method signatures like
 * "TestActivity.someMethod()" and the scorer matches by activity prefix.
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
        // Method key starts with "TestActivity." so activityHasDirectMop("TestActivity") matches
        File tempFile = createActivityBasedJson("TestActivity.doEncrypt()", true, false);
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
        File tempFile = createActivityBasedJson("TestActivity.doHash()", false, true);
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
        // Method key is for a different activity
        File tempFile = createActivityBasedJson("OtherActivity.doSomething()", true, true);
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
        File tempFile = createActivityBasedJson("TestActivity.encrypt()", true, false);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            Action action = new Action(Action.Type.CLICK, 50, 60, "algorithm", "Button");
            assertEquals(1000, custom.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testActivityWithCodePackagePrefix() throws Exception {
        // When codePackage is set, the qualified prefix is "com.example.TestActivity."
        ScreenState pkgScreen = new ScreenState(
                Collections.<ScreenItem>emptyList(), "TestActivity");
        File tempFile = createActivityBasedJson("com.example.TestActivity.method()", true, false);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            staticMap.setCodePackage("com.example");
            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            assertEquals(500, scorer.score(action, pkgScreen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    // --- Helper ---

    /**
     * Creates a temporary JSON file with activity-based method signatures.
     * The method signature format matches what StaticMap.activityHasDirectMop() expects:
     * keys start with "ActivityName." so prefix matching works.
     */
    private File createActivityBasedJson(String methodSig, boolean directMop, boolean transitiveMop)
            throws Exception {
        File tempFile = Files.createTempFile("static_map_test", ".json").toFile();
        String json = "{"
                + "\"reachability\": {"
                + "\"directly_reaches_mop\": {\"" + methodSig + "\": " + directMop + "},"
                + "\"reaches_mop\": {\"" + methodSig + "\": " + transitiveMop + "}"
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
